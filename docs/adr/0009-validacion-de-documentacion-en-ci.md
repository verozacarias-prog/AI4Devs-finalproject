# 0009 — Validación de documentación en integración continua

- Estado: Aceptada
- Fecha: 2026-09-21

## Contexto

El proyecto ya tenía dos verificadores propios, `scripts/verify_docs.py` y
`scripts/verify_architecture.py`, que corrían en un gancho de pre-commit. Ese gancho tiene dos
agujeros: hay que activarlo a mano en cada clon con `git config core.hooksPath`, y se saltea con
`git commit --no-verify`. El repositorio no tenía ningún flujo de integración continua.

Además, el verificador propio salta explícitamente los enlaces que empiezan por `http`, así que
los enlaces externos nunca se comprobaban.

El módulo 5 del máster AI4Devs propone tres herramientas para esta capa: `markdownlint` para el
formato, `lychee` para los enlaces y `Vale` para el estilo de la prosa.

## Decisión

Se agrega el flujo `.github/workflows/docs-quality.yml`, que corre en cada pull request, en cada
integración a la rama principal, y todos los lunes. Repite los dos verificadores propios y suma
dos herramientas:

- `lychee`, para los enlaces externos. Cubre exactamente el hueco que el verificador propio deja
  abierto a propósito. Corre además de forma periódica, porque un enlace externo se rompe sin que
  nadie toque la documentación.
- `markdownlint-cli2`, para el formato del Markdown: listas rodeadas de líneas en blanco, bloques
  de código con lenguaje declarado, sangrías consistentes.

`Vale` se descarta. Sus estilos listos para usar están escritos para prosa en inglés: sus reglas
son listas de palabras inglesas y detección de voz pasiva en inglés. La documentación de este
proyecto está toda en español, así que habría que escribir las reglas desde cero.

Los registros —`prompts.md` y los archivos `conversacion-*`— quedan exentos de las dos
herramientas nuevas. Citan texto y direcciones ajenas por definición, que es el mismo criterio por
el que el verificador propio ya los excluye de la comprobación de texto duplicado.

## Consecuencias

### Positivas

- Las comprobaciones dejan de depender de que cada clon active el gancho o de que nadie lo saltee.
- Los enlaces externos se comprueban por primera vez, y de forma periódica.
- El flujo también construye el portal, así que una documentación que rompa la construcción no
  llega a la rama principal.

### Negativas y costos asumidos

- Hubo que pasar una limpieza de formato sobre la documentación existente. De ciento cuarenta
  hallazgos iniciales, ciento tres eran de una sola regla cosmética sobre el espaciado de las
  tablas, que quedó desactivada.
- Dos reglas más quedan desactivadas porque chocan con la plantilla oficial del curso, que salta
  de encabezado de nivel uno a nivel tres y usa negritas donde iría un encabezado. La plantilla
  manda sobre el estilo del linter.
- Las herramientas nuevas se configuran en archivos propios en la raíz, que se suman a los que ya
  había.
- La comprobación de enlaces externos puede fallar por causas ajenas al proyecto, como un servidor
  caído o un límite de peticiones.

## Alternativas descartadas

- **Llevar a integración continua solo los dos verificadores propios:** es lo mínimo para cerrar
  el agujero del gancho, pero deja los enlaces externos sin comprobar, que era el hueco concreto y
  demostrable.
- **Incluir `Vale`:** descartado por el idioma, según lo explicado arriba.
- **Reemplazar los verificadores propios por las herramientas del módulo:** las herramientas
  generales no conocen las convenciones de este repositorio, como el dueño único por hecho, la
  plantilla de las decisiones de arquitectura o el frontmatter de los skills.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
