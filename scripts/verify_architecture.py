#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Architecture rule checks for the Platita repository.

Enforces the structural rules of ADR 0001 and ADR 0020, declared in AGENTS.md:

  1. backend/app/domain/ must not depend on adapters or on infrastructure libraries.
  2. frontend/ must not import from backend/ nor reach the database directly.
  3. Inside backend/, database libraries are imported only by the postgres and pgvector
     outbound adapters, the migrations and the tests.
  4. Inside backend/, no AI orchestration framework is imported. The only exception is the
     text splitting package, and only in the text splitter outbound adapter and the tests.
  5. An inbound adapter never imports another one: the API, the message worker, the
     commands and the scheduled processes each reach the use cases on their own, so any of
     them can be replaced or deployed apart without dragging the others.
  6. Every file is where its kind goes: the endpoints in api/routers/, each use case inside
     the folder of its feature, each domain service inside the folder of its topic, nothing
     else loose in domain/ but errors.py, and each repository in a file of its own under
     postgres/repositories/.
  7. No file of backend/app/ or frontend/src/ has a general name, such as utils or helpers:
     its name says what it holds. The shadcn/ui components are left out, as the tool names
     them.
  8. Every folder of backend/app/ and frontend/src/ is in the tree of
     docs/02-arquitectura.md. A folder whose subfolders the tree does not list, such as
     use_cases/, may have any; one whose subfolders it lists must have them all listed.

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

BACKEND_DIR = 'backend'
DOMAIN_DIR = os.path.join(BACKEND_DIR, 'app', 'domain')
ADAPTERS_PKG = 'adapters'
FRONTEND_DIR = 'frontend'

# ADR 0001 — el SQL vive en un solo lugar. Rutas relativas a la raíz del repositorio.
DB_ACCESS_ALLOWED = [
    os.path.join(BACKEND_DIR, 'app', 'adapters', 'outbound', 'postgres'),
    os.path.join(BACKEND_DIR, 'app', 'adapters', 'outbound', 'pgvector'),
    os.path.join(BACKEND_DIR, 'migrations'),
    os.path.join(BACKEND_DIR, 'tests'),
]
DB_LIBRARIES = {'sqlalchemy', 'psycopg', 'psycopg2', 'asyncpg', 'alembic', 'pgvector'}

# ADR 0020 — sin framework de orquestación de IA. Cualquier módulo cuya raíz empiece con
# "langchain" cuenta como framework, además de los de esta lista.
AI_FRAMEWORKS = {'langgraph', 'langsmith', 'llama_index', 'haystack', 'semantic_kernel',
                 'crewai', 'autogen', 'dspy'}
AI_SPLITTER_PACKAGE = 'langchain_text_splitters'
AI_SPLITTER_ALLOWED = [
    os.path.join(BACKEND_DIR, 'app', 'adapters', 'outbound', 'text_splitter'),
    os.path.join(BACKEND_DIR, 'tests'),
]

# ADR 0001 — app/shared/ tiene utilidades técnicas: sólo librería estándar, nada del resto de
# app/, y un módulo por tema. Estos nombres son los de un módulo general.
INBOUND_DIR = os.path.join(BACKEND_DIR, 'app', ADAPTERS_PKG, 'inbound')
INBOUND_PACKAGE = 'app.%s.inbound' % ADAPTERS_PKG
SHARED_DIR = os.path.join(BACKEND_DIR, 'app', 'shared')
# A name that says nothing of what the file holds, so everything ends up in it.
GENERAL_NAMES = {'helpers', 'helper', 'utils', 'util', 'common', 'misc'}
GENERAL_NAME_ROOTS = [os.path.join(BACKEND_DIR, 'app'), os.path.join(FRONTEND_DIR, 'src')]
GENERAL_NAME_EXTENSIONS = ('.py', '.ts', '.tsx', '.js', '.jsx')
# The shadcn/ui components keep the names the tool gives them.
GENERAL_NAME_EXEMPT = [os.path.join(FRONTEND_DIR, 'src', 'components', 'ui')]

