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
| `UNIQUE` sobre `resulting_transaction_id`, `resulting_transfer_id` y `resulting_card_purchase_id` de `pending_transaction` | Exista la migración inicial | Impide que dos pendientes queden enlazados al mismo movimiento. No duplica plata, pero deja datos inconsistentes |
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
- **Subagentes: sin decidir.** Un subagente corre en su propio contexto, así que hay que volver a
  explicarle la tarea entera y devuelve un resumen en vez del trabajo. Eso se paga cuando hay algo
  para paralelizar o una búsqueda grande que conviene mantener fuera del contexto. Ninguna de las
  tareas actuales es así —el skill y los dos commands leen uno o dos archivos cada uno—, pero eso
  puede cambiar cuando exista código. No se descarta: se deja pendiente hasta que aparezca una
  tarea que lo justifique.
