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

**Gasto, ingreso o transferencia lo clasifica el modelo, y se ve en la confirmación.** Un mensaje
como "le pasé 300 lucas a MP" puede ser una transferencia entre cuentas propias o un pago a otra
persona, y "le pasé 30 a Juan", un préstamo (§ 16) o un pago. El modelo elige el tipo al
interpretar el mensaje, sin una pregunta previa. Lo que lo hace seguro no depende del modelo:

- **La confirmación dice el tipo y su efecto:** "Transferencia de $300.000 de Galicia a Mercado
  Pago. No cuenta como gasto", o "Gasto de $30.000 · Juan · varios". El usuario ve siempre qué se
  va a registrar antes de confirmarlo.
- **Una transferencia necesita dos cuentas propias.** Si el modelo la clasifica como transferencia
  y el destino o el origen no es una cuenta del usuario, esa cuenta falta y se pregunta como
  cualquier dato que falta (§ 5). Nunca se inventa una cuenta.
- **Se corrige con una respuesta corta.** Antes de confirmar, "no, era un gasto" cambia el tipo
  del pendiente y el asistente pregunta lo que el tipo nuevo necesite, como la categoría o el
  presupuesto. Después de confirmado, se corrige como cualquier movimiento (§ 15).

**Desde el dashboard, las mismas reglas.** El dashboard carga gastos, ingresos y transferencias
([ADR 0002](adr/0002-whatsapp-como-canal-principal.md)). En el formulario, la cuenta y el
presupuesto no vienen preseleccionados: el usuario los elige, porque un campo ya elegido que se
envía sin mirar sería un valor por defecto encubierto. La fecha, la moneda y la categoría pueden
venir sugeridas y a la vista, igual que en la confirmación por WhatsApp. Enviar el formulario es
la confirmación. Las compras con tarjeta y las reglas recurrentes se cargan solo por WhatsApp, y
también un pago con pesos de una tarjeta en otra moneda, porque puede dejar un residuo que se
confirma conversando (§ 13).

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

**Una vez por mes, el saldo se contrasta con el real.** Por más cuidado que ponga el usuario, el
saldo de Platita se separa del real: gastos que no cargó, comisiones, rendimientos, efectivo
usado sin registrar. Al terminar cada mes de presupuesto (el fin de su período individual
mensual, o el fin de mes si sus períodos son quincenales o solo familiares), el asistente manda
un solo mensaje con el saldo de cada cuenta, salvo las tarjetas, que se concilian contra su
resumen (§ 13), las cuentas "Me deben", cuyo saldo no existe fuera de Platita (§ 16), y las
cuentas de inversión, cuyo valor cambia con el mercado (ver abajo). Y pregunta si coincide. Si no coincide, el usuario dice cuánto tiene y el
asistente primero ayuda a encontrar lo que falta cargar, que se registra como cualquier
movimiento. Lo que quede sin explicar se registra como un ajuste confirmado por el usuario,
imputado al período que terminó, con su último día como fecha: un gasto en la categoría base
"Faltantes sin identificar" si falta plata, o un ingreso en "Sobrantes sin identificar" si
sobra. Si el usuario reconoce lo que sobra como un rendimiento de una cuenta remunerada o de un
plazo fijo, es un ingreso en la categoría base "Rendimientos", y si lo reconoce como un
reintegro, en "Devoluciones y reintegros" (§ 16). El ajuste pesa en el presupuesto, porque un
gasto olvidado es plata que salió. Responder no es obligatorio: sin
respuesta, ese mes queda sin contrastar y se vuelve a preguntar al siguiente.

**Una cuenta de inversión solo recibe aportes y retiros.** Una cuenta de tipo broker, como la de
un agente de bolsa, se mueve solo con transferencias desde y hacia otras cuentas propias (§ 13):
aportar es transferirle plata, y retirar es transferir desde ella. No lleva gastos, ingresos ni
reglas recurrentes, y la base lo impone. Lo que pasa adentro, como comprar CEDEARs, cobrar
dividendos o la suba y baja de los precios, no se registra. Por eso su saldo es lo aportado
neto: lo transferido menos lo retirado. Puede quedar negativo, si el usuario retiró más de lo que
aportó, y el dashboard lo muestra como "aportado neto" y no como saldo. Platita no sabe cuánto
vale la cartera, y la cuenta no entra en el contraste mensual.

**Borrar un movimiento.** El usuario puede borrar un gasto, un ingreso, una transferencia o una
regla recurrente que ya confirmó, incluida una compra con tarjeta. El movimiento queda marcado
como borrado, con quién y cuándo, y deja de contar en el saldo, en el gastado de los
presupuestos y en las alertas. Borrar una regla corta las ocurrencias que faltaban generar,
como las cuotas pendientes de una compra; las ya generadas se borran una por una (§ 8 y § 13).
Cómo se pide por WhatsApp, y cómo se restaura lo borrado, está en § 15. El fundamento está en el
[ADR 0015](adr/0015-borrado-logico-de-movimientos.md).

**Una cuenta, una moneda.** Cada cuenta tiene una sola moneda, igual que en el banco, donde una
cuenta en pesos y otra en dólares de la misma entidad son dos cuentas distintas. Un movimiento
puede estar en otra moneda que su cuenta, como "gasté 50 dólares con la Galicia pesos", pero el
saldo suma cada movimiento ya convertido a la moneda de la cuenta (§ 6), así que nunca suma
montos de monedas distintas. La moneda de una cuenta no se puede cambiar: una cuenta en otra
moneda es otra cuenta.

**Una stablecoin es una cuenta en dólares.** Las monedas son las del catálogo ISO 4217, y USDT o
USDC no están en él. Una stablecoin que sigue al dólar se registra en una cuenta en USD, real y
con su propio nombre, como "Binance USDT", y sus movimientos son en dólares. Que la stablecoin
pierda la paridad no se modela. Una cripto volátil, como BTC, va en una cuenta de inversión, que
solo recibe aportes y retiros (ver abajo).

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