# Where each kind of file goes (AGENTS.md § 4).
API_DIR = os.path.join(BACKEND_DIR, 'app', ADAPTERS_PKG, 'inbound', 'api')
ROUTERS_DIR = os.path.join(API_DIR, 'routers')
ROUTER_CLASS = 'APIRouter'
DOMAIN_DIR = os.path.join(BACKEND_DIR, 'app', 'domain')
USE_CASES_DIR = os.path.join(DOMAIN_DIR, 'use_cases')
SERVICES_DIR = os.path.join(DOMAIN_DIR, 'services')
# The only module loose in domain/: everything else goes in its folder.
DOMAIN_LOOSE_FILES = {'errors.py'}
REPOSITORIES_DIR = os.path.join(BACKEND_DIR, 'app', ADAPTERS_PKG, 'outbound', 'postgres',
                                'repositories')
REPOSITORY_CLASS = re.compile(r'^Postgres\w*Repository$')
PACKAGE_FILE = '__init__.py'

# The tree of folders the specification describes, and the folders it must cover.
ARCHITECTURE_DOC = os.path.join('docs', '02-arquitectura.md')
TREE_SECTION = '### **2.3.'
TREE_FENCE = '```'
TREE_INDENT = 2
TREE_FOLDER_MARK = '/'
TREE_ROOTS = [os.path.join(BACKEND_DIR, 'app'), os.path.join(FRONTEND_DIR, 'src')]
STDLIB_MODULES = set(getattr(sys, 'stdlib_module_names', ())) | {'__future__'}

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
    'voyageai': 'cliente de embeddings: pertenece a adapters/outbound/embedding_client/',
    'cohere': 'cliente de IA: pertenece a un adaptador de salida',
    'mistralai': 'cliente de IA: pertenece a un adaptador de salida',
    'tiktoken': 'librería de IA: pertenece a un adaptador de salida',
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
    (re.compile(r'\b(?:from|require\()\s*[\'"](?:pg|postgres|pg-promise|@prisma/client|drizzle-orm'
                r'|knex|typeorm|mysql2?|sequelize)[\'"]', re.I),
     'cliente de base de datos en el frontend'),
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
        # Sin backend/ todavía no hay nada que revisar. Con backend/ pero sin su dominio en la
        # ruta esperada, omitir sería dar por buena una regla que nunca se evaluó.
        if os.path.isdir(BACKEND_DIR):
            errors.append('%s/ existe pero %s no: la regla de dependencia del dominio no se puede '
                          'evaluar. El dominio va en %s (AGENTS.md §4)'
                          % (BACKEND_DIR, DOMAIN_DIR, DOMAIN_DIR))
        else:
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
                # from . import x  -> node.module is None; los relativos se revisan aparte.
                # El paquete importado también puede ser un nombre y no el módulo:
                # "from backend.app import adapters" o "from . import adapters".
                targets = [(node.module, node.lineno)]
                if any(a.name == ADAPTERS_PKG for a in node.names):
                    errors.append('%s:%d el dominio importa de %s/ — debe hablar sólo con puertos'
                                  % (path, node.lineno, ADAPTERS_PKG))
                    continue

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


def mentions_float(annotation):
    """True si la anotación usa float en cualquier nivel: float, Optional[float], list[float]..."""
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id == 'float':
            return True
        if isinstance(node, ast.Attribute) and node.attr == 'float' \
                and isinstance(node.value, ast.Name) and node.value.id == 'builtins':
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and re.search(r'\bfloat\b', node.value):
            return True
    return False


def check_money_types():
    """AGENTS.md §5: montos en Decimal, nunca float. Es error: un float en un monto redondea."""
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
            if mentions_float(annotation):
                errors.append('%s:%d "%s" está tipado con float; los montos van en Decimal'
                              % (path, node.lineno, name))


