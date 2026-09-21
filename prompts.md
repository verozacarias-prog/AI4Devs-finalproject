> Registro del uso de IA en el desarrollo de **Platita**. Sigue la estructura de la plantilla oficial (secciones 1 a 7, máximo 3 prompts por sección). Cada prompt se transcribe **textual**, tal como se escribió, sin corregir la redacción ni limpiar las dudas — incluidos los que rechazaron o corrigieron una propuesta de la IA, que son los que mejor muestran dónde estuvo el criterio humano.
>
> Para cada prompt se indica: herramienta y modelo, qué devolvió, y qué decisión se tomó a partir de eso.
>
> La numeración de secciones de este archivo se corresponde con `docs/01-producto.md` a `docs/07-pull-requests.md`. La reestructuración que produjo esa división se registra en su propia sección, sin número, porque tocó todas.

---

## Herramientas y modelos por fase

| Fase | Herramienta | Modelo | Para qué |
|---|---|---|---|
| Ideación y definición de producto | Claude (claude.ai) | Claude Opus 4.1 | Iterar la idea sin generar documentación, discutir alcance y decisiones de producto |
| Análisis de repositorios de referencia | Claude Code | Claude Sonnet 4.5 | Auditar la plantilla oficial y dos proyectos de ejemplo del curso, con acceso al código y al historial git local |
| Documentación técnica (readme.md) | Claude (claude.ai) | Claude Opus 4.1 | Redactar y refinar arquitectura, modelo de datos, HU y tickets |
| Reestructuración de la documentación | Claude Code | Claude Opus 5, contexto 1M (`claude-opus-5[1m]`) | Partir el readme monolítico en `docs/`, extraer las reglas de dominio, redactar `CLAUDE.md` y los ADR |
| Código, tests y despliegue | *(pendiente — Entrega 2)* | | |

## Skills, subagentes, rules y comandos personalizados

| Recurso | Estado en la Entrega 1 |
|---|---|
| `CLAUDE.md` — rules del proyecto | **Versionado.** Contrato operativo para asistentes de IA: regla de idioma, regla de dependencia hexagonal con lista negra de imports en `domain/`, siete invariantes que un asistente rompe por defecto, convenciones de código, seguridad, migraciones, y la regla de precedencia entre especificación y código |
| `AGENTS.md` | **Versionado.** Tres líneas que remiten a `CLAUDE.md`, para que otros asistentes lo encuentren sin duplicar su contenido |
| Skills | No se usaron |
| Subagentes | No se usaron |
| Hooks | No se configuraron |
| Comandos personalizados | No se crearon |
| MCP | Google Calendar, Google Drive y `claude-mermaid` (previsualización de diagramas). El MCP de GitHub está configurado pero falla al conectar por un error de header de autorización — sigue pendiente de revisión |

La auditoría de repos de referencia (ver §1, Prompt 2) recomendó configurar y versionar las rules antes de empezar a codear, porque **ninguno de los dos proyectos de ejemplo del curso lo había hecho**. `CLAUDE.md` y `AGENTS.md` se escribieron al cierre de la Entrega 1 siguiendo esa recomendación, de modo que la Entrega 2 arranque con el contrato ya puesto. Los hooks, skills y subagentes quedan para la fase de código, donde tienen sentido.

Hay un detalle operativo que vale registrar: `CLAUDE.md` estaba siendo ignorado por el `.gitignore` global del entorno de trabajo, así que existía en disco pero no entraba al repositorio. Se detectó al revisar `git status` después de crearlo y se resolvió con `git add -f`.

**Nota de método:** ninguna cifra, métrica ni porcentaje de este proyecto fue generado por IA sin verificación. Esa decisión salió directamente de un hallazgo de la auditoría de repos: los dos proyectos de ejemplo del curso declaraban métricas (cobertura de tests, ROI) que no se correspondían con su código.

---

## 1. Descripción general del producto

**Prompt 1** — *Claude (claude.ai) · ideación inicial*