**El primer período nace en el alta.** Al completar la parte obligatoria del alta (§ 11), el
sistema crea el primer período individual del usuario, ya confirmado: mensual, en su moneda
primaria, con ingreso estimado 0 y sin topes, desde el día del alta hasta el último día de ese
mes. Es la única excepción a que un período se confirme antes de arrancar, porque ya arrancó. Así
el primer gasto, incluido el que el usuario escribió antes de darse de alta, tiene dónde
imputarse. Un período sin topes registra el gastado igual, pero no dispara alertas. El mensaje
que cierra el alta le avisa que ese primer período existe y que puede ponerle ingreso y topes
desde el dashboard.

**Un período mensual puede empezar cualquier día.** Termina el día anterior al mismo día del mes
siguiente: uno que empieza el 10 de octubre termina el 9 de noviembre. Si ese día no existe en el
mes, como el 31, se usa el último día del mes, igual que en las reglas recurrentes (§ 8). El
período siguiente empieza el día después de que termina el anterior. Para mover el día de
inicio, por ejemplo para alinearlo con el cobro, el usuario cambia las fechas de un borrador, y
desde ahí los siguientes se calculan a partir de ese. El período de transición puede durar más o
menos de un mes.

**El borrador copia el período anterior.** Con anticipación al inicio de cada período, el sistema
genera el borrador del siguiente para el mismo dueño, copiando del último período: la cadencia,
la moneda, el ingreso estimado y cada tope. La anticipación con que se genera y la del
recordatorio son configuración, igual que las cuotas de uso (§ 12). La sugerencia ajustada por
inflación (could-have) reemplazará a la copia cuando exista, sin cambiar el resto de la regla.

**Dónde se arma y dónde se confirma.**

