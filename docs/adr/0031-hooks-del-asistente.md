# 0031 — Cuatro reglas del asistente las controlan hooks de Claude Code

- Estado: Aceptada
- Fecha: 2026-11-19

## Contexto

Las reglas que un asistente tiene que respetar están en [`AGENTS.md`](../../AGENTS.md). Las que
se responden con sí o no ya tienen un control con código, pero llega tarde: el hook de
pre-commit corre al commitear y el pipeline al abrir el pull request
([ADR 0021](0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md)). Mientras el
asistente trabaja, lo único que sostiene esas reglas es que el modelo las lea y las cumpla.

Cuatro de ellas se pueden comprobar en el momento en que el asistente actúa, antes de que el
error quede escrito: que ningún secreto entre en su contexto, que no cambie un test ni la línea de
aprobación de una especificación, que no termine un turno con la suite en rojo, y que no haga
commit, push ni merge, ni gaste en el modelo real, sin que una persona lo pida.

El [ADR 0024](0024-tests-primero-en-el-backend.md) había previsto un hook que corriera los tests
después de cada edición, solo para informar, porque en la fase en rojo los tests fallan a
propósito. Esa razón se resuelve mirando qué cambió: si lo único sin commitear son tests, es la
fase en rojo.

Los hooks se adaptaron del SDD Harness Kit (`github.com/DisTinta/sdd-harness-kit`, licencia MIT),
que trae diez. Se tomaron cuatro: los demás repiten lo que ya hace el pre-commit o dependen de
OpenSpec, que Platita no usa.

## Decisión

1. **Cuatro hooks de Claude Code, versionados en `.claude/hooks/`** y registrados en
   `.claude/settings.json`, para que valgan en cualquier clon. Son scripts de bash que leen con
   `jq` lo que Claude Code les pasa.
2. **Secretos.** Ningún archivo de entorno, clave ni credencial se lee, ni con la herramienta de
   lectura ni por la shell: `.env` y sus variantes, `credentials*`, `id_rsa`, `id_ed25519`,
   `*.pem`, `*.key` y `service-account*.json`. Se pueden leer `.env.example` y
   `frontend/e2e/compose.env`, que están versionados y no tienen secretos.
3. **Tests, especificación y migraciones.**
   - Sumar líneas enteras a un test existente es libre, con cualquier herramienta. Cambiar o
     borrar algo de uno pregunta, y también agregar texto dentro de una línea, como `or True`
     al final de una aserción.
   - Deshabilitar un test pregunta: `skip`, `xfail`, `.only` y sus variantes, incluidos
     `pytestmark` y `@mark.skip`.
   - Borrar o cambiar un test desde la shell también pregunta: `rm`, `mv`, `sed -i`, una
     redirección con `>`, y `git checkout`, `restore` o `rm` sobre un test.
   - Cambiar los hooks o su configuración, `.claude/hooks/` y `.claude/settings*.json`,
     pregunta.
   - El asistente no puede completar la línea «Aprobado por» de un `spec.md`.
   - Editar una migración que ya está en git pregunta.
   - Los archivos de entorno no se editan, ni una ruta con `..`.
4. **Cierre del turno.** Al terminar cada turno corren los tests unitarios del backend, si
   cambió `backend/app/` o `backend/tests/`, y los del dashboard, si cambió `frontend/src/`. Se
   cuentan los archivos nuevos todavía sin agregar. Una mitad cuyos únicos cambios son tests es
   la fase en rojo, y pasa. Reemplaza el punto 8 del ADR 0024.
   - Si alguno falla, el turno no se cierra y el asistente recibe el fallo.
   - Si en el segundo intento sigue fallando, el turno cierra, pero con un aviso a la persona:
     bloquear otra vez podría dejar al asistente en un bucle con un test que no sabe arreglar.
   - Si a una mitad le falta con qué correr, `backend/.venv` o `frontend/node_modules`, el
     turno cierra con un aviso.
