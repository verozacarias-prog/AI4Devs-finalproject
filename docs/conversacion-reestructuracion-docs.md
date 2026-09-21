# Conversación completa — reestructuración de la documentación

- **Fecha:** 2026-09-20
- **Herramienta:** Claude Code (CLI)
- **Modelo:** Claude Opus 5, contexto 1M (`claude-opus-5[1m]`)
- **Rama:** `feature/entrega-1-VNZ`
- **Commit resultante:** `6ddbe05`

Adjunto de apoyo a [`prompts.md`](../prompts.md), que registra solo los prompts clave.
Los turnos de la autora están transcritos **textuales**. Los turnos del asistente se
resumen en qué hizo y qué herramientas usó, porque incluyen volcados de archivos y salidas
de comandos que no aportan al registro.

**Configuración de IA usada en esta sesión:** ningún skill, subagente, hook ni comando
personalizado. Claude Code con acceso a Bash y al árbol del repositorio, nada más. En este
punto de la conversación `CLAUDE.md` todavía no existía: se creó dentro de esta misma
sesión, así que el asistente trabajó sin contrato operativo previo y con las reglas
íntegramente en el prompt. El MCP de GitHub falló al conectar (`400: Authorization header
is badly formatted`) y no se usó.

---

## Turno 1 — Autora

> Sos un asistente trabajando sobre el repositorio de mi proyecto final del máster AI4Devs.
> Tu tarea es REESTRUCTURAR la documentación existente. Es un trabajo de extracción y
> reorganización, NO de redacción de contenido nuevo.
>
> ## Contexto del proyecto
>
> - Producto: "Platita", asistente financiero personal y familiar por WhatsApp con IA.
> - Autora: Verónica Noemi Zacarías (iniciales VNZ).
> - El repo es un fork de https://github.com/LIDR-academy/AI4Devs-finalproject
> - El código y la documentación viven ambos en este fork. Una rama por entrega.
> - Rama de trabajo actual: feature/entrega-1-VNZ (ya estoy parada en ella, árbol limpio).
> - Entrega 1 (documentación, sin código) vence el 24 de septiembre de 2026.
> - Stack previsto para las entregas siguientes: Python + FastAPI, arquitectura hexagonal
>   (ports & adapters), PostgreSQL con pgvector, frontend web para dashboard.
> - Regla de idioma del proyecto: TODA la documentación va en español. El código, las
>   entidades, las columnas de base de datos, los endpoints y los nombres de archivo de
>   código van en inglés. Los mensajes al usuario final (WhatsApp) van en español.
> - Trabajo en macOS, filesystem case-insensitive. Tenelo en cuenta para renombrados.
>
> ## Estado actual del repositorio
>
> - En la raíz hay un README (puede llamarse `readme.md` o `README.md`) de unas 760 líneas
>   que contiene TODA la documentación siguiendo la plantilla oficial del curso, con las
>   secciones numeradas 0 a 7 [...]
> - Hay un `prompts.md` en la raíz con el registro de uso de IA, organizado con la misma
>   numeración de secciones.
> - Varias secciones contienen diagramas Mermaid inline y bloques de código.
>
> ## Estructura objetivo
>
> ```
> README.md                  <- portada e índice. Sin contenido propio de las secciones.
> prompts.md                 <- se queda en la raíz, el curso lo pide por nombre exacto
> CLAUDE.md
> AGENTS.md
> LICENSE
> docs/
>   00-ficha.md
>   01-producto.md
>   02-arquitectura.md
>   03-modelo-de-datos.md
>   04-api.md
>   05-historias-de-usuario.md
>   06-tickets.md
>   07-pull-requests.md
>   reglas-de-dominio.md
>   adr/
>     0001-arquitectura-hexagonal.md
>     0002-whatsapp-como-canal-principal.md
>     0003-login-por-codigo-unico.md
>     0004-postgres-con-pgvector-como-unico-almacen.md
>     0005-python-fastapi-en-vez-de-go.md
> ```
>
> ## Reglas inviolables
>
> 1. NO inventes contenido. Todo el texto de `docs/00-` a `docs/07-` y de
>    `reglas-de-dominio.md` sale del README actual, copiado literal. Si algo te parece
>    incompleto, dejalo como está y reportámelo al final. No lo completes vos.
> 2. NO reescribas, no resumas, no "mejores" la redacción, no cambies el tono. Es un
>    movimiento de texto, no una edición.
> 3. Un solo dueño por hecho. Ningún contenido puede quedar en dos archivos. Si extraés
>    algo a `reglas-de-dominio.md`, en el origen queda un resumen de 2 o 3 líneas y un
>    enlace, nunca el texto completo repetido.
> 4. La serie numerada `00-` a `07-` está CERRADA. No crees archivos nuevos con número.
>    Todo documento futuro va en `docs/` con nombre descriptivo sin número.
> 5. Nombres de archivo en kebab-case, sin acentos ni ñ (rompen en Linux y CI). Excepciones
>    que conservan su nombre canónico porque las herramientas los buscan así:
>    `README.md`, `CLAUDE.md`, `AGENTS.md`, `LICENSE`, `prompts.md`.
> 6. Preservá los bloques Mermaid y los bloques de código intactos, con su sección.
> 7. No hagas commit ni push. Dejá los cambios en el working tree.
>
> *(Siguen las siete tareas detalladas —partir el README, portada, reglas de dominio,
> CLAUDE.md, AGENTS.md, los cinco ADR, licencia y ficha—, una lista de verificación de
> ocho puntos, y el cierre:)*
>
> ## Antes de escribir nada
>
> Mostrame primero el plan: qué archivos vas a crear, qué rango de secciones va a cada uno,
> qué referencias cruzadas detectaste y cómo las vas a convertir, y qué reglas de dominio
> identificaste para extraer. Esperá mi aprobación antes de tocar archivos.

