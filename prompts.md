> Registro del uso de IA en el desarrollo de **Platita**. Sigue la estructura de la plantilla oficial (secciones 1 a 7, máximo 3 prompts por sección). Cada prompt se transcribe **textual**, tal como se escribió, sin corregir la redacción ni limpiar las dudas — incluidos los que rechazaron o corrigieron una propuesta de la IA, que son los que mejor muestran dónde estuvo el criterio humano.
>
> Para cada prompt se indica: herramienta y modelo, qué devolvió, y qué decisión se tomó a partir de eso.
>
> La numeración de secciones se corresponde con `docs/01-producto.md` a `docs/07-pull-requests.md`, las siete de la plantilla oficial. Los prompts que produjeron esa división y el resto de la estructura del repositorio están en §2.3, que es donde la plantilla pide la estructura de ficheros.
>
> Dos bloques quedan fuera de la numeración porque la consigna los pide aparte: la tabla de herramientas y modelos, acá arriba, y el resumen de ajustes humanos sobre el output de la IA, al final.

**De dónde salió esta documentación.** Las secciones 1 a 6 nacieron de una conversación
iterativa en claude.ai, un ida y vuelta largo de preguntas y ajustes que no se adjunta por su
extensión. Sus prompts decisivos están transcritos en cada sección; lo que esa conversación
dejó, en síntesis:

- **La elección del dominio.** Se evaluaron dos ideas y ganó la financiera por ser una necesidad
  propia y concreta: varias cuentas, dos monedas y un presupuesto familiar resueltos a mano en
  planillas.
- **El alcance, acotado y declarado.** Las funcionalidades quedaron clasificadas en must, should
  y could-have, y las historias de usuario subieron de tres a cinco para que ninguna funcionalidad
  comprometida quedara sin una que la respalde.
- **El patrón arquitectónico, nombrado.** La documentación describía el sistema como «por capas»
  sin comprometerse; pasó a declarar arquitectura hexagonal, con la regla de dependencia escrita
  y reflejada en el diagrama y en la estructura de carpetas.
- **Las decisiones justificadas por diseño, no por esfuerzo.** Se rechazó explícitamente el
  argumento de «es un proyecto corto» como fundamento técnico, y se lo reemplazó por propiedades
  verificables, como la reversibilidad de un motor detrás de un puerto.
- **Las reglas de dominio más duras.** De ahí salieron las que hoy están en
  [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md): ninguna cuenta por defecto, ningún
  presupuesto imputado sin confirmación, y sólo tres valores derivables sin preguntar.
- **El criterio de verificación.** Ninguna cifra ni métrica se dio por buena sin comprobarla, y
  se prefirió dejar una sección incompleta antes que completarla con algo plausible.

---

## Herramientas y modelos por fase

| Fase | Herramienta | Modelo | Para qué |
|---|---|---|---|
| Ideación y definición de producto | Claude (claude.ai) | Claude Opus 4.1 | Iterar la idea sin generar documentación, discutir alcance y decisiones de producto |
| Análisis de repositorios de referencia | Claude Code | Claude Sonnet 4.5 | Auditar la plantilla oficial y dos proyectos de ejemplo del curso, con acceso al código y al historial git local |
| Documentación técnica (readme.md) | Claude (claude.ai) | Claude Opus 4.1 | Redactar y refinar arquitectura, modelo de datos, HU y tickets |
| Reestructuración de la documentación | Claude Code | Claude Opus 5, contexto 1M (`claude-opus-5[1m]`) | Partir el readme monolítico en `docs/`, extraer las reglas de dominio, redactar `CLAUDE.md` y los ADR |
| Diagnóstico arquitectónico y cierre de la especificación | Claude Code | Claude Opus 5.5, contexto 1M (`claude-opus-5-5[1m]`) | Auditar la especificación contra el código, resolver los hallazgos con la autora y escribir las decisiones en `docs/` y en cuatro ADR |
| Diseño de la capa de datos | Claude Code | Claude Opus 5.5, contexto 1M (`claude-opus-5-5[1m]`) | Revisar el modelo de datos en modo de solo lectura, resolver las divergencias con la autora y escribir las decisiones en `docs/` y en dos ADR |
| Modelo de amenazas | Claude Code | Claude Opus 5.5, contexto 1M (`claude-opus-5-5[1m]`) | Analizar la seguridad de la especificación en modo de solo lectura, resolver con la autora las decisiones de sesión y de login, y escribirlas en `docs/` y en dos ADR |
| Código, tests y despliegue | *(pendiente — Entrega 2)* | | |