- **Confirmar tal cual, por WhatsApp.** El recordatorio de período sin confirmar lista el ingreso
  estimado y los topes del borrador, y las reglas recurrentes de monto variable que vencen en el
  período, numeradas y con su último monto (§ 8). Si el usuario responde que lo confirma, pasa a
  `confirmed` sin cambios. Puede corregir montos de esas reglas en la misma respuesta ("el 1 es
  850.356"), o dejar alguno sin confirmar. Los topes no se cambian por WhatsApp. La respuesta usa
  la cuota de registro.
- **Armar o cambiar, en el dashboard.** Crear un período, cambiar sus fechas, el ingreso estimado
  o los topes, y confirmarlo, se hace en el dashboard. Por WhatsApp no se editan topes: el
  recordatorio incluye el enlace para hacerlo.
- **Sin confirmar al empezar.** Si un período empieza sin confirmar, lo que caiga en él queda
  pendiente como siempre. La pregunta de ese pendiente ofrece confirmar el borrador en el mismo
  mensaje, con su resumen, y una sola respuesta confirma las dos cosas. Si no hay borrador, como en
  un grupo familiar que todavía no tiene ningún período, la pregunta manda al dashboard para
  armarlo.

**Alertas de presupuesto.** Cuando el gastado de una categoría con tope pasa el 80% y cuando pasa
el 100% del tope, el asistente manda una alerta proactiva ([HU5](05-historias-de-usuario.md)).
Los dos umbrales son iguales para todos los usuarios y están en la configuración, igual que las
cuotas de uso (§ 12). Cada umbral se avisa una sola vez por categoría y período, aunque un
reintegro baje el gastado y después vuelva a subir. En un presupuesto familiar, la alerta le
llega a cada miembro vigente que dio permiso para avisos (§ 11). Una categoría sin tope no manda
alertas.

**En un presupuesto familiar confirma el dueño.** Solo el dueño vigente del grupo (§ 10) crea,
cambia y confirma los períodos familiares, desde el dashboard o respondiendo al recordatorio, que
recibe solo él. Los demás miembros ven el borrador. Si un miembro imputa algo a un período
familiar que todavía no está confirmado, su pendiente espera: la pregunta le dice que falta la
confirmación del dueño y le ofrece imputarlo a su presupuesto individual.

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

**Un pendiente también puede ser un cambio sobre un movimiento ya confirmado:** una corrección,
un borrado o una restauración que espera que el usuario elija el movimiento o confirme el cambio
(§ 15). Tiene `intent = 'change'`, guarda en `parsed_data` qué movimiento o qué candidatos y qué
cambio, y al confirmarse aplica el cambio sobre el movimiento existente en vez de crear uno.

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
  permite contestar fuera de orden sin ambigüedad. Si el mensaje citado es la confirmación de un
  lote ya cerrado, la respuesta es un pedido de corrección, borrado o restauración de los
  movimientos de ese lote (§ 15). Si no es ninguna de las dos cosas —una alerta, la pregunta de
  un lote ya cerrado—, la respuesta se procesa como si no citara nada.
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
en el [ADR 0011](adr/0011-cotizaciones-con-adaptador-generico-configurable.md). Una tarjeta en
otra moneda no usa la cotización de referencia sino la de cómo se paga su resumen, que en
Argentina puede ser la fuente del dólar tarjeta (§ 13).

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

**Entre miembros de un grupo, se pregunta antes de confirmar.** Dos miembros pueden cargar el
mismo gasto al presupuesto del grupo, por ejemplo el super que pagó uno. Antes de confirmar un
movimiento imputado a un período de grupo, el asistente busca si otro miembro ya registró uno con
el mismo monto y la misma moneda en ese período, el mismo día o con un día de diferencia. Si lo
encuentra, pregunta: "Sofía ya cargó $92.000 en super hoy al presupuesto del grupo. ¿Es el mismo
gasto?". Si el usuario dice que sí, el pendiente se rechaza y no se registra nada. Si dice que no,
se registra normalmente. El sistema nunca lo descarta solo, y no muestra nada que el miembro no
viera ya, porque los miembros ven los movimientos del grupo.

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

**El monto de una regla es fijo o variable.** Al dar de alta una regla sin fin, el asistente
pregunta si el monto es siempre el mismo, y la regla queda marcada como fija o variable. El
usuario puede cambiar la marca después. Una regla con fin, como las cuotas de una compra con
tarjeta o de un préstamo, es siempre fija. Una regla fija genera su movimiento completo en cada
ciclo, sin preguntar. Una regla variable, como el alquiler que se ajusta por un índice, la luz o
la jubilación, solo genera su movimiento sin preguntar si el monto de ese ciclo ya está
confirmado. Un monto se confirma en uno de dos momentos:

1. **Al armar el presupuesto.** El borrador de cada período lista las reglas variables que
   vencen en él, con el último monto confirmado (§ 3). Confirmar el período confirma esos montos
   tal como se listaron, o con los que el usuario corrija en la respuesta. El usuario puede
   dejar alguno sin confirmar si todavía no lo sabe: "la luz todavía no sé". La regla guarda el
   monto confirmado y hasta qué fecha vale, que es el fin de ese período.
2. **Al vencer.** Una ocurrencia de una regla variable cuyo monto no quedó confirmado para su
   fecha no se genera como movimiento: queda pendiente, con todo completo salvo el monto y con
   el último monto confirmado como sugerencia. El asistente pregunta si es el mismo o cambió.
   Sigue el mismo camino que el pendiente sin período: no vence y se recuerda cada 3 días.

La sugerencia es siempre el último monto que el usuario confirmó, no el del alta de la regla.
Cuando exista la carga por email (could-have), la factura detectada completa el monto de ese
pendiente, y el asistente pide confirmarlo igual que cualquier monto.

**Pausar no es borrar.** Una regla pausada deja de generar y se puede reanudar. Una regla
borrada queda marcada con quién y cuándo, y no genera más; lo que ya generó sigue siendo
movimientos comunes, que se borran uno por uno.

**Lo que falta pagar es comprometido.** Las ocurrencias que le quedan a una regla con fin, por
su monto, son lo comprometido a futuro: se muestran aparte y por período en el dashboard, para
que un mes cargado de cuotas no sea una sorpresa. Vale igual para las cuotas de una tarjeta
(§ 13) que para las de un préstamo.

**Un préstamo es un ingreso y una regla de cuotas.** Cuando el usuario cuenta que sacó un
préstamo, el asistente registra dos cosas, que confirma en el mismo mensaje: un ingreso por el
monto recibido, en la cuenta donde entró, y una regla recurrente de gasto con el monto de la
cuota y la cantidad de cuotas como fin. Así el presupuesto refleja el flujo de caja, como en las
tarjetas: el mes del préstamo, el ingreso compensa lo que se compre con esa plata, y después
pesa cada cuota, con sus intereses incluidos. Lo que queda por devolver es lo comprometido de la
regla. Van en categorías propias del usuario, "Préstamos recibidos" y "Cuotas de préstamos", que
se crean con confirmación como cualquier categoría nueva (§ 4) si todavía no existen.

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

**Si el monto es variable y no está confirmado, el recurrente también queda pendiente.** Es el
tercer caso en que el motor no genera el movimiento completo. La regla está arriba, en "El monto
de una regla es fijo o variable". Un mismo pendiente puede esperar más de un dato, por ejemplo el
monto y la confirmación del período, y se pregunta todo junto.

Ver también: [1.2, movimientos recurrentes](01-producto.md#12-características-y-funcionalidades-principales) · [RECURRING_RULE en 3.2](03-modelo-de-datos.md#recurring_rule) · [restricción XOR en 3.2](03-modelo-de-datos.md#recurring_rule).

## 9. Trazabilidad de origen (`source`)

El valor de `source` no es opcional ni inferible después: se fija al crear la fila y habilita
tanto la auditoría como el chequeo de duplicados del grupo 7. Qué registra y para qué, en los
enlaces de abajo.

Ver: [1.2, trazabilidad de origen](01-producto.md#12-características-y-funcionalidades-principales) · [TRANSACTION en 3.2](03-modelo-de-datos.md#transaction) · [HU4](05-historias-de-usuario.md).

## 10. Grupos familiares: administración, salida y visibilidad

**Un grupo puede ser una familia o una actividad.** Además de una familia, un grupo puede ser una
actividad del usuario, como el consultorio de una monotributista: un grupo de un solo miembro,
que es su dueño. Su presupuesto separa los gastos y los cobros de la actividad de los personales,
sin cuentas ficticias, porque en Platita la cuenta y el presupuesto son independientes: la misma
cuenta real puede alimentar el presupuesto individual y el del grupo. Todo lo de esta sección
vale igual para los dos. No hay un campo que diga de qué tipo es: el asistente y el dashboard
nombran cada presupuesto por el nombre del grupo, así que el usuario nunca ve la palabra
"familiar" en un grupo que no lo es. En la base, la tabla sigue siendo `FAMILY_GROUP`.

**El retiro del titular.** Si los cobros de una actividad van al presupuesto del grupo, el
presupuesto individual se queda sin esos ingresos. Lo que la educación financiera llama
"pagarse un sueldo" se registra como un retiro: dos movimientos sobre la misma cuenta, por el
mismo monto y con la misma fecha, que se confirman juntos en un solo mensaje. Uno es un gasto en
el período del grupo, en la categoría base "Retiro del titular". El otro es un ingreso en el
período individual, en la categoría base "Retiro de la actividad". El saldo de la cuenta no
cambia, porque se compensan. Los dos quedan enlazados: corregir o borrar uno corrige o borra el
otro (§ 15). En un total que suma más de un presupuesto del mismo usuario, los retiros no se
cuentan, porque son plata que cambió de presupuesto y no salió ni entró. Con una cuenta real
separada para la actividad, el retiro es una transferencia común (§ 13).

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
todos los movimientos imputados a ellos, sin importar qué miembro los registró. También ven
cuánto imputó cada miembro al período, en el dashboard y en las consultas (§ 17). Platita no
calcula quién le debe a quién: saldar cuentas entre miembros exige transferencias entre usuarios
distintos, que quedan para cuando exista la cuenta compartida del grupo
([hoja de ruta](hoja-de-ruta.md#decisiones-abiertas)). Un
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

Hasta completarla, el usuario no puede registrar movimientos. Al completarla, el sistema crea su
primer período de presupuesto, ya confirmado (§ 3).

**El primer mensaje no se pierde.** Si lo primero que escribió fue un gasto, queda guardado y,
al terminar la parte obligatoria, se retoma como un pendiente normal (§ 5), sin pedirle que lo
repita. El período que propone es ese primer período.

**La configuración y el perfil son opcionales.** Al terminar la parte obligatoria, el asistente
ofrece seguir, o dejarlo para otro día:

- **Categorías.** El usuario ya tiene el catálogo base, así que nunca queda sin categorías. Se
  le muestran y puede sumar propias, de gasto o de ingreso (§ 4).
- **Perfil financiero**, para que los consejos se crucen con su situación real: ingreso mensual
  aproximado (por rangos, no exacto), cuántas personas dependen de ese ingreso, si tiene deudas,
  si tiene fondo de emergencia y de cuántos meses, y su objetivo principal (ahorrar, salir de
  deudas, armar un fondo de emergencia o empezar a invertir). No se pregunta la tolerancia al
  riesgo al invertir: los consejos no eligen instrumentos (§ 18), así que no tendría uso.

Cada pregunta se puede saltear, y todo se completa o cambia después desde el dashboard. El
perfil guarda cuándo se actualizó, para que un consejo sepa si el dato puede haber quedado viejo.
Si el usuario responde que tiene deudas, el asistente le ofrece crear sus categorías para
préstamos, "Préstamos recibidos" y "Cuotas de préstamos" (§ 8), y las crea solo si confirma.

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
| Alerta de presupuesto | Utilidad | Al pasar el 80% y el 100% del tope de una categoría. En un presupuesto familiar, a cada miembro con permiso |
| Pendientes sin confirmar | Utilidad | Antes de vencer, o cada 3 días si son de un recurrente |
| Período sin confirmar | Utilidad | Cerca del inicio de un período que sigue en `draft`: lista su ingreso y sus topes, y se confirma respondiendo. En un período familiar, solo al dueño |
| Recurrente o cuota por confirmar | Utilidad | Cuando un recurrente o una cuota de tarjeta no encuentra período confirmado, necesita que el usuario confirme la cotización, o es de monto variable y su monto no está confirmado. Las ocurrencias variables de una tarjeta no usan esta plantilla: se preguntan en la conciliación |
| Conciliación del resumen | Utilidad | Unos días después del cierre de un resumen de tarjeta: pide los montos de las suscripciones variables sin confirmar, en una tarjeta en otra moneda cómo se va a pagar y la cotización del resumen, y el total del banco. Antes del ajuste pregunta por compras sin cargar, y recomienda revisar los consumos |
| Saldos del mes | Utilidad | Al terminar cada mes de presupuesto: muestra el saldo de cada cuenta y pregunta si coincide con el real |

Ver también: [HU6](05-historias-de-usuario.md) · [APP_USER y FINANCIAL_PROFILE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [OUTBOUND_MESSAGE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales).

## 12. Límites de uso del asistente

Cada mensaje que el asistente interpreta o responde con IA tiene un costo, y Platita está
abierta a cualquier persona. Sin límites, un uso abusivo, o un error que dispare mensajes en
bucle, se traslada directo a la factura del proveedor de LLM.

**Tres cuotas diarias por usuario, separadas.**

| Cuota | Qué cuenta | Límite inicial |
|---|---|---|
| Registro | Mensajes interpretados para cargar, completar o corregir movimientos, incluidas las respuestas del alta | 50 por día |
| Consultas | Preguntas sobre los datos propios, respondidas con las funciones de lectura (§ 17). Cuenta una por pregunta, aunque el modelo llame a varias funciones | 20 por día |
| Consejos | Consultas respondidas con la base de conocimiento financiero | 10 por día |

Están separadas porque registrar es el núcleo del producto y no puede quedar bloqueado porque el
usuario hizo muchas preguntas. Una pregunta que necesita la base de conocimiento es un consejo,
aunque además use datos propios, y cuenta en esa cuota; una que solo usa datos propios es una
consulta. El día es el día calendario en la zona horaria del usuario
(`time_zone`). Los límites son configuración, no valores escritos en el código, para poder ajustarlos
sin desplegar.

**Superar una cuota no pierde nada.**

- **Registro:** el mensaje se guarda igual y queda sin procesar hasta que la cuota se renueva al
  día siguiente. El asistente responde con un texto fijo, sin llamar al LLM, que avisa que lo va
  a procesar mañana. Perder un gasto que el usuario escribió sería peor que demorarlo.
- **Consultas y consejos:** el asistente responde con un texto fijo, sin llamar al LLM, que avisa
  que llegó al límite del día, y ofrece el enlace al dashboard. Registrar movimientos sigue
  funcionando.

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
efectivo, pasar de un banco a una billetera, comprar dólares, pagar la tarjeta, prestarle plata a
alguien con una cuenta "Me deben", § 16) es una transferencia, no un gasto ni un ingreso. Baja el saldo de una cuenta y sube el de otra, y no
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
esa fecha. Si ese período no está confirmado, la ocurrencia queda pendiente igual que la de
cualquier regla recurrente (§ 8): no vence y se recuerda cada 3 días. Si la moneda de la tarjeta
no es la del período, también queda pendiente, pero sin aviso: su cotización se confirma una sola
vez para todo el resumen, en la conciliación (ver "Una tarjeta en otra moneda", más abajo). Si la regla es de monto variable, como una suscripción que sube de precio,
y su monto no quedó confirmado al armar el presupuesto, la ocurrencia también queda pendiente,
pero el cierre no avisa: se pregunta en la conciliación, donde el usuario tiene el resumen con el
precio real. Una regla genera como mucho un movimiento, o un pendiente, por ocurrencia,
y una regla borrada no genera más (§ 2).

**Resúmenes.** Las fechas de cierre y vencimiento de cada resumen se generan a partir de los días
fijos de la tarjeta, y el usuario puede corregirlas para un resumen puntual, porque los bancos a
veces las corren. Un resumen ya cerrado no se corrige.

**Pagar el resumen es una transferencia** de una cuenta del usuario a la tarjeta. Si paga el
saldo en dólares con pesos, la transferencia tiene un monto en cada moneda.

**Una tarjeta en otra moneda: una cotización por resumen, según cómo se paga.** Cuando la moneda
de la tarjeta, por ejemplo dólares, no es la del presupuesto, sus consumos no pesan con la
cotización de referencia del usuario, sino con la que corresponde a cómo se va a pagar el
resumen. En Argentina, pagar dólares con pesos cuesta el dólar tarjeta: el oficial más la
percepción.

- **Se pregunta en la conciliación.** Las ocurrencias de un resumen en dólares nacen pendientes
  de cotización al cierre, sin aviso, y el mensaje de la conciliación pregunta cómo se va a pagar
  el saldo: con dólares o con pesos. Con pesos, sugiere la cotización de la fuente del dólar
  tarjeta. Con dólares, la cotización de referencia del usuario (§ 6). El usuario la confirma una
  sola vez, y vale para todas las ocurrencias del resumen y para su ajuste de conciliación. El
  resumen guarda esa cotización.
- **Si paga antes de confirmar.** Si el usuario paga con pesos antes de que se confirme la
  cotización del resumen, la cotización del resumen es la que resulta del pago: los pesos que
  pagó divididos por los dólares que canceló.
- **El residuo al pagar.** Entre la conciliación y el pago, el dólar se mueve. Al registrar un
  pago con pesos, los dólares pagados se asignan como cualquier pago, primero a lo vencido y
  después a la deuda del próximo vencimiento, cada tramo con la cotización de su resumen. Si los
  pesos pagados no coinciden con esa cuenta, la diferencia se registra como un ajuste imputado
  al período del pago y confirmado en el mismo mensaje. Si pagó de más es un gasto en la
  categoría base "Diferencia de cambio", y si pagó de menos, un ingreso en "Diferencia de cambio
  a favor". Un pago con dólares propios no tiene residuo.
- **La percepción es parte del costo.** Queda incluida en lo que pesa cada consumo, en su
  categoría. Aunque es recuperable ante ARCA, separarla para mostrar cuánto se puede recuperar
  queda como mejora futura.

**Cada resumen se concilia contra el total del banco.** Un resumen trae cargos que no salen de
ninguna compra: intereses por no haber pagado el total, impuestos que cambian mes a mes,
percepciones y devoluciones. Platita no los calcula. El banco publica el resumen unos días
después del cierre, así que el asistente no pregunta el día del cierre: pregunta unos días
después, cuando el usuario ya puede tenerlo. La demora es configuración, con 3 días por
defecto. En ese mensaje pide primero los montos de las ocurrencias variables del resumen que
quedaron sin confirmar, numeradas y con su último monto, y después el total a pagar que figura
en el resumen del banco. Una respuesta general, como "todo igual, el total es 184.300", confirma
los montos sugeridos, igual que en un lote (§ 5). Recién con esos montos confirmados, compara el
total con lo que Platita tiene pendiente de pago en esa tarjeta: la deuda del próximo vencimiento más el saldo vencido que se
arrastra. Antes de registrar la diferencia como ajuste, muestra cuánto es y pregunta si falta
cargar alguna compra de ese resumen, con el enlace al dashboard donde ver lo registrado. Cada
compra que el usuario nombra se registra como una compra con tarjeta de ese resumen, en su
categoría, y la diferencia se recalcula. Si responde que está todo, no se registra ninguna. Lo
que queda sin explicar se registra como un solo movimiento de ajuste sobre la tarjeta, imputado
al período del vencimiento y confirmado por el usuario. Si el banco cobra de más, es un gasto en
la categoría base "Intereses, impuestos y cargos"; si cobra de menos, porque una devolución
superó a los cargos, es un ingreso en la categoría base "Devoluciones y reintegros". Desde ahí,
Platita coincide con el banco. Una tarjeta con saldo en pesos y en dólares son dos cuentas, y
cada una se concilia contra su propio total. El ajuste sigue el camino de cualquier pendiente
(§ 5): si el usuario no responde, vence, y ese resumen queda sin conciliar. Las ocurrencias
variables no vencen, porque son pendientes de una regla: se recuerdan cada 3 días hasta que el
usuario da su monto.

**Revisar los consumos del resumen.** En el mismo mensaje de la conciliación, el asistente
recomienda revisar que no haya ningún consumo que el usuario no reconozca, y más si la
diferencia es mayor de lo esperable. Un consumo no reconocido no va al ajuste: se registra
aparte, como cualquier gasto, para que quede visible mientras el usuario lo desconoce ante el
banco. Si el banco lo revierte, la devolución aparece en la conciliación de un resumen siguiente.

**Una compra cargada después del cierre.** Si el usuario registra una compra con tarjeta cuya
fecha cae en un resumen ya cerrado:

- **Si ese resumen todavía no se concilió,** la compra entra en él, y la conciliación la tiene en
  cuenta.
- **Si ya se concilió,** el asistente pregunta si la compra estaba incluida en el ajuste de ese
  resumen, mostrando su monto. Si estaba, registra la compra en ese resumen y recalcula el ajuste
  restándole la compra, en la misma confirmación. Si el ajuste queda en cero se borra, y si cambia
  de signo pasa a la otra categoría. Si no estaba, la compra entra en el resumen siguiente.

**Pagar con una billetera usando una tarjeta vinculada.** Con el QR de una billetera se puede
pagar con su saldo o con una tarjeta vinculada a ella, y la cuenta afectada es distinta en cada
caso. Si el usuario tiene al menos una tarjeta dada de alta, la primera vez que registra un pago
con una billetera el asistente pregunta si a veces paga con tarjetas vinculadas a ella, y guarda
la respuesta en la cuenta de la billetera. Si dice que no, no vuelve a preguntar. Si dice que sí,
en cada pago con esa billetera pregunta "¿con saldo o con qué tarjeta?", ofreciendo sus
tarjetas. Pagado con tarjeta, es una compra con tarjeta sobre esa cuenta. La respuesta se puede
cambiar después.

**Saldo, deuda y comprometido.** Como en cualquier cuenta (§ 2), el saldo de la tarjeta cuenta
solo lo que ya ocurrió: los gastos ya vencidos menos los pagos recibidos. Lo facturado en un
resumen que todavía no venció no es saldo, es deuda: se muestra aparte como lo que hay que pagar
en el próximo vencimiento, que es el total del resumen del banco. Un pago cancela primero lo
vencido y después esa deuda, así que pagar antes del vencimiento la reduce en el momento. Lo
comprometido a futuro, las ocurrencias de sus reglas todavía no generadas, se muestra aparte
como el de cualquier regla con fin (§ 8).

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
  WhatsApp (§ 15). Un movimiento ya confirmado que se corrige queda marcado con cuándo y quién lo
  corrigió por última vez; el valor anterior no se conserva
  ([ADR 0014](adr/0014-marca-de-edicion-en-movimientos.md)).
- **Supresión:** el borrado de cuenta descrito arriba.

**Datos que salen hacia el proveedor de LLM.** Nunca se envían identificadores (teléfono, nombre,
email ni ids internos), solo lo necesario para la tarea. El detalle está en el
[ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md).

Ver también: [Términos y política de privacidad](terminos-y-privacidad.md) · [APP_USER, INBOUND_MESSAGE y OUTBOUND_MESSAGE en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales).

## 15. Corregir, borrar y restaurar un movimiento confirmado

Un movimiento ya confirmado —un gasto, un ingreso, una transferencia o una regla recurrente,
incluida una compra con tarjeta— se corrige, se borra o se restaura desde el dashboard o por
WhatsApp. Esta sección dice cómo se hace por WhatsApp. Qué se guarda de cada cambio está en el
[ADR 0014](adr/0014-marca-de-edicion-en-movimientos.md) y en el
[ADR 0015](adr/0015-borrado-logico-de-movimientos.md).

**Solo quien lo registró.** Un usuario corrige, borra o restaura solo los movimientos que
registró él, también los que imputó a un presupuesto familiar. Los demás miembros los ven
marcados como corregidos o borrados, con quién y cuándo. La única excepción a que cada uno
resuelva lo suyo sigue siendo la del dueño que saca a un miembro con pendientes abiertos (§ 10),
y vale solo para pendientes, no para movimientos confirmados.

**Cómo se señala el movimiento.** Hay dos formas, y ninguna adivina:

1. **Citando la confirmación.** El usuario responde citando el "Listo…" con que Platita confirmó
   el movimiento. La cita apunta exactamente a los movimientos de ese lote, sin importar cuánto
   tiempo pasó. Si el lote tenía varios, el cambio va por número: "el 2 fueron 3.800". Pasado el
   plazo de retención el texto de la confirmación se borra, pero su identificador queda, así que
   la cita sigue funcionando (§ 14). Si el movimiento se corrigió después de esa confirmación, el
   cambio se aplica sobre sus valores actuales, y la respuesta los muestra. Si se borró, el
   asistente lo dice y ofrece restaurarlo.
2. **Describiéndolo.** Sin cita, el asistente busca entre los movimientos del usuario por lo que
   describe: fecha, monto, descripción, categoría o cuenta. Si encuentra uno solo, pregunta si es
   ese. Si encuentra varios, los ofrece numerados, como mucho 5, y el usuario elige. Si hay más,
   pide un dato que achique la búsqueda ("¿de qué día?") o manda el enlace al dashboard con la
   búsqueda aplicada. El tope es configuración.

Una corrección sin cita nunca se aplica al último movimiento por ser el último. Aunque llegue un
minuto después del "Listo", pasa por la búsqueda, donde ese movimiento aparece primero para que el
usuario lo confirme.

**Qué pide confirmación.**

- **Corregir.** Con cita, el movimiento ya está identificado: el cambio se aplica y el asistente
  responde con el movimiento completo, igual que en una confirmación, donde el usuario puede
  volver a corregir. Con búsqueda, elegir el candidato confirma el cambio.
- **Un retiro del titular** se corrige o se borra entero: cambiar el monto o la fecha de una mitad
  cambia la otra, y borrar una borra las dos (§ 10).
- **Borrar y restaurar.** Siempre piden confirmación, con cita o sin ella: "¿Borro el café de
  $2.500 de ayer?". Restaurar busca entre los movimientos borrados del usuario. Una regla
  recurrente borrada no se restaura: se vuelve a crear.
- **Una fecha que cambia de período.** Si la fecha corregida cae en otro período, se vuelve a
  pedir la confirmación del período (§ 1), porque ningún movimiento se imputa a un período sin que
  el usuario lo confirme. Una fecha anterior al alta de la cuenta se rechaza, como en cualquier
  registro (§ 2).

**Cambiar la cuenta a una tarjeta.** Si un gasto se registró en una cuenta y en realidad se pagó
con una tarjeta, como un pago con la billetera que fue con la tarjeta vinculada, la corrección no
cambia la cuenta del gasto: lo borra y registra una compra con esa tarjeta, en el resumen que
incluye su fecha, en una sola confirmación. Una compra con tarjeta es una regla y no un gasto
común (§ 13).

**Cambiar el tipo.** Un gasto que en realidad fue una transferencia, o al revés, no se corrige
cambiándole el tipo, porque son tablas distintas: la corrección borra el movimiento y registra el
del otro tipo, en una sola confirmación, pidiendo lo que el tipo nuevo necesite.

**Qué no se corrige por WhatsApp.**

- **La fecha de una cuota de tarjeta.** Es la del vencimiento del resumen (§ 13). Su monto y su
  categoría sí se corrigen.
- **Muchos movimientos a la vez**, como "pasá todos los de delivery de septiembre a comida". El
  asistente manda el enlace al dashboard, porque la lista no se lee bien en un chat.

**La conversación de un cambio es un pendiente.** Mientras espera que el usuario elija un
candidato, confirme un borrado o confirme el período de una fecha nueva, el cambio vive como un
pendiente de tipo cambio, en un lote de uno (§ 5). Así respeta las mismas reglas: un solo lote en
conversación, la respuesta citando su pregunta y el vencimiento. Mientras tanto, el movimiento no
cambia. Corregir, borrar y restaurar consumen la cuota de registro (§ 12).

Ver también: [PENDING_TRANSACTION y PENDING_BATCH en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU3](05-historias-de-usuario.md).

## 16. Reintegros, devoluciones y plata que te deben

Hay dos situaciones en las que entra plata que no es un ingreso, y cada una tiene su mecanismo.

**Un reintegro resta del gasto que devuelve.** Un reintegro, la devolución de una compra o lo
que otros le pagan al usuario por un gasto que ya registró se registran como un ingreso vinculado
a ese gasto (`refund_of`), en la categoría base "Devoluciones y reintegros".

- **Qué cambia en los números.** El ingreso vinculado no suma como ingreso del período: resta
  del gastado de la categoría del gasto que devuelve. El saldo de la cuenta sube igual, porque la
  plata entró.
- **En qué período resta.** En el período en que llega el reintegro, no en el del gasto: es el
  mismo criterio de flujo de caja que las cuotas de tarjeta (§ 13). Un período ya terminado no
  cambia. Si en ese período la categoría tuvo menos gastos que el reintegro, su gastado puede
  quedar negativo, y se muestra así.
- **Cómo se vincula.** Cuando el usuario registra un ingreso que el asistente clasifica en
  "Devoluciones y reintegros", o que habla de una devolución, un reintegro o lo que le pagaron
  por un gasto, el asistente pregunta de qué gasto es. Lo busca igual que en § 15 y ofrece hasta
  5 candidatos numerados. El usuario elige, o dice que no es de ningún gasto, y entonces queda
  como un ingreso común. El vínculo nunca se adivina.
- **Topes.** Si los reintegros vinculados a un gasto suman más que su monto, el asistente lo avisa
  antes de confirmar.
- **Si se borra el gasto.** Sus reintegros se desvinculan y pasan a ser ingresos comunes. El
  asistente lo avisa al pedir la confirmación del borrado.

El ajuste de una conciliación de tarjeta en "Devoluciones y reintegros" (§ 13) es un solo número
por resumen y no se vincula a ninguna compra.

**La plata que te deben es una cuenta.** Un préstamo a otra persona, o la parte de un gasto
compartido que otro va a pagar, no es un gasto: es plata del usuario que tiene otro. Se registra
como una transferencia a una cuenta de tipo "Me deben", y cuando la devuelven, como una
transferencia desde esa cuenta. Ninguna de las dos pesa en el presupuesto.

- **Una cuenta por persona.** El asistente usa el nombre de la persona: "Me debe Juan". La crea la
  primera vez, con confirmación, como cualquier cuenta. Si el usuario no nombra a nadie, usa una
  cuenta genérica "Me deben". Tiene una moneda, como toda cuenta, y saldo inicial 0.
- **Su saldo es lo que te deben.** Lo calcula Platita con las transferencias, así que no entra en
  el contraste mensual de saldos (§ 2). Aunque por dentro es una cuenta, el dashboard no la
  muestra en la lista de cuentas ni la suma al total disponible: aparece en una sección propia,
  "Me deben", por persona, porque no es una cuenta que el usuario tenga en un banco.
- **Dividir en el momento.** Si al pagar el usuario ya sabe su parte, el asistente registra las
  dos cosas en una sola confirmación. Por ejemplo, con "pagué la cena, 64 mil de MP, mi parte 16,
  el resto Juan, Pedro y Ana", registra un gasto de $16.000 y tres transferencias de $16.000 a
  "Me debe Juan", "Me debe Pedro" y "Me debe Ana". Si no lo sabe al pagar, registra el gasto
  completo, y lo que le pagan después se vincula como reintegro.

Lo que el usuario le debe a otro, como cuando otra persona pagó la cena, no tiene cuenta propia
todavía: se registra como gasto cuando el usuario le paga.

Ver también: [TRANSACTION y ACCOUNT en 3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) · [HU4](05-historias-de-usuario.md).

## 17. Preguntas sobre los propios datos

El usuario le puede preguntar al asistente lo que quiera sobre su plata: "¿cuánto gasté en
delivery este mes?", "¿gasté más en comida que el mes pasado?", "¿cuánto tengo en MP?". El
modelo no consulta la base: pide datos a un conjunto de funciones de solo lectura escritas en
código, las combina y responde. El fundamento está en el
[ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md).

**Las funciones.** Cada una devuelve datos ya calculados, con las mismas reglas que el resto del
producto: sin movimientos borrados ni duplicados (§ 2 y § 7), con el gastado neto de reintegros
(§ 16) y convertido con la cotización guardada en cada movimiento (§ 6).

| Función | Qué devuelve |
|---|---|
| Gastado | El total gastado en un rango de fechas, opcionalmente por categoría, por cuenta o agrupado por categoría |
| Ingresos | El total de ingresos en un rango de fechas, opcionalmente por categoría |
| Movimientos | Los movimientos que cumplen unos filtros (fechas, categoría, cuenta, monto, descripción), como mucho 20 |
| Saldos | El saldo de una cuenta o de todas, agrupadas por moneda, y lo aportado neto de las cuentas de inversión (§ 2) |
| Presupuesto | Para un período, el ingreso estimado y real, y el tope, el gastado y el porcentaje de cada categoría. En un período de grupo, además, cuánto imputó cada miembro |
| Tarjeta | La deuda del próximo vencimiento de una tarjeta, su fecha y lo comprometido en cuotas |
| Me deben | El saldo de cada cuenta "Me deben" (§ 16) |

**Qué garantiza el código, no el modelo.**

- **El usuario no es un parámetro.** Cada función filtra por el usuario del mensaje. Los períodos
  familiares que devuelve son los que ese usuario puede leer (§ 10).
- **Nada escribe.** Registrar, corregir o borrar siguen por sus flujos, con confirmación.
- **Las cifras salen de las funciones.** El modelo tiene la instrucción de no dar ningún número
  que no le haya devuelto una función. Si la respuesta necesita una cuenta que ninguna función
  hace, la función la tiene que hacer: el modelo no suma ni resta.
- **Topes por pregunta.** Como mucho 5 llamadas a funciones y 20 movimientos por lista. Los dos
  son configuración.

**Lo que no se puede responder.** Si la pregunta no se puede armar con las funciones, o el
resultado no entra en un mensaje, el asistente lo dice con un texto fijo y manda el enlace al
dashboard. Nunca estima ni inventa un dato. Si la pregunta es un pedido de registrar, corregir o
borrar, sigue ese flujo.

**En el dashboard, el resumen del período.** El dashboard muestra, para un período, el ingreso
estimado y el real, el gastado de todas las categorías, con tope o sin él, el total gastado y lo
comprometido para los períodos siguientes. Sale de las mismas reglas que la función Presupuesto.

Ver también: [LLM_USAGE en 3.2](03-modelo-de-datos.md#llm_usage) · [la API](04-api.md) · [HU4](05-historias-de-usuario.md).

## 18. Alcance de los consejos

Los consejos son educación financiera aplicada a la situación real del usuario, no asesoramiento
de inversiones. En Argentina, recomendar a una persona en qué invertir según su situación está
reservado a agentes registrados en la CNV, así que Platita explica y el usuario decide.

**Qué hace un consejo.**

- **Explica** instrumentos, riesgos, costos y cómo funcionan: qué es un FCI, un plazo fijo, un
  CEDEAR, cómo conviene pagar la tarjeta.
- **Usa los datos del usuario** para lo que es suyo: su presupuesto, su deuda, cuánto ahorra por
  mes y de cuánto debería ser su fondo de emergencia. Los pide con las funciones de § 17, así que
  sale de su historial real y no de un número escrito en el perfil. Con ingresos irregulares, el
  fondo de emergencia y la capacidad de ahorro se calculan sobre varios meses, no sobre uno.
- **Ordena prioridades generales:** antes de invertir, salir de deudas caras y armar un fondo de
  emergencia. Es criterio general de educación financiera, no una elección hecha para el usuario.

**Los consejos son individuales.** Usan los datos del usuario que pregunta: su presupuesto
individual, sus cuentas y su perfil. No usan un presupuesto de grupo ni el perfil de otro
miembro. Una pareja no puede pedir un consejo conjunto; cada uno lo pide sobre lo suyo. Las
consultas sobre datos (§ 17) sí leen los períodos del grupo, porque solo muestran cifras que el
miembro ya puede ver.

**Qué no hace.**

- **No elige un instrumento ni reparte montos** por el usuario: nada de "te conviene 70% CEDEARs".
- **No recomienda una entidad ni un producto con nombre.** Puede citar una tasa promedio del
  mercado, no "invertí en el plazo fijo del banco X".
- **No usa un perfil de riesgo,** porque no lo pregunta (§ 11).

Toda respuesta que habla de inversiones termina con una aclaración: es educación financiera, no
una recomendación personalizada. Es lo mismo que dicen los
[términos](terminos-y-privacidad.md).

**Los datos de mercado tienen fecha.** Las tasas y la inflación no se escriben en la base de
conocimiento, porque cambian cada semana o cada mes. Salen de fuentes que se actualizan solas,
con el mismo adaptador que las cotizaciones
([ADR 0011](adr/0011-cotizaciones-con-adaptador-generico-configurable.md)): en el MVP, la tasa
promedio de plazo fijo que publica el BCRA y la inflación mensual del INDEC. Cada respuesta que
usa uno de esos datos dice de qué fecha es. Si el dato guardado es demasiado viejo, lo dice en
vez de usarlo.

Ver también: [1.2, consejos con RAG](01-producto.md#12-características-y-funcionalidades-principales) · [INDICATOR_VALUE en 3.2](03-modelo-de-datos.md#indicator_value) · [HU5](05-historias-de-usuario.md).
