# Flujo de trabajo con IA

El proyecto se desarrolla con asistentes de IA y la configuración está versionada en el
repositorio, no en la máquina de quien lo escribe.

## Contratos

| Archivo | Qué contiene | Quién lo lee |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | El contrato completo: regla de dependencia hexagonal, siete invariantes de dominio, carpetas, convenciones, seguridad, base de datos y qué leer antes de qué | Cualquier asistente, sea cual sea la herramienta |
| `CLAUDE.md` | Enlace simbólico a `AGENTS.md`. Existe para que las herramientas que buscan ese nombre encuentren el contrato, no porque tenga contenido propio | Claude Code |
| [`docs/`](.) | La especificación del proyecto. Manda sobre los dos anteriores | Personas y asistentes |

## Skill

`domain-rules`, versionado en `.claude/skills/`. Es un skill y no un command porque conviene que
se dispare solo: la regla existe justamente porque es fácil saltársela, y depender de que la
persona se acuerde de invocarla derrota el propósito.

| Skill | Cuándo se activa | Qué hace |
|---|---|---|
| `domain-rules` | Al empezar cualquier trabajo que toque movimientos, cuentas, presupuestos, categorías o pendientes | Lee las reglas de dominio completas y devuelve qué grupos aplican, qué se resuelve solo, qué exige confirmación del usuario y qué invariante está en riesgo |

## Commands

Tres comandos versionados en `.claude/commands/`, que se invocan escribiendo `/nombre`. Son
verificaciones, y una verificación se corre cuando la persona decide, no cuando el modelo lo
infiere.

| Command | Cuándo | Qué hace |
|---|---|---|
| `/ui-states` | Al cerrar el corte vertical 2 | Verifica que la pantalla implemente y testee los cuatro estados, con foco en que *vacío* no esté resuelto como *error* |
| `/spec-drift` | Antes del último commit de un corte, y antes de cada entrega | Compara la especificación contra el código y reporta las diferencias **sin resolverlas** |
| `/security-audit` | Antes de cada entrega, no en cada pull request | Audita todo el backend contra el OWASP Top 10 web y el de aplicaciones LLM, de a un hallazgo por vez y por criticidad. No modifica nada. El cruce de diseño está en [seguridad de la capa de IA](seguridad-llm.md) |

## Verificación automática

Dos scripts que corren solos en el hook de pre-commit. Lo que se responde con sí o no va acá; lo
que requiere criterio es un command.

| Script | Qué valida |
|---|---|
| [`scripts/verify_docs.py`](../scripts/verify_docs.py) | Enlaces y anclas, documentos huérfanos, texto duplicado entre archivos, bloques Mermaid, nombres de archivo, plantilla de los ADR, y frontmatter de commands y skills |
| [`scripts/verify_architecture.py`](../scripts/verify_architecture.py) | Que `domain/` no importe infraestructura ni adaptadores ni tipe montos con `float`, que las librerías de acceso a la base solo aparezcan en los adaptadores de salida de PostgreSQL y pgvector, las migraciones y los tests, que ningún framework de orquestación de IA se importe fuera del adaptador de particionado, y que `frontend/` no alcance la base de datos. Tolerante mientras no exista el código, pero falla si existe `backend/` sin su dominio en la ruta esperada |

Los dos corren también en integración continua, junto con `markdownlint-cli2` y `lychee`, porque
el hook se saltea con `--no-verify` y depende de que cada clon lo active. Detalle en las
[convenciones de documentación](08-convenciones-de-documentacion.md#87-verificación-automática).

## Método de trabajo

Toda funcionalidad se parte en tres [cortes verticales](convenciones-de-desarrollo.md#1-cortes-verticales)
que atraviesan backend y frontend, y toda pantalla implementa
[cuatro estados](convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).
En el backend el test se escribe antes que el código, sobre casos que aprueba una persona
([ADR 0024](adr/0024-tests-primero-en-el-backend.md)). Cada corte se cierra contra el
[Definition of Done](07-pull-requests.md#definition-of-done).

## Agente revisor

Un subagente, versionado en `.claude/agents/`. Es un agente y no un command porque tiene que
partir de cero: corre en un contexto propio, sin la conversación en la que se escribió el
cambio ([ADR 0022](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md)).

| Agente | Cuándo | Qué hace |
|---|---|---|
| [`pr-reviewer`](../.claude/agents/pr-reviewer.md) | A mano, antes de pedir el merge de cada pull request | Revisa la regla hexagonal más allá del verificador, las reglas de dominio, que nada identificatorio llegue al proveedor ni a un registro, los tests, la documentación y la tabla de seguridad de la capa de IA. Entrega un informe para pegar en el pull request |

El revisor solo lee e informa. El merge lo hace siempre una persona, y un asistente hace commit
solo cuando una persona se lo pide.

## Hooks

El único hook es el de pre-commit, en [`.githooks/`](../.githooks/). Se activa con
`git config core.hooksPath .githooks`, una vez por clon. Cuando exista el código se suma un
segundo hook, del asistente y no de git, que corre los tests unitarios después de cada edición
en `backend/` ([ADR 0024](adr/0024-tests-primero-en-el-backend.md)). El revisor no corre en un hook, por lo
que explica el [ADR 0022](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md).
