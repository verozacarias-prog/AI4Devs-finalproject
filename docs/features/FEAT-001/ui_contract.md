# Contrato de UI — FEAT-001 · Pantalla de cuentas

- **Historia de usuario:** [HU1](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)
- **Se escribe:** antes del corte vertical 1, junto con la especificación. Este llegó tarde: se
  escribió con la pantalla ya armada, antes de aprobar sus casos de componente.

Por qué este contrato vive separado de los componentes está en las
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#3-artefactos-de-una-funcionalidad).

## Componentes

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|
| `Card` y `CardTitle` de shadcn/ui | Existen, desde el [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md) | El marco de la pantalla, igual que el estado del sistema y la entrada. Es una sección con el título como nombre, así que un lector de pantalla la anuncia como "Tus cuentas" |
| `Button` de shadcn/ui | Existe, desde el ADR 0027 | Reintentar |
| Línea de estado (`role="status"`) | Existe, como en la entrada de desarrollo | Anuncia cargando y vacío, y recibe el foco al reintentar |
| Alerta de error (`role="alert"`) | Existe, como en la entrada de desarrollo | El estado de error |
| Grupo de cuentas | Nuevo, en `AccountsPage` | Un título por moneda, y otro para las inversiones. Ningún componente existente agrupa |
| Fila de cuenta | Nuevo, en `AccountsPage` | Nombre, una etiqueta con el tipo y el saldo de una cuenta, en una línea |

## Tokens del Design System

Todos salen de `frontend/src/design-tokens.css`, que es el tema entero de Tailwind, con las dos
excepciones que admite el [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md): las
clases fijas, como `rounded-full` en la etiqueta del tipo, y la transparencia sobre un color del
tema. No se creó ningún token para esta pantalla.

| Uso | Token |
|---|---|
| Fondo, texto, borde y radio de la tarjeta | `--color-card`, `--color-card-foreground`, `--color-border`, `--radius-xl`, `--shadow-sm` |
| Título "Tus cuentas" | `--text-xl`, `--font-weight-semibold` |
| Lista de cuentas: borde y separación entre filas | `--color-border`, `--radius-lg`, `--spacing` |
| Título de cada grupo y etiqueta del tipo | `--color-muted-foreground`, `--color-muted`, `--text-xs`, `--font-weight-semibold`, `--tracking-wide` |
| Nombre de la cuenta y saldo | `--font-weight-medium`, `--font-weight-semibold` |
| Saldo negativo, como el de una tarjeta con gastos vencidos | `--color-destructive` |
| Error | `--color-destructive` |
| Foco del teclado | `--color-ring`, `--focus-ring-width` |

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre la pantalla, o se aprieta Reintentar | "Consultando tus cuentas…", sin ningún saldo | Llega la respuesta, o falla |
| Con contenido | `GET /accounts` trae al menos una cuenta que no es "Me deben" | Un grupo por moneda, en el orden en que llegan, y aparte las inversiones con "Aportado neto" | — |
| Vacío | `GET /accounts` trae una lista vacía, o solo cuentas "Me deben" | "Todavía no tenés cuentas" y que se dan de alta conversando con Platita, sin alerta | — |
| Error | La API responde con un error, no responde a tiempo o no se llega a ella | "No se pudieron consultar tus cuentas", la causa y Reintentar, sin ningún saldo | Reintentar vuelve a Cargando |

Sin sesión no es un estado de esta pantalla. Si `GET /accounts` responde `401`, la pantalla y el
menú desaparecen, y se vuelve a mostrar la entrada.

## Datos que consume

[`GET /accounts`](../../04-api.md): de cada cuenta usa `id`, `name`, `type`, `currency`, `balance`
y `balance_kind`. La pantalla no suma, no convierte y no redondea: muestra el `balance` tal como
llega, con el formato de su moneda. Usa `type` solo para dejar afuera las cuentas "Me deben", y
`balance_kind` para poner aparte las de inversión.

## Accesibilidad

- [x] Todo control tiene nombre accesible: el único es Reintentar.
- [x] El contraste cumple el mínimo de WCAG AA, 4,5:1 para texto normal: se calculó para cada
  color de texto contra su fondo, y el más bajo es el verde de "conectado" sobre la tarjeta
  blanca, con 5,19:1.
- [x] La pantalla se puede operar sólo con teclado: el único control es un botón.
- [x] Los montos se anuncian con su moneda: cada saldo se escribe con el formato de su moneda,
  como "$ 25.000,00" o "US$ 400,00", nunca como número suelto.

## Textos

Están en `frontend/src/messages.ts`, bajo `accounts`, salvo los compartidos, bajo `common`.

| Clave | Texto |
|---|---|
| `heading` | Tus cuentas |
| `loading` | Consultando tus cuentas… |
| `currencyGroup` | Cuentas en {moneda} |
| `investmentsHeading` | Inversiones |
| `investmentsDetail` | Lo aportado neto: lo que pusiste menos lo que sacaste, no lo que vale hoy. |
| `netContributed` | Aportado neto |
| `empty` | Todavía no tenés cuentas |
| `emptyDetail` | Las cuentas se dan de alta conversando con Platita. |
| `failed` | No se pudieron consultar tus cuentas |
| `common.apiFailures` | La causa de un error, compartida con las otras pantallas |
| `common.retry` | Reintentar, compartido con las otras pantallas |
| `types` | Banco, Billetera, Inversión, Efectivo, Tarjeta de crédito, Me deben |
