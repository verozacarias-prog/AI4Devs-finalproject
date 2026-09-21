#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Documentation consistency checks for the Platita repository.

Run it from the repository root:

    python3 scripts/verify_docs.py

Exits with 1 if any check fails. Warnings never fail the run.
Conventions enforced here are documented in docs/08-convenciones-de-documentacion.md.
"""
import glob
import io
import itertools
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

README = 'README.md'
DOCS_DIR = 'docs'
ADR_DIR = os.path.join(DOCS_DIR, 'adr')
COMMANDS_DIR = os.path.join('.claude', 'commands')
SKILLS_DIR = os.path.join('.claude', 'skills')
CANONICAL = {'README.md', 'CLAUDE.md', 'AGENTS.md', 'LICENSE', 'prompts.md'}

README_SOFT_LIMIT = 95        # ficha (0.1-0.5) + una línea por documento + enlaces
MIN_SENTENCE = 90             # ignora frases cortas, que coinciden por vocabulario
SIM_ERROR = 0.90              # entre documentos vivos: duplicación real
SIM_WARN = 0.85               # entre documentos vivos: revisar a mano
SIM_ADR = 0.80                # doc vs ADR: sólo se avisa, ver §8.6

errors = []
warnings = []


def fail(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def read(path):
    return io.open(path, encoding='utf-8').read()


def markdown_files():
    out = [README]
    for name in ('CLAUDE.md', 'AGENTS.md', 'prompts.md'):
        if os.path.exists(name):
            out.append(name)
    for root, _, names in os.walk(DOCS_DIR):
        for n in sorted(names):
            if n.endswith('.md'):
                out.append(os.path.join(root, n))
    if os.path.isdir(COMMANDS_DIR):
        for n in sorted(os.listdir(COMMANDS_DIR)):
            if n.endswith('.md'):
                out.append(os.path.join(COMMANDS_DIR, n))
    for p in sorted(glob.glob(os.path.join(SKILLS_DIR, '*', 'SKILL.md'))):
        out.append(p)
    return out


def is_adr(path):
    return os.path.normpath(path).startswith(os.path.normpath(ADR_DIR) + os.sep)


def anchor(heading):
    """GitHub-style slug for a Markdown heading."""
    h = re.sub(r'`|\*\*|\*', '', heading).strip().rstrip(':').lower().replace(' ', '-')
    return ''.join(c for c in h if c.isalnum() or c in '-_')


def anchors_of(path):
    return set(anchor(h) for h in re.findall(r'^#{1,6}\s+(.*)$', read(path), re.M))


def strip_code(text):
    return re.sub(r'```.*?```', '', text, flags=re.S)


def sentences(path):
    t = strip_code(read(path))
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)   # enlaces -> sólo el texto
    t = re.sub(r'[*`>#|]', ' ', t)
    out = []
    for s in re.split(r'(?<=[.:;])\s+|\n\n', t):
        s = ' '.join(s.split())
        if len(s) >= MIN_SENTENCE:
            out.append(s)
    return out


# --- 1. los enlaces relativos resuelven a archivo y a ancla existentes -----------
def check_links(files):
    cache = {os.path.normpath(f): anchors_of(f) for f in files}
    total = 0
    for f in files:
        text = strip_code(read(f))
        for m in re.finditer(r'\[[^\]]*\]\(([^)\s]+)\)', text):
            target = m.group(1)
            if target.startswith(('http://', 'https://', 'mailto:')):
                continue
            total += 1
            if target.startswith('#'):
                if target[1:] not in cache[os.path.normpath(f)]:
                    fail('ancla interna inexistente: %s -> %s' % (f, target))
                continue
            path, _, frag = target.partition('#')
            resolved = os.path.normpath(os.path.join(os.path.dirname(f), path))
            if not os.path.exists(resolved):
                fail('enlace roto: %s -> %s' % (f, target))
            elif frag and os.path.isfile(resolved) and frag not in cache.get(resolved, set()):
                fail('ancla inexistente: %s -> %s' % (f, target))
    return total


# --- 2. ningún documento de docs/ queda sin enlazar desde el README -------------
def check_orphans():
    index = read(README)

    def linked(path):
        if path in index:
            return True
        # un enlace al directorio (docs/adr/, docs/features/) cubre su contenido
        parent = os.path.dirname(path)
        while parent and os.path.normpath(parent) != os.path.normpath(DOCS_DIR):
            if (parent.replace(os.sep, '/') + '/') in index:
                return True
            parent = os.path.dirname(parent)
        return False

    for root, _, names in os.walk(DOCS_DIR):
        for n in sorted(names):
            if not n.endswith('.md'):
                continue
            path = os.path.join(root, n)
            if not linked(path):
                fail('documento huérfano, no enlazado desde %s: %s' % (README, path))


# --- 3. ningún contenido repetido entre archivos --------------------------------
def is_record(path):
    """Registros que citan texto de otros archivos por definición: prompts y transcripciones."""
    base = os.path.basename(path)
    return base == 'prompts.md' or base.startswith('conversacion-')


def check_duplicates(files):
    files = [f for f in files if not is_record(f)]

    seen = {}
    for f in files:
        lines = [l.rstrip() for l in read(f).split('\n')]
        for i in range(len(lines) - 3):
            window = lines[i:i + 4]
            if sum(1 for l in window if l.strip()) < 4:
                continue
            key = '\n'.join(window)
            if key in seen and seen[key] != f:
                fail('bloque idéntico en dos archivos: %s y %s -> %.60s...'
                     % (seen[key], f, window[0].strip()))
            seen.setdefault(key, f)

    corpus = {f: sentences(f) for f in files}
    for a, b in itertools.combinations(files, 2):
        for x in corpus[a]:
            for y in corpus[b]:
                ratio = SequenceMatcher(None, x, y).ratio()
                if is_adr(a) or is_adr(b):
                    # §8.6: un ADR puede repetir para ser autosuficiente, pero un
                    # documento vivo no puede repetir lo que dice un ADR.
                    if ratio >= SIM_ADR:
                        warn('doc y ADR comparten texto (%.2f): %s y %s\n'
                             '        esperable si el ADR repite para ser autosuficiente (§8.6);\n'
                             '        revisar que no sea el documento repitiendo el porqué del ADR\n'
                             '        -> %.85s...' % (ratio, a, b, x))
                elif ratio >= SIM_ERROR:
                    fail('texto duplicado (%.2f) entre %s y %s -> %.70s...' % (ratio, a, b, x))
                elif ratio >= SIM_WARN:
                    warn('texto parecido (%.2f) entre %s y %s -> %.70s...' % (ratio, a, b, x))


# --- 4. bloques de código y Mermaid completos -----------------------------------
def check_fences(files):
    for f in files:
        text = read(f)
        if text.count('```') % 2:
            fail('bloque de código sin cerrar en %s' % f)
        for m in re.finditer(r'```mermaid\n(.*?)\n```', text, re.S):
            body = m.group(1).strip()
            if not body:
                fail('bloque mermaid vacío en %s' % f)
            elif not re.match(r'(flowchart|graph|sequenceDiagram|erDiagram|classDiagram|'
                              r'stateDiagram|gantt|pie|journey|mindmap)\b', body):
                fail('bloque mermaid sin tipo de diagrama reconocible en %s: %.40s' % (f, body))


# --- 5. nombres de archivo sin acentos, ñ ni espacios ---------------------------
def check_names():
    for root, dirs, names in os.walk('.'):
        if any(p in root for p in ('/.git', 'node_modules', '__pycache__')):
            continue
        for n in names + dirs:
            if n.startswith('.'):
                continue
            decomposed = unicodedata.normalize('NFD', n)
            if ' ' in n or any(unicodedata.combining(c) or ord(c) > 127 for c in decomposed):
                fail('nombre de archivo con espacio, acento o ñ: %s' % os.path.join(root, n))


# --- 6. el README es portada, no resumen ----------------------------------------
def check_readme_size():
    n = len(read(README).split('\n'))
    if n > README_SOFT_LIMIT:
        warn('%s tiene %d líneas (referencia: %d). Revisá que no haya entrado el resumen '
             'de una sección.' % (README, n, README_SOFT_LIMIT))
    return n


# --- 7. la serie numerada está cerrada ------------------------------------------
def check_series():
    numbered = sorted(n for n in os.listdir(DOCS_DIR) if re.match(r'^\d\d-', n))
    expected = ['%02d-' % i for i in range(1, len(numbered) + 1)]
    got = [n[:3] for n in numbered]
    if got != expected:
        fail('la serie numerada de %s tiene huecos o repetidos: %s' % (DOCS_DIR, got))
    return numbered


# --- 8. los ADR conservan su plantilla ------------------------------------------
def check_adrs():
    required = ['## Contexto', '## Decisión', '## Consecuencias',
                '### Positivas', '### Negativas y costos asumidos',
                '## Alternativas descartadas']
    if not os.path.isdir(ADR_DIR):
        return []
    found = sorted(n for n in os.listdir(ADR_DIR) if n.endswith('.md'))
    for n in found:
        text = read(os.path.join(ADR_DIR, n))
        for section in required:
            if section not in text:
                fail('el ADR %s no tiene la sección "%s"' % (n, section))
        if '- Estado:' not in text:
            fail('el ADR %s no declara Estado' % n)
        if 'Los ADR son inmutables' not in text:
            fail('el ADR %s no lleva la nota de inmutabilidad' % n)
    return found


# --- 9. commands y skills tienen frontmatter válido -------------------------------
def _check_frontmatter(path, label, required):
    """Un frontmatter roto no avisa: el command no se carga y el skill pierde todos
    sus campos, cayendo al nombre del directorio y a la primera línea del cuerpo."""
    n = os.path.relpath(path)
    lines = read(path).split('\n')
    if not lines or lines[0].strip() != '---':
        fail('%s %s no abre con un delimitador "---" de frontmatter (primera línea: %r)'
             % (label, n, lines[0][:20] if lines else ''))
        return
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
    except StopIteration:
        fail('%s %s no cierra el frontmatter' % (label, n))
        return
    body = '\n'.join(lines[1:end])
    for field in required:
        if not re.search(r'^%s:\s*\S' % field, body, re.M):
            fail('%s %s no declara "%s" en el frontmatter' % (label, n, field))
    if not '\n'.join(lines[end + 1:]).strip():
        fail('%s %s no tiene instrucciones debajo del frontmatter' % (label, n))


def check_skills():
    found = sorted(glob.glob(os.path.join(SKILLS_DIR, '*', 'SKILL.md')))
    for p in found:
        _check_frontmatter(p, 'el skill', ('name', 'description'))
        declared = re.search(r'^name:\s*(\S+)', read(p), re.M)
        folder = os.path.basename(os.path.dirname(p))
        if declared and declared.group(1).strip() != folder:
            fail('el skill %s declara name "%s" pero vive en el directorio "%s"'
                 % (os.path.relpath(p), declared.group(1).strip(), folder))
    return found


def check_commands():
    if not os.path.isdir(COMMANDS_DIR):
        return []
    found = sorted(n for n in os.listdir(COMMANDS_DIR) if n.endswith('.md'))
    for n in found:
        path = os.path.join(COMMANDS_DIR, n)
        lines = read(path).split('\n')
        if not lines or lines[0].strip() != '---':
            fail('el command %s no abre con un delimitador "---" de frontmatter (primera línea: %r)'
                 % (n, lines[0][:20] if lines else ''))
            continue
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
        except StopIteration:
            fail('el command %s no cierra el frontmatter' % n)
            continue
        body = '\n'.join(lines[1:end])
        if not re.search(r'^description:\s*\S', body, re.M):
            fail('el command %s no declara "description" en el frontmatter' % n)
        if not lines[end + 1:] or not '\n'.join(lines[end + 1:]).strip():
            fail('el command %s no tiene instrucciones debajo del frontmatter' % n)
    return found


def main():
    if not os.path.exists(README) or not os.path.isdir(DOCS_DIR):
        print('Ejecutá este script desde la raíz del repositorio.')
        return 1

    files = markdown_files()
    links = check_links(files)
    check_orphans()
    check_duplicates(files)
    check_fences(files)
    check_names()
    readme_lines = check_readme_size()
    numbered = check_series()
    adrs = check_adrs()
    commands = check_commands()
    skills = check_skills()

    print('Verificación de documentación')
    print('  archivos markdown revisados : %d' % len(files))
    print('  enlaces relativos validados : %d' % links)
    print('  documentos numerados        : %d' % len(numbered))
    print('  ADR                         : %d' % len(adrs))
    print('  commands                    : %d' % len(commands))
    print('  skills                      : %d' % len(skills))
    print('  %s                   : %d líneas' % (README, readme_lines))
    print('')

    for w in warnings:
        print('  AVISO  %s' % w)
    for e in errors:
        print('  ERROR  %s' % e)

    if errors:
        print('\n%d error(es). Ver docs/08-convenciones-de-documentacion.md.' % len(errors))
        return 1
    print('%s Sin errores%s.' % ('', ' (%d aviso/s)' % len(warnings) if warnings else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
