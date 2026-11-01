# Hoja de ruta

Qué queda por hacer, cuándo se desbloquea y por qué importa. No es una lista de deseos: cada
punto salió de una decisión ya tomada y documentada, y está acá porque **depende de que exista
código** y no se puede adelantar sin inventar.

Los pendientes del registro de uso de IA —qué prompts falta documentar, el MCP de GitHub— viven
en [`prompts.md`](../prompts.md), no acá.

## Alcance de la entrega 2

Qué se construye en la entrega 2 y qué queda para la entrega final. WhatsApp sigue siendo el
canal del producto: en esta entrega el flujo conversacional se construye y se muestra por el
chat web, que es un andamio ([ADR 0002](adr/0002-whatsapp-como-canal-principal.md)). Los consejos
con RAG son parte del producto y llegan en la entrega final; por eso algunas de sus piezas
quedan puestas desde ahora.

El proveedor de LLM ya está elegido: GPT-5.4 mini, de OpenAI
([ADR 0025](adr/0025-gpt-5-4-mini-como-modelo-de-lenguaje.md)). El de embeddings se elige
antes de la rama de consejos, con la evaluación del
[ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md).

| Entra en la entrega 2 | Dónde está la regla |
|---|---|
| Chat web dentro del dashboard, por el mismo camino asíncrono que WhatsApp | [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md), [la API](04-api.md) |
| Entrada de desarrollo en `local`, que abre una sesión real sin código: se elige un usuario de prueba | [ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md) |
| Registro de gastos e ingresos con toda su conversación: lo que se resuelve solo a la vista, preguntar lo que falta, el pendiente y su continuación, y categoría nueva con confirmación | [Reglas de dominio § 1, § 4 y § 5](reglas-de-dominio.md) |
| Pantalla de cuentas con el saldo calculado, donde se ve el efecto de cada movimiento | [Reglas de dominio § 2](reglas-de-dominio.md#2-cuentas-y-saldo-calculado), `GET /accounts` |
| El paso de clasificación con las tres clases de mensaje, el tope diario total y las tres cuotas | [ADR 0018](adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md) |
| Desde la primera migración, la extensión pgvector; desde la migración del esquema, la columna del mensaje citado. El puerto de LLM, desde el primer caso de uso que lo usa; los de embeddings y de vector store, con la rama de consejos | [ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md), [3. Modelo de datos](03-modelo-de-datos.md) |
| Docker Compose que levanta la base, las migraciones, la API y el worker con un comando, y el pipeline de seis controles, cinco desde el primer commit de código y el análisis de seguridad después | [ADR 0021](adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md) |
| La tabla de llamadas al modelo con su envoltorio y el script de métricas, los registros en JSON con su filtro y su test, los eventos de seguridad y las tres rutas de salud | [ADR 0023](adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md) |
| Datos de prueba: una plantilla de usuario con el alta completa, cuentas, su primer período confirmado y perfil financiero. En `local` el script de datos de prueba crea varios usuarios con ella, con el consentimiento registrado y al menos uno con un grupo | [Reglas de dominio § 3 y § 11](reglas-de-dominio.md) |

Cuáles de estos tramos entran en la entrega final y cuáles pasan a una segunda versión lo dice
la [línea de corte de la entrega final](#alcance-de-la-entrega-final).

| Queda fuera de la entrega 2 | Por qué |
|---|---|
| El adaptador de WhatsApp, el login por código, los números habilitados y el alta conversacional | Dependen del canal real. El procesamiento ya queda probado por el chat web |
| Preguntas sobre los propios datos y consejos con RAG, con la carga de la base de conocimiento y sus dos tablas | Son ramas aparte de la clasificación. La de consejos espera al modelo de embeddings |
| Un gasto en otra moneda, reintegros vinculados, retiro y aporte del titular, y el aviso de duplicado entre miembros | Cada uno es un flujo con sus propios casos de error |
| Transferencias, compras con tarjeta y reglas recurrentes | Las dos últimas dependen de los procesos programados |
| Procesos programados: vencimiento y recordatorio de pendientes, alertas, recurrentes, cierres de resumen, cotizaciones | En la entrega 2 un pendiente sin responder queda abierto |
| Varios movimientos en un mensaje, con respuestas por número, y elegir entre el presupuesto individual y el de un grupo | Son los dos últimos tramos de la conversación del registro ([reglas de dominio § 1 y § 5](reglas-de-dominio.md)). Se pasaron el 13 de octubre de 2026, porque la entrega 2 vence el 22 |
| Corregir, borrar y restaurar un movimiento confirmado, con el botón de responder un mensaje | Es un flujo aparte, que parte de un movimiento ya registrado ([reglas de dominio § 15](reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado)). Se pasó en la misma fecha |
| El entorno `demo` y su despliegue: la entrada con un enlace personal, para que otra persona pueda probar siendo dueña de sus datos, los dos comandos que crean y regeneran el enlace, la pantalla del aviso de prueba y el usuario de prueba de cada persona | El proveedor y el plan siguen sin decidir, y la entrega 2 se prueba en `local` ([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)). Se pasó en la misma fecha |
| La sección "Me deben" de la pantalla de cuentas, con cada persona y lo que debe | La pide [reglas de dominio § 16](reglas-de-dominio.md#16-reintegros-devoluciones-y-plata-que-te-deben). Las cuentas "Me deben" se crean al registrar un préstamo, que llega en la entrega final, así que en la entrega 2 la sección estaría siempre vacía. Mientras tanto la pantalla no las lista. Se decidió el 14 de octubre de 2026 |
| Que la entrada de desarrollo avise cuando el navegador no guarda la sesión, en vez de volver a la lista sin decir nada | La cookie de la sesión es `Secure`, y sobre `http` en la propia máquina Safari no la guarda: la sesión se abre, el siguiente pedido llega sin ella, y la persona no sabe por qué no entró. El README ya avisa qué navegadores usar. Se decidió el 14 de octubre de 2026 |
| La pantalla de presupuesto y `GET /budgets/{budget_id}`, y los formularios de carga del dashboard | La pantalla de cuentas ya muestra el efecto de un gasto. El reparto por ticket está en [6. Tickets](06-tickets.md) |

**Un pendiente a la vez en la entrega 2.** Las [reglas de dominio § 5](reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración)
suman al lote que espera respuesta un movimiento nuevo que llega mientras tanto, y reenvían la
lista numerada. En la entrega 2 un lote tiene un solo pendiente: con uno esperando respuesta, el
asistente pide terminar el anterior y no anota el nuevo
([FEAT-003](features/FEAT-003/spec.md), CA-36). Sumarlo al lote llega con los varios
movimientos en un mensaje, en la entrega final.

**Lo que el asistente todavía no sabe hacer responde un texto fijo.** La clasificación reconoce las tres
clases y todos los tipos de registro desde el inicio. Cuando el mensaje pide algo de la segunda
tabla, el asistente no llama al modelo otra vez ni cobra cuota:

- Un registro que no es un gasto ni un ingreso: "Eso todavía no lo sé anotar. Por ahora me
  manejo con gastos e ingresos."
- Una consulta o un consejo: "Todavía no sé responder preguntas. Por ahora anoto gastos e
  ingresos, y tus saldos los ves en el dashboard."

**Si el tiempo no alcanza, se cae lo último de esta lista y no lo primero:** el camino feliz de
un gasto y de un ingreso con la pantalla de cuentas; y los pendientes y la categoría nueva.

## Alcance de la entrega final

Decidido el 15 de octubre de 2026, a partir de la devolución de la entrega 1. El núcleo es el
registro conversacional con confirmación, las cuentas con su saldo, el presupuesto y el
dashboard, todo por el chat web. WhatsApp no entra: el chat web recorre el mismo camino
([ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md)), y el canal real depende de la
configuración de Meta, que no suma a lo que se evalúa.

| Entra en la entrega final, además de la entrega 2 | Dónde está la regla |
|---|---|
| El entorno `demo` desplegado, con el enlace personal de cada persona y el aviso de prueba | [ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md) |
| La pantalla de presupuesto: el resumen del período con cada categoría con tope y las sin tope que tuvieron movimientos, el detalle de una categoría con sus movimientos, y un selector que abre el período que cubre hoy. Sale de `GET /budget-periods/{period_id}/summary`, `GET /budgets/{budget_id}` y la lectura de `GET /budget-periods`, que se adelanta de la HU2. Decidido el 24 de octubre de 2026, porque sin el resumen la pantalla mostraba una sola categoría y no tenía de dónde sacar su id | [HU4](05-historias-de-usuario.md), [la API](04-api.md) |
| Armar y confirmar el presupuesto de un período individual desde el dashboard: cadencia, día de inicio, ingreso estimado y tope por categoría, en borrador hasta confirmarlo | [HU2](05-historias-de-usuario.md), [reglas de dominio § 3](reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio), [la API](04-api.md) |
| Varios movimientos en un mensaje, con respuestas por número | [Reglas de dominio § 1 y § 5](reglas-de-dominio.md) |
| Corregir, borrar y restaurar un movimiento confirmado, con el botón de responder un mensaje | [Reglas de dominio § 15](reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado) |
| Preguntas sobre los propios datos | [Reglas de dominio § 17](reglas-de-dominio.md#17-preguntas-sobre-los-propios-datos) |

**Si el tiempo no alcanza, se cae lo último de esa tabla y no lo primero.** Las preguntas sobre
los propios datos van al final. De la HU2 quedan afuera el borrador que se arma solo y el
recordatorio antes del inicio, que son procesos programados, y los montos recurrentes.

**Crear una categoría desde el dashboard entra si queda tiempo.** Una categoría se va a poder crear
de dos formas: conversando con Platita, como hoy, y desde el dashboard, al armar un período. Lo
segundo necesita un endpoint nuevo y va después de terminar la HU2. Decidido por Vero el 1 de
noviembre de 2026.

Pasa a una segunda versión, con su diseño ya escrito en `docs/`: el adaptador de WhatsApp, el
login por código, los números habilitados y el alta conversacional; los consejos con RAG y la
base de conocimiento; los grupos familiares y la elección entre el presupuesto individual y el
de un grupo; la multimoneda, los reintegros, las transferencias, las compras con tarjeta y las
reglas recurrentes; los procesos programados, entre ellos las alertas y el vencimiento de los
pendientes; y la sección "Me deben".

El entorno `demo` llega en la entrega final. Se despliega desde la rama de la entrega y hace de
entorno de pruebas: cada persona que prueba tiene su usuario y su enlace. Dónde se aloja depende
de la decisión abierta sobre el proveedor y el plan. En la entrega 2 Platita se prueba en `local`.

## Entrega 2

| Qué | Se desbloquea cuando | Por qué importa |
|---|---|---|
| Documentar los tokens del Design System aparte de los componentes | Haya diseño del dashboard | Para que la app móvil los reutilice en vez de reconstruirlos leyendo código. Hoy viven en `frontend/src/design-tokens.css` ([ADR 0026](adr/0026-react-typescript-y-vite-para-el-dashboard.md)), sin un documento propio |
| Revisar que la redirección de `/app` a `/app/` salga con `https` detrás del proxy del proveedor | Haya un primer despliegue | El servidor arma esa dirección desde el pedido que recibe. Si no confía en los headers del proxy, puede salir con `http` |
| Rellenar el [`ui_contract.md`](features/TEMPLATE/ui_contract.md) de la entrada de desarrollo y del estado del sistema | La entrega final | Las pantallas de cuentas y del chat ya tienen el suyo |
| El hook que corre los tests unitarios después de cada edición del asistente en `backend/` | Exista el scaffold | Avisa enseguida si una edición rompió algo. Informa y no bloquea, porque en la fase en rojo los tests fallan a propósito ([ADR 0024](adr/0024-tests-primero-en-el-backend.md)) |
| Que un error que no pasa por los registros tampoco salga crudo: uno que ocurre antes de configurar el filtro, uno en un hilo propio, y los del servicio de migraciones | Exista el worker | Hoy esos errores salen como texto por la salida de errores, con el host y el usuario de la base, sin la contraseña. El worker es el primer proceso con hilos propios y con datos de usuarios |
| El puerto de LLM, y después los de embeddings y de vector store | Se escriba el primer caso de uso que usa cada uno: el registro de un gasto y la rama de consejos | El scaffold no los trae: su forma depende de los casos de uso, y declararlos antes sería adivinarla ([ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md)) |
| `scripts/llm_metrics.sql` | Exista la tabla `LLM_CALL` | Las cuatro métricas del [ADR 0023](adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md). Sin la tabla no hay contra qué probar las consultas |
| Sentry, el monitor externo y las dos alertas críticas | Haya un primer despliegue | Al sumar Sentry se verifican en su sitio el plan y la retención, y se completa la fila de [términos y privacidad](terminos-y-privacidad.md) |
| Correr `/security-audit` | Exista el backend, y antes de cada entrega | Audita el código contra las dos listas de OWASP. El cruce de diseño ya está en [seguridad de la capa de IA](seguridad-llm.md) |
| Publicar la referencia de la API en el portal | Corra FastAPI | El OpenAPI lo genera el framework; falta exponerlo como consola navegable y enlazarlo desde [`llms.txt`](../llms.txt), que hoy no puede describir endpoints que no existen |
| Documentación del código, con docstrings y su generador | Exista el backend | Es la capa que falta de las cuatro de [documentación viva](documentacion-viva.md#1-las-cuatro-capas). El equivalente en Python de lo que el módulo 5 propone con TypeDoc |
| Verificar las copias de respaldo del plan de base de datos: cuántos días retiene y si permite restaurar a un punto en el tiempo | Se contrate el plan de PostgreSQL en Render | Los datos de una cuenta borrada siguen en las copias hasta que vencen, y la política de privacidad tiene que decir cuánto tardan ([términos y privacidad](terminos-y-privacidad.md)). Restaurar a un punto en el tiempo es lo que permite volver atrás si una migración o un error rompen datos |
| Revisar los índices del [Ticket 3](06-tickets.md) contra las consultas reales | Haya datos y consultas medibles | `pending_transaction (batch_id)` sobra, porque lo cubre `UNIQUE (batch_id, position)`; los índices de saldo y de presupuesto conviene hacerlos parciales o que cubran las columnas que suman, contemplando `duplicate_of` y `deleted_at`; y el de duplicados sirve a una función que todavía no existe. Con pocos usuarios no se nota |
| Que la tarjeta de la entrada de desarrollo no se dibuje hasta saber que la entrada está encendida | Exista el entorno `demo`, con su pantalla del enlace personal | Hoy se oculta recién cuando la API responde que está apagada. Antes de eso se ve un instante mientras carga, queda como tarjeta de error si `GET /me` falla. Con una sesión abierta ya no se ve: el dashboard muestra el menú ([ADR 0027](adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md)). Hace falta que la API le diga al dashboard cómo está configurada |
| Que el campo `endpoint` de los registros conserve el prefijo de un router incluido con `prefix=` | Se incluya el primer router con prefijo | Hoy toda ruta se declara completa en `routes.py`. Con un prefijo dado al incluir, la línea `http.request` registraría la ruta sin él, y dejaría de ser "la ruta como está declarada" ([Operación 6.3](operacion.md#63-registros)) |
| Decidir si la referencia de la API, `/docs` y `/openapi.json`, queda abierta en `production` | Haya un primer despliegue | Hoy está abierta en todo entorno. No expone datos de nadie, pero sí qué endpoints existen. Lo habitual es apagarla en producción o dejarla solo en `local` y `demo` |
| Enviar el encabezado `Strict-Transport-Security` | Haya un primer despliegue | El control de origen compara sin el esquema, así que una página servida por `http` en el mismo dominio lo pasaría ([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)). En `local` no aplica: no hay `https` |
| Los dos comandos de operación del entorno `demo`, que crean y regeneran un enlace personal, y la pantalla del aviso de prueba, con su texto versionado | Se decida el proveedor, en la entrega final | Es lo que deja probar a alguien más sin que vea los datos de otro, y con su consentimiento registrado ([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)). Sin ellos, `demo` no tiene por dónde entrar |
| Sumar al verificador de arquitectura el nombre del SDK del proveedor de embeddings | Se elija ese proveedor | El dominio no conoce ninguna librería de IA ([ADR 0020](adr/0020-sin-framework-de-orquestacion-de-ia.md)), y el verificador solo frena las que tiene en su lista. El del LLM, `openai`, ya está |
| Revisar las dependencias que trae `langchain-text-splitters` y que ninguna envíe datos por su cuenta | Se instale, con la carga de la base de conocimiento | Lo pide el [ADR 0020](adr/0020-sin-framework-de-orquestacion-de-ia.md). Es para la entrega final |
| Política de acceso central y tests de aislamiento entre usuarios | Exista el scaffold | La regla ya está en la [API](04-api.md): el usuario sale de la sesión y un recurso ajeno responde `404`. Lo que falta es aplicarla en un solo lugar del dominio, incluida la visibilidad por intervalos de membresía de los grupos familiares y las respuestas por WhatsApp que citan un lote, y probarla en cada endpoint y en el worker. Implementada caso por caso, alguno se escapa |
| Que la API y el worker se conecten a la base con el rol `platita_app`, y solo las migraciones con el dueño de las tablas | Exista la migración del esquema, que crea el rol | Hoy Compose usa un solo usuario para todo, que puede eliminar filas. Mientras la aplicación no se conecte con su rol, la prohibición de `DELETE` del [ADR 0015](adr/0015-borrado-logico-de-movimientos.md) existe en la base pero no la protege |
| Topes de tamaño: el cuerpo de un pedido, el texto de un mensaje del chat, la carga inicial de la conversación y la salida del modelo | Haya un primer despliegue | Hoy la API lee el cuerpo entero antes de mirar la sesión y nada lo limita: un pedido de cientos de MB puede tumbar la instancia, y un mensaje enorme va entero al modelo. Lo encontró `/security-audit` el 19/10/2026 (A06 y LLM10). Dos de los topes cambian el contrato, así que primero va [4. API](04-api.md). El de la salida del modelo es parte del tope de tokens por mensaje que sigue en [decisiones abiertas](#decisiones-abiertas) |
| Fijar las dependencias indirectas del backend con sus hashes, y las imágenes base por digest | Haya un primer despliegue | Hoy cada build vuelve a resolver las dependencias indirectas, entre ellas el cliente HTTP del SDK del modelo, que corre con la clave del proveedor y ve el texto de los mensajes. Lo encontró `/security-audit` el 19/10/2026 (A03 y LLM03). Al hacerlo se actualiza la fila LLM03 de [seguridad de la capa de IA](seguridad-llm.md) |
| Cambiar la rama por defecto del fork al abrir la rama de la entrega final | Exista esa rama | El portal se publica desde ahí, si el entorno `github-pages` la tiene autorizada, Dependabot abre ahí sus pull requests, y los enlaces del portal a GitHub apuntan a la rama por defecto. En la entrega 2 ya se hizo. Detalle en [documentación viva](documentacion-viva.md#7-el-modelo-de-ramas) |
| Decidir si se guarda el día de inicio elegido de un ciclo mensual, para que un ciclo del 31 vuelva al 31 después de febrero | Llegue el borrador que se arma solo | Sin eso el inicio queda corrido: un período del 31 de enero termina el 27 de febrero, el siguiente empieza el 28 y desde ahí el ciclo sigue el 28 ([reglas de dominio § 3](reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)). Se aceptó así el 29 de octubre de 2026 |

## Más adelante — aplicación móvil

| Qué | Por qué es barato si se hace en orden |
|---|---|
| Reutilizar el contrato de UI y los tokens en la app nativa | La máquina de estados pertenece al contrato de la pantalla, no a la tecnología que la renderiza |
| Regenerar el cliente de API desde el mismo OpenAPI | Es la promesa que justifica la arquitectura hexagonal en el [ADR 0001](adr/0001-arquitectura-hexagonal.md): una app móvil que consume la misma API sin tocar lógica de negocio |
| Evaluar auditorías de seguridad específicas de móvil | Recién tiene sentido cuando exista superficie móvil que auditar |

## Decisiones abiertas

Las decisiones que salen de recorrer casos de usuarios reales sobre el diseño están en la última
corrida de la [validación por casos de uso](use-case-walkthrough.md#10-decisiones-pendientes-fase-3),
con sus opciones y una recomendación. Las de esta lista son las que no salieron de ahí.

- El grupo 9 (trazabilidad de origen) de [`reglas-de-dominio.md`](reglas-de-dominio.md) es un
  grupo de enlace, sin texto propio: su contenido normativo vive en el catálogo de
  funcionalidades de [1.2](01-producto.md#12-características-y-funcionalidades-principales) y no
  se duplicó. Darle texto propio exige escribir contenido nuevo, no reorganizar el existente. El
  grupo 6 (multimoneda) ya tiene texto propio.
- **Cuenta compartida de un grupo familiar: a futuro.** Un grupo podría tener una cuenta propia
  donde los miembros ponen plata para cubrir el presupuesto familiar. Hoy toda cuenta es de un
  usuario, y la base lo impone: un movimiento y su cuenta tienen el mismo `user_id`, y una
  transferencia solo une cuentas del mismo usuario ([3. Modelo de datos](03-modelo-de-datos.md#31-diagrama-del-modelo-de-datos)).
  Sumarlo exige que una cuenta pueda ser de un usuario o de un grupo, que un aporte sea una
  transferencia entre la cuenta de un miembro y la del grupo, y cambiar esas claves foráneas.
  Con esas mismas restricciones, el cambio es explícito y no aparece por accidente.
- **Devoluciones con tarjeta: limitación conocida, no bloqueante.** Lo que el banco acredita por
  una devolución o una reversión llega en la conciliación como un ajuste en "Devoluciones y
  reintegros" que no se vincula a la compra
  ([reglas de dominio § 13 y § 16](reglas-de-dominio.md#16-reintegros-devoluciones-y-plata-que-te-deben)).
  El total de la tarjeta queda bien, pero el gastado del rubro de la compra no baja y el ingreso
  del período sube. Si la compra era en cuotas, las restantes se siguen generando hasta que el
  usuario borra la regla, y cada conciliación las compensa. Resolverlo exige que un reintegro pueda
  apuntar a una compra con tarjeta, que es una regla y no un movimiento. Caso A1.4 y decisión D18
  de la [validación por casos de uso](use-case-walkthrough.md).
- **Varios intervalos de membresía en un grupo: mejora.** Quien sale de un grupo y vuelve reabre
  su única fila de `USER_GROUP`, y pierde el intervalo anterior: si vuelve a salir, solo conserva
  la lectura de los períodos de su último intervalo
  ([reglas de dominio § 10](reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad)).
  Guardar cada intervalo exige que la membresía tenga su propio id, en vez de la clave
  `(user_id, family_group_id)`, y que la regla de visibilidad recorra todos los intervalos.
- **Qué pasa cuando un recurrente o una cuota no se pueden generar.** Los casos previstos, sin
  período confirmado o con una cotización por confirmar, quedan como pendiente
  ([reglas de dominio § 8](reglas-de-dominio.md#8-movimientos-recurrentes-la-excepción-a-la-confirmación)).
  Falta definir qué pasa ante un error inesperado, por ejemplo una restricción de la base que
  rechaza el movimiento o una caída a mitad del proceso: si el proceso reintenta, si la regla se
  pausa, y qué se le avisa al usuario. Sin eso, el alquiler de un mes puede no registrarse sin que nadie se entere.
- **Qué recibe el usuario si el modelo se niega a responder: decidido el 17 de octubre de
  2026.** Una negativa del modelo recibe enseguida un texto fijo que pide escribirlo de otra
  forma, sin reintentar. Una respuesta que el proveedor corta se trata como un modelo caído y se
  reintenta ([FEAT-003](features/FEAT-003/spec.md), CA-40).
- **La documentación automática de la API: sin decidir.** El framework publica `/docs` y
  `/openapi.json` sin pedir sesión, en todos los entornos. Hoy solo describen las rutas de
  salud. Falta decidir si en `production` se apagan o piden sesión, antes de que describan los
  endpoints del producto. La referencia pública de la API tiene su propio punto en la lista de
  arriba.
- **Metadatos de los mensajes: sin plazo de borrado.** Pasado el plazo de retención se borran el
  texto y el teléfono de cada mensaje ([reglas de dominio § 14](reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos)),
  pero la fila con sus metadatos queda para siempre. Con pocos usuarios no pesa; se revisa cuando
  el volumen de mensajes lo justifique.
- **Términos y política de privacidad: sin redactar.** Bloquean abrir Platita a usuarios reales.
  El índice de lo que tienen que cubrir está en [términos y privacidad](terminos-y-privacidad.md).
- **Dominio propio: antes de abrir a usuarios reales.** Mientras tanto el dashboard se sirve desde
  un subdominio de `onrender.com`, que un usuario no distingue con facilidad de uno falso. No
  cambia la sesión ([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)).
- **Toma de cuenta por el número: sin decidir.** El teléfono es el único factor: quien controla el
  número de WhatsApp, por un cambio de SIM, un número que la operadora reasignó o un teléfono
  prestado, recibe el código y opera como el usuario. Falta decidir qué pasa si el usuario pierde
  su número, si se le avisa por WhatsApp cada ingreso al dashboard y cada exportación, si se pide
  un código reciente antes de exportar o de gestionar miembros, si se reverifica después de una
  inactividad larga, y si se ofrece un segundo factor que no dependa del teléfono, como una passkey.
  Es el riesgo más alto que queda del modelo de amenazas. Bloquea abrir a usuarios reales.
- **Abuso del tope del proveedor de LLM: acotado, con restos sin decidir.** Las cuotas son por
  usuario ([reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente)). Que
  varias cuentas creadas con números descartables agoten el tope global de 20 dólares ya no es
  posible sin pasar por quien opera Platita, porque solo escriben los números habilitados
  (§ 11), y cada usuario tiene además un tope diario total de mensajes clasificados. Falta
  decidir un tope de tokens por mensaje, cuotas menores para cuentas nuevas y una alerta de
  gasto diario antes de llegar al tope. El costo por día ya se puede leer de la tabla de
  llamadas al modelo ([ADR 0023](adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md)).
- **Qué responde el asistente ante lo que pasó a la entrega final: decidido en parte.** Los
  textos fijos de arriba cubren un registro que no es gasto ni ingreso, y una consulta o un
  consejo. Un mensaje con varios movimientos recibe el de un registro que no es gasto ni
  ingreso, decidido el 17 de octubre de 2026 ([FEAT-003](features/FEAT-003/spec.md), C2-35).
  Quedan para la entrega final un usuario con un período individual y uno de grupo para la misma
  fecha, y una respuesta que cita una confirmación para corregirla o borrarla.
- **La memoria de la clasificación: sin decidir.** El [ADR 0018](adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md),
  punto 9, dice que la clasificación recibe el último intercambio. El código le manda solo el
  mensaje y, si hay uno esperando respuesta, el estado del pendiente. Falta decidir si se suma
  el último intercambio o si se corrige el ADR porque el pendiente alcanza. Encontrado con el
  `/spec-drift` del corte 2 de FEAT-003, el 17 de octubre de 2026.
- **Proponer u ofrecer la cuenta: sin decidir.** Las [reglas de dominio § 1](reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)
  dicen que, para lo que requiere confirmación, el asistente propone lo más probable y el
  usuario confirma. [FEAT-003](features/FEAT-003/spec.md) ofrece las cuentas candidatas sin
  proponer una, que es una regla determinista (CA-19 y CA-20). Falta decidir cuál de las dos
  queda, y escribirlo en la otra.
- **Un movimiento roto bloquea todos los saldos: a revisar después de la entrega 2.** Si un
  movimiento en otra moneda llegara sin cotización, el cálculo se detiene y la pantalla de
  cuentas muestra el error, sin el saldo de ninguna cuenta (caso C2-12 de
  [FEAT-001](features/FEAT-001/spec.md)). Hoy no puede pasar, porque la base rechaza ese
  movimiento. Sigue la regla de que un saldo calculado no se muestra parcial
  ([convenciones de desarrollo § 2](convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla)),
  pero la autora duda de que una cuenta rota tenga que esconder las demás. La alternativa es
  mostrar las otras y marcar esa como no calculada, que exige cambiar esa regla.
- **Alta por el chat web: sin decidir.** El alta corre por el chat, igual en WhatsApp y en el
  chat web, desde el segundo paso. Pero para abrir el chat web hace falta una sesión, y una
  persona que todavía no es usuario no la tiene. Falta decidir cómo entra. La candidata es que el
  login del andamio deje pasar a un número habilitado, muestre los términos y, al aceptarlos,
  cree el usuario y la sesión. El modelo de datos sirve tanto para eso como para dejar el alta
  solo en WhatsApp. Se decide en la entrega final. El enlace personal del entorno de pruebas no
  lo resuelve: da una cuenta de prueba ya armada, sin pasar por el alta
  ([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)).
- **Deshabilitar el número de un usuario ya dado de alta: sin decidir.** Habilitar un número
  decide quién puede empezar un alta. Falta decidir qué pasa si se deshabilita el de alguien que
  ya usa Platita: si el asistente deja de responderle, si conserva el acceso al dashboard y qué
  se le avisa. Importa cuando el producto sea pago.
- **Pantalla de administración para habilitar números: mejora.** Hoy se habilita con un comando
  de operación, que solo puede correr quien tiene acceso al servidor. Una pantalla exige un rol
  de administrador que la especificación no tiene. El comando y la pantalla llamarían al mismo
  caso de uso, así que pasar de uno a otro no rehace nada.
- **La tasa de plazo fijo como dato descargado: a revisar.** Hoy los datos de mercado que
  Platita descarga son las cotizaciones, la inflación mensual y la tasa promedio de plazo fijo
  ([reglas de dominio § 18](reglas-de-dominio.md#18-alcance-de-los-consejos)). La autora duda de
  mantener la tercera. No afecta la entrega 2.
- **Cuotas en YAML versionado o ajustables sin desplegar: decidido el 18 de octubre de 2026.**
  Manda [reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente): el tope
  diario total y las cuotas se leen de variables de entorno, y se bajan reiniciando el proceso,
  sin desplegar. [2.5](02-arquitectura.md#25-seguridad) se corrigió
  ([FEAT-003](features/FEAT-003/spec.md), CA-46).
- **Registro de eventos de seguridad: definido en parte.** Dónde se registran, cómo se redactan
  y cuáles son los primeros eventos está en el [ADR 0023](adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md): pedidos y fallos de código,
  sesiones creadas, límites alcanzados, cuotas superadas y respuestas bloqueadas. Falta decidir
  si se suman las exportaciones, los pedidos de borrado y los cambios de miembros, y qué evento
  dispara una alerta a quien opera Platita. Se decide antes de abrir a usuarios reales.
- **Obligaciones legales de los datos: sin validar.** Además de los términos, falta confirmar con
  alguien con conocimiento legal la inscripción de la base ante la autoridad de aplicación de la
  Ley 25.326, la transferencia de datos al proveedor de alojamiento y al de LLM fuera del país, y
  que el alcance de los consejos, educación financiera que no elige instrumentos
  ([reglas de dominio § 18](reglas-de-dominio.md#18-alcance-de-los-consejos)), no se encuadre como
  asesoramiento de inversiones regulado. Bloquea abrir a usuarios reales.
- **Proveedor y plan de despliegue: sin decidir.** [Operación](operacion.md), en su parte
  todavía propuesta, plantea Render en su
  plan pago más chico, por unos US$23 a 25 por mes, con una copia diaria cifrada fuera de Render.
  La alternativa es un servidor virtual único por unos US$6, que suma a quien opera parchear el
  sistema, administrar PostgreSQL y montar las copias. Hay que decidir cuánto vale no operar un
  servidor.
- **Pérdida de datos y tiempo de recuperación aceptados: sin decidir.** La propuesta pierde
  minutos ante un error y hasta 24 horas si se pierde la cuenta del proveedor, y se recupera en
  una a cuatro horas. Define la frecuencia de las copias y si alcanza el plan de base más chico.
- **Quién genera las alertas proactivas: divergencia.** Las alertas usan el motor RAG, pero en el
  diagrama de [2.4](02-arquitectura.md#24-infraestructura-y-despliegue) los procesos programados
  no llegan al LLM, y solo el worker lo hace. O las genera el worker, o al diagrama le falta esa
  conexión. Toca a la rama de consejos: el consejo de una alerta sale de la base de conocimiento.
  Hay que decidirla antes de escribir esa rama.
- **Un cron o uno por tarea: sin decidir.** [2.4](02-arquitectura.md#24-infraestructura-y-despliegue)
  habla de procesos programados separados del servicio web, sin decir cuántos.
  [Operación](operacion.md) propone uno solo que despacha las tareas vencidas, porque cada cron
  cuesta aparte; a cambio, una tarea que se cuelga demora a las demás hasta que vence su tiempo.