La auditoría de repos de referencia (ver §1, Prompt 2) recomendó configurar y versionar las rules antes de empezar a codear, porque **ninguno de los dos proyectos de ejemplo del curso lo había hecho**. Esa recomendación se siguió al cierre de la Entrega 1. La configuración resultante —contratos, skill, commands, verificadores y hook— está descrita en [`docs/flujo-de-trabajo-con-ia.md`](docs/flujo-de-trabajo-con-ia.md) y no se repite acá.

Hay un detalle operativo que vale registrar: `CLAUDE.md` estaba siendo ignorado por el `.gitignore` global del entorno de trabajo, así que existía en disco pero no entraba al repositorio. Se detectó al revisar `git status` después de crearlo y se resolvió con `git add -f`.

**Nota de método:** ninguna cifra, métrica ni porcentaje de este proyecto fue generado por IA sin verificación. Esa decisión salió directamente de un hallazgo de la auditoría de repos: los dos proyectos de ejemplo del curso declaraban métricas (cobertura de tests, ROI) que no se correspondían con su código.

---

## 1. Descripción general del producto

**Prompt 1** — *Claude (claude.ai) · ideación inicial*

> "Sí, quiero eh, contarte la idea del proyecto y ir iterándola. Eh, en la primera entrega de, de este proyecto final es solo documentación, o sea, desarrollar la idea igual después te voy a pasar bien el documento pero es desarrollar la idea y presentar toda la documentación ahora solo quiero que iteremos la idea sin generar ningún tipo de documentación Eh, ellos especifican que tiene que ser todo desarrollado de punta a punta con IA"

*Qué devolvió y qué se decidió:* la instrucción explícita de **no generar documentación todavía** fue deliberada, para evitar que el asistente saltara a producir el entregable antes de que la idea estuviera decidida. Se evaluaron dos dominios —asistente financiero y asistente de hábitos/fitness— y se eligió el financiero por ser una necesidad real propia: manejo de dos monedas y presupuesto familiar resueltos hoy en planillas.

Este prompt abrió una conversación iterativa larga, un ida y vuelta de preguntas y ajustes que produjo el contenido de las secciones 1 a 6 de este documento. No se adjunta completa por su extensión; sus intervenciones decisivas están transcritas en cada sección, y lo que dejó en conjunto fue esto:

- **El alcance, acotado y declarado.** Las funcionalidades quedaron clasificadas en must, should y could-have, y las historias de usuario subieron de tres a cinco para que ninguna funcionalidad comprometida quedara sin una que la respalde.
- **El patrón arquitectónico, nombrado.** La documentación describía el sistema como «por capas» sin comprometerse; pasó a declarar arquitectura hexagonal, con la regla de dependencia escrita y reflejada en el diagrama y en la estructura de carpetas.
- **Las decisiones justificadas por diseño, no por esfuerzo.** Se rechazó el argumento de «es un proyecto corto» como fundamento técnico y se lo reemplazó por propiedades verificables, como la reversibilidad de un motor de vectores detrás de un puerto.
- **Las reglas de dominio más duras.** De acá salieron las que hoy viven en [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md): ninguna cuenta por defecto, ningún presupuesto imputado sin confirmación explícita, y sólo tres valores derivables sin preguntar.
- **El criterio de verificación.** Ninguna cifra ni métrica se dio por buena sin comprobarla, y se prefirió dejar una sección marcada como incompleta antes que completarla con algo plausible.

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