> "Sí, quiero eh, contarte la idea del proyecto y ir iterándola. Eh, en la primera entrega de, de este proyecto final es solo documentación, o sea, desarrollar la idea igual después te voy a pasar bien el documento pero es desarrollar la idea y presentar toda la documentación ahora solo quiero que iteremos la idea sin generar ningún tipo de documentación Eh, ellos especifican que tiene que ser todo desarrollado de punta a punta con IA"

*Qué devolvió y qué se decidió:* la instrucción explícita de **no generar documentación todavía** fue deliberada, para evitar que el asistente saltara a producir el entregable antes de que la idea estuviera decidida. Se evaluaron dos dominios (asistente financiero y asistente de hábitos/fitness) y se eligió el financiero por ser una necesidad real propia: manejo de dos monedas y presupuesto familiar resueltos hoy en planillas.

---

**Prompt 2** — *Claude Code · auditoría de repositorios de referencia*

> "no no para, ya clone los repo, porque tambien me sirve tener el codigo local, quiero que hagas especial enfasis en agentes, skills y todo lo que hayan hecho en esos repos para uso de ia, dame el prompt"

*Contexto:* la propuesta inicial de la IA era leer los repos desde el chat. Se descartó: al estar clonados en local, Claude Code puede revisar el **historial git completo**, no solo los archivos actuales. Esa diferencia resultó decisiva.

*Qué devolvió y qué se decidió:* el informe (`informe-repos-referencia.md`) encontró que **ninguno de los dos proyectos de ejemplo versionó configuración de IA** (sin `CLAUDE.md`/`AGENTS.md`, sin reglas, subagentes ni hooks), y que el único caso real de reglas versionadas estaba en el historial de la plantilla, proveniente de entregas de otros alumnos mergeadas por error. Hallazgo que condicionó todo el resto del proyecto: **el error más común es que la documentación no coincida con el código implementado** (arquitectura AWS documentada sobre mocks JSON, cobertura del 85% declarada con 11 tests). De ahí salió la decisión de clasificar explícitamente el alcance en este proyecto (ver Prompt 3).

---

**Prompt 3** — *Claude (claude.ai) · alineación de alcance con los criterios del curso*

> "bueno, volve a leer Proyecto Final Master, el documento de contexto, para alinear lo que tenemos hasta ahora con lo ellos piden recomiendan"

*Qué devolvió y qué se decidió:* la auditoría detectó que la sección 1.2 listaba 14 funcionalidades contra solo 3 historias de usuario, cuando el curso pide 3-5 must-have y exige que en la entrega final esas funcionalidades estén completas, testeadas y desplegadas. Se decidió **clasificar las funcionalidades en must / should / could-have** dentro del propio readme, dejando por escrito que lo could-have está diseñado pero no implementado —decisión de alcance, no omisión—, y **subir de 3 a 5 las historias de usuario** para cubrir features must-have que no tenían HU que las respaldara (cuentas con saldo, armado del presupuesto). El parser de emails, la funcionalidad de mayor riesgo (depende de formatos de mail de cada banco, que no se controlan), se movió a could-have.

---

## 2. Arquitectura del Sistema

### 2.1. Diagrama de arquitectura

**Prompt 1** — *Claude (claude.ai) · corrección sobre el patrón arquitectónico*

> "-todo el desarrollo va a estar en ingles, por lo tanto nombres en base de datos etc tambien
> -no mencionas que se va a usar arquitectura hexagonal"

*Qué devolvió y qué se decidió:* la documentación describía el sistema como "arquitectura por capas" sin nombrar el patrón real que se quería seguir. Se reescribió la sección 2.1 declarando **arquitectura hexagonal (ports & adapters)** de forma explícita, con el dominio aislado detrás de puertos y los adaptadores de entrada/salida separados en el diagrama y en la estructura de carpetas. La justificación quedó anclada a una razón concreta del proyecto: hay varias integraciones externas reemplazables (WhatsApp, LLM, base vectorial, cotizaciones) y ya se identificó al menos un reemplazo probable. Se definió además que **todo el desarrollo va en inglés** (tablas, campos, endpoints), reservando el español para el contenido de cara al usuario final.

---

**Prompt 2** — *Claude (claude.ai) · herramientas de diagramación*

