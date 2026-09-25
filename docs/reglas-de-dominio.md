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

- **Resueltos por el sistema, sin preguntar:** `transaction_date` (hoy en la zona horaria del usuario, salvo que el mensaje indique otra fecha), `currency` (la primaria del usuario, salvo indicación contraria) y `category_id` (resuelto contra las categorías existentes; si ninguna encaja, se sugiere crear una). Quedan visibles en el mensaje de confirmación, que es donde el usuario los corrige.
- **Pedidos o confirmados por el usuario:** `amount`, `type` si el mensaje no lo deja claro, `account_id` siempre que no se mencione una cuenta, y `budget_period_id` **siempre**. Con el presupuesto el sistema no decide solo: `transaction_date` acota los períodos candidatos (y si el usuario pertenece a un grupo familiar, esa fecha cae dentro de su período individual y del familiar a la vez), pero cuál de ellos absorbe el gasto es una decisión del usuario, no algo derivable. El asistente propone el candidato más probable y el usuario confirma o elige otro; ninguna transacción se imputa a un presupuesto sin ese visto bueno. Hay dos excepciones a que ese visto bueno lo dé el propio usuario en el momento: las reglas recurrentes (§ 8) y el dueño de un grupo familiar que saca a un miembro con pendientes abiertos (§ 10).

Si falta o queda sin confirmar alguno de los campos que dependen del usuario, el movimiento no se registra: queda como `PENDING_TRANSACTION` hasta que responda. La misma regla aplicará a los movimientos detectados por el parser de emails cuando se implemente (could-have): traen monto, fecha y normalmente cuenta, pero nunca el presupuesto, así que quedarán pendientes de confirmación igual que los manuales incompletos.

Del alcance técnico del Ticket 1:

- Aplicación de defaults derivables antes de decidir si falta algo: `transaction_date` = hoy si no viene, `currency` = primaria del usuario si no viene.
- Resolución de cuenta por nombre si se menciona — **sin fallback ni cuenta por defecto**: si no se menciona, se pregunta.
- Mensaje de confirmación que lista también los valores resueltos por defecto (fecha, moneda, categoría) y acepta una corrección posterior sobre cualquiera de ellos.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [HU3](05-historias-de-usuario.md) · [Ticket 1](06-tickets.md).

## 2. Cuentas y saldo calculado

El **saldo no se guarda como columna**: se calcula como `initial_balance` más la suma de ingresos menos egresos de sus `TRANSACTION` —excluidas las marcadas como duplicado, ver § 7, y las borradas—, más las transferencias que recibe y menos las que envía (§ 13), así nunca queda desincronizado de los movimientos reales.

**El saldo es lo que ya ocurrió.** Solo cuentan los movimientos y las transferencias con fecha
hasta hoy, en la zona horaria del usuario. Lo registrado con fecha futura, como una cuota de
tarjeta que vence la semana próxima, no es saldo: es una deuda o un ingreso previsto, que se
muestra aparte y entra en el saldo el día de su fecha. El saldo a cualquier día pasado se
calcula igual, contando hasta ese día.

**Nada antes del alta de la cuenta.** El saldo inicial es el saldo de la cuenta el día en que se
dio de alta, en la zona horaria del usuario. Un movimiento o una transferencia no puede tener
fecha anterior a ese día, y la base lo rechaza. Si el usuario carga un gasto anterior, el
asistente le explica que la cuenta registra desde su alta y que ese gasto ya está reflejado en
el saldo inicial.

**Borrar un movimiento.** El usuario puede borrar un gasto, un ingreso, una transferencia o una
regla recurrente que ya confirmó, incluida una compra con tarjeta. El movimiento queda marcado
como borrado, con quién y cuándo, y deja de contar en el saldo, en el gastado de los
presupuestos y en las alertas. Borrar una regla corta las ocurrencias que faltaban generar,
como las cuotas pendientes de una compra; las ya generadas se borran una por una (§ 8 y § 13). El fundamento está en el
[ADR 0015](adr/0015-borrado-logico-de-movimientos.md).

**Una cuenta, una moneda.** Cada cuenta tiene una sola moneda, igual que en el banco, donde una
cuenta en pesos y otra en dólares de la misma entidad son dos cuentas distintas. Un movimiento
puede estar en otra moneda que su cuenta, como "gasté 50 dólares con la Galicia pesos", pero el
saldo suma cada movimiento ya convertido a la moneda de la cuenta (§ 6), así que nunca suma
montos de monedas distintas. La moneda de una cuenta no se puede cambiar: una cuenta en otra
moneda es otra cuenta.

**Cada cuenta tiene un nombre distinto.** Un usuario no puede tener dos cuentas con el mismo
nombre, sin distinguir mayúsculas, porque el asistente las reconoce por el nombre que el usuario
menciona. Aun así, una mención puede coincidir con más de una: "la Galicia" puede ser "Galicia
pesos" o "Galicia USD". En ese caso el asistente no elige: pregunta, ofreciendo las cuentas que
coinciden, igual que cuando no se menciona ninguna.