**Prompt 3** — *Claude Code · diagnóstico arquitectónico de solo lectura, y cierre de la especificación*

> "Actuá como Arquitecto/a de Software Principal con experiencia en sistemas financieros y en productos construidos por equipos muy chicos. Tu criterio prioriza, en este orden: corrección e integridad de los datos, simplicidad operativa, costo, y recién después escalabilidad. [...] Esta tarea es de SOLO LECTURA. No crees, modifiques ni borres archivos. [...] Producir un diagnóstico arquitectónico accionable de Platita. [...] Cada hallazgo debe citar su evidencia con ruta de archivo [...] Distinguí siempre "según docs" de "según código"."
>
> *(y más adelante, sobre la primera propuesta de la IA para las cotizaciones)* "un adapter por cada pais, me parece un poco mucho, no se podria hacer un adapter generico y cosas particulares que necesita el adapter hacerlo por configuracion, con configuracion me refiero a que a mi como developer, incluir un nuevo pais no me cueste un adapter nuevo, si no que solo tenga que agregar configuracion"

*(prompt completo: ~110 líneas con rol, contexto, modo de trabajo, objetivo en dos fases, restricciones, formato de salida y criterio de calidad)*

*Qué devolvió y qué se decidió:* como todavía no existe código, el diagnóstico se hizo sobre la especificación y encontró 18 hallazgos, tres de ellos críticos. **El saldo podía sumar pesos con dólares**, porque nada obligaba a que un movimiento estuviera en la moneda de su cuenta. **Un reintento de WhatsApp duplicaba movimientos**, porque el webhook procesaba de forma síncrona y sin clave de idempotencia. **Una doble ejecución de recurrentes generaba dos cargos.** Las respuestas de la autora a las preguntas del diagnóstico cambiaron el supuesto de partida: Platita es para público general, no solo para la autora y su familia, y eso sumó diez hallazgos más, sobre privacidad, alta de usuarios, costo del LLM y plantillas de Meta.

La sesión no terminó en el informe. Cada hallazgo se resolvió con una decisión humana, se escribió en `docs/` y se commiteó por separado. De ahí salieron cuatro ADR: el [0010](docs/adr/0010-webhook-asincrono-con-tabla-de-entrada.md) (webhook asíncrono con tabla de entrada), el [0011](docs/adr/0011-cotizaciones-con-adaptador-generico-configurable.md) (cotizaciones con un adaptador genérico configurable), el [0012](docs/adr/0012-tarjetas-de-credito-y-transferencias.md) (tarjetas de crédito y transferencias) y el [0013](docs/adr/0013-datos-minimos-al-proveedor-de-llm.md) (datos mínimos al proveedor de LLM). También salieron los grupos 10 a 14 de las reglas de dominio y la HU6.

La corrección citada arriba muestra el patrón de la sesión. La primera propuesta de la IA para buscar cotizaciones era un adaptador por país: correcta, pero con un costo de código por cada país nuevo. La autora pidió que sumar un país fuera solo configuración, y el resultado, un adaptador HTTP genérico con las fuentes descritas en YAML, es mejor diseño que el original.

---

### 2.3. Estructura de ficheros

> La estructura real del repositorio —`docs/` numerado, reglas de dominio con dueño único, ADR, plantillas por funcionalidad y scripts de verificación— se construyó con **Claude Code sobre Claude Opus 5 (contexto 1M)**, no en claude.ai, porque requería acceso al árbol de archivos, a `git` y a la ejecución de scripts. La conversación completa está en [`docs/conversacion-reestructuracion-docs.md`](docs/conversacion-reestructuracion-docs.md).
>
> *La estructura de `backend/` y `frontend/` se completa en la Entrega 2 con el scaffold real; la prevista se definió en los prompts de §2.1.*

**Prompt 1** — *Claude Code · reestructurar el readme monolítico con reglas inviolables*

