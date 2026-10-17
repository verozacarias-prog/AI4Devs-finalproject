# Especificación — FEAT-003 · Registro de un gasto y de un ingreso

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Estado:** aprobada para el corte 1. Los casos de los cortes 2 y 3 están en borrador
- **Fecha:** 2026-10-16

## Alcance

Entra el modelo de lenguaje en el worker: la llamada inicial que clasifica cada mensaje y, si es
un registro, devuelve sus campos ([ADR 0018](../../adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md)),
con GPT-5.4 mini ([ADR 0025](../../adr/0025-gpt-5-4-mini-como-modelo-de-lenguaje.md)) detrás del
puerto de LLM y del envoltorio que registra cada llamada en `LLM_CALL`
([ADR 0023](../../adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md)).
Con eso, un gasto o un ingreso escrito en el chat web queda registrado y se ve en la pantalla de
cuentas. Reemplaza el texto fijo que el worker responde desde
[FEAT-002](../FEAT-002/spec.md).

Es la parte de la HU3 que la [hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-2) pone
en la entrega 2, partida en los tres cortes de las
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales):

1. **Camino feliz.** Un gasto y un ingreso con todo lo que hace falta a la vista quedan
   registrados en un solo mensaje, y lo que el asistente todavía no sabe hacer responde su texto fijo.