**Si el usuario nombra otra moneda, el asistente convierte y pide confirmación.** Cuando la
moneda del mensaje no coincide con la de la cuenta, el asistente convierte el monto a la moneda
de la cuenta con la cotización de referencia del usuario (§ 6) y le pide que confirme el valor
convertido antes de registrar. Por ejemplo, con "gasté 50 dólares con la Galicia pesos" y una
cotización de 1.000, responde "Serían $50.000 de Galicia pesos, ¿está bien?". El monto
convertido, como todo monto, exige confirmación (§ 1): mientras tanto el movimiento queda como
`PENDING_TRANSACTION`. Si el banco debitó otra cifra, el usuario la corrige en la respuesta y
vale la suya: la cotización pasa a ser la que resulta de su cifra. El movimiento guarda el gasto
como se hizo, 50 dólares, y la cotización (`amount`, `currency`, `exchange_rate`); el débito en
la cuenta se calcula con esos dos valores. Si el usuario no tiene cotización de referencia
configurada, el asistente no inventa una: le pregunta cuánto se debitó en la moneda de la cuenta.

La conversión a la moneda primaria del presupuesto (§ 6) es otra cosa: no toca el saldo de la
cuenta, solo cuánto pesa el movimiento en el presupuesto.

Y del alcance técnico del Ticket 1, la contracara en el registro:

