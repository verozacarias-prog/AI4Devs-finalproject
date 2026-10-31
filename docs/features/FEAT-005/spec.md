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

- **CA-10.** En un período confirmado, el usuario cambia el ingreso estimado y los topes, con las mismas reglas que en un borrador. Su cadencia, sus fechas y su moneda no cambian, y el período sigue confirmado.

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

- **Aprobado por:** Veronica Zacarias 30/10/2026

Entran las validaciones de [la API](../../04-api.md), en su orden: el período de otro usuario,
`404`; el período de un grupo para un miembro que no es el dueño, `403`
(CA-16); la superposición con otro período del mismo dueño,
`409` con `budget_period_overlap`; cambiar la cadencia, las fechas o la moneda de un período
confirmado, `409` con `confirmed_period_fixed` (CA-10); un período quincenal sin fin, `422` con `period_end_required`
(CA-11); un tope sobre una categoría de ingreso, `422` con `budget_category_not_expense`
(CA-14); un ingreso estimado negativo, `422` con `estimated_income_negative` (CA-15), y el `CHECK` que
lo impide en la base, en una migración nueva (AGENTS.md § 8); y los tres `422` de fechas
invertidas, tope de cero o menos y categoría repetida, con su código cada uno (pregunta abierta 11).
También la categoría de otro usuario, `404`; un campo que la API
no conoce, `422` en vez de ignorarlo, y `family_group_id`, `422` con
`group_period_not_supported`; y los estados vacío y de error de la pantalla. El `404` del período de otro usuario, en
`PUT` y en la confirmación, el `403`, los dos `409` de arriba, el `422` con
`period_end_required`, el `404` de la categoría ajena y el `422` del campo desconocido no están
en el corte 1: entran acá, con sus tests primero (ADR 0024). Hasta entonces, un tope sobre una
categoría que no existe termina en `500`, porque la base rechaza la referencia, y lo cubre el
`404` de la categoría ajena. Decidido por Vero el 30 de octubre de 2026.

