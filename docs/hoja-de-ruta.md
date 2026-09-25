# Hoja de ruta

Qué queda por hacer, cuándo se desbloquea y por qué importa. No es una lista de deseos: cada
punto salió de una decisión ya tomada y documentada, y está acá porque **depende de que exista
código** y no se puede adelantar sin inventar.

Los pendientes del registro de uso de IA —qué prompts falta documentar, el MCP de GitHub— viven
en [`prompts.md`](../prompts.md), no acá.

## Entrega 2

| Qué | Se desbloquea cuando | Por qué importa |
|---|---|---|
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
| Seed de datos falsos para desarrollo, que se niegue a correr contra producción | Exista el scaffold | Monedas y categorías base ya van en una migración; esto es solo el script de datos de prueba. Sin la protección, correrlo contra la base de producción mezcla datos inventados con reales |
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
- **Corregir un movimiento citando su confirmación: a futuro.** Hoy, citar el "Listo. $3.500 ·
  comida…" se procesa como un mensaje sin cita
  ([reglas de dominio § 5](reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración)).
  Que la cita apunte a ese movimiento haría las correcciones más directas, pero exige enlazar cada
  mensaje de confirmación con el movimiento que confirma, y decidir qué pasa si el movimiento ya
  se corrigió o se borró. Es una funcionalidad nueva, no una regla de borde.
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
- **Abuso del tope del proveedor de LLM: sin decidir.** Las cuotas son por usuario
  ([reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente)), así que varias
  cuentas creadas con números descartables agotan el tope global de 20 dólares y el asistente deja
  de funcionar para todos. Falta decidir un tope de tokens por mensaje, cuotas menores para
  cuentas nuevas y una alerta de gasto diario antes de llegar al tope. Bloquea abrir a usuarios
  reales.
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
  si los consejos que cruzan el perfil de riesgo con los datos del usuario pueden encuadrarse como
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
  conexión.
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