2. **Errores y lo que exige confirmación.** Preguntar lo que falta, el pendiente y su
   continuación, la categoría nueva con confirmación, y lo que pasa cuando el modelo falla: los
   reintentos con espera creciente, el estado `failed` y su aviso, que
   [FEAT-002](../FEAT-002/spec.md#alcance) dejó para cuando existiera el modelo.
3. **Límites y observabilidad.** El tope diario total y las tres cuotas, los registros sin datos
   del usuario, lo que se envía al proveedor, y el script de métricas.

No hay pantalla nueva: el gasto se escribe en el chat de FEAT-002 y su efecto se ve en la de
cuentas de [FEAT-001](../FEAT-001/spec.md).

## Reglas de dominio que aplican

- [§ 1 — Registro de un movimiento: qué se asume y qué se confirma](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)
- [§ 2 — Cuentas y saldo calculado](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado), en
  la resolución de la cuenta por su nombre y en que nada se registra antes de su alta.
- [§ 3 — Presupuestos](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio),
  en que solo un período confirmado recibe movimientos.
- [§ 4 — Categorías](../../reglas-de-dominio.md#4-categorías-catálogo-base-categorías-propias-y-creación-con-confirmación)
- [§ 5 — PENDING_TRANSACTION](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración),
  desde el corte 2.
- [§ 12 — Límites de uso del asistente](../../reglas-de-dominio.md#12-límites-de-uso-del-asistente),
  en el corte 3.
- [§ 14 — Datos que salen hacia el proveedor de LLM](../../reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos)

Y las decisiones de arquitectura del modelo: los ADR
[0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md),
[0013](../../adr/0013-datos-minimos-al-proveedor-de-llm.md),
[0018](../../adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md),
[0020](../../adr/0020-sin-framework-de-orquestacion-de-ia.md),
[0023](../../adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md) y
[0025](../../adr/0025-gpt-5-4-mini-como-modelo-de-lenguaje.md).

## Criterios de aceptación

Una regla por criterio. Los de los cortes 2 y 3 están escritos para ver el alcance completo, y
se revisan junto con sus casos, antes de empezar cada corte.

### Interpretar el mensaje

Una sola llamada al modelo dice qué es el mensaje y, si es un registro, qué hay que registrar.

- **CA-1.** Cada mensaje se clasifica con una sola llamada al modelo, que dice si es un registro, una consulta, un consejo o ninguna de las tres, y, si es un registro, qué tipo de registro es y sus campos.
- **CA-2.** Al modelo le llegan el texto del mensaje, los nombres de las cuentas y de las categorías del usuario y el día en que escribió, y nunca un identificador.
- **CA-3.** Cada llamada al modelo deja una fila en `LLM_CALL` con su propósito, su modelo, sus tokens, su duración, su costo y su resultado, y sin ningún contenido.
- **CA-4.** Un monto llega del modelo al movimiento como `Decimal`, sin pasar nunca por `float`.

### Registrar un gasto o un ingreso

Lo que se puede resolver a la vista se registra en un solo mensaje.

- **CA-5.** Un gasto o un ingreso que dice el monto, nombra una cuenta que coincide con una sola del usuario, encaja en una de sus categorías y cae en un solo período posible, que está confirmado, queda registrado sin preguntar nada.
- **CA-6.** La fecha es el día en que el usuario escribió, en su zona horaria, salvo que el mensaje diga otra.
- **CA-7.** La moneda es la de la cuenta que nombra el mensaje.
- **CA-8.** La cuenta y la categoría se reconocen por su nombre sin distinguir mayúsculas.
- **CA-9.** La cuenta la decide el código, con la mención y la moneda que devuelve el modelo: la mención tiene que estar escrita en el mensaje; una mención con todas las palabras del nombre de una sola cuenta la nombra; si no, la nombran una palabra de su nombre, sus iniciales o su tipo, y una moneda dicha deja solo las cuentas en esa moneda; con exactamente una candidata se usa esa, y con ninguna o varias no se registra ([reglas de dominio § 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)).
- **CA-10.** Un gasto o un ingreso con fecha anterior al alta de su cuenta no se registra, y la respuesta explica que la cuenta registra desde su alta y que eso ya está en el saldo con que se dio de alta ([reglas de dominio § 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado)).
- **CA-11.** El movimiento queda con `source = 'manual'`.
- **CA-12.** La confirmación dice si fue un gasto o un ingreso, el monto y la cuenta, y lista la fecha, la moneda, la categoría y el presupuesto.
- **CA-13.** Un gasto o un ingreso completo también pasa por un lote de uno: su pendiente queda promovido y el lote cerrado, con la confirmación como `confirmation_message_id`, para que esa confirmación se pueda citar.
- **CA-14.** El movimiento, su pendiente, su lote, el mensaje procesado y la confirmación se guardan juntos, o no se guarda ninguno.
- **CA-15.** El saldo de la cuenta, en la pantalla de cuentas, ya incluye el movimiento.

### Lo que el asistente todavía no sabe hacer

- **CA-16.** Un registro que no es un gasto ni un ingreso recibe un texto fijo, no registra nada y no vuelve a llamar al modelo.
- **CA-17.** Una consulta o un consejo recibe un texto fijo y no vuelve a llamar al modelo.
- **CA-18.** Un mensaje que no es de ninguna clase, como un saludo, recibe un texto fijo que pide una aclaración.

### Preguntar lo que falta — corte 2

- **CA-19.** Un gasto o un ingreso sin cuenta no usa ninguna por defecto: queda pendiente y el asistente pregunta, ofreciendo las cuentas del usuario.
- **CA-20.** Una cuenta nombrada que coincide con más de una, como "la Galicia", se pregunta ofreciendo las que coinciden.
- **CA-21.** Un mensaje sin monto, o que no deja claro si es gasto o ingreso, queda pendiente y se pregunta.
- **CA-22.** Cuando falta más de un dato, se preguntan todos en un solo mensaje, y lo ya interpretado se conserva.
- **CA-23.** La respuesta del usuario continúa el pendiente y, completo, lo promueve a movimiento.
- **CA-24.** Si ninguna categoría encaja, el asistente propone crear una y no la crea sin confirmación.
- **CA-25.** Un único período posible que está en borrador deja el movimiento pendiente.

### Cuando algo falla — corte 2

- **CA-26.** Si la llamada al modelo falla o devuelve algo que no se puede validar, el mensaje se reintenta con espera creciente; agotados los intentos queda `failed`, el usuario recibe un aviso y su siguiente mensaje se procesa.
- **CA-27.** Si dos workers terminan el mismo mensaje, queda un solo movimiento.
- **CA-28.** Si el tiempo máximo de la llamada al modelo no es menor que la duración del lock, ningún proceso arranca.

### Límites y observabilidad — corte 3

- **CA-29.** Con el tope diario total alcanzado, el mensaje no se clasifica y se procesa al día siguiente.
- **CA-30.** Con la cuota de registro agotada, el mensaje se demora al día siguiente, y una consulta o un consejo con su cuota agotada recibe un texto fijo.
- **CA-31.** Ninguna línea de los registros lleva el texto, el monto ni el teléfono.
- **CA-32.** El prompt de sistema es el mismo para todos los usuarios.
- **CA-33.** Una llamada al modelo cuyo mensaje termina con la transacción final deshecha deja igual su fila en `LLM_CALL`, y el worker usa siempre el envoltorio.
- **CA-34.** Cada fila de `LLM_CALL` de una clasificación dice qué campos de la salida vinieron vacíos, sin ningún valor, para poder diagnosticar una interpretación fallida sin guardar contenido. Sumado el 17/10/2026, después de que un mensaje de la prueba contra el modelo real no se registrara sin que pudiera saberse por qué. Necesita una columna nueva en `LLM_CALL`.
- **CA-35.** `scripts/llm_metrics.sql` da la latencia, el costo, la calidad y las respuestas bloqueadas del ADR 0023.

## Casos de prueba

Siguen la forma de [FEAT-002](../FEAT-002/spec.md#casos-de-prueba), con una diferencia en lo
que se reemplaza:

- En un caso **unitario** la acción es un caso de uso o el adaptador del modelo, con los puertos
  reemplazados por dobles, sin base de datos y sin red.
- En un caso de **integración** los datos están guardados en PostgreSQL y la acción es una ronda
  del worker o un pedido a [la API](../../04-api.md).
- Ningún test llama al proveedor real. Donde el caso dice "el modelo responde", el puerto de LLM
  es un doble que devuelve esa interpretación; en los casos del adaptador, lo que se reemplaza
  es el transporte HTTP del SDK.

Salvo que el caso diga otra cosa: la base tiene los datos de prueba de `local`, creados el 1 de
octubre de 2026; Lucía es de Buenos Aires y su teléfono es +000000000001; tiene las cuentas
Galicia pesos ($350.000), Mercado Pago ($80.000), Efectivo ($25.000) y Galicia USD (US$500),
todas dadas de alta ese día, y un solo período, individual, confirmado, en pesos, del 1 al 31 de
octubre; no es miembro de ningún grupo; y en Buenos Aires son las 15:00 del sábado 17 de octubre
de 2026, 2026-10-17T18:00:00Z.

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacarias 16/10/2026
- **C1-17 a C1-23, sumados con la prueba contra el modelo real, que registró dos gastos en una cuenta que el mensaje no decía:** Veronica Zacarias 17/10/2026
- **C1-24, el motivo de un gasto anterior al alta de su cuenta, sumado con la prueba contra el modelo real:** Veronica Zacarias 17/10/2026
- **C1-25, el nombre de otra cuenta fuera de la mención, sumado con la segunda revisión de pr-reviewer:** Veronica Zacarias 17/10/2026
- **Total:** 25 casos, 17 unitarios y 8 de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Un gasto que nombra la cuenta queda registrado | Integración | CA-5, CA-7, CA-11, CA-13 y CA-14 |
| C1-02 | Un ingreso que nombra la cuenta queda registrado | Integración | CA-5 y CA-7 |
| C1-03 | La confirmación de un gasto lista lo que se asumió | Unitario | CA-12 |
| C1-04 | La confirmación de un ingreso dice que es un ingreso | Unitario | CA-12 |
| C1-05 | El saldo de la cuenta ya incluye el gasto | Integración | CA-15 |
| C1-06 | La fecha es el día en que escribió, no el día en que se procesa | Unitario | CA-6 |
| C1-07 | Una fecha que el mensaje indica se respeta | Unitario | CA-6 |
| C1-08 | La cuenta y la categoría se reconocen sin distinguir mayúsculas | Unitario | CA-8 |
| C1-09 | Una transferencia recibe el texto fijo y no registra nada | Integración | CA-16 |
| C1-10 | Una consulta recibe el texto fijo | Integración | CA-17 |
| C1-11 | Un consejo recibe el texto fijo | Unitario | CA-17 |
| C1-12 | Un saludo recibe el pedido de aclaración | Integración | CA-18 |
| C1-13 | La clasificación deja su fila en `LLM_CALL` | Integración | CA-3 |
| C1-14 | El adaptador pide al modelo configurado una salida estructurada | Unitario | CA-1 y CA-2 |
| C1-15 | El adaptador devuelve el monto como `Decimal` | Unitario | CA-4 |
| C1-16 | Escribir un gasto en el chat y ver la confirmación | Integración | CA-5 y CA-12 |
| C1-17 | Una cuenta que el mensaje no escribe no se usa | Unitario | CA-9 |
| C1-18 | Un nombre a medias sin moneda no elige entre dos cuentas | Unitario | CA-9 |
| C1-19 | Un nombre a medias con la moneda dicha elige la cuenta | Unitario | CA-9 |
| C1-20 | Las iniciales nombran una cuenta | Unitario | CA-9 |
| C1-21 | El tipo y la moneda nombran una cuenta | Unitario | CA-9 |
| C1-22 | El tipo sin moneda no elige entre dos cuentas | Unitario | CA-9 |
| C1-23 | El adaptador devuelve la moneda que dice el mensaje | Unitario | CA-9 |
| C1-24 | Un gasto anterior al alta de su cuenta explica por qué no se anota | Unitario | CA-10 |
| C1-25 | El nombre de otra cuenta fuera de la mención no cambia la cuenta | Unitario | CA-9 |

#### C1-01 · Un gasto que nombra la cuenta queda registrado

- **Sale de:** CA-5, CA-7, CA-11, CA-13 y CA-14 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper con Mercado Pago", pendiente, con
  `sent_at` 2026-10-17T17:59:55Z, y el modelo responde que es un registro de tipo gasto, con
  monto 3500, cuenta "Mercado Pago" y categoría "Supermercado", sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` tiene una sola fila, de Lucía, con `type = 'expense'`,
  `amount = 3500.00`, `currency = 'ARS'`, la cuenta Mercado Pago, la categoría base
  Supermercado, su período de octubre, `transaction_date = 2026-10-17`, `source = 'manual'`,
  `exchange_rate` nulo y `description` nula; `PENDING_BATCH` tiene un solo lote de Lucía, manual,
  `closed`, con `awaiting_reply` falso; `PENDING_TRANSACTION` tiene un solo pendiente en ese
  lote, en la posición 1, manual, `promoted`, con `intent = 'transaction'`, `missing_fields`
  vacío y `resulting_transaction_id` igual al movimiento; el mensaje queda `processed`; y
  `OUTBOUND_MESSAGE` tiene una sola respuesta a ese mensaje, con
  `response_kind = 'registration'`, que es el `confirmation_message_id` del lote.
- **Test:** `tests/integration/test_registration.py::test_an_expense_that_names_the_account_is_registered`

#### C1-02 · Un ingreso que nombra la cuenta queda registrado

- **Sale de:** CA-5 y CA-7 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "cobré 850000 de sueldo en la Galicia pesos", pendiente, y
  el modelo responde que es un registro de tipo ingreso, con monto 850000, cuenta "Galicia
  pesos" y categoría "Sueldo", sin fecha,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` tiene una sola fila, de Lucía, con `type = 'income'`,
  `amount = 850000.00`, `currency = 'ARS'`, la cuenta Galicia pesos, la categoría base Sueldo,
  su período de octubre y `transaction_date = 2026-10-17`; y la respuesta tiene
  `response_kind = 'registration'`.
- **Test:** `tests/integration/test_registration.py::test_an_income_that_names_the_account_is_registered`

#### C1-03 · La confirmación de un gasto lista lo que se asumió

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el gasto de C1-01 ya resuelto: $3.500, Mercado Pago, Supermercado, 17/10/2026, ARS,
  y el período individual del 1/10/2026 al 31/10/2026,
- **cuando** se arma la confirmación,
- **entonces** el texto es, línea por línea:

  > ¡Listo! Anoté un gasto de $3.500 en Mercado Pago.
  > Fecha: 17/10/2026
  > Moneda: ARS
  > Categoría: Supermercado
  > Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026

- **Test:** `tests/unit/test_registration_confirmation.py::test_the_confirmation_of_an_expense_lists_what_was_assumed`

#### C1-04 · La confirmación de un ingreso dice que es un ingreso

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** el ingreso de C1-02 ya resuelto: $850.000, Galicia pesos, Sueldo, 17/10/2026, ARS, y
  el mismo período,
- **cuando** se arma la confirmación,
- **entonces** su primera línea es "¡Listo! Anoté un ingreso de $850.000 en Galicia pesos.", y
  las otras cuatro son las de C1-03 con "Categoría: Sueldo".
- **Test:** `tests/unit/test_registration_confirmation.py::test_the_confirmation_of_an_income_says_it_is_an_income`

#### C1-05 · El saldo de la cuenta ya incluye el gasto

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** el gasto de C1-01 ya procesado, y ningún otro movimiento de Lucía,
- **cuando** Lucía pide `GET /accounts`,
- **entonces** Mercado Pago tiene saldo `76500.00`, que es 80.000 − 3.500, y las otras tres
  cuentas conservan su saldo inicial.
- **Test:** `tests/integration/test_registration.py::test_the_balance_of_the_account_already_includes_the_expense`

#### C1-06 · La fecha es el día en que escribió, no el día en que se procesa

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** un mensaje de Lucía con `sent_at` 2026-10-17T02:30:00Z, que en Buenos Aires es el 16
  de octubre a las 23:30, y el modelo responde un gasto sin fecha,
- **cuando** se procesa con el reloj en 2026-10-17T18:00:00Z,
- **entonces** el movimiento tiene `transaction_date = 2026-10-16`, y al modelo le llegó ese
  mismo día, 2026-10-16, como el día en que el usuario escribió.
- **Test:** `tests/unit/test_answer_message.py::test_the_date_is_the_day_she_wrote_not_the_day_it_is_processed`

#### C1-07 · Una fecha que el mensaje indica se respeta

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "ayer gasté 1200 de nafta con Efectivo", y el modelo responde un
  gasto con fecha 2026-10-16, cuenta "Efectivo" y categoría "Transporte",
- **cuando** se procesa,
- **entonces** el movimiento tiene `transaction_date = 2026-10-16`, y la confirmación dice
  "Fecha: 16/10/2026".
- **Test:** `tests/unit/test_answer_message.py::test_a_date_the_message_gives_is_kept`

#### C1-08 · La cuenta y la categoría se reconocen sin distinguir mayúsculas

- **Sale de:** CA-8 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, y el modelo responde un gasto con cuenta "mercado pago" y
  categoría "SUPERMERCADO",
- **cuando** se procesa,
- **entonces** el movimiento queda en la cuenta Mercado Pago y en la categoría Supermercado, y
  la confirmación los nombra como están guardados: "Mercado Pago" y "Supermercado".
- **Test:** `tests/unit/test_answer_message.py::test_the_account_and_the_category_are_recognized_whatever_their_case`

#### C1-09 · Una transferencia recibe el texto fijo y no registra nada

- **Sale de:** CA-16 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "pasé 20000 de Galicia pesos a Mercado Pago", pendiente, y
  el modelo responde que es un registro de tipo transferencia,
- **cuando** el worker hace una ronda,
- **entonces** `TRANSACTION` y `TRANSFER` siguen vacías, el modelo recibió una sola llamada, el
  mensaje queda `processed`, y la respuesta es "Eso todavía no lo sé anotar. Por ahora me
  manejo con gastos e ingresos.", con `response_kind = 'fixed_text'`.
- **Test:** `tests/integration/test_registration.py::test_a_transfer_gets_the_fixed_text_and_registers_nothing`

#### C1-10 · Una consulta recibe el texto fijo

- **Sale de:** CA-17 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "¿cuánto gasté este mes?", pendiente, y el modelo responde
  que es una consulta,
- **cuando** el worker hace una ronda,
- **entonces** el modelo recibió una sola llamada, el mensaje queda `processed`, y la respuesta
  es "Todavía no sé responder preguntas. Por ahora anoto gastos e ingresos, y tus saldos los
  ves en el dashboard.", con `response_kind = 'fixed_text'`.
- **Test:** `tests/integration/test_registration.py::test_a_query_gets_the_fixed_text`

#### C1-11 · Un consejo recibe el texto fijo

- **Sale de:** CA-17 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "¿me conviene sacar un préstamo?", y el modelo responde que es
  un consejo,
- **cuando** se procesa,
- **entonces** el modelo recibió una sola llamada y la respuesta es el mismo texto de C1-10, con
  `response_kind = 'fixed_text'`.
- **Test:** `tests/unit/test_answer_message.py::test_an_advice_gets_the_fixed_text`

#### C1-12 · Un saludo recibe el pedido de aclaración

- **Sale de:** CA-18 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "hola", pendiente, y el modelo responde que no es de ninguna
  clase,
- **cuando** el worker hace una ronda,
- **entonces** no se registra nada, el mensaje queda `processed`, y la respuesta es "¡Hola! Soy
  Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué cobraste, y con qué
  cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago».", con `response_kind = 'fixed_text'`.
- **Test:** `tests/integration/test_registration.py::test_a_greeting_gets_the_request_for_details`

#### C1-13 · La clasificación deja su fila en `LLM_CALL`

- **Sale de:** CA-3 · **Tipo:** integración
- **Dado** el mensaje de C1-01, pendiente, y un adaptador doble envuelto por el envoltorio de
  registro, que responde la interpretación de C1-01 con 812 tokens de entrada y 64 de salida,
- **cuando** el worker hace una ronda,
- **entonces** `LLM_CALL` tiene una sola fila, con el `inbound_message_id` de ese mensaje,
  `purpose = 'classification'`, `provider = 'openai'`, `model = 'gpt-5.4-mini'`, la versión del
  prompt informada, `input_tokens = 812`, `output_tokens = 64`, `duration_ms` mayor o igual a 0,
  `estimated_cost_usd = 0.000897`, que es 812 × 0,75 / 1.000.000 + 64 × 4,50 / 1.000.000, y
  `outcome = 'ok'`; y ninguna de sus columnas tiene el texto, el monto ni el nombre de una
  cuenta.
- **Test:** `tests/integration/test_registration.py::test_the_classification_leaves_its_row_in_llm_call`

#### C1-14 · El adaptador pide al modelo configurado una salida estructurada

- **Sale de:** CA-1 y CA-2 · **Tipo:** unitario
- **Dado** el adaptador de OpenAI con un transporte HTTP doble, y un pedido de clasificación con
  el texto "gasté 3500 en el súper con Mercado Pago", las cuatro cuentas de Lucía, sus
  categorías de gasto y de ingreso, y el día 2026-10-17,
- **cuando** el adaptador clasifica,
- **entonces** el transporte recibió un solo pedido, con el modelo `gpt-5.4-mini`, esfuerzo de
  razonamiento bajo y un esquema de salida estructurada; el texto, los nombres de las cuentas y
  de las categorías y el día van en el mensaje del usuario, delimitados como datos; y el prompt
  de sistema no contiene ninguno de ellos.
- **Test:** `tests/unit/test_openai_llm.py::test_the_adapter_asks_the_configured_model_for_a_structured_output`

#### C1-15 · El adaptador devuelve el monto como `Decimal`

- **Sale de:** CA-4 · **Tipo:** unitario
- **Dado** el adaptador de OpenAI con un transporte HTTP doble que responde un registro de tipo
  gasto con monto "3500.50",
- **cuando** el adaptador clasifica,
- **entonces** la interpretación que devuelve tiene el monto `Decimal("3500.50")`, que no es un
  `float`.
- **Test:** `tests/unit/test_openai_llm.py::test_the_adapter_returns_the_amount_as_a_decimal`

#### C1-16 · Escribir un gasto en el chat y ver la confirmación

- **Sale de:** CA-5 y CA-12 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta y el chat web encendido, y el modelo responde la
  interpretación de C1-01,
- **cuando** Lucía envía "gasté 3500 en el súper con Mercado Pago" por `POST /chat/messages`,
  el worker hace una ronda y Lucía pide `GET /chat/messages`,
- **entonces** la conversación trae su mensaje y, después, la respuesta de Platita con el texto
  de C1-03.
- **Test:** `tests/integration/test_registration.py::test_write_an_expense_in_the_chat_and_see_the_confirmation`

#### C1-17 · Una cuenta que el mensaje no escribe no se usa

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pagué 26 mil a la muni por transferencia", y el modelo responde
  un gasto de 26000, con cuenta "Galicia pesos", categoría "Impuestos y trámites" y sin moneda,
- **cuando** se procesa,
- **entonces** no se registra ningún movimiento, y la respuesta es "Eso todavía no lo sé anotar.
  Por ahora me manejo con gastos e ingresos.", con `response_kind = 'fixed_text'`.
- **Test:** `tests/unit/test_answer_message.py::test_an_account_the_message_does_not_write_is_not_used`

#### C1-18 · Un nombre a medias sin moneda no elige entre dos cuentas

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "gasté 2000 en la verdulería con galicia", y el modelo responde
  un gasto de 2000, con cuenta "galicia", categoría "Supermercado" y sin moneda,
- **cuando** se procesa,
- **entonces** no se registra ningún movimiento: "galicia" nombra a Galicia pesos y a Galicia
  USD.
- **Test:** `tests/unit/test_answer_message.py::test_half_a_name_without_a_currency_does_not_choose_between_two_accounts`

#### C1-19 · Un nombre a medias con la moneda dicha elige la cuenta

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "gasté 2000 mangos en la verdulería con galicia", y el modelo
  responde un gasto de 2000, con cuenta "galicia", categoría "Supermercado" y moneda ARS,
- **cuando** se procesa,
- **entonces** el movimiento queda en Galicia pesos, y la confirmación empieza con "¡Listo!
  Anoté un gasto de $2.000 en Galicia pesos.".
- **Test:** `tests/unit/test_answer_message.py::test_half_a_name_with_the_currency_said_chooses_the_account`

#### C1-20 · Las iniciales nombran una cuenta

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pagué 3500 en el súper con MP", y el modelo responde un gasto
  de 3500, con cuenta "MP", categoría "Supermercado" y sin moneda,
- **cuando** se procesa,
- **entonces** el movimiento queda en Mercado Pago.
- **Test:** `tests/unit/test_answer_message.py::test_the_initials_name_an_account`

#### C1-21 · El tipo y la moneda nombran una cuenta

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "gasté 5 mil pesos en la carnicería con el banco", y el modelo
  responde un gasto de 5000, con cuenta "el banco", categoría "Supermercado" y moneda ARS,
- **cuando** se procesa,
- **entonces** el movimiento queda en Galicia pesos, la única cuenta de banco en pesos.
- **Test:** `tests/unit/test_answer_message.py::test_the_type_and_the_currency_name_an_account`

#### C1-22 · El tipo sin moneda no elige entre dos cuentas

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "gasté 5 mil en la carnicería con el banco", y el modelo responde
  un gasto de 5000, con cuenta "el banco", categoría "Supermercado" y sin moneda,
- **cuando** se procesa,
- **entonces** no se registra ningún movimiento: Lucía tiene dos cuentas de banco.
- **Test:** `tests/unit/test_answer_message.py::test_the_type_without_a_currency_does_not_choose_between_two_accounts`

#### C1-23 · El adaptador devuelve la moneda que dice el mensaje

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** el adaptador de OpenAI con un transporte HTTP doble que responde un registro de tipo
  gasto con cuenta "galicia" y moneda "ARS",
- **cuando** el adaptador clasifica,
- **entonces** la interpretación que devuelve tiene la cuenta "galicia" y la moneda "ARS", y el
  esquema de salida estructurada que se envió pide la moneda, que puede ser ARS, USD o nula.
- **Test:** `tests/unit/test_openai_llm.py::test_the_adapter_returns_the_currency_the_message_says`

#### C1-24 · Un gasto anterior al alta de su cuenta explica por qué no se anota

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** Lucía con Mercado Pago dada de alta el 13/10/2026, un mensaje suyo, "el lunes cargué
  nafta, 25 lucas, con MP", y el modelo responde un gasto de 25000, con cuenta "MP", categoría
  "Transporte", moneda ARS y fecha 2026-10-12,
- **cuando** se procesa,
- **entonces** no se registra ningún movimiento, y la respuesta es "Mercado Pago la tenés
  cargada desde el 13/10/2026, así que lo que gastaste antes ya está en el saldo con el que la
  diste de alta. Lo dejo sin anotar para no contarlo dos veces.", con
  `response_kind = 'fixed_text'`.
- **Test:** `tests/unit/test_answer_message.py::test_an_expense_before_its_account_was_opened_says_why_it_is_not_registered`

#### C1-25 · El nombre de otra cuenta fuera de la mención no cambia la cuenta

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** un mensaje de Lucía, "pagué 3500 en el súper con MP porque no tenía efectivo", y el
  modelo responde un gasto de 3500, con cuenta "MP", categoría "Supermercado" y sin moneda,
- **cuando** se procesa,
- **entonces** el movimiento queda en Mercado Pago, y no en Efectivo, aunque "efectivo" es el
  nombre completo de una cuenta y está en el mensaje.
- **Test:** `tests/unit/test_answer_message.py::test_the_name_of_another_account_outside_the_mention_does_not_change_the_account`

### Corte 2 — errores y lo que exige confirmación

- **Aprobado por:** pendiente

Los casos se escriben antes de empezar el corte, con las preguntas abiertas ya resueltas.

### Corte 3 — límites y observabilidad

- **Aprobado por:** pendiente

## Mensajes al usuario

Van en `backend/app/messages.py`, en español rioplatense, como habla alguien de acá: con voseo
("contame", "mandá"), vocabulario local ("el súper", "anoté"), cálidos y cortos. Sin lunfardo que
no se entienda en todo el país y sin emojis, para que el detalle de la confirmación se lea
igual en el chat web y en WhatsApp.

La confirmación de un movimiento registrado, con los valores que se asumieron:

> ¡Listo! Anoté un gasto de $3.500 en Mercado Pago.
> Fecha: 17/10/2026
> Moneda: ARS
> Categoría: Supermercado
> Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026

El monto va con punto de miles y, si tiene centavos, con coma: $3.500, $3.500,50. Las fechas,
como día/mes/año.

Los textos fijos de lo que el asistente todavía no sabe hacer, los mismos de la
[hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-2). Para un registro que no es un
gasto ni un ingreso:

> Eso todavía no lo sé anotar. Por ahora me manejo con gastos e ingresos.

Para una consulta o un consejo:

> Todavía no sé responder preguntas. Por ahora anoto gastos e ingresos, y tus saldos los ves en
> el dashboard.

Un gasto o un ingreso anterior al alta de su cuenta, con el nombre de la cuenta y el día de su
alta:

> Mercado Pago la tenés cargada desde el 13/10/2026, así que lo que gastaste antes ya está en el
> saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo dos veces.

En un ingreso dice "lo que cobraste antes" en vez de "lo que gastaste antes".

La respuesta a un mensaje que no es de ninguna clase. Sirve igual para un saludo y para algo
que no se entiende, así la clasificación no necesita una clase más:

> ¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué cobraste, y con
> qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago».

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| Nunca una cuenta por defecto ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-01 registra solo con una cuenta nombrada; en el corte 2, el gasto sin cuenta |
| Con un solo período posible y confirmado, se imputa sin preguntar ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-01, C1-02 |
| Los defaults derivables son solo fecha, moneda y categoría, y se listan junto con el presupuesto ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-03, C1-04 |
| Hoy es el día en que el usuario escribió ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-06 |
| Montos en `Decimal`, nunca `float` | C1-15 |
| La moneda viaja con el monto, y sale de la cuenta ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-01, C1-02 |
| El saldo se calcula ([§ 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado)) | C1-05 |
| Una categoría nueva no se crea sin confirmación ([§ 4](../../reglas-de-dominio.md#4-categorías-catálogo-base-categorías-propias-y-creación-con-confirmación)) | En el corte 2 |
| Al proveedor no le llega ningún identificador ([ADR 0013](../../adr/0013-datos-minimos-al-proveedor-de-llm.md)) | C1-14, y en el corte 3 el test que falla si aparece uno |

## Sin cubrir

- Que el prompt real interprete bien los mensajes: ningún test llama al proveedor. Se comprueba
  a mano, con la clave en `.env`, escribiendo en el chat los mensajes de C1-01, C1-02, C1-07,
  C1-09, C1-10 y C1-12. Los casos que mini falló en la evaluación quedan como casos del prompt
  ([ADR 0025](../../adr/0025-gpt-5-4-mini-como-modelo-de-lenguaje.md), punto 9), pero pertenecen
  a las consultas, que no entran en la entrega 2.
- Que el proceso del worker arranque con el adaptador real: se comprueba a mano con
  `docker compose up`. El test de que el worker usa siempre el envoltorio va en el corte 3.

## Fuera de alcance

- Varios movimientos en un mensaje, elegir entre el presupuesto individual y el de un grupo, y
  corregir, borrar o restaurar: entrega final
  ([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-2)). Qué responde el asistente
  ante cada uno es la pregunta abierta 2.
- Un gasto en otra moneda, transferencias, compras con tarjeta, reglas recurrentes, reintegros
  y el aviso de duplicado entre miembros: reciben el texto fijo de C1-09.
- Las consultas y los consejos: reciben el texto fijo de C1-10.
- La descripción del movimiento: queda nula. Ninguna pantalla de la entrega 2 la muestra.
- El webhook de WhatsApp.

## Preguntas abiertas

1. **Qué recibe el usuario si el modelo se niega a responder** o el proveedor corta la
   respuesta ([hoja de ruta](../../hoja-de-ruta.md#decisiones-abiertas)). Corte 2.
2. **Qué responde el asistente ante lo que pasó a la entrega final:** varios movimientos en un
   mensaje, un usuario con un período individual y uno de grupo para la misma fecha, y una
   respuesta que cita una confirmación ([hoja de ruta](../../hoja-de-ruta.md#decisiones-abiertas)).
   Corte 2.
3. **Qué responde ante un gasto en una cuenta o en una moneda distinta de la del período,**
   como "gasté 20 dólares con la Galicia USD": la multimoneda no entra en la entrega 2, y
   registrarlo exige confirmar una cotización. Corte 2.
