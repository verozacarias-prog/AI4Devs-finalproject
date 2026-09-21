#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Architecture rule checks for the Platita repository.

Enforces the two structural rules of ADR 0001, declared in AGENTS.md:

  1. backend/app/domain/ must not depend on adapters or on infrastructure libraries.
  2. frontend/ must not import from backend/ nor reach the database directly.

Tolerant by design: while backend/ or frontend/ do not exist yet, the matching
checks are skipped instead of failing, so the net is in place before the first
file lands.

    python3 scripts/verify_architecture.py
"""
import ast
import io
import os
import re
import sys

DOMAIN_DIR = os.path.join('backend', 'app', 'domain')
ADAPTERS_PKG = 'adapters'
FRONTEND_DIR = 'frontend'

# AGENTS.md — imports prohibidos dentro de domain/
FORBIDDEN_IN_DOMAIN = {
    'sqlalchemy': 'ORM: pertenece a adapters/outbound/postgres/',
    'alembic': 'migraciones: pertenecen a backend/migrations/',
    'fastapi': 'framework web: pertenece a adapters/inbound/api/',
    'starlette': 'framework web: pertenece a adapters/inbound/',
    'httpx': 'cliente HTTP: pertenece a un adaptador de salida',
    'requests': 'cliente HTTP: pertenece a un adaptador de salida',
    'psycopg': 'driver de base de datos: pertenece a adapters/outbound/postgres/',
    'psycopg2': 'driver de base de datos: pertenece a adapters/outbound/postgres/',
    'asyncpg': 'driver de base de datos: pertenece a adapters/outbound/postgres/',
    'redis': 'infraestructura: pertenece a un adaptador de salida',
    'anthropic': 'cliente de LLM: pertenece a adapters/outbound/llm_client/',
    'openai': 'cliente de LLM: pertenece a adapters/outbound/llm_client/',
    'litellm': 'cliente de LLM: pertenece a adapters/outbound/llm_client/',
    'boto3': 'infraestructura: pertenece a un adaptador de salida',
}

# AGENTS.md §6 — Pydantic sólo en el borde
EDGE_ONLY_IN_DOMAIN = {
    'pydantic': 'Pydantic va sólo en el borde (adaptadores), no en el dominio',
}

# frontend/ no puede alcanzar la base de datos
DB_LEAK_PATTERNS = [
    (re.compile(r'postgres(?:ql)?://', re.I), 'cadena de conexión a PostgreSQL'),
    (re.compile(r'\bDATABASE_URL\b'), 'variable de conexión a la base de datos'),
    (re.compile(r'\bfrom\s+[\'"][^\'"]*\.\./backend', re.I), 'import desde backend/'),
    (re.compile(r'\brequire\([\'"][^\'"]*\.\./backend', re.I), 'require desde backend/'),
    (re.compile(r'\bfrom\s+[\'"]@backend/', re.I), 'alias de import hacia backend/'),
]
FRONTEND_SOURCE_EXT = ('.ts', '.tsx', '.js', '.jsx', '.vue', '.svelte', '.mjs')
SKIP_DIRS = {'node_modules', '.git', '__pycache__', 'dist', 'build', '.next', '.venv', 'venv'}

errors = []
warnings = []
skipped = []


def read(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def walk(root, extensions):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in sorted(names):
            if n.endswith(extensions):
                yield os.path.join(base, n)


def root_module(name):
    return (name or '').split('.')[0]


def check_domain_imports():
    """Regla 1: el dominio no conoce la infraestructura ni los adaptadores."""
    if not os.path.isdir(DOMAIN_DIR):
        skipped.append('%s todavía no existe: regla de dependencia del dominio no evaluada'
                       % DOMAIN_DIR)
        return 0

    checked = 0
    for path in walk(DOMAIN_DIR, ('.py',)):
        checked += 1
        source = read(path)
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            errors.append('%s:%s no se pudo parsear (%s)' % (path, exc.lineno, exc.msg))
            continue

        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [(a.name, node.lineno) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                # from . import x  -> node.module is None; los relativos se revisan aparte
                targets = [(node.module, node.lineno)]
                if node.level and node.module and ADAPTERS_PKG in node.module.split('.'):
                    errors.append('%s:%d el dominio importa de %s/ — debe hablar sólo con puertos'
                                  % (path, node.lineno, ADAPTERS_PKG))

            for module, line in targets:
                if not module:
                    continue
                head = root_module(module)
                if ADAPTERS_PKG in module.split('.'):
                    errors.append('%s:%d el dominio importa de %s/ — debe hablar sólo con puertos'
                                  % (path, line, ADAPTERS_PKG))
                elif head in FORBIDDEN_IN_DOMAIN:
                    errors.append('%s:%d import prohibido en el dominio: %s (%s)'
                                  % (path, line, head, FORBIDDEN_IN_DOMAIN[head]))
                elif head in EDGE_ONLY_IN_DOMAIN:
                    errors.append('%s:%d %s (%s)'
                                  % (path, line, head, EDGE_ONLY_IN_DOMAIN[head]))
    return checked


def check_money_types():
    """AGENTS.md §5: montos en Decimal, nunca float. Aviso, no error."""
    if not os.path.isdir(DOMAIN_DIR):
        return
    money = re.compile(r'(amount|balance|limit|income|total|price|monto|saldo)', re.I)
    for path in walk(DOMAIN_DIR, ('.py',)):
        try:
            tree = ast.parse(read(path), filename=path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            annotation = getattr(node, 'annotation', None)
            if annotation is None:
                continue
            name = None
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
            elif isinstance(node, ast.arg):
                name = node.arg
            if not name or not money.search(name):
                continue
            if isinstance(annotation, ast.Name) and annotation.id == 'float':
                warnings.append('%s:%d "%s" está tipado como float; los montos van en Decimal'
                                % (path, node.lineno, name))


def check_frontend_isolation():
    """Regla 2: el frontend habla con el backend sólo por la API REST."""
    if not os.path.isdir(FRONTEND_DIR):
        skipped.append('%s/ todavía no existe: aislamiento del frontend no evaluado'
                       % FRONTEND_DIR)
        return 0

    checked = 0
    for path in walk(FRONTEND_DIR, FRONTEND_SOURCE_EXT):
        checked += 1
        for lineno, line in enumerate(read(path).split('\n'), 1):
            for pattern, label in DB_LEAK_PATTERNS:
                if pattern.search(line):
                    errors.append('%s:%d %s — el frontend habla con el backend sólo por la API '
                                  'REST (ADR 0001)' % (path, lineno, label))
    return checked


def main():
    if not os.path.exists('AGENTS.md'):
        print('Ejecutá este script desde la raíz del repositorio.')
        return 1

    domain_files = check_domain_imports()
    check_money_types()
    frontend_files = check_frontend_isolation()

    print('Verificación de arquitectura')
    print('  archivos de dominio revisados  : %d' % domain_files)
    print('  archivos de frontend revisados : %d' % frontend_files)
    print('')

    for s in skipped:
        print('  OMITIDO  %s' % s)
    for w in warnings:
        print('  AVISO    %s' % w)
    for e in errors:
        print('  ERROR    %s' % e)

    if errors:
        print('\n%d error(es). Las reglas están en AGENTS.md y en '
              'docs/adr/0001-arquitectura-hexagonal.md.' % len(errors))
        return 1
    if skipped and not domain_files and not frontend_files:
        print('Todavía no hay código que revisar. La verificación queda lista para cuando lo haya.')
    else:
        print('Sin errores%s.' % (' (%d aviso/s)' % len(warnings) if warnings else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
