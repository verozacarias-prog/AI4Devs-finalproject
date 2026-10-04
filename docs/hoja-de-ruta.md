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

**Antes de escribir código** se elige el proveedor de LLM, con la evaluación del
[ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md). El de embeddings
se elige antes de la rama de consejos.

| Entra en la entrega 2 | Dónde está la regla |
|---|---|
| Chat web dentro del dashboard, por el mismo camino asíncrono que WhatsApp | [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md), [la API](04-api.md) |
| Entrada de desarrollo: se elige un usuario de prueba y se abre una sesión real, sin código | [ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md) |
| Registro de gastos e ingresos con toda su conversación: lo que se resuelve solo a la vista, preguntar lo que falta, el pendiente y su continuación, varios en un mensaje con respuestas por número, categoría nueva con confirmación, y elegir entre el presupuesto individual y el de un grupo | [Reglas de dominio § 1, § 4 y § 5](reglas-de-dominio.md) |
| Corregir, borrar y restaurar un movimiento confirmado, con el botón de responder un mensaje | [Reglas de dominio § 15](reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado) |
| Pantalla de cuentas con el saldo calculado, donde se ve el efecto de cada movimiento | [Reglas de dominio § 2](reglas-de-dominio.md#2-cuentas-y-saldo-calculado), `GET /accounts` |
| El paso de clasificación con las tres clases de mensaje, el tope diario total y las tres cuotas | [ADR 0018](adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md) |
| Desde la primera migración: la extensión pgvector y la columna del mensaje citado. Desde el primer commit del dominio: los puertos de LLM, de embeddings y de vector store | [ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md), [3. Modelo de datos](03-modelo-de-datos.md) |
| Datos de prueba: usuarios con el alta completa, consentimiento registrado, cuentas, su primer período confirmado y perfil financiero, y al menos uno con un grupo | [Reglas de dominio § 3 y § 11](reglas-de-dominio.md) |

| Queda para la entrega final | Por qué |
|---|---|
| El adaptador de WhatsApp, el login por código, los números habilitados y el alta conversacional | Dependen del canal real. El procesamiento ya queda probado por el chat web |
| Preguntas sobre los propios datos y consejos con RAG, con la carga de la base de conocimiento y sus dos tablas | Son ramas aparte de la clasificación. La de consejos espera al modelo de embeddings |
| Un gasto en otra moneda, reintegros vinculados, retiro y aporte del titular, y el aviso de duplicado entre miembros | Cada uno es un flujo con sus propios casos de error |
| Transferencias, compras con tarjeta y reglas recurrentes | Las dos últimas dependen de los procesos programados |
| Procesos programados: vencimiento y recordatorio de pendientes, alertas, recurrentes, cierres de resumen, cotizaciones | En la entrega 2 un pendiente sin responder queda abierto |
| La pantalla de presupuesto y `GET /budgets/{budget_id}`, y los formularios de carga del dashboard | La pantalla de cuentas ya muestra el efecto de un gasto. El reparto por ticket está en [6. Tickets](06-tickets.md) |

**Lo que todavía no tiene código responde un texto fijo.** La clasificación reconoce las tres
clases y todos los tipos de registro desde el inicio. Cuando el mensaje pide algo de la segunda
tabla, el asistente no llama al modelo otra vez ni cobra cuota:

- Un registro que no es un gasto ni un ingreso: "Todavía no puedo registrar eso. Por ahora
  registro gastos e ingresos."
- Una consulta o un consejo: "Todavía no puedo responder preguntas. Por ahora registro gastos e
  ingresos, y tus saldos están en el dashboard."

**Si el tiempo no alcanza, se cae lo último de esta lista y no lo primero:** el camino feliz de
un gasto y de un ingreso con la pantalla de cuentas; los pendientes y la categoría nueva; varios
movimientos en un mensaje; el presupuesto de un grupo; y corregir, borrar y restaurar.

El entorno de demostración se despliega con datos inventados. Dónde, depende de la decisión
abierta sobre el proveedor y el plan.

## Entrega 2

| Qué | Se desbloquea cuando | Por qué importa |
|---|---|---|
| Evaluación del proveedor de LLM: unos 20 casos de la [validación por casos de uso](use-case-walkthrough.md) y casos de inyección de prompts, contra dos candidatos | Ya se puede hacer: no necesita código del producto | Sin un proveedor elegido no se puede interpretar un gasto. Mide calidad en español rioplatense, costo y latencia, con el filtro de privacidad del [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), si clasificar, extraer y pedir datos en una sola llamada baja la calidad, y si hace bien las cuentas de una respuesta, como una proporción o un promedio. El resultado se registra en un ADR |
| Generar el cliente del dashboard desde el OpenAPI de FastAPI | Corra la API | Es lo que impide que el frontend se desincronice del backend sin que falle la compilación, y lo que deja el cliente resuelto para una futura app móvil. Decidido en el [ADR 0005](adr/0005-python-fastapi-en-vez-de-go.md) |
| `scripts/verify_api_contract.py` | Exista el OpenAPI | Compara el contrato generado contra [`04-api.md`](04-api.md) y entra al hook de pre-commit. Automatiza la parte de `/spec-drift` que sí es binaria; lo que requiere criterio sigue siendo el command |
| Tokens del Design System, documentados aparte de los componentes | Haya diseño del dashboard | Para que la app móvil los reutilice en vez de reconstruirlos leyendo código |
| Rellenar un [`ui_contract.md`](features/TEMPLATE/ui_contract.md) por pantalla | Haya pantallas | La plantilla ya está; el contenido sale al escribir cada especificación |
| Completar `AGENTS.md` §11 con los comandos de tests y linters | Exista el scaffold | Hoy están los dos verificadores; faltan las herramientas de código |
| Los tres pull requests de [7. Pull requests](07-pull-requests.md) | Se implemente la primera funcionalidad | Salen solos de los tres [cortes verticales](convenciones-de-desarrollo.md#1-cortes-verticales), no hay que fabricarlos al cierre |
| Definir subagentes, si hacen falta | Haya tareas que lo justifiquen | Ver la decisión abierta de abajo |
| Publicar la referencia de la API en el portal | Corra FastAPI | El OpenAPI lo genera el framework; falta exponerlo como consola navegable y enlazarlo desde [`llms.txt`](../llms.txt), que hoy no puede describir endpoints que no existen |
| Documentación del código, con docstrings y su generador | Exista el backend | Es la capa que falta de las cuatro de [documentación viva](documentacion-viva.md#1-las-cuatro-capas). El equivalente en Python de lo que el módulo 5 propone con TypeDoc |
| Verificar las copias de respaldo del plan de base de datos: cuántos días retiene y si permite restaurar a un punto en el tiempo | Se contrate el plan de PostgreSQL en Render | Los datos de una cuenta borrada siguen en las copias hasta que vencen, y la política de privacidad tiene que decir cuánto tardan ([términos y privacidad](terminos-y-privacidad.md)). Restaurar a un punto en el tiempo es lo que permite volver atrás si una migración o un error rompen datos |
| Revisar los índices del [Ticket 3](06-tickets.md) contra las consultas reales | Haya datos y consultas medibles | `pending_transaction (batch_id)` sobra, porque lo cubre `UNIQUE (batch_id, position)`; los índices de saldo y de presupuesto conviene hacerlos parciales o que cubran las columnas que suman, contemplando `duplicate_of` y `deleted_at`; y el de duplicados sirve a una función que todavía no existe. Con pocos usuarios no se nota |
| Seed de datos falsos para desarrollo, que se niegue a correr contra producción | Exista el scaffold | Monedas y categorías base ya van en una migración; esto es solo el script de datos de prueba. En la entrega 2 es además de donde salen los usuarios, con lo que lista el [alcance](#alcance-de-la-entrega-2). Sin la protección, correrlo contra la base de producción mezcla datos inventados con reales |
| Sumar al verificador de arquitectura los nombres de los SDK de los proveedores elegidos | Se elijan los proveedores | El dominio no conoce ninguna librería de IA ([ADR 0020](adr/0020-sin-framework-de-orquestacion-de-ia.md)), y el verificador solo frena las que tiene en su lista |
| Revisar las dependencias que trae `langchain-text-splitters` y que ninguna envíe datos por su cuenta | Se instale, con la carga de la base de conocimiento | Lo pide el [ADR 0020](adr/0020-sin-framework-de-orquestacion-de-ia.md). Es para la entrega final |
| Política de acceso central y tests de aislamiento entre usuarios | Exista el scaffold | La regla ya está en la [API](04-api.md): el usuario sale de la sesión y un recurso ajeno responde `404`. Lo que falta es aplicarla en un solo lugar del dominio, incluida la visibilidad por intervalos de membresía de los grupos familiares y las respuestas por WhatsApp que citan un lote, y probarla en cada endpoint y en el worker. Implementada caso por caso, alguno se escapa |
| `UNIQUE` sobre `resulting_transaction_id`, `resulting_transfer_id` y `resulting_recurring_rule_id` de `pending_transaction` | Exista la migración inicial | Impide que dos pendientes queden enlazados al mismo movimiento. No duplica plata, pero deja datos inconsistentes |
| Cambiar la rama por defecto del fork al abrir la rama de la entrega 2 | Exista esa rama | El entorno `github-pages` solo despliega desde la rama por defecto. Detalle en [documentación viva](documentacion-viva.md#7-el-modelo-de-ramas-condiciona-el-despliegue) |

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
  gasto diario antes de llegar al tope.
- **Alta por el chat web: sin decidir.** El alta corre por el chat, igual en WhatsApp y en el
  chat web, desde el segundo paso. Pero para abrir el chat web hace falta una sesión, y una
  persona que todavía no es usuario no la tiene. Falta decidir cómo entra. La candidata es que el
  login del andamio deje pasar a un número habilitado, muestre los términos y, al aceptarlos,
  cree el usuario y la sesión. El modelo de datos sirve tanto para eso como para dejar el alta
  solo en WhatsApp. Se decide en la entrega final.
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
- **Cuotas en YAML versionado o ajustables sin desplegar: contradicción.**
  [2.5](02-arquitectura.md#25-seguridad) pone las cuotas de uso en archivos YAML del repositorio,
  que solo cambian con un despliegue, y [reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente)
  pide poder ajustarlas sin desplegar. Importa ante un abuso, porque define cuánto tarda bajar una
  cuota. Hay que decidir cuál de los dos manda.
- **Registro de eventos de seguridad: sin definir.** Sin él, una fuerza bruta sobre los códigos,
  un abuso del LLM o una toma de cuenta pasan sin que nadie se entere. Falta definir qué eventos
  se registran (pedidos y canjes de código, límites alcanzados, firmas inválidas del webhook,
  exportaciones, pedidos de borrado, cambios de miembros, cuotas superadas), cómo se redactan
  para no guardar teléfono, montos ni texto, y qué dispara una alerta a quien opera Platita.
- **Obligaciones legales de los datos: sin validar.** Además de los términos, falta confirmar con
  alguien con conocimiento legal la inscripción de la base ante la autoridad de aplicación de la
  Ley 25.326, la transferencia de datos al proveedor de alojamiento y al de LLM fuera del país, y
  que el alcance de los consejos, educación financiera que no elige instrumentos
  ([reglas de dominio § 18](reglas-de-dominio.md#18-alcance-de-los-consejos)), no se encuadre como
  asesoramiento de inversiones regulado. Bloquea abrir a usuarios reales.
- **Proveedor y plan de despliegue: sin decidir.** [Operación](operacion.md) propone Render en su
  plan pago más chico, por unos US$23 a 25 por mes, con una copia diaria cifrada fuera de Render.
  La alternativa es un servidor virtual único por unos US$6, que suma a quien opera parchear el
  sistema, administrar PostgreSQL y montar las copias. Hay que decidir cuánto vale no operar un
  servidor.
- **Pérdida de datos y tiempo de recuperación aceptados: sin decidir.** La propuesta pierde
  minutos ante un error y hasta 24 horas si se pierde la cuenta del proveedor, y se recupera en
  una a cuatro horas. Define la frecuencia de las copias y si alcanza el plan de base más chico.
- **Rama desde la que se despliega la aplicación: divergencia.**
  [2.4](02-arquitectura.md#24-infraestructura-y-despliegue) dice que el despliegue sale de un push
  a `main`, pero en este fork `main` es el espejo del repositorio del curso y el trabajo vive en
  ramas `feature/**` ([documentación viva](documentacion-viva.md#7-el-modelo-de-ramas-condiciona-el-despliegue)).
  Hay que decidir cuál es la rama de despliegue antes de conectar Render.
- **Quién genera las alertas proactivas: divergencia.** Las alertas usan el motor RAG, pero en el
  diagrama de [2.4](02-arquitectura.md#24-infraestructura-y-despliegue) los procesos programados
  no llegan al LLM, y solo el worker lo hace. O las genera el worker, o al diagrama le falta esa
  conexión. Toca a la rama de consejos: el consejo de una alerta sale de la base de conocimiento.
  Hay que decidirla antes de escribir esa rama.
- **Un cron o uno por tarea: sin decidir.** [2.4](02-arquitectura.md#24-infraestructura-y-despliegue)
  habla de procesos programados separados del servicio web, sin decir cuántos.
  [Operación](operacion.md) propone uno solo que despacha las tareas vencidas, porque cada cron
  cuesta aparte; a cambio, una tarea que se cuelga demora a las demás hasta que vence su tiempo.
- **Subagentes: sin decidir.** Un subagente corre en su propio contexto, así que hay que volver a
  explicarle la tarea entera y devuelve un resumen en vez del trabajo. Eso se paga cuando hay algo
  para paralelizar o una búsqueda grande que conviene mantener fuera del contexto. Ninguna de las
  tareas actuales es así —el skill y los dos commands leen uno o dos archivos cada uno—, pero eso
  puede cambiar cuando exista código. No se descarta: se deja pendiente hasta que aparezca una
  tarea que lo justifique.
