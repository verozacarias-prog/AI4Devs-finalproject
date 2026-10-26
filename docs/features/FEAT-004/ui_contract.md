# Contrato de UI — FEAT-004 · Pantalla de presupuesto

- **Historia de usuario:** [HU4](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)
- **Se escribe:** antes de la pantalla del corte 1, junto con sus casos de componente.

Sigue la forma del [contrato de la pantalla de cuentas](../FEAT-001/ui_contract.md).

## Componentes

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|
| `Card` y `CardTitle` de shadcn/ui | Existen, desde el [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md) | El marco de la pantalla, como en la de cuentas: una sección que un lector de pantalla anuncia como "Tu presupuesto" |
| `Button` de shadcn/ui | Existe, desde el ADR 0027 | Reintentar, abrir el detalle de una categoría con tope y volver al resumen |
| Selector de período | Nuevo, en `BudgetPage`, sobre un `select` nativo | Elegir el período. Es nativo porque shadcn/ui no tiene uno instalado y sumarlo trae una librería nueva; el nativo ya se opera con teclado y anuncia su opción |
| Línea de estado (`role="status"`) | Existe, como en la pantalla de cuentas | Anuncia la carga; el vacío sin períodos es un título (C3-05) |
| Alerta de error (`role="alert"`) | Existe, como en la pantalla de cuentas | El estado de error |
| Aviso de borrador | Nuevo, en `BudgetPage` | Dice que el período elegido está en borrador y falta confirmarlo |
| Barra de una categoría | Nuevo, en `BudgetPage` | Lo gastado sobre el tope, con tres estados: normal, cerca del tope y excedida. Llena hasta el 100 %, aunque el porcentaje lo pase, y vacía si es negativo |
| Fila de una categoría sin tope | Nuevo, en `BudgetPage` | El nombre, lo gastado y "Sin tope" en gris, sin barra ni porcentaje, y sin detalle |
| Lista de movimientos del detalle | Nuevo, en `BudgetPage` | Cada movimiento en una fila, con una etiqueta para su tipo y otra para su origen. Lo que pesa en el tope y la cotización aparecen solo si hubo conversión: si no, lo que pesa es su monto |

## Tokens del Design System

Salen de `frontend/src/design-tokens.css`, con las excepciones que admite el
[ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md).

| Uso | Token |
|---|---|
| Tarjeta, título y listas | Los mismos que la pantalla de cuentas: `--color-card`, `--color-card-foreground`, `--color-border`, `--radius-xl`, `--radius-lg`, `--shadow-sm`, `--text-xl`, `--font-weight-semibold`, `--spacing` |
| Fondo de una barra | `--color-muted` |
| Barra normal | `--color-primary` |
| Barra cerca del tope y aviso de borrador | `--color-warning`, **nuevo**: el tema no tiene un color de advertencia, y ni el de error ni el de éxito dicen "cuidado" |
| Barra excedida, en rojo y llena, y monto negativo | `--color-destructive` |
| Etiquetas de tipo y origen, y textos secundarios | `--color-muted-foreground`, `--color-muted`, `--text-xs` |
| Foco del teclado | `--color-ring`, `--focus-ring-width` |

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre la pantalla, se elige otro período, se abre un detalle o se aprieta Reintentar | "Consultando tu presupuesto…", sin montos ni barras | Llega la respuesta, o falla |
| Con contenido: resumen | Llegaron los períodos y el resumen del elegido | El selector, el aviso si es un borrador, los ingresos, el total gastado y una fila por categoría | Elegir otro período, o una categoría con tope |
| Con contenido: detalle | Se eligió una categoría con tope y llegó su detalle | El tope, lo gastado, el porcentaje y los movimientos | "Volver al resumen", al mismo período |
| Vacío: sin períodos | `GET /budget-periods` trae la lista vacía | "Todavía no tenés un presupuesto" y qué va a ver cuando arme uno, sin selector ni alerta | — |
| Vacío: período sin topes ni gastos | El resumen del elegido no trae categorías | "Este período todavía no tiene topes ni gastos" y que los gastos se cuentan por el chat, sin alerta; el selector sigue a la vista. Los tres montos se muestran si alguno no es cero, como un ingreso estimado cargado sin topes | Elegir otro período |
| Error | La API responde con un error, no responde a tiempo o no se llega a ella, en cualquiera de las consultas | "No se pudo consultar tu presupuesto", la causa y Reintentar, sin ningún monto | Reintentar vuelve a Cargando y repite solo la consulta que falló |