> "bueno, ahora en el documento de contexto de proyecto final de ai4devs, indican algunas herramientas para generar mejores graficos y documentaciones, si es necesario releelo centrandote en eso, y apliquemos eso al nuestro documento"

*Qué devolvió y qué se decidió:* el material del curso recomienda **diagramas C4 en Mermaid** (un proyecto de referencia documentó su arquitectura con los 13 puntos de Simon Brown más C4). Se reestructuró la sección 2.1 en los tres niveles de C4 —contexto, contenedores y componentes— y se agregaron dos diagramas que faltaban: el de infraestructura (§2.4, que la plantilla pide explícitamente) y un diagrama de secuencia del flujo conversacional (§1.3).

*Verificación antes de dar la decisión por buena:* la IA propuso inicialmente la sintaxis nativa `C4Context`/`C4Container` de Mermaid. Al verificarlo, el renderizador Mermaid de GitHub **no soporta esa extensión**, así que los diagramas no se hubieran visto en el repositorio. Se reescribieron con `flowchart` y subgrafos, que es la práctica establecida para representar C4 en Markdown de GitHub. Los seis diagramas del readme se compilaron con `mermaid-cli` y se inspeccionaron renderizados antes de darlos por válidos — dos tenían etiquetas superpuestas que no se detectan leyendo el código fuente del diagrama.

---

### 2.2. Descripción de componentes principales

**Prompt 1** — *Claude (claude.ai) · pedido de justificación de decisiones técnicas*

> "explicame un poco estos dos puntos
> * pgvector sobre Postgres en vez de una base vectorial separada, para no sumar una segunda tecnología de BD a un proyecto de 30 horas.
> * Railway o Render para el despliegue, sin justificarlo a fondo todavía — lo dejé como propuesta a confirmar."

*Qué devolvió y qué se decidió:* se pidió explicación de dos decisiones que la IA había propuesto sin fundamentar. La respuesta llevó a verificar cuál de las dos plataformas soporta pgvector de forma nativa y a dejar la decisión documentada con su razón, en vez de como una preferencia sin sustento.

---

**Prompt 2** — *Claude (claude.ai) · rechazo de la justificación por esfuerzo*

> "Lo que yo quiero tambien con la base de datos, es que si en algun en el futuro quiero escalar esto no sea tan complicado. No nos centremos en las 30 horas de trabajo, mismo en ai4devs, dice tambien que muchos chicos le dedican mucho mas de eso."

*Qué devolvió y qué se decidió:* la IA había justificado pgvector con "es un proyecto de 30 horas", un argumento de esfuerzo que no resuelve el problema de fondo. Se rechazó y se reescribió la decisión en términos de **reversibilidad**: el acceso a la base vectorial queda detrás de un puerto propio (`VectorStorePort`), de modo que cambiar a Pinecone/Qdrant/Weaviate sea reemplazar un adaptador y no tocar el dominio. La decisión dejó de apoyarse en el tiempo disponible y pasó a apoyarse en el diseño.

---

### 2.3. Estructura de ficheros

*Se completa en la Entrega 2, con el scaffold real generado. La estructura prevista (carpetas `domain/ports`, `adapters/inbound`, `adapters/outbound`) se definió en los prompts de 2.1.*

---

### 2.4. Infraestructura y despliegue

*Ver Prompt 1 de §2.2. Decisión pendiente de confirmación final; se documenta en la Entrega 2 junto con el despliegue real.*

---

### 2.5. Seguridad

**Prompt 1** — *Claude (claude.ai) · requisitos de seguridad y alcance*

> "Varios puntos que se me ocurrieron ahora:
> -login para seguridad para la pagina web
> -modo offline?
> -backup de informacion, o exportacion del presupuesto y gastos si el usuario lo requiere
> -configuracion de gastos recurrentes"

*Qué devolvió y qué se decidió:* de acá salió el esquema de **login sin contraseñas** (código de un solo uso por WhatsApp, canal ya verificado, intercambiado por un JWT corto), que evita almacenar y gestionar contraseñas. El modo offline se evaluó y se **descartó con su razón documentada**: el canal principal ya requiere conectividad, y el problema real no sería cachear datos sino resolver conflictos de sincronización de ediciones offline.

