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
  son solo esos textos y no queda nada pendiente. Un pendiente que ya estaba en el lote y deja de
  poder anotarse, como cuando aparece otro período para su fecha, queda rechazado y la respuesta
  lo nombra por su número, tanto al contestar como al sumarse otro movimiento. Si el mensaje
  nuevo trae uno solo que no se puede anotar, la línea dice "Ese movimiento no lo anoté: " y no
  un ordinal.
- **CA-13.** Con un lote esperando respuesta, un mensaje que trae otro movimiento lo suma al lote
  con el número siguiente, y el asistente manda la lista actualizada. Reemplaza CA-36 de
  FEAT-003.
- **CA-14.** Un lote tiene como mucho 10 pendientes. Si un mensaje trae más de los que entran,
  entran los primeros hasta llegar a 10, y la respuesta dice cuántos tomó y pide mandar el resto
  después. Para llegar a 10 cuentan solo los que entran al lote: uno que no se puede anotar no
  ocupa un lugar. Cada número se usa una sola vez por lote, también el de un pendiente descartado
  o vencido, así que un lote que ya usó sus 10 números no toma otro movimiento aunque muestre
  menos. Decidido por Vero el 7/11/2026, con el `pr-reviewer`.
- **CA-18.** Cada pendiente del lote vence a las 24 horas de creado
  ([§ 5](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración)),
  aunque se haya sumado después que los otros. Uno vencido sale del lote, queda `expired`, y la
  respuesta lo nombra en una línea propia; los demás siguen con su número, y el modelo recibe
  solo esos. Si vencieron todos, el lote se cierra y el mensaje se procesa como si no hubiera
  nada abierto, como en CA-38 de [FEAT-003](../FEAT-003/spec.md). Decidido por Vero el
  7/11/2026, con el `/spec-drift` del corte 2 (issue #151).
- **CA-22.** Un mensaje puede contestar el lote y traer otro movimiento a la vez, como "el 2 con
  MP, y además 500 de café en efectivo": se aplica la respuesta por número, el movimiento nuevo
  no se anota, y la respuesta termina con "El movimiento nuevo mandámelo en otro mensaje." Así
  nunca se pierde en silencio. Decidido por Vero el 7/11/2026, con el `pr-reviewer`. Primero se
  decidió sumarlo al lote, y se cambió el mismo día: en la prueba con el modelo real, 1 de cada 4
  veces el modelo repetía un pendiente como movimiento nuevo, y el código lo habría anotado dos
  veces. Vale para toda respuesta al lote, también la que descarta todo: la respuesta conserva su
  texto, como la confirmación o "Listo, no anoto ninguno.", y el aviso va al final. Extendido por
  Vero el 7/11/2026, con la segunda pasada del `pr-reviewer`. Con un solo pendiente, la respuesta
  es la de un pendiente solo, "Listo, no lo anoto.", y con dos o más movimientos nuevos el aviso
  va en plural.
- **CA-23.** Los pendientes de un lote se leen siempre con el usuario del mensaje: los de un lote
  de otro usuario no se leen nunca ([AGENTS.md § 7](../../../AGENTS.md#7-seguridad)). Sumado por
  Vero el 7/11/2026, con el `pr-reviewer`.

### Observabilidad — corte 3

- **CA-15.** Los registros de un mensaje con varios movimientos dicen cuántos trajo y cuántos
  entraron al lote, sin montos, sin el texto del mensaje y sin nombres de cuentas.
- **CA-16.** La fila de `LLM_CALL` de una clasificación con varios movimientos dice qué campos
  vinieron vacíos en alguno de ellos. Cuántos movimientos devolvió no se guarda: el consumo se
  mide por llamada, y un mensaje con varios movimientos es una sola. Decidido por Vero el
  7/11/2026.
- **CA-17.** Cada pendiente del lote cuenta sus propias correcciones con la regla de § 5: "el 2
  fueron 3800" suma uno al pendiente 2 y no cambia los demás.
- **CA-19.** Lo que el código descarta de cualquier movimiento del mensaje, o de cualquier
  pendiente en una respuesta por número, marca la llamada `blocked`, como CA-47 de
  [FEAT-003](../FEAT-003/spec.md). Sumado por Vero el 7/11/2026, con el `/spec-drift` del
  corte 2.
- **CA-20.** Si no hay un lote abierto, el mensaje es nuevo aunque el modelo diga que contesta
  uno: cuál es el lote abierto lo sabe el código, no el modelo. Sumado por Vero el 7/11/2026,
  con la prueba a mano.
- **CA-21.** En cada movimiento del lote y en cada respuesta por número, el nombre completo de
  una cuenta que el mensaje no escribe no cuenta como mención, aunque el mensaje la nombre de
  otra forma, como "Mercado Pago" con "todos con mp": se descarta como cualquier mención no
  escrita (CA-9 de [FEAT-003](../FEAT-003/spec.md)), y que el modelo copie las palabras lo pide
  el prompt. Se probó aceptarlo si alguna parte del mensaje nombraba esa cuenta y ninguna otra, y
  se descartó el 7/11/2026 con el `pr-reviewer`: una palabra suelta como "pesos" o "pago", o las
  iniciales escritas para otro movimiento, alcanzaban para registrar en una cuenta que el
  movimiento no nombra. Decidido por Vero el 7/11/2026.

## Casos de prueba

Los tipos de caso, qué se reemplaza en cada uno y los datos de partida son los de
[FEAT-003](../FEAT-003/spec.md#casos-de-prueba), con los tipos de cuenta de
[FEAT-006](../FEAT-006/spec.md#casos-de-prueba).

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacarias 6/11/2026
- **C1-08 aprobado por:** Veronica Zacarias 7//11/2026
- **C1-09 y C1-10 aprobados por:** Veronica Zacarias 7//11/2026
- **Total:** 9 casos, 6 unitarios y 3 de integración. C1-09 se descartó.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Dos gastos completos en un mensaje quedan registrados en un lote | Integración | CA-3 y CA-4 |
| C1-02 | La confirmación de un lote lista cada movimiento con su número | Unitario | CA-5 |
| C1-03 | Un gasto y una transferencia en un mensaje quedan registrados | Integración | CA-3 y CA-4 |
| C1-04 | El gastado del período suma los dos gastos | Integración | CA-3 |
| C1-05 | Cada movimiento conserva su propia fecha | Unitario | CA-2 |
| C1-06 | Un mensaje con varios movimientos cuenta una vez en la cuota | Unitario | CA-6 |
| C1-07 | El adaptador devuelve cada movimiento del mensaje | Unitario | CA-1 |
| C1-08 | Sin lote abierto, un mensaje que el modelo marca como respuesta es nuevo | Unitario | CA-20 |
| C1-09 | El nombre completo de una cuenta que el mensaje nombra por sus iniciales cuenta como mención. Descartado | Unitario | CA-21 |
| C1-10 | El nombre completo de una cuenta que el mensaje nombra junto con otra no cuenta | Unitario | CA-21 |

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

#### C1-08 · Sin lote abierto, un mensaje que el modelo marca como respuesta es nuevo

- **Sale de:** CA-20 · **Tipo:** unitario
- **Dado** que Lucía no tiene ningún lote abierto, el mensaje "anotá: 1500 de carnicería, 10 mil
  de uber y 5400 de verdulería, todos con MP", y el modelo responde los tres gastos con cuenta
  "MP" pero marca el mensaje como respuesta a un lote ("continues"),
- **cuando** se procesa,
- **entonces** se registran los tres gastos, de $1.500, $10.000 y $5.400, en Mercado Pago, con
  una sola confirmación numerada.
- **Test:** `tests/unit/test_several_movements.py::test_with_no_open_batch_a_message_the_model_marks_as_a_reply_is_new`

#### C1-09 · El nombre completo de una cuenta que el mensaje nombra por sus iniciales cuenta como mención

- **Sale de:** CA-21 · **Tipo:** unitario
- **Dado** el mensaje "anotá: 1500 de carnicería y 10 mil de uber, todos con mp", y el modelo
  responde los dos gastos con cuenta "Mercado Pago", que el mensaje no escribe,
- **cuando** se procesa,
- **entonces** se registran los dos gastos, de $1.500 y $10.000, en Mercado Pago, y la llamada no
  queda marcada `blocked`: "mp" son las iniciales de Mercado Pago y de ninguna otra cuenta de
  Lucía.
- **Descartado:** la regla de la que salía (CA-21) se descartó el 7/11/2026, con el
  `pr-reviewer`. El test se borró con la aprobación de Vero.
- **Test:** —

#### C1-10 · El nombre completo de una cuenta que el mensaje nombra junto con otra no cuenta

- **Sale de:** CA-21 · **Tipo:** unitario
- **Dado** el mensaje "gasté 2000 en el súper con galicia", y el modelo responde un gasto con
  cuenta "Galicia pesos", que el mensaje no escribe,
- **cuando** se procesa,
- **entonces** no se registra ningún movimiento, la respuesta pregunta la cuenta, y la llamada
  queda marcada `blocked`: "galicia" nombra a Galicia pesos y a Galicia USD.
- **Test:** `tests/unit/test_several_movements.py::test_the_full_name_of_an_account_the_message_names_with_another_does_not_count`

### Corte 2 — lo que falta y lo que no se puede anotar

- **Aprobado por:** Veronica Zacarias 06/11/2026
- **C2-17 a C2-19, sumados con el `/spec-drift` del corte 2:** Veronica Zacarias 06/11/2026
- **C2-20 a C2-25, sumados con el `pr-reviewer`:** Veronica Zacarias 07/11/2026
- **C2-26 y C2-27, sumados con la segunda pasada del `pr-reviewer`:** Veronica Zacarias 07/11/2026
- **C2-28 y C2-29, sumados con las observaciones de la segunda pasada:** Veronica Zacarias 07/11/2026
- **Total:** 29 casos, 25 unitarios y 4 de integración.

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
| C2-20 | Un pendiente que deja de poder anotarse cuando se suma otro movimiento queda rechazado | Unitario | CA-12 |
| C2-21 | Lo que no se puede anotar no ocupa un lugar de los 10 | Unitario | CA-14 |
| C2-22 | Un lote que usó sus 10 números lo dice así, aunque muestre menos | Unitario | CA-14 |
| C2-23 | Una respuesta por número y un movimiento nuevo en el mismo mensaje: el nuevo se pide en otro mensaje | Unitario | CA-22 |
| C2-24 | Un solo movimiento nuevo que no se puede anotar se nombra sin ordinal | Unitario | CA-12 |
| C2-25 | Los pendientes de un lote no se leen con otro usuario | Integración | CA-23 |
| C2-26 | Descartar todos por número y traer un movimiento nuevo: se confirma el descarte y se avisa | Unitario | CA-11, CA-22 |
| C2-27 | Descartar el lote entero y traer un movimiento nuevo: se avisa | Unitario | CA-22 |
| C2-28 | Descartar un pendiente solo y traer un movimiento nuevo: la respuesta es la de un pendiente solo | Unitario | CA-22 |
| C2-29 | Una respuesta que trae dos movimientos nuevos avisa en plural | Unitario | CA-22 |

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

  > 2\. El gasto de $1.200 en Transporte.
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

#### C2-20 · Un pendiente que deja de poder anotarse cuando se suma otro movimiento queda rechazado

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el mensaje "ayer gasté 3500 en el súper", que deja el pendiente 1 esperando la cuenta;
  un segundo período de Lucía creado después, del 15/9 al 16/10, que también cubre ayer; y el
  mensaje "y 1200 de nafta con MP", de hoy, que el modelo responde como otro movimiento, un gasto
  completo,
- **cuando** se procesa,
- **entonces** se registra el gasto de $1.200 en Mercado Pago; el pendiente 1 queda `rejected`;
  el lote queda cerrado sin ningún pendiente `open`; y la respuesta termina con la línea "El 1 no
  lo anoté: " seguida del texto de más de un período posible, con la primera letra en minúscula
  como en C2-09. La fecha del súper, ayer, la cubren
  los dos períodos, y la de la nafta, hoy, solo el de octubre: corregido así por Vero el
  7/11/2026, porque con las dos del mismo día la nafta tampoco se podía anotar.
- **Test:** `tests/unit/test_pending_batch.py::test_a_pending_that_can_no_longer_be_registered_when_another_joins_is_rejected`

#### C2-21 · Lo que no se puede anotar no ocupa un lugar de los 10

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** un lote de 9 gastos esperando la cuenta, y el mensaje "compré una heladera en cuotas y
  500 de café con MP", que el modelo responde como otro movimiento con dos: una compra con tarjeta
  y un gasto completo,
- **cuando** se procesa,
- **entonces** el café entra al lote con el número 10, la lista lo muestra completo, la compra se
  nombra en una línea propia como no anotada, y la respuesta no dice que tomó solo una parte.
- **Test:** `tests/unit/test_pending_batch.py::test_what_cannot_be_registered_takes_no_place_of_the_10`

#### C2-22 · Un lote que usó sus 10 números lo dice así, aunque muestre menos

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** un lote de 10 gastos esperando la cuenta, de los que una respuesta descartó del 4 al 10,
  y el mensaje "y 500 de café con MP", que el modelo responde como otro movimiento completo,
- **cuando** se procesa,
- **entonces** el café no entra, la lista muestra los pendientes 1 a 3, y la respuesta termina con
  "Esta lista ya usó sus 10 números, así que no tomé los nuevos: mandámelos cuando terminemos con
  estos."
- **Test:** `tests/unit/test_pending_batch.py::test_a_batch_that_used_its_10_numbers_says_so_though_it_shows_fewer`

#### C2-23 · Una respuesta por número y un movimiento nuevo en el mismo mensaje: el nuevo se pide en otro mensaje

- **Sale de:** CA-22 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 con efectivo, y además 500 de
  café con MP", y el modelo responde que contesta el pendiente 2 con cuenta "efectivo" y trae,
  además, un gasto de 500 con cuenta "MP" y categoría Comida afuera y delivery,
- **cuando** se procesa,
- **entonces** se registran los dos gastos del lote, de $3.500 y $1.200, con la confirmación
  numerada; el café no se anota ni queda pendiente; y la respuesta termina con la línea "El
  movimiento nuevo mandámelo en otro mensaje." Cambiado por Vero el 7/11/2026, con CA-22.
- **Test:** `tests/unit/test_pending_batch.py::test_a_reply_by_number_and_a_new_movement_in_the_same_message`

#### C2-24 · Un solo movimiento nuevo que no se puede anotar se nombra sin ordinal

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, y el mensaje "compré una heladera en cuotas",
  que el modelo responde como otro movimiento, una compra con tarjeta,
- **cuando** se procesa,
- **entonces** el lote sigue con sus dos pendientes, y la respuesta repite la lista y termina con
  la línea "Ese movimiento no lo anoté: " seguida del texto de lo que todavía no se sabe anotar.
- **Test:** `tests/unit/test_pending_batch.py::test_a_single_new_movement_that_cannot_be_registered_is_named_without_an_ordinal`

#### C2-25 · Los pendientes de un lote no se leen con otro usuario

- **Sale de:** CA-23 · **Tipo:** integración
- **Dado** el lote de C2-01 de Lucía guardado en PostgreSQL,
- **cuando** el repositorio lee los pendientes de ese lote con el usuario de Pablo,
- **entonces** la lista está vacía; y con el de Lucía tiene los dos pendientes, en orden.
- **Test:** `tests/integration/test_pending_batch.py::test_the_pendings_of_a_batch_are_not_read_with_another_user`

#### C2-26 · Descartar todos por número y traer un movimiento nuevo: se confirma el descarte y se avisa

- **Sale de:** CA-11 y CA-22 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 1 y el 2 no, y anotá 500 de café
  con MP", y el modelo responde que descarta los pendientes 1 y 2 por número y trae, además, un
  gasto de 500 con cuenta "MP" y categoría Comida afuera y delivery,
- **cuando** se procesa,
- **entonces** no se registra ningún gasto, los dos pendientes quedan rechazados y el lote
  cerrado, y la respuesta es "Listo, no anoto ninguno." seguida de la línea "El movimiento nuevo
  mandámelo en otro mensaje."
- **Test:** `tests/unit/test_pending_batch.py::test_discarding_all_by_number_with_a_new_movement_confirms_and_warns`

#### C2-27 · Descartar el lote entero y traer un movimiento nuevo: se avisa

- **Sale de:** CA-22 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "no anotes ninguno, anotá solo 500 de
  café con MP", y el modelo responde que descarta el lote y trae, además, un gasto de 500 con
  cuenta "MP" y categoría Comida afuera y delivery,
- **cuando** se procesa,
- **entonces** no se registra ningún gasto, los dos pendientes quedan rechazados y el lote
  cerrado, y la respuesta es "Listo, no anoto ninguno." seguida de la línea "El movimiento nuevo
  mandámelo en otro mensaje."
- **Test:** `tests/unit/test_pending_batch.py::test_discarding_the_whole_batch_with_a_new_movement_warns`

#### C2-28 · Descartar un pendiente solo y traer un movimiento nuevo: la respuesta es la de un pendiente solo

- **Sale de:** CA-22 · **Tipo:** unitario
- **Dado** el mensaje "gasté 1200 de nafta", que deja un pendiente solo esperando la cuenta, el
  mensaje "no lo anotes, y anotá 500 de café con MP", y el modelo responde que descarta el
  pendiente y trae, además, un gasto de 500 con cuenta "MP" y categoría Comida afuera y delivery,
- **cuando** se procesa,
- **entonces** no se registra ningún gasto, el pendiente queda rechazado, y la respuesta es
  "Listo, no lo anoto." seguida de la línea "El movimiento nuevo mandámelo en otro mensaje."
- **Test:** `tests/unit/test_pending_batch.py::test_discarding_a_lone_pending_with_a_new_movement_answers_as_a_lone_pending`

#### C2-29 · Una respuesta que trae dos movimientos nuevos avisa en plural

- **Sale de:** CA-22 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 con efectivo, y además 500 de
  café y 800 del diario con MP", y el modelo responde que contesta el pendiente 2 con cuenta
  "efectivo" y trae, además, un gasto de 500 y otro de 800, los dos con cuenta "MP",
- **cuando** se procesa,
- **entonces** se registran los dos gastos del lote, de $3.500 y $1.200; ninguno de los nuevos se
  anota; y la respuesta termina con la línea "Los movimientos nuevos mandámelos en otro mensaje."
- **Test:** `tests/unit/test_pending_batch.py::test_a_reply_that_brings_two_new_movements_warns_in_plural`

### Corte 3 — observabilidad

- **Aprobado por:** Veronica Zacarias 07/11/2026
- **C3-07, sumado con el `pr-reviewer`:** Veronica Zacarias 07/11/2026
- **Total:** 7 casos, 5 unitarios y 2 de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C3-01 | Los registros de un mensaje con varios movimientos dicen cuántos trajo y cuántos entraron al lote, sin datos del usuario | Integración | CA-15 |
| C3-02 | La fila de la clasificación lista los campos vacíos de cualquiera de los movimientos | Unitario | CA-16 |
| C3-03 | Una respuesta por número suma la corrección solo al pendiente que cambia | Unitario | CA-17 |
| C3-04 | Las correcciones de cada pendiente del lote quedan guardadas | Integración | CA-17 |
| C3-05 | Una cuenta no escrita en el segundo movimiento del mensaje marca la llamada `blocked` | Unitario | CA-19 |
| C3-06 | Una cuenta no escrita en una respuesta por número marca la llamada `blocked` | Unitario | CA-19 |
| C3-07 | Sin lote abierto, la fila lista los campos vacíos de los movimientos y no de las respuestas | Unitario | CA-16 y CA-20 |

#### C3-01 · Los registros de un mensaje con varios movimientos dicen cuántos trajo y cuántos entraron al lote, sin datos del usuario

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper con MP, 1200 de nafta en efectivo y
  compré una heladera en cuotas", pendiente, y el modelo responde dos gastos completos y una
  compra con tarjeta,
- **cuando** el worker hace una ronda,
- **entonces** la línea `message.answered` del mensaje dice `movements: 3` y `batched: 2`; y
  ninguna línea de los registros contiene "3500", "3.500", "1200", "1.200", "súper",
  "heladera", "Mercado Pago", "Efectivo", "Lucía" ni "000000000001".
- **Test:** `tests/integration/test_batch_observability.py::test_the_line_of_a_message_with_several_movements_says_how_many_came_and_entered`

#### C3-02 · La fila de la clasificación lista los campos vacíos de cualquiera de los movimientos

- **Sale de:** CA-16 · **Tipo:** unitario
- **Dado** el envoltorio que registra las llamadas, y un modelo que responde dos gastos: uno de
  3500 con cuenta "MP" y categoría Supermercado, y uno de 1200 sin cuenta, con categoría
  Transporte, los dos sin moneda ni fecha,
- **cuando** se clasifica el mensaje,
- **entonces** la fila de `LLM_CALL` tiene `empty_fields` igual a `account`, `currency` y
  `transaction_date`: la cuenta vacía del segundo cuenta aunque el primero la tenga.
- **Test:** `tests/unit/test_batch_observability.py::test_the_row_of_the_classification_lists_the_empty_fields_of_any_movement`

#### C3-03 · Una respuesta por número suma la corrección solo al pendiente que cambia

- **Sale de:** CA-17 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 fueron 1300 en efectivo", y el
  modelo responde que contesta el pendiente 2 con monto 1300 y cuenta "efectivo",
- **cuando** se procesa,
- **entonces** se registran los dos gastos; el pendiente 2 queda con `corrected_fields_count`
  1, porque cambió el monto, y la cuenta que faltaba no suma; y el pendiente 1 queda con 0.
- **Test:** `tests/unit/test_batch_observability.py::test_a_reply_by_number_adds_the_correction_only_to_the_pending_it_changes`

#### C3-04 · Las correcciones de cada pendiente del lote quedan guardadas

- **Sale de:** CA-17 · **Tipo:** integración
- **Dado** el lote de C2-01 esperando respuesta, un mensaje web nuevo de Lucía, "el 2 fueron
  1300 en efectivo", pendiente, y el modelo responde como en C3-03,
- **cuando** el worker hace una ronda,
- **entonces** en `PENDING_TRANSACTION` el pendiente de la posición 2 tiene
  `corrected_fields_count = 1` y el de la posición 1, `0`.
- **Test:** `tests/integration/test_batch_observability.py::test_the_corrections_of_each_pending_of_the_batch_are_stored`

#### C3-05 · Una cuenta no escrita en el segundo movimiento del mensaje marca la llamada `blocked`

- **Sale de:** CA-19 · **Tipo:** unitario
- **Dado** el mensaje "gasté 3500 en el súper con MP y 1200 de nafta", y el modelo responde dos
  gastos: el primero con cuenta "MP" y el segundo con cuenta "Brubank", que el mensaje no
  escribe,
- **cuando** se procesa,
- **entonces** la llamada queda marcada `blocked`, y el segundo gasto queda sin cuenta.
- **Test:** `tests/unit/test_batch_observability.py::test_an_account_not_written_in_the_second_movement_leaves_the_call_blocked`

#### C3-06 · Una cuenta no escrita en una respuesta por número marca la llamada `blocked`

- **Sale de:** CA-19 · **Tipo:** unitario
- **Dado** el lote de C2-01 esperando respuesta, el mensaje "el 2 en efectivo", y el modelo
  responde que contesta el pendiente 2 con cuenta "Mercado Pago", que la respuesta no escribe,
- **cuando** se procesa,
- **entonces** la llamada queda marcada `blocked`, y el pendiente 2 sigue sin cuenta.
- **Test:** `tests/unit/test_batch_observability.py::test_an_account_not_written_in_a_reply_by_number_leaves_the_call_blocked`

#### C3-07 · Sin lote abierto, la fila lista los campos vacíos de los movimientos y no de las respuestas

- **Sale de:** CA-16 y CA-20 · **Tipo:** unitario
- **Dado** el envoltorio que registra las llamadas, un pedido sin lote abierto, y un modelo que
  responde un gasto de 3500 con cuenta "MP" y categoría Supermercado, sin moneda ni fecha, y
  marca el mensaje como respuesta con una respuesta por número que solo trae un monto,
- **cuando** se clasifica el mensaje,
- **entonces** la fila de `LLM_CALL` tiene `empty_fields` igual a `currency` y
  `transaction_date`: los del gasto, no los de la respuesta.
- **Test:** `tests/unit/test_batch_observability.py::test_with_no_open_batch_the_row_lists_the_empty_fields_of_the_movements`

## Mensajes al usuario

| Situación | Texto |
|---|---|
| Lote completo registrado | La confirmación de C1-02 |
| Un solo movimiento | La confirmación o la pregunta de [FEAT-003](../FEAT-003/spec.md) y [FEAT-006](../FEAT-006/spec.md), sin número |
| Lote con algo que falta | La lista numerada de C2-01: cada uno con lo ya interpretado, "completo" o lo que le falta |
| Se descartan todos | "Listo, no anoto ninguno." |
| Movimiento que todavía no se sabe anotar | "El {ordinal} movimiento no lo anoté: " y su texto fijo, en una línea propia (C2-07); si es el único movimiento nuevo de un lote abierto, "Ese movimiento no lo anoté: " (C2-24); si se cayó al responder o al sumarse otro, "El {número} no lo anoté: " (C2-09 y C2-20) |
| Más de 10 en un mensaje | "Tomé solo los primeros {N} movimientos. Los otros {n} mandámelos en otro mensaje.", o "El otro mandámelo en otro mensaje." si queda uno solo. {N} son los que se leyeron: 10, más los que no se pueden anotar y se nombran aparte (C2-12, C2-21) |
| Un lote que se llena con un mensaje nuevo | "Tomé solo el primero de los movimientos nuevos. El otro mandámelo cuando terminemos con estos.", o con "los primeros {n}" y "los otros {m}" |
| Una respuesta que trae además un movimiento nuevo | "El movimiento nuevo mandámelo en otro mensaje.", en una línea propia al final, también después de un descarte (C2-23, C2-26 a C2-28); con dos o más, "Los movimientos nuevos mandámelos en otro mensaje." (C2-29) |
| Pendiente vencido en un lote que sigue | "El {número} no lo anoté: pasaron más de 24 horas.", en una línea propia (C2-17) |
| Un lote que ya usó sus 10 números, y llega otro movimiento | "Esta lista ya usó sus 10 números, así que no tomé los nuevos: mandámelos cuando terminemos con estos." (C2-22) |

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
