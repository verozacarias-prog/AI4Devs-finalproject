# Reglas de dominio

Dueño único de las reglas de negocio de Platita. El texto sale literal de las secciones
1.2, 3.1, 3.2 y 6 del documento original; donde antes estaba repetido, el origen quedó
con un resumen y un enlace a este archivo.

Las viñetas del catálogo must/should/could de [1.2](01-producto.md#12-características-y-funcionalidades-principales) no se copian acá: siguen siendo
la descripción del producto y se enlazan desde cada grupo.

Antes de escribir código para cualquier ticket de dominio, leer este documento completo.

---

## 1. Registro de un movimiento: qué se asume y qué se confirma

**Qué se asume y qué se confirma**: para que cargar un gasto sea un solo mensaje, el asistente completa solo lo que puede resolver sin adivinar — la **fecha** es la de hoy salvo que el mensaje diga otra cosa, la **moneda** es la primaria del usuario salvo que se indique otra, y la **categoría** se ubica entre las existentes, sugiriendo crear una nueva solo si no encaja en ninguna. Todo eso aparece explícito en el mensaje de confirmación, donde el usuario corrige cualquiera de esos valores con una respuesta corta. En cambio hay datos que **requieren confirmación del usuario**: el **monto**, si es **gasto o ingreso** cuando el mensaje no lo deja claro, la **cuenta** (imputarla mal rompe el saldo calculado) y **a qué presupuesto se imputa el gasto** — la fecha acota los períodos posibles, pero elegir si el gasto pesa sobre el presupuesto individual o el familiar es una decisión del usuario, no algo que el sistema pueda deducir. El asistente propone lo más probable y el usuario confirma. Lo ya interpretado queda guardado mientras tanto, así se responde solo lo que falta y no se repite el mensaje entero.

**Campos obligatorios de un movimiento.** Una fila en `TRANSACTION` solo existe con todos estos datos presentes: `amount`, `currency`, `type`, `transaction_date`, `category_id`, `account_id` y `budget_period_id` — todos `NOT NULL` en la base de datos, así que ninguna vía de carga puede insertar un movimiento a medias. Lo que cambia entre ellos es **de dónde sale el valor**, no si es obligatorio:

- **Resueltos por el sistema, sin preguntar:** `transaction_date` (hoy, salvo que el mensaje indique otra fecha), `currency` (la primaria del usuario, salvo indicación contraria) y `category_id` (resuelto contra las categorías existentes; si ninguna encaja, se sugiere crear una). Quedan visibles en el mensaje de confirmación, que es donde el usuario los corrige.
- **Pedidos o confirmados por el usuario:** `amount`, `type` si el mensaje no lo deja claro, `account_id` siempre que no se mencione una cuenta, y `budget_period_id` **siempre**. Con el presupuesto el sistema no decide solo: `transaction_date` acota los períodos candidatos (y si el usuario pertenece a un grupo familiar, esa fecha cae dentro de su período individual y del familiar a la vez), pero cuál de ellos absorbe el gasto es una decisión del usuario, no algo derivable. El asistente propone el candidato más probable y el usuario confirma o elige otro; ninguna transacción se imputa a un presupuesto sin ese visto bueno. Hay dos excepciones a que ese visto bueno lo dé el propio usuario en el momento: las reglas recurrentes (§ 8) y el dueño de un grupo familiar que saca a un miembro con pendientes abiertos (§ 10).

Si falta o queda sin confirmar alguno de los campos que dependen del usuario, el movimiento no se registra: queda como `PENDING_TRANSACTION` hasta que responda. La misma regla aplicará a los movimientos detectados por el parser de emails cuando se implemente (could-have): traen monto, fecha y normalmente cuenta, pero nunca el presupuesto, así que quedarán pendientes de confirmación igual que los manuales incompletos.

Del alcance técnico del Ticket 1:

- Aplicación de defaults derivables antes de decidir si falta algo: `transaction_date` = hoy si no viene, `currency` = primaria del usuario si no viene.
- Resolución de cuenta por nombre si se menciona — **sin fallback ni cuenta por defecto**: si no se menciona, se pregunta.
- Mensaje de confirmación que lista también los valores resueltos por defecto (fecha, moneda, categoría) y acepta una corrección posterior sobre cualquiera de ellos.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [HU3](05-historias-de-usuario.md) · [Ticket 1](06-tickets.md).

## 2. Cuentas y saldo calculado

El **saldo no se guarda como columna**: se calcula como `initial_balance` más la suma de ingresos menos egresos de sus `TRANSACTION` —excluidas las marcadas como duplicado, ver § 7— así nunca queda desincronizado de los movimientos reales.

**Una cuenta, una moneda.** Cada cuenta tiene una sola moneda, igual que en el banco, donde una
cuenta en pesos y otra en dólares de la misma entidad son dos cuentas distintas. Un movimiento
se registra siempre en la moneda de la cuenta de la que sale o a la que entra la plata:
`TRANSACTION.currency` es igual a `ACCOUNT.currency`, sin excepción. Por eso el saldo nunca
suma montos de monedas distintas. La moneda de una cuenta no se puede cambiar mientras tenga
movimientos.

**Si el usuario nombra otra moneda, el asistente convierte y pide confirmación.** Cuando la
moneda del mensaje no coincide con la de la cuenta, el asistente convierte el monto a la moneda
de la cuenta con la cotización de referencia del usuario (§ 6) y le pide que confirme el valor
convertido antes de registrar. Por ejemplo, con "gasté 50 dólares con la Galicia pesos" y una
cotización de 1.000, responde "Serían $50.000 de Galicia pesos, ¿está bien?". El monto
convertido es un `amount` más y, como todo monto, exige confirmación (§ 1): mientras tanto el
movimiento queda como `PENDING_TRANSACTION`. Si el banco debitó otra cifra, el usuario la
corrige en la respuesta y vale la suya. El movimiento guarda el monto original, su moneda y la
cotización usada (`original_amount`, `original_currency`, `exchange_rate`), para que se sepa
después que fue un gasto en otra moneda y con qué valor se convirtió. Si el usuario no tiene cotización de referencia
configurada, el asistente no inventa una: le pregunta cuánto se debitó en la moneda de la cuenta.

La conversión a la moneda primaria del presupuesto (§ 6) es otra cosa: no toca el saldo de la
cuenta, solo cuánto pesa el movimiento en el presupuesto.

Y del alcance técnico del Ticket 1, la contracara en el registro:

- Resolución de cuenta por nombre si se menciona — **sin fallback ni cuenta por defecto**: si no se menciona, se pregunta.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [ACCOUNT en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU1](05-historias-de-usuario.md).

## 3. Presupuestos: individual o familiar, períodos y confirmación previa al inicio

La regla de negocio es que, para un período mensual, tiene que estar en `confirmed` antes de que arranque el mes (`period_start`); el mismo criterio aplica a quincenal con su propio `period_start`. El sistema genera el borrador del próximo período con anticipación y manda un recordatorio proactivo por WhatsApp si sigue en `draft` cerca de la fecha límite — mismo mecanismo que ya dispara las alertas de [HU3](05-historias-de-usuario.md), aplicado a un caso distinto.

Del alcance técnico del Ticket 1:

- Resolución de `budget_period_id`: a partir de `transaction_date` se arman los períodos candidatos del usuario (individual y de sus grupos familiares) y se propone el más probable — **nunca se asigna sin confirmación explícita del usuario**.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [restricción XOR en 3.1](03-modelo-de-datos.md#31-diagrama-del-modelo-de-datos) · [BUDGET_PERIOD en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU2](05-historias-de-usuario.md).

## 4. Categorías: catálogo base, categorías propias y creación con confirmación

Del alcance técnico del Ticket 1:

- Resolución de categoría contra el catálogo existente del usuario; si ninguna encaja, proponer crear una nueva, sin crearla sin confirmación.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [CATEGORY en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU3](05-historias-de-usuario.md).

## 5. PENDING_TRANSACTION: creación, continuación de la conversación, promoción y expiración

Se usa cuando falta algo que **depende de una decisión del usuario** — la cuenta, el monto, el tipo si es ambiguo, o la confirmación del presupuesto; no se crea un pendiente por una fecha o una moneda ausente, porque esas se resuelven solas.

Cuando el usuario responde, se completa y se promueve a `TRANSACTION` (quedando enlazada por `resulting_transaction_id`). `expires_at` evita que se acumulen pendientes eternos de mensajes que nunca se contestaron.

Del alcance técnico del Ticket 1:

- Si falta algún campo que depende del usuario (`amount`, `type` ambiguo, `account_id`, o el `budget_period_id` sin confirmar): crear una `PENDING_TRANSACTION` con lo interpretado y la lista de faltantes, y responder preguntando solo por esos, ofreciendo las opciones disponibles del usuario. Manejar el mensaje de respuesta como continuación de ese pendiente, no como un movimiento nuevo.
- La categoría entra en esa lista cuando ninguna existente encaja. Es el único caso en que `category_id` deja de resolverse solo: como una categoría nueva no se crea sin confirmación (§ 4), `category` se agrega a `missing_fields` y se pregunta ofreciendo elegir una del catálogo del usuario o confirmar la creación de la propuesta. La respuesta se procesa como continuación del pendiente, y el movimiento no se promueve a `TRANSACTION` hasta tener un `category_id` válido.

Ver también: [PENDING_TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU3](05-historias-de-usuario.md).

## 6. Multimoneda y cotización

La regla vive en el catálogo de funcionalidades y en el modelo de datos, no se duplica acá:
un presupuesto recibe movimientos en varias monedas y los convierte a su moneda primaria con
una cotización de referencia configurada a mano en esta etapa; la `TRANSACTION` guarda tanto el
monto original (`amount`, `currency`) como el convertido (`converted_amount`).

Ver: [1.2, soporte multimoneda](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU4](05-historias-de-usuario.md).

## 7. Chequeo de duplicados entre origen manual y automático

`duplicate_of` es el mecanismo previsto de detección de duplicados entre carga manual y automática: antes de crear una `TRANSACTION` nueva se busca, para el mismo usuario, otra transacción reciente de la vía contraria con monto y moneda iguales y `transaction_date` dentro de una ventana de un par de días.

Si aparece una candidata, **la fila nueva se guarda igual**, con `duplicate_of` apuntando a la original. Se guarda y no se descarta porque cada vía aporta algo distinto —el mensaje de WhatsApp la intención del usuario, el mail del banco el dato del movimiento real— y porque descartar en silencio lo que el usuario acaba de escribir es indistinguible de un movimiento perdido.

Lo que no se duplica es el dinero: **una fila con `duplicate_of` no nulo no entra en ninguna agregación** — ni en el saldo de la cuenta (§ 2), ni en el gastado de un presupuesto, ni en las alertas. Cuenta el original; la fila enlazada queda como evidencia de la otra vía y como el lugar donde el usuario deshace el enlace si el sistema se equivocó y en realidad eran dos gastos distintos.

`TRANSACTION.duplicate_of` referencia otra `TRANSACTION` del mismo usuario cuando el sistema detecta que probablemente describen el mismo gasto real (mismo monto y moneda, fecha cercana, un origen manual y el otro automático). La columna se crea desde la migración inicial, pero la lógica que la puebla depende de la carga por email, que es could-have (ver [1.2](01-producto.md#12-características-y-funcionalidades-principales)).

Ver también: [1.2, detección de duplicados](01-producto.md#12-características-y-funcionalidades-principales) · [Ticket 3](06-tickets.md), que crea el índice de soporte.

## 8. Gastos recurrentes: la excepción a la confirmación

**Excepción: movimientos generados por una regla recurrente.** Un `RECURRING_EXPENSE` define una sola vez, al configurarse, su cuenta y su dueño de presupuesto (`budget_user_id` o `budget_family_group_id`, exactamente uno). En cada ciclo, el motor resuelve el `BUDGET_PERIOD` concreto de ese dueño que cubre la fecha de ejecución e inserta la `TRANSACTION` ya completa — la confirmación ocurrió al dar de alta la regla, no se vuelve a pedir mes a mes.

Para que eso sea posible sin preguntar nada mes a mes, la regla define desde el alta **todo lo que un movimiento necesita**: categoría, cuenta (`account_id`) y dueño del presupuesto (`budget_user_id` o `budget_family_group_id`).

**Una regla genera como mucho un movimiento por fecha de ejecución.** Si el proceso programado
corre dos veces el mismo día o se reintenta después de un fallo, no se genera un segundo cargo.
La base lo garantiza con una clave única, y el avance de `next_execution` ocurre en la misma
transacción que inserta el movimiento.

Ver también: [1.2, gastos recurrentes](01-producto.md#12-características-y-funcionalidades-principales) · [RECURRING_EXPENSE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [restricción XOR en 3.1](03-modelo-de-datos.md#31-diagrama-del-modelo-de-datos).

## 9. Trazabilidad de origen (`source`)

El valor de `source` no es opcional ni inferible después: se fija al crear la fila y habilita
tanto la auditoría como el chequeo de duplicados del grupo 7. Qué registra y para qué, en los
enlaces de abajo.

Ver: [1.2, trazabilidad de origen](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU4](05-historias-de-usuario.md).

## 10. Grupos familiares: administración, salida y visibilidad

**Quién administra.** Cada grupo familiar tiene un dueño (`role = 'owner'` en `USER_GROUP`), que
es quien administra sus miembros: agrega y saca usuarios del grupo. El resto de los miembros
tiene `role = 'member'`.

**El dueño también puede salir.** Al hacerlo elige a otro miembro vigente del grupo como nuevo
dueño, y el rol pasa sin que el elegido tenga que aceptarlo. En la misma transacción se cierra la
membresía del que sale y se asigna `role = 'owner'` al elegido, de modo que el grupo nunca queda
sin dueño vigente. Las demás reglas de salida de esta sección le aplican igual. La única
excepción es que sea el último miembro: ahí no hay a quién pasarle el rol (ver abajo).

**Sacar a un miembro: el dueño resuelve sus pendientes.** Cuando el dueño saca a un miembro que
tiene `PENDING_TRANSACTION` abiertas, las resuelve él: confirma o rechaza cada una. Es la única
excepción a que el propio usuario confirme cuenta y presupuesto (§ 1), y vale solo dentro de ese
flujo: fuera de él, el dueño no ve ni resuelve los pendientes de otros miembros. Al confirmar, se
aplican las mismas validaciones que si confirmara el miembro: la cuenta tiene que ser del
miembro, y el período, uno suyo o de un grupo al que pertenezca. Cada pendiente guarda quién lo
resolvió (`resolved_by`), para que quede claro en la auditoría que no fue su autor. Una vez
cerrados todos los pendientes, la salida sigue las mismas reglas que una salida voluntaria.

**El último miembro.** Cuando sale el último miembro vigente, se genera una exportación a
archivo de los movimientos y períodos del grupo para ese usuario, y su membresía se cierra como
cualquier otra. No se deshabilita al usuario, que sigue usando Platita con sus cuentas,
presupuestos individuales y otros grupos, ni se borra el grupo. El grupo queda sin miembros
vigentes y, por lo tanto, nadie puede imputarle movimientos nuevos. Quien salió conserva la
lectura de sus períodos, igual que en cualquier salida.

**La membresía se cierra, no se borra.** Cuando un usuario sale de un grupo, su fila en
`USER_GROUP` queda con `left_at` informado en vez de eliminarse. Así se sigue sabiendo en qué
períodos fue miembro, que es lo que definen las dos reglas siguientes.

**Lo registrado no cambia al salir.** Los movimientos que el usuario ya imputó a un período del
grupo siguen imputados ahí: siguen pesando en el gastado del presupuesto familiar y siguen
visibles para los miembros del grupo. Salir no reescribe la historia del presupuesto.

**No se sale con pendientes abiertos.** Un usuario no puede salir de un grupo mientras tenga
alguna `PENDING_TRANSACTION` abierta, sea cual sea el presupuesto al que apunte: como el período
nunca se asigna sin confirmación (§ 1), cualquier pendiente podría terminar en el presupuesto
familiar. Primero confirma o rechaza cada uno. Rechazar es un cierre explícito del pendiente, no
un vencimiento (§ 5).

**Los recurrentes hacia el grupo se pausan.** Al salir, cada `RECURRING_EXPENSE` del usuario con
`budget_family_group_id` de ese grupo pasa a `active = false`. No se borra ni se reasigna: queda
el historial de lo ya generado, y reactivarla hacia otro presupuesto es una decisión del usuario.

**Quién ve el presupuesto familiar.** Los miembros actuales del grupo ven todos sus períodos y
todos los movimientos imputados a ellos, sin importar qué miembro los registró. Un
usuario que salió conserva acceso **de solo lectura** a los períodos del grupo en los que fue
miembro, es decir, los que se superponen con su intervalo de membresía (`joined_at` a
`left_at`). No ve los posteriores ni puede imputarles movimientos.

**La pertenencia se valida al imputar, no al preguntar.** Un pendiente se promueve a un período
familiar solo si, en ese momento, el usuario sigue siendo miembro del grupo. La validación ocurre
dentro de la misma transacción de base de datos que la promoción.

Ver también: [FAMILY_GROUP / USER_GROUP en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [§ 5, pendientes](#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración) · [§ 8, recurrentes](#8-gastos-recurrentes-la-excepción-a-la-confirmación) · [decisiones abiertas](hoja-de-ruta.md#decisiones-abiertas).
