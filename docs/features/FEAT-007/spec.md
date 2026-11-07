# Especificación — FEAT-007 · Varios movimientos en un mensaje

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Estado:** aprobada
- **Fecha:** 2026-11-06

## Alcance

Un mensaje con varios movimientos, como "gasté 3500 en el súper con MP y 1200 de nafta en
efectivo", queda registrado entero: cada movimiento es un pendiente de un mismo lote, numerado, y
el asistente pregunta y confirma el lote en un solo mensaje. El usuario contesta lo que falte por
número ("el 2 con MP") o en general ("todos con MP"). Reemplaza el texto fijo con que el
asistente respondía un mensaje con varios movimientos desde [FEAT-003](../FEAT-003/spec.md)
(C2-35), y el aviso de CA-36 de FEAT-003, que no sumaba al lote un movimiento nuevo.

Entra en la entrega final ([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-final)), con
este alcance:

- **Entra:** gastos, ingresos y transferencias, mezclados en un mismo mensaje, hasta 10 por lote,
  por el chat web.
- **No entra:** responder citando la pregunta de un lote que no está en conversación, que llega
  con el botón de responder de [corregir, borrar y restaurar](../../reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado);
  los lotes de movimientos detectados en emails, que son de una segunda versión; y el
  recordatorio y el vencimiento de un lote por un proceso programado, como en FEAT-003.

Partida en los tres cortes de las
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales):

1. **Camino feliz.** Un mensaje con varios movimientos completos queda registrado de una vez, con
   una sola confirmación numerada.
2. **Lo que falta y lo que no se puede anotar.** La pregunta numerada, las respuestas por número
   o generales, descartar uno, el movimiento nuevo que se suma al lote, el tope de 10 y el
   movimiento que recibe un texto fijo.
3. **Observabilidad.** Lo que registran los registros y la fila de `LLM_CALL` de un mensaje con
   varios movimientos, y las correcciones por número.

No hay pantalla nueva.

## Reglas de dominio que aplican

- [§ 1 — Registro de un movimiento](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma),
  que vale para cada movimiento del mensaje como si llegara solo.
- [§ 5 — PENDING_TRANSACTION](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración),
  en el lote como unidad de conversación, las respuestas por número, la convergencia de mensajes
  seguidos y el tope de 10.
