# Documentación viva

Cómo se mantiene sincronizada la documentación de este proyecto con el código que describe. No
repite las convenciones de escritura, que están en
[8. Convenciones de documentación](08-convenciones-de-documentacion.md), ni el fundamento de cada
decisión, que está en los ADR enlazados.

La idea es una sola: la documentación vive en el repositorio, viaja en el mismo commit que el
código que describe, y algo automático se queja cuando se desactualiza.

## 1. Las cuatro capas

| Capa | Dónde vive | Quién la lee |
|---|---|---|
| Especificación | `docs/`, y nada más ([AGENTS.md](../AGENTS.md) sección 10) | Personas y asistentes |
| Decisiones de arquitectura | [`docs/adr/`](adr/) | Quien se pregunte por qué el sistema es así |
| Contrato para asistentes | [`AGENTS.md`](../AGENTS.md), con `CLAUDE.md` como enlace simbólico | Cualquier herramienta de IA |
| Contexto para agentes | `llms.txt` en la raíz y en el portal | Agentes de IA externos |

La documentación de la API y la del código todavía no existen: se generan desde el código, y el
backend no está implementado. Ver la [hoja de ruta](hoja-de-ruta.md).

## 2. Una sola fuente

`docs/` es la fuente. Todo lo demás se deriva de ella y está en `.gitignore`, con una sola
excepción: `llms.txt`, que se genera igual que el resto pero **sí se versiona**, porque un agente
que clona el repositorio no ve el sitio publicado.

```text
docs/  ──┬──▶  GitHub lo renderiza directamente, incluidos los diagramas Mermaid
         │
         └──▶  site/scripts/sync-docs.mjs
                 ├──▶  site/src/content/docs/   (generado, no versionado)
                 ├──▶  site/public/llms-full.txt (generado, no versionado)
                 └──▶  llms.txt                  (generado y versionado)
```

`docs/` no se modifica para alimentar al portal: el script agrega el frontmatter que Starlight
exige, reescribe los enlaces y extrae los diagramas, que se renderizan en el cliente y se
verificaron sobre el sitio publicado. El fundamento y los problemas concretos que
resuelve están en el [ADR 0008](adr/0008-astro-starlight-como-portal.md).

`llms.txt` está versionado, a diferencia de los otros dos, porque un agente que clona el
repositorio no ve el portal. Por eso la integración continua falla si quedó desfasado de `docs/`.

## 3. Las tres barreras

Cada cambio pasa por tres controles, de más cerca a más lejos de quien escribe:

| Cuándo | Qué corre | Se saltea |
|---|---|---|
| Antes de cada commit | Los dos verificadores propios, vía `.githooks/pre-commit` | Sí, con `--no-verify` |
| En cada pull request | Los dos verificadores, `markdownlint-cli2`, `lychee`, la construcción del portal y `gitleaks`, que busca secretos | No |
| Todos los lunes | `lychee`, porque un enlace externo se rompe sin que nadie toque nada | No |

El detalle de qué valida cada herramienta está en
[8.7](08-convenciones-de-documentacion.md#87-verificación-automática), y por qué son esas y no
otras, en el [ADR 0009](adr/0009-validacion-de-documentacion-en-ci.md). Los controles del
código, que se suman con el primer commit de código, están en el
[ADR 0021](adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md).

## 4. Qué hace la IA y qué no

La IA redacta borradores: transcribe una decisión ya tomada al formato de un ADR, propone un
diagrama desde la estructura del código, o pasa una limpieza de formato. Lo que no hace es decidir
qué merece documentarse, ni dar por buena la semántica de lo que generó.

Cuando la especificación y el código difieren, un asistente no elige un lado: reporta la
divergencia. El procedimiento completo está en [AGENTS.md](../AGENTS.md) sección 10, y el command
[`/spec-drift`](../.claude/commands/spec-drift.md) existe para correrlo antes de cada entrega.

## 5. La documentación viaja en el commit del código

Un pull request que cambia un endpoint, el esquema de la base de datos o una regla de negocio
actualiza el documento que lo describe **en ese mismo pull request**, no después. Esa es la única
forma de que la documentación no se desactualice: si el cambio se aplaza, no ocurre.

La lista completa está en la sección Documentación del
[Definition of Done](07-pull-requests.md#definition-of-done). Hoy se verifica leyendo, con la
ayuda de `/spec-drift`. La parte que es binaria —comparar el contrato generado por FastAPI contra
[`04-api.md`](04-api.md)— se automatiza con `verify_api_contract.py` cuando exista la API, y está
en la [hoja de ruta](hoja-de-ruta.md).

## 6. Trabajar con el portal

```sh
cd site
npm install          # una vez
npm run sync         # regenera el contenido desde docs/
npm run dev          # servidor local
npm run build        # construye, y regenera llms.txt
```

El portal se publica solo, con `.github/workflows/docs.yml`, en cada integración a la rama de la
entrega en curso.

## 7. El modelo de ramas

Este repositorio es un fork del repositorio del curso, y se entrega tres veces. De ahí sale un
modelo de ramas con dos niveles:

```text
main
 └─ feature/entrega-2-VNZ               rama de la entrega: sale de main y vuelve a main
     ├─ hu3-c1-registro-de-gasto        un corte de una historia
     ├─ hu3-c2-registro-de-gasto
     └─ tarea-scaffold-y-docker         lo que no es una historia
```

- **`main` tiene las entregas cerradas.** Cada entrega se integra a `main` cuando se cierra, y
  la rama de la entrega siguiente sale de ahí.
- **La rama de la entrega no recibe commits directos.** Todo cambio entra por un pull request
  desde una rama corta, con los controles en verde. Así la rama de la entrega funciona siempre.
- **Una rama corta por corte vertical.** Una historia se parte en tres
  [cortes](convenciones-de-desarrollo.md#1-cortes-verticales), y cada uno es un pull request.
  La rama se llama `hu<N>-c<corte>-<tema>`. Lo que no resuelve una historia, como el scaffold o
  un arreglo, va en una rama `tarea-<tema>`.

Los pasos, uno por uno, están en el [README](../README.md#cómo-colaborar). Tres detalles de
GitHub condicionan el modelo y no son evidentes:

- **Las ramas cortas no empiezan con `feature/`.** El flujo que publica el portal corre con cada
  push a `main` y a `feature/entrega-*`. Una rama de trabajo con ese prefijo publicaría
  documentación que todavía no se integró. Los controles no lo necesitan: corren al abrir el
  pull request.
- **En un pull request contra otro repositorio, GitHub ejecuta los workflows del repositorio
  base**, no los de este. Por eso los pull requests de trabajo se abren dentro del fork, contra
  la rama de la entrega.
- **El portal se publica desde la rama por defecto.** El entorno `github-pages` acepta solo las
  ramas que tiene autorizadas, y Dependabot abre sus pull requests contra la rama por defecto.
  Al abrir una entrega hay que poner su rama como rama por defecto del fork, en
  `Settings → Branches`, y revisar que esté autorizada en `Settings → Environments →
  github-pages`.

Que los controles impidan un merge depende, además, de proteger la rama de la entrega con esos
controles como obligatorios ([ADR 0021](adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md)).

Si se agrega un documento a `docs/`, hay que sumarlo a la barra lateral en `site/astro.config.mjs`
salvo que vaya dentro de `adr/` o `features/`, que se indexan solos.
