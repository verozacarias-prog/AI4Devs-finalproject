# Especificación — FEAT-006 · Registro de una transferencia entre cuentas propias

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Estado:** aprobada
- **Fecha:** 2026-11-04

## Alcance

Una transferencia escrita en el chat, como "pasé 20000 de Galicia pesos a Mercado Pago" o
"retiré 20 lucas del cajero de la Galicia pesos", queda registrada en `TRANSFER` y su efecto se
ve en el saldo de las dos cuentas, en la pantalla de cuentas de [FEAT-001](../FEAT-001/spec.md).
Reemplaza el texto fijo con que el asistente respondía una transferencia desde
[FEAT-003](../FEAT-003/spec.md) (C1-09).

Entra en la entrega final por decisión de Vero del 4 de noviembre de 2026
([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-final)), con este alcance:

- **Entra:** la transferencia entre dos cuentas del usuario en la misma moneda, por el chat.
- **No entra, y responde un texto fijo:** la transferencia entre cuentas de distinta moneda,
  que necesita la cotización de [§ 6](../../reglas-de-dominio.md#6-multimoneda-y-cotización).
- **No entra:** la comisión como gasto aparte, porque con un solo monto no hay comisión
  ([§ 13](../../reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias)); la carga desde
  el dashboard con `POST /transfers`; las cuentas "Me deben" (§ 16); y corregir el tipo de un
  pendiente con "no, era un gasto", que llega con
  [corregir un movimiento](../../reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado).

Con esta funcionalidad, una cuenta también se reconoce por su tipo sin una lista de palabras en
el código: el modelo devuelve el tipo de cuenta que el mensaje dice y las palabras que lo dicen,
y el código comprueba que esas palabras estén escritas
([reglas de dominio § 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma),
[ADR 0028](../../adr/0028-el-modelo-interpreta-el-codigo-controla-las-invariantes.md)). Vale
igual para un gasto, un ingreso y los dos lados de una transferencia, así que cambia también
CA-9 de [FEAT-003](../FEAT-003/spec.md).

Partida en los tres cortes de las
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales):

1. **Camino feliz.** Una transferencia con las dos cuentas y el monto a la vista queda
   registrada en un solo mensaje, y la cuenta se reconoce también por su tipo.
2. **Errores y lo que exige confirmación.** Preguntar la cuenta que falta, las dos cuentas que
   resultan la misma, el texto fijo de las monedas distintas y la fecha anterior al alta.
3. **Observabilidad.** Lo que registran los registros y la fila de `LLM_CALL` de una
   transferencia, sin montos ni nombres.

No hay pantalla nueva.

## Reglas de dominio que aplican

- [§ 1 — Registro de un movimiento](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma),
  en qué cuenta nombra un mensaje y en la confirmación, que dice el tipo y su efecto.
- [§ 2 — Cuentas y saldo calculado](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado),
  en lo que una transferencia suma y resta, y en que nada se registra antes del alta.
- [§ 5 — PENDING_TRANSACTION](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración),
  en el pendiente con `intent = 'transfer'` y el lote de uno.