> "Tu tarea es REESTRUCTURAR la documentación existente. Es un trabajo de extracción y reorganización, NO de redacción de contenido nuevo. [...] NO inventes contenido. Todo el texto de `docs/00-` a `docs/07-` y de `reglas-de-dominio.md` sale del README actual, copiado literal. Si algo te parece incompleto, dejalo como está y reportámelo al final. No lo completes vos. [...] Un solo dueño por hecho. Ningún contenido puede quedar en dos archivos. [...] Mostrame primero el plan [...] Esperá mi aprobación antes de tocar archivos."

*(prompt completo: ~130 líneas con siete tareas y una lista de verificación de ocho puntos)*

*Qué devolvió y qué se decidió:* de acá salió la estructura actual — el readme de 760 líneas partido en `docs/01-` a `docs/07-`, las reglas de negocio extraídas a un archivo con dueño único, y los cinco ADR. Exigir el plan **antes** de tocar archivos evitó el problema que más caro sale: al mapear las referencias cruzadas, la IA detectó que el Ticket 2 apuntaba a un "endpoint de 6.1" que **nunca existió** —la sección 6 no tiene subsecciones numeradas— y, en vez de corregirlo por su cuenta, lo reportó. El mismo plan expuso que el fundamento del ADR 0005 no estaba escrito en ninguna parte del readme, y la autora tuvo que aportarlo (ver el ajuste 9 del resumen).

---

**Prompt 2** — *Claude Code · verificación ejecutable en vez de revisión por lectura*

> *(de la lista de verificación del Prompt 1)* "Revisá y reportá el resultado de cada punto: 1. Todos los enlaces relativos del README y de los docs resuelven a un archivo que existe. [...] 4. Los bloques Mermaid siguen siendo sintácticamente válidos y están completos. [...] 7. El total de líneas de `docs/` más `README.md` es aproximadamente igual al del README original, más lo nuevo. Si perdiste contenido en el camino, se nota acá."

*Qué devolvió y qué se decidió:* exigir una verificación **ejecutable** en vez de una revisión por lectura fue lo que encontró los errores, y terminó agregando `scripts/` y `.githooks/` a la estructura del repositorio. El script valida enlaces contra archivo y ancla, busca texto duplicado entre archivos, cuenta bloques de código y compara volumen contra el original. Encontró dos errores propios que una lectura no habría detectado: un bloque YAML sin cerrar por un off-by-one al partir la sección 4, y una palabra borrada por el shell al interpretar backticks dentro de un heredoc. Más tarde detectó una frase idéntica en dos archivos y un enlace roto al mover una sección. El punto 7 confirmó que las 41 líneas del original ausentes en la estructura nueva eran todas ediciones deliberadas.

---

**Prompt 3** — *Claude Code · analizar un repositorio de referencia, y corregir el supuesto de alcance*

> "Explora el siguiente repositorio misproyectos/ai4devs/mobile-facephi y analiza ÚNICAMENTE cómo está estructurada su documentación. No modifiques ningún archivo, realiza solo análisis. [...] Identifica entre 3 y 5 brechas o puntos ciegos (información crítica del proyecto que la documentación actual NO explica o no deja clara [...])."
>
> *(y después, sobre la lista de adopciones que devolvió)* "pero mi proyecto no es solo backend, tambien va a tener un front que es la web de visualizacion, metricas y dashboard, y pensando a futura en ampliar eso a una app mobil"

*Qué devolvió y qué se decidió:* el análisis del repositorio ajeno —2.371 líneas de documentación contra seis archivos Kotlin, cuatro de ellos andamiaje— encontró brechas concretas y verificables: comandos de lint documentados que no existen porque el plugin no está instalado, cuatro skills sin frontmatter que por eso no se cargan, un command que abre con `-****---` y no parsea, y una sección de «gotchas» que describe un módulo y un endpoint inexistentes. El patrón de fondo es el mismo hallazgo de §1, Prompt 2: la documentación describe el estado deseado y nada marca la diferencia con el real.