### Asistente

Leyó el README completo (760 líneas) y `prompts.md`, mapeó los encabezados y las
referencias cruzadas con `grep`, y obtuvo el remoto con `git remote get-url origin`.
Presentó el plan sin tocar archivos: tabla de rangos de líneas por documento, 16
referencias cruzadas detectadas (12 entre archivos, 4 internas), 9 grupos de reglas de
dominio, y cuatro puntos que requerían decisión humana —dos grupos de reglas no previstos
en el brief, la falta de fundamento del ADR 0005, el desajuste de `prompts.md`, y la
referencia inexistente "endpoint de 6.1" del Ticket 2.

---

## Turno 2 — Autora

> el documento 00-ficha.md me parece incesario separarlo, nunca va a cambiar, que esta
> informacion este directamente en el readme. Que otras definiciones quedaron pendientes?

### Asistente

Aceptó el recorte y señaló el choque con la regla de las 60 líneas del README: con la ficha
adentro daban ~70-75. Listó las definiciones pendientes en tres bloques: cinco que requerían
decisión de la autora, cinco huecos preexistentes del README, y dos ya resueltos.

---

## Turno 3 — Autora

> Respuestas a los puntos pendientes:
>
> 1. Tope del README: 75 líneas. Pero tomá el número como orientativo, no como regla.
>    La regla real es: el README contiene la ficha completa (0.1 a 0.5) y UNA línea por
>    documento en la tabla índice, nada más. Si queda en 80 líneas porque la ficha es
>    larga, está bien. Si queda en 60 porque metiste un resumen de alguna sección,
>    está mal.
>
> 2. Numeración: mantené 01- a 07-. No renumeres. Se corresponde con las secciones 1 a 7
>    de la plantilla oficial del curso y con la numeración interna de prompts.md.
>    El hueco del 00 no molesta.
>
> 3. Grupos extra de reglas de dominio: incluí los dos, el 8 (gastos recurrentes como
>    excepción a la confirmación) y el 9 (trazabilidad de origen / source).
>
> 4. ADR 0005 — la razón existe, no la dejes pendiente. Escribí el ADR completo con este
>    fundamento:
>
>    Contexto: la autora tiene 15+ años de experiencia backend y su stack principal es Go
>    con arquitectura hexagonal, además de NestJS y Java/Kotlin. Python también forma parte
>    de su stack. El producto tiene un núcleo de IA de primera clase [...]
>
>    *(sigue el fundamento completo: razones, consecuencias positivas, negativas y
>    alternativas descartadas)*
>
> 5. prompts.md: no lo reestructures. Agregá una sola línea al principio del archivo
>    aclarando que la numeración de secciones se corresponde con docs/01-… a docs/07-….
>
> 6. Corregí el "endpoint de 6.1" del Ticket 2 por "Ticket 1". Es una referencia a una
>    numeración que nunca existió. Autorizado como excepción explícita a la regla de no
>    editar contenido.
>
> 7. Borrá la nota "Cambiá el nombre si preferís otro" de 0.2. Es una instrucción para mí,
>    no documentación del producto.
>
> 8. Actualizá el árbol de carpetas de la sección 2.3 con la estructura real resultante de
>    esta reestructuración. Es obligatorio, no opcional: ese bloque describe el repositorio
>    y a partir de este cambio estaría afirmando algo falso [...]
>
> 9. Placeholders diferidos: dejalos tal cual, como propusiste.
>
> 10. Fecha de los ADR: 2026-09-20 en los cinco.
>
> Una cosa más antes de arrancar: en tu plan de la Tarea 3, la explicación de por qué las
> descripciones de entidades de 3.2 se quedan donde están quedó cortada a mitad de frase.
> El criterio es correcto, pero terminá de explicarlo antes de empezar: es el punto donde
> más fácil se cuela una duplicación entre 03-modelo-de-datos.md y reglas-de-dominio.md.
>
> Con eso, aprobado. Arrancá.

