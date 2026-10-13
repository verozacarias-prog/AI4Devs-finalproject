#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API contract checks for the Platita repository.

The contract of the API is generated from the code and versioned in
frontend/src/api/openapi.json; the pipeline fails if that file is not what the code
generates. This script checks that file, so it needs nothing installed:

  1. The reference is complete. Every operation says what it is for (summary and
     description) and has a tag; every response says when it happens, in words of its own
     and not the default ones of the framework; every parameter and every field of every
     schema is described; and no schema of the framework is left in the contract. An
     operation that asks for a session documents its 401, and one that changes something
     documents the 403 of the origin check.
  2. Every error has the body of an error. A response that is not a success uses the
     error schema, unless it answers with the same body as the success, as the health
     routes do.
  3. The contract matches the specification. Every operation of the contract is in
     docs/04-api.md, and so is every status it may answer with.

What it does not check: that docs/04-api.md describes each field, or that an endpoint the
specification describes is implemented. The specification may be ahead of the code.

Tolerant by design: while the contract file does not exist, there is nothing to check.

    python3 scripts/verify_api_contract.py
"""
import http
import io
import json
import os
import re
import sys

CONTRACT_PATH = os.path.join('frontend', 'src', 'api', 'openapi.json')
SPEC_PATH = os.path.join('docs', '04-api.md')

HTTP_METHODS = ('get', 'post', 'put', 'patch', 'delete', 'head', 'options')
ERROR_SCHEMA = 'ErrorBody'
# Lo que el framework escribe solo cuando nadie describió la respuesta.
FRAMEWORK_DESCRIPTIONS = {'Successful Response', 'Validation Error'}
FRAMEWORK_SCHEMAS = {'HTTPValidationError', 'ValidationError'}
FIRST_ERROR_STATUS = 400
MIN_SUMMARY_WORDS = 2
# Un pedido que modifica algo pasa por el control de origen, y uno que pide sesión puede no
# tenerla: los dos tienen que estar en la referencia.
CHANGING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
UNAUTHORIZED = '401'
FORBIDDEN = '403'

# En 04-api.md, un título de endpoint nombra una o varias operaciones entre acentos graves.
SPEC_HEADING = re.compile(r'^#{2,6} ')
SPEC_OPERATION = re.compile(r'`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (/[^`\s]*)`')
SPEC_STATUS = re.compile(r'(?<![\w.])([1-5][0-9]{2})(?![\w.])')
PATH_PARAMETER = re.compile(r'\{[^}]*\}')


def read_json(path):
    with io.open(path, encoding='utf-8') as handle:
        return json.load(handle)


def read_text(path):
    with io.open(path, encoding='utf-8') as handle:
        return handle.read()


def operations_of(contract):
    """Yields (label, method, path, operation) for every operation of the contract."""
    for path in sorted(contract.get('paths', {})):
        for method in HTTP_METHODS:
            operation = contract['paths'][path].get(method)
            if operation is not None:
                yield '{} {}'.format(method.upper(), path), method.upper(), path, operation


def is_default_description(status, description):
    if not description or description in FRAMEWORK_DESCRIPTIONS:
        return True
    try:
        return description == http.HTTPStatus(int(status)).phrase
    except ValueError:
        return False


def schema_names(node):
    """Every schema a piece of the contract refers to, by name."""
    names = set()
    if isinstance(node, dict):
        reference = node.get('$ref')
        if isinstance(reference, str):
            names.add(reference.rsplit('/', 1)[-1])
        for value in node.values():
            names |= schema_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= schema_names(value)
    return names


def check_reference(contract):
    errors = []
    info = contract.get('info', {})
    if not info.get('description'):
        errors.append('el contrato no dice qué es la API (falta info.description)')
    described_tags = {tag.get('name') for tag in contract.get('tags', []) if tag.get('description')}

    for label, _method, _path, operation in operations_of(contract):
        summary = operation.get('summary', '')
        if len(summary.split()) < MIN_SUMMARY_WORDS:
            # Una sola palabra es el nombre de la función, que el framework pone solo.
            errors.append('{}: falta el resumen (summary), escrito a mano'.format(label))
        responses = operation.get('responses', {})
        if operation.get('security') and UNAUTHORIZED not in responses:
            errors.append('{}: pide sesión y no documenta su {}'.format(label, UNAUTHORIZED))
        if _method in CHANGING_METHODS and FORBIDDEN not in responses:
            errors.append('{}: modifica algo y no documenta el {} del control de '
                          'origen'.format(label, FORBIDDEN))
        if not operation.get('description'):
            errors.append('{}: falta la descripción, que dice para qué sirve'.format(label))
        tags = operation.get('tags', [])
        if not tags:
            errors.append('{}: no está en ningún grupo (tags)'.format(label))
        for tag in tags:
            if tag not in described_tags:
                errors.append('{}: el grupo "{}" no tiene descripción'.format(label, tag))
        for parameter in operation.get('parameters', []):
            if not parameter.get('description'):
                errors.append('{}: el parámetro "{}" no tiene descripción'.format(
                    label, parameter.get('name')))
        success_schemas = set()
        for status, response in sorted(operation.get('responses', {}).items()):
            if status.isdigit() and int(status) < FIRST_ERROR_STATUS:
                success_schemas |= schema_names(response)
        for status, response in sorted(operation.get('responses', {}).items()):
            if is_default_description(status, response.get('description')):
                errors.append('{}: la respuesta {} no dice cuándo ocurre'.format(label, status))
            if status.isdigit() and int(status) >= FIRST_ERROR_STATUS:
                used = schema_names(response)
                if used != {ERROR_SCHEMA} and not (used and used <= success_schemas):
                    errors.append('{}: la respuesta {} no usa el cuerpo de un error ({})'.format(
                        label, status, ERROR_SCHEMA))

    schemas = contract.get('components', {}).get('schemas', {})
    for name in sorted(schemas):
        if name in FRAMEWORK_SCHEMAS:
            errors.append('el esquema "{}" es del framework: ninguna respuesta de la API '
                          'tiene esa forma'.format(name))
            continue
        for field, definition in sorted(schemas[name].get('properties', {}).items()):
            if not definition.get('description'):
                errors.append('{}.{}: el campo no tiene descripción'.format(name, field))
    return errors


def normalized(path):
    """A path with its parameters unnamed: the specification may name them differently."""
    return PATH_PARAMETER.sub('{}', path)


def spec_sections(text):
    """Maps each operation the specification names in a title to the text of its section."""
    sections = {}
    current = []
    body = []

    def close():
        for operation in current:
            sections[operation] = '\n'.join(body)

    in_code = False
    for line in text.splitlines():
        if line.startswith('```'):
            in_code = not in_code
        if not in_code and SPEC_HEADING.match(line):
            close()
            current = [(method, normalized(path))
                       for method, path in SPEC_OPERATION.findall(line)]
            body = [line]
        else:
            body.append(line)
    close()
    return sections


def check_against_spec(contract, spec_text):
    errors = []
    sections = spec_sections(spec_text)
    for label, method, path, operation in operations_of(contract):
        section = sections.get((method, normalized(path)))
        if section is None:
            errors.append('{}: está en el contrato y no en {}'.format(label, SPEC_PATH))
            continue
        documented = set(SPEC_STATUS.findall(section))
        for status in sorted(operation.get('responses', {})):
            if status not in documented:
                errors.append('{}: responde {} y su sección de {} no lo nombra'.format(
                    label, status, SPEC_PATH))
    return errors


def main():
    print('Verificación del contrato de la API')
    if not os.path.isfile(CONTRACT_PATH):
        print('  {} no existe todavía: nada que revisar.'.format(CONTRACT_PATH))
        return 0
    contract = read_json(CONTRACT_PATH)
    errors = check_reference(contract)
    if os.path.isfile(SPEC_PATH):
        errors += check_against_spec(contract, read_text(SPEC_PATH))
    else:
        errors.append('{} no existe'.format(SPEC_PATH))

    print('  operaciones revisadas : {}'.format(len(list(operations_of(contract)))))
    print('')
    if errors:
        for error in errors:
            print('  ERROR  {}'.format(error))
        print('')
        print('{} error/es.'.format(len(errors)))
        return 1
    print('Sin errores.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
