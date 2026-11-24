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

Cuatro comandos, nombrados acá por su rol: cómo se invoca cada uno está en el
[apartado del plugin](#plugin). Lo propio de Platita lo leen de `AGENTS.md` y de los documentos que
`AGENTS.md` les indica. Tres
son verificaciones, y una verificación se corre cuando la persona decide, no cuando el modelo lo
infiere. El cuarto, `/ticket`, recorre el flujo de un corte y se detiene en cada punto que decide
una persona.

| Command | Cuándo | Qué hace |
|---|---|---|
| `/ticket` | Al empezar un corte o una tarea, con sus issues | Recorre los pasos de [cómo colaborar](como-colaborar.md#1-incluir-un-cambio), de la issue a la descripción del pull request. Se detiene para que la persona apruebe los casos, pida cada revisión y el push, y pruebe a mano. El asistente hace el commit de cada paso, abre el pull request cuando la persona pide el push, y el merge lo hace ella |
| `/ui-states` | Al cerrar el corte vertical 2 | Verifica que la pantalla implemente y testee los cuatro estados, con foco en que *vacío* no esté resuelto como *error* |
| `/spec-drift` | En modo `corte`, antes del último commit de un corte; en modo `proyecto`, antes de cada entrega | Compara la especificación contra el código y reporta las diferencias **sin resolverlas**. El modo `proyecto` arma la lista de documentos desde `docs/` y dice cuáles no revisó. Al final propone una issue por hallazgo, y las crea solo si la persona las aprueba |
| `/security-audit` | Antes de cada entrega, no en cada pull request | Audita todo el backend contra el OWASP Top 10 web y el de aplicaciones LLM, de a un hallazgo por vez y por criticidad. No modifica nada. El cruce de diseño está en [seguridad de la capa de IA](seguridad-llm.md) |

## Verificación automática

Tres scripts que corren solos en el hook de pre-commit. Lo que se responde con sí o no va acá; lo
que requiere criterio es un command.

| Script | Qué valida |
|---|---|
| [`scripts/verify_docs.py`](../scripts/verify_docs.py) | Enlaces y anclas, documentos huérfanos, texto duplicado entre archivos, bloques Mermaid, nombres de archivo, plantilla de los ADR, y frontmatter de commands, skills y agentes |
| [`scripts/verify_architecture.py`](../scripts/verify_architecture.py) | Que `domain/` no importe infraestructura ni adaptadores ni tipe montos con `float`, que las librerías de acceso a la base solo aparezcan en los adaptadores de salida de PostgreSQL y pgvector, las migraciones y los tests, que ningún framework de orquestación de IA se importe fuera del adaptador de particionado, y que `frontend/` no alcance la base de datos. Tolerante mientras no exista el código, pero falla si existe `backend/` sin su dominio en la ruta esperada |
| [`scripts/verify_api_contract.py`](../scripts/verify_api_contract.py) | Que la referencia de la API, el contrato versionado que en `local` muestra `/docs`, esté completa, y que lo que el contrato declara esté en [`04-api.md`](04-api.md). Compara del contrato hacia la especificación, no al revés |

Los tres corren también en integración continua, junto con `markdownlint-cli2` y `lychee`, porque
el hook se saltea con `--no-verify` y depende de que cada clon lo active. Detalle en las
[convenciones de documentación](08-convenciones-de-documentacion.md#87-verificación-automática).

## Método de trabajo

Toda funcionalidad se parte en tres [cortes verticales](convenciones-de-desarrollo.md#1-cortes-verticales)
que atraviesan backend y frontend, y toda pantalla implementa
[cuatro estados](convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).
En el backend el test se escribe antes que el código, sobre casos que aprueba una persona
([ADR 0024](adr/0024-tests-primero-en-el-backend.md)). Cada corte se cierra contra el
[Definition of Done](07-pull-requests.md#definition-of-done).

## Despliegue

El asistente escribe la imagen, Docker Compose y el pipeline
([ADR 0021](adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md)), con los mismos
controles que el resto del código. Antes de cada entrega corre `/security-audit`, que audita el
backend contra las dos listas de OWASP. El despliegue del entorno `demo`, en la entrega final,
lo escribe el asistente y lo aprueba una persona: ningún asistente despliega ni hace merge.

## Agente revisor

Un subagente, que lee `AGENTS.md` completo; cómo se invoca está en el
[apartado del plugin](#plugin). Es un agente y no un command porque tiene que
partir de cero: corre en un contexto propio, sin la conversación en la que se escribió el
cambio ([ADR 0022](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md)).

| Agente | Cuándo | Qué hace |
|---|---|---|
| `pr-reviewer` | A mano, antes de pedir el merge de cada pull request | Revisa la regla hexagonal más allá del verificador, las reglas de dominio, que nada identificatorio llegue al proveedor ni a un registro, los tests y que en el backend hayan ido antes que el código, la documentación y la tabla de seguridad de la capa de IA. Entrega un informe para pegar en el pull request |

El revisor solo lee e informa. El merge lo hace siempre una persona, y un asistente hace push
solo cuando una persona se lo pide.

## Hooks

Hay dos tipos. El de git es el de pre-commit, en [`.githooks/`](../.githooks/), y se activa con
`git config core.hooksPath .githooks`, una vez por clon. Los del asistente son cuatro, y Claude
Code los corre solo: actúan en el momento en que el asistente lee, busca, edita, corre un
comando o termina un turno, antes de que el error quede escrito
([ADR 0031](adr/0031-hooks-del-asistente.md)). De dónde vienen y qué necesitan está en el
[apartado del plugin](#plugin).

| Control | Cuándo corre | Qué hace |
|---|---|---|
| Secretos | Antes de leer o buscar en un archivo | Rechaza `.env`, claves y credenciales. `.env.example` y `frontend/e2e/compose.env` se leen |
| Tests, especificación y migraciones | Antes de editar o escribir | Pregunta antes de cambiar, borrar o deshabilitar algo de un test existente, de editar una migración versionada y de tocar los hooks o su configuración. Rechaza completar la línea «Aprobado por» de un `spec.md` y editar un archivo de entorno. Sumar líneas enteras a un test es libre |
| Comandos | Antes de un comando | Rechaza `rm -r`, push forzado, reescribir la historia, `git commit --no-verify`, el merge, `production` y despliegues, y leer secretos por la shell. Pregunta antes de `git push`, salvo `--dry-run`, borrar o cambiar un test, descartar trabajo local, `evals.classification.run --run` y de instalar un paquete |
| Suite en verde | Al terminar el turno | Corre los tests unitarios del backend o del dashboard, solo la mitad que cambió. En rojo frena una vez, y si sigue en rojo cierra con un aviso. Si lo único que cambió en una mitad son tests, es la fase en rojo y pasa |

Para explorar en local con la suite en rojo, una variable en el `env` de
`.claude/settings.local.json` apaga el último; su nombre está en el
[apartado del plugin](#plugin). Nunca dentro de una entrega.

El revisor no corre en un hook, por lo que explica el
[ADR 0022](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md).

## Plugin

Dos plugins de Claude Code, habilitados en `.claude/settings.json` para que valgan en cualquier
clon y no solo en una máquina. Quien clona el repositorio los instala una vez, con
`/plugin install context7@claude-plugins-official` y
`claude plugin install fastapi-harness@fastapi-harness --scope project`.

| Plugin | Cuándo se usa | Qué hace |
|---|---|---|
| `fastapi-harness` | Siempre: los hooks actúan solos, y los comandos y el agente se invocan a mano | Trae los hooks, los comandos y el agente revisor de este documento, en la versión que fija `.claude/settings.json` ([ADR 0032](adr/0032-el-harness-del-asistente-viene-de-un-plugin.md)) |
| `context7` | Cuando el asistente va a usar una librería y la versión importa | Trae la documentación vigente de esa librería, por versión, en vez de confiar en lo que el modelo recuerda |

Este apartado y el ADR 0032 son los únicos lugares de la especificación que nombran el plugin
`fastapi-harness`, aparte del comando de instalación de
[cómo colaborar](como-colaborar.md). El resto nombra cada pieza por su rol, y esta tabla dice qué es cada rol en
el plugin:

| Rol en Platita | En `fastapi-harness` |
|---|---|
| `/ticket`, `/spec-drift`, `/ui-states`, `/security-audit` | `/fastapi-harness:ticket`, `/fastapi-harness:spec-drift`, `/fastapi-harness:ui-states`, `/fastapi-harness:security-audit` |
| El agente `pr-reviewer` | `fastapi-harness:pr-reviewer` |
| Los controles de secretos, tests, comandos y suite en verde | `block-secret-reads.sh`, `protect-tests-and-specs.sh`, `block-dangerous-bash.sh` y `verify-tests-on-stop.sh`. Necesitan `jq`; sin él se apagan. Sus casos los prueba el pipeline del plugin |
| La configuración para Platita | `.claude/fastapi-harness.json` |
| La salida para explorar en local con la suite en rojo | `HARNESS_ALLOW_RED=1` |

No es una verificación y no suma ninguna dependencia al código: es una consulta que hace el
asistente mientras escribe. La consulta sale del repositorio hacia `mcp.context7.com`, así que
lleva solo el nombre de la librería y la pregunta, nunca código del proyecto ni datos de un
usuario. Lo que vuelve es texto de un tercero: se lee como información, no como instrucciones.