---

### 2.6. Tests

*Se completa en la Entrega final. La estrategia prevista (tests unitarios sobre casos de uso con dobles de prueba en lugar de adaptadores reales, integración sobre adaptadores y endpoints, y un E2E del flujo principal) se definió como consecuencia directa de la arquitectura hexagonal documentada en §2.1.*

---

## 3. Modelo de Datos

**Prompt 1** — *Claude (claude.ai) · corrección sobre el origen del contenido del RAG*

> "aca hay un tema, los documentos financieron no los carga el usuario, los cargaria yo como dueña del producto, para pre-cargar lo que el usuario le puede preguntar a la ia, se puede hacer algun mecanismo de ver si hay que actualizar esa informacion."

*Qué devolvió y qué se decidió:* la IA había modelado la base de conocimiento del RAG como contenido **por usuario** (con `usuario_id`), lo cual era un malentendido del producto: es contenido curado por el equipo, compartido entre todos los usuarios. Se rediseñó la entidad `ADVICE_DOCUMENT` quitando la relación con el usuario y agregando `topic`, `status` y `last_reviewed_at` para poder gestionar la vigencia del contenido. Se descartó automatizar la actualización: con el volumen real (decenas o cientos de artículos curados) alcanza una revisión periódica manual apoyada en esa marca.

---

**Prompt 2** — *Claude (claude.ai) · rechazo de un valor por defecto*

> "no, un gasto no se puede registrar sin cuenta asociada, si o si lo tiene que pedir, igual que pedir a que presupuesto pertenece, son datos que no se pueden suponer, hay que definir datos con los cuales no se puede registrar un gasto o ingreso, y si o si hay que pedirlos"

*Contexto:* este es el ajuste humano más significativo de la fase de diseño, y llegó **en dos rondas**. La IA propuso primero una cuenta "efectivo" por defecto autogenerada, para que el campo pudiera ser obligatorio sin fricción. Se rechazó por comodidad falsa. La IA corrigió haciendo el campo opcional, lo que se rechazó también: un movimiento sin cuenta rompe el saldo calculado, que es una de las garantías centrales del producto.

*Qué se decidió:* los campos pasaron a ser `NOT NULL` **en la base de datos**, no solo validados en la aplicación, de modo que ninguna vía de carga pueda saltear la regla. Como contrapartida se creó la entidad `PENDING_TRANSACTION`, en tabla aparte: lo que se interpretó de un mensaje incompleto se guarda ahí mientras el asistente pregunta lo que falta, sin descartar el trabajo ya hecho ni relajar las restricciones de la tabla de la que salen saldos y presupuestos.

---

**Prompt 3** — *Claude (claude.ai) · corrección del exceso opuesto*

> "si no viene la fecha en el mensaje, se toma la actual, si quiere cambiar la fecha lo dira en el mensaje de confirmacion, la fecha define el periodo de presupuesto, eso se maneja internamente, no se pregunta, la categoria se maneja como se habia definido, si no viene, se trata de ubicar en una categoria existente y si no encaja en ninguna se sugiere la creacion de una, la moneda se toma la primaria a menos que se diga lo contrario."

*Qué devolvió y qué se decidió:* tras el Prompt 2, la IA había generalizado la regla de "no suponer nada" a **todos** los campos, lo que hubiera convertido cargar un gasto en un interrogatorio. Esta corrección acotó el criterio: fecha, moneda y categoría **sí** tienen un valor por defecto derivable y no se preguntan; se muestran en el mensaje de confirmación, que pasa a ser el punto donde el usuario los corrige. La lista de datos que se piden quedó reducida a monto, cuenta, tipo cuando es ambiguo, y confirmación del presupuesto.

---

## 4. Especificación de la API

*Los tres endpoints documentados (`POST /webhook/whatsapp`, `GET /budgets/{budget_id}`, `POST /transactions`) se derivaron de las decisiones de modelo de datos de §3, no de un prompt independiente. El contrato OpenAPI completo se genera desde el código en la Entrega 2 y se recorta a los 3 endpoints que pide la plantilla — patrón tomado de la auditoría de repos de referencia (§1, Prompt 2), que identificó los ERD y árboles de carpetas generados **a partir del código real** como marcador de una entrega sólida.*

