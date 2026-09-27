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

Dos comandos versionados en `.claude/commands/`, que se invocan escribiendo `/nombre`. Son
verificaciones, y una verificación se corre cuando la persona decide, no cuando el modelo lo
infiere.

| Command | Cuándo | Qué hace |
|---|---|---|
| `/ui-states` | Al cerrar el corte vertical 2 | Verifica que la pantalla implemente y testee los cuatro estados, con foco en que *vacío* no esté resuelto como *error* |
| `/spec-drift` | Antes del último commit de un corte, y antes de cada entrega | Compara la especificación contra el código y reporta las diferencias **sin resolverlas** |

## Verificación automática

Dos scripts que corren solos en el hook de pre-commit. Lo que se responde con sí o no va acá; lo
que requiere criterio es un command.

| Script | Qué valida |
|---|---|
| [`scripts/verify_docs.py`](../scripts/verify_docs.py) | Enlaces y anclas, documentos huérfanos, texto duplicado entre archivos, bloques Mermaid, nombres de archivo, plantilla de los ADR, y frontmatter de commands y skills |
| [`scripts/verify_architecture.py`](../scripts/verify_architecture.py) | Que `domain/` no importe infraestructura ni adaptadores ni tipe montos con `float`, que las librerías de acceso a la base solo aparezcan en los adaptadores de salida de PostgreSQL y pgvector, las migraciones y los tests, y que `frontend/` no alcance la base de datos. Tolerante mientras no exista el código, pero falla si existe `backend/` sin su dominio en la ruta esperada |

Los dos corren también en integración continua, junto con `markdownlint-cli2` y `lychee`, porque
el hook se saltea con `--no-verify` y depende de que cada clon lo active. Detalle en las
[convenciones de documentación](08-convenciones-de-documentacion.md#87-verificación-automática).

## Método de trabajo

Toda funcionalidad se parte en tres [cortes verticales](convenciones-de-desarrollo.md#1-cortes-verticales)
que atraviesan backend y frontend, y toda pantalla implementa
[cuatro estados](convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).
Cada corte se cierra contra el [Definition of Done](07-pull-requests.md#definition-of-done).

## Hooks y subagentes

El único hook es el de pre-commit, en [`.githooks/`](../.githooks/). Se activa con
`git config core.hooksPath .githooks`, una vez por clon.

No hay subagentes definidos todavía. Queda como decisión abierta en la
[hoja de ruta](hoja-de-ruta.md).
