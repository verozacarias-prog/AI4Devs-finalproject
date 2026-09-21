# 8. Convenciones de documentación

Cómo se escribe la documentación de este proyecto. No describe el producto: describe el
repositorio. Quien agregue un documento, un diagrama o una decisión de arquitectura en las
entregas siguientes tiene que respetar lo que está acá.

Las secciones 1 a 7 siguen la plantilla oficial del curso. Esta sección no forma parte de esa
plantilla: es un agregado del proyecto.

## 8.1. Idioma

> **Nota de idioma:** todo el desarrollo (código, nombres de tablas y campos, endpoints, payloads) va en **inglés**, de acá en adelante en todo el documento. El texto explicativo de esta entrega queda en español porque es el idioma de la documentación del curso; lo que el usuario final lee o le dice al asistente por WhatsApp también sigue en español, porque el público objetivo del producto es hispanohablante.

## 8.2. Diagramas

Los diagramas están escritos en **Mermaid** con sintaxis `flowchart` y no con la extensión `C4Context`/`C4Container`: el renderizador Mermaid de GitHub no soporta esa extensión, así que los diagramas no se verían en el repositorio. Usar `flowchart` con subgrafos es la práctica habitual para representar C4 en Markdown de GitHub y mantiene el diagrama versionado junto al código, sin depender de imágenes exportadas que quedan desactualizadas.

En consecuencia, para cualquier diagrama nuevo:

- Mermaid inline en el Markdown, nunca una imagen exportada.
- Sintaxis `flowchart` con subgrafos, aunque el diagrama sea conceptualmente C4.
- El diagrama de modelo de datos usa `erDiagram` y el de flujo conversacional `sequenceDiagram`,
  que sí están soportados por el renderizador de GitHub.

## 8.3. Nombres de archivo

- Kebab-case, sin acentos ni ñ: rompen en Linux y en CI.
- Sin espacios.
- Conservan su nombre canónico, porque las herramientas los buscan así: `README.md`,
  `CLAUDE.md`, `AGENTS.md`, `LICENSE`, `prompts.md`.

## 8.4. Estructura de `docs/`

- La serie numerada `01-` a `08-` está cerrada. No se crean archivos nuevos con número.
- Todo documento futuro va en `docs/` con nombre descriptivo y sin número.
- `README.md` es portada e índice: contiene la ficha del proyecto, una línea por documento y la
  descripción del flujo de trabajo con IA (contratos, commands y verificadores). Nunca el
  resumen de una sección: para eso está el documento enlazado.
- Todo archivo de `docs/` tiene que estar enlazado desde el `README.md`.

## 8.5. Decisiones de arquitectura

- Una decisión por archivo, en `docs/adr/`, numerados `NNNN-titulo-en-kebab-case.md`.
- Formato Michael Nygard: Contexto, Decisión, Consecuencias (positivas / negativas y costos
  asumidos) y Alternativas descartadas.
- Los ADR son inmutables. Si una decisión queda sin efecto, no se edita su archivo: se crea uno
  nuevo y el Estado del anterior pasa a `Reemplazada por NNNN`.

## 8.6. Un solo dueño por hecho

Ningún contenido puede estar completo en dos archivos. Cuando una regla o una explicación
pertenece a otro documento, en el origen queda un resumen de dos o tres líneas y un enlace
relativo, nunca el texto repetido.

Las reglas de negocio tienen un dueño único: [`reglas-de-dominio.md`](reglas-de-dominio.md).
Las referencias entre documentos se escriben como enlaces relativos con ancla, no como
"ver 3.2".

**Excepción: los ADR.** Un ADR tiene que poder leerse solo, años después, sin el resto del
repositorio a mano: es un registro congelado de por qué se decidió algo con la información que
había en ese momento. Si dependiera de un enlace a un documento vivo, su contenido cambiaría
cuando ese documento cambie, y la nota de inmutabilidad del pie sería falsa. Así que un ADR
**puede repetir** el texto que necesite para ser autosuficiente.

La excepción vale en una sola dirección. Lo que no puede pasar es lo contrario: **ningún
documento de `docs/` repite el contenido de un ADR**. Cuando una sección necesita mencionar una
decisión de arquitectura, enuncia qué se decidió y enlaza al ADR, que es el dueño del porqué.
Por ejemplo, [2.1](02-arquitectura.md#21-diagrama-de-arquitectura) nombra el patrón hexagonal
porque hace falta para leer el diagrama, y manda al
[ADR 0001](adr/0001-arquitectura-hexagonal.md) para el fundamento.

## 8.7. Verificación automática

Estas convenciones se verifican con un script, no a ojo:

```
python3 scripts/verify_docs.py
```

Chequea que los enlaces relativos resuelvan a un archivo y a un ancla que existen, que ningún
documento de `docs/` quede sin enlazar desde el `README.md`, que no haya texto duplicado entre
archivos, que los bloques de código y de Mermaid estén completos, que los nombres de archivo no
tengan acentos ni espacios, que la serie numerada no tenga huecos, que los ADR conserven su
plantilla y que los commands de `.claude/commands/` abran y cierren su frontmatter y declaren
`description`. Los avisos no frenan nada; los errores sí.

Un enlace a un directorio cubre su contenido: alcanza con que el `README.md` enlace
`docs/adr/` o `docs/features/` para que sus archivos no cuenten como huérfanos.

Para que corra solo antes de cada commit que toque documentación, una vez por clon:

```
git config core.hooksPath .githooks
```

El hook está versionado en `.githooks/pre-commit`. Se saltea con `git commit --no-verify`.

## 8.8. Qué tiene autoridad

Los archivos de `docs/` son la especificación del proyecto. `CLAUDE.md` es el contrato
operativo para asistentes de IA y resume algunas de estas reglas: cuando difieran, manda
`docs/`. El criterio completo está en [`CLAUDE.md`](../CLAUDE.md), sección 10.