def imported_modules(tree):
    """Pares (módulo, línea) de cada import absoluto del archivo."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module, node.lineno


def inside(path, directory):
    return os.path.normpath(path).startswith(os.path.normpath(directory) + os.sep)


def check_database_access():
    """Regla 3: fuera de los repositorios, las migraciones y los tests, nadie importa una
    librería de acceso a la base. El dominio lo cubre la regla 1, así que acá se omite."""
    if not os.path.isdir(BACKEND_DIR):
        skipped.append('%s/ todavía no existe: acceso a la base no evaluado' % BACKEND_DIR)
        return 0

    checked = 0
    for path in walk(BACKEND_DIR, ('.py',)):
        if inside(path, DOMAIN_DIR) or any(inside(path, d) for d in DB_ACCESS_ALLOWED):
            continue
        checked += 1
        try:
            tree = ast.parse(read(path), filename=path)
        except SyntaxError as exc:
            errors.append('%s:%s no se pudo parsear (%s)' % (path, exc.lineno, exc.msg))
            continue
        for module, line in imported_modules(tree):
            head = root_module(module)
            if head in DB_LIBRARIES:
                errors.append('%s:%d importa %s fuera de los repositorios — el acceso a la base va '
                              'por un caso de uso y un puerto (ADR 0001)' % (path, line, head))
    return checked


def check_shared_utilities():
    """Regla 5 (ADR 0001): un módulo de app/shared/ importa sólo la librería estándar y no se
    llama como un módulo general."""
    if not os.path.isdir(SHARED_DIR):
        return 0
    if len(STDLIB_MODULES) < 2:
        skipped.append('este Python no lista su librería estándar: %s no evaluado' % SHARED_DIR)
        return 0

    checked = 0
    for path in walk(SHARED_DIR, ('.py',)):
        checked += 1
        try:
            tree = ast.parse(read(path), filename=path)
        except SyntaxError as exc:
            errors.append('%s:%s no se pudo parsear (%s)' % (path, exc.lineno, exc.msg))
            continue
        for node in ast.walk(tree):
            # Un punto queda dentro de shared/; dos o más salen hacia el resto de app/.
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                errors.append('%s:%d sale de app/shared/ con un import relativo — app/shared/ '
                              'no importa nada del resto de app/ (ADR 0001)'
                              % (path, node.lineno))
        for module, line in imported_modules(tree):
            head = root_module(module)
            if head not in STDLIB_MODULES:
                errors.append('%s:%d importa %s — app/shared/ usa sólo la librería estándar y '
                              'nada del resto de app/ (ADR 0001)' % (path, line, module))
    return checked


def is_ai_framework(head):
    return head.startswith('langchain') or head in AI_FRAMEWORKS


def check_ai_frameworks():
    """Regla 4 (ADR 0020): ningún framework de orquestación de IA en el backend. Se permite
    sólo el paquete de particionado, y sólo en su adaptador y en los tests."""
    if not os.path.isdir(BACKEND_DIR):
        skipped.append('%s/ todavía no existe: frameworks de IA no evaluados' % BACKEND_DIR)
        return
    for path in walk(BACKEND_DIR, ('.py',)):
        try:
            tree = ast.parse(read(path), filename=path)
        except SyntaxError:
            continue  # ya lo reportan las reglas 1 y 3
        splitter_allowed = any(inside(path, d) for d in AI_SPLITTER_ALLOWED)
        for module, line in imported_modules(tree):
            head = root_module(module)
            if not is_ai_framework(head):
                continue
            if head == AI_SPLITTER_PACKAGE and splitter_allowed:
                continue
            if head == AI_SPLITTER_PACKAGE:
                errors.append('%s:%d importa %s fuera del adaptador de particionado '
                              '(adapters/outbound/text_splitter/) (ADR 0020)'
                              % (path, line, head))
            else:
                errors.append('%s:%d importa %s — no se usa ningún framework de orquestación '
                              'de IA; los adaptadores usan el SDK del proveedor (ADR 0020)'
                              % (path, line, head))


def inbound_adapter_of(module):
    """El adaptador de entrada al que apunta un módulo importado, o None si no es uno."""
    prefix = INBOUND_PACKAGE + '.'
    if not module.startswith(prefix):
        return None
    return module[len(prefix):].split('.')[0]


def check_inbound_adapters():
    """Regla 5: un adaptador de entrada no importa a otro. Cada uno llega a los casos de uso
    por su cuenta, así que cualquiera se puede reemplazar o desplegar aparte."""
    if not os.path.isdir(INBOUND_DIR):
        return
    for path in walk(INBOUND_DIR, ('.py',)):
        relative = os.path.relpath(path, INBOUND_DIR).split(os.sep)
        if len(relative) < 2:
            # Un archivo suelto en inbound/, como su __init__.py: no es de ningún adaptador.
            continue
        own = relative[0]
        try:
            tree = ast.parse(read(path), filename=path)
        except SyntaxError as exc:
            errors.append('%s:%s no se pudo parsear (%s)' % (path, exc.lineno, exc.msg))
            continue
        targets = [(inbound_adapter_of(module), line) for module, line in imported_modules(tree)]
        # `from app.adapters.inbound import api` names the adapter in the imported names.
        targets += [
            (alias.name, node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == INBOUND_PACKAGE
            for alias in node.names
        ]
        for other, line in targets:
            if other is not None and other != own:
                errors.append('%s:%d el adaptador de entrada %s importa de %s — cada uno llega a '
                              'los casos de uso por su cuenta (ADR 0001)' % (path, line, own, other))


def parsed(path):
    """El árbol de un archivo de Python, o None si no se pudo leer (y queda el error)."""
    try:
        return ast.parse(read(path), filename=path)
    except SyntaxError as exc:
        errors.append('%s:%s no se pudo parsear (%s)' % (path, exc.lineno, exc.msg))
        return None


def check_file_places():
    """Regla 6: cada archivo está donde va su tipo. Un endpoint fuera de api/routers/, un
    caso de uso o un servicio de dominio suelto, o un repositorio fuera de su archivo vuelven a
    mezclar lo que se separó."""
    if os.path.isdir(API_DIR):
        for path in walk(API_DIR, ('.py',)):
            if inside(path, ROUTERS_DIR):
                continue
            tree = parsed(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == ROUTER_CLASS):
                    errors.append('%s:%d declara endpoints fuera de %s — cada grupo de '
                                  'endpoints va en su archivo de routers/' % (path, node.lineno,
                                                                             ROUTERS_DIR))
    if os.path.isdir(USE_CASES_DIR):
        for name in sorted(os.listdir(USE_CASES_DIR)):
            if name.endswith('.py') and name != PACKAGE_FILE:
                errors.append('%s es un caso de uso suelto — va dentro de la carpeta de su '
                              'funcionalidad, como sessions/ o messages/'
                              % os.path.join(USE_CASES_DIR, name))
    if os.path.isdir(SERVICES_DIR):
        for name in sorted(os.listdir(SERVICES_DIR)):
            if name.endswith('.py') and name != PACKAGE_FILE:
                errors.append('%s es un servicio de dominio suelto — va dentro de la carpeta de '
                              'su tema, como accounts/ o transactions/'
                              % os.path.join(SERVICES_DIR, name))
    if os.path.isdir(DOMAIN_DIR):
        for name in sorted(os.listdir(DOMAIN_DIR)):
            if name.endswith('.py') and name != PACKAGE_FILE and name not in DOMAIN_LOOSE_FILES:
                errors.append('%s está suelto en domain/ — una regla que no es de una sola '
                              'entidad es un servicio de dominio y va en services/, en la '
                              'carpeta de su tema (docs/02-arquitectura.md, 2.3)'
                              % os.path.join(DOMAIN_DIR, name))
    backend_app = os.path.join(BACKEND_DIR, 'app')
    if os.path.isdir(backend_app):
        for path in walk(backend_app, ('.py',)):
            tree = parsed(path)
            if tree is None:
                continue
            repositories = [node for node in tree.body if isinstance(node, ast.ClassDef)
                            and REPOSITORY_CLASS.match(node.name)]
            if repositories and not inside(path, REPOSITORIES_DIR):
                errors.append('%s:%d define %s fuera de %s — cada repositorio va en su archivo '
                              'ahí' % (path, repositories[0].lineno, repositories[0].name,
                                       REPOSITORIES_DIR))
            elif len(repositories) > 1:
                errors.append('%s:%d define %d repositorios — va uno por archivo, que se '
                              'corresponde con su puerto'
                              % (path, repositories[1].lineno, len(repositories)))


def check_general_names():
    """Regla 7: ningún archivo se llama utils, helpers o parecido. Un nombre así no dice qué
    hay adentro, y termina juntando funciones que no tienen nada que ver entre sí."""
    for root in GENERAL_NAME_ROOTS:
        if not os.path.isdir(root):
            continue
        for path in walk(root, GENERAL_NAME_EXTENSIONS):
            if any(inside(path, exempt) for exempt in GENERAL_NAME_EXEMPT):
                continue
            stem = os.path.basename(path).split('.')[0]
            if stem in GENERAL_NAMES:
                errors.append('%s tiene un nombre general — el nombre dice qué hay adentro, '
                              'como local_date.py o class-names.ts (AGENTS.md § 3)' % path)


def documented_folders():
    """Las carpetas del árbol de docs/02-arquitectura.md, como rutas desde la raíz."""
    text = read(ARCHITECTURE_DOC)
    start = text.find(TREE_SECTION)
    if start < 0:
        return None
    opening = text.find(TREE_FENCE, start)
    body_start = text.find('\n', opening) + 1
    body = text[body_start:text.find(TREE_FENCE, body_start)]
    folders = set()
    stack = []
    for line in body.splitlines():
        content = line.lstrip(' ')
        if not content.startswith(TREE_FOLDER_MARK):
            continue
        depth = (len(line) - len(content)) // TREE_INDENT
        name = content.split()[0].strip(TREE_FOLDER_MARK)
        del stack[depth:]
        stack.append(name)
        # A line like /components/ui names a folder and the one inside it.
        parts = os.path.join(*stack).split(TREE_FOLDER_MARK)
        for end in range(1, len(parts) + 1):
            folders.add(os.path.join(*parts[:end]))
    return folders


def check_documented_tree():
    """Regla 8: el árbol de la especificación nombra cada carpeta del código. Si el árbol lista
    las subcarpetas de una carpeta, tienen que estar todas; si no lista ninguna, como en
    use_cases/, la carpeta las organiza por su cuenta."""
    if not os.path.exists(ARCHITECTURE_DOC):
        return
    documented = documented_folders()
    if documented is None:
        errors.append('%s no tiene el árbol de carpetas de la sección 2.3' % ARCHITECTURE_DOC)
        return
    with_children = {os.path.dirname(folder) for folder in documented}
    for root in TREE_ROOTS:
        if not os.path.isdir(root):
            continue
        for base, dirs, _names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for d in dirs:
                folder = os.path.normpath(os.path.join(base, d))
                parent = os.path.dirname(folder)
                if folder not in documented and parent in with_children:
                    errors.append('%s no está en el árbol de %s — sumala, con qué va adentro'
                                  % (folder, ARCHITECTURE_DOC))


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
    backend_files = check_database_access()
    check_ai_frameworks()
    check_shared_utilities()
    check_inbound_adapters()
    check_file_places()
    check_general_names()
    check_documented_tree()
    frontend_files = check_frontend_isolation()

    print('Verificación de arquitectura')
    print('  archivos de dominio revisados  : %d' % domain_files)
    print('  resto del backend revisado     : %d' % backend_files)
    print('  archivos de frontend revisados : %d' % frontend_files)
    print('')

    for s in skipped:
        print('  OMITIDO  %s' % s)
    for w in warnings:
        print('  AVISO    %s' % w)
    for e in errors:
        print('  ERROR    %s' % e)

    if errors:
        print('\n%d error(es). Las reglas están en AGENTS.md, en '
              'docs/adr/0001-arquitectura-hexagonal.md y en '
              'docs/adr/0020-sin-framework-de-orquestacion-de-ia.md.' % len(errors))
        return 1
    if skipped and not domain_files and not backend_files and not frontend_files:
        print('Todavía no hay código que revisar. La verificación queda lista para cuando lo haya.')
    else:
        print('Sin errores%s.' % (' (%d aviso/s)' % len(warnings) if warnings else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
