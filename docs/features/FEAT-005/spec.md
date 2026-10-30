# Especificación — FEAT-005 · Armar y confirmar el presupuesto de un período

- **Historia de usuario:** [HU2](../../05-historias-de-usuario.md)
- **Estado:** borrador
- **Fecha:** 2026-10-29

## Alcance

Entra lo que la entrega final suma de la HU2: armar y confirmar desde el dashboard el
presupuesto de un período individual
([hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-final)):

- `POST /budget-periods`: crear un borrador, con su cadencia, su día de inicio, su moneda, su
  ingreso estimado y un tope por cada categoría que el usuario quiera controlar (issue #73).
- `PUT /budget-periods/{period_id}`: reemplazar el contenido de un borrador, o el ingreso
  estimado y los topes de un período confirmado (issue #73).
- `POST /budget-periods/{period_id}/confirm`: confirmarlo (issue #73).
- `GET /categories`: las categorías de gasto del usuario, para elegir a cuáles ponerles tope
  (issue #73).
- La pantalla del dashboard que arma el borrador y lo confirma (issue #74), con sus cuatro
  estados y su [contrato de UI](ui_contract.md).

La lectura, `GET /budget-periods`, ya está desde la [FEAT-004](../FEAT-004/spec.md): esta
funcionalidad la usa para mostrar el borrador y el período confirmado.

No entra, porque la hoja de ruta lo deja para una segunda versión: el borrador que se arma solo
copiando el período anterior y el recordatorio antes del inicio, que son procesos programados;
los montos de las reglas recurrentes de monto variable al confirmar, porque las reglas
recurrentes no están; y confirmar por WhatsApp. Crear un período de grupo tampoco entra, porque la HU2 de
la entrega final es individual; cambiar o confirmar uno ya existente sí, solo su dueño
([pregunta abierta 7](#preguntas-abiertas)).

## Reglas de dominio que aplican

- [§ 1 — Registro de un movimiento](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma),
  en que con un solo período posible y confirmado un gasto se imputa sin preguntar, y con uno
  solo en borrador queda pendiente.
- [§ 3 — Presupuestos](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio):
  el día de inicio, el fin de un período mensual, el borrador, dónde se arma y se confirma, que
  los períodos de un mismo dueño no se solapan y que solo uno confirmado recibe movimientos.
- [§ 4 — Categorías](../../reglas-de-dominio.md#4-categorías-catálogo-base-categorías-propias-y-creación-con-confirmación),
  en que cada categoría es de gasto o de ingreso.
- [§ 10 — Grupos familiares](../../reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad),
  en que un período de grupo lo arma y lo confirma solo su dueño vigente.

## Criterios de aceptación

### Armar un borrador

El usuario arma el presupuesto de un período, que queda en borrador hasta que lo confirma.

- **CA-1.** El usuario crea un período individual en borrador, con su cadencia, mensual o quincenal, su día de inicio, su moneda, su ingreso estimado y un tope por cada categoría que quiera controlar. El período es del usuario de la sesión.
- **CA-2.** El período puede empezar cualquier día. Uno mensual sin fin indicado termina el día anterior al mismo día del mes siguiente: uno que empieza el 10 de noviembre termina el 9 de diciembre.
- **CA-3.** Un período mensual con el fin indicado termina ese día, aunque dure más o menos de un mes: es el período de transición para mover el día de inicio.
- **CA-11.** Un período quincenal termina el día que el usuario indica: su fin no se calcula, y sin él el período no se crea.
- **CA-4.** Cambiar un borrador reemplaza su contenido entero: sus fechas, su moneda, su ingreso estimado y sus topes. Un tope que no va en el cambio deja de existir.
- **CA-5.** El ingreso estimado y cada tope se guardan y se devuelven con sus centavos exactos.
- **CA-15.** El ingreso estimado es 0 o más: 0 es el de un período sin ingreso, como el primero, y con uno negativo el período no se guarda.
- **CA-6.** Un borrador figura en la lista de períodos como borrador, con sus topes, y no recibe movimientos: un gasto con fecha en él queda pendiente.

### Las categorías y el formulario

- **CA-12.** Para elegir a qué categorías ponerles tope, el usuario ve sus categorías de gasto, las del catálogo base y las propias, por nombre y sin distinguir mayúsculas. No ve las de ingreso ni las propias de otro usuario.
- **CA-13.** Un período nuevo arranca como copia del último del usuario, que puede cambiar antes de guardar ([reglas de dominio § 3](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)), con el inicio sugerido el día después del fin de ese período. El último es el período individual que empieza más tarde, aunque sea un borrador, decidido por Vero el 29 de octubre de 2026. En un mensual el fin lo calcula la API; en un quincenal queda vacío, porque se indica siempre. Sin un período anterior, el formulario viene vacío. Lo hace la pantalla con `GET /budget-periods`, sin regla nueva en el backend.
- **CA-14.** Un tope va solo sobre una categoría de gasto: sobre una de ingreso, el período no se guarda.

### Confirmar

- **CA-7.** Confirmar un borrador lo pasa a confirmado, sin cambiar nada más de él.
- **CA-8.** Un período confirmado recibe movimientos: si es el único que cubre la fecha de un gasto, el gasto se imputa a él sin preguntar.
- **CA-9.** Confirmar un período ya confirmado responde igual y no cambia nada.

### Cambiar un período confirmado

- **CA-10.** En un período confirmado, el usuario cambia el ingreso estimado y los topes, con las mismas reglas que en un borrador. Sus fechas y su moneda no cambian, y el período sigue confirmado.

### Quién lo cambia

- **CA-16.** Solo el dueño de un período lo cambia y lo confirma: el usuario en uno individual, y el dueño vigente del grupo en uno de grupo. Un miembro que no es el dueño lo lee y no lo cambia.

## Casos de prueba

Siguen la forma de [FEAT-001](../FEAT-001/spec.md#casos-de-prueba), con otras acciones:

- En un caso **unitario** se calcula el fin de un período o se corre un caso de uso con dobles
  de los puertos, en memoria.
- En un caso de **integración** se pide `POST /budget-periods`, `PUT /budget-periods/{period_id}`,
  `POST /budget-periods/{period_id}/confirm` o `GET /budget-periods` a [la API](../../04-api.md),
  con los datos guardados en PostgreSQL.
- Los casos de **componente**, de la pantalla (#74), se suman y se aprueban cuando la pantalla
  está armada ([convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales)).

Salvo que el caso diga otra cosa, valen los datos de los casos de la
[FEAT-004](../FEAT-004/spec.md#casos-de-prueba): Lucía, su cuenta "Galicia pesos" y su período
actual, confirmado, del 10 de octubre al 9 de noviembre de 2026, con sus dos topes. Además, Lucía
no es miembro de ningún grupo, y hoy es 29 de octubre de 2026.

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacariass 29/10/2026
- **Total:** 21 casos, 12 unitarios y 9 de integración. C1-17 y C1-18 son **nuevos**, sumados el
  29 de octubre de 2026 por la [pregunta abierta 1](#preguntas-abiertas); C1-19, por la 3; y
  C1-20 y C1-21, por la 4. C1-11, C1-13, C1-14 y C1-15 **cambiaron** por la 8. CA-13 se
  prueba con casos de componente, que se proponen cuando la pantalla esté armada.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Un mensual termina el día anterior al mismo día del mes siguiente | Unitario | CA-2 |
| C1-02 | Un mensual que empieza el 1 termina el último día del mes | Unitario | CA-2 |
| C1-03 | Un mensual que empieza un día que el mes siguiente no tiene | Unitario | CA-2 |
| C1-04 | Un mensual con el fin indicado termina ese día | Unitario | CA-3 |
| C1-05 | Crear deja un borrador del usuario, con sus topes | Unitario | CA-1 |
| C1-06 | Cambiar un borrador reemplaza su contenido entero | Unitario | CA-4 |
| C1-07 | Confirmar un borrador no cambia nada más de él | Unitario | CA-7 |
| C1-08 | Confirmar uno ya confirmado no escribe nada | Unitario | CA-9 |
| C1-09 | Un gasto que cae solo en un borrador queda pendiente | Unitario | CA-6 |
| C1-10 | El mismo gasto, con el período ya confirmado, se imputa sin preguntar | Unitario | CA-8 |
| C1-11 | **Cambiado.** Lucía crea el borrador del período siguiente | Integración | CA-1 y CA-2 |
| C1-12 | El borrador figura en la lista, con sus topes | Integración | CA-6 |
| C1-13 | **Cambiado.** Lucía cambia el borrador | Integración | CA-4 |
| C1-14 | **Cambiado.** Lucía confirma el borrador | Integración | CA-7 |
| C1-15 | **Cambiado.** Confirmarlo otra vez responde igual | Integración | CA-9 |
| C1-16 | El ingreso y los topes llegan con sus centavos exactos | Integración | CA-5 |
| C1-17 | **Nuevo.** Cambiar un confirmado cambia su ingreso y sus topes, y nada más | Unitario | CA-10 |
| C1-18 | **Nuevo.** Lucía les pone otro ingreso y otros topes a su período actual | Integración | CA-10 |
| C1-19 | **Nuevo.** Un quincenal termina el día indicado | Unitario | CA-11 |
| C1-20 | **Nuevo.** Lucía ve sus categorías de gasto, base y propias, por nombre | Integración | CA-12 |
| C1-21 | **Nuevo.** Las categorías propias de otro usuario no aparecen | Integración | CA-12 |

#### C1-01 · Un mensual termina el día anterior al mismo día del mes siguiente

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** un período mensual que empieza el 10 de noviembre de 2026, sin fin indicado,
- **cuando** se calcula su fin,
- **entonces** es el 9 de diciembre de 2026.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_monthly_one_ends_the_day_before_the_same_day_of_the_next_month`

#### C1-02 · Un mensual que empieza el 1 termina el último día del mes

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** un período mensual que empieza el 1 de febrero de 2027, sin fin indicado,
- **cuando** se calcula su fin,
- **entonces** es el 28 de febrero de 2027, el día anterior al 1 de marzo.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_monthly_one_that_starts_on_the_first_ends_on_the_last_day_of_the_month`

#### C1-03 · Un mensual que empieza un día que el mes siguiente no tiene

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** un período mensual que empieza el 31 de enero de 2027, sin fin indicado,
- **cuando** se calcula su fin,
- **entonces** es el 27 de febrero de 2027: el 31 de febrero no existe, el mismo día del mes
  siguiente pasa a ser el 28, el último del mes, y el período termina el día anterior.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_monthly_one_that_starts_on_a_day_the_next_month_does_not_have`

#### C1-04 · Un mensual con el fin indicado termina ese día

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** un período mensual que empieza el 10 de noviembre de 2026, con el fin indicado el 30
  de noviembre de 2026,
- **cuando** se calcula su fin,
- **entonces** es el 30 de noviembre de 2026, aunque dure 21 días.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_monthly_one_with_its_end_given_ends_that_day`

#### C1-05 · Crear deja un borrador del usuario, con sus topes

- **Sale de:** CA-1 · **Tipo:** unitario
- **Dado** Lucía, sin otros períodos que el actual,
- **cuando** crea un período mensual que empieza el 10 de noviembre de 2026, en ARS, con un
  ingreso estimado de $1.500.000,00 y los topes Supermercado $320.000,00 y Transporte
  $90.000,00,
- **entonces** queda guardado un período en borrador, de Lucía y de ningún grupo, del 10 de
  noviembre al 9 de diciembre de 2026, en ARS, con ese ingreso, y dos topes con esas categorías
  y esos montos.
- **Test:** `tests/unit/test_budget_planning.py::test_creating_leaves_a_draft_of_the_user_with_its_limits`

#### C1-06 · Cambiar un borrador reemplaza su contenido entero

- **Sale de:** CA-4 · **Tipo:** unitario
- **Dado** el borrador de Lucía del 10 de noviembre al 9 de diciembre de 2026, en ARS, con un
  ingreso estimado de $1.500.000,00 y los topes Supermercado $320.000,00 y Transporte
  $90.000,00,
- **cuando** lo cambia a un período mensual que empieza el 15 de noviembre de 2026, sin fin
  indicado, en ARS, con un ingreso estimado de $1.600.000,00 y los topes Supermercado
  $350.000,00 y Salud $50.000,00,
- **entonces** el borrador va del 15 de noviembre al 14 de diciembre de 2026, con ese ingreso, y
  tiene dos topes, Supermercado $350.000,00 y Salud $50.000,00. Transporte ya no tiene tope. El
  período sigue en borrador y conserva su id.
- **Test:** `tests/unit/test_budget_planning.py::test_changing_a_draft_replaces_its_whole_content`

#### C1-07 · Confirmar un borrador no cambia nada más de él

- **Sale de:** CA-7 · **Tipo:** unitario
- **Dado** el borrador de Lucía del 10 de noviembre al 9 de diciembre de 2026, en ARS, con un
  ingreso estimado de $1.500.000,00 y los topes Supermercado $320.000,00 y Transporte
  $90.000,00,
- **cuando** lo confirma,
- **entonces** el período queda confirmado, con las mismas fechas, la misma moneda, el mismo
  ingreso y los mismos dos topes.
- **Test:** `tests/unit/test_budget_planning.py::test_confirming_a_draft_changes_nothing_else_of_it`

#### C1-08 · Confirmar uno ya confirmado no escribe nada

- **Sale de:** CA-9 · **Tipo:** unitario
- **Dado** el período actual de Lucía, ya confirmado,
- **cuando** lo confirma,
- **entonces** el caso de uso termina sin error y no pide al repositorio ninguna escritura.
- **Test:** `tests/unit/test_budget_planning.py::test_confirming_one_already_confirmed_writes_nothing`

#### C1-09 · Un gasto que cae solo en un borrador queda pendiente

- **Sale de:** CA-6 · **Tipo:** unitario
- **Dado** que el único período que cubre el 15 de noviembre de 2026 es el borrador de Lucía
  del 10 de noviembre al 9 de diciembre,
- **cuando** se resuelve un gasto interpretado de $5.000,00 en Supermercado, con "Galicia pesos"
  y fecha 15 de noviembre de 2026,
- **entonces** no se puede registrar sin preguntar: le falta la confirmación del período, y el
  gasto no se imputa al borrador.
- **Test:** `tests/unit/test_budget_period_movements.py::test_an_expense_that_falls_only_in_a_draft_stays_pending`

#### C1-10 · El mismo gasto, con el período ya confirmado, se imputa sin preguntar

- **Sale de:** CA-8 · **Tipo:** unitario
- **Dado** que el único período que cubre el 15 de noviembre de 2026 es el de Lucía del 10 de
  noviembre al 9 de diciembre, ya confirmado,
- **cuando** se resuelve el mismo gasto de C1-09,
- **entonces** se puede registrar sin preguntar, imputado a ese período.
- **Test:** `tests/unit/test_budget_period_movements.py::test_the_same_expense_with_the_period_confirmed_is_charged_without_asking`

#### C1-11 · Lucía crea el borrador del período siguiente

- **Estado:** cambiado, aprobado: comprueba la respuesta completa (pregunta abierta 8)
- **Sale de:** CA-1 y CA-2 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con `period_type` mensual, `period_start`
  2026-11-10, sin `period_end` ni `family_group_id`, `primary_currency` ARS,
  `estimated_income` 1500000 y los topes Supermercado 320000 y Transporte 90000,
- **entonces** responde `201` con el período completo, con la forma de un elemento de
  `GET /budget-periods`: su `id`, `family_group_id` y `family_group_name` nulos, `period_type`
  mensual, `period_start` 2026-11-10, `period_end` 2026-12-09, `status` `draft`,
  `primary_currency` ARS, `estimated_income` 1500000, `can_edit` verdadero, `is_current` falso y
  los topes Supermercado 320000 y Transporte 90000, cada uno con su `id`. En la base queda el
  período con `user_id` de Lucía, `family_group_id` nulo y sus dos filas de `BUDGET`.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_the_draft_of_the_next_period`

#### C1-12 · El borrador figura en la lista, con sus topes

- **Sale de:** CA-6 · **Tipo:** integración
- **Dado** Lucía con el borrador de C1-11 guardado,
- **cuando** pide `GET /budget-periods`,
- **entonces** la lista trae primero el borrador, con `status` `draft`, `can_edit` verdadero,
  `is_current` falso y los topes Supermercado 320000 y Transporte 90000, y después su período
  actual, confirmado y con `is_current` verdadero.
- **Test:** `tests/integration/test_budget_planning.py::test_the_draft_appears_in_the_list_with_its_limits`

#### C1-13 · Lucía cambia el borrador

- **Estado:** cambiado, aprobado: comprueba la respuesta completa (pregunta abierta 8)
- **Sale de:** CA-4 · **Tipo:** integración
- **Dado** Lucía con el borrador de C1-11 guardado,
- **cuando** pide `PUT /budget-periods/{period_id}` con el contenido de C1-06: mensual,
  `period_start` 2026-11-15, ARS, `estimated_income` 1600000 y los topes Supermercado 350000 y
  Salud 50000,
- **entonces** responde `200` con el período completo, con la forma de un elemento de
  `GET /budget-periods`: el mismo `id`, `period_start` 2026-11-15, `period_end` 2026-12-14,
  `status` `draft`, `estimated_income` 1600000, `can_edit` verdadero y solo los topes
  Supermercado 350000 y Salud 50000. `GET /budget-periods` trae el borrador igual.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_changes_the_draft`

#### C1-14 · Lucía confirma el borrador

- **Estado:** cambiado, aprobado: comprueba la respuesta completa (pregunta abierta 8)
- **Sale de:** CA-7 · **Tipo:** integración
- **Dado** Lucía con el borrador de C1-11 guardado,
- **cuando** pide `POST /budget-periods/{period_id}/confirm` sin cuerpo,
- **entonces** responde `200` con el período completo, con la forma de un elemento de
  `GET /budget-periods`: el mismo `id`, `status` `confirmed`, `period_start` 2026-11-10,
  `period_end` 2026-12-09, `estimated_income` 1500000, `can_edit` verdadero y los topes
  Supermercado 320000 y Transporte 90000. `GET /budget-periods` trae el período igual.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_confirms_the_draft`

#### C1-15 · Confirmarlo otra vez responde igual

- **Estado:** cambiado, aprobado: comprueba la respuesta completa (pregunta abierta 8)
- **Sale de:** CA-9 · **Tipo:** integración
- **Dado** Lucía con el período de C1-14 ya confirmado,
- **cuando** pide otra vez `POST /budget-periods/{period_id}/confirm`,
- **entonces** responde `200` con el mismo cuerpo que en C1-14, y el período sigue igual en la
  base.
- **Test:** `tests/integration/test_budget_planning.py::test_confirming_it_again_answers_the_same`

#### C1-16 · El ingreso y los topes llegan con sus centavos exactos

- **Sale de:** CA-5 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** crea un borrador mensual que empieza el 10 de noviembre de 2026, con un ingreso
  estimado de 1450000.55 y un tope de Supermercado de 300000.10, y después pide
  `GET /budget-periods`,
- **entonces** el borrador trae `estimated_income` 1450000.55 y `limit_amount` 300000.10, sin
  redondeo ni pérdida por punto flotante.
- **Test:** `tests/integration/test_budget_planning.py::test_the_income_and_the_limits_arrive_with_their_exact_cents`

#### C1-17 · Cambiar un confirmado cambia su ingreso y sus topes, y nada más

- **Estado:** nuevo, aprobado
- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** el período actual de Lucía, confirmado, del 10 de octubre al 9 de noviembre de 2026,
  en ARS, con un ingreso estimado de $1.450.000,00 y los topes Supermercado $300.000,00 y
  Transporte $80.000,00,
- **cuando** lo cambia con las mismas fechas y la misma moneda, un ingreso estimado de
  $1.520.000,00 y los topes Supermercado $310.000,00 y Salud $40.000,00,
- **entonces** el período sigue confirmado, del 10 de octubre al 9 de noviembre de 2026 y en
  ARS, con ese ingreso, y tiene dos topes, Supermercado $310.000,00 y Salud $40.000,00.
  Transporte ya no tiene tope.
- **Test:** `tests/unit/test_budget_planning.py::test_changing_a_confirmed_one_changes_its_income_and_its_limits_and_nothing_else`

#### C1-18 · Lucía les pone otro ingreso y otros topes a su período actual

- **Estado:** nuevo, aprobado
- **Sale de:** CA-10 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta y su período actual guardado, confirmado,
- **cuando** pide `PUT /budget-periods/{period_id}` con el contenido de C1-17: mensual,
  `period_start` 2026-10-10, `period_end` 2026-11-09, ARS, `estimated_income` 1520000 y los
  topes Supermercado 310000 y Salud 40000,
- **entonces** responde `200`, y `GET /budget-periods` trae ese período con `status`
  `confirmed`, las mismas fechas, ese ingreso y solo esos dos topes.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_puts_another_income_and_other_limits_on_her_current_period`

#### C1-19 · Un quincenal termina el día indicado

- **Estado:** nuevo, aprobado
- **Sale de:** CA-11 · **Tipo:** unitario
- **Dado** un período quincenal que empieza el 10 de noviembre de 2026, con el fin indicado el 24
  de noviembre de 2026,
- **cuando** se calcula su fin,
- **entonces** es el 24 de noviembre de 2026, el que indicó el usuario.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_biweekly_one_ends_on_the_day_given`

#### C1-20 · Lucía ve sus categorías de gasto, base y propias, por nombre

- **Estado:** nuevo, aprobado
- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta, con una categoría propia de gasto, "clases de inglés", en
  minúscula, y una propia de ingreso, "Clases particulares",
- **cuando** pide `GET /categories`,
- **entonces** responde `200` con las quince categorías de gasto de uso diario del catálogo base
  y las seis especiales de gasto, veintiuna en total, con `is_base` verdadero, y "clases de inglés", con `is_base`
  falso, todas por nombre sin distinguir mayúsculas: "clases de inglés" va entre "Aporte a la
  actividad" y "Comida afuera y delivery". No trae "Clases particulares" ni ninguna categoría de
  ingreso.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_sees_her_expense_categories_base_and_own_by_name`

#### C1-21 · Las categorías propias de otro usuario no aparecen

- **Estado:** nuevo, aprobado
- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta, sin categorías propias, y Pablo con una categoría propia
  de gasto, "Kiosco",
- **cuando** Lucía pide `GET /categories`,
- **entonces** la lista no trae "Kiosco": trae solo las del catálogo base.
- **Test:** `tests/integration/test_budget_planning.py::test_the_own_categories_of_another_user_do_not_appear`

### Corte 2 — errores y estado vacío

- **Aprobado por:** pendiente

Entran las validaciones de [la API](../../04-api.md), en su orden: el período de otro usuario,
`404`; el período de un grupo para un miembro que no es el dueño, `403`
(CA-16); la superposición con otro período del mismo dueño,
`409`; cambiar las fechas o la moneda de un período confirmado, `409` con
`confirmed_period_fixed` (CA-10); un período quincenal sin fin, `422` con `period_end_required`
(CA-11); un tope sobre una categoría de ingreso, `422` con `budget_category_not_expense`
(CA-14); un ingreso estimado negativo, `422` con `estimated_income_negative` (CA-15), y el `CHECK` que
lo impide en la base, en una migración nueva (AGENTS.md § 8); y fechas
invertidas, un tope menor o igual a cero o
una categoría repetida, `422`. También la categoría de otro usuario, `404`, y los estados vacío
y de error de la pantalla.

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

## Estados de pantalla

Los detalla el [contrato de UI](ui_contract.md).

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | Se abre el formulario, o se guarda o se confirma | Lo dice, sin el formulario editable |
| Con contenido | Llegaron las categorías y, al editar, el borrador | El formulario, con el botón de guardar y, en un borrador guardado, el de confirmar |
| Vacío | No aplica: el formulario siempre tiene algo que mostrar, porque el catálogo base de categorías nunca está vacío | — |
| Error | La API responde con un error, no responde a tiempo o no se llega a ella | Qué falló, sin perder lo que el usuario cargó, y reintentar |

## Mensajes al usuario

No hay mensajes por WhatsApp: armar y confirmar es del dashboard. Los textos de la pantalla van
en `frontend/src/messages.ts`.

## Reglas de dominio bajo prueba

| Regla | Caso que la cubre |
|---|---|
| Solo un período confirmado recibe movimientos ([§ 3](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)) | C1-09 |
| Con un solo período posible y confirmado no se pregunta ([§ 1](../../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)) | C1-10 |
| Montos en `Decimal`, nunca `float` ([`AGENTS.md` § 5](../../../AGENTS.md#5-invariantes-que-un-asistente-rompe-por-defecto)) | C1-16 |
| Los períodos de un mismo dueño no se solapan ([§ 3](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)) | Corte 2 |

## Sin cubrir

- Que la moneda de un período confirmado no cambie lo impone además un trigger de la base desde
  la migración del esquema. El caso de la API que lo rechaza, con `confirmed_period_fixed`, es
  del corte 2.

## Fuera de alcance

- El borrador que se arma solo, el recordatorio antes del inicio y los montos de las reglas
  recurrentes al confirmar: son de una segunda versión.
- Confirmar por WhatsApp.

## Preguntas abiertas

1. ~~¿Se pueden cambiar el ingreso y los topes de un período ya confirmado?~~ Resuelta el 29
   de octubre de 2026: sí, el ingreso estimado y los topes, pero no sus fechas ni su moneda
   (CA-10). Las reglas de dominio § 3 dicen que el primer período nace confirmado y sin topes,
   y que se le ponen desde el dashboard, y [la API](../../04-api.md) respondía `409` a todo
   `PUT` sobre un confirmado. Se corrigió la API, se aclaró § 3, y se sumaron C1-17 y C1-18.
2. ~~Cuándo termina un mensual que empieza un día que el mes siguiente no tiene.~~ Resuelta el
   29 de octubre de 2026: uno que empieza el 31 de enero termina el 27 de febrero, el día
   anterior al 28, y el siguiente empieza el 28 de febrero, igual que la regla recurrente del 31.
   La regla de § 3 admitía también el 28 de febrero, y se aclaró con este ejemplo (C1-03).
   Se acepta el corrimiento que dan las reglas: el período siguiente termina el 27 de marzo y
   el ciclo sigue el 28, porque no se guarda el día de inicio elegido. Decidido el 29 de octubre
   de 2026; si se guarda queda en la [hoja de ruta](../../hoja-de-ruta.md#entrega-2), para cuando
   llegue el borrador que se arma solo.
3. ~~Cuánto dura un período quincenal.~~ Resuelta el 29 de octubre de 2026: su fin no se
   calcula, y el pedido lo trae siempre (CA-11). Sin él responde `422` con
   `period_end_required`, que es del corte 2. Quedó en [la API](../../04-api.md), y se sumó
   C1-19.
4. ~~De dónde salen las categorías del formulario.~~ Resuelta el 29 de octubre de 2026: de
   `GET /categories`, que se sumó a [la API](../../04-api.md) en este corte (CA-12, C1-20 y
   C1-21). Su `401` es del corte 2. Al implementarlo, sus textos van en `reference.py`.
5. ~~¿Un tope sobre una categoría de ingreso?~~ Resuelta el 29 de octubre de 2026: no, responde
   `422` con `budget_category_not_expense` (CA-14), en `POST` y en `PUT`. Su caso es del corte 2.
6. ~~¿Un ingreso estimado negativo?~~ Resuelta el 29 de octubre de 2026: no, el ingreso es 0 o
   más y uno negativo responde `422` con `estimated_income_negative` (CA-15), en `POST` y en
   `PUT`. Su caso es del corte 2. El primer período nace con 0, no vacío: la columna es
   `NOT NULL DEFAULT 0`. La base no tiene un `CHECK` que impida un ingreso negativo.
7. ~~¿Entran los períodos de grupo?~~ Resuelta el 29 de octubre de 2026: cambiar y confirmar
   un período lo hace solo su dueño, con `period_access.can_edit`, y un miembro que no lo es
   recibe `403` (CA-16), que es del corte 2. Crear un período de grupo desde el dashboard sigue
   afuera. El contrato de `POST /budget-periods` ya admite `family_group_id`, con el `403` del
   miembro: no se amplió ni se recortó, y queda sin implementar en esta funcionalidad.
8. ~~Qué responden `POST` y `PUT /budget-periods/{period_id}`.~~ Resuelta el 29 de octubre de
   2026: `201` y `200`, los dos con el período completo, con la misma forma que cada elemento de
   `GET /budget-periods`, porque la pantalla suma o reemplaza ese período en su lista sin otra
   llamada. Confirmar responde `200` con el mismo cuerpo, también si ya estaba confirmado.
   Quedó en [la API](../../04-api.md), y cambiaron C1-11, C1-13, C1-14 y C1-15.
9. ~~El `409` de confirmar.~~ Resuelta el 29 de octubre de 2026: se quitó de
   [la API](../../04-api.md). Las restricciones de exclusión de `budget_period` comparan las
   fechas de todo período del mismo dueño, sin mirar su estado, así que un borrador nunca se
   superpone con otro período y confirmarlo no puede chocar.
