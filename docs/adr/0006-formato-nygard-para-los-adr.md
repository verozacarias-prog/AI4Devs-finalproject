# 0006 — Se mantiene el formato Nygard y la numeración correlativa en los ADR

- Estado: Aceptada
- Fecha: 2026-09-21

## Contexto

El módulo 5 del máster AI4Devs propone, para el registro de decisiones de arquitectura, el
formato MADR (Markdown Any Decision Records), la herramienta `log4brains` y nombres de archivo
con fecha ISO, del tipo `YYYYMMDD-slug.md`. El argumento del módulo para la fecha es que evita
colisiones cuando varias personas abren registros en ramas paralelas, y el argumento para MADR
es que su sección de opciones consideradas es más fácil de rellenar por un agente de IA.

Cuando se evaluó la propuesta, el proyecto ya tenía cinco registros escritos en formato Michael
Nygard, numerados de forma correlativa, y una convención escrita que los declara inmutables. Esa
numeración no es decorativa: se usa como referencia corta en el contrato para asistentes, en la
hoja de ruta, en la lista de verificación de los pull requests, y en el propio mecanismo de
reemplazo, que dice que el registro superado cambia su estado a `Reemplazada por NNNN`. Además,
el verificador de documentación tiene las secciones de la plantilla escritas en el código.

El proyecto lo desarrolla una sola persona, en una rama por entrega.

## Decisión

Se mantiene el formato Michael Nygard con numeración correlativa `NNNN-` y se descartan MADR,
`log4brains` y los nombres con fecha. Razones:

- La única diferencia estructural real entre las dos plantillas es dónde se enumeran las opciones:
  MADR las lista antes de la decisión, Nygard las explica después como alternativas descartadas.
  Los registros existentes ya tienen esa sección, y además parten las consecuencias en positivas
  y en negativas con sus costos asumidos, que es más de lo que la otra plantilla pide.
- El problema que la fecha resuelve —dos registros creados a la vez en ramas distintas— no existe
  con una sola autora. A cambio, la fecha destruye la referencia corta, que sí se usa en cinco
  lugares del repositorio.
- `log4brains` es una herramienta de npm y exige adoptar su plantilla y sus nombres en bloque.
  Su aporte sustantivo es un sitio navegable de registros, y el proyecto ya resuelve eso con el
  portal de documentación, que genera el índice de registros por su cuenta.

## Consecuencias

### Positivas

- Los cinco registros existentes no se reescriben ni se renombran.
- La referencia corta del tipo «ADR 0001» sigue siendo válida en todo el repositorio.
- No entra una dependencia de npm cuyo único aporte se solapa con el portal de documentación.
- `scripts/verify_docs.py` sigue validando la plantilla sin cambios.

### Negativas y costos asumidos

- Si en el futuro el proyecto suma personas que trabajen en ramas paralelas, dos registros nuevos
  pueden pedir el mismo número y habrá que resolver la colisión a mano al integrar.
- No hay comando de andamiaje: cada registro se crea copiando la estructura de uno anterior.
- La plantilla es algo menos mecánica de rellenar por un agente de IA que la alternativa, porque
  el razonamiento vive en la prosa y no en una lista de opciones con ventajas e inconvenientes.

## Alternativas descartadas

- **Migrar a MADR conservando la numeración:** se quedaría con lo único que la otra plantilla
  aporta sin perder la referencia corta, pero obliga a reescribir cinco registros declarados
  inmutables y a tocar el verificador, a cambio de mover de lugar una sección que ya existe.
- **Adoptar `log4brains` completo:** renombrar los cinco archivos, reescribirlos, actualizar la
  convención, los enlaces del índice y el verificador. Descartado por el costo y porque rompe la
  inmutabilidad declarada, sin resolver ningún problema que el proyecto tenga hoy.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