La corrección humana que vino después es la más valiosa: la primera lista de adopciones optimizaba para un backend con un dashboard accesorio y **descartaba el contrato de UI por sobrecarga**. Con las tres superficies a la vista —web, móvil futura y la API como frontera— todo se reordenó. De ahí salieron `docs/convenciones-de-desarrollo.md`, `docs/features/TEMPLATE/`, `scripts/verify_architecture.py` y `docs/hoja-de-ruta.md`. La IA no se equivocó razonando: partió de un supuesto incompleto que sólo la autora podía corregir.

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

**Prompt 2** — *Claude Code · modelo de amenazas de solo lectura, y cierre de las decisiones de login*

> "Actuá como Senior Application Security Engineer (AppSec) con experiencia en fintech de consumo y en equipos muy chicos. Tu criterio prioriza controles de alto impacto y bajo costo operativo por sobre defensas exhaustivas que una sola persona no puede mantener. Pensás como atacante, pero entregás mitigaciones concretas. [...] Esta tarea es de SOLO LECTURA. [...] NUNCA reproduzcas el valor de un secreto, token o credencial. [...] Priorizá controles que una sola persona pueda implementar y operar."
>
> *(y más adelante, sobre la recomendación de un dominio propio)* "este proyecto en un mvp, particular por ahora, no se si se justifica un dominio propio, a menos que los haya gratis y se justifique"
>
> *(y sobre las decisiones que quedaban abiertas)* "esas deciciones son criticas? o que queda por definir super critico?"

*(prompt completo: ~130 líneas con rol, contexto, modo de trabajo, objetivo en dos fases, restricciones, formato de salida y criterio de calidad)*

*Qué devolvió y qué se decidió:* sin código todavía, el modelo de amenazas se armó sobre la especificación: diagrama de flujo de datos con límites de confianza, STRIDE sobre cada flujo que los cruza, casos de abuso y un plan de diez ítems. No encontró secretos en los commits del proyecto; en el historial heredado del repositorio del curso solo había valores de ejemplo. Ningún riesgo quedó en "Crítico". Tres hallazgos cambiaron la especificación:

- **El JWT de 15 minutos no se podía revocar.** Cerrar sesión o pedir el borrado de la cuenta no cortaba un token ya emitido, y el cliente no tenía dónde guardarlo sin exponerlo.
- **El límite de pedidos de código delataba a los usuarios.** Se calculaba contando los códigos del usuario, así que solo un número registrado podía llegar al `429`.
- **El código de borrado no protegía lo que decía proteger.** La especificación lo justificaba contra quien tiene el teléfono en la mano, pero el código llega a ese mismo teléfono.

Salieron dos ADR. El [0016](docs/adr/0016-sesion-de-servidor-en-el-mismo-origen.md) reemplaza al 0003: el código se canjea por una sesión en la base, en una cookie que ningún script puede leer, y la API sirve también el dashboard para que la cookie funcione sin dominio propio. El [0017](docs/adr/0017-limites-del-login-y-codigos-con-proposito.md) cuenta los límites del login por número y por IP, exista o no el usuario, y ata cada código a su propósito.

Lo que queda por decidir antes de abrir a usuarios reales pasó a la [hoja de ruta](docs/hoja-de-ruta.md): qué hacer ante la toma de cuenta por el número, el abuso del tope del LLM, el registro de eventos de seguridad y las obligaciones legales de los datos. La autora confirmó además dos supuestos del análisis: el primer lanzamiento no tiene usuarios fuera de Argentina, y la app móvil no tiene fecha.

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

**Prompt 4** — *Claude Code · diseño de la capa de datos de solo lectura, y cierre de las divergencias*

