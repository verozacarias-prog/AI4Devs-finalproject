# Especificación — FEAT-004 · Pantalla de presupuesto

- **Historia de usuario:** [HU4](../../05-historias-de-usuario.md)
- **Estado:** aprobada para el corte 1
- **Fecha:** 2026-10-25

## Alcance

Entra la lectura del presupuesto de un período, que es lo que la entrega final suma de la HU4
([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-final)):

- `GET /budget-periods`, solo la lectura: los períodos que el usuario puede leer, con sus topes
  y el que cubre hoy marcado. Crear, cambiar y confirmar un período es de la HU2.
- `GET /budget-periods/{period_id}/summary`: el resumen de un período, con el ingreso estimado y
  el real, y lo gastado de cada categoría.
- `GET /budgets/{budget_id}`: una categoría con tope, con sus movimientos.
- La pantalla del dashboard que los consume (issue #71), con sus cuatro estados y su
  [contrato de UI](ui_contract.md).

La regla de quién puede leer un período de grupo entra completa, aunque los grupos pasan a una
segunda versión, porque los datos de `local` ya tienen uno ("Casa", de Pablo, con Sofía como
miembro). Decidido por Vero el 24 de octubre de 2026.

No entra, porque los flujos que lo alimentan llegan en una segunda versión: lo comprometido
para los períodos siguientes (reglas recurrentes), lo retirado de inversiones (transferencias) y
cuánto imputó cada miembro a un período de grupo (registrar en un grupo).

## Reglas de dominio que aplican

- [§ 2 — Cuentas y saldo calculado](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado), en
  que un movimiento borrado no cuenta.
- [§ 3 — Presupuestos](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio):
  el tope de una categoría y los períodos que no se solapan.
- [§ 6 — Multimoneda](../../reglas-de-dominio.md#6-multimoneda-y-cotización), en lo que pesa en
  el presupuesto un movimiento en otra moneda.
- [§ 7 — Duplicados](../../reglas-de-dominio.md#7-chequeo-de-duplicados-entre-origen-manual-y-automático):
  una fila marcada como duplicado no suma.
- [§ 10 — Grupos familiares](../../reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad),
  en quién ve un período de grupo.
- [§ 16 — Reintegros](../../reglas-de-dominio.md#16-reintegros-devoluciones-y-plata-que-te-deben):
  un reintegro vinculado resta del gastado en el período en que llega.
- [§ 17 — Preguntas sobre los propios datos](../../reglas-de-dominio.md#17-preguntas-sobre-los-propios-datos),
  en el resumen del período del dashboard.

## Criterios de aceptación

### Qué períodos ve el usuario

La pantalla abre el período que cubre hoy y deja elegir cualquier otro que el usuario pueda leer.

- **CA-1.** El usuario ve la lista de sus períodos individuales y los de los grupos de los que es miembro vigente, cada uno con sus fechas, su estado, su moneda, su ingreso estimado y sus topes.
- **CA-2.** El período que cubre hoy, en la zona horaria del usuario, viene marcado. Hay como mucho uno por dueño: quien tiene un grupo puede tener marcados su individual y el del grupo.
- **CA-3.** Un período de grupo dice el nombre del grupo, para distinguirlo del individual.
- **CA-4.** Un período dice si el usuario lo puede editar: el individual sí, y el de un grupo solo si es su dueño vigente.
- **CA-5.** Los períodos van del que empieza más tarde al que empieza antes. Con el mismo inicio, primero el individual y después los de grupo por nombre. Los topes de cada período van por nombre de categoría, sin distinguir mayúsculas.

### Cuánto se gastó

Lo gastado de una categoría en un período sale de sus movimientos, con las mismas reglas que el saldo.

- **CA-6.** Lo gastado de una categoría es la suma de sus gastos imputados al período.
- **CA-7.** Un gasto en otra moneda que la del período pesa por su monto convertido con su propia cotización, redondeado a dos decimales antes de sumar. Un gasto en la moneda del período pesa por su monto, aunque su cuenta sea de otra moneda.
- **CA-8.** Un reintegro vinculado a un gasto de la categoría resta en el período en que llegó, aunque el gasto sea de otro período. Lo gastado puede quedar negativo.
- **CA-9.** Un movimiento borrado o marcado como duplicado no suma ni resta.
- **CA-10.** El porcentaje usado es lo gastado sobre el tope, por cien, redondeado a un decimal con la mitad hacia arriba. Una categoría sin tope no tiene porcentaje.

### El resumen del período

El resumen muestra el período entero.

- **CA-11.** El ingreso real es la suma de los ingresos imputados al período, convertidos como en CA-7, sin los reintegros vinculados, que restan del gastado y no son ingreso.
- **CA-12.** El resumen lista cada categoría con tope, aunque no tenga gastos, y cada categoría sin tope que tuvo movimientos en el período. Van por nombre, sin distinguir mayúsculas.
- **CA-13.** El total gastado es la suma de lo gastado de todas las categorías del resumen.

### El detalle de una categoría

Desde una categoría con tope se ven los movimientos que suman en ella.

- **CA-14.** El detalle de una categoría con tope muestra su tope, lo gastado, el porcentaje y los movimientos que suman o restan en ella, del más nuevo al más viejo. Cada movimiento trae su fecha, su descripción, si es un gasto o un reintegro, su monto y moneda, lo que pesa en el tope, la cotización si hubo conversión, la cuenta y su origen.

### Quién lo ve

- **CA-15.** El período de un grupo lo leen sus miembros vigentes, y quien salió del grupo solo si el período se superpone con su membresía. Para cualquier otro usuario, el período, su resumen y sus topes no existen: `404`.
- **CA-16.** Un período individual lo lee solo su dueño.

## Casos de prueba

Siguen la forma de [FEAT-001](../FEAT-001/spec.md#casos-de-prueba), con otras acciones:

- En un caso **unitario** se calcula lo gastado, el resumen o qué período cubre hoy, en memoria.
- En un caso de **integración** se pide `GET /budget-periods`, el resumen o el detalle de un
  tope a [la API](../../04-api.md), con los datos guardados en PostgreSQL.
- En un caso de **componente** se abre la pantalla de presupuesto (#71) con las respuestas de la
  API simuladas, y se mira lo que muestra.

Salvo que el caso diga otra cosa: el usuario es Lucía, de Buenos Aires, con moneda primaria
ARS; tiene las cuentas "Galicia pesos", en ARS, y "Galicia USD", en USD, dadas de alta el 1 de
octubre de 2026; su período individual va del 10 de octubre al 9 de noviembre de 2026, está
confirmado, es en ARS, tiene un ingreso estimado de $1.450.000,00 y dos topes, Supermercado
$300.000,00 y Transporte $80.000,00; y hoy es 25 de octubre de 2026.

### Corte 1 — camino feliz

- **Aprobado por:** Verónica Zacarías 25/10/2026
- **C1-26 a C1-38, de componente, sumados para la pantalla:** Veronica Zacarias 25/10/2026
- **C1-29 cambiado al probar la pantalla (una categoría sin tope dice "Sin tope"):** Verónica Zacarías 25/10/2026
- **Total:** 38 casos, 18 unitarios, 7 de integración y 13 de componente.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Lo gastado suma los gastos de la categoría | Unitario | CA-6 y CA-10 |
| C1-02 | Un gasto en dólares pesa convertido | Unitario | CA-7 |
| C1-03 | Cada gasto se redondea antes de sumar | Unitario | CA-7 |
| C1-04 | Un gasto en pesos con una cuenta en dólares pesa por su monto | Unitario | CA-7 |
| C1-05 | Un reintegro resta en el período en que llega | Unitario | CA-8 |
| C1-06 | El reintegro de un gasto anterior puede dejar lo gastado en negativo | Unitario | CA-8 y CA-10 |
| C1-07 | Lo borrado no suma ni resta | Unitario | CA-9 |
| C1-08 | Un gasto duplicado suma una sola vez | Unitario | CA-9 |
| C1-09 | Un gasto de otra categoría o de otro período no suma | Unitario | CA-6 |
| C1-10 | El porcentaje se redondea a un decimal | Unitario | CA-10 |
| C1-11 | La mitad se redondea hacia arriba, y se puede pasar del cien | Unitario | CA-10 |
| C1-12 | Una categoría sin tope no tiene porcentaje | Unitario | CA-10 |
| C1-13 | El ingreso real no cuenta los reintegros | Unitario | CA-11 |
| C1-14 | Qué categorías trae el resumen y en qué orden | Unitario | CA-12 |
| C1-15 | El total gastado suma las categorías, netas de reintegros | Unitario | CA-13 |
| C1-16 | El período que cubre hoy viene marcado | Unitario | CA-2 |
| C1-17 | "Hoy" es el día del usuario, no el del servidor | Unitario | CA-2 |
| C1-18 | Con un grupo, un período marcado por dueño | Unitario | CA-2 |
| C1-19 | Lucía ve sus períodos, en orden y con sus topes | Integración | CA-1, CA-4 y CA-5 |
| C1-20 | Pablo ve su período y el de "Casa", y lo puede editar | Integración | CA-1, CA-3, CA-4 y CA-5 |
| C1-21 | Sofía ve el período de "Casa" y no lo puede editar | Integración | CA-4 y CA-15 |
| C1-22 | El resumen del período de Lucía | Integración | CA-11, CA-12 y CA-13 |
| C1-23 | El detalle de Supermercado, con sus movimientos | Integración | CA-14 |
| C1-24 | La consulta a la base aplica las mismas reglas que el cálculo | Integración | CA-6 a CA-9 |
| C1-25 | Los montos y el porcentaje llegan con sus dígitos exactos | Integración | CA-7 y CA-10 |
| C1-26 | Mientras se consulta, lo dice y no muestra montos | Componente | CA-1 |
| C1-27 | Abre el período que cubre hoy | Componente | CA-2 |
| C1-28 | Un período en borrador avisa que falta confirmarlo | Componente | CA-1 y CA-2 |
| C1-29 | El resumen del período de Lucía | Componente | CA-10, CA-11, CA-12 y CA-13 |
| C1-30 | La barra dice si la categoría está cerca del tope o lo pasó | Componente | CA-10 |
| C1-31 | Los montos se muestran tal como llegan, sin cuentas propias | Componente | CA-13 |
| C1-32 | Lo gastado negativo se ve con su signo | Componente | CA-8 |
| C1-33 | Se elige otro período, y el de un grupo dice su nombre | Componente | CA-1, CA-3 y CA-5 |
| C1-34 | El detalle de Supermercado, con sus movimientos | Componente | CA-14 |
| C1-35 | Un gasto en dólares muestra su cotización | Componente | CA-7 y CA-14 |
| C1-36 | Una categoría sin tope no abre un detalle | Componente | CA-14 |
| C1-37 | Del detalle se vuelve al resumen del mismo período | Componente | CA-14 |
| C1-38 | El menú lleva a la pantalla de presupuesto | Componente | CA-1 |

#### C1-01 · Lo gastado suma los gastos de la categoría

- **Sale de:** CA-6 y CA-10 · **Tipo:** unitario
- **Dado** en el período de Lucía dos gastos en Supermercado, de $154.500,00 el 12 de octubre y
  de $60.000,00 el 18 de octubre, los dos en ARS con "Galicia pesos",
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $214.500,00 (154.500 + 60.000) y el porcentaje usado es 71,5
  (214.500 / 300.000 × 100).
- **Test:** `tests/unit/test_budget_status.py::test_what_is_spent_adds_the_expenses_of_the_category`

#### C1-02 · Un gasto en dólares pesa convertido

- **Sale de:** CA-7 · **Tipo:** unitario
- **Dado** en el período de Lucía un solo gasto en Supermercado de USD 50,00 con "Galicia USD",
  con una cotización guardada de 1.200 pesos por dólar,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $60.000,00 (50 × 1.200), en ARS.
- **Test:** `tests/unit/test_budget_status.py::test_an_expense_in_dollars_weighs_converted`

#### C1-03 · Cada gasto se redondea antes de sumar

- **Sale de:** CA-7 · **Tipo:** unitario
- **Dado** en el período de Lucía dos gastos en Supermercado de USD 10,01 cada uno, con una
  cotización guardada de 1.234,5678 en los dos,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $24.716,04: cada gasto pesa 12.358,02 (10,01 × 1.234,5678 =
  12.358,023678, redondeado), y 12.358,02 + 12.358,02 = 24.716,04. Sumar antes de redondear
  daría 24.716,05.
- **Test:** `tests/unit/test_budget_status.py::test_each_expense_is_rounded_before_adding`

#### C1-04 · Un gasto en pesos con una cuenta en dólares pesa por su monto

- **Sale de:** CA-7 · **Tipo:** unitario
- **Dado** en el período de Lucía un solo gasto en Supermercado de $50.000,00, en ARS, con
  "Galicia USD", con la cotización guardada de 0,0008333333 dólares por peso que convirtió el
  débito a la cuenta,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $50.000,00: el gasto ya está en la moneda del período y la
  cotización no se usa para el presupuesto.
- **Test:** `tests/unit/test_budget_status.py::test_an_expense_in_pesos_with_an_account_in_dollars_weighs_its_amount`

#### C1-05 · Un reintegro resta en el período en que llega

- **Sale de:** CA-8 · **Tipo:** unitario
- **Dado** en el período de Lucía un gasto en Supermercado de $100.000,00 el 12 de octubre y un
  ingreso de $30.000,00 el 20 de octubre, en "Devoluciones y reintegros", vinculado a ese gasto,
  los dos en ARS,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $70.000,00 (100.000 − 30.000) y el porcentaje usado es 23,3
  (70.000 / 300.000 × 100 = 23,33…).
- **Test:** `tests/unit/test_budget_status.py::test_a_refund_subtracts_in_the_period_it_arrives`

#### C1-06 · El reintegro de un gasto anterior puede dejar lo gastado en negativo

- **Sale de:** CA-8 y CA-10 · **Tipo:** unitario
- **Dado** un gasto en Supermercado de $45.000,00 del 20 de septiembre, imputado al período
  anterior, y en el período de Lucía, sin otros movimientos en Supermercado, un ingreso de
  $20.000,00 el 15 de octubre, en "Devoluciones y reintegros", vinculado a ese gasto,
- **cuando** se calcula el estado del tope de Supermercado del período de octubre,
- **entonces** lo gastado es −$20.000,00 y el porcentaje usado es −6,7 (−20.000 / 300.000 ×
  100 = −6,66…). El período anterior no cambia.
- **Test:** `tests/unit/test_budget_status.py::test_the_refund_of_an_earlier_expense_can_leave_what_is_spent_negative`

#### C1-07 · Lo borrado no suma ni resta

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** en el período de Lucía, en Supermercado, un gasto de $100.000,00, otro de $40.000,00
  que el usuario borró, y un ingreso de $10.000,00 vinculado al primero que también borró,
  todos en ARS,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $100.000,00: ni el gasto borrado suma ni el reintegro borrado
  resta.
- **Test:** `tests/unit/test_budget_status.py::test_what_is_deleted_neither_adds_nor_subtracts`

#### C1-08 · Un gasto duplicado suma una sola vez

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** en el período de Lucía un gasto en Supermercado de $25.000,00 y otro igual marcado
  como duplicado del primero,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** lo gastado es $25.000,00.
- **Test:** `tests/unit/test_budget_status.py::test_a_duplicated_expense_adds_only_once`

#### C1-09 · Un gasto de otra categoría o de otro período no suma

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** un gasto en Supermercado de $30.000,00 en el período de Lucía, uno en Transporte de
  $12.000,00 en el mismo período, y uno en Supermercado de $50.000,00 del 5 de octubre,
  imputado al período anterior,
- **cuando** se calcula el estado del tope de Supermercado del período de octubre,
- **entonces** lo gastado es $30.000,00.
- **Test:** `tests/unit/test_budget_status.py::test_an_expense_of_another_category_or_another_period_does_not_add`

#### C1-10 · El porcentaje se redondea a un decimal

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** en el período de Lucía gastos en Supermercado por $100.000,00,
- **cuando** se calcula el estado del tope de Supermercado,
- **entonces** el porcentaje usado es 33,3 (100.000 / 300.000 × 100 = 33,33…), calculado sin
  pasar por punto flotante.
- **Test:** `tests/unit/test_budget_status.py::test_the_percentage_is_rounded_to_one_decimal`

#### C1-11 · La mitad se redondea hacia arriba, y se puede pasar del cien

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** en el período de Lucía gastos en Transporte por $80.040,00,
- **cuando** se calcula el estado del tope de Transporte,
- **entonces** el porcentaje usado es 100,1 (80.040 / 80.000 × 100 = 100,05, y la mitad sube).
  Con el redondeo al par daría 100,0.
- **Test:** `tests/unit/test_budget_status.py::test_the_half_is_rounded_up_and_it_can_go_past_one_hundred`

#### C1-12 · Una categoría sin tope no tiene porcentaje

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** en el período de Lucía un gasto en "Comida afuera y delivery", que no tiene tope, de
  $38.500,00,
- **cuando** se calcula el resumen del período,
- **entonces** "Comida afuera y delivery" aparece con lo gastado $38.500,00, sin tope y sin
  porcentaje.
- **Test:** `tests/unit/test_period_summary.py::test_a_category_without_a_limit_has_no_percentage`

#### C1-13 · El ingreso real no cuenta los reintegros

- **Sale de:** CA-11 · **Tipo:** unitario
- **Dado** en el período de Lucía un ingreso en Sueldo de $1.200.000,00, un ingreso en Otros
  ingresos de USD 100,00 con "Galicia USD" y una cotización de 1.200, y un ingreso de
  $30.000,00 en "Devoluciones y reintegros" vinculado a un gasto en Supermercado,
- **cuando** se calcula el resumen del período,
- **entonces** el ingreso real es $1.320.000,00 (1.200.000 + 100 × 1.200), sin el reintegro, y
  el ingreso estimado es $1.450.000,00.
- **Test:** `tests/unit/test_period_summary.py::test_the_actual_income_does_not_count_refunds`

#### C1-14 · Qué categorías trae el resumen y en qué orden

- **Sale de:** CA-12 · **Tipo:** unitario
- **Dado** en el período de Lucía un gasto en "Salud" de $8.000,00, uno en "café", una
  categoría propia escrita en minúsculas, de $5.000,00, y ningún movimiento en Supermercado, en
  Transporte ni en otra categoría,
- **cuando** se calcula el resumen del período,
- **entonces** las categorías son, en este orden: "café" ($5.000,00, sin tope), "Salud" ($8.000,00, sin tope), "Supermercado" ($0,00 de $300.000,00, 0,0) y
  "Transporte" ($0,00 de $80.000,00, 0,0). Ninguna otra categoría aparece.
- **Test:** `tests/unit/test_period_summary.py::test_which_categories_the_summary_brings_and_in_what_order`

#### C1-15 · El total gastado suma las categorías, netas de reintegros

- **Sale de:** CA-13 · **Tipo:** unitario
- **Dado** en el período de Lucía un gasto en Supermercado de $100.000,00, un reintegro de
  $30.000,00 vinculado a él, un gasto en Transporte de $12.000,00 y uno en Salud, sin tope, de
  $8.000,00,
- **cuando** se calcula el resumen del período,
- **entonces** el total gastado es $90.000,00 (70.000 + 12.000 + 8.000).
- **Test:** `tests/unit/test_period_summary.py::test_the_total_spent_adds_the_categories_net_of_refunds`

#### C1-16 · El período que cubre hoy viene marcado

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** que Lucía tiene el período del 10 de septiembre al 9 de octubre, confirmado, el del 10
  de octubre al 9 de noviembre, confirmado, y el del 10 de noviembre al 9 de diciembre, en
  borrador, y hoy es 25 de octubre,
- **cuando** se listan sus períodos,
- **entonces** solo el del 10 de octubre al 9 de noviembre viene marcado como actual.
- **Test:** `tests/unit/test_list_budget_periods.py::test_the_period_that_covers_today_comes_marked`

#### C1-17 · "Hoy" es el día del usuario, no el del servidor

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** los mismos tres períodos del caso C1-16, y el reloj marca 10 de noviembre de 2026 a
  la 01:00 UTC, que en Buenos Aires es 9 de noviembre a las 22:00,
- **cuando** se listan sus períodos,
- **entonces** viene marcado el del 10 de octubre al 9 de noviembre: para Lucía todavía es 9, el
  último día de ese período.
- **Test:** `tests/unit/test_list_budget_periods.py::test_today_is_the_day_of_the_user_not_of_the_server`

#### C1-18 · Con un grupo, un período marcado por dueño

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** que Pablo tiene su período individual del 10 de octubre al 9 de noviembre y es dueño
  de "Casa", cuyo período va del 1 al 31 de octubre, y hoy es 25 de octubre,
- **cuando** se listan sus períodos,
- **entonces** vienen marcados los dos: uno es suyo y el otro del grupo.
- **Test:** `tests/unit/test_list_budget_periods.py::test_with_a_group_one_period_is_marked_for_each_owner`

#### C1-19 · Lucía ve sus períodos, en orden y con sus topes

- **Sale de:** CA-1, CA-4 y CA-5 · **Tipo:** integración
- **Dado** guardados en la base el período de Lucía del 10 de octubre al 9 de noviembre, con sus
  topes de Supermercado y Transporte, y otro del 10 de noviembre al 9 de diciembre, en borrador,
  en ARS, con ingreso estimado de $1.500.000,00 y un tope en Transporte de $90.000,00,
- **cuando** Lucía, con su sesión, pide `GET /budget-periods`,
- **entonces** responde `200` con dos períodos: primero el de noviembre, en `draft`, sin marcar
  como actual, con el tope de Transporte; después el de octubre, en `confirmed`, marcado como
  actual, con los topes de Supermercado y de Transporte, en ese orden. Los dos son
  individuales, sin nombre de grupo, y los dos dicen que Lucía los puede editar.
- **Test:** `tests/integration/test_budgets.py::test_lucia_sees_her_periods_in_order_and_with_their_limits`

#### C1-20 · Pablo ve su período y el de "Casa", y lo puede editar

- **Sale de:** CA-1, CA-3, CA-4 y CA-5 · **Tipo:** integración
- **Dado** guardados en la base el período individual de Pablo y el de "Casa", del que es dueño,
  los dos del 1 al 31 de octubre y confirmados,
- **cuando** Pablo, con su sesión, pide `GET /budget-periods`,
- **entonces** responde `200` con dos períodos, en este orden: el individual, sin nombre de
  grupo, y el de "Casa", con el nombre del grupo. Los dos vienen marcados como actuales y los
  dos dicen que Pablo los puede editar.
- **Test:** `tests/integration/test_budgets.py::test_pablo_sees_his_period_and_the_one_of_casa_and_can_edit_them`

#### C1-21 · Sofía ve el período de "Casa" y no lo puede editar

- **Sale de:** CA-4 y CA-15 · **Tipo:** integración
- **Dado** guardados en la base el período de "Casa", del 1 al 31 de octubre, confirmado, con un
  tope en Supermercado de $500.000,00, y Sofía como miembro vigente del grupo, sin ser su dueña,
- **cuando** Sofía, con su sesión, pide `GET /budget-periods` y después el resumen de ese
  período,
- **entonces** la lista trae el período de "Casa", con su nombre, diciendo que Sofía no lo puede
  editar, y el resumen responde `200` con Supermercado: $0,00 de $500.000,00.
- **Test:** `tests/integration/test_budgets.py::test_sofia_sees_the_period_of_casa_and_cannot_edit_it`

#### C1-22 · El resumen del período de Lucía

- **Sale de:** CA-11, CA-12 y CA-13 · **Tipo:** integración
- **Dado** guardados en el período de Lucía: un ingreso en Sueldo de $1.200.000,00; dos gastos en
  Supermercado, de $154.500,00 en ARS y de USD 50,00 a 1.200; un gasto en Transporte de
  $12.000,00; y uno en "Comida afuera y delivery", sin tope, de $38.500,00,
- **cuando** Lucía, con su sesión, pide `GET /budget-periods/{period_id}/summary`,
- **entonces** responde `200` con moneda ARS, ingreso estimado 1450000.00, ingreso real
  1200000.00, total gastado 265000.00 (214.500 + 12.000 + 38.500) y estas categorías, en este
  orden: "Comida afuera y delivery" (38500.00, sin tope ni porcentaje ni `budget_id`),
  "Supermercado" (214500.00 de 300000.00, 71.5, con el `budget_id` de su tope) y "Transporte"
  (12000.00 de 80000.00, 15.0, con el suyo).
- **Test:** `tests/integration/test_budgets.py::test_the_summary_of_the_period_of_lucia`

#### C1-23 · El detalle de Supermercado, con sus movimientos

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** guardados en el período de Lucía, en Supermercado, un gasto de $154.500,00 en ARS con
  "Galicia pesos", sin descripción, del 12 de octubre, y uno de USD 50,00 con "Galicia USD", a
  1.200, con la descripción "super", del 18 de octubre, los dos cargados por chat,
- **cuando** Lucía, con su sesión, pide `GET /budgets/{budget_id}` del tope de Supermercado,
- **entonces** responde `200` con la categoría "Supermercado", moneda ARS, tope 300000.00,
  gastado 214500.00, porcentaje 71.5 y dos movimientos, en este orden: el del 18 de octubre
  (gasto, 50.00 USD, pesa 60000.00, cotización 1200, "Galicia USD", "super", manual) y el del 12
  (gasto, 154500.00 ARS, pesa 154500.00, sin cotización, "Galicia pesos", sin descripción,
  manual).
- **Test:** `tests/integration/test_budgets.py::test_the_detail_of_supermercado_with_its_movements`

#### C1-24 · La consulta a la base aplica las mismas reglas que el cálculo

- **Sale de:** CA-6 a CA-9 · **Tipo:** integración
- **Dado** guardados en el período de Lucía, en Supermercado: un gasto de $100.000,00; uno de
  $40.000,00 borrado; uno de $25.000,00 marcado como duplicado del primero; un reintegro de
  $30.000,00 vinculado al primero; y además un gasto en Supermercado de $50.000,00 en el período
  anterior y uno en Transporte de $12.000,00 en este,
- **cuando** Lucía pide `GET /budgets/{budget_id}` del tope de Supermercado,
- **entonces** lo gastado es 70000.00 (100.000 − 30.000), y los movimientos son solo el gasto de
  $100.000,00 y el reintegro, que viene como ingreso.
- **Test:** `tests/integration/test_budgets.py::test_the_database_query_follows_the_rules_of_what_is_spent`

#### C1-25 · Los montos y el porcentaje llegan con sus dígitos exactos

- **Sale de:** CA-7 y CA-10 · **Tipo:** integración
- **Dado** guardados en el período de Lucía dos gastos en Supermercado de USD 10,01, con una
  cotización de 1.234,5678 cada uno, y un gasto en Transporte de $80.040,00,
- **cuando** Lucía pide el resumen del período,
- **entonces** Supermercado trae lo gastado 24716.04 y el porcentaje 8.2 (24.716,04 / 300.000 ×
  100 = 8,238…), y Transporte trae 80040.00 y 100.1, escritos en el JSON con esos dígitos.
- **Test:** `tests/integration/test_budgets.py::test_the_amounts_and_the_percentage_arrive_with_their_exact_digits`

Los casos de componente simulan las respuestas de la API con los datos de Lucía. Salvo que el
caso diga otra cosa, `GET /budget-periods` trae dos períodos, en este orden: el actual, del 10
de octubre al 9 de noviembre de 2026, confirmado, con `is_current` en verdadero; y el anterior,
del 10 de septiembre al 9 de octubre, confirmado. El resumen y el detalle son los que dice cada
caso.

#### C1-26 · Mientras se consulta, lo dice y no muestra montos

- **Sale de:** CA-1 · **Tipo:** componente
- **Dado** una respuesta de `GET /budget-periods` o del resumen que todavía no llegó,
- **cuando** se abre la pantalla,
- **entonces** dice "Consultando tu presupuesto…" y no muestra ningún monto ni ninguna barra.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-26: while the budget is being asked for, it says so and shows no amount"

#### C1-27 · Abre el período que cubre hoy

- **Sale de:** CA-2 · **Tipo:** componente
- **Dado** los dos períodos de Lucía, con el actual marcado,
- **cuando** se abre la pantalla,
- **entonces** el selector muestra elegido "Personal · del 10/10/2026 al 9/11/2026", y se pide el
  resumen de ese período y no el del anterior.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-27: it opens the period that covers today"

#### C1-28 · Un período en borrador avisa que falta confirmarlo

- **Sale de:** CA-1 y CA-2 · **Tipo:** componente
- **Dado** que el período actual de Lucía viene con el estado `draft`, con sus dos topes y un
  resumen sin gastos,
- **cuando** se abre la pantalla,
- **entonces** abre ese período, con el aviso "Este período está en borrador: confirmalo para
  que reciba movimientos", y muestra sus topes con $ 0,00 gastado.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-28: a draft period warns that it still has to be confirmed"

#### C1-29 · El resumen del período de Lucía

- **Sale de:** CA-10, CA-11, CA-12 y CA-13 · **Tipo:** componente
- **Dado** un resumen con ingreso estimado 1450000.00, ingreso real 1500000.00, total gastado
  108256.04 y tres categorías, en este orden: "Café", sin tope, gastado 3500.00; "Supermercado",
  tope 300000.00, gastado 24716.04, porcentaje 8.2; y "Transporte", tope 80000.00, gastado
  80040.00, porcentaje 100.1,
- **cuando** se abre la pantalla,
- **entonces** muestra el ingreso estimado $ 1.450.000,00, el real $ 1.500.000,00 y el total
  gastado $ 108.256,04, y las tres categorías en ese orden: Café con $ 3.500,00 gastado y
  "Sin tope" en gris, sin barra ni porcentaje; Supermercado con una barra, $ 24.716,04 de $ 300.000,00 y 8,2 %; y
  Transporte con una barra, $ 80.040,00 de $ 80.000,00 y 100,1 %.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-29: the summary of the period of Lucía"

#### C1-30 · La barra dice si la categoría está cerca del tope o lo pasó

- **Sale de:** CA-10 · **Tipo:** componente
- **Dado** un resumen con cuatro categorías con tope, con los porcentajes 80.0, 80.1, 100.0 y
  100.1,
- **cuando** se abre la pantalla,
- **entonces** la barra de 80,0 % es normal, las de 80,1 % y 100,0 % están cerca del tope, con
  el color de advertencia y la etiqueta "Cerca del tope", y la de 100,1 % está excedida: llena,
  en rojo, el color de error, con la etiqueta "Excedido". Pasar el 80 % es estar cerca, y pasar
  el 100 % es haberlo pasado, con los mismos umbrales que las alertas ([§ 3](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)).
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-30: the bar says whether the category is near its limit or over it"

#### C1-31 · Los montos se muestran tal como llegan, sin cuentas propias

- **Sale de:** CA-13 · **Tipo:** componente
- **Dado** un resumen con una sola categoría, "Supermercado", gastado 0.10, y un total gastado
  escrito como `0.30`,
- **cuando** se abre la pantalla,
- **entonces** el total gastado es $ 0,30 y no $ 0,10: la pantalla no suma ni redondea.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-31: the amounts are shown as they arrive, without sums of its own"

#### C1-32 · Lo gastado negativo se ve con su signo

- **Sale de:** CA-8 · **Tipo:** componente
- **Dado** un resumen con "Supermercado", tope 300000.00, gastado -5000.00 y porcentaje -1.7,
- **cuando** se abre la pantalla,
- **entonces** Supermercado muestra -$ 5.000,00, con el guion que pone el formato de moneda de
  `es-AR`, y -1,7 %, con la barra vacía.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-32: a negative spent is shown with its sign"

#### C1-33 · Se elige otro período, y el de un grupo dice su nombre

- **Sale de:** CA-1, CA-3 y CA-5 · **Tipo:** componente
- **Dado** que la lista trae cuatro períodos, en el orden de CA-5: uno de Lucía del 10 de
  noviembre al 9 de diciembre, en borrador; su actual; uno del grupo "Casa", del que es miembro,
  del 10 de octubre al 9 de noviembre; y su anterior,
- **cuando** se abre el selector y se elige el anterior,
- **entonces** el selector lista los cuatro en el orden en que llegan: "Personal · del
  10/11/2026 al 9/12/2026 · Borrador", "Personal · del 10/10/2026 al 9/11/2026", "Casa · del
  10/10/2026 al 9/11/2026" y "Personal · del 10/9/2026 al 9/10/2026"; se pide el resumen del
  anterior y se muestra ese.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-33: another period is chosen, and the one of a group says its name"

#### C1-34 · El detalle de Supermercado, con sus movimientos

- **Sale de:** CA-14 · **Tipo:** componente
- **Dado** el resumen del caso C1-29, y un detalle de Supermercado con tope 300000.00, gastado
  184500.00, porcentaje 61.5 y tres movimientos, en este orden: un reintegro del 20 de octubre,
  30000.00 ARS, "devolución", "Galicia pesos", manual; un gasto del 18, 60000.00 ARS, "super",
  "Galicia pesos", automático; y un gasto del 12, 154500.00 ARS, sin descripción, "Galicia
  pesos", manual,
- **cuando** se elige Supermercado,
- **entonces** se pide `GET /budgets/{budget_id}` de su tope, y se ven $ 184.500,00 de
  $ 300.000,00 y 61,5 %, y los tres movimientos en ese orden, cada uno con su fecha, su
  descripción o nada, "Reintegro" o "Gasto", su monto con su moneda, la cuenta y una etiqueta
  "Manual" o "Automático".
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-34: the detail of Supermercado, with its movements"

#### C1-35 · Un gasto en dólares muestra su cotización

- **Sale de:** CA-7 y CA-14 · **Tipo:** componente
- **Dado** un detalle con dos gastos: uno de 10.00 USD, cotización 1234.5678, que pesa
  12345.68, con "Galicia USD"; y uno de 5000.00 ARS, sin cotización, con "Galicia pesos",
- **cuando** se elige la categoría,
- **entonces** el de dólares muestra US$ 10,00, "cotización 1.234,5678" y que pesa
  $ 12.345,68; el de pesos muestra $ 5.000,00 y ninguna cotización.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-35: an expense in dollars shows its exchange rate"

#### C1-36 · Una categoría sin tope no abre un detalle

- **Sale de:** CA-14 · **Tipo:** componente
- **Dado** el resumen del caso C1-29,
- **cuando** se abre la pantalla,
- **entonces** Supermercado y Transporte se pueden elegir, y Café no: no es un botón ni un
  enlace, y no se pide ningún detalle.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-36: a category without a limit does not open a detail"

#### C1-37 · Del detalle se vuelve al resumen del mismo período

- **Sale de:** CA-14 · **Tipo:** componente
- **Dado** el detalle de Supermercado del caso C1-34 abierto,
- **cuando** se elige "Volver al resumen",
- **entonces** se ve el resumen del mismo período, con el selector en el mismo período.
- **Test:** `src/pages/BudgetPage.test.tsx` › "case C1-37: from the detail it goes back to the summary of the same period"

#### C1-38 · El menú lleva a la pantalla de presupuesto

- **Sale de:** CA-1 · **Tipo:** componente
- **Dado** el dashboard con la sesión de Lucía, en la pantalla de cuentas,
- **cuando** se elige "Presupuesto" en el menú,
- **entonces** se ve la pantalla de presupuesto y "Presupuesto" queda marcada como la pantalla
  actual.
- **Test:** `src/components/AppShell.test.tsx` › "case C1-38: the menu leads to the budget screen"

### Corte 2 — errores y estado vacío

- **Aprobado por:** pendiente

Los casos se escriben antes de este corte. Cubre, como mínimo: sin sesión, `401`; el período,
el resumen o el tope de otro usuario, `404`; el período de un grupo del que no es miembro,
`404`; quien salió de un grupo ve los períodos que se superponen con su membresía y no los
posteriores; un usuario sin períodos; un período sin topes ni movimientos; un id que no es un
UUID; y los estados de vacío y error de la pantalla.

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

Los casos se escriben antes de este corte. Cubre que la línea de cada pedido no lleve montos,
nombres de categorías, de cuentas ni del grupo, y la accesibilidad de la pantalla: las barras
anuncian su porcentaje y los montos su moneda.

## Estados de pantalla

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | Mientras la lista de períodos o el resumen no respondieron | Un indicador de carga |
| Con contenido | Hay un período elegido y su resumen llegó | El ingreso estimado y el real, y una barra por categoría con tope (normal, cerca del tope, excedido) y lo gastado de las que no tienen |
| Vacío | El usuario no tiene ningún período, o el elegido no tiene topes ni movimientos | Que no hay nada que mostrar y qué hacer |
| Error | Alguna de las consultas falló | Qué pasó y un botón para reintentar |

Qué período se abre está en la decisión 8, y la máquina de estados entera en el
[contrato de UI](ui_contract.md).

## Mensajes al usuario

No hay mensajes de WhatsApp. Los textos de la pantalla van en `frontend/src/messages.ts`.

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| Un monto nunca es `float`, tampoco el porcentaje ni al responder | C1-03, C1-10, C1-11, C1-25 |
| La moneda viaja con el monto | C1-23 |
| Cada movimiento se convierte con su cotización, redondeado antes de sumar ([§ 6](../../reglas-de-dominio.md#6-multimoneda-y-cotización)) | C1-02 a C1-04, C1-25 |
| Lo borrado y lo duplicado no cuentan ([§ 2](../../reglas-de-dominio.md#2-cuentas-y-saldo-calculado) y [§ 7](../../reglas-de-dominio.md#7-chequeo-de-duplicados-entre-origen-manual-y-automático)) | C1-07, C1-08, C1-24 |
| Un reintegro resta en el período en que llega ([§ 16](../../reglas-de-dominio.md#16-reintegros-devoluciones-y-plata-que-te-deben)) | C1-05, C1-06, C1-13 |
| "Hoy" es el día del usuario | C1-17 |
| Todo acceso se limita al usuario de la sesión y a sus grupos ([§ 10](../../reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad)) | C1-21 y el corte 2 |

## Sin cubrir

- Que los montos sean `Decimal` y no `float` dentro del backend: lo valida
  `scripts/verify_architecture.py`.

## Fuera de alcance

- Crear, cambiar y confirmar un período: es la HU2 (#73 y #74).
- Lo comprometido para los períodos siguientes, lo retirado de inversiones y cuánto imputó cada
  miembro de un grupo: llegan con las reglas recurrentes, las transferencias y el registro en un
  grupo, en una segunda versión. El resumen no trae esos campos.
- Las preguntas al asistente sobre el presupuesto, que son la § 17 por chat (#78).

## Decisiones tomadas al especificar

1. ~~Qué devuelve `GET /budgets/{budget_id}` y de dónde sale la pantalla.~~ Resuelta el 24 de
   octubre de 2026: entran también el resumen del período y la lectura de `GET /budget-periods`,
   con el período actual marcado por el backend. Se corrigieron la hoja de ruta, la API y los
   tickets.
2. ~~Qué trae cada movimiento del detalle.~~ Resuelta el 24 de octubre de 2026: los campos de
   CA-14, del más nuevo al más viejo y sin paginar. Quedó en [la API](../../04-api.md).
3. ~~Los períodos de grupo.~~ Resuelta el 24 de octubre de 2026: la regla de lectura entra
   completa.
4. ~~El redondeo del porcentaje.~~ Resuelta el 25 de octubre de 2026, al aprobar el corte 1:
   un decimal, con la mitad hacia arriba (CA-10). Quedó en [la API](../../04-api.md).
5. ~~Qué categorías sin tope trae el resumen.~~ Resuelta el 25 de octubre de 2026: solo las que
   tuvieron movimientos en el período (CA-12). Se corrigió [la API](../../04-api.md), que decía
   "todas sus categorías, tengan tope o no".
6. ~~El orden de los períodos y de las categorías.~~ Resuelta el 25 de octubre de 2026: CA-5 y
   CA-12.
7. ~~De qué depende que un período diga que se puede editar.~~ Resuelta el 25 de octubre de
   2026: de quién es el dueño y no del estado (CA-4).
8. ~~Qué período abre la pantalla.~~ Resuelta el 25 de octubre de 2026: el primero de la lista
   que viene marcado como actual, aunque esté en borrador, y entonces con su aviso (C1-27 y
   C1-28). Si ninguno cubre hoy, el primero de la lista, sin aviso ni caso propio: pasa solo
   mientras el borrador del período siguiente no se genere solo, que es de una segunda versión,
   y con el selector a la vista y las fechas en cada período no se confunde con el actual.
9. ~~Cuándo una barra está cerca del tope.~~ Resuelta el 25 de octubre de 2026: al pasar el 80 %,
   y excedida al pasar el 100 %, los mismos umbrales que las alertas (C1-30). Van como constante
   del dashboard, porque la configuración de las alertas todavía no existe.
