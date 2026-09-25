# 0007 — AGENTS.md como fuente única y CLAUDE.md como enlace simbólico

- Estado: Aceptada
- Fecha: 2026-09-21

## Contexto

El repositorio tenía dos contratos para asistentes de IA en archivos separados. Uno corto, con
la regla de dependencia hexagonal y las siete invariantes de dominio, pensado para que cualquier
herramienta lo lea entero. Otro largo, con el mapa de carpetas, las convenciones de código, la
seguridad, la base de datos y el procedimiento ante divergencias entre especificación y código.
El corto declaraba ser breve a propósito y el largo lo nombraba como dueño de las reglas que
resumía, de modo que la duplicación estaba resuelta por la convención de un solo dueño por hecho.

El módulo 5 del máster AI4Devs propone una fuente única con un enlace simbólico, para que
cualquier herramienta encuentre el contrato bajo el nombre que busca sin que existan dos textos
que puedan desincronizarse.

Las herramientas de IA buscan nombres de archivo distintos: unas leen `AGENTS.md` y otras
`CLAUDE.md`. Mantener dos archivos obliga a recordar cuál es el dueño de cada regla cada vez que
una cambia.

## Decisión

`AGENTS.md` pasa a contener el contrato completo y `CLAUDE.md` pasa a ser un enlace simbólico a
él, versionado como tal en git con modo `120000`. La numeración de secciones del contrato largo
se conserva intacta, porque se cita por número desde la hoja de ruta, la lista de verificación de
los pull requests, el command `/spec-drift` y los comentarios de `verify_architecture.py`.

Las dos secciones que antes delegaban en el archivo corto —la regla de dependencia hexagonal y
las invariantes de dominio— pasan a contener el texto completo, y una nota al principio del
archivo señala cuáles son las dos que hay que leer sí o sí.

## Consecuencias

### Positivas

- Existe un solo texto: la desincronización entre los dos contratos deja de ser posible.
- Cualquier herramienta encuentra el contrato bajo el nombre que busca.
- Las referencias por número de sección siguen siendo válidas sin tocarlas.

### Negativas y costos asumidos

- Se pierde la propiedad que hacía útil al archivo corto, que era ser corto. Un asistente que lo
  lea entero recibe ahora mucho más contexto del mínimo, y la nota inicial es un paliativo, no un
  sustituto.
- GitHub no renderiza un archivo Markdown que es un enlace simbólico: muestra el puntero. Por eso
  ningún enlace de la documentación puede apuntar al nombre enlazado, y esa es una regla nueva que
  hay que recordar al escribir documentación.
- `scripts/verify_docs.py` necesitó un parche para excluir enlaces simbólicos del corpus. Sin él,
  el mismo contenido entraba dos veces y la comprobación de texto duplicado cancelaba cada commit.
- Los enlaces simbólicos dependen de la configuración `core.symlinks` de git, que no está activa
  por defecto en todas las plataformas. En un clon donde no lo esté, el archivo enlazado aparece
  como un archivo de texto con la ruta adentro.
- Obligó a corregir un enlace dentro del [ADR 0005](0005-python-fastapi-en-vez-de-go.md), que era
  inmutable, y por lo tanto a escribir una excepción de mantenimiento en la convención.

## Alternativas descartadas

- **Dejar los dos archivos separados:** era la opción recomendada por el análisis previo, porque
  las dos capas eran deliberadas y la duplicación ya estaba resuelta nombrando un dueño por regla.
  Descartada por decisión de la autora, que priorizó tener una sola fuente por encima de conservar
  un contrato mínimo que se lea entero.
- **Duplicar el contenido en los dos archivos sin enlace simbólico:** resuelve la compatibilidad
  de nombres y no depende de `core.symlinks`, pero es exactamente la desincronización que se
  quería evitar, y contradice la convención de un solo dueño por hecho.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
