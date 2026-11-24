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
push ni merge, ni gaste en el modelo real, sin que una persona lo pida.

El [ADR 0024](0024-tests-primero-en-el-backend.md) había previsto un hook que corriera los tests
después de cada edición, solo para informar, porque en la fase en rojo los tests fallan a
propósito. Esa razón se resuelve mirando qué cambió: si lo único sin commitear son tests, es la
fase en rojo.

Los hooks se adaptaron del SDD Harness Kit (`github.com/DisTinta/sdd-harness-kit`, licencia MIT),
que trae diez. Se tomaron cuatro: los demás repiten lo que ya hace el pre-commit o dependen de
OpenSpec, que Platita no usa.

## Decisión

1. **Cuatro hooks de Claude Code.** De dónde vienen y dónde se configuran para Platita lo
   decide el [ADR 0032](0032-el-harness-del-asistente-viene-de-un-plugin.md); este decide qué
   reglas controlan. Cómo reconoce cada hook una acción (qué comandos, qué banderas, qué formas
   de escribirlos) es del harness y está en su documentación: este ADR no lo repite, para que una
   versión nueva del harness no lo cambie.
2. **Secretos** ([`AGENTS.md` § 7](../../AGENTS.md#7-seguridad)). Ningún archivo de entorno,
   clave ni credencial entra en el contexto del asistente, con ninguna herramienta, ni se edita.
   Se pueden leer `.env.example` y `frontend/e2e/compose.env`, que están versionados y no tienen
   secretos.
3. **Tests, especificación y migraciones** ([§ 8](../../AGENTS.md#8-base-de-datos) y
   [§ 13](../../AGENTS.md#13-método-de-trabajo)).
   - Sumar un caso a un test existente es libre: es la fase en rojo. Cambiar, borrar o
     deshabilitar algo de uno pregunta.
   - El asistente no puede completar la línea «Aprobado por» de un `spec.md`.
   - Editar una migración que ya está en git pregunta.
   - Cambiar los hooks o su configuración pregunta, incluidos `.claude/settings.json` y
     `.claude/fastapi-harness.json`, que son de Platita.
4. **Cierre del turno** ([§ 13](../../AGENTS.md#13-método-de-trabajo)). Al terminar cada turno
   corren los tests unitarios de la mitad que cambió: el backend, si cambió `backend/app/` o
   `backend/tests/`, y el dashboard, si cambió `frontend/src/`. En rojo, el turno no se cierra.
   Una mitad cuyos únicos cambios son tests es la fase en rojo, y pasa. Si a una mitad le falta
   con qué correr, `backend/.venv` o `frontend/node_modules`, el turno cierra con un aviso.
   Reemplaza el punto 8 del ADR 0024.
5. **Comandos** ([§ 9](../../AGENTS.md#9-librerías), [§ 11](../../AGENTS.md#11-comandos-de-verificación)
   y [§ 13](../../AGENTS.md#13-método-de-trabajo)).
   - Se rechazan el borrado recursivo, borrar un disco, abrir permisos a todos, el push
     forzado, reescribir la historia, saltear el pre-commit, el merge, operar contra
     `production` y desplegar.
   - Preguntan el push, descartar trabajo local, el set de regresión del prompt con `--run` y
     la instalación de un paquete.
6. **Una salida para explorar en local:** una variable en el `env` de
   `.claude/settings.local.json` apaga el control del cierre del turno. Nunca dentro de una
   entrega. Su nombre lo dice el ADR 0032.
7. **Los hooks tienen sus propios tests,** en el repositorio de donde vienen, que corren en su
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
- Cada push pide una confirmación. El commit no: queda en la máquina y se deshace fácil.
- **Hasta dónde llegan.** Los hooks frenan lo que un asistente haría en el curso normal del
  trabajo, no lo que se arma para esquivarlos. Miran el texto del comando o de la edición, no lo
  que hace, así que a veces frenan de más y a veces dejan pasar: un secreto leído por un
  programa que lo abre por su cuenta, o un test anulado con lógica y no con `skip`. Algunos de
  esos límites están en la documentación del harness. Para eso están el agente revisor, que lee el
  cambio entero, y la persona. Los hooks no los reemplazan.
- Si el asistente no logra el verde, el turno puede cerrar en rojo con un aviso, para no dejarlo
  en un bucle con un test que no sabe arreglar.
- Si a los hooks les falta lo que necesitan para correr, se apagan solos en lugar de romper la
  sesión: el control se pierde sin aviso. Lo mismo pasa con el cierre del turno si los tests
  tardan más que su límite de tiempo.
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