5. **Comandos.**
   - Se rechazan el borrado recursivo (`rm -r`), `mkfs`, `dd`, `chmod 777`, el push forzado
     (`--force`, `--force-with-lease`, `-f` o `+rama`), `git filter-branch`,
     `git commit --no-verify` (o `-n`), el merge (`gh pr merge` o `gh api …/merge`) y desplegar.
     Las banderas cortas cuentan también juntas, como `-fu` o `-nm`. También operar contra
     `production`, que se reconoce como un entorno puesto en `production` fuera de las comillas
     (`APP_ENV=production`, `--env production`), no como la palabra suelta.
   - Preguntan `git commit`, `git push`, `git reset --hard`, `git clean -f`, el set de regresión
     del prompt con `--run` y la instalación de un paquete.
   - Git se lee sin el texto entre comillas, para que el mensaje de un commit no se confunda con
     una bandera, y sin sus opciones globales, para que `git -C <dir> push` sea un push.
6. **Una salida para explorar en local:** `PLATITA_PERMITIR_ROJO=1`, en el `env` de
   `.claude/settings.local.json`, apaga el control del cierre del turno. Nunca dentro de una
   entrega.
7. **Los hooks tienen sus propios tests,** en `scripts/test_assistant_hooks.sh`, que corre en el
   pipeline. Cada caso le pasa al hook lo que mandaría Claude Code, contra un repositorio
   descartable.

## Consecuencias

### Positivas

- Cuatro reglas de `AGENTS.md` dejan de depender de que el modelo las recuerde.
- El error se frena antes de escribirse, no al commitear ni en el pull request.
- La fase en rojo del ADR 0024 sigue funcionando, y el resto de los turnos no cierra en rojo
  sin que la persona se entere.
- El dashboard entra en el control, que el ADR 0024 dejaba afuera.

### Negativas y costos asumidos

- Cerrar un turno que tocó código tarda unos 6 s si cambió el backend, y unos 25 s si cambiaron
  las dos mitades.
- Cada commit y cada push piden una confirmación.
- **Hasta dónde llegan.** Los hooks frenan lo que un asistente haría en el curso normal del
  trabajo, no lo que se arma para esquivarlos. Miran el texto del comando o de la edición, no lo
  que hace, y no hay forma de que esa lista sea completa:
  - Un `rm -rf` dentro del mensaje de un commit se rechaza igual.
  - Un `NODE_ENV=production` se rechaza aunque no opere contra el entorno `production`.
  - Pasan sin preguntar los secretos leídos con un comando que no está en la lista, como
    `python -c` o `git show HEAD:.env`, y un comodín como `cat .e*`.
  - Un push con `--mirror`, `--delete` o `:rama` pregunta como cualquier push, y cambiar
    `.claude/settings.json` desde la shell no pregunta.
  - También pasa un test anulado con lógica y no con `skip`: un `return` al principio, una
    función redefinida con el mismo nombre, o un `conftest.py` que vacía la colección.
  - Lo mismo vale para la línea «Aprobado por» escrita con otro formato o desde la shell.

  Para todo eso están el agente revisor, que lee el cambio entero, y la persona. Los hooks no
  los reemplazan.
- El cierre del turno frena una sola vez. Si el asistente no logra el verde, el turno cierra en
  rojo y lo que queda es el aviso.
- Sin `jq`, los hooks se apagan solos en lugar de romper la sesión: el control se pierde sin aviso.
  Lo mismo pasa con el cierre del turno si los tests tardan más de los 300 s de su límite.
- Solo valen en Claude Code. Otra herramienta sigue leyendo `AGENTS.md`, sin ningún control.

## Alternativas descartadas

- **Correr los tests después de cada edición, solo para informar, como preveía el ADR 0024:**
  avisa antes, pero corre en cada edición y no impide terminar el turno en rojo.
- **Dejar todo en el pre-commit y en el pipeline:** no suma nada, pero el error se ve recién
  cuando ya está escrito, y el pre-commit se saltea con `--no-verify`.
- **Instalar el SDD Harness Kit completo:** trae más controles, pero impone el inglés en la
  documentación, otro nombre de ramas, OpenSpec y sus propios `AGENTS.md` y `CLAUDE.md`, que
  chocan con el [ADR 0007](0007-agents-md-como-fuente-unica.md).

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
