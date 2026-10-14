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
| Tarjeta (`card`) | Existe | El marco de la pantalla, igual que el estado del sistema y la entrada |
| Línea de estado (`role="status"`) | Existe, como en la entrada de desarrollo | Anuncia cargando y vacío, y recibe el foco al reintentar |
| Alerta de error (`role="alert"`) con botón Reintentar | Existe, como en la entrada de desarrollo | El estado de error |
| Grupo de cuentas (`account-group`) | Nuevo | Un título por moneda, y otro para las inversiones. Ninguno de los existentes agrupa |
| Fila de cuenta (`account`) | Nuevo | Nombre, tipo y saldo de una cuenta en una línea. No había ninguna lista de montos |

## Tokens del Design System

Todos salen de `frontend/src/design-tokens.css`. No se creó ninguno nuevo.

| Uso | Token |
|---|---|
| Fondo y borde de la tarjeta | `--color-surface`, `--color-border`, `--radius-medium` |
| Separación entre filas | `--border-width`, `--color-border`, `--space-2` |
| Título de cada grupo y tipo de cuenta | `--color-text-muted`, `--font-size-small`, `--font-weight-strong` |
| Nombre de la cuenta | `--font-weight-strong` |
| Saldo negativo, como el de una tarjeta con gastos vencidos | `--color-danger` |
| Error | `--color-danger` |
| Foco del teclado | `--focus-ring` |

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre la pantalla, o se aprieta Reintentar | "Consultando tus cuentas…", sin ningún saldo | Llega la respuesta, o falla |
| Con contenido | `GET /accounts` trae al menos una cuenta que no es "Me deben" | Un grupo por moneda, en el orden en que llegan, y aparte las inversiones con "Aportado neto" | — |
| Vacío | `GET /accounts` trae una lista vacía, o solo cuentas "Me deben" | "Todavía no tenés cuentas" y que se dan de alta conversando con Platita, sin alerta | — |
| Error | La API responde con un error, no responde a tiempo o no se llega a ella | "No se pudieron consultar tus cuentas", la causa y Reintentar, sin ningún saldo | Reintentar vuelve a Cargando |

Sin sesión no es un estado de esta pantalla. Si `GET /accounts` responde `401`, la pantalla
desaparece y se vuelve a mostrar la entrada.

## Datos que consume

[`GET /accounts`](../../04-api.md): de cada cuenta usa `id`, `name`, `type`, `currency`, `balance`
y `balance_kind`. La pantalla no suma, no convierte y no redondea: muestra el `balance` tal como
llega, con el formato de su moneda. Usa `type` solo para dejar afuera las cuentas "Me deben", y
`balance_kind` para poner aparte las de inversión.

## Accesibilidad

- [x] Todo control tiene nombre accesible: el único es Reintentar.
- [x] El contraste cumple el mínimo de la guía del Design System: usa los mismos colores que las
  otras dos tarjetas.
- [x] La pantalla se puede operar sólo con teclado: el único control es un botón.
- [x] Los montos se anuncian con su moneda: cada saldo se escribe con el formato de su moneda,
  como "$ 25.000,00" o "US$ 400,00", nunca como número suelto.

## Textos

Están en `frontend/src/messages.ts`, bajo `accounts`.

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
| `apiUnreachable`, `apiError`, `apiTimeout` | Las mismas causas que la entrada de desarrollo |
| `retry` | Reintentar |
| `types` | Banco, Billetera, Inversión, Efectivo, Tarjeta de crédito, Me deben |
