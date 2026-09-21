# 0008 — Astro Starlight como portal de documentación

- Estado: Aceptada
- Fecha: 2026-09-21

## Contexto

La documentación del proyecto son archivos Markdown en `docs/`, que GitHub ya renderiza, incluidos
los diagramas Mermaid. El módulo 5 del máster AI4Devs propone consolidarla en un sitio estático
navegable, construido con Astro Starlight y publicado en GitHub Pages, con índice autogenerado de
decisiones de arquitectura y generación del archivo `llms.txt` para agentes de IA.

Cuando se evaluó la propuesta, el repositorio no tenía una sola línea de JavaScript ni un
`package.json`, y el stack del dashboard todavía no estaba decidido. El análisis previo recomendó
aplazar el portal hasta que existiera ese stack, porque hasta entonces la herramienta entra como
una dependencia huérfana. La autora decidió montarlo igual, priorizando tener la documentación
publicada y visible.

## Decisión

Se monta el portal con Astro Starlight en `site/`, publicado en GitHub Pages.

Vive en `site/` y no en `docs/site/` por una razón concreta: `markdown_files()`, en
`scripts/verify_docs.py`, recorre `docs/` de forma recursiva, así que cualquier archivo Markdown
ahí adentro entraría en la comprobación de texto duplicado y haría fallar el verificador contra
copias de sus propias fuentes. Además `docs/` es la especificación y no debe contener artefactos
generados.

`docs/` no se modifica para alimentar al portal. Un script, `site/scripts/sync-docs.mjs`, produce
la copia que Starlight necesita: le agrega el frontmatter con el título derivado del encabezado de
nivel uno, reescribe los enlaces y extrae los diagramas. Esa copia está en `.gitignore` y se
regenera en cada construcción. La fuente sigue siendo una sola.

Los diagramas se renderizan en el cliente. La alternativa de generarlos como imagen durante la
construcción obliga a instalar un navegador sin interfaz en integración continua, que es mucho
coste para un sitio de documentación.

## Consecuencias

### Positivas

- La documentación tiene una dirección propia, con buscador e índice de decisiones autogenerado.
- Los archivos `llms.txt` y `llms-full.txt` se generan solos desde las mismas fuentes.
- `docs/` sigue renderizando en GitHub exactamente igual que antes.

### Negativas y costos asumidos

- Entra un entorno de Node en un repositorio que no tenía JavaScript, antes de decidir el stack
  del dashboard. Si ese stack termina siendo otro, conviven dos conjuntos de dependencias.
- La documentación se publica en dos lugares y hay que sostener los enlaces relativos en los dos.
  Astro reescribe los enlaces sueltos pero no los que llevan ancla, y casi todas las referencias
  cruzadas de este proyecto llevan ancla, así que el script los reescribe por su cuenta.
- El renderizador de bloques de código de Starlight se queda con los diagramas y descarta la clase
  que el renderizador del cliente necesita, así que hay que extraerlos antes como HTML suelto.
- Los diagramas dependen de que el navegador del lector descargue la librería desde una red de
  distribución de contenidos. Sin conexión a esa red, se ven vacíos.
- El script de sincronización es código propio que hay que mantener cuando cambie Starlight.

## Alternativas descartadas

- **Aplazarlo hasta que exista el dashboard:** era la recomendación del análisis previo. El
  repositorio ya es navegable en GitHub, los diagramas se ven, y esperar habría evitado introducir
  Node antes de tiempo. Descartada por decisión de la autora.
- **Docusaurus:** más extendido, pero pesa más en la construcción y aporta funcionalidad que este
  proyecto no necesita.
- **`log4brains`:** publica un sitio solo de decisiones de arquitectura, no de la documentación
  entera, y exige adoptar una plantilla y unos nombres de archivo que el
  [ADR 0006](0006-formato-nygard-para-los-adr.md) descarta.
- **Agregar el frontmatter directamente a los archivos de `docs/`:** evitaría el script de
  sincronización, pero GitHub muestra el frontmatter como una tabla al principio de cada
  documento, y `docs/` dejaría de leerse bien en el repositorio, que es donde se trabaja.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