> "Actuá como Lead Database Architect especializado/a en modelado de datos para sistemas financieros construidos y operados por equipos muy chicos. Tu criterio prioriza, en este orden: corrección e integridad de los datos, trazabilidad, simplicidad operativa, y recién después rendimiento. [...] Esta tarea es de SOLO LECTURA. [...] Cada afirmación sobre el estado actual cita su ruta de archivo. Lo deducido se marca [INFERIDO]."
>
> *(y más adelante, sobre la propuesta de guardar el historial completo de cada movimiento)* "esta pregunta "¿Cuánto había gastado el presupuesto familiar el 15?" se deberia poder responder sin tener un historial, la funcionalidad general de este proyecto es un registro de gastos, no entiendo como solo se puede responder teniendo un historial"

*(prompt completo: ~100 líneas con rol, contexto, modo de trabajo, objetivo en dos fases, restricciones, formato de salida y criterio de calidad)*

*Qué devolvió y qué se decidió:* sin código todavía, el diseño se hizo sobre la especificación. Confirmó PostgreSQL como motor y encontró seis divergencias entre documentos de `docs/`. **La regla de retención borraba el teléfono de los mensajes, pero el modelo lo declaraba obligatorio.** **La conversión a la moneda del presupuesto no guardaba qué cotización se usó.** **Un pendiente no podía convertirse en transferencia ni en compra con tarjeta.** Faltaban además la zona horaria del usuario, un registro de las correcciones y la moneda en el índice de duplicados. Las seis se resolvieron con decisiones de la autora.

La sesión siguió con las recomendaciones de diseño, presentadas de a una y ordenadas por criticidad. Se aplicaron:

- tipos exactos para montos, instantes y monedas, con un catálogo `CURRENCY`;
- la tabla `app_user`;
- claves foráneas que incluyen `user_id`, para que un movimiento no pueda usar la cuenta de otro usuario;
- idempotencia en `POST /transactions`;
- migraciones en un único paso del despliegue;
- nombres de cuenta únicos;
- reglas para las respuestas citadas y para los recurrentes.

Las de menor impacto pasaron a la [hoja de ruta](docs/hoja-de-ruta.md). Salieron dos ADR: el [0014](docs/adr/0014-marca-de-edicion-en-movimientos.md) (las correcciones se marcan con cuándo y quién) y el [0015](docs/adr/0015-borrado-logico-de-movimientos.md) (borrar un movimiento es marcarlo).

La corrección citada arriba muestra el ajuste más importante de la sesión. La IA propuso guardar el historial completo de cada movimiento en una tabla llenada por un trigger, con el argumento de que sin él no se podía saber cuánto se había gastado en una fecha pasada. La autora señaló que eso se responde con los datos actuales. Lo que solo un historial resuelve es qué mostraba el sistema antes de una corrección, y esa es una pregunta de auditoría contable, no de un registro de gastos. El ADR 0014 quedó reducido a dos columnas, `updated_at` y `updated_by`, y el historial pasó a ser una ampliación posible, no una obligación.

---

## 4. Especificación de la API