---

## 5. Historias de Usuario

**Prompt 1** — *Claude (claude.ai) · definición del alcance del MVP*

> "bueno, volve a leer Proyecto Final Master, el documento de contexto, para alinear lo que tenemos hasta ahora con lo ellos piden recomiendan"
>
> *(seguido de)* "si, me parece bien, arranca con eso"

*Qué devolvió y qué se decidió:* se pasó de 3 a 5 historias de usuario, ordenadas por secuencia real de uso (configurar cuentas → armar presupuesto → registrar movimientos → revisar dashboard → recibir alertas). Cuatro son must-have y componen el flujo end-to-end comprometido; la quinta (alertas con RAG) es should-have. Se marcó la prioridad **dentro de cada historia**, para que el alcance comprometido sea legible sin cruzar secciones.

---

**Prompt 2** — *Claude (claude.ai) · caso de uso real que originó una funcionalidad*

> "antes de ingresar un gasto hay que revisar si ya no fue ingresado por via automatica, porque lo que me pasa mucho a mi, es que yo hago un gasto por medio de la tarjeta o la cuenta bancaria, y me llega un mail de aviso de ese gasto, entonces ahi se estaria duplicando el consumo"

*Qué devolvió y qué se decidió:* funcionalidad que no estaba contemplada y que salió de la experiencia concreta de uso. Se agregó el campo `duplicate_of` (autoreferencia en `TRANSACTION`) y el mecanismo de detección por monto, moneda y ventana de fechas entre vías de carga opuestas. Al clasificar el alcance (§1, Prompt 3) quedó como could-have, porque depende de la carga por email: la columna se crea desde la migración inicial, la lógica llega después.

---

## 6. Tickets de Trabajo

**Prompt 1** — *Claude (claude.ai) · ajuste de configuración de presupuestos*

> "se me ocurren dos cosas, tambien, la configuracion del periodo de presupuestos, si es mensual, si es quincenal, y la definicion de la fecha de armado del presupuesto, por ejemplo, si es mensual, antes del primero del mes el presupuesto ya tiene que estar armado, incluyendo todos los ingresos y gastos estimados"

*Qué devolvió y qué se decidió:* obligó a separar el modelo en dos entidades. `BUDGET_PERIOD` pasó a contener el presupuesto del mes/quincena como concepto completo (dueño, cadencia, fechas, ingreso estimado y estado `draft`/`confirmed`), y `BUDGET` quedó reducido al tope de una categoría dentro de ese período. Antes, cada límite por categoría repetía sus propias fechas. La regla de negocio "tiene que estar confirmado antes de que arranque el período" se implementó como estado, no como un campo de fecha límite separado, reutilizando el mismo mecanismo de recordatorio proactivo que ya existía para las alertas de presupuesto.

---

**Prompt 2** — *Claude (claude.ai) · verificación de una funcionalidad que se daba por hecha*

> "los gastos recurrentes se les puede definir un presupuesto cuando se ingresan, eso ya esta no?"

*Qué devolvió y qué se decidió:* **no estaba.** `RECURRING_EXPENSE` tenía categoría, monto y periodicidad, pero ni cuenta ni presupuesto — lo que hubiera hecho que cada ejecución mensual generara un pendiente pidiendo datos, exactamente lo contrario de lo que un gasto recurrente debe hacer. Se agregaron `account_id` y el dueño del presupuesto. Detalle de diseño: se guarda el **dueño** (usuario o grupo familiar) y no un `budget_period_id` concreto, porque la regla vive a lo largo de muchos períodos; en cada ejecución se resuelve el período de ese dueño que cubre la fecha.

---

## 7. Pull Requests

*No aplica a esta entrega. Se completa en la Entrega final con 3 pull requests reales enlazados.*

---

## Reestructuración de la documentación