- Resolución de cuenta por nombre si se menciona — **sin fallback ni cuenta por defecto**: si no se menciona, se pregunta.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [ACCOUNT en 3.2](03-modelo-de-datos.md#account) · [HU1](05-historias-de-usuario.md).

## 3. Presupuestos: individual o familiar, períodos y confirmación previa al inicio

La regla de negocio es que, para un período mensual, tiene que estar en `confirmed` antes de que arranque el mes (`period_start`); el mismo criterio aplica a quincenal con su propio `period_start`. El sistema genera el borrador del próximo período con anticipación y manda un recordatorio proactivo por WhatsApp si sigue en `draft` cerca de la fecha límite — mismo mecanismo que ya dispara las alertas de [HU3](05-historias-de-usuario.md), aplicado a un caso distinto.

**Los períodos de un mismo dueño no se solapan.** Un usuario, o un grupo familiar, no puede
tener dos períodos que cubran el mismo día, y un período termina en su fecha de inicio o
después. Así, para una fecha y un dueño hay como mucho un período candidato, y resolverlo es
determinista. La base lo impone.

**Solo un período confirmado recibe movimientos.** Mientras está en `draft` no se le imputa
nada, sea cual sea la vía de carga, y un período confirmado que ya tiene movimientos no vuelve
a `draft`. La base lo impone también, porque un movimiento imputado a un borrador pesaría en un
presupuesto que el usuario todavía no aprobó.

Del alcance técnico del Ticket 1:

- Resolución de `budget_period_id`: a partir de `transaction_date` se arman los períodos candidatos del usuario (individual y de sus grupos familiares) y se propone el más probable — **nunca se asigna sin confirmación explícita del usuario**.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [restricción XOR en 3.2](03-modelo-de-datos.md#budget_period) · [BUDGET_PERIOD en 3.2](03-modelo-de-datos.md#budget_period) · [HU2](05-historias-de-usuario.md).

## 4. Categorías: catálogo base, categorías propias y creación con confirmación

**Cada categoría es de gasto o de ingreso.** Una categoría declara si clasifica gastos o
ingresos, y un movimiento solo puede usar una categoría de su mismo tipo: un sueldo no se
clasifica como "comida". La base lo impone. El catálogo base trae categorías de los dos tipos, y
el usuario puede sumar propias de cualquiera de ellos.

Del alcance técnico del Ticket 1:

- Resolución de categoría contra el catálogo existente del usuario; si ninguna encaja, proponer crear una nueva, sin crearla sin confirmación.

Ver también: [1.2](01-producto.md#12-características-y-funcionalidades-principales) · [CATEGORY en 3.2](03-modelo-de-datos.md#category) · [HU3](05-historias-de-usuario.md).

## 5. PENDING_TRANSACTION: creación, continuación de la conversación, promoción y expiración

Se usa cuando falta algo que **depende de una decisión del usuario** — la cuenta, el monto, el tipo si es ambiguo, o la confirmación del presupuesto; no se crea un pendiente por una fecha o una moneda ausente, porque esas se resuelven solas.

Cuando el usuario responde, se completa y se promueve a `TRANSACTION` (quedando enlazada por `resulting_transaction_id`). `expires_at` evita que se acumulen pendientes eternos de mensajes que nunca se contestaron.

**Un pendiente también puede ser una transferencia o una compra con tarjeta.** Las dos se
confirman conversando igual que un gasto (§ 13): a una transferencia le puede faltar la cuenta
de origen o de destino, o la confirmación de la cotización si las monedas difieren; a una compra
con tarjeta, la tarjeta, la cantidad de cuotas, el monto de la cuota o a qué presupuesto va.
Mientras tanto quedan como pendiente, con `intent` indicando en qué se van a convertir, y al
completarse se promueven a `TRANSFER` o a `RECURRING_RULE` en vez de a `TRANSACTION`: una
compra con tarjeta es una regla recurrente (§ 13). Lotes, recordatorios y vencimiento son
los mismos para los tres.

**Los pendientes de un recurrente no vencen.** Un pendiente generado por una regla recurrente
(§ 8) representa un gasto que ocurre sí o sí, como el alquiler: descartarlo sería perder el
registro de ese mes. Por eso no tiene `expires_at` y, en vez de vencer, se vuelve a recordar
cada 3 días hasta que el usuario lo confirme o lo rechace.

Del alcance técnico del Ticket 1:

- Si falta algún campo que depende del usuario (`amount`, `type` ambiguo, `account_id`, o el `budget_period_id` sin confirmar): crear una `PENDING_TRANSACTION` con lo interpretado y la lista de faltantes, y responder preguntando solo por esos, ofreciendo las opciones disponibles del usuario. Manejar el mensaje de respuesta como continuación de ese pendiente, no como un movimiento nuevo.
- La categoría entra en esa lista cuando ninguna existente encaja. Es el único caso en que `category_id` deja de resolverse solo: como una categoría nueva no se crea sin confirmación (§ 4), `category` se agrega a `missing_fields` y se pregunta ofreciendo elegir una del catálogo del usuario o confirmar la creación de la propuesta. La respuesta se procesa como continuación del pendiente, y el movimiento no se promueve a `TRANSACTION` hasta tener un `category_id` válido.

**Varios pendientes a la vez: el lote es la unidad de conversación.** Un usuario puede tener
cualquier cantidad de pendientes abiertos: varios gastos cargados juntos, o varios avisos
detectados en sus emails. Lo que se limita no es cuántos existen, sino sobre qué se le pregunta.
Cada pendiente pertenece a un lote (`PENDING_BATCH`), y un gasto suelto es un lote de uno.

- **Un solo lote en conversación por usuario.** Es el lote sobre el que el asistente hizo la
  última pregunta y espera respuesta. Los demás esperan su turno. Cuando todos los pendientes
  del lote en conversación quedan promovidos, rechazados o vencidos, el asistente pregunta por
  el siguiente.
- **Los manuales pasan adelante.** Los pendientes que el usuario acaba de cargar van antes que
  los detectados por email: el usuario tiene el contexto fresco, y los de email pueden esperar.
  Un lote nunca mezcla pendientes manuales y automáticos.
- **Se pregunta por lote, en un solo mensaje.** El asistente lista todos los pendientes del lote,
  numerados, con lo que ya interpretó de cada uno y lo que le falta. Varios gastos en un mismo
  mensaje van al mismo lote.
- **Varios mensajes seguidos convergen en un lote.** Si llega un gasto manual nuevo mientras hay
  un lote manual esperando respuesta, se suma a ese lote y el asistente reenvía la lista
  actualizada, en vez de hacer una pregunta aparte por cada mensaje.
- **La respuesta puede ser general o por número.** Por ejemplo, "todos al familiar", o "el 1 con
  Mercado Pago, el resto al mío". Una respuesta general cuenta como confirmación explícita del
  presupuesto de cada pendiente (§ 1) porque cada uno fue listado con su monto antes de la
  respuesta; lo que sigue prohibido es imputar un pendiente que no se le mostró al usuario. Las
  correcciones también pueden ir por número ("el 2 fueron 3800").
- **Responder citando un mensaje manda.** Si el usuario responde citando la pregunta de un lote
  concreto, la respuesta va a ese lote aunque no sea el que está en conversación. Es lo que
  permite contestar fuera de orden sin ambigüedad. Si el mensaje citado no es la pregunta de un
  lote abierto —una confirmación, una alerta, la pregunta de un lote ya cerrado—, la respuesta
  se procesa como si no citara nada.
- **Como mucho 10 pendientes por lote.** Más que eso no se lee bien en un mensaje de WhatsApp y
  multiplica las chances de una interpretación errónea. Si el usuario manda más, el asistente
  toma los primeros 10 y le avisa que siga con el resto.

Ver también: [PENDING_TRANSACTION y PENDING_BATCH en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU3](05-historias-de-usuario.md).

## 6. Multimoneda y cotización

Un presupuesto recibe movimientos en varias monedas y los convierte a su moneda primaria. La
`TRANSACTION` guarda el monto en la moneda en que se hizo (`amount`, `currency`) y, si hace
falta convertir, la cotización usada (`exchange_rate`), para que el dashboard pueda mostrarla y
la conversión dé siempre el mismo resultado.

**Dos conversiones, una sola cotización.** Un movimiento se convierte para dos cosas distintas:

1. **A la moneda de la cuenta**, para el saldo (§ 2). Pasa cuando el usuario dice "gasté 50
   dólares con la Galicia pesos".
2. **A la moneda del presupuesto**, para lo que pesa en el presupuesto, sin tocar el saldo. Pasa
   cuando un movimiento de una cuenta en dólares se imputa a un presupuesto en pesos.

Las dos usan la misma cotización, guardada en el movimiento. Alcanza con una porque un
movimiento involucra como mucho dos monedas entre la suya, la de su cuenta y la de su período.
Los montos convertidos no se guardan: se calculan con esa cotización y se redondean a 2
decimales movimiento por movimiento, antes de sumar. El fundamento está en el
[ADR 0011](adr/0011-cotizaciones-con-adaptador-generico-configurable.md).

**Si hay tres monedas, se pide el monto en la de la cuenta.** Un gasto de 30 euros con una
cuenta en dólares, imputado a un presupuesto en pesos, necesitaría dos cotizaciones. En ese caso
el asistente pregunta cuánto se debitó en la moneda de la cuenta, y el movimiento se registra
en esa moneda, con la cotización al presupuesto. El usuario tiene que dar ese dato de todos
modos, porque sin él no se sabe cuánto bajó la cuenta.

**La cotización se sugiere y el usuario confirma.** En las dos conversiones el asistente propone
el valor con la última cotización guardada de la fuente de referencia del usuario
(`exchange_rate_reference`), la muestra en el mensaje de confirmación y el usuario la acepta o la
corrige. Una cotización nunca se aplica sin que el usuario vea el resultado.

**De dónde sale la cotización.** Se busca sola, desde las fuentes configuradas, y se guarda por
fuente y fecha; convertir nunca consulta al proveedor en el momento. En el MVP hay fuentes solo
para Argentina, donde cada usuario elige cuál usa (por ejemplo, MEP u oficial). El mecanismo está
en el [ADR 0011](adr/0011-cotizaciones-con-adaptador-generico-configurable.md).

**Sin cotización, se pregunta.** Si el usuario no tiene fuente de referencia, porque su país
todavía no tiene una configurada, o si la última cotización guardada es demasiado vieja, el
asistente no propone un valor: pregunta cuánto se debitó en la moneda de la cuenta, o cuánto
representa en la moneda del presupuesto. De lo que el usuario responde sale la cotización
usada, y un test verifica que recalcular con ella devuelve la cifra que dio.

Ver: [1.2, soporte multimoneda](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#transaction) · [HU4](05-historias-de-usuario.md).

## 7. Chequeo de duplicados entre origen manual y automático

`duplicate_of` es el mecanismo previsto de detección de duplicados entre carga manual y automática: antes de crear una `TRANSACTION` nueva se busca, para el mismo usuario, otra transacción reciente de la vía contraria con monto y moneda iguales y `transaction_date` dentro de una ventana de un par de días.

Si aparece una candidata, **la fila nueva se guarda igual**, con `duplicate_of` apuntando a la original. Se guarda y no se descarta porque cada vía aporta algo distinto —el mensaje de WhatsApp la intención del usuario, el mail del banco el dato del movimiento real— y porque descartar en silencio lo que el usuario acaba de escribir es indistinguible de un movimiento perdido.

Lo que no se duplica es el dinero: **una fila con `duplicate_of` no nulo no entra en ninguna agregación** — ni en el saldo de la cuenta (§ 2), ni en el gastado de un presupuesto, ni en las alertas. Cuenta el original; la fila enlazada queda como evidencia de la otra vía y como el lugar donde el usuario deshace el enlace si el sistema se equivocó y en realidad eran dos gastos distintos.

`TRANSACTION.duplicate_of` referencia otra `TRANSACTION` del mismo usuario cuando el sistema detecta que probablemente describen el mismo gasto real (mismo monto y moneda, fecha cercana, un origen manual y el otro automático). La columna se crea desde la migración inicial, pero la lógica que la puebla depende de la carga por email, que es could-have (ver [1.2](01-producto.md#12-características-y-funcionalidades-principales)).

Ver también: [1.2, detección de duplicados](01-producto.md#12-características-y-funcionalidades-principales) · [Ticket 3](06-tickets.md), que crea el índice de soporte.

## 8. Movimientos recurrentes: la excepción a la confirmación

**Excepción: movimientos generados por una regla recurrente.** Un `RECURRING_RULE` define una sola vez, al configurarse, su cuenta y su dueño de presupuesto (`budget_user_id` o `budget_family_group_id`, exactamente uno). En cada ciclo, el motor resuelve el `BUDGET_PERIOD` concreto de ese dueño que cubre la fecha de ejecución e inserta la `TRANSACTION` ya completa — la confirmación ocurrió al dar de alta la regla, no se vuelve a pedir mes a mes.

Para que eso sea posible sin preguntar nada mes a mes, la regla define desde el alta **todo lo que un movimiento necesita**: si es gasto o ingreso (`type`), categoría, cuenta (`account_id`) y dueño del presupuesto (`budget_user_id` o `budget_family_group_id`). Una regla puede generar gastos, como el alquiler, o ingresos, como el sueldo; todo lo de esta sección vale igual para los dos.

**Una regla genera como mucho un movimiento por ocurrencia.** Si el proceso programado
corre dos veces el mismo día o se reintenta después de un fallo, no se genera un segundo cargo.
La base lo garantiza con una clave única, y el avance de `next_execution` ocurre en la misma
transacción que inserta el movimiento.

**Cuándo corre cada regla.** Una regla semanal corre el mismo día de la semana, y una anual en la
misma fecha cada año. Una regla mensual corre el mismo día de cada mes; si ese día no existe en
el mes, como el 31 en abril o el 30 en febrero, corre el último día del mes, y al mes siguiente
vuelve a su día. El alquiler que vence el 31 se genera igual en febrero. Por el mismo criterio,
una regla anual del 29 de febrero corre el 28 en los años que no son bisiestos.

**Una regla puede tener fin.** Si define una cantidad de ocurrencias, como las 6 cuotas de una
compra, deja de generar al llegar a esa cantidad. Sin cantidad, sigue hasta que el usuario la
pausa o la borra.

**Pausar no es borrar.** Una regla pausada deja de generar y se puede reanudar. Una regla
borrada queda marcada con quién y cuándo, y no genera más; lo que ya generó sigue siendo
movimientos comunes, que se borran uno por uno.

**En una tarjeta, la regla genera al cierre del resumen.** Si la cuenta de la regla es una
tarjeta de crédito, cada ocurrencia se agenda igual que en cualquier regla, pero no se genera
en su fecha: entra en el resumen que la incluye y se genera al cerrarse ese resumen, con fecha
igual al vencimiento (§ 13).

**Sin período confirmado, el recurrente queda pendiente.** Si en la fecha de ejecución el dueño
no tiene un período confirmado que la cubra, porque no existe o porque sigue en `draft`, el
motor no descarta el gasto ni lo imputa a un borrador: crea una `PENDING_TRANSACTION` con todo
completo salvo el período, que entra en la fila de lotes como cualquier otro pendiente (§ 5).
El asistente avisa, por ejemplo: "Se generó el alquiler de $500.000, pero no tenés presupuesto
confirmado para octubre. ¿Lo confirmás?". La misma clave de unicidad aplica al pendiente, así
una doble ejecución tampoco duplica el aviso.

**Si hace falta convertir, el recurrente también queda pendiente.** Cuando la moneda de la
cuenta de la regla no es la del período que cubre la fecha, el motor no aplica una cotización
por su cuenta, porque ninguna se aplica sin que el usuario vea el resultado (§ 6). Crea una
`PENDING_TRANSACTION` con todo completo salvo la cotización del presupuesto, con el valor
sugerido a la vista, y sigue el mismo camino que el pendiente sin período: no vence y se recuerda
cada 3 días.

Ver también: [1.2, movimientos recurrentes](01-producto.md#12-características-y-funcionalidades-principales) · [RECURRING_RULE en 3.2](03-modelo-de-datos.md#recurring_rule) · [restricción XOR en 3.2](03-modelo-de-datos.md#recurring_rule).

## 9. Trazabilidad de origen (`source`)

El valor de `source` no es opcional ni inferible después: se fija al crear la fila y habilita
tanto la auditoría como el chequeo de duplicados del grupo 7. Qué registra y para qué, en los
enlaces de abajo.

Ver: [1.2, trazabilidad de origen](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#transaction) · [HU4](05-historias-de-usuario.md).

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

**Cómo se entrega la exportación.** Es un archivo Excel con dos hojas. "Movimientos" lista cada
movimiento del grupo con fecha, tipo, monto, moneda, cuenta, categoría, período, quién lo
registró y origen. "Presupuestos" lista cada período con su ingreso estimado y, por categoría,
el tope y lo gastado. Se descarga desde el dashboard, detrás del login: el archivo no viaja por
WhatsApp, para que las finanzas de toda la familia no queden guardadas en el chat ni en sus
respaldos. Por WhatsApp solo va un aviso de que está disponible. El archivo no se guarda: se
genera en el momento de descargarlo, con los datos de los períodos que ese usuario puede leer,
así que siempre está al día y no hay una copia de más que custodiar.

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

**Los recurrentes hacia el grupo se pausan.** Al salir, cada `RECURRING_RULE` del usuario con
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

Ver también: [FAMILY_GROUP / USER_GROUP en 3.2](03-modelo-de-datos.md#family_group-y-user_group) · [§ 5, pendientes](#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración) · [§ 8, recurrentes](#8-movimientos-recurrentes-la-excepción-a-la-confirmación) · [decisiones abiertas](hoja-de-ruta.md#decisiones-abiertas).

## 11. Alta de usuario, consentimiento y mensajes proactivos

**Sin consentimiento no se guarda nada.** Cuando escribe un número que Platita no conoce, lo
primero es pedirle que acepte los términos y la política de privacidad. Hasta que acepta, no se
guarda nada más que el mensaje recibido, y no se procesa con IA. Se registra cuándo aceptó y qué
versión de los términos.

**El alta tiene una parte obligatoria y corta.** Es lo mínimo para registrar el primer gasto:

1. Consentimiento de términos y política de privacidad.
2. Nombre y país. Del país se sugiere la moneda primaria, que el usuario confirma, y, si existe,
   la fuente de cotización; en Argentina se le pregunta cuál prefiere (por ejemplo, MEP u
   oficial). La zona horaria se deduce del país sin preguntar; solo si el país tiene más de una
   (por ejemplo, Brasil o México) se le pide que elija.
3. Permiso para recibir avisos (ver abajo).
4. Al menos una cuenta, con la opción de dar de alta varias en el mismo mensaje. Por cada una se
   confirma tipo, moneda y saldo inicial, que es el saldo de ese día.

Hasta completarla, el usuario no puede registrar movimientos.

**El primer mensaje no se pierde.** Si lo primero que escribió fue un gasto, queda guardado y,
al terminar la parte obligatoria, se retoma como un pendiente normal (§ 5), sin pedirle que lo
repita.

**La configuración y el perfil son opcionales.** Al terminar la parte obligatoria, el asistente
ofrece seguir, o dejarlo para otro día:

- **Categorías.** El usuario ya tiene el catálogo base, así que nunca queda sin categorías. Se
  le muestran y puede sumar propias, de gasto o de ingreso (§ 4).
- **Perfil financiero**, para que los consejos se crucen con su situación real: ingreso mensual
  aproximado (por rangos, no exacto), cuántas personas dependen de ese ingreso, si tiene deudas,
  si tiene fondo de emergencia y de cuántos meses, su objetivo principal (ahorrar, salir de
  deudas, armar un fondo de emergencia o empezar a invertir) y con cuánto riesgo se siente
  cómodo al invertir.

Cada pregunta se puede saltear, y todo se completa o cambia después desde el dashboard. El
perfil guarda cuándo se actualizó, para que un consejo sepa si el dato puede haber quedado viejo.

**Mensajes proactivos: solo con permiso.** Un mensaje es proactivo cuando Platita lo inicia sin
estar respondiendo a algo que el usuario acaba de escribir: alertas de presupuesto (HU5),
recordatorios de pendientes (§ 5), recordatorio de período sin confirmar (§ 3) y aviso de
recurrente o cuota por confirmar (§ 8 y § 13). Si el usuario no dio permiso para avisos, Platita nunca le envía
uno. Lo que sí puede hacer es mencionarlo dentro de una respuesta a algo que el usuario
escribió, por ejemplo al confirmar un gasto: "Listo. Ojo, vas al 82% del rubro". El permiso se
puede dar o retirar en cualquier momento.

**Los códigos no son avisos.** El de login y el de borrado de cuenta se envían porque el usuario
los pidió en ese momento, así que no dependen del permiso para avisos.

**Fuera de la ventana de conversación, plantilla.** WhatsApp permite responder con texto libre
solo dentro de las 24 horas posteriores al último mensaje del usuario. Pasado ese plazo, todo
mensaje de Platita tiene que ser una plantilla aprobada por Meta, que además se paga por envío.
Las que hacen falta son:

| Plantilla | Categoría en Meta | Cuándo se usa |
|---|---|---|
| Código de login | Autenticación | Al pedir entrar al dashboard |
| Código de borrado de cuenta | Autenticación | Al pedir borrar la cuenta |
| Alerta de presupuesto | Utilidad | Al pasar un umbral |
| Pendientes sin confirmar | Utilidad | Antes de vencer, o cada 3 días si son de un recurrente |
| Período sin confirmar | Utilidad | Cerca del inicio de un período que sigue en `draft` |
| Recurrente o cuota por confirmar | Utilidad | Cuando un recurrente o una cuota de tarjeta no encuentra período confirmado, o necesita que el usuario confirme la cotización |

Ver también: [HU6](05-historias-de-usuario.md) · [APP_USER y FINANCIAL_PROFILE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [OUTBOUND_MESSAGE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales).

## 12. Límites de uso del asistente

Cada mensaje que el asistente interpreta o responde con IA tiene un costo, y Platita está
abierta a cualquier persona. Sin límites, un uso abusivo, o un error que dispare mensajes en
bucle, se traslada directo a la factura del proveedor de LLM.

**Dos cuotas diarias por usuario, separadas.**

| Cuota | Qué cuenta | Límite inicial |
|---|---|---|
| Registro | Mensajes interpretados para cargar, completar o corregir movimientos, incluidas las respuestas del alta | 50 por día |
| Consejos | Consultas respondidas con la base de conocimiento financiero | 10 por día |

Están separadas porque registrar es el núcleo del producto y no puede quedar bloqueado porque el
usuario hizo muchas preguntas. El día es el día calendario en la zona horaria del usuario
(`time_zone`). Los límites son configuración, no valores escritos en el código, para poder ajustarlos
sin desplegar.

**Superar una cuota no pierde nada.**

- **Registro:** el mensaje se guarda igual y queda sin procesar hasta que la cuota se renueva al
  día siguiente. El asistente responde con un texto fijo, sin llamar al LLM, que avisa que lo va
  a procesar mañana. Perder un gasto que el usuario escribió sería peor que demorarlo.
- **Consejos:** el asistente responde con un texto fijo que avisa que llegó al límite de
  consultas del día. Registrar movimientos sigue funcionando.

**Un tope global mensual como corte de emergencia.** Además de las cuotas por usuario, la cuenta
del proveedor de LLM tiene un límite de gasto mensual de 20 dólares, configurado en la consola
del proveedor y no en Platita. Es el último resguardo: si algo se sale de control, la factura no
pasa de ese monto. Cuando se alcanza, el proveedor rechaza las llamadas y el worker lo trata como
una caída del LLM: reintenta y, si se agotan los intentos, el mensaje queda en `failed` y el
usuario recibe el aviso de que no se pudo procesar. Además avisa a quien opera Platita, que
decide si subir el tope. Hasta entonces, el asistente no puede interpretar mensajes de nadie.

Ver también: [LLM_USAGE en 3.2](03-modelo-de-datos.md#llm_usage) · [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md), por cómo se reintentan los mensajes.

## 13. Tarjetas de crédito y transferencias

**Transferencias entre cuentas propias.** Mover plata entre dos cuentas del mismo usuario (sacar
efectivo, pasar de un banco a una billetera, comprar dólares, pagar la tarjeta) es una
transferencia, no un gasto ni un ingreso. Baja el saldo de una cuenta y sube el de otra, y no
entra en ningún presupuesto ni en ninguna alerta. Cada lado va en la moneda de su cuenta; si las
monedas difieren, se guarda la cotización usada y, como toda conversión, se confirma con el
usuario (§ 6). Origen y destino son cuentas distintas del mismo usuario.

**La tarjeta es una cuenta.** Una tarjeta de crédito es una cuenta de tipo `credit_card`, con un
día de cierre y un día de vencimiento. Por la regla de una moneda por cuenta (§ 2), una tarjeta
con consumos en pesos y en dólares se da de alta como dos cuentas, igual que los dos saldos de su
resumen.

**Un gasto con tarjeta pesa en el presupuesto del mes en que vence, no en el de la compra.** El
presupuesto se piensa como flujo de caja: una compra del 20 de septiembre que vence el 5 de
octubre afecta octubre. Una compra hecha después del cierre entra en el resumen siguiente y
afecta el mes de ese vencimiento.

**Una compra con tarjeta es una regla recurrente.** Se registra como una regla mensual (§ 8)
sobre la cuenta de la tarjeta, con el monto de cada cuota y tantas ocurrencias como cuotas; una
compra en un pago tiene una sola. Si el usuario dice el total, el asistente divide, propone el
monto de la cuota y el usuario lo confirma o lo corrige con el de su resumen. Al comprar, y una
sola vez, el usuario confirma si va a su presupuesto o al familiar. Una suscripción pagada con la
tarjeta es una regla igual, pero sin límite de ocurrencias. El fundamento está en el
[ADR 0012](adr/0012-tarjetas-de-credito-y-transferencias.md).

**Cada ocurrencia se genera al cerrar el resumen.** Al cerrar cada resumen, el sistema genera,
por cada ocurrencia de las reglas de esa tarjeta que entra en él, un gasto sobre la cuenta de la
tarjeta con fecha igual al vencimiento, imputado al período confirmado de ese dueño que cubre
esa fecha. Si ese período no está confirmado, o si la moneda de la tarjeta no es la del período,
la ocurrencia queda pendiente igual que la de cualquier regla recurrente (§ 8): no vence y se
recuerda cada 3 días. Una regla genera como mucho un movimiento, o un pendiente, por ocurrencia,
y una regla borrada no genera más (§ 2).

**Resúmenes.** Las fechas de cierre y vencimiento de cada resumen se generan a partir de los días
fijos de la tarjeta, y el usuario puede corregirlas para un resumen puntual, porque los bancos a
veces las corren. Un resumen ya cerrado no se corrige.

**Pagar el resumen es una transferencia** de una cuenta del usuario a la tarjeta. Si paga el
saldo en dólares con pesos, la transferencia tiene un monto en cada moneda, y la percepción
impositiva que cobre el banco se registra aparte como un gasto que el usuario confirma.

**Saldo, deuda y comprometido.** Como en cualquier cuenta (§ 2), el saldo de la tarjeta cuenta
solo lo que ya ocurrió: los gastos ya vencidos menos los pagos recibidos. Lo facturado en un
resumen que todavía no venció no es saldo, es deuda: se muestra aparte como lo que hay que pagar
en el próximo vencimiento, que es el total del resumen del banco. Un pago cancela primero lo
vencido y después esa deuda, así que pagar antes del vencimiento la reduce en el momento. Lo
comprometido a futuro, las ocurrencias de sus reglas todavía no generadas, se muestra aparte y
por período en el dashboard, para que un mes cargado de cuotas no sea una sorpresa.

Ver también: [ADR 0012](adr/0012-tarjetas-de-credito-y-transferencias.md) · [ACCOUNT, RECURRING_RULE, CARD_STATEMENT y TRANSFER en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales).

## 14. Privacidad: retención, borrado de cuenta y derechos

**El texto de los mensajes se guarda por un plazo limitado.** Pasado el plazo desde que un
mensaje se procesó, se borra su contenido (el texto y el teléfono en los mensajes recibidos y
enviados, y el mensaje original guardado en un pendiente) y quedan solo los metadatos: cuándo
llegó, si se procesó y la clave que evita duplicados. Los movimientos, saldos y presupuestos que
salieron de ese mensaje no se tocan. El plazo es configurable, con un valor por defecto de 60
días. Nada se borra mientras lo necesite un pendiente o un lote todavía abierto.

**Qué se pierde con eso, y por qué se acepta.** Pasado el plazo no se puede mostrar qué escribió
el usuario ante un reclamo tardío, ni reproducir un error viejo con el mensaje que lo causó. Se
acepta porque cada movimiento ya fue confirmado por el usuario con un mensaje que lista su monto,
y porque el usuario conserva su propia copia de la conversación en WhatsApp. Para mejorar la
interpretación, antes del vencimiento se pueden guardar aparte, a mano y anonimizados, casos de
prueba elegidos.

**Borrado de cuenta.** El usuario puede pedir borrar su cuenta, por WhatsApp o desde el
dashboard:

1. Antes de confirmar se le ofrece descargar todos sus datos.
2. Confirma con un código de un solo uso, que llega por WhatsApp y solo sirve para borrar la
   cuenta. Desde el dashboard, exige tener el teléfono además de la sesión. Por WhatsApp, el
   código llega al mismo chat: no protege contra quien tiene el teléfono, pero hace que ninguna
   frase mal interpretada dispare el borrado. Contra quien tiene el teléfono, la defensa es el
   plazo de gracia.
3. Si es dueño de un grupo familiar, primero transfiere el rol, como al salir (§ 10).
4. La cuenta queda desactivada durante un plazo de gracia, configurable y de 7 días por
   defecto, en el que puede cancelar el borrado. Al pedirlo se cierran todas sus sesiones del
   dashboard; puede volver a entrar con un código para cancelar. Durante ese plazo no recibe
   mensajes proactivos.
5. Vencido el plazo, se borra lo personal: teléfono, nombre, perfil financiero, cuentas,
   presupuestos individuales, movimientos que no son de un presupuesto familiar, pendientes,
   mensajes, códigos de login y sesiones.
6. Lo compartido se anonimiza en vez de borrarse: los movimientos que imputó a presupuestos
   familiares quedan, porque el grupo los sigue necesitando (§ 10), pero registrados por un "ex
   miembro": se quita quién los registró. Lo mismo vale para la cuenta y la categoría que esos
   movimientos referencian, que pasan a tener nombres genéricos numerados ("Cuenta 1", "Cuenta 2"),
   porque los nombres son únicos por usuario. La descripción de cada movimiento se conserva tal como la escribió,
   porque es parte de lo que el grupo ve, así que puede seguir nombrando personas o lugares.

**Derechos del usuario.**

- **Acceso:** puede descargar en cualquier momento todos sus datos en Excel desde el dashboard.
- **Rectificación:** puede corregir sus datos desde el dashboard, y sus movimientos también por
  WhatsApp. Un movimiento ya confirmado que se corrige queda marcado con cuándo y quién lo
  corrigió por última vez; el valor anterior no se conserva
  ([ADR 0014](adr/0014-marca-de-edicion-en-movimientos.md)).
- **Supresión:** el borrado de cuenta descrito arriba.

**Datos que salen hacia el proveedor de LLM.** Nunca se envían identificadores (teléfono, nombre,
email ni ids internos), solo lo necesario para la tarea. El detalle está en el
[ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md).

Ver también: [Términos y política de privacidad](terminos-y-privacidad.md) · [APP_USER, INBOUND_MESSAGE y OUTBOUND_MESSAGE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales).