- [§ 12 — Límites de uso del asistente](../../reglas-de-dominio.md#12-límites-de-uso-del-asistente),
  en que la cuota de registro cuenta mensajes y no movimientos.
- [§ 13 — Tarjetas de crédito y transferencias](../../reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias),
  para una transferencia dentro del lote.

## Criterios de aceptación

### Interpretar un mensaje con varios movimientos

- **CA-1.** El modelo devuelve cada movimiento del mensaje, en el orden en que está escrito, con
  los mismos datos que devuelve de un movimiento solo ([FEAT-003](../FEAT-003/spec.md) y CA-1
  de [FEAT-006](../FEAT-006/spec.md)).
- **CA-2.** Cada movimiento se resuelve como si llegara solo: su cuenta con CA-9 de FEAT-003, su
  fecha, su moneda, su categoría y su período. Lo que el mensaje dice de un movimiento no se usa
  para otro.

### Registrar un lote completo — corte 1

- **CA-3.** Un mensaje cuyos movimientos están todos completos los registra a todos sin preguntar
  nada: cada gasto o ingreso en `TRANSACTION` y cada transferencia en `TRANSFER`.
- **CA-4.** Los movimientos del mensaje son pendientes de un mismo lote manual, numerados del 1
  en adelante en el orden del mensaje. Al registrarse, cada pendiente queda promovido y el lote
  se cierra.
- **CA-5.** Una sola confirmación lista los movimientos con su número, cada uno con lo que diría
  su confirmación si llegara solo: el tipo, el monto, la cuenta o las dos cuentas, la fecha, la
  moneda, la categoría y el presupuesto. El lote la guarda como `confirmation_message_id`.
- **CA-6.** Un mensaje con varios movimientos cuenta una sola vez en la cuota de registro y en el
  tope diario, igual que uno con un movimiento
  ([reglas de dominio § 12](../../reglas-de-dominio.md#12-límites-de-uso-del-asistente)).
- **CA-7.** Un mensaje con un solo movimiento recibe la misma confirmación y la misma pregunta
  que antes, sin número.

### Lo que falta y lo que no se puede anotar — corte 2

- **CA-8.** Si a algún movimiento del lote le falta un dato, no se registra ninguno hasta que el
  lote está completo. Una sola pregunta lista todos, numerados, con lo ya interpretado de cada
  uno y lo que le falta a los que están incompletos. Decidido por Vero el 6/11/2026: así el lote
  tiene una sola confirmación, y una corrección que la cita va por número
  ([§ 15](../../reglas-de-dominio.md#15-corregir-borrar-y-restaurar-un-movimiento-confirmado)).
- **CA-9.** La respuesta puede ir por número, como "el 2 con MP", o ser general, como "todos con
  MP". El modelo devuelve, por número, lo que la respuesta agrega o cambia de cada pendiente, y
  el código lo aplica con las mismas reglas que a un pendiente solo.
- **CA-10.** Cuando todos los pendientes del lote quedan completos, se registran juntos con la
  confirmación de CA-5. Mientras falte algo, la pregunta se repite con la lista actualizada.
- **CA-11.** Una respuesta puede descartar un pendiente por número, como "el 2 no lo anotes": ese
  queda rechazado y los demás siguen. Si se descartan todos, el lote se cierra sin registrar
  nada.
- **CA-12.** Un movimiento que todavía no se sabe anotar —una compra con tarjeta, una regla
  recurrente, un cambio, uno en otra moneda o con más de un período posible— no entra al lote: la
  respuesta lo nombra en una línea propia con su texto fijo, y los demás siguen. Decidido por
  Vero el 6/11/2026, para no perder los que sí se pueden anotar. Si ninguno entra, la respuesta
  son solo esos textos y no queda nada pendiente.
- **CA-13.** Con un lote esperando respuesta, un mensaje que trae otro movimiento lo suma al lote
  con el número siguiente, y el asistente manda la lista actualizada. Reemplaza CA-36 de
  FEAT-003.
- **CA-14.** Un lote tiene como mucho 10 pendientes. Si un mensaje trae más de los que entran,
  entran los primeros hasta llegar a 10, y la respuesta dice cuántos tomó y pide mandar el resto
  después.
- **CA-18.** Cada pendiente del lote vence a las 24 horas de creado
  ([§ 5](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración)),
  aunque se haya sumado después que los otros. Uno vencido sale del lote, queda `expired`, y la
  respuesta lo nombra en una línea propia; los demás siguen con su número, y el modelo recibe
  solo esos. Si vencieron todos, el lote se cierra y el mensaje se procesa como si no hubiera
  nada abierto, como en CA-38 de [FEAT-003](../FEAT-003/spec.md). Decidido por Vero el
  7/11/2026, con el `/spec-drift` del corte 2 (issue #151).

### Observabilidad — corte 3

- **CA-15.** Los registros de un mensaje con varios movimientos dicen cuántos trajo y cuántos
  entraron al lote, sin montos, sin el texto del mensaje y sin nombres de cuentas.
- **CA-16.** La fila de `LLM_CALL` de una clasificación con varios movimientos dice cuántos
  movimientos devolvió el modelo, y qué campos vinieron vacíos en alguno de ellos.
- **CA-17.** Cada pendiente del lote cuenta sus propias correcciones con la regla de § 5: "el 2
  fueron 3800" suma uno al pendiente 2 y no cambia los demás.

## Casos de prueba

Los tipos de caso, qué se reemplaza en cada uno y los datos de partida son los de
[FEAT-003](../FEAT-003/spec.md#casos-de-prueba), con los tipos de cuenta de
[FEAT-006](../FEAT-006/spec.md#casos-de-prueba).

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacarias 6/11/2026
- **Total:** 7 casos, 4 unitarios y 3 de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Dos gastos completos en un mensaje quedan registrados en un lote | Integración | CA-3 y CA-4 |
| C1-02 | La confirmación de un lote lista cada movimiento con su número | Unitario | CA-5 |
| C1-03 | Un gasto y una transferencia en un mensaje quedan registrados | Integración | CA-3 y CA-4 |
| C1-04 | El gastado del período suma los dos gastos | Integración | CA-3 |
| C1-05 | Cada movimiento conserva su propia fecha | Unitario | CA-2 |
| C1-06 | Un mensaje con varios movimientos cuenta una vez en la cuota | Unitario | CA-6 |
| C1-07 | El adaptador devuelve cada movimiento del mensaje | Unitario | CA-1 |

#### C1-01 · Dos gastos completos en un mensaje quedan registrados en un lote

- **Sale de:** CA-3 y CA-4 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper con MP y 1200 de nafta en efectivo",
  pendiente, con `sent_at` 2026-10-17T17:59:55Z, y el modelo responde que es un registro con dos
  movimientos: un gasto de 3500, cuenta "MP", categoría Supermercado, y un gasto de 1200, cuenta
  "efectivo", categoría Transporte, los dos sin moneda y sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` tiene dos filas de Lucía, `source = 'manual'`, con
  `transaction_date = 2026-10-17`, `currency = 'ARS'` y el período de octubre: un gasto de
  `3500.00` en Mercado Pago, Supermercado, y uno de `1200.00` en Efectivo, Transporte;
  `PENDING_BATCH` tiene un solo lote de Lucía, manual, `closed`, con `awaiting_reply` falso;
  `PENDING_TRANSACTION` tiene dos pendientes en ese lote, `promoted`, con `missing_fields` vacío:
  el de la posición 1 enlazado al gasto de 3500 y el de la posición 2 al de 1200; el mensaje queda
  `processed`; y Lucía recibe una sola respuesta, la confirmación del lote, de tipo
  `registration`, que el lote guarda como `confirmation_message_id`.
- **Test:** `tests/integration/test_several_movements.py::test_two_complete_expenses_in_one_message_are_registered_in_one_batch`

#### C1-02 · La confirmación de un lote lista cada movimiento con su número

- **Sale de:** CA-5 · **Tipo:** unitario
- **Dado** los dos gastos de C1-05 ya resueltos, el de 3500 del 16 de octubre y el de 1200 del 17,
  en el período individual de Lucía del 1 al 31 de octubre,
- **cuando** se arma la confirmación del lote,
- **entonces** el texto es, línea por línea:

  > ¡Listo! Anoté 2 movimientos:
  >
  > 1. Un gasto de $3.500 en Mercado Pago.
  > Fecha: 16/10/2026
  > Moneda: ARS
  > Categoría: Supermercado
  > Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026
  >
  > 2. Un gasto de $1.200 en Efectivo.
  > Fecha: 17/10/2026
  > Moneda: ARS
  > Categoría: Transporte
  > Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026

  Y una transferencia en un lote dice, en su número, "Una transferencia de $20.000 de Galicia
  pesos a Efectivo.", "No cuenta como gasto.", su fecha y su moneda.
- **Test:** `tests/unit/test_several_movements.py::test_the_confirmation_of_a_batch_lists_each_movement_with_its_number`

#### C1-03 · Un gasto y una transferencia en un mensaje quedan registrados

- **Sale de:** CA-3 y CA-4 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper con MP y pasé 20000 de Galicia pesos
  a efectivo", pendiente, y el modelo responde que es un registro con dos movimientos: un gasto de
  3500, cuenta "MP", categoría Supermercado, y una transferencia de 20000, cuenta de origen
  "Galicia pesos" y de destino "efectivo", sin moneda y sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` tiene un gasto de `3500.00` en Mercado Pago; `TRANSFER` tiene una
  transferencia de `20000.00` de Galicia pesos a Efectivo, en ARS; el lote de Lucía queda
  `closed` con dos pendientes `promoted`: el de la posición 1 con `intent = 'transaction'`,
  enlazado al gasto, y el de la posición 2 con `intent = 'transfer'`, enlazado a la
  transferencia; y hay una sola confirmación, que el lote guarda.
- **Test:** `tests/integration/test_several_movements.py::test_an_expense_and_a_transfer_in_one_message_are_registered`

#### C1-04 · El gastado del período suma los dos gastos

- **Sale de:** CA-3 · **Tipo:** integración
- **Dado** el mensaje de C1-01 ya procesado, y ningún otro movimiento de Lucía,
- **cuando** Lucía pide `GET /budget-periods/{period_id}/summary` de su período de octubre,
- **entonces** el total gastado es `4700.00`, que es 3.500 + 1.200.
- **Test:** `tests/integration/test_several_movements.py::test_what_the_period_spent_adds_both_expenses`

#### C1-05 · Cada movimiento conserva su propia fecha

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "ayer gasté 3500 en el súper con MP y hoy 1200 de nafta en
  efectivo", y el modelo responde los dos gastos de C1-01, el primero con fecha 2026-10-16 y el
  segundo sin fecha,
- **cuando** se procesa,
- **entonces** el gasto de 3500 queda con `transaction_date = 2026-10-16` y el de 1200 con
  `2026-10-17`, el día en que Lucía escribió.
- **Test:** `tests/unit/test_several_movements.py::test_each_movement_keeps_its_own_date`

#### C1-06 · Un mensaje con varios movimientos cuenta una vez en la cuota

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** Lucía con 3 mensajes de registro contados hoy, y el mensaje de C1-01,
- **cuando** se procesa,
- **entonces** la cuota de registro de Lucía queda en 4, no en 5, y el tope diario suma uno.
- **Test:** `tests/unit/test_several_movements.py::test_a_message_with_several_movements_counts_once_against_the_quota`

#### C1-07 · El adaptador devuelve cada movimiento del mensaje

- **Sale de:** CA-1 · **Tipo:** unitario
- **Dado** el transporte HTTP del SDK, que responde la salida estructurada de un registro con dos
  movimientos: un gasto de "3500" con cuenta "MP" y categoría Supermercado, y una transferencia de
  "20000" con cuenta de origen "Galicia pesos" y de destino "efectivo",
- **cuando** el adaptador clasifica el mensaje,
- **entonces** la clasificación tiene los dos movimientos en ese orden: el primero un gasto de
  `Decimal("3500")`, cuenta "MP", categoría Supermercado; el segundo una transferencia de
  `Decimal("20000")`, cuenta de origen "Galicia pesos" y de destino "efectivo"; y el esquema que
  se le pidió al modelo devuelve los movimientos como una lista.
- **Test:** `tests/unit/test_several_movements.py::test_the_adapter_returns_every_movement_of_the_message`

### Corte 2 — lo que falta y lo que no se puede anotar

- **Aprobado por:** Veronica Zacarias 06/11/2026
- **C2-17 a C2-19, sumados con el `/spec-drift` del corte 2:** Veronica Zacarias 06/11/2026
- **Total:** 19 casos, 16 unitarios y 3 de integración.

Donde el caso dice que el modelo contesta "el pendiente 2", el doble devuelve una respuesta por
número: el número del pendiente y lo que la respuesta le agrega o le cambia, con los mismos campos
de un movimiento, o que lo descarta.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C2-01 | Con un movimiento incompleto, no se registra ninguno y la pregunta los lista numerados | Integración | CA-8 |
| C2-02 | La respuesta por número completa el lote y se registran juntos | Integración | CA-9 y CA-10 |
| C2-03 | Una respuesta general vale para cada pendiente | Unitario | CA-9 |
| C2-04 | Mientras falte algo, la pregunta se repite con la lista actualizada | Unitario | CA-10 |
| C2-05 | Descartar uno por número registra los demás | Unitario | CA-11 |
| C2-06 | Descartar todos cierra el lote sin registrar nada | Unitario | CA-11 |
| C2-07 | Un movimiento que todavía no se sabe anotar se nombra aparte y los demás se registran | Unitario | CA-12 |
| C2-08 | Si ninguno se puede anotar, no queda nada pendiente | Unitario | CA-12 |
| C2-09 | Una respuesta que deja un pendiente sin poder anotarse lo saca del lote | Unitario | CA-12 |
| C2-10 | Con un lote esperando respuesta, otro movimiento se suma al lote | Integración | CA-13 |
| C2-11 | Con una transferencia pendiente, otro movimiento se suma y la lista la nombra en su moneda | Unitario | CA-13 |
| C2-12 | De un mensaje con más de 10, entran los primeros 10 | Unitario | CA-14 |
| C2-13 | Un lote con 9 suma uno solo de los dos que llegan | Unitario | CA-14 |
| C2-14 | Una respuesta a un número que no está en el lote no cambia nada | Unitario | CA-9 |
| C2-15 | El modelo recibe cada pendiente del lote con su número | Unitario | CA-9 |
| C2-16 | El adaptador devuelve las respuestas por número | Unitario | CA-9 |
| C2-17 | Un pendiente vencido sale del lote y la respuesta lo nombra; los demás se registran | Unitario | CA-18 |
| C2-18 | El modelo recibe solo los pendientes vigentes, y la lista sigue con los que faltan | Unitario | CA-18 |
| C2-19 | Si vencieron todos, el lote se cierra y el mensaje se procesa como nuevo | Unitario | CA-18 |

Reemplazan a C2-12 de [FEAT-003](../FEAT-003/spec.md) y a C2-12 y C2-15 de
[FEAT-006](../FEAT-006/spec.md), que probaban el aviso de CA-36 de FEAT-003: con CA-13 ese aviso
deja de existir, y sus tests se borran.

#### C2-01 · Con un movimiento incompleto, no se registra ninguno y la pregunta los lista numerados

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper con MP y 1200 de nafta", pendiente,
  y el modelo responde dos gastos: uno de 3500, cuenta "MP", categoría Supermercado, y uno de
  1200, sin cuenta, categoría Transporte,
- **cuando** el worker hace una ronda,
- **entonces** no hay ningún gasto en `TRANSACTION`; el único lote de Lucía espera respuesta
  (`open` y `awaiting_reply`), y su `question_message_id` es la respuesta; en ese lote hay dos
  pendientes `open`: el de la posición 1 con `missing_fields` vacío y el de
  la posición 2 con `missing_fields = ['account_id']`; y la respuesta, de tipo `registration`,
  es, línea por línea:

  > 1. El gasto de $3.500 en Supermercado con Mercado Pago, completo.
  >
  > 2. El gasto de $1.200 en Transporte.
  > ¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.

- **Test:** `tests/integration/test_pending_batch.py::test_with_an_incomplete_movement_none_is_registered_and_the_question_lists_them`

#### C2-02 · La respuesta por número completa el lote y se registran juntos

- **Sale de:** CA-9 y CA-10 · **Tipo:** integración
- **Dado** el lote de C2-01 esperando respuesta, un mensaje web nuevo de Lucía, "el 2 en
  efectivo", pendiente, y el modelo responde que contesta el pendiente 2 con cuenta "efectivo",
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` tiene el gasto de `3500.00` en Mercado Pago y el de `1200.00` en
  Efectivo; los dos pendientes quedan `promoted`, en sus posiciones 1 y 2, cada uno enlazado a su
  gasto; el lote deja de esperar respuesta y se cierra guardando la respuesta como su
  confirmación; y esa respuesta es la confirmación numerada de C1-02, con los dos gastos.
- **Test:** `tests/integration/test_pending_batch.py::test_the_reply_by_number_completes_the_batch_and_they_are_registered_together`

#### C2-03 · Una respuesta general vale para cada pendiente

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un lote de Lucía esperando respuesta con dos gastos sin cuenta, el 1 de $3.500 en
  Supermercado y el 2 de $1.200 en Transporte, el mensaje "todos con MP", y el modelo responde
  que contesta el pendiente 1 y el 2, los dos con cuenta "MP",
- **cuando** se procesa,
- **entonces** se registran los dos gastos en Mercado Pago, con una sola confirmación.
- **Test:** `tests/unit/test_pending_batch.py::test_a_general_reply_applies_to_each_pending`

#### C2-04 · Mientras falte algo, la pregunta se repite con la lista actualizada

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** un lote de Lucía esperando respuesta con dos gastos: el 1 de $3.500 en Supermercado,
  sin cuenta, y el 2 en Transporte con Efectivo, sin monto; el mensaje "el 1 con MP", y el modelo
  responde que contesta el pendiente 1 con cuenta "MP",
- **cuando** se procesa,
- **entonces** no se registra nada; el pendiente 1 queda `open` con `missing_fields` vacío y
  cuenta Mercado Pago; y la respuesta es:

  > 1. El gasto de $3.500 en Supermercado con Mercado Pago, completo.
  >
  > 2. El gasto en Transporte con Efectivo.
  > ¿Cuánto fue?

- **Test:** `tests/unit/test_pending_batch.py::test_while_something_is_missing_the_list_is_repeated_up_to_date`

#### C2-05 · Descartar uno por número registra los demás

- **Sale de:** CA-11 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 no lo anotes", y el modelo
  responde que descarta el pendiente 2,
- **cuando** se procesa,
- **entonces** el pendiente 2 queda `rejected`; el gasto de $3.500 en Mercado Pago se registra y
  el pendiente 1 queda `promoted`; el lote queda `closed`; y, como se registró uno solo, la
  respuesta es la confirmación de un movimiento solo, sin número, que empieza "¡Listo! Anoté un
  gasto de $3.500 en Mercado Pago.".
- **Test:** `tests/unit/test_pending_batch.py::test_discarding_one_by_number_registers_the_others`

#### C2-06 · Descartar todos cierra el lote sin registrar nada

- **Sale de:** CA-11 · **Tipo:** unitario
- **Dado** los dos pendientes de C2-01 sin contestar, Lucía escribe "no anotes ninguno", y el
  modelo responde que los descarta a todos,
- **cuando** se procesa,
- **entonces** no se registra nada; los dos pendientes quedan `rejected`; el lote queda `closed`
  con `awaiting_reply` falso; y la respuesta es "Listo, no anoto ninguno.".
- **Test:** `tests/unit/test_pending_batch.py::test_discarding_all_closes_the_batch_with_nothing_registered`

#### C2-07 · Un movimiento que todavía no se sabe anotar se nombra aparte y los demás se registran

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "gasté 3500 en el súper con MP y compré una heladera en 6 cuotas
  con la Visa", y el modelo responde un gasto de 3500, cuenta "MP", categoría Supermercado, y una
  compra con tarjeta,
- **cuando** se procesa,
- **entonces** se registra el gasto en un lote de uno, con el pendiente en la posición 1, y la
  respuesta es la confirmación de un movimiento solo, seguida de una línea en blanco y de "El
  segundo movimiento no lo anoté: eso todavía no lo sé anotar. Por ahora me manejo con gastos,
  ingresos y transferencias.".
- **Test:** `tests/unit/test_pending_batch.py::test_a_movement_that_cannot_be_registered_yet_is_named_apart`

#### C2-08 · Si ninguno se puede anotar, no queda nada pendiente

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "compré una heladera en 6 cuotas y pago el alquiler todos los
  meses", y el modelo responde una compra con tarjeta y una regla recurrente,
- **cuando** se procesa,
- **entonces** no se registra nada ni se crea ningún lote, y la respuesta tiene dos líneas: "El
  primer movimiento no lo anoté: eso todavía no lo sé anotar. Por ahora me manejo con gastos,
  ingresos y transferencias." y la misma con "El segundo".
- **Test:** `tests/unit/test_pending_batch.py::test_when_none_can_be_registered_nothing_is_left_pending`

#### C2-09 · Una respuesta que deja un pendiente sin poder anotarse lo saca del lote

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 con la Galicia USD", y el
  modelo responde que contesta el pendiente 2 con cuenta "Galicia USD", una cuenta en dólares
  para un gasto en un período en pesos,
- **cuando** se procesa,
- **entonces** el pendiente 2 queda `rejected`; el gasto de $3.500 en Mercado Pago se registra;
  y la respuesta es la confirmación de un movimiento solo, seguida de una línea en blanco y de
  "El 2 no lo anoté: eso todavía no lo sé anotar. Por ahora me manejo con gastos, ingresos y
  transferencias.".
- **Test:** `tests/unit/test_pending_batch.py::test_a_reply_that_leaves_a_pending_unregistrable_takes_it_out_of_the_batch`

#### C2-10 · Con un lote esperando respuesta, otro movimiento se suma al lote

- **Sale de:** CA-13 · **Tipo:** integración
- **Dado** el pendiente de C2-01 de [FEAT-003](../FEAT-003/spec.md) esperando respuesta, el gasto
  de $3.500 en Supermercado sin cuenta, en un lote de uno; un mensaje web nuevo de Lucía, "y
  1200 de nafta en efectivo", pendiente, y el modelo responde que trae otro movimiento, un gasto
  de 1200, cuenta "efectivo", categoría Transporte,
- **cuando** el worker hace una ronda,
- **entonces** no se registra nada; el lote sigue `open` y esperando respuesta, ahora con dos
  pendientes: el de la posición 1, sin cuenta, y uno nuevo en la posición 2, completo; el
  `question_message_id` del lote apunta a la respuesta; y la respuesta es:

  > 1. El gasto de $3.500 en Supermercado.
  > ¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.
  >
  > 2. El gasto de $1.200 en Transporte con Efectivo, completo.

- **Test:** `tests/integration/test_pending_batch.py::test_with_a_batch_awaiting_a_reply_another_movement_joins_it`

#### C2-11 · Con una transferencia pendiente, otro movimiento se suma y la lista la nombra en su moneda

- **Sale de:** CA-13 · **Tipo:** unitario
- **Dado** una transferencia pendiente de Lucía, "pasé 100 dólares", sin cuentas, y el mensaje
  "gasté 3500 en el súper con Mercado Pago", con el que el modelo responde que trae otro
  movimiento, un gasto completo,
- **cuando** se procesa,
- **entonces** no se registra nada; el gasto entra al lote en la posición 2; y la respuesta
  empieza "1. La transferencia de US$100.", seguida de las preguntas de las dos cuentas, y lista
  el gasto como "2. El gasto de $3.500 en Supermercado con Mercado Pago, completo.".
- **Test:** `tests/unit/test_pending_batch.py::test_with_a_pending_transfer_another_movement_joins_and_the_list_names_it_in_its_currency`

#### C2-12 · De un mensaje con más de 10, entran los primeros 10

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** un mensaje de Lucía con 12 gastos completos, y el modelo responde los 12,
- **cuando** se procesa,
- **entonces** se registran los primeros 10, en las posiciones 1 a 10 de un lote cerrado; los
  dos últimos no; y la confirmación termina con una línea en blanco y "Tomé solo los primeros 10
  movimientos. Los otros 2 mandámelos en otro mensaje.".
- **Test:** `tests/unit/test_pending_batch.py::test_of_a_message_with_more_than_10_the_first_10_go_in`

#### C2-13 · Un lote con 9 suma uno solo de los dos que llegan

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** un lote de Lucía esperando respuesta con 9 pendientes, y un mensaje con el que el
  modelo responde que trae otros dos movimientos completos,
- **cuando** se procesa,
- **entonces** entra el primero, en la posición 10; el segundo no entra; y la lista termina con
  una línea en blanco y "Tomé solo el primero de los movimientos nuevos. El otro mandámelo cuando
  terminemos con estos.".
- **Test:** `tests/unit/test_pending_batch.py::test_a_batch_with_9_adds_only_one_of_the_two_that_come`

#### C2-14 · Una respuesta a un número que no está en el lote no cambia nada

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 5 con MP", y el modelo responde
  que contesta el pendiente 5 con cuenta "MP",
- **cuando** se procesa,
- **entonces** no se registra nada, los dos pendientes siguen como estaban, y la respuesta repite
  la lista de C2-01.
- **Test:** `tests/unit/test_pending_batch.py::test_a_reply_to_a_number_that_is_not_in_the_batch_changes_nothing`

#### C2-15 · El modelo recibe cada pendiente del lote con su número

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, y el mensaje "el 2 en efectivo",
- **cuando** se procesa,
- **entonces** el pedido al modelo trae los dos pendientes, cada uno con su número, lo ya
  interpretado y lo que le falta, y la pregunta que recibió Lucía; y no trae ningún
  identificador.
- **Test:** `tests/unit/test_pending_batch.py::test_the_model_receives_each_pending_of_the_batch_with_its_number`

#### C2-16 · El adaptador devuelve las respuestas por número

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** el transporte HTTP del SDK, que responde la salida estructurada de una respuesta que
  contesta el pendiente 2 con cuenta "efectivo" y descarta el 1,
- **cuando** el adaptador clasifica el mensaje,
- **entonces** la clasificación tiene las dos respuestas por número: la del 2 con cuenta
  "efectivo", y la del 1, que lo descarta; y el esquema que se le pidió al modelo las devuelve
  como una lista.
- **Test:** `tests/unit/test_pending_batch.py::test_the_adapter_returns_the_replies_by_number`

#### C2-17 · Un pendiente vencido sale del lote y la respuesta lo nombra; los demás se registran

- **Sale de:** CA-18 · **Tipo:** unitario
- **Dado** un lote de Lucía esperando respuesta con el pendiente 1, el gasto de $3.500 en
  Supermercado sin cuenta, creado hace 26 horas, y el pendiente 2, el gasto de $1.200 en
  Transporte con Efectivo, completo, que se sumó hace 18 horas; el mensaje "el 1 con MP", y el
  modelo responde que contesta el pendiente 1 con cuenta "MP",
- **cuando** se procesa,
- **entonces** el pendiente 1 queda `expired` y no se registra; el gasto de $1.200 en Efectivo se
  registra y el pendiente 2 queda `promoted`; el lote queda `closed`; y la respuesta es la
  confirmación de un movimiento solo, seguida de una línea en blanco y de "El 1 no lo anoté:
  pasaron más de 24 horas.".
- **Test:** `tests/unit/test_pending_batch.py::test_an_expired_pending_leaves_the_batch_and_the_reply_names_it`

#### C2-18 · El modelo recibe solo los pendientes vigentes, y la lista sigue con los que faltan

- **Sale de:** CA-18 · **Tipo:** unitario
- **Dado** el lote de C2-17, pero con el pendiente 2 sin cuenta, y el mensaje "el 1 con MP",
- **cuando** se procesa,
- **entonces** el pedido al modelo trae solo el pendiente 2, con su número; no se registra nada;
  el pendiente 1 queda `expired` y el 2 sigue `open`; y la respuesta es, línea por línea:

  > 2. El gasto de $1.200 en Transporte.
  > ¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.
  >
  > El 1 no lo anoté: pasaron más de 24 horas.

- **Test:** `tests/unit/test_pending_batch.py::test_the_model_receives_only_the_pendings_still_valid`

#### C2-19 · Si vencieron todos, el lote se cierra y el mensaje se procesa como nuevo

- **Sale de:** CA-18 · **Tipo:** unitario
- **Dado** un lote de Lucía esperando respuesta con dos gastos sin cuenta, creados hace 26
  horas, el mensaje "gasté 500 en el súper con MP", y el modelo responde un gasto completo,
- **cuando** se procesa,
- **entonces** el pedido al modelo no trae ningún lote abierto; los dos pendientes quedan
  `expired` y su lote `closed`; y el gasto se registra en un lote nuevo de uno, con la
  confirmación de siempre, sin ningún aviso de vencimiento.
- **Test:** `tests/unit/test_pending_batch.py::test_when_all_expired_the_batch_closes_and_the_message_is_a_new_one`

### Corte 3 — observabilidad

- **Aprobado por:** pendiente

Los casos se escriben antes del corte.

## Mensajes al usuario

| Situación | Texto |
|---|---|
| Lote completo registrado | La confirmación de C1-02 |
| Un solo movimiento | La confirmación o la pregunta de [FEAT-003](../FEAT-003/spec.md) y [FEAT-006](../FEAT-006/spec.md), sin número |
| Lote con algo que falta | La lista numerada de C2-01: cada uno con lo ya interpretado, "completo" o lo que le falta |
| Se descartan todos | "Listo, no anoto ninguno." |
| Movimiento que todavía no se sabe anotar | "El {ordinal} movimiento no lo anoté: " y su texto fijo, en una línea propia (C2-07); si se cayó al responder, "El {número} no lo anoté: " (C2-09) |
| Más de 10 en un mensaje | "Tomé solo los primeros 10 movimientos. Los otros {n} mandámelos en otro mensaje.", o "El otro mandámelo en otro mensaje." si queda uno solo |
| Un lote que se llena con un mensaje nuevo | "Tomé solo el primero de los movimientos nuevos. El otro mandámelo cuando terminemos con estos.", o con "los primeros {n}" y "los otros {m}" |
| Pendiente vencido en un lote que sigue | "El {número} no lo anoté: pasaron más de 24 horas.", en una línea propia (C2-17) |
| Un lote que ya tiene 10, y llega otro movimiento | "Ya hay 10 movimientos en esta lista, así que no tomé los nuevos: mandámelos cuando terminemos con estos." |

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| Cada movimiento se resuelve como si llegara solo (§ 1) | C1-01, C1-03 y C1-05 |
| Los defaults van en la confirmación (§ 1) | C1-02 |
| Un lote nunca mezcla manuales y automáticos, y numera del 1 al 10 (§ 5) | C1-01 y C1-03 |
| La cuota cuenta mensajes (§ 12) | C1-06 |
| Montos en `Decimal`, con la moneda al lado | C1-01 y C1-07 |

## Sin cubrir

- Lo que el modelo decide, como separar "y 1200 de nafta" en otro movimiento, no lo prueba
  ningún test: se prueba a mano con el modelo real
  ([ADR 0028](../../adr/0028-el-modelo-interpreta-el-codigo-controla-las-invariantes.md)).
- Que un mensaje con un solo movimiento no cambie (CA-7) lo siguen probando los casos de
  FEAT-003 y FEAT-006, que deben pasar sin cambios.

## Fuera de alcance

Lo listado en [Alcance](#alcance) como "No entra".

## Preguntas abiertas

Ninguna.