> Fase posterior a la redacción del contenido: el readme monolítico de 760 líneas se partió en `docs/`. Trabajo hecho con **Claude Code sobre Claude Opus 5 (contexto 1M)**, no en claude.ai, porque requería acceso al árbol de archivos, a `git` y a la ejecución de scripts de verificación.
>
> La conversación completa está en [`docs/conversacion-reestructuracion-docs.md`](docs/conversacion-reestructuracion-docs.md). Acá van los tres prompts decisivos.

**Prompt 1** — *Claude Code · brief de reestructuración con reglas inviolables*

> "Tu tarea es REESTRUCTURAR la documentación existente. Es un trabajo de extracción y reorganización, NO de redacción de contenido nuevo. [...] NO inventes contenido. Todo el texto de `docs/00-` a `docs/07-` y de `reglas-de-dominio.md` sale del README actual, copiado literal. Si algo te parece incompleto, dejalo como está y reportámelo al final. No lo completes vos. [...] Un solo dueño por hecho. Ningún contenido puede quedar en dos archivos. [...] Mostrame primero el plan [...] Esperá mi aprobación antes de tocar archivos."

*(prompt completo: ~130 líneas con las siete tareas y una lista de verificación de ocho puntos)*

*Qué devolvió y qué se decidió:* el plan previo evitó el problema que más caro sale en este tipo de tarea. Al mapear las referencias cruzadas antes de mover nada, la IA detectó que el Ticket 2 apuntaba a un "endpoint de 6.1" que **nunca existió** —la sección 6 no tiene subsecciones numeradas— y, en vez de corregirlo por su cuenta, lo reportó. La regla de pedir el plan primero también expuso que el fundamento del ADR 0005 no estaba escrito en ninguna parte del readme (ver Prompt 2).

---

**Prompt 2** — *Claude Code · aporte del fundamento que faltaba y corrección de un corte de razonamiento*

> "ADR 0005 — la razón existe, no la dejes pendiente. Escribí el ADR completo con este fundamento: [...]"
>
> "Una cosa más antes de arrancar: en tu plan de la Tarea 3, la explicación de por qué las descripciones de entidades de 3.2 se quedan donde están quedó cortada a mitad de frase. El criterio es correcto, pero terminá de explicarlo antes de empezar: es el punto donde más fácil se cuela una duplicación entre 03-modelo-de-datos.md y reglas-de-dominio.md."

*Qué devolvió y qué se decidió:* dos correcciones humanas de naturaleza distinta. La primera **aporta información que la IA no tenía y con razón no inventó**: la elección de Python sobre Go nunca se había justificado por escrito, y el ADR habría quedado con las secciones vacías. La segunda detecta que el asistente había dejado un criterio a medio explicar y exige cerrarlo *antes* de ejecutar, no después — el criterio en cuestión (frase descriptiva se queda en 3.2, frase prescriptiva se muda a reglas de dominio) es exactamente el que evita duplicar contenido entre los dos archivos. Al explicitarlo, el asistente cambió su propio plan: las viñetas del catálogo must/should/could de 1.2 dejaron de mudarse, porque son el entregable calificado del curso.

---

**Prompt 3** — *Claude Code · verificación automatizada como parte del entregable*

> *(de la lista de verificación del Prompt 1)* "Revisá y reportá el resultado de cada punto: 1. Todos los enlaces relativos del README y de los docs resuelven a un archivo que existe. [...] 4. Los bloques Mermaid siguen siendo sintácticamente válidos y están completos. [...] 7. El total de líneas de `docs/` más `README.md` es aproximadamente igual al del README original, más lo nuevo. Si perdiste contenido en el camino, se nota acá."

*Qué devolvió y qué se decidió:* exigir una verificación **ejecutable** en vez de una revisión por lectura fue lo que encontró los errores. El asistente escribió un script que valida los 70 enlaces relativos contra archivo y ancla, busca bloques repetidos entre archivos, cuenta fences de código y compara volumen contra el original. Encontró dos errores propios que una lectura no habría detectado: un bloque YAML sin cerrar por un off-by-one al partir la sección 4, y una palabra borrada por el shell al interpretar backticks dentro de un heredoc. El punto 7 confirmó que las 41 líneas del original ausentes en la estructura nueva eran todas ediciones deliberadas, sin pérdida involuntaria.

---

## Ajustes humanos sobre el output de la IA — resumen