### Asistente

Cerró primero el criterio que había quedado a medias: qué frase de 3.2 es **descriptiva**
(se queda) y cuál es **prescriptiva** (se muda), con la tabla entidad por entidad.

Ejecutó después: `git mv readme.md README.md`, partición de las siete secciones con `sed`
por rango de líneas, y construcción de `reglas-de-dominio.md` mediante un script Python que
copia el texto **por número de línea** desde el README original y aborta si no encuentra el
fragmento esperado, en vez de retranscribirlo a mano.

Dos ajustes sobre la marcha, reportados a la autora:

- Las viñetas del catálogo must/should/could de 1.2 **no** se mudaron: son el entregable
  calificado del curso. Solo salió de 1.2 el bloque "qué se asume y qué se confirma", que
  era lo que el brief pedía. Los demás grupos poseen el texto normativo de 3.1, 3.2 y la
  sección 6, y enlazan a 1.2 sin copiarlo.
- Del Ticket 1 salieron seis viñetas de alcance técnico que eran regla de dominio, y
  quedaron las cinco que son tarea de ingeniería (firma del webhook, extracción vía
  `LLMPort`, promoción atómica, job de expiración, fuera de alcance).

Escribió el README de 59 líneas con la ficha completa, `CLAUDE.md`, `AGENTS.md`, `LICENSE`
y los cinco ADR, y corrió una verificación automatizada de los ocho puntos pedidos.

**Dos errores propios detectados por esa verificación, no por lectura:**

1. Al partir la sección 4 se comió la marca de cierre del último bloque YAML, por un
   off-by-one en el rango de líneas. Lo detectó el chequeo de fences pares y regeneró el
   archivo desde `git show HEAD:readme.md`.
2. El heredoc sin comillas del ADR 0004 dejó que el shell interpretara `` `ADVICE_DOCUMENT` ``
   como sustitución de comando y borró la palabra. Lo detectó el barrido de backticks.

Además reportó que `CLAUDE.md` estaba siendo ignorado por el `~/.gitignore_global` de la
autora, así que existía en disco pero no aparecía en `git status`.

---

## Turno 4 — Autora

> forza el add de calude.md, hace commit , y push

### Asistente

`git add -f CLAUDE.md`, commit `6ddbe05` (19 archivos, +1244 / −760) y push a
`origin/feature/entrega-1-VNZ`. Señaló que el renombrado del README ya no figura como `R`
sino como borrado más alta, porque el contenido cambió casi por completo al convertirse en
portada y git no lo empareja por similitud.

---

## Turno 5 — Autora

> actualiza el archivo prompts.md, si necesitas alguna informacion pregunta, no inventes nada

### Asistente

Leyó `prompts.md` y planteó tres preguntas en vez de completar por su cuenta: cómo
transcribir prompts de 100+ líneas, si completar los dos placeholders de modelo, y dónde
ubicar un trabajo que tocó todas las secciones.

---

## Turno 6 — Autora

Aportó la consigna oficial de la entrega, que pide máximo 3 prompts por sección, permite
adjuntar la conversación completa como archivo o link, y suma como requisito documentar
herramientas, modelos y para qué se usó cada uno, y si se usaron skills, subagentes, rules
o comandos personalizados.

### Asistente

Esa consigna resolvió dos de las tres preguntas —fragmento decisivo en `prompts.md` más
conversación completa adjunta, y sección propia— y dejó al descubierto que el archivo no
tenía un apartado explícito de skills, subagentes y rules, que a partir de esta sesión sí
tiene contenido real. Quedó pendiente solo el dato de los modelos de las fases anteriores,
que la autora debía aportar.