- [§ 12 — Límites de uso del asistente](../../reglas-de-dominio.md#12-límites-de-uso-del-asistente),
  en la cuota de registro.
- [§ 13 — Tarjetas de crédito y transferencias](../../reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias)

## Criterios de aceptación

### Interpretar una transferencia

- **CA-1.** Si el mensaje es una transferencia, el modelo devuelve el monto y, por cada lado, el
  de origen y el de destino, las palabras con que el mensaje nombra la cuenta y, si el mensaje
  dice de qué tipo es la cuenta, el tipo y las palabras que lo dicen.
- **CA-2.** Cada lado se resuelve con la regla de CA-9 de [FEAT-003](../FEAT-003/spec.md): la
  cuenta la decide el código, y una palabra que el mensaje no escribe nunca se usa.

### Registrar una transferencia

- **CA-3.** Una transferencia que dice el monto y nombra dos cuentas distintas del usuario, una
  sola por lado y las dos en la misma moneda, queda registrada sin preguntar nada.
- **CA-4.** La transferencia va en la moneda de sus cuentas, con el mismo monto en cada lado y
  sin cotización.
- **CA-5.** La fecha se resuelve igual que la de un gasto, con CA-6 de
  [FEAT-003](../FEAT-003/spec.md).
- **CA-6.** Una transferencia no se imputa a ningún período y no cambia el gastado ni el
  ingreso de ningún presupuesto.
- **CA-7.** La transferencia queda con `source = 'manual'`.
- **CA-8.** La confirmación dice que es una transferencia, el monto, la cuenta de origen y la de
  destino, que no cuenta como gasto, y lista la fecha y la moneda.
- **CA-9.** Una transferencia completa también pasa por un lote de uno: su pendiente, con
  `intent = 'transfer'`, queda promovido, con `resulting_transfer_id` igual a la transferencia,
  y el lote cerrado, con la confirmación como `confirmation_message_id`.
- **CA-10.** Registrar una transferencia es una sola operación de base de datos, como la de
  CA-14 de [FEAT-003](../FEAT-003/spec.md): si algo falla, no queda ni la transferencia ni su
  pendiente.
- **CA-11.** El saldo de las dos cuentas, en la pantalla de cuentas, ya incluye la
  transferencia: baja el de origen y sube el de destino.

### Preguntar lo que falta — corte 2

- **CA-12.** Una transferencia sin monto, o con un lado que no nombra exactamente una cuenta,
  queda pendiente y se pregunta lo que falta en un solo mensaje, ofreciendo las cuentas del
  usuario: las que nombra la mención de ese lado, o todas, sin la cuenta del otro lado. Igual
  pregunta aunque quede una sola. Decidido por Vero el 5/11/2026.
- **CA-13.** Si los dos lados nombran la misma cuenta, no se registra nada y se preguntan las
  dos, origen y destino: el asistente no sabe cuál de las dos menciones está mal. Decidido por
  Vero el 4/11/2026.
- **CA-14.** Una transferencia entre cuentas de distinta moneda no se registra y recibe un
  texto fijo, sin otra llamada al modelo. Decidido por Vero el 4/11/2026. Lo mismo vale si el
  mensaje dice una moneda que no es la de una de sus cuentas, como "pasé 100 dólares de Galicia
  pesos a Mercado Pago": anotarla en la moneda de las cuentas guardaría otro monto que el
  dicho, y convertirla necesita la cotización. Decidido por Vero el 5/11/2026.
- **CA-15.** Una transferencia con fecha anterior al alta de cualquiera de sus dos cuentas no se
  registra, y la respuesta lo explica como en CA-10 de [FEAT-003](../FEAT-003/spec.md).

### Observabilidad — corte 3

- **CA-16.** Los registros de una transferencia no tienen el monto, el texto del mensaje ni el
  nombre de una cuenta.
- **CA-17.** Un pendiente de transferencia cuenta las correcciones de la respuesta como uno de
  gasto ([reglas de dominio § 5](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración)):
  cambiar el monto suma uno, cambiar la fecha suma uno, y cambiar una cuenta, o las dos, suma
  uno. Completar un lado que faltaba, o elegir entre las cuentas ofrecidas, no suma. Decidido
  por Vero el 6/11/2026; resuelve la issue #146.
- **CA-18.** La fila de `LLM_CALL` de una clasificación que resulta una transferencia dice qué
  campos de la transferencia vinieron vacíos, como CA-34 de [FEAT-003](../FEAT-003/spec.md): los
  de un gasto menos la categoría, que una transferencia no lleva, y más la cuenta de destino,
  `to_account`. Decidido por Vero el 6/11/2026. Necesita una migración nueva, porque el `CHECK`
  de `empty_fields` no admite `to_account`.

## Casos de prueba

Los tipos de caso, qué se reemplaza en cada uno y los datos de partida son los de
[FEAT-003](../FEAT-003/spec.md#casos-de-prueba). De esos datos importa además el tipo de cada
cuenta: Galicia pesos y Galicia USD son de banco, Mercado Pago es una billetera y Efectivo es de
efectivo.

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacarias 5/11/2026
- **Total:** 8 casos, 5 unitarios y 3 de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Una transferencia que nombra las dos cuentas queda registrada | Integración | CA-3, CA-4, CA-7, CA-9 y CA-10 |
| C1-02 | La confirmación dice que es una transferencia y que no cuenta como gasto | Unitario | CA-8 |
| C1-03 | El saldo de las dos cuentas ya incluye la transferencia | Integración | CA-11 |
| C1-04 | Una transferencia no cambia el gastado del período | Integración | CA-6 |
| C1-05 | El tipo de cuenta que dice el mensaje elige el destino | Unitario | CA-1 y CA-2 |
| C1-06 | Un tipo dicho con palabras que el mensaje no escribe no se usa | Unitario | CA-2 |
| C1-07 | Una fecha que el mensaje indica se respeta | Unitario | CA-5 |
| C1-08 | El adaptador devuelve los dos lados de la transferencia | Unitario | CA-1 |

#### C1-01 · Una transferencia que nombra las dos cuentas queda registrada

- **Sale de:** CA-3, CA-4, CA-7, CA-9 y CA-10 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "pasé 20000 de Galicia pesos a Mercado Pago", pendiente, con
  `sent_at` 2026-10-17T17:59:55Z, y el modelo responde que es un registro de tipo transferencia,
  con monto 20000, cuenta de origen "Galicia pesos" y cuenta de destino "Mercado Pago", sin tipo
  de cuenta, sin moneda y sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSFER` tiene una sola fila, de Lucía, con origen Galicia pesos,
  `from_amount = 20000.00`, `from_currency = 'ARS'`, destino Mercado Pago,
  `to_amount = 20000.00`, `to_currency = 'ARS'`, `exchange_rate` nulo,
  `transfer_date = 2026-10-17` y `source = 'manual'`; `TRANSACTION` sigue vacía; `PENDING_BATCH`
  tiene un solo lote de Lucía, manual, `closed`, con `awaiting_reply` falso;
  `PENDING_TRANSACTION` tiene un solo pendiente en ese lote, en la posición 1, `promoted`, con
  `intent = 'transfer'`, `missing_fields` vacío, `resulting_transfer_id` igual a la
  transferencia y `resulting_transaction_id` nulo; el mensaje queda `processed`; y la
  confirmación es la única respuesta a ese mensaje, de tipo `registration`, y el lote la guarda
  como `confirmation_message_id`.
- **Test:** `tests/integration/test_registration.py::test_a_transfer_that_names_both_accounts_is_registered`

#### C1-02 · La confirmación dice que es una transferencia y que no cuenta como gasto

- **Sale de:** CA-8 · **Tipo:** unitario
- **Dado** la transferencia de C1-01 ya resuelta: $20.000, de Galicia pesos a Mercado Pago,
  17/10/2026, ARS,
- **cuando** se arma la confirmación,
- **entonces** el texto es, línea por línea:

  > ¡Listo! Anoté una transferencia de $20.000 de Galicia pesos a Mercado Pago.
  > No cuenta como gasto.
  > Fecha: 17/10/2026
  > Moneda: ARS

- **Test:** `tests/unit/test_registration_confirmation.py::test_the_confirmation_says_it_is_a_transfer_and_does_not_count_as_an_expense`

#### C1-03 · El saldo de las dos cuentas ya incluye la transferencia

- **Sale de:** CA-11 · **Tipo:** integración
- **Dado** la transferencia de C1-01 ya procesada, y ningún otro movimiento de Lucía,
- **cuando** Lucía pide `GET /accounts`,
- **entonces** Galicia pesos tiene saldo `330000.00`, que es 350.000 − 20.000, Mercado Pago
  `100000.00`, que es 80.000 + 20.000, y Efectivo y Galicia USD conservan su saldo inicial.
- **Test:** `tests/integration/test_registration.py::test_the_balance_of_both_accounts_already_includes_the_transfer`

#### C1-04 · Una transferencia no cambia el gastado del período

- **Sale de:** CA-6 · **Tipo:** integración
- **Dado** la transferencia de C1-01 ya procesada, y ningún otro movimiento de Lucía,
- **cuando** Lucía pide `GET /budget-periods/{period_id}/summary` de su período de octubre,
- **entonces** el total gastado es `0.00` y el ingreso real es `0.00`.
- **Test:** `tests/integration/test_registration.py::test_a_transfer_does_not_change_what_the_period_spent`

#### C1-05 · El tipo de cuenta que dice el mensaje elige el destino

- **Sale de:** CA-1 y CA-2 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "retiré 20 lucas del cajero de la Galicia pesos", y el modelo
  responde una transferencia de 20000, con cuenta de origen "Galicia pesos", y de destino sin
  palabras de nombre, con el tipo efectivo dicho con "del cajero",
- **cuando** se procesa,
- **entonces** la transferencia queda de Galicia pesos a Efectivo, la única cuenta de tipo
  efectivo, por $20.000.
- **Test:** `tests/unit/test_answer_message.py::test_the_type_of_account_the_message_says_chooses_the_destination`

#### C1-06 · Un tipo dicho con palabras que el mensaje no escribe no se usa

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "saqué 20 lucas de la Galicia pesos", y el modelo responde una
  transferencia de 20000, con cuenta de origen "Galicia pesos", y de destino sin palabras de
  nombre, con el tipo efectivo dicho con "efectivo",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia: "efectivo" no está escrito en el mensaje.
- **Test:** `tests/unit/test_answer_message.py::test_a_type_said_with_words_the_message_does_not_write_is_not_used`

#### C1-07 · Una fecha que el mensaje indica se respeta

- **Sale de:** CA-5 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "ayer pasé 20000 de Galicia pesos a Mercado Pago", y el modelo
  responde la transferencia de C1-01 con fecha 2026-10-16,
- **cuando** se procesa,
- **entonces** la transferencia queda con `transfer_date = 2026-10-16`, y la confirmación dice
  "Fecha: 16/10/2026".
- **Test:** `tests/unit/test_answer_message.py::test_a_date_the_message_gives_for_a_transfer_is_kept`

#### C1-08 · El adaptador devuelve los dos lados de la transferencia

- **Sale de:** CA-1 · **Tipo:** unitario
- **Dado** el transporte HTTP del SDK, que responde la salida estructurada de una transferencia
  de "20000", con cuenta de origen "Galicia pesos", cuenta de destino nula, tipo de destino
  `cash` y sus palabras "del cajero",
- **cuando** el adaptador clasifica el mensaje,
- **entonces** la clasificación tiene `registration_type` transferencia, monto
  `Decimal("20000")`, cuenta de origen "Galicia pesos", sin tipo de origen, cuenta de destino
  nula, tipo de destino efectivo y palabras de destino "del cajero"; y el esquema que se le pidió
  al modelo solo acepta como tipo de cuenta los del catálogo de `ACCOUNT.type` o nulo.
- **Test:** `tests/unit/test_openai_llm.py::test_the_adapter_returns_both_sides_of_a_transfer`

### Corte 2 — errores y lo que exige confirmación

- **Aprobado por:** Veronica Zacarias 05/11/2026
- **C2-14, sumado al ver que la moneda dicha no frenaba una transferencia:** Veronica Zacarias 05/11/2026
- **El orden de las cuentas ofrecidas, cambiado al de la pregunta de un gasto:** Veronica Zacarias 05/11/2026
- **C2-15, sumado con la revisión de `pr-reviewer` del corte 2:** Veronica Zacarias 05/11/2026
- **Total:** 15 casos, 12 unitarios y 3 de integración.

Las cuentas se ofrecen en el mismo orden que en la pregunta de un gasto: primero las de la moneda
primaria del usuario y, en cada moneda, banco, billetera y efectivo, antes que el resto, y por
nombre. Para Lucía es Galicia pesos, Mercado Pago, Efectivo y Galicia USD. Cuando falta un lado, la pregunta ofrece las cuentas que nombra su
mención, o todas si no hay mención, menos la del otro lado, que ya se sabe. Igual pregunta,
aunque quede una sola: ofrecer no es elegir. Decidido por Vero el 5/11/2026. Lo que falta de una
transferencia se nombra por su campo en `TRANSFER`: `amount`, `from_account_id` y
`to_account_id`, y se pregunta en ese orden. Una transferencia que queda pendiente gasta la cuota
de registro, como un gasto pendiente, y también una rechazada por la fecha anterior al alta, como
un gasto; una que recibe el texto fijo de CA-14 no la gasta.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C2-01 | Una transferencia sin destino queda pendiente y pregunta a qué cuenta fue | Integración | CA-12 |
| C2-02 | Sin monto y sin origen, pregunta las dos cosas en un solo mensaje | Unitario | CA-12 |
| C2-03 | Una mención que coincide con dos no ofrece la cuenta del otro lado | Unitario | CA-12 |
| C2-04 | La respuesta completa el pendiente y registra la transferencia | Integración | CA-9 y CA-12 |
| C2-05 | Una respuesta a medias pregunta solo lo que sigue faltando | Unitario | CA-12 |
| C2-06 | Al modelo le llega el pendiente de la transferencia sin ningún identificador | Unitario | CA-12 |
| C2-07 | Las dos cuentas iguales no registran nada y preguntan las dos | Unitario | CA-13 |
| C2-08 | Una transferencia entre monedas distintas recibe el texto fijo y no queda pendiente | Integración | CA-14 |
| C2-09 | Elegir en la respuesta una cuenta en otra moneda cierra el pendiente con el texto fijo | Unitario | CA-14 |
| C2-10 | Con fecha anterior al alta de las dos cuentas, la respuesta nombra la de origen | Unitario | CA-15 |
| C2-11 | Con fecha anterior al alta solo del destino, la respuesta nombra el destino | Unitario | CA-15 |
| C2-12 | Con una transferencia pendiente, otro movimiento no se anota y la respuesta la nombra | Unitario | CA-12 |
| C2-13 | Un monto que no entra se vuelve a preguntar, diciendo por qué | Unitario | CA-12 |
| C2-14 | Una moneda dicha que no es la de las cuentas recibe el texto fijo | Unitario | CA-14 |
| C2-15 | Sin cuentas, el monto de la transferencia pendiente se nombra en la moneda dicha | Unitario | CA-12 |

#### C2-01 · Una transferencia sin destino queda pendiente y pregunta a qué cuenta fue

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "pasé 20000 de Galicia pesos", pendiente, con `sent_at`
  2026-10-17T17:59:55Z, y el modelo responde que es un registro de tipo transferencia, con monto
  20000, cuenta de origen "Galicia pesos" y sin cuenta ni tipo de destino,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSFER` sigue vacía; `PENDING_BATCH` tiene un solo lote de Lucía, manual,
  `open`, con `awaiting_reply` verdadero y la respuesta como `question_message_id`;
  `PENDING_TRANSACTION` tiene un solo pendiente en ese lote, `open`, con
  `intent = 'transfer'` y `missing_fields = ['to_account_id']`; el mensaje queda `processed`;
  el contador `registration` de Lucía del 17/10/2026 vale 1; y la única respuesta, de tipo
  `registration`, es "¿A qué cuenta fue? Mercado Pago, Efectivo o Galicia USD.".
- **Test:** `tests/integration/test_pending_transfer.py::test_a_transfer_without_a_destination_stays_pending_and_asks_where_it_went`

#### C2-02 · Sin monto y sin origen, pregunta las dos cosas en un solo mensaje

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé plata a Mercado Pago", y el modelo responde una
  transferencia sin monto, sin cuenta de origen y con cuenta de destino "Mercado Pago",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia, el pendiente queda con
  `missing_fields = ['amount', 'from_account_id']`, y la respuesta es, línea por línea:

  > ¿Cuánto fue?
  > ¿De qué cuenta salió? Galicia pesos, Efectivo o Galicia USD.

- **Test:** `tests/unit/test_pending_transfer.py::test_without_an_amount_and_an_origin_it_asks_both_in_one_message`

#### C2-03 · Una mención que coincide con dos no ofrece la cuenta del otro lado

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 20000 de Galicia pesos a la galicia", y el modelo responde
  una transferencia de 20000, con cuenta de origen "Galicia pesos" y de destino "galicia",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia: "galicia" nombra a Galicia pesos y a Galicia
  USD; el pendiente queda con `missing_fields = ['to_account_id']`, y la respuesta es "¿A qué
  cuenta fue? Galicia USD.", sin Galicia pesos, que es el origen.
- **Test:** `tests/unit/test_pending_transfer.py::test_a_mention_that_matches_two_does_not_offer_the_account_of_the_other_side`

#### C2-04 · La respuesta completa el pendiente y registra la transferencia

- **Sale de:** CA-9 y CA-12 · **Tipo:** integración
- **Dado** el pendiente de C2-01, y otro mensaje web de Lucía, posterior, "a Mercado Pago", y
  el modelo responde que continúa el pendiente, con cuenta de destino "Mercado Pago",
- **cuando** el worker hace una ronda,
- **entonces** `TRANSFER` tiene una sola fila, de Galicia pesos a Mercado Pago, con
  `from_amount = 20000.00`, `to_amount = 20000.00`, en ARS y con `transfer_date = 2026-10-17`;
  el pendiente queda `promoted`, con `missing_fields` vacío y `resulting_transfer_id` igual a la
  transferencia; el lote queda `closed`, con `awaiting_reply` falso y la confirmación como
  `confirmation_message_id`; y la confirmación es la de C1-02.
- **Test:** `tests/integration/test_pending_transfer.py::test_the_reply_completes_the_pending_and_registers_the_transfer`

#### C2-05 · Una respuesta a medias pregunta solo lo que sigue faltando

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el pendiente de C2-02, y una respuesta de Lucía, "fueron 20 lucas", con la que el
  modelo continúa el pendiente con monto 20000,
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia, el pendiente queda con
  `missing_fields = ['from_account_id']` y monto 20000, y la respuesta es "¿De qué cuenta
  salió? Galicia pesos, Efectivo o Galicia USD.".
- **Test:** `tests/unit/test_pending_transfer.py::test_a_reply_that_completes_half_asks_only_what_is_still_missing`

#### C2-06 · Al modelo le llega el pendiente de la transferencia sin ningún identificador

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el pendiente de C2-01, y una respuesta de Lucía, "a Mercado Pago",
- **cuando** se clasifica,
- **entonces** el pendiente abierto que recibe el modelo dice, en lo interpretado, el tipo
  `transfer`, el monto 20000 y la cuenta de origen "Galicia pesos"; en lo que falta,
  `to_account_id`; y como pregunta, la de C2-01; y no tiene ningún identificador.
- **Test:** `tests/unit/test_pending_transfer.py::test_the_model_gets_the_pending_transfer_without_any_identifier`

#### C2-07 · Las dos cuentas iguales no registran nada y preguntan las dos

- **Sale de:** CA-13 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 20000 de Galicia pesos a Galicia pesos", y el modelo
  responde una transferencia de 20000, con cuenta de origen y de destino "Galicia pesos",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia; el pendiente queda con
  `missing_fields = ['from_account_id', 'to_account_id']`, sin ninguna de las dos cuentas en lo
  interpretado; y la respuesta es, línea por línea:

  > La cuenta de origen y la de destino no pueden ser la misma.
  > ¿De qué cuenta salió? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.
  > ¿A qué cuenta fue? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.

- **Test:** `tests/unit/test_pending_transfer.py::test_the_same_account_on_both_sides_registers_nothing_and_asks_both`

#### C2-08 · Una transferencia entre monedas distintas recibe el texto fijo y no queda pendiente

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "pasé 100 de Galicia USD a Mercado Pago", pendiente, y el
  modelo responde una transferencia de 100, con cuenta de origen "Galicia USD" y de destino
  "Mercado Pago",
- **cuando** el worker hace una ronda,
- **entonces** `TRANSFER`, `PENDING_BATCH` y `PENDING_TRANSACTION` siguen vacías; `LLM_CALL`
  tiene una sola fila de ese mensaje; el contador `registration` de Lucía no suma; el mensaje
  queda `processed`; y la única respuesta, con `response_kind = 'fixed_text'`, es "Todavía no
  sé anotar una transferencia entre cuentas de distinta moneda. Por ahora, solo entre cuentas
  de la misma moneda.".
- **Test:** `tests/integration/test_pending_transfer.py::test_a_transfer_between_different_currencies_gets_the_fixed_text_and_stays_no_pending`

#### C2-09 · Elegir en la respuesta una cuenta en otra moneda cierra el pendiente con el texto fijo

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** el pendiente de C2-03, y una respuesta de Lucía, "a Galicia USD", con la que el
  modelo continúa el pendiente con cuenta de destino "Galicia USD",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia, el pendiente queda `rejected`, el lote
  `closed` con `awaiting_reply` falso, y la respuesta es el texto fijo de C2-08.
- **Test:** `tests/unit/test_pending_transfer.py::test_choosing_an_account_in_another_currency_in_the_reply_closes_the_pending_with_the_fixed_text`

#### C2-10 · Con fecha anterior al alta de las dos cuentas, la respuesta nombra la de origen

- **Sale de:** CA-15 · **Tipo:** unitario
- **Dado** Lucía con Galicia pesos y Mercado Pago dadas de alta el 13/10/2026, un mensaje suyo,
  "el lunes pasé 20000 de Galicia pesos a Mercado Pago", y el modelo responde la transferencia
  de C1-01 con fecha 2026-10-12,
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia ni queda ningún pendiente abierto, y la
  respuesta es "Galicia pesos la tenés cargada desde el 13/10/2026, así que lo que
  transferiste antes ya está en el saldo con el que la diste de alta. Lo dejo sin anotar para
  no contarlo dos veces.", con `response_kind = 'fixed_text'`.
- **Test:** `tests/unit/test_pending_transfer.py::test_a_date_before_both_accounts_were_opened_names_the_origin`

#### C2-11 · Con fecha anterior al alta solo del destino, la respuesta nombra el destino

- **Sale de:** CA-15 · **Tipo:** unitario
- **Dado** Lucía con Mercado Pago dada de alta el 13/10/2026 y Galicia pesos antes del
  12/10/2026, un mensaje suyo, "el lunes pasé 20000 de Galicia pesos a Mercado Pago", y el
  modelo responde la transferencia de C1-01 con fecha 2026-10-12,
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia ni queda ningún pendiente abierto, y la respuesta es
  "Mercado Pago la tenés cargada desde el 13/10/2026, así que lo que transferiste antes ya está
  en el saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo dos veces.".
- **Test:** `tests/unit/test_pending_transfer.py::test_a_date_before_only_the_destination_was_opened_names_the_destination`

#### C2-12 · Con una transferencia pendiente, otro movimiento no se anota y la respuesta la nombra

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el pendiente de C2-01, y otro mensaje de Lucía, "gasté 3500 en el súper con Mercado
  Pago", con el que el modelo responde que trae otro movimiento,
- **cuando** se procesa,
- **entonces** no se registra nada, el pendiente sigue `open` con lo que tenía, y la respuesta
  es, línea por línea:

  > No anoté tu último mensaje: primero terminemos con la transferencia de $20.000 de Galicia pesos, y después mandámelo de nuevo.
  > ¿A qué cuenta fue? Mercado Pago, Efectivo o Galicia USD.

- **Test:** `tests/unit/test_pending_transfer.py::test_with_a_pending_transfer_another_movement_is_not_registered_and_the_reply_names_it`

#### C2-13 · Un monto que no entra se vuelve a preguntar, diciendo por qué

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 1000000000000000000 de Galicia pesos a Mercado Pago", y
  el modelo responde una transferencia por ese monto, con cuenta de origen "Galicia pesos" y de
  destino "Mercado Pago",
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia, el pendiente queda con
  `missing_fields = ['amount']`, y la respuesta es, línea por línea:

  > Ese monto es más grande de lo que puedo registrar.
  > ¿Cuánto fue?

- **Test:** `tests/unit/test_pending_transfer.py::test_an_amount_that_does_not_fit_is_asked_again_saying_why`

#### C2-14 · Una moneda dicha que no es la de las cuentas recibe el texto fijo

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 100 dólares de Galicia pesos a Mercado Pago", y el modelo
  responde una transferencia de 100, con moneda USD dicha con "dólares", cuenta de origen
  "Galicia pesos" y de destino "Mercado Pago", las dos en ARS,
- **cuando** se procesa,
- **entonces** no se registra ninguna transferencia ni queda ningún pendiente, y la respuesta es
  "Todavía no sé anotar una transferencia en otra moneda que la de sus cuentas. Por ahora, solo
  en la moneda de las dos cuentas.", con `response_kind = 'fixed_text'`.
- **Test:** `tests/unit/test_pending_transfer.py::test_a_currency_said_that_is_not_the_one_of_the_accounts_gets_the_fixed_text`

#### C2-15 · Sin cuentas, el monto de la transferencia pendiente se nombra en la moneda dicha

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 100 dólares", con el que el modelo responde una
  transferencia de 100, con moneda USD dicha con "dólares" y sin ninguna de las dos cuentas, y
  después otro mensaje suyo, "gasté 3500 en el súper con Mercado Pago", con el que el modelo
  responde que trae otro movimiento,
- **cuando** se procesa el segundo,
- **entonces** no se registra nada, el pendiente sigue `open`, y la primera línea de la
  respuesta es "No anoté tu último mensaje: primero terminemos con la transferencia de US$100,
  y después mandámelo de nuevo.": el monto va en la moneda que Lucía dijo, no en la primaria.
- **Test:** `tests/unit/test_pending_transfer.py::test_without_accounts_the_amount_of_the_pending_transfer_is_named_in_the_currency_said`

### Corte 3 — observabilidad

- **Aprobado por:** Veronica Zacarias 6/11/2026
- **Total:** 5 casos, 2 unitarios y 3 de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C3-01 | Ninguna línea de los registros de una transferencia lleva el monto, el texto ni una cuenta | Integración | CA-16 |
| C3-02 | Una respuesta que cambia el monto de una transferencia pendiente suma una corrección | Integración | CA-17 |
| C3-03 | Cambiar las dos cuentas suma una sola corrección | Unitario | CA-17 |
| C3-04 | Elegir entre las cuentas ofrecidas no suma una corrección | Unitario | CA-17 |
| C3-05 | La fila de la clasificación de una transferencia dice qué campos vinieron vacíos | Integración | CA-18 |

#### C3-01 · Ninguna línea de los registros de una transferencia lleva el monto, el texto ni una cuenta

- **Sale de:** CA-16 · **Tipo:** integración
- **Dado** los mensajes web de Lucía "pasé 20000 de Galicia pesos" y, después, "a Mercado
  Pago", y el modelo responde las interpretaciones de C2-01 y de C2-04,
- **cuando** el worker hace una ronda con cada uno, el primero queda pendiente y el segundo
  registra la transferencia,
- **entonces** ninguna línea de los registros contiene "20000", "20.000", "pasé", "Galicia",
  "Mercado Pago", "Lucía" ni "000000000001".
- **Test:** `tests/integration/test_registration_logs.py::test_no_log_line_of_a_transfer_carries_the_amount_the_text_or_an_account`

#### C3-02 · Una respuesta que cambia el monto de una transferencia pendiente suma una corrección

- **Sale de:** CA-17 · **Tipo:** integración
- **Dado** el pendiente de C2-01, y otro mensaje web de Lucía, posterior, "no, fueron 30 lucas,
  a Mercado Pago", y el modelo responde que continúa el pendiente, con monto 30000 y cuenta de
  destino "Mercado Pago",
- **cuando** el worker hace una ronda,
- **entonces** `TRANSFER` tiene una sola fila, de Galicia pesos a Mercado Pago, con
  `from_amount = 30000.00`; y el pendiente queda `promoted` con `corrected_fields_count = 1`:
  el monto, que el modelo había interpretado, cambió, y el destino faltaba, así que completarlo
  no cuenta.
- **Test:** `tests/integration/test_pending_transfer.py::test_a_reply_that_changes_the_amount_of_a_pending_transfer_adds_a_correction`

#### C3-03 · Cambiar las dos cuentas suma una sola corrección

- **Sale de:** CA-17 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé plata de Galicia pesos a Mercado Pago", que queda
  pendiente porque el modelo responde una transferencia sin monto, con cuenta de origen
  "Galicia pesos" y de destino "Mercado Pago"; y la respuesta "fueron 20000, de Efectivo a
  Galicia pesos", que continúa el pendiente con monto 20000, origen "Efectivo" y destino
  "Galicia pesos",
- **cuando** se procesa la respuesta,
- **entonces** se registra la transferencia de Efectivo a Galicia pesos, y el pendiente queda
  `promoted` con `corrected_fields_count = 1`: cambiaron las dos cuentas, que cuentan como un
  solo campo, y el monto faltaba.
- **Test:** `tests/unit/test_pending_transfer.py::test_changing_both_accounts_adds_a_single_correction`

#### C3-04 · Elegir entre las cuentas ofrecidas no suma una corrección

- **Sale de:** CA-17 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pasé 20000 de galicia a Mercado Pago", que queda pendiente
  porque "galicia" nombra a Galicia pesos y a Galicia USD; y la respuesta "de Galicia pesos",
  que continúa el pendiente con cuenta de origen "Galicia pesos",
- **cuando** se procesa la respuesta,
- **entonces** se registra la transferencia de Galicia pesos a Mercado Pago, y el pendiente
  queda `promoted` con `corrected_fields_count = 0`: el origen faltaba, y elegirlo entre los
  ofrecidos lo completa.
- **Test:** `tests/unit/test_pending_transfer.py::test_choosing_among_the_offered_accounts_adds_no_correction`

#### C3-05 · La fila de la clasificación de una transferencia dice qué campos vinieron vacíos

- **Sale de:** CA-18 · **Tipo:** integración
- **Dado** el mensaje de C2-01, "pasé 20000 de Galicia pesos", y el modelo responde una
  transferencia de 20000 con cuenta de origen "Galicia pesos", sin cuenta de destino, sin
  moneda y sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** la fila de `LLM_CALL` tiene `empty_fields` con `to_account`, `currency` y
  `transaction_date`, sin `category` y sin ningún valor de la salida.
- **Test:** `tests/integration/test_llm_calls.py::test_the_row_of_a_transfer_says_which_of_its_fields_came_empty`

## Mensajes al usuario

| Situación | Texto |
|---|---|
| Transferencia registrada | La confirmación de C1-02 |
| Falta el monto (corte 2) | "¿Cuánto fue?", el mismo de un gasto |
| Falta la cuenta de origen (corte 2) | "¿De qué cuenta salió? {cuentas}." |
| Falta la cuenta de destino (corte 2) | "¿A qué cuenta fue? {cuentas}." |
| Las dos cuentas son la misma (corte 2) | "La cuenta de origen y la de destino no pueden ser la misma.", antes de las dos preguntas |
| Transferencia entre monedas distintas (corte 2) | "Todavía no sé anotar una transferencia entre cuentas de distinta moneda. Por ahora, solo entre cuentas de la misma moneda." |
| Transferencia en otra moneda que la de sus cuentas (corte 2) | "Todavía no sé anotar una transferencia en otra moneda que la de sus cuentas. Por ahora, solo en la moneda de las dos cuentas." |
| Fecha anterior al alta de una de sus cuentas (corte 2) | El texto de CA-10 de [FEAT-003](../FEAT-003/spec.md), con "transferiste", y la cuenta de origen si la fecha es anterior al alta de las dos |
| Otro movimiento con una transferencia pendiente (corte 2) | El texto de CA-36 de [FEAT-003](../FEAT-003/spec.md), que la nombra como "la transferencia de {monto} de {origen} a {destino}", con lo que se sabe |

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| Nunca una cuenta por defecto (§ 1) | C1-06, C2-01, C2-03 y C2-07 |
| Origen y destino son cuentas distintas (§ 13) | C2-03 y C2-07 |
| Nada antes del alta de la cuenta (§ 2) | C2-10 y C2-11 |
| Una transferencia no se imputa a ningún período (§ 13) | C1-01 y C1-04 |
| Montos en `Decimal`, con la moneda al lado | C1-01 y C1-08 |
| El saldo se calcula, no se guarda (§ 2) | C1-03 |
| Qué cuenta como corrección (§ 5) | C3-02, C3-03 y C3-04 |

## Sin cubrir

- Lo que el modelo decide, como que "del cajero" dice efectivo, no lo prueba ningún test: se
  prueba a mano con el modelo real
  ([ADR 0028](../../adr/0028-el-modelo-interpreta-el-codigo-controla-las-invariantes.md)).

## Fuera de alcance

Lo listado en [Alcance](#alcance) como "No entra".

## Preguntas abiertas

Ninguna.
