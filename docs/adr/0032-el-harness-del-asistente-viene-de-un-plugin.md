# 0032 — Los hooks, los comandos y el agente revisor vienen del plugin fastapi-harness

- Estado: Aceptada
- Fecha: 2026-11-22

## Contexto

Los hooks del [ADR 0031](0031-hooks-del-asistente.md), los cuatro comandos y el agente revisor
del [ADR 0022](0022-revision-de-pull-requests-con-un-agente-del-repositorio.md) vivían en
`.claude/`, dentro de Platita. Cambiar uno pedía una rama de Platita con sus verificadores, el
revisor y el portal: mejorar el proceso frenaba al producto. Y lo aprendido no se podía usar en
otro proyecto Python y FastAPI.

## Decisión

1. **Vienen de un plugin de Claude Code,** `fastapi-harness`, del repositorio público
   `verozacarias-prog/fastapi-harness`, que es también su marketplace. `.claude/settings.json`
   lo declara y lo fija en un tag, hoy `v0.1.1`. Cada clon lo instala una vez:
   `claude plugin install fastapi-harness@fastapi-harness --scope project`.
2. **Qué controlan los hooks lo sigue decidiendo el ADR 0031;** este decide de dónde vienen.
   Lo que es solo de Platita está en `.claude/fastapi-harness.json`:
   - `frontend/e2e/compose.env` como archivo que se puede leer;
   - las carpetas de tests, `backend/tests/` y `frontend/e2e/`, y los `*.test.ts(x)` del
     dashboard;
   - la línea «Aprobado por» de `docs/features/*/spec.md`;
   - las migraciones de `backend/migrations/versions/`;
   - las dos suites del cierre del turno, la del backend y la del dashboard;
   - el despliegue con Render, que se rechaza, y el set de regresión con `--run`, que pregunta;
   - la sección de `AGENTS.md` que cada mensaje cita.
3. **La salida para explorar en local** pasa a llamarse `HARNESS_ALLOW_RED`, porque el plugin
   no conoce a Platita. Reemplaza a `PLATITA_PERMITIR_ROJO`.
4. **Los comandos y el agente traen el método;** lo propio de Platita va en
   `.claude/fastapi-harness/<nombre>.md`, versionado en este repositorio. Se invocan con el
   prefijo del plugin, como `/fastapi-harness:spec-drift` y el agente
   `fastapi-harness:pr-reviewer`.
5. **Los tests de los hooks** corren en el pipeline del plugin, donde cambian. El de Platita ya
   no los corre.
6. **Una versión nueva** se toma cambiando `ref` en `.claude/settings.json`, en un pull request,
   y corriendo `claude plugin update fastapi-harness@fastapi-harness`.

## Consecuencias

### Positivas

- El harness se cambia y se versiona sin abrir una rama de Platita.
- Sirve para otros proyectos Python y FastAPI, con su propia configuración.
- Platita toma una versión nueva cuando decide, y un hook roto no le llega hasta que cambia el
  tag.

### Negativas y costos asumidos

- Un clon sin el `plugin install` trabaja sin hooks, y solo `/plugin` lo muestra.
- El pipeline de Platita ya no prueba los hooks: confía en la versión que fija.
- Para saber qué hace un hook hay que leer dos lugares: el plugin y la configuración de Platita.
- Los hooks instalados viven fuera del repositorio, en la caché de plugins de Claude Code. El
  control de que cambiar los hooks pregunta no llega ahí: solo los protege el permiso de Claude
  Code para escribir fuera del directorio de trabajo.

## Alternativas descartadas

- **Enlaces simbólicos en `~/.claude`, desde un repositorio aparte:** sirve en una sola
  máquina; otro clon y el pipeline no lo ven.
- **Una copia dentro de Platita que un script actualiza:** cada versión nueva sería igual un
  pull request de Platita con todo el código del harness.
- **Dejarlo como estaba:** es lo que frenaba al producto.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
