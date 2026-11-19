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
   lectura ni por la shell. `.env.example` se puede leer.
3. **Tests, especificación y migraciones.**
   - Sumar a un test existente es libre; cambiar o borrar algo de uno pregunta.
   - El asistente no puede completar la línea «Aprobado por» de un `spec.md`.
   - Editar una migración que ya está en git pregunta.
   - Los archivos de entorno no se editan.
4. **Cierre del turno.** Al terminar cada turno corren los tests unitarios del backend, si
   cambió `backend/app/` o `backend/tests/`, y los del dashboard, si cambió `frontend/src/`. Se
   cuentan los archivos nuevos todavía sin agregar. Si alguno falla, el turno no se cierra. Una
   mitad cuyos únicos cambios son tests es la fase en rojo, y pasa. Reemplaza el punto 8 del
   ADR 0024.
5. **Comandos.**
   - Se rechazan los borrados masivos, el push forzado, `git commit --no-verify`, `gh pr merge`,
     operar contra `production` y desplegar.
   - Preguntan `git commit`, `git push`, el set de regresión del prompt con `--run` y la
     instalación de un paquete.
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
- La fase en rojo del ADR 0024 sigue funcionando, y el resto de los turnos no puede cerrar en rojo.
- El dashboard entra en el control, que el ADR 0024 dejaba afuera.

### Negativas y costos asumidos

- Cerrar un turno que tocó código tarda unos 6 s si cambió el backend, y unos 25 s si cambiaron
  las dos mitades.
- Cada commit y cada push piden una confirmación.
- Los hooks miran el texto del comando. Un `rm -rf` dentro del mensaje de un commit se rechaza
  igual, y un comando armado para esquivarlos puede pasar. No reemplazan la lectura de la persona.
- Sin `jq`, los hooks se apagan solos en lugar de romper la sesión: el control se pierde sin aviso.
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