- **Total:** 29 casos, 9 unitarios y 20 de integración, sin aprobar. Además de los datos de
  arriba, Pablo es el dueño del grupo "Casa" y Sofía es miembro, sin serlo; el grupo tiene un
  período confirmado del 10 de octubre al 9 de noviembre de 2026 y un borrador del 10 de
  noviembre al 9 de diciembre. Pablo tiene un período propio del 10 de octubre al 9 de noviembre
  y una categoría propia de gasto, "Kiosco". Lucía tiene la categoría propia de ingreso "Clases
  particulares". En cada error, nada de lo que el pedido trae queda guardado. Los casos de
  componente de la pantalla (#74) se proponen cuando esté armada: todavía no existe.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C2-01 | Cambiar o confirmar un período que no existe responde que no existe | Unitario | Validación 2 |
| C2-02 | Lucía cambia el período de Pablo | Integración | Validación 2 |
| C2-03 | Lucía confirma un período de Pablo | Integración | Validación 2 |
| C2-04 | Un miembro que no es el dueño no cambia ni confirma el período del grupo | Unitario | CA-16 |
| C2-05 | Sofía cambia el período confirmado de "Casa" | Integración | CA-16 |
| C2-06 | Sofía confirma el borrador de "Casa" | Integración | CA-16 |
| C2-07 | En un confirmado, cambiar la cadencia, el inicio, el fin o la moneda no se guarda | Unitario | CA-10 |
| C2-08 | Lucía le cambia la moneda a su período actual | Integración | CA-10 |
| C2-09 | Un período que se superpone con otro del mismo dueño no se guarda | Unitario | Validación 6 |
| C2-10 | Lucía crea un período que empieza dentro del actual | Integración | Validación 6 |
| C2-11 | Lucía mueve un borrador sobre su período actual | Integración | Validación 6 |
| C2-12 | Un quincenal sin fin no tiene fin | Unitario | CA-11 |
| C2-13 | Lucía crea un quincenal sin `period_end` | Integración | CA-11 |
| C2-14 | Fechas invertidas, un tope de cero o menos y una categoría repetida no se guardan | Unitario | Validaciones 4 y 7 |
| C2-15 | Lucía crea un período con un tope de 0 | Integración | Validación 7 |
| C2-16 | Un tope sobre una categoría de ingreso no se guarda | Unitario | CA-14 |
| C2-17 | Lucía le pone un tope a "Clases particulares" | Integración | CA-14 |
| C2-18 | Un ingreso estimado negativo no se guarda, y uno de 0 sí | Unitario | CA-15 |
| C2-19 | Lucía crea un período con un ingreso de -1 | Integración | CA-15 |
| C2-20 | La base rechaza un ingreso estimado negativo | Integración | CA-15 |
| C2-21 | Lucía le pone un tope a "Kiosco", la categoría de Pablo | Integración | CA-12 |
| C2-22 | Lucía le pone un tope a una categoría que no existe | Integración | CA-12 |
| C2-23 | Lucía crea un período con `family_group_id` | Integración | Pregunta abierta 7 |
| C2-24 | Sin sesión, armar, cambiar, confirmar y ver las categorías responden `401` | Integración | La API |
| C2-25 | Con dos errores a la vez, responde el primero del orden | Unitario | Validaciones, en orden |
| C2-26 | Pablo, el dueño, cambia y confirma el borrador de "Casa" | Integración | CA-16 |
| C2-27 | Pablo crea un período propio con las fechas del borrador de "Casa" | Integración | Validación 6 |
| C2-28 | Un campo que la API no conoce no se guarda ni se ignora | Integración | La API |
| C2-29 | Lucía cambia y confirma con un `period_id` que no es un UUID | Integración | La API |

#### C2-01 · Cambiar o confirmar un período que no existe responde que no existe

- **Sale de:** validación 2 de [la API](../../04-api.md) · **Tipo:** unitario
- **Dado** un identificador que no es de ningún período,
- **cuando** se cambia o se confirma ese período,
- **entonces** el caso de uso dice que no existe, con `not_found`, y no escribe nada.
- **Test:** `tests/unit/test_budget_planning.py::test_changing_or_confirming_a_period_that_does_not_exist_says_it_does_not_exist`

#### C2-02 · Lucía cambia el período de Pablo

- **Sale de:** validación 2 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta y el período propio de Pablo guardado,
- **cuando** pide `PUT /budget-periods/{period_id}` sobre él, con otro ingreso,
- **entonces** responde `404` con `not_found`, y el período de Pablo sigue igual.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_changes_the_period_of_pablo`

#### C2-03 · Lucía confirma un período de Pablo

- **Sale de:** validación 2 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta y un borrador propio de Pablo guardado,
- **cuando** pide `POST /budget-periods/{period_id}/confirm` sobre él,
- **entonces** responde `404` con `not_found`, y el período sigue en borrador.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_confirms_a_period_of_pablo`

#### C2-04 · Un miembro que no es el dueño no cambia ni confirma el período del grupo

- **Sale de:** CA-16 · **Tipo:** unitario
- **Dado** Sofía, miembro de "Casa" sin ser su dueña, y el borrador del grupo,
- **cuando** lo cambia o lo confirma,
- **entonces** el caso de uso lo rechaza con `not_the_owner`, y no escribe nada.
- **Test:** `tests/unit/test_budget_planning.py::test_a_member_who_is_not_the_owner_neither_changes_nor_confirms_the_period_of_the_group`

#### C2-05 · Sofía cambia el período confirmado de "Casa"

- **Sale de:** CA-16 · **Tipo:** integración
- **Dado** Sofía con su sesión abierta,
- **cuando** pide `PUT /budget-periods/{period_id}` sobre el período confirmado de "Casa", con
  sus mismas fechas y moneda y otro ingreso,
- **entonces** responde `403` con `not_the_owner`, y el período sigue igual.
- **Test:** `tests/integration/test_budget_planning.py::test_sofia_changes_the_confirmed_period_of_casa`

#### C2-06 · Sofía confirma el borrador de "Casa"

- **Sale de:** CA-16 · **Tipo:** integración
- **Dado** Sofía con su sesión abierta,
- **cuando** pide `POST /budget-periods/{period_id}/confirm` sobre el borrador de "Casa",
- **entonces** responde `403` con `not_the_owner`, y el período sigue en borrador.
- **Test:** `tests/integration/test_budget_planning.py::test_sofia_confirms_the_draft_of_casa`

#### C2-07 · En un confirmado, cambiar la cadencia, el inicio, el fin o la moneda no se guarda

- **Sale de:** CA-10 · **Tipo:** unitario
- **Dado** el período actual de Lucía, confirmado y mensual,
- **cuando** se cambia a quincenal con sus mismas fechas, con otro `period_start`, con otro
  `period_end` o con otra moneda, cada uno por separado,
- **entonces** el caso de uso lo rechaza con `confirmed_period_fixed`, y no escribe nada.
- **Test:** `tests/unit/test_budget_planning.py::test_in_a_confirmed_period_changing_the_cadence_the_start_the_end_or_the_currency_is_not_saved`

#### C2-08 · Lucía le cambia la moneda a su período actual

- **Sale de:** CA-10 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `PUT /budget-periods/{period_id}` sobre su período actual con sus mismas
  fechas y `primary_currency` USD,
- **entonces** responde `409` con `confirmed_period_fixed`, y el período sigue en ARS, con su
  ingreso y sus topes.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_changes_the_currency_of_her_current_period`

#### C2-09 · Un período que se superpone con otro del mismo dueño no se guarda

- **Sale de:** validación 6 · **Tipo:** unitario
- **Dado** el período actual de Lucía, del 10 de octubre al 9 de noviembre de 2026,
- **cuando** se crea un mensual que empieza el 1 de noviembre,
- **entonces** el caso de uso lo rechaza con `budget_period_overlap`, y no escribe nada. Uno que
  empieza el 10 de noviembre, el día después, sí se guarda.
- **Test:** `tests/unit/test_budget_planning.py::test_a_period_that_overlaps_another_of_the_same_owner_is_not_saved`

#### C2-10 · Lucía crea un período que empieza dentro del actual

- **Sale de:** validación 6 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con un mensual que empieza el 1 de noviembre de 2026,
- **entonces** responde `409` con `budget_period_overlap`, y no se guarda ningún período nuevo.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_a_period_that_starts_inside_the_current_one`

#### C2-11 · Lucía mueve un borrador sobre su período actual

- **Sale de:** validación 6 · **Tipo:** integración
- **Dado** Lucía con el borrador de C1-11 guardado,
- **cuando** pide `PUT /budget-periods/{period_id}` sobre él con `period_start` 2026-11-01,
- **entonces** responde `409` con `budget_period_overlap`, y el borrador sigue del 10 de
  noviembre al 9 de diciembre.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_moves_a_draft_over_her_current_period`

#### C2-12 · Un quincenal sin fin no tiene fin

- **Sale de:** CA-11 · **Tipo:** unitario
- **Dado** un período quincenal que empieza el 10 de noviembre de 2026, sin fin indicado,
- **cuando** se calcula su fin,
- **entonces** no se calcula: falla con `period_end_required`.
- **Test:** `tests/unit/test_budget_period_end.py::test_a_biweekly_period_without_an_end_has_no_end`

#### C2-13 · Lucía crea un quincenal sin `period_end`

- **Sale de:** CA-11 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con `period_type` quincenal, `period_start` 2026-11-10 y
  sin `period_end`,
- **entonces** responde `422` con `period_end_required`, y no se guarda ningún período.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_a_biweekly_period_without_period_end`

#### C2-14 · Fechas invertidas, un tope de cero o menos y una categoría repetida no se guardan

- **Sale de:** validaciones 4 y 7 · **Tipo:** unitario
- **Dado** Lucía,
- **cuando** se crea un período con el fin antes del inicio, con un tope de 0, con uno de -1, o
  con dos topes sobre Supermercado, cada uno por separado,
- **entonces** el caso de uso lo rechaza con `period_dates_inverted`, `budget_limit_not_positive`
  o `budget_category_repeated`, y no escribe nada.
- **Test:** `tests/unit/test_budget_planning.py::test_inverted_dates_a_limit_of_zero_or_less_and_a_repeated_category_are_not_saved`

#### C2-15 · Lucía crea un período con un tope de 0

- **Sale de:** validación 7 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con el contenido de C1-11 y el tope de Transporte en 0,
- **entonces** responde `422` con `budget_limit_not_positive`, y no se guarda ningún período.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_a_period_with_a_limit_of_zero`

#### C2-16 · Un tope sobre una categoría de ingreso no se guarda

- **Sale de:** CA-14 · **Tipo:** unitario
- **Dado** Lucía, con su categoría de ingreso "Clases particulares",
- **cuando** se crea o se cambia un período con un tope sobre ella,
- **entonces** el caso de uso lo rechaza con `budget_category_not_expense`, y no escribe nada.
- **Test:** `tests/unit/test_budget_planning.py::test_a_limit_on_an_income_category_is_not_saved`

#### C2-17 · Lucía le pone un tope a "Clases particulares"

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** Lucía con el borrador de C1-11 guardado,
- **cuando** pide `PUT /budget-periods/{period_id}` con un tope de 10000 sobre "Clases
  particulares",
- **entonces** responde `422` con `budget_category_not_expense`, y el borrador sigue con sus
  topes.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_puts_a_limit_on_clases_particulares`

#### C2-18 · Un ingreso estimado negativo no se guarda, y uno de 0 sí

- **Sale de:** CA-15 · **Tipo:** unitario
- **Dado** Lucía,
- **cuando** se crea un período con `estimated_income` -0.01, y otro con 0,
- **entonces** el primero se rechaza con `estimated_income_negative` sin escribir nada, y el
  segundo queda guardado con ingreso 0.
- **Test:** `tests/unit/test_budget_planning.py::test_a_negative_estimated_income_is_not_saved_and_one_of_zero_is`

#### C2-19 · Lucía crea un período con un ingreso de -1

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con el contenido de C1-11 y `estimated_income` -1,
- **entonces** responde `422` con `estimated_income_negative`, y no se guarda ningún período.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_a_period_with_an_income_of_minus_one`

#### C2-20 · La base rechaza un ingreso estimado negativo

- **Sale de:** CA-15 y [AGENTS.md § 8](../../../AGENTS.md#8-base-de-datos) · **Tipo:** integración
- **Dado** la base con la migración nueva aplicada,
- **cuando** se inserta directo un período con `estimated_income` -1, sin pasar por la API,
- **entonces** la base lo rechaza por su `CHECK`.
- **Test:** `tests/integration/test_budget_planning.py::test_the_database_rejects_a_negative_estimated_income`

#### C2-21 · Lucía le pone un tope a "Kiosco", la categoría de Pablo

- **Sale de:** CA-12 y [AGENTS.md § 7](../../../AGENTS.md#7-seguridad) · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con el contenido de C1-11 y un tope sobre "Kiosco",
- **entonces** responde `404` con `not_found`, y no se guarda ningún período.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_puts_a_limit_on_kiosco_the_category_of_pablo`

#### C2-22 · Lucía le pone un tope a una categoría que no existe

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con el contenido de C1-11 y un tope sobre un
  identificador que no es de ninguna categoría,
- **entonces** responde `404` con `not_found`, y no `500`, y no se guarda ningún período.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_puts_a_limit_on_a_category_that_does_not_exist`

#### C2-23 · Lucía crea un período con `family_group_id`

- **Sale de:** [pregunta abierta 7](#preguntas-abiertas) · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `POST /budget-periods` con el contenido de C1-11 y un `family_group_id`,
- **entonces** responde `422` con `group_period_not_supported`, y no se guarda ningún período:
  crear uno de grupo llega con los grupos, en la segunda versión.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_creates_a_period_with_family_group_id`

#### C2-24 · Sin sesión, armar, cambiar, confirmar y ver las categorías responden `401`

- **Sale de:** [la API](../../04-api.md) · **Tipo:** integración
- **Dado** un pedido sin sesión, desde la página de la API,
- **cuando** pide `POST /budget-periods`, `PUT /budget-periods/{period_id}`,
  `POST /budget-periods/{period_id}/confirm` o `GET /categories`, cada uno por separado,
- **entonces** cada uno responde `401` con `unauthorized`, y no se guarda nada.
- **Test:** `tests/integration/test_budget_planning.py::test_without_a_session_building_changing_confirming_and_listing_categories_answer_401`

#### C2-25 · Con dos errores a la vez, responde el primero del orden

- **Sale de:** "Validaciones, en este orden" de [la API](../../04-api.md) · **Tipo:** unitario
- **Dado** Sofía y el período confirmado de "Casa",
- **cuando** lo cambia con otra moneda, y Lucía crea un período que se superpone con el actual
  y tiene un tope de 0,
- **entonces** a Sofía se le responde `not_the_owner` y no `confirmed_period_fixed`, y a Lucía
  `budget_period_overlap` y no `budget_limit_not_positive`.
- **Test:** `tests/unit/test_budget_planning.py::test_with_two_errors_at_once_the_first_of_the_order_answers`

#### C2-26 · Pablo, el dueño, cambia y confirma el borrador de "Casa"

- **Sale de:** [CA-16](#criterios-de-aceptación) · **Tipo:** integración
- **Dado** Pablo, dueño de "Casa", con su sesión abierta, y el borrador del grupo,
- **cuando** pide `PUT /budget-periods/{period_id}` con otro ingreso estimado y después
  `POST /budget-periods/{period_id}/confirm`,
- **entonces** los dos responden `200`, y el período queda con el ingreso nuevo y `confirmed`.
- **Test:** `tests/integration/test_budget_planning.py::test_pablo_the_owner_changes_and_confirms_the_draft_of_casa`

#### C2-27 · Pablo crea un período propio con las fechas del borrador de "Casa"

- **Sale de:** validación 6 de [la API](../../04-api.md) · **Tipo:** integración
- **Dado** Pablo con su sesión abierta, y el borrador de "Casa" del 10 de noviembre al 9 de
  diciembre de 2026,
- **cuando** pide `POST /budget-periods` con un período propio de esas mismas fechas,
- **entonces** responde `201` y el período queda guardado: los períodos no se solapan por dueño, y
  el del grupo tiene otro dueño que el suyo individual.
- **Test:** `tests/integration/test_budget_planning.py::test_pablo_creates_an_own_period_with_the_dates_of_the_draft_of_casa`

#### C2-28 · Un campo que la API no conoce no se guarda ni se ignora

- **Sale de:** [la API](../../04-api.md) · **Tipo:** integración
- **Dado** Lucía con su sesión abierta y su borrador de C1-11,
- **cuando** pide `POST /budget-periods` con un campo que la API no conoce, o
  `PUT /budget-periods/{period_id}` con un `family_group_id`, cada uno por separado,
- **entonces** cada uno responde `422` con `invalid_request`, no se crea ningún período y el
  borrador no cambia.
- **Test:** `tests/integration/test_budget_planning.py::test_a_field_the_api_does_not_know_is_neither_saved_nor_ignored`

#### C2-29 · Lucía cambia y confirma con un `period_id` que no es un UUID

- **Sale de:** [la API](../../04-api.md) · **Tipo:** integración
- **Dado** Lucía con su sesión abierta,
- **cuando** pide `PUT /budget-periods/{period_id}` y `POST /budget-periods/{period_id}/confirm`
  con un `period_id` que no es un UUID, cada uno por separado,
- **entonces** cada uno responde `422` con `invalid_request`.
- **Test:** `tests/integration/test_budget_planning.py::test_lucia_changes_and_confirms_with_a_period_id_that_is_not_a_uuid`

Se resuelve en la [HU5](../../05-historias-de-usuario.md), porque hoy nada escribe en `sent_alert`:
un tope que un `PUT` deja afuera se borra, y si ya tiene alertas enviadas la referencia de
`sent_alert` a `budget` impide borrarlo. Decidido por Vero el 31 de octubre de 2026.

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

## Estados de pantalla

Los detalla el [contrato de UI](ui_contract.md).

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | Se abre el formulario, o se guarda o se confirma | Lo dice, sin el formulario editable |
| Con contenido | Llegaron las categorías y, al editar, el borrador | El formulario, con el botón de guardar y, en un borrador guardado, el de confirmar |
| Vacío | `GET /categories` responde sin ninguna categoría de gasto | En lugar de la lista de topes, que no hay categorías de gasto para ponerles tope. El resto del formulario sigue disponible, y el período se puede guardar sin topes. Decidido por Vero el 31 de octubre de 2026 |
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
   afuera. Resuelto el 30 de octubre de 2026: un `POST /budget-periods` con `family_group_id`
   responde `422` con `group_period_not_supported` (C2-23), y [la API](../../04-api.md) se
   corrigió para decir lo mismo. Crear un período de grupo llega con los grupos, en la segunda
   versión.
8. ~~Qué responden `POST` y `PUT /budget-periods/{period_id}`.~~ Resuelta el 29 de octubre de
   2026: `201` y `200`, los dos con el período completo, con la misma forma que cada elemento de
   `GET /budget-periods`, porque la pantalla suma o reemplaza ese período en su lista sin otra
   llamada. Confirmar responde `200` con el mismo cuerpo, también si ya estaba confirmado.
   Quedó en [la API](../../04-api.md), y cambiaron C1-11, C1-13, C1-14 y C1-15.
9. ~~El `409` de confirmar.~~ Resuelta el 29 de octubre de 2026: se quitó de
   [la API](../../04-api.md). Las restricciones de exclusión de `budget_period` comparan las
   fechas de todo período del mismo dueño, sin mirar su estado, así que un borrador nunca se
   superpone con otro período y confirmarlo no puede chocar.
10. ~~El código del `409` por superposición.~~ Resuelta el 30 de octubre de 2026: un período que
    se superpone con otro del mismo dueño, al crearlo o al cambiarlo, responde `409` con
    `budget_period_overlap` (C2-09 a C2-11), y quedó en [la API](../../04-api.md).
11. ~~Los códigos de los `422` de fechas invertidas, tope de cero o menos y categoría repetida.~~
    Resuelta el 30 de octubre de 2026: cada uno lleva el suyo, `period_dates_inverted`,
    `budget_limit_not_positive` y `budget_category_repeated` (C2-14 y C2-15), para que la
    pantalla marque el campo que falló, y quedaron en [la API](../../04-api.md).
12. ~~El orden de las validaciones de fechas.~~ Resuelta el 31 de octubre de 2026: el fin que falta
    y las fechas invertidas van antes de comparar las fechas de un confirmado y de la
    superposición, porque sin un fin válido no se pueden comparar. `family_group_id` va primero, y
    la categoría ajena, junto a los demás errores de los topes. Quedó en [la API](../../04-api.md).
13. ~~¿Se puede cambiar la cadencia de un período confirmado?~~ Resuelta el 31 de octubre de 2026:
    no, responde `409` con `confirmed_period_fixed`, porque
    [§ 3](../../reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)
    dice que un confirmado cambia solo el ingreso estimado y los topes (CA-10 y C2-07). Quedó en
    [la API](../../04-api.md).