Qué período se abre está en la [decisión 8 de la especificación](spec.md#decisiones-tomadas-al-especificar).
Sin sesión no es un estado de esta pantalla: como en la de cuentas, un `401` vuelve a la entrada.

## Datos que consume

- [`GET /budget-periods`](../../04-api.md): de cada período usa `id`, `family_group_name`,
  `period_start`, `period_end`, `status` e `is_current`. No usa `can_edit`, porque editar es de
  la HU2.
- `GET /budget-periods/{period_id}/summary`: `estimated_income`, `actual_income`, `total_spent`,
  `primary_currency` y, de cada categoría, `category`, `budget_id`, `limit_amount`,
  `spent_amount` y `used_percentage`.
- `GET /budgets/{budget_id}`: el tope, lo gastado, el porcentaje y los movimientos con todos sus
  campos.

La pantalla no suma, no convierte y no redondea: muestra cada monto y cada porcentaje tal como
llega. Lo único que calcula es el estado de la barra, con los umbrales de `src/constants.ts`.

## Accesibilidad

- [x] Todo control tiene nombre accesible: el selector "Período", el botón de cada categoría con
  tope, Volver y Reintentar, todos nativos (C3-02).
- [x] El contraste cumple el mínimo de WCAG AA: 4,5:1 para el texto y 3:1 para las barras. Se
  calculó cada color contra su fondo. El texto más bajo es el error en rojo sobre la tarjeta, con
  5,37:1, y la barra más baja es la de cerca del tope contra el fondo de la barra, con 3,39:1: el
  ámbar se oscureció en el corte 3, porque el anterior daba 2,07:1.
- [x] La pantalla se puede operar sólo con teclado: el selector y los botones son nativos y Tab
  llega a todos (C3-02).
- [x] Las barras anuncian su porcentaje, y su estado no se dice solo con el color: cada una es un
  medidor con el nombre de su categoría, que se lee "85,0 %, cerca del tope", y al lado se
  escriben el porcentaje y la etiqueta (C3-03 y C1-30).
- [x] Los montos se anuncian con su moneda, igual que en las cuentas de FEAT-001: los del
  resumen, lo gastado, el tope y cada movimiento, también lo que pesa en el tope (C3-04).

## Textos

Van en `frontend/src/messages.ts`, bajo `budget`, salvo los compartidos, bajo `common`.

| Clave | Texto |
|---|---|
| `nav.budget` | Presupuesto |
| `heading` | Tu presupuesto |
| `loading` | Consultando tu presupuesto… |
| `period` | Período |
| `personal` | Personal |
| `periodRange` | del {inicio} al {fin} |
| `draft` | Borrador |
| `draftNotice` | Este período está en borrador: confirmalo para que reciba movimientos |
| `estimatedIncome` | Ingreso estimado |
| `actualIncome` | Ingreso real |
| `totalSpent` | Total gastado |
| `categories` | Categorías, el nombre de la lista para un lector de pantalla |
| `spentOf` | {gastado} de {tope} |
| `nearLimit` | Cerca del tope |
| `overLimit` | Excedido |
| `barValue` | {porcentaje}, {estado}, con el estado de `nearLimit` u `overLimit` en minúscula; solo el porcentaje si la barra es normal |
| `noLimit` | Sin tope |
| `back` | Volver al resumen |
| `noPeriods` | Todavía no tenés un presupuesto |
| `noPeriodsDetail` | Cuando armes tu primer período, acá vas a ver cuánto llevás gastado. |
| `emptyPeriod` | Este período todavía no tiene topes ni gastos |
| `emptyPeriodDetail` | Contale tus gastos a Platita y aparecen acá. |
| `failed` | No se pudo consultar tu presupuesto |
| `movements` | Movimientos, el nombre de la lista del detalle |
| `weighs` | Pesa en el tope, el título de lo que pesa un movimiento convertido |
| `types` | Gasto, Reintegro |
| `exchangeRate` | cotización {cotización} |
| `sources` | Manual, Automático |
| `common.apiFailures` y `common.retry` | Los compartidos con las otras pantallas |