*Los tres endpoints principales (`POST /webhook/whatsapp`, `GET /budgets/{budget_id}`, `POST /transactions`) se derivaron de las decisiones de modelo de datos de §3, no de un prompt independiente. El diagnóstico arquitectónico de §2.2 (Prompt 3) sumó siete operaciones más, hasta llegar a diez: la verificación del webhook que exige Meta (`GET /webhook/whatsapp`), el login (`POST /auth/code`, `POST /auth/token`), la exportación de un grupo familiar y los derechos de acceso y supresión (`GET /me/export`, `POST` y `DELETE /me/deletion`). La plantilla pide tres; se documentan todas porque forman parte del alcance comprometido y un contrato incompleto sería justamente la divergencia entre documentación y código que se quiere evitar. El contrato OpenAPI completo se genera desde el código en la Entrega 2 — patrón tomado de la auditoría de repos de referencia (§1, Prompt 2), que identificó los ERD y árboles de carpetas generados **a partir del código real** como marcador de una entrega sólida.*

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
| 13 | Descartar el contrato de UI por «sobrecarga para tu escala» | Supuesto incompleto: el proyecto tiene frontend y una app móvil prevista. Pasó de descartado a prioridad |
| 14 | Ubicar `/spec-drift` después del commit | Encontrar la divergencia ahí implica haber commiteado código incorrecto. Se movió antes del último commit del corte |
| 15 | Escribir toda una convención sobre «vertical slices» sin definir el término | Se renombró a «corte vertical», por la regla de idioma, y se antepuso la definición |
| 16 | Nombrar los commands en español (`regla`, `estado`, `divergencia`) | Los nombres de archivo de código van en inglés. Renombrados a `domain-rules`, `ui-states` y `spec-drift` |
| 17 | Aplicar el módulo 5 tal cual: MADR, `log4brains` y nombres de ADR con fecha | Se contrastó contra `docs/` antes de ejecutar. Los ADR existentes ya tenían lo único que MADR aporta, y la fecha rompía la referencia corta `NNNN` usada en cinco lugares. Descartado en el ADR 0006 |
| 18 | Recomendar mantener `AGENTS.md` y `CLAUDE.md` separados | La autora priorizó tener una sola fuente por encima de conservar un contrato corto que se lea entero. Se fusionó con enlace simbólico, asumiendo el costo en el ADR 0007 |
| 19 | Recomendar diferir el portal de documentación a la Entrega 2 | La autora priorizó tener la documentación publicada y visible. Se montó Starlight, asumiendo la entrada de Node antes de decidir el stack del dashboard (ADR 0008) |
| 20 | Dar por buenas las recetas del módulo 5 sin probarlas | Dos fallaron en el spike: Astro no reescribe los enlaces `.md` que llevan ancla, y un bloque HTML en Markdown termina en la primera línea en blanco, lo que partía los diagramas. Se detectaron construyendo, no leyendo |
| 21 | Un solo pendiente abierto por usuario, para que la respuesta no fuera ambigua | Con la carga por email entran varios gastos juntos. Se separó cuántos pendientes existen de sobre cuál se pregunta: lotes numerados, con uno solo en conversación |
| 22 | Si la moneda no coincide con la de la cuenta, el asistente no convierte: pregunta | Fricción innecesaria. El asistente convierte con la cotización y pide confirmar el valor, como con cualquier monto |
| 23 | Un adaptador de cotizaciones por país | Sumar un país tiene que costar configuración, no código. Un adaptador genérico con fuentes en YAML (ADR 0011) |
| 24 | Imputar el gasto con tarjeta al presupuesto de la fecha de compra, como YNAB y Actual Budget | La autora piensa el presupuesto como flujo de caja: cada cuota pesa en el mes en que vence. Obligó a modelar la compra como una regla que genera cuotas (ADR 0012) |
| 25 | Un plazo fijo de 30 días para borrar el texto de los mensajes | Configurable en YAML y con 60 días por defecto, para tener margen al afinar la interpretación |
| 26 | Una tabla con la regla de cuotas que, al escribirla, no tenía la columna necesaria | La IA lo detectó al revisar su propio texto antes de mostrarlo. Otros dos errores de la sesión los encontró la verificación ejecutable, no la lectura: un chequeo que tardaba 111 segundos y una prueba de detección mal armada |
| 27 | Guardar el historial completo de cada movimiento, argumentando que sin él no se podía saber cuánto se había gastado en una fecha | Eso se responde con los datos actuales; el historial solo resuelve qué mostraba el sistema antes de una corrección, que es auditoría contable. Se redujo a `updated_at` y `updated_by` (ADR 0014) |
| 28 | Ilustrar el problema de las correcciones con "el 2 fueron 3800", que es una corrección dentro de un lote de pendientes | La autora notó que el problema solo existe si el movimiento ya está confirmado. El ejemplo era de la etapa previa, donde nadie más lo ve ni pesa en ningún saldo |
| 29 | Una regla para un caso casi imposible: el worker se cae entre enviar un mensaje y guardar su id | La autora dudó de que aplicara. Al revisarlo apareció el caso frecuente, citar una confirmación o una alerta, y la regla se generalizó a "si el mensaje citado no es pregunta de un lote abierto, se procesa como si no citara nada" |
| 30 | Interpretar "bueno esta bien asi" como no aplicar la solución propuesta | La autora quería aplicarla. Ante una respuesta ambigua, la IA eligió una interpretación en vez de preguntar |
| 31 | Un dominio propio como condición para que la cookie de sesión funcione | La autora cuestionó el costo en un MVP sin usuarios. La IA buscó una alternativa sin costo: la API sirve también el dashboard, en el mismo origen (ADR 0016). El dominio quedó para antes de abrir a usuarios reales, como defensa contra el phishing |
| 32 | Un plan de remediación con varios riesgos "Altos", sin decir cuándo había que resolver cada uno | La autora preguntó si algo era crítico. Nada lo era: sin usuarios, no había nada expuesto. Se reordenó por cuándo conviene resolver cada cosa. Lo que cambiaba el esquema antes de programar el login se resolvió en el ADR 0017; el resto pasó a la hoja de ruta |

