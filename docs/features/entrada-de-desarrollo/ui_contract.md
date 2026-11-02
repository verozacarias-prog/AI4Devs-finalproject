# Contrato de UI — Entrada de desarrollo y enlace personal

- **Historia de usuario:** ninguna. Es un andamio, y no una funcionalidad del producto.
- **Especificación:** [ADR 0016](../../adr/0016-sesion-de-servidor-en-el-mismo-origen.md) y
  [`04-api.md`](../../04-api.md#get-devusers-y-post-devsession).
- **Se escribe:** llegó tarde. La entrada de `local` ya existía, y este contrato se escribió al
  sumarle el enlace personal de `demo`.

Es la pantalla por donde se entra sin un código de WhatsApp. Tiene dos formas, según el entorno:
en `local`, una lista de usuarios de prueba; en `demo`, el enlace personal de cada persona, con un
aviso de prueba que se acepta la primera vez. Se quita junto con la entrada de desarrollo.

## Componentes

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|
| `Button` de shadcn/ui, del [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md) | Existe | Entrar como un usuario, Acepto, Cerrar sesión y Reintentar |
| `Card` y `CardTitle`, del mismo ADR | Existen | La tarjeta, que no se dibuja hasta la primera respuesta: antes no se sabe si esta entrada existe en el entorno |
| Línea de estado (`role="status"`) | Nueva en esta pantalla, y de acá la tomaron las demás | Anuncia cargando, la lista, la sesión abierta, vacío, el aviso y la sesión que terminó, y recibe el foco cuando desaparece el botón que se apretó |
| Alerta de error (`role="alert"`) | Nueva en esta pantalla, y de acá la tomaron las demás | El estado de error y el enlace que ya no sirve |

## Tokens del Design System

Todos salen de `frontend/src/design-tokens.css`. Esta pantalla no suma ninguno.

| Uso | Token |
|---|---|
| Fondo, texto, borde y radio de la tarjeta | `--color-card`, `--color-card-foreground`, `--color-border`, `--radius-xl`, `--shadow-sm` |
| Línea de estado y detalles | `--color-muted-foreground`, `--text-sm` |
| Quién entró | `--color-success` |
| Error y enlace que no sirve | `--color-destructive` |
| El comando del estado vacío | `--color-muted`, `--color-border`, `--radius-md`, `--text-sm` |
| Foco del teclado | `--color-ring`, `--focus-ring-width` |

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre la pantalla, con o sin enlace, o se aprieta un botón | "Consultando la sesión…". Hasta la primera respuesta, solo esa línea, sin tarjeta | Llega la respuesta, o falla |
| Con contenido | `GET /dev/users` trae usuarios, hay una sesión abierta o el enlace pide el aviso | La lista, "Entraste como…", o el aviso con sus tres puntos y Acepto | Elegir un usuario, cerrar la sesión o aceptar el aviso |
| Vacío | En `local`, `GET /dev/users` trae una lista vacía | "No hay usuarios de prueba", con el comando para crearlos y Reintentar | Correr el comando y Reintentar |
| Error | Una consulta responde con un error, no responde a tiempo o no llega | "No se pudo consultar la sesión", la causa y Reintentar. Con un enlace, Reintentar lo vuelve a mandar | Reintentar vuelve a Cargando |

Con un enlace no hay estado vacío: el pedido termina en el aviso, en la cuenta o en un rechazo.

Hay tres situaciones que no son estados de la pantalla:

- **Enlace que no sirve.** `POST /dev/session` responde `404`: se ve "Este enlace ya no sirve" y a
  quién pedirle otro, sin Reintentar, porque reintentar no lo arreglaría.
- **Entrada que no existe acá.** Sin sesión y con `GET /dev/users` en `404`, como en `demo` sin un
  enlace: la tarjeta no se dibuja, y se ven la marca y el estado del sistema.
- **Sesión que terminó después de entrar con un enlace.** La misma respuesta, en un navegador que
  ya entró con un enlace: la tarjeta dice "Tu sesión terminó" y que hay que abrir de nuevo el
  enlace personal, sin ningún botón. Pasa cuando la sesión vence, al recargar o al seguir usando
  la app, y cuando la persona la cierra. El navegador guarda solo que entró con un enlace, nunca
  el enlace. Sin esa marca, o si el navegador no deja guardarla, la pantalla es la de la entrada
  que no existe: en `production` la respuesta es la misma, y ahí no hay enlace que abrir.

El valor del enlace sale de la barra del navegador antes de que llegue ninguna respuesta. Si la
página tiene una sesión de otra persona, gana el enlace. Esa sesión no se revoca y sigue vigente
hasta que venza.

## Datos que consume

- `POST /dev/session`, con `access_token` y `accept_test_notice`, o con `user_id`. Del `409` usa
  `notice_version`.
- `GET /me`: `name`.
- `GET /dev/users`: `id` y `name` de cada usuario.
- `POST /auth/logout`.

## Accesibilidad

- [x] Todo control tiene nombre accesible: cada uno es un botón con su texto.
- [x] El contraste cumple el mínimo de WCAG AA, 4,5:1 para texto normal. Calculado con los colores
  de `design-tokens.css`, sobre `--color-card`:
  - línea de estado y detalles, `--color-muted-foreground`: 6,0:1;
  - quién entró, `--color-success`: 5,2:1;
  - error y enlace que no sirve, `--color-destructive`: 5,4:1.
- [x] La pantalla se puede operar sólo con teclado: son botones nativos.
- [x] Los montos y porcentajes se anuncian con su moneda y su unidad: esta pantalla no muestra
  ninguno.
- [x] La línea de estado anuncia cada cambio, también la aparición del aviso, y el foco va a ella
  cuando desaparece el botón que se apretó.

## Textos

Están en `frontend/src/messages.ts`, bajo `devEntry`. Un cambio en los puntos del aviso lleva una
versión nueva, `TEST_NOTICE_VERSION`, en `backend/app/test_data.py`.

| Clave | Contenido |
|---|---|
| `heading` | Entrada de desarrollo |
| `linkHeading` | Entrar a Platita |
| `loading` | Consultando la sesión… |
| `noticeHeading` | Antes de entrar |
| `noticeAnnounced` | Antes de entrar, leé este aviso |
| `noticePoints` | Este es un entorno de prueba. / Lo que escribas lo procesa un proveedor de IA. / Tus datos pueden borrarse sin aviso. |
| `accept` | Acepto |
| `linkRejected` | Este enlace ya no sirve |
| `linkRejectedDetail` | Pedile uno nuevo a quien te lo mandó. |
| `linkSessionEnded` | Tu sesión terminó |
| `linkSessionEndedDetail` | Para volver a entrar, abrí de nuevo tu enlace personal. |
| `failed` | No se pudo consultar la sesión |