| # | Qué propuso la IA | Qué se corrigió y por qué |
|---|---|---|
| 1 | Base de conocimiento del RAG modelada por usuario | Es contenido curado por el producto, compartido. Se rediseñó la entidad y se agregó gestión de vigencia |
| 2 | Justificar pgvector con "es un proyecto de 30 horas" | Argumento de esfuerzo, no de diseño. Se reemplazó por reversibilidad detrás de un puerto |
| 3 | Describir el sistema como "arquitectura por capas" | Se declaró explícitamente hexagonal y se reflejó en diagrama y estructura de carpetas |
| 4 | Cuenta "efectivo" por defecto para movimientos sin cuenta | Comodidad falsa: ensucia el saldo calculado. Rechazado |
| 5 | Hacer el campo cuenta opcional (segunda propuesta) | También rechazado: sin cuenta no hay saldo confiable. Se impuso `NOT NULL` + `PENDING_TRANSACTION` |
| 6 | Generalizar "no suponer nada" a todos los campos | Exceso opuesto: fecha, moneda y categoría sí tienen default derivable. Se acotó la regla |
| 7 | Dar por implementado el presupuesto en gastos recurrentes | No estaba. Se detectó al preguntar explícitamente en vez de asumir |
| 8 | Documentar 14 funcionalidades con 3 historias de usuario | Brecha entre lo prometido y lo comprometido. Se clasificó en must/should/could-have |
| 9 | Dejar el ADR 0005 con las secciones en `[pendiente de completar]` | Correcto no inventarlo, pero la razón existía sin escribir. La aportó la autora y el ADR se completó |
| 10 | Separar la ficha del proyecto en un `docs/00-ficha.md` propio | Información que nunca cambia y que el curso busca en la portada. Se eliminó el archivo y la ficha quedó en el README |
| 11 | Mudar todo el catálogo must/should/could de 1.2 a las reglas de dominio | Es el entregable calificado del curso. Solo se mudó el bloque normativo; el resto se enlaza |
| 12 | Tratar las viñetas de alcance técnico del Ticket 1 como reglas de dominio en bloque | Seis eran regla, cinco eran tarea de ingeniería. Vaciar el ticket lo habría dejado sin contenido |

El patrón que se repite: la IA tiende a **resolver la ambigüedad por su cuenta** eligiendo un valor por defecto razonable, y a **justificar decisiones técnicas por el esfuerzo** que ahorran en vez de por sus propiedades de diseño. Las dos cosas hay que detectarlas leyendo, porque el resultado siempre suena defendible.

En la fase de reestructuración aparece un patrón distinto, propio de trabajar con la IA sobre archivos en vez de sobre texto en un chat: los errores dejan de ser de criterio y pasan a ser **mecánicos y silenciosos** —un bloque de código sin cerrar, una palabra que se come el shell—. No se detectan leyendo el resultado, porque el archivo sigue pareciendo correcto. Se detectan ejecutando una verificación. De ahí que la lista de comprobaciones vaya dentro del prompt y no después.

---

## Pendiente para las próximas entregas

- ~~Configurar y versionar `CLAUDE.md`~~ — hecho al cierre de la Entrega 1. Faltan los hooks y los subagentes, que se definen en la fase de código.
- Completar en `CLAUDE.md` la sección 11, «Comandos de verificación», que hoy dice «Se completa en la entrega 2».
- Revisar el MCP de GitHub, que falla al conectar por un error de header de autorización.
- Registrar los prompts de código, tests y despliegue a medida que se escriben, no al cierre.
- Verificar la sincronización entre la documentación (`docs/02-arquitectura.md` §2.3, `docs/03-modelo-de-datos.md`, `docs/04-api.md`) y el código real antes de cada entrega, aplicando la regla de precedencia de `CLAUDE.md` §10: la especificación manda, lo que se corrige es el código.
- Dar contenido propio a los grupos 6 (multimoneda) y 9 (trazabilidad de origen) de `docs/reglas-de-dominio.md`, que hoy son grupos de enlace: su texto normativo vive en el catálogo de funcionalidades de §1.2 y no se duplicó.