El patrón que se repite: la IA tiende a **resolver la ambigüedad por su cuenta** eligiendo un valor por defecto razonable, y a **justificar decisiones técnicas por el esfuerzo** que ahorran en vez de por sus propiedades de diseño. Las dos cosas hay que detectarlas leyendo, porque el resultado siempre suena defendible.

En la fase de reestructuración aparece un patrón distinto, propio de trabajar con la IA sobre archivos en vez de sobre texto en un chat: los errores dejan de ser de criterio y pasan a ser **mecánicos y silenciosos** —un bloque de código sin cerrar, una palabra que se come el shell—. No se detectan leyendo el resultado, porque el archivo sigue pareciendo correcto. Se detectan ejecutando una verificación. De ahí que la lista de comprobaciones vaya dentro del prompt y no después.

En la fase de diseño de datos aparece un tercer patrón: la IA **sobredimensiona la solución con un argumento que suena riguroso** —trazabilidad, auditoría, casos de borde—. La pregunta que lo desarma es para qué sirve en este producto: la mitad de lo que justificaba el historial completo se resolvía con los datos que ya había.

En el modelo de amenazas el mismo patrón toma otra forma: la IA propone **el control estándar de la industria** sin pesar la etapa del producto, y **califica los riesgos sin decir cuándo importan**. Un dominio propio y un riesgo "Alto" son correctos en abstracto. Las preguntas que los ubican son qué protegen hoy, sin usuarios, y qué cuesta más hacer después.

---

## Pendiente para las próximas entregas

- ~~Configurar y versionar `CLAUDE.md`~~ — hecho al cierre de la Entrega 1, junto con `AGENTS.md`, tres commands y un hook de pre-commit. `CLAUDE.md` pasó después a ser un enlace simbólico a `AGENTS.md`.
- ~~Montar el sistema de documentación viva del módulo 5~~ — hecho al cierre de la Entrega 1: portal, integración continua, `llms.txt` y cuatro ADR. Descrito en [documentación viva](docs/documentacion-viva.md).
- ~~Comprobar en un navegador real que los diagramas del portal se renderizan~~ — verificado sobre el sitio publicado al cierre de la Entrega 1.
- Revisar el MCP de GitHub, que falla al conectar por un error de header de autorización. Quedó desactivado al cierre de la Entrega 1; hay que reautenticarlo antes de usarlo para los pull requests.
- Registrar los prompts de código, tests y despliegue a medida que se escriben, no al cierre.
- Verificar la sincronización entre la documentación (`docs/02-arquitectura.md` §2.3, `docs/03-modelo-de-datos.md`, `docs/04-api.md`) y el código real antes de cada entrega, aplicando la regla de precedencia de `AGENTS.md` §10: la especificación manda, lo que se corrige es el código.

Lo que depende de que exista código —el cliente generado desde el OpenAPI, el verificador del contrato de API, los tokens del Design System, los comandos de tests y linters, y los hooks y subagentes— está en la [hoja de ruta](docs/hoja-de-ruta.md).
