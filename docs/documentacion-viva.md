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

`docs/` es la fuente. Todo lo demás se deriva de ella y está en `.gitignore`:

```text
docs/  ──┬──▶  GitHub lo renderiza directamente, incluidos los diagramas Mermaid
         │
         └──▶  site/scripts/sync-docs.mjs
                 ├──▶  site/src/content/docs/   (generado, no versionado)
                 ├──▶  site/public/llms-full.txt (generado, no versionado)
                 └──▶  llms.txt                  (generado y versionado)
```

`docs/` no se modifica para alimentar al portal: el script agrega el frontmatter que Starlight
exige, reescribe los enlaces y extrae los diagramas. El fundamento y los problemas concretos que
resuelve están en el [ADR 0008](adr/0008-astro-starlight-como-portal.md).

`llms.txt` está versionado, a diferencia de los otros dos, porque un agente que clona el
repositorio no ve el portal. Por eso la integración continua falla si quedó desfasado de `docs/`.

## 3. Las tres barreras

Cada cambio pasa por tres controles, de más cerca a más lejos de quien escribe:

| Cuándo | Qué corre | Se saltea |
|---|---|---|
| Antes de cada commit | Los dos verificadores propios, vía `.githooks/pre-commit` | Sí, con `--no-verify` |
| En cada pull request | Los dos verificadores, `markdownlint-cli2`, `lychee` y la construcción del portal | No |
| Todos los lunes | `lychee`, porque un enlace externo se rompe sin que nadie toque nada | No |

El detalle de qué valida cada herramienta está en
[8.7](08-convenciones-de-documentacion.md#87-verificación-automática), y por qué son esas y no
otras, en el [ADR 0009](adr/0009-validacion-de-documentacion-en-ci.md).

## 4. Qué hace la IA y qué no

La IA redacta borradores: transcribe una decisión ya tomada al formato de un ADR, propone un
diagrama desde la estructura del código, o pasa una limpieza de formato. Lo que no hace es decidir
qué merece documentarse, ni dar por buena la semántica de lo que generó.

Cuando la especificación y el código difieren, un asistente no elige un lado: reporta la
divergencia. El procedimiento completo está en [AGENTS.md](../AGENTS.md) sección 10, y el command
[`/spec-drift`](../.claude/commands/spec-drift.md) existe para correrlo antes de cada entrega.

## 5. Trabajar con el portal

```sh
cd site
npm install          # una vez
npm run sync         # regenera el contenido desde docs/
npm run dev          # servidor local
npm run build        # construye, y regenera llms.txt
```

El portal se publica solo en cada integración a la rama principal, con
`.github/workflows/docs.yml`. Requiere que GitHub Pages esté configurado en el repositorio con
origen «GitHub Actions».

Si se agrega un documento a `docs/`, hay que sumarlo a la barra lateral en `site/astro.config.mjs`
salvo que vaya dentro de `adr/` o `features/`, que se indexan solos.
