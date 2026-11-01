# Contrato de UI — FEAT-005 · Armar y confirmar el presupuesto

- **Historia de usuario:** [HU2](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)
- **Se escribe:** antes de la pantalla del corte 1, junto con sus casos de componente.
- **Estado:** borrador.

Sigue la forma del [contrato de la pantalla de presupuesto](../FEAT-004/ui_contract.md).

## Componentes

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|
| `Card` y `CardTitle` de shadcn/ui | Existen, desde el [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md) | El marco del formulario, como en las otras pantallas |
| `Button` de shadcn/ui | Existe, desde el ADR 0027 | Guardar el borrador, confirmarlo, sumar y quitar un tope, reintentar y volver |
| Entrada al formulario | Nuevo, en `BudgetPage` | "Armar un período" en su propio bloque, con la fecha desde la que puede empezar el próximo período individual, y "Editar" al lado del selector "Tus períodos existentes", en un período que el usuario puede editar (`can_edit`), en borrador o confirmado (CA-10). Decidido por Vero el 31 de octubre y el 1 de noviembre de 2026 |
| Formulario del período | Nuevo, `BudgetPeriodFormPage` | La cadencia, el día de inicio, el fin, la moneda, el ingreso estimado y la lista de topes. Al armar uno nuevo viene con la cadencia, la moneda, el ingreso y los topes del último período del usuario, y el inicio el día después de su fin (CA-13); en uno confirmado, la cadencia, las fechas y la moneda no se editan (CA-10) |
| Cadencia, moneda y categoría de un tope nuevo | Nuevos, sobre un `select` nativo | Como el selector de período de la FEAT-004: shadcn/ui no tiene uno instalado. La moneda se elige del catálogo, con su código y su nombre, y no se escribe (CA-17). Decidido por Vero el 31 de octubre de 2026 |
| Tabla de topes | Nueva, en `BudgetPeriodFormPage` | Un solo dropdown y un monto para sumar un tope, que ofrece solo las categorías sin tope. Cada tope es una fila con su categoría, su monto editable y "Quitar". Decidido por Vero el 1 de noviembre de 2026 |
| Fecha de inicio y de fin | Nuevos, sobre un `input type="date"` nativo | El fin es optativo en un período mensual: vacío, lo calcula el backend |
| Montos | Nuevos, sobre un `input` de texto con `inputMode="decimal"` | El ingreso y cada tope viajan como texto decimal, nunca como `number` de JavaScript. Aceptan solo cifras y un separador decimal, con el aviso "Sin puntos de miles. Para los centavos usá coma: 1450000,55". Decidido por Vero el 1 de noviembre de 2026 |
| Línea de estado (`role="status"`) | Existe, como en las otras pantallas | Anuncia la carga, el guardado y la confirmación |
| Alerta de error (`role="alert"`) | Existe, como en las otras pantallas | El estado de error |

## Tokens del Design System

Los mismos que la [pantalla de presupuesto](../FEAT-004/ui_contract.md#tokens-del-design-system),
sin tokens nuevos.

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre el formulario | "Preparando el formulario…", sin campos editables | Llegan las categorías, las monedas y, al editar, el borrador, o falla |
| Con contenido: armando | Llegó lo necesario | El formulario y "Guardar borrador". Al crear, con la cadencia, la moneda, el ingreso y los topes del último período del usuario y el inicio sugerido el día después de su fin, que se puede cambiar, con el fin vacío, o todo vacío si no tiene ninguno; al editar, con el período | Guardar, o volver al resumen |
| Guardando | Se aprieta "Guardar borrador" o "Confirmar" | El formulario sin poder editarse y la línea de estado, con "Guardando…" o "Confirmando…". Al terminar, la línea anuncia que quedó guardado o confirmado. Decidido por Vero el 1 de noviembre de 2026 | Llega la respuesta, o falla |
| Con contenido: guardado | El borrador quedó guardado | Lo guardado, con el fin calculado, "Editar" y "Confirmar" | Confirmar, editar o volver |
| Vacío | `GET /categories` responde sin ninguna categoría de gasto | En lugar de la lista de topes, que no hay categorías de gasto para ponerles tope. El resto del formulario sigue disponible | Guardar sin topes, o volver al resumen |
| Confirmado | Se confirmó | Que el período quedó confirmado y desde cuándo recibe movimientos | Volver al resumen, con ese período elegido |
| Error | La API responde con un error, no responde a tiempo o no se llega a ella | Qué falló y Reintentar, sin perder lo cargado en el formulario | Reintentar repite solo el pedido que falló |
| Rechazado | La API rechaza el pedido por una regla, como fechas superpuestas o un tope en 0 | El mensaje de esa regla, sin Reintentar, porque el mismo pedido recibiría el mismo rechazo, y el formulario editable con lo cargado. Si las fechas se superponen, también "Tus períodos", con las fechas de los otros períodos del mismo dueño. Decidido por Vero el 31 de octubre y el 1 de noviembre de 2026 | Corregir y volver a guardar, o volver al resumen |

Un usuario sin períodos anteriores no es el estado vacío: ve el formulario en blanco y las
categorías para elegir. Decidido por Vero el 31 de octubre de 2026.
Sin sesión no es un estado de esta pantalla: un `401` vuelve a la entrada.

## Datos que consume

- Crear, cambiar y confirmar el borrador, con los tres endpoints de escritura de
  [la API](../../04-api.md).
- La lista de períodos, para abrir un período al editarlo y para precargar uno nuevo con el
  último del usuario (CA-13).
- `GET /categories`, las categorías de gasto del usuario, para elegir a cuáles ponerles tope.
- `GET /currencies`, las monedas del catálogo, para elegir la del período.

El último período es el individual que empieza más tarde, aunque sea un borrador (CA-13).

Los casos de componente, también los de la precarga, se proponen cuando la pantalla esté armada.
