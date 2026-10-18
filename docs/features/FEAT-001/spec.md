# Especificación — FEAT-001 · Pantalla de cuentas

- **Historia de usuario:** [HU1](../../05-historias-de-usuario.md)
- **Estado:** aprobada para el corte 1. Los casos de los cortes 2 y 3 están en borrador
- **Fecha:** 2026-10-13

## Alcance

Entra `GET /accounts`, con el saldo calculado de cada cuenta del usuario de la sesión, y la
pantalla del dashboard que las lista. Es la parte de la HU1 que entra en la entrega 2
([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-2)): la pantalla donde se ve el
efecto de cada movimiento.

No entra dar de alta ni editar una cuenta. Las cuentas que se ven son las de los datos de
prueba, y el alta conversacional queda para la entrega final.

## Reglas de dominio que aplican

- [§ 2 — Cuentas y saldo calculado](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado)
- [§ 6 — Multimoneda](../../reglas-de-dominio.md), en lo que hace al monto que se mueve en la
  cuenta cuando el movimiento está en otra moneda.
- [§ 13 — Tarjetas de crédito y transferencias](../../reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias),
  en lo que una transferencia suma y resta al saldo.

## Criterios de aceptación

Cada criterio es una regla, en una frase. Los casos que la comprueban están más abajo, en
[Casos de prueba](#casos-de-prueba), y cada caso dice de qué criterio sale.

### Qué se ve de cada cuenta

La pantalla lista las cuentas del usuario, agrupadas por moneda, y las de inversión aparte.

- **CA-1.** Quien entró al dashboard ve, en la pantalla de cuentas, cada una de sus cuentas con su nombre, su tipo, su moneda y su saldo, salvo las cuentas "Me deben" (CA-15).
- **CA-6.** Una cuenta de inversión se ve aparte de las demás, con lo aportado neto en lugar de un saldo.
- **CA-9.** Las cuentas se ven agrupadas por moneda.
- **CA-12.** Primero va el grupo de la moneda primaria del usuario y después los demás, por código de moneda. Dentro de cada grupo las cuentas van por nombre, sin distinguir mayúsculas.
- **CA-13.** Quien entra por la entrada de desarrollo ve primero la pantalla de cuentas, sin pasar por un menú.
- **CA-15.** Una cuenta "Me deben" no aparece en la lista de cuentas, porque esa plata la tiene otra persona ([reglas de dominio § 16](../../reglas-de-dominio.md#16-reintegros-devoluciones-y-plata-que-te-deben)). La API la manda, marcada por su tipo, y la pantalla no la lista. Su sección propia llega en la entrega final.

### El saldo se calcula

El saldo de una cuenta sale de su saldo inicial y de lo que ya ocurrió en ella; nunca es un valor guardado.

- **CA-2.** El saldo de una cuenta es su saldo inicial, más sus ingresos, menos sus gastos, más las transferencias que recibió y menos las que envió.
- **CA-3.** Un movimiento o una transferencia con fecha posterior a hoy, en la zona horaria del usuario, todavía no cuenta.
- **CA-4.** Un movimiento borrado o marcado como duplicado no cuenta, y una transferencia borrada tampoco.
- **CA-5.** Un movimiento en otra moneda que la de su cuenta cuenta por su monto convertido con su propia cotización, redondeado a dos decimales antes de sumar.

### Cada uno ve solo lo suyo

Las cuentas y los saldos que se muestran son los del usuario de la sesión.

- **CA-7.** Cada usuario ve solo sus cuentas, y ningún movimiento de otro usuario cambia sus saldos.
- **CA-8.** Sin una sesión válida no se ve ninguna cuenta: se muestra la entrada.

### Sin cuentas y con una consulta que falla

No tener cuentas y que la consulta falle son dos situaciones distintas, y la pantalla las distingue.

- **CA-10.** Un usuario sin cuentas ve que no tiene ninguna y qué hacer, sin un mensaje de error.
- **CA-11.** Si la consulta falla, no se ve ningún saldo: se ve qué pasó y se puede reintentar.

### Lo que queda en los registros

Un pedido deja su línea en los registros sin datos del usuario ([ADR 0023](../../adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md)).

- **CA-14.** La línea de un pedido dice a qué endpoint fue, y ninguna línea lleva un saldo, el nombre de una cuenta ni el nombre del usuario.

## Casos de prueba

Cada caso es un ejemplo concreto de un criterio, y se entiende solo, sin leer los demás:
**Dado** es el estado inicial completo, **cuando** es una sola acción y **entonces** es el
estado final, con la cuenta escrita para revisarla a mano.

- En un caso **unitario** la acción es calcular el saldo, con los datos armados en memoria, sin
  base de datos.
- En un caso de **integración** los datos están guardados en PostgreSQL y la acción es un
  pedido a `GET /accounts` ([la API](../../04-api.md)), que es lo que la pantalla consulta.
- Los casos de **componente**, los de los estados de la pantalla, se suman cuando la pantalla
  esté armada.

Salvo que el caso diga otra cosa, el usuario es de Buenos Aires, su moneda primaria es ARS, y
las cuentas se dieron de alta el 1 de octubre de 2026.

### Corte 1 — camino feliz

- **Aprobado por:** Verónica Zacarías 14/10/2026
- **C1-22 y C1-23, sumados después de la aprobación:** Verónica Zacarías 14/10/2026
- **C1-24, sumado después:** Verónica Zacarías 14/10/2026
- **C1-25 a C1-31, de componente, sumados con la pantalla armada:** Verónica Zacarías 14/10/2026
- **Total:** 31 casos, 17 unitarios, 7 de integración y 7 de componente.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Una cuenta sin movimientos | Unitario | CA-2 |
| C1-02 | Un gasto y un ingreso | Unitario | CA-2 |
| C1-03 | Una transferencia recibida y una enviada | Unitario | CA-2 |
| C1-04 | Un gasto con fecha de mañana no cuenta | Unitario | CA-3 |
| C1-05 | "Hoy" es el día del usuario, no el del servidor | Unitario | CA-3 |
| C1-21 | El mismo gasto cuenta cuando llega su día para el usuario | Unitario | CA-3 |
| C1-06 | Una transferencia con fecha de mañana no cuenta | Unitario | CA-3 |
| C1-07 | Un gasto borrado no cuenta | Unitario | CA-4 |
| C1-08 | Un gasto duplicado cuenta una sola vez | Unitario | CA-4 |
| C1-09 | Una transferencia borrada no cuenta | Unitario | CA-4 |
| C1-10 | Un gasto en dólares sobre una cuenta en pesos | Unitario | CA-5 |
| C1-11 | Cada movimiento se redondea antes de sumar | Unitario | CA-5 |
| C1-12 | Una cuenta de inversión dice que su número es lo aportado | Unitario | CA-6 |
| C1-13 | Lo aportado neto puede ser negativo | Unitario | CA-6 |
| C1-20 | Lo declarado al dar de alta cuenta como aportado | Unitario | CA-6 |
| C1-14 | Lucía ve sus cuatro cuentas | Integración | CA-1 |
| C1-15 | Un gasto guardado baja el saldo de su cuenta y de ninguna otra | Integración | CA-2 |
| C1-16 | La consulta a la base aplica las mismas reglas que el cálculo | Integración | CA-2, CA-3 y CA-4 |
| C1-17 | El monto llega con sus dígitos exactos | Integración | CA-2 |
| C1-18 | Las cuentas de Lucía vienen ordenadas | Integración | CA-12 |
| C1-19 | El orden con otra moneda primaria y con minúsculas | Integración | CA-12 |
| C1-22 | Una compra de dólares entre cuentas propias | Unitario | CA-2 |
| C1-23 | La cuenta "Me deben" viene marcada por su tipo | Integración | CA-15 |
| C1-24 | Una tarjeta con gastos vencidos sin pagar queda en negativo | Unitario | CA-2 |
| C1-25 | Mientras se consulta, lo dice y no muestra saldos | Componente | CA-1 |
| C1-26 | Las cuentas de Lucía, agrupadas por moneda y en orden | Componente | CA-1, CA-9 y CA-12 |
| C1-27 | Una cuenta de inversión va aparte, con lo aportado neto | Componente | CA-6 |
| C1-28 | Una cuenta "Me deben" no aparece | Componente | CA-15 |
| C1-29 | Un saldo negativo se ve con su signo | Componente | CA-2 |
| C1-30 | Un saldo se muestra tal como llega, sin cuentas propias | Componente | CA-2 |
| C1-31 | Al entrar, lo primero que se ve son las cuentas | Componente | CA-13 |

#### C1-01 · Una cuenta sin movimientos

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, sin movimientos
  ni transferencias, y hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $350.000,00: el saldo inicial, sin cambios.
- **Test:** `tests/unit/test_list_accounts.py::test_an_account_without_movements_keeps_its_initial_balance`

#### C1-02 · Un gasto y un ingreso

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con un gasto de
  $3.500,00 del 15 de octubre y un ingreso de $10.000,00 del 15 de octubre, los dos en ARS, y
  hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $356.500,00: 350.000 − 3.500 + 10.000.
- **Test:** `tests/unit/test_list_accounts.py::test_an_expense_subtracts_and_an_income_adds`

#### C1-03 · Una transferencia recibida y una enviada

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, que recibió una
  transferencia de $20.000,00 desde "Mercado Pago" el 10 de octubre y envió una de $5.000,00 a
  "Efectivo" el 12 de octubre, sin gastos ni ingresos, y hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $365.000,00: 350.000 + 20.000 − 5.000.
- **Test:** `tests/unit/test_list_accounts.py::test_a_received_transfer_adds_and_a_sent_one_subtracts`

#### C1-04 · Un gasto con fecha de mañana no cuenta

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con un gasto de
  $3.500,00 del 15 de octubre y otro de $9.000,00 del 16 de octubre, y hoy es 15 de octubre de
  2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $346.500,00: 350.000 − 3.500. El gasto del 16 no cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_an_expense_dated_tomorrow_does_not_count`

#### C1-05 · "Hoy" es el día del usuario, no el del servidor

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** un usuario de Buenos Aires con la cuenta "Galicia pesos", en ARS, con saldo inicial
  de $350.000,00 y un gasto de $3.500,00 con fecha 15 de octubre, y el reloj marca 15 de
  octubre de 2026 a la 01:00 UTC, que en Buenos Aires es 14 de octubre a las 22:00,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $350.000,00: para el usuario todavía es 14, y el gasto del 15 no
  cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_today_is_the_day_of_the_user_not_of_the_server`

#### C1-21 · El mismo gasto cuenta cuando llega su día para el usuario

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** el mismo usuario, la misma cuenta y el mismo gasto de $3.500,00 con fecha 15 de
  octubre del caso C1-05, y el reloj marca 15 de octubre de 2026 a las 03:00 UTC, que en
  Buenos Aires es 15 de octubre a las 00:00,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $346.500,00: 350.000 − 3.500. Para el usuario ya es 15.
- **Test:** `tests/unit/test_list_accounts.py::test_the_same_expense_counts_once_its_day_arrives_for_the_user`

#### C1-06 · Una transferencia con fecha de mañana no cuenta

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, que recibe una
  transferencia de $20.000,00 desde "Mercado Pago" con fecha 16 de octubre, sin nada más, y hoy
  es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $350.000,00: la transferencia del 16 no cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_a_transfer_dated_tomorrow_does_not_count`

#### C1-07 · Un gasto borrado no cuenta

- **Sale de:** CA-4 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con un solo
  gasto de $3.500,00 del 10 de octubre, que el usuario borró el 12 de octubre, y hoy es 15 de
  octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $350.000,00: el gasto borrado no cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_a_deleted_expense_does_not_count`

#### C1-08 · Un gasto duplicado cuenta una sola vez

- **Sale de:** CA-4 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con dos gastos
  de $3.500,00 del 10 de octubre, el segundo marcado como duplicado del primero, y hoy es 15 de
  octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $346.500,00: 350.000 − 3.500. El duplicado no cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_a_duplicated_expense_counts_once`

#### C1-09 · Una transferencia borrada no cuenta

- **Sale de:** CA-4 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, que envió una
  transferencia de $5.000,00 a "Efectivo" el 12 de octubre, que el usuario borró después, sin
  nada más, y hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $350.000,00: la transferencia borrada no cuenta.
- **Test:** `tests/unit/test_list_accounts.py::test_a_deleted_transfer_does_not_count`

#### C1-10 · Un gasto en dólares sobre una cuenta en pesos

- **Sale de:** CA-5 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con un gasto de
  50,00 USD del 10 de octubre con cotización de 1.000 pesos por dólar, y hoy es 15 de octubre
  de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $300.000,00: el gasto pesa 50 × 1.000 = 50.000 pesos, y
  350.000 − 50.000.
- **Test:** `tests/unit/test_list_accounts.py::test_an_expense_in_dollars_on_an_account_in_pesos_counts_converted`

#### C1-11 · Cada movimiento se redondea antes de sumar

- **Sale de:** CA-5 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, con dos gastos
  de 0,01 USD del 10 de octubre, cada uno con cotización de 1.234,5 pesos por dólar, y hoy es
  15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es $349.975,30. Cada gasto pesa 0,01 × 1.234,5 = 12,345, que se
  redondea a $12,35; los dos suman $24,70, y 350.000 − 24,70. Si se sumara antes de redondear
  daría $24,69, un centavo menos.
- **Test:** `tests/unit/test_list_accounts.py::test_each_movement_is_rounded_before_adding`

#### C1-12 · Una cuenta de inversión dice que su número es lo aportado

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** un usuario con dos cuentas sin movimientos: "Galicia pesos", de tipo banco, en ARS,
  con saldo inicial de $350.000,00, y "Balanz USD", de tipo inversión, en USD, con saldo
  inicial de 0,00,
- **cuando** se listan sus cuentas,
- **entonces** "Galicia pesos" viene con `balance_kind` igual a `balance`, y "Balanz USD" con
  `balance_kind` igual a `net_contributed`.
- **Test:** `tests/unit/test_list_accounts.py::test_an_investment_account_says_its_number_is_the_net_contributed`

#### C1-13 · Lo aportado neto puede ser negativo

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** la cuenta "Balanz USD", de tipo inversión, en USD, dada de alta con 0,00, que
  recibió una transferencia de 1.000,00 USD el 5 de octubre y envió una de 1.200,00 USD el 10
  de octubre, y hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** lo aportado neto es −200,00 USD: 0 + 1.000 − 1.200.
- **Test:** `tests/unit/test_list_accounts.py::test_the_net_contributed_can_be_negative`

#### C1-20 · Lo declarado al dar de alta cuenta como aportado

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** la cuenta "Balanz USD", de tipo inversión, en USD, dada de alta con 3.000,00 USD
  declarados, que recibió una transferencia de 1.000,00 USD el 5 de octubre, sin nada más, y
  hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** lo aportado neto es 4.000,00 USD: 3.000 + 1.000.
- **Test:** `tests/unit/test_list_accounts.py::test_what_was_declared_on_opening_counts_as_contributed`

#### C1-14 · Lucía ve sus cuatro cuentas

- **Sale de:** CA-1 · **Tipo:** integración
- **Dado** la base con los datos de prueba recién creados, donde Lucía tiene cuatro cuentas sin
  ningún movimiento ni transferencia: "Galicia pesos", banco, ARS, saldo inicial $350.000,00;
  "Mercado Pago", billetera, ARS, $80.000,00; "Efectivo", efectivo, ARS, $25.000,00; y "Galicia
  USD", banco, USD, 500,00; y Lucía tiene una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** responde `200` con exactamente esas cuatro cuentas, cada una con su `id`, su
  `name`, su `type`, su `currency`, `balance_kind` igual a `balance`, y `balance` igual a su
  saldo inicial: 350000.00, 80000.00, 25000.00 y 500.00.
- **Test:** `tests/integration/test_accounts.py::test_lucia_sees_her_four_accounts`

#### C1-15 · Un gasto guardado baja el saldo de su cuenta y de ninguna otra

- **Sale de:** CA-2 · **Tipo:** integración
- **Dado** los datos de prueba del caso C1-14, más un gasto de Lucía de $3.500,00 en ARS, con
  fecha de hoy, sobre "Galicia pesos", guardado en la base; y Lucía tiene una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** "Galicia pesos" viene con 346500.00, que es 350.000 − 3.500, y las otras tres
  siguen igual: "Mercado Pago" 80000.00, "Efectivo" 25000.00 y "Galicia USD" 500.00.
- **Test:** `tests/integration/test_accounts.py::test_a_stored_expense_lowers_its_account_and_no_other`

#### C1-16 · La consulta a la base aplica las mismas reglas que el cálculo

- **Sale de:** CA-2, CA-3 y CA-4 · **Tipo:** integración
- **Dado** los datos de prueba del caso C1-14, con "Galicia pesos" en $350.000,00 y "Mercado
  Pago" en $80.000,00, más estos registros de Lucía guardados en la base, todos en ARS y sobre
  "Galicia pesos": un ingreso de $10.000,00 de hoy; un gasto de $2.000,00 de hoy, borrado; un
  gasto de $1.500,00 de hoy y otro igual marcado como su duplicado; un gasto de $9.000,00 con
  fecha de mañana; y una transferencia de $5.000,00 de hoy hacia "Mercado Pago"; y Lucía tiene
  una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** "Galicia pesos" viene con 353500.00, que es 350.000 + 10.000 − 1.500 − 5.000, y
  "Mercado Pago" con 85000.00, que es 80.000 + 5.000. No cuentan el gasto borrado, el
  duplicado ni el de mañana.
- **Test:** `tests/integration/test_accounts.py::test_the_query_to_the_database_applies_the_same_rules_as_the_calculation`

#### C1-17 · El monto llega con sus dígitos exactos

- **Sale de:** CA-2 · **Tipo:** integración
- **Dado** un usuario de prueba con una sola cuenta, "Caja chica", en ARS, con saldo inicial de
  $0,10, y un ingreso de $0,20 de hoy guardado en la base; y ese usuario tiene una sesión
  abierta,
- **cuando** pide `GET /accounts`,
- **entonces** el texto de la respuesta trae `"balance": 0.30`, que es 0,10 + 0,20, con sus dos
  decimales. No trae `0.3` ni `0.30000000000000004`: el monto no pasó por punto flotante.
- **Test:** `tests/integration/test_accounts.py::test_the_amount_arrives_with_its_exact_digits`

#### C1-18 · Las cuentas de Lucía vienen ordenadas

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** los datos de prueba del caso C1-14, donde la moneda primaria de Lucía es ARS, y
  Lucía tiene una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** las cuentas vienen en este orden: "Efectivo", "Galicia pesos", "Mercado Pago" y
  "Galicia USD". Primero las tres en pesos, por nombre, y después la que está en dólares.
- **Test:** `tests/integration/test_accounts.py::test_the_accounts_of_lucia_come_in_order`

#### C1-19 · El orden con otra moneda primaria y con minúsculas

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** un usuario de prueba con moneda primaria USD y cuatro cuentas sin movimientos,
  guardadas en este orden: "Caja" en EUR, "banco" en ARS, "Wise" en USD y "Ahorro" en ARS; y
  ese usuario tiene una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** las cuentas vienen en este orden: "Wise", "Ahorro", "banco" y "Caja". Primero la
  de su moneda primaria, después ARS y EUR por código de moneda, y "banco" va después de
  "Ahorro" aunque empiece con minúscula.
- **Test:** `tests/integration/test_accounts.py::test_the_order_with_another_primary_currency_and_lowercase_names`

#### C1-22 · Una compra de dólares entre cuentas propias

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** "Galicia pesos", en ARS, con saldo inicial de $350.000,00, y "Galicia USD", en USD,
  con saldo inicial de 500,00, sin movimientos; y una transferencia del 10 de octubre que sale
  de "Galicia pesos" por $120.000,00 y entra en "Galicia USD" por 100,00 USD, que es una compra
  de dólares desde el home banking; y hoy es 15 de octubre de 2026,
- **cuando** se calcula el saldo de las dos cuentas,
- **entonces** "Galicia pesos" queda en $230.000,00, que es 350.000 − 120.000, y "Galicia USD"
  en 600,00 USD, que es 500 + 100. Cada lado cuenta en la moneda de su cuenta, sin convertir.
- **Test:** `tests/unit/test_list_accounts.py::test_buying_dollars_between_own_accounts_counts_each_side_in_its_currency`

#### C1-23 · La cuenta "Me deben" viene marcada por su tipo

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** los datos de prueba del caso C1-14, más una cuenta de Lucía "Me debe Juan", de tipo
  "Me deben", en ARS, con saldo inicial de $0,00, que recibió una transferencia de $30.000,00
  desde "Mercado Pago" el 10 de octubre; y Lucía tiene una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** la respuesta trae "Me debe Juan" con `type` igual a `receivable` y `balance`
  igual a 30000.00, que es 0 + 30.000, y "Mercado Pago" con 50000.00, que es 80.000 − 30.000.
  La pantalla usa el tipo para dejarla afuera de la lista.
- **Test:** `tests/integration/test_accounts.py::test_an_account_others_owe_comes_marked_by_its_type`

#### C1-24 · Una tarjeta con gastos vencidos sin pagar queda en negativo

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** la cuenta "Visa", de tipo tarjeta de crédito, en ARS, dada de alta con saldo inicial
  de $0,00, con un gasto de $50.000,00 con fecha 5 de octubre, que es la del vencimiento de su
  resumen, sin pagos, y hoy es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el saldo es −$50.000,00, que es 0 − 50.000: la misma fórmula que cualquier
  cuenta, sin dar vuelta el signo por ser tarjeta.
- **Test:** `tests/unit/test_list_accounts.py::test_a_card_with_unpaid_expenses_already_due_is_negative`

#### C1-25 · Mientras se consulta, lo dice y no muestra saldos

- **Sale de:** CA-1 · **Tipo:** componente
- **Dado** una respuesta de `GET /accounts` que todavía no llegó,
- **cuando** se abre la pantalla,
- **entonces** dice "Consultando tus cuentas…" y no muestra ninguna cuenta ni ningún saldo.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-25: while the accounts are being asked for, it says so and shows no balance"

#### C1-26 · Las cuentas de Lucía, agrupadas por moneda y en orden

- **Sale de:** CA-1, CA-9 y CA-12 · **Tipo:** componente
- **Dado** una respuesta de `GET /accounts` simulada con las cuentas de Lucía, en este orden: "Efectivo", efectivo, ARS, 25000.00; "Galicia pesos", banco, ARS, 350000.00; "Mercado Pago", billetera, ARS, 80000.00; y "Galicia USD", banco, USD, 500.00, todas con `balance_kind` igual a `balance`,
- **cuando** se abre la pantalla,
- **entonces** muestra el grupo "Cuentas en ARS" con Efectivo $ 25.000,00, Galicia pesos $ 350.000,00 y Mercado Pago $ 80.000,00, en ese orden, y después el grupo "Cuentas en USD" con Galicia USD US$ 500,00. Cada cuenta dice su tipo: Efectivo, Banco, Billetera, Banco. No hay ningún total.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-26: the accounts of Lucía, grouped by currency, in order, with no total"

#### C1-27 · Una cuenta de inversión va aparte, con lo aportado neto

- **Sale de:** CA-6 · **Tipo:** componente
- **Dado** la respuesta del caso C1-26 más "Balanz USD", inversión, USD, 3100.00, con `balance_kind` igual a `net_contributed`,
- **cuando** se abre la pantalla,
- **entonces** "Balanz USD" aparece bajo "Inversiones", con "Aportado neto" en lugar del tipo y US$ 3.100,00, y no aparece en "Cuentas en USD".
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-27: an investment account goes apart, with the net contributed"

#### C1-28 · Una cuenta "Me deben" no aparece

- **Sale de:** CA-15 · **Tipo:** componente
- **Dado** la respuesta del caso C1-26 más "Me debe Juan", "Me deben", ARS, 30000.00,
- **cuando** se abre la pantalla,
- **entonces** "Me debe Juan" no aparece en ningún lugar de la pantalla, y las otras cuatro cuentas sí.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-28: an account others owe does not appear"

#### C1-29 · Un saldo negativo se ve con su signo

- **Sale de:** CA-2 · **Tipo:** componente
- **Dado** una respuesta con una sola cuenta, "Visa", tarjeta de crédito, ARS, -50000.00,
- **cuando** se abre la pantalla,
- **entonces** muestra Visa con −$ 50.000,00, con el estilo de un monto negativo.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-29: a negative balance is shown with its sign"

#### C1-30 · Un saldo se muestra tal como llega, sin cuentas propias

- **Sale de:** CA-2 · **Tipo:** componente
- **Dado** una respuesta con una sola cuenta, "Caja chica", efectivo, ARS, con `balance` escrito como `0.30`,
- **cuando** se abre la pantalla,
- **entonces** muestra Caja chica con $ 0,30.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C1-30: a balance is shown as it arrives, without sums of its own"

#### C1-31 · Al entrar, lo primero que se ve son las cuentas

- **Sale de:** CA-13 · **Tipo:** componente
- **Dado** el dashboard abierto sin sesión, con la entrada de desarrollo encendida y la respuesta de `GET /accounts` del caso C1-26,
- **cuando** se elige a Lucía en la entrada,
- **entonces** aparecen el menú y "Tus cuentas" con sus cuentas, "Cuentas" queda marcada como la
  pantalla actual, y la entrada deja de verse. El caso se reescribió el 14 de octubre de 2026,
  con la aprobación de Vero, cuando llegó el menú lateral
  ([ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md)): antes decía que las
  cuentas aparecían antes que el estado del sistema y que la entrada, en la misma página.
- **Test:** `src/App.test.tsx` › "case C1-31: choosing Lucía in the entry shows the menu and her accounts first"

### Corte 2 — errores y estado vacío

- **Aprobado por:** Veronica Zacarias 14/10/2026
- **Total:** 12 casos, 1 unitario, 6 de integración y 5 de componente.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C2-01 | Sin sesión no hay cuentas | Integración | CA-8 |
| C2-02 | Una sesión vencida vale lo mismo que ninguna | Integración | CA-8 |
| C2-03 | Lucía no ve las cuentas de Pablo | Integración | CA-7 |
| C2-04 | Un gasto de Pablo no cambia el saldo de Lucía | Integración | CA-7 |
| C2-05 | Un usuario sin cuentas | Integración | CA-10 |
| C2-06 | El usuario sale de la sesión, no del pedido | Integración | CA-7 |
| C2-07 | Sin cuentas, el estado vacío y no un error | Componente | CA-10 |
| C2-08 | Con solo cuentas "Me deben", también vacío | Componente | CA-10 y CA-15 |
| C2-09 | Un error por cada causa, sin ningún saldo | Componente | CA-11 |
| C2-10 | Reintentar después de un error trae las cuentas | Componente | CA-11 |
| C2-11 | Si la sesión venció, vuelve la entrada | Componente | CA-8 |
| C2-12 | Sin cotización, el saldo no se calcula | Unitario | CA-5 |

#### C2-01 · Sin sesión no hay cuentas

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** la base con los datos de prueba, donde Lucía tiene sus cuatro cuentas, y un pedido
  que no trae la cookie de sesión,
- **cuando** llega a `GET /accounts`,
- **entonces** responde `401` con `{"error": "unauthorized"}`, y la respuesta no trae ninguna
  cuenta.
- **Test:** `tests/integration/test_accounts.py::test_without_a_session_there_are_no_accounts`

#### C2-02 · Una sesión vencida vale lo mismo que ninguna

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** la base con los datos de prueba, y una sesión de Lucía creada hace 12 horas, que ya
  venció,
- **cuando** se pide `GET /accounts` con la cookie de esa sesión,
- **entonces** responde `401` con `{"error": "unauthorized"}`, y la respuesta no trae ninguna
  cuenta.
- **Test:** `tests/integration/test_accounts.py::test_an_expired_session_is_worth_the_same_as_none`

#### C2-03 · Lucía no ve las cuentas de Pablo

- **Sale de:** CA-7 · **Tipo:** integración
- **Dado** la base con los datos de prueba, donde Lucía y Pablo tienen cada uno sus cuatro
  cuentas con los mismos nombres, "Galicia pesos", "Mercado Pago", "Efectivo" y "Galicia USD";
  y Lucía tiene una sesión abierta,
- **cuando** Lucía pide `GET /accounts`,
- **entonces** responde `200` con cuatro cuentas, las cuatro de Lucía, y ninguno de los cuatro
  `id` de las cuentas de Pablo aparece en la respuesta.
- **Test:** `tests/integration/test_accounts.py::test_lucia_does_not_see_the_accounts_of_pablo`

#### C2-04 · Un gasto de Pablo no cambia el saldo de Lucía

- **Sale de:** CA-7 · **Tipo:** integración
- **Dado** los datos de prueba del caso C2-03, con la "Galicia pesos" de cada uno en
  $350.000,00, más un gasto de Pablo de $3.500,00 de hoy sobre su "Galicia pesos"; y Lucía
  tiene una sesión abierta,
- **cuando** Lucía pide `GET /accounts`,
- **entonces** su "Galicia pesos" viene con 350000.00, sin cambios.
- **Test:** `tests/integration/test_accounts.py::test_an_expense_of_pablo_does_not_change_the_balance_of_lucia`

#### C2-05 · Un usuario sin cuentas

- **Sale de:** CA-10 · **Tipo:** integración
- **Dado** un usuario de prueba que no tiene ninguna cuenta, con una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** responde `200` con `{"accounts": []}`. No es un error.
- **Test:** `tests/integration/test_accounts.py::test_a_user_without_accounts_gets_an_empty_list`

#### C2-06 · El usuario sale de la sesión, no del pedido

- **Sale de:** CA-7 · **Tipo:** integración
- **Dado** los datos de prueba del caso C2-03, y Lucía con una sesión abierta,
- **cuando** Lucía pide `GET /accounts?user_id=` seguido del `id` de Pablo,
- **entonces** responde `200` con las cuatro cuentas de Lucía y ninguna de Pablo: el parámetro
  no se lee.
- **Test:** `tests/integration/test_accounts.py::test_the_user_comes_from_the_session_not_from_the_request`

#### C2-07 · Sin cuentas, el estado vacío y no un error

- **Sale de:** CA-10 · **Tipo:** componente
- **Dado** una respuesta de `GET /accounts` con la lista vacía,
- **cuando** se abre la pantalla,
- **entonces** dice "Todavía no tenés cuentas" y "Las cuentas se dan de alta conversando con Platita.", sin alerta y sin botón de reintentar.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C2-07: without accounts it is empty, not an error"

#### C2-08 · Con solo cuentas "Me deben", también vacío

- **Sale de:** CA-10 y CA-15 · **Tipo:** componente
- **Dado** una respuesta con una sola cuenta, "Me debe Juan", "Me deben", ARS, 30000.00,
- **cuando** se abre la pantalla,
- **entonces** muestra el mismo estado vacío del caso C2-07, sin "Me debe Juan".
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C2-08: with only accounts others owe, it is empty too"

#### C2-09 · Un error por cada causa, sin ningún saldo

- **Sale de:** CA-11 · **Tipo:** componente
- **Dado** tres situaciones, una por vez: la API responde `500`; no se llega a la API; y la API no responde a tiempo,
- **cuando** se abre la pantalla,
- **entonces** en las tres muestra una alerta con "No se pudieron consultar tus cuentas" y su causa: "La API respondió con un error.", "No se puede llegar a la API." o "La API no respondió a tiempo.", con el botón Reintentar y sin ningún saldo.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C2-09: an error for each cause, with no balance: %s"

#### C2-10 · Reintentar después de un error trae las cuentas

- **Sale de:** CA-11 · **Tipo:** componente
- **Dado** la pantalla en el error del caso C2-09 por un `500`, y una API que ahora responde las cuentas del caso C1-26,
- **cuando** se aprieta Reintentar,
- **entonces** el foco pasa a la línea de estado, dice "Consultando tus cuentas…" y después muestra las cuentas, sin la alerta.
- **Test:** `src/pages/AccountsPage.test.tsx` › "case C2-10: retrying after an error brings the accounts"

#### C2-11 · Si la sesión venció, vuelve la entrada

- **Sale de:** CA-8 · **Tipo:** componente
- **Dado** Lucía adentro, con la pantalla de cuentas, y una API que ahora responde `401` a `GET /accounts`,
- **cuando** se vuelve a abrir la pantalla de cuentas,
- **entonces** la pantalla de cuentas desaparece, no queda ningún saldo a la vista, y la entrada vuelve a ofrecer los usuarios de prueba.
- **Test:** `src/App.test.tsx` › "case C2-11: when the session expired, the entry comes back"

#### C2-12 · Sin cotización, el saldo no se calcula

- **Sale de:** CA-5 · **Tipo:** unitario
- **Dado** la cuenta "Galicia pesos", en ARS, con saldo inicial de $350.000,00, y un gasto de
  50,00 USD del 10 de octubre que llegó sin cotización, un dato que la base hoy rechaza; y hoy
  es 15 de octubre de 2026,
- **cuando** se calcula su saldo,
- **entonces** el cálculo se detiene con un error y no devuelve ningún saldo. No suma los 50
  como si fueran pesos: el saldo nunca suma montos de monedas distintas
  ([reglas de dominio § 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado)).
- **Test:** `tests/unit/test_balance_without_rate.py::test_without_an_exchange_rate_the_balance_is_not_computed`

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** Veronica Zacarias 14/10/2026
- **Total:** 1 caso, de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C3-01 | Los registros no llevan saldos ni nombres | Integración | CA-14 |

#### C3-01 · Los registros no llevan saldos ni nombres

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** los datos de prueba del caso C1-14, y Lucía con una sesión abierta,
- **cuando** pide `GET /accounts`,
- **entonces** la línea de registro del pedido lleva `GET /accounts` como endpoint, y ninguna
  línea escrita durante el pedido contiene un saldo, el nombre de una cuenta ni "Lucía".
- **Test:** `tests/integration/test_accounts.py::test_the_logs_carry_no_balances_or_names`

## Estados de pantalla

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | Mientras `GET /accounts` no respondió | Un indicador de carga |
| Con contenido | La consulta trajo al menos una cuenta | Las cuentas agrupadas por moneda, con su saldo |
| Vacío | La consulta respondió sin cuentas | Que no hay cuentas y que se dan de alta conversando |
| Error | La consulta falló, no respondió a tiempo o no llegó | Qué pasó y un botón para reintentar |

Sin sesión no es un estado de esta pantalla: se muestra la entrada.

## Mensajes al usuario

No hay mensajes de WhatsApp. Los textos de la pantalla van en `frontend/src/messages.ts`.

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| El saldo se calcula, no se guarda ([§ 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado)) | C1-01 a C1-03, C1-15 |
| El saldo es lo que ya ocurrió, en la zona horaria del usuario | C1-04 a C1-06, C1-21 |
| Lo borrado y lo duplicado no cuentan | C1-07 a C1-09, C1-16 |
| El saldo nunca suma montos de monedas distintas | C1-10, C1-11, C1-22 |
| Un monto nunca es `float`, tampoco al responder | C1-17 |
| Lo aportado neto de una cuenta de inversión | C1-12, C1-13, C1-20 |
| Todo acceso se limita al usuario de la sesión | C2-03, C2-04, C2-06 |

## Sin cubrir

- Que los montos sean `Decimal` y no `float` dentro del backend: lo valida
  `scripts/verify_architecture.py`.
- Los totales por moneda: quedaron fuera de alcance.

## Fuera de alcance

- Dar de alta, editar o borrar una cuenta.
- La deuda y el ingreso previstos, que son los movimientos con fecha futura y se muestran
  aparte del saldo.
- El contraste mensual del saldo.
- Los totales por moneda.
- La sección "Me deben", con cada persona y su saldo: llega en la entrega final, con los préstamos, que son los que crean esas cuentas.

## Decisiones tomadas al especificar

Las preguntas que se abrieron al escribir este documento, ya resueltas.

1. ~~Cómo viaja un monto en el JSON.~~ Resuelta el 13 de octubre de 2026: como número, igual
   que en el ejemplo de [la API](../../04-api.md), escrito con sus dígitos exactos. El dashboard
   no hace cuentas con él
   ([convenciones de desarrollo](../../convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla)).
   Límite conocido: el navegador lee el número como punto flotante, que muestra exactos los
   montos con dos decimales hasta unos 90 billones. La base admite más, `NUMERIC(20,2)`. Para
   los saldos de una persona no se llega; si alguna vez hiciera falta, el monto pasaría a
   viajar como texto.
2. ~~Si la pantalla muestra un total por moneda.~~ Resuelta el 13 de octubre de 2026: sin
   totales por ahora. La pantalla muestra las cuentas agrupadas por moneda y nada más. Sumar un
   total exige decidir antes si una tarjeta resta y si una cuenta "Me deben" suma, y cuando se
   sume lo calcula la API.
3. ~~En qué orden vienen las cuentas.~~ Resuelta el 13 de octubre de 2026. Es el CA-12, y el
   orden lo da la respuesta de [`GET /accounts`](../../04-api.md).
4. ~~Cómo se llega a la pantalla de cuentas.~~ Resuelta el 13 de octubre de 2026: es lo que se
   ve al entrar, sin elegir nada. Es el CA-13. La navegación entre pantallas se decidió el 14 de
   octubre de 2026, con el menú lateral
   ([ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md)): "Cuentas" es la
   primera opción y la que queda marcada al entrar. El chat web va en la sección "Pruebas" del
   menú, aparte de las pantallas del producto
   ([ADR 0002](../../adr/0002-whatsapp-como-canal-principal.md)).
5. ~~El saldo inicial de una cuenta de inversión.~~ Resuelta el 13 de octubre de 2026: cuenta
   como aportado, y quedó escrito en
   [reglas de dominio § 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado).
6. ~~El signo del saldo de una tarjeta.~~ Resuelta el 14 de octubre de 2026: la misma fórmula
   que cualquier cuenta, así que una tarjeta con gastos vencidos sin pagar queda en negativo. Se
   corrigió la frase de
   [reglas de dominio § 13](../../reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias)
   que decía lo contrario. Es el C1-24.
