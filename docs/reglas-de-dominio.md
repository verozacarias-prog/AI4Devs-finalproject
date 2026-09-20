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
  - **Pedidos o confirmados por el usuario:** `amount`, `type` si el mensaje no lo deja claro, `account_id` siempre que no se mencione una cuenta, y `budget_period_id` **siempre**. Con el presupuesto el sistema no decide solo: `transaction_date` acota los períodos candidatos (y si el usuario pertenece a un grupo familiar, esa fecha cae dentro de su período individual y del familiar a la vez), pero cuál de ellos absorbe el gasto es una decisión del usuario, no algo derivable. El asistente propone el candidato más probable y el usuario confirma o elige otro; ninguna transacción se imputa a un presupuesto sin ese visto bueno.

Si falta o queda sin confirmar alguno de los campos que dependen del usuario, el movimiento no se registra: queda como `PENDING_TRANSACTION` hasta que responda. La misma regla aplicará a los movimientos detectados por el parser de emails cuando se implemente (could-have): traen monto, fecha y normalmente cuenta, pero nunca el presupuesto, así que quedarán pendientes de confirmación igual que los manuales incompletos.

Del alcance técnico del Ticket 1:

- Aplicación de defaults derivables antes de decidir si falta algo: `transaction_date` = hoy si no viene, `currency` = primaria del usuario si no viene.
- Resolución de cuenta por nombre si se menciona — **sin fallback ni cuenta por defecto**: si no se menciona, se pregunta.
- Mensaje de confirmación que lista también los valores resueltos por defecto (fecha, moneda, categoría) y acepta una corrección posterior sobre cualquiera de ellos.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [HU3](05-historias-de-usuario.md) · [Ticket 1](06-tickets.md).

## 2. Cuentas y saldo calculado

El **saldo no se guarda como columna**: se calcula como `initial_balance` más la suma de ingresos menos egresos de sus `TRANSACTION` — así nunca queda desincronizado de los movimientos reales.

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

Ver también: [PENDING_TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU3](05-historias-de-usuario.md).

## 6. Multimoneda y cotización

La regla vive en el catálogo de funcionalidades y en el modelo de datos, no se duplica acá:
un presupuesto recibe movimientos en varias monedas y los convierte a su moneda primaria con
una cotización de referencia configurada a mano en esta etapa; la `TRANSACTION` guarda tanto el
monto original (`amount`, `currency`) como el convertido (`converted_amount`).

Ver: [1.2, soporte multimoneda](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU4](05-historias-de-usuario.md).

## 7. Chequeo de duplicados entre origen manual y automático

`duplicate_of` es el mecanismo previsto de detección de duplicados entre carga manual y automática: antes de crear una `TRANSACTION` nueva se busca, para el mismo usuario, otra transacción reciente de la vía contraria con monto y moneda iguales y `transaction_date` dentro de una ventana de un par de días — si aparece una candidata, no se crea una segunda fila: se enlaza vía `duplicate_of` y el registro nuevo aporta lo que le falte al original.

`TRANSACTION.duplicate_of` referencia otra `TRANSACTION` del mismo usuario cuando el sistema detecta que probablemente describen el mismo gasto real (mismo monto y moneda, fecha cercana, un origen manual y el otro automático). La columna se crea desde la migración inicial, pero la lógica que la puebla depende de la carga por email, que es could-have (ver [1.2](01-producto.md#12-características-y-funcionalidades-principales)).

Ver también: [1.2, detección de duplicados](01-producto.md#12-características-y-funcionalidades-principales) · [Ticket 3](06-tickets.md), que crea el índice de soporte.

## 8. Gastos recurrentes: la excepción a la confirmación

**Excepción: movimientos generados por una regla recurrente.** Un `RECURRING_EXPENSE` define una sola vez, al configurarse, su cuenta y su dueño de presupuesto (`budget_user_id` o `budget_family_group_id`, exactamente uno). En cada ciclo, el motor resuelve el `BUDGET_PERIOD` concreto de ese dueño que cubre la fecha de ejecución e inserta la `TRANSACTION` ya completa — la confirmación ocurrió al dar de alta la regla, no se vuelve a pedir mes a mes.

Para que eso sea posible sin preguntar nada mes a mes, la regla define desde el alta **todo lo que un movimiento necesita**: categoría, cuenta (`account_id`) y dueño del presupuesto (`budget_user_id` o `budget_family_group_id`).

Ver también: [1.2, gastos recurrentes](01-producto.md#12-características-y-funcionalidades-principales) · [RECURRING_EXPENSE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [restricción XOR en 3.1](03-modelo-de-datos.md#31-diagrama-del-modelo-de-datos).

## 9. Trazabilidad de origen (`source`)

Cada movimiento guarda si se cargó manual (WhatsApp) o automático (gasto recurrente, o email
cuando se implemente). El valor no es opcional ni inferible después: se fija al crear la fila y
habilita tanto la auditoría como el chequeo de duplicados del grupo 7.

Ver: [1.2, trazabilidad de origen](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU4](05-historias-de-usuario.md).
