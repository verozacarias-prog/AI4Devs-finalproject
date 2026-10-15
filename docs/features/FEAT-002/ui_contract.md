# Contrato de UI — FEAT-002 · Chat web

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)
- **Se escribe:** antes del corte vertical 1, junto con la especificación

El chat web es un andamio de desarrollo, no una pantalla del producto
([ADR 0002](../../adr/0002-whatsapp-como-canal-principal.md)). Por eso va en la sección
"Pruebas" del menú lateral, junto al estado del sistema, y no junto a "Cuentas". La opción
aparece solo si el chat web está encendido: si `GET /chat/messages` responde `404`, el menú no
la dibuja.

## Componentes

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|
| `Card` y `CardTitle` de shadcn/ui | Existen, desde el [ADR 0027](../../adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md) | El marco de la pantalla, con "Chat con Platita" como título |
| `Button` de shadcn/ui | Existe, desde el ADR 0027 | Enviar, Reintentar la consulta y Reintentar un envío |
| Opción del menú (`NavItem`) | Existe, en `App.tsx` | "Chat", en la sección "Pruebas" |
| Línea de estado (`role="status"`) | Existe, como en la pantalla de cuentas | Anuncia cargando, vacío y "Platita está procesando…" |
| Alerta de error (`role="alert"`) | Existe, como en la pantalla de cuentas | El estado de error |
| Burbuja de mensaje | Nuevo, en `ChatPage` | Un mensaje con su hora, a la derecha si es del usuario y a la izquierda si es de Platita. Ningún componente existente alinea por autor |
| Campo para escribir | Nuevo, en `ChatPage` | Un `textarea` nativo con su etiqueta, y Enviar. shadcn/ui no está instalado con su `Textarea`, y uno nativo con los tokens alcanza |

## Tokens del Design System

Todos salen de `frontend/src/design-tokens.css`. No se crea ningún token para esta pantalla.

| Uso | Token |
|---|---|
| Fondo, texto, borde y radio de la tarjeta | `--color-card`, `--color-card-foreground`, `--color-border`, `--radius-xl`, `--shadow-sm` |
| Burbuja del usuario | `--color-primary`, `--color-primary-foreground`, `--radius-lg` |
| Burbuja de Platita | `--color-muted`, `--color-foreground`, `--radius-lg` |
| Hora de cada mensaje y "Platita está procesando…" | `--color-muted-foreground`, `--text-xs`. En la burbuja del usuario, la hora usa `--color-primary-foreground` con transparencia: el gris no se lee sobre `--color-primary` |
| Campo para escribir | `--color-input`, `--color-border`, `--radius-md` |
| Error, y un envío que falló | `--color-destructive`. "No enviado" va sobre `--color-card`, dentro de la burbuja del usuario |
| Foco del teclado | `--color-ring`, `--focus-ring-width` |

## Máquina de estados

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | Se abre la pantalla, o se aprieta Reintentar | "Abriendo la conversación…", sin el campo para escribir | Llega la respuesta, o falla |
| Con contenido | `GET /chat/messages` trae al menos un mensaje | La conversación, en el orden en que llega, y el campo para escribir | — |
| Vacío | `GET /chat/messages` trae una lista vacía | Una invitación con un ejemplo de gasto, sin alerta, y el campo para escribir | Se envía el primer mensaje |
| Error | La primera consulta responde con un error, no responde a tiempo o no llega | "No se pudo abrir la conversación", la causa y Reintentar | Reintentar vuelve a Cargando |

Dentro de "Con contenido" hay tres situaciones, que no son estados de la pantalla:

- **Procesando.** El último mensaje es del usuario y todavía no tiene respuesta: debajo se ve
  "Platita está procesando…".
- **No enviado.** El `POST` de un mensaje falló: la burbuja queda con "No enviado" y Reintentar,
  y el reintento repite el pedido con la misma `Idempotency-Key`.
- **Consulta periódica caída.** Una consulta de mensajes nuevos falló con la conversación en
  pantalla: la conversación sigue, se ve un aviso, y se sigue preguntando.

Mientras la pantalla está abierta, pregunta por mensajes nuevos cada 3 segundos, con el
`next_cursor` de la última respuesta. Al cambiar de pantalla deja de preguntar.

Una sesión que venció tampoco es un estado: ante un `401`, de la consulta o del envío, el
dashboard vuelve a la entrada de desarrollo.

## Datos que consume

- [`GET /chat/messages`](../../04-api.md#post-chatmessages-y-get-chatmessages): de cada mensaje
  usa `id`, `direction`, `text` y `created_at`, y de la respuesta, `next_cursor`. `response_kind`
  y `quoted_message_id` llegan y no se usan.
- [`POST /chat/messages`](../../04-api.md#post-chatmessages-y-get-chatmessages): manda `text`, y
  la `Idempotency-Key` que genera una vez por mensaje. No manda `quoted_message_id`: el botón
  "Responder" llega en la entrega final.

## Accesibilidad

- [ ] Todo control tiene nombre accesible: el campo para escribir, Enviar y cada Reintentar.
- [ ] El contraste cumple el mínimo de WCAG AA, 4,5:1 para texto normal, también la hora sobre
  cada burbuja.
- [ ] La pantalla se puede operar sólo con teclado: se escribe, se envía con Enter o con el
  botón, y se llega a cada Reintentar con Tab.
- [ ] Una respuesta nueva de Platita se anuncia a un lector de pantalla sin mover el foco.
- [ ] Quién escribió cada mensaje se dice con texto, no solo con el lado y el color.

## Textos

Van en `frontend/src/messages.ts`, bajo `chat`, salvo los compartidos, bajo `common` y `nav`.

| Clave | Texto |
|---|---|
| `nav.chat` | Chat |
| `heading` | Chat con Platita |
| `loading` | Abriendo la conversación… |
| `empty` | Todavía no le escribiste a Platita |
| `emptyDetail` | Contale un gasto como se lo contarías a alguien, por ejemplo: "gasté 3500 en el súper con Galicia". |
| `conversation` | Conversación con Platita: el nombre con que un lector de pantalla anuncia la lista de mensajes |
| `inputLabel` | Tu mensaje |
| `send` | Enviar |
| `processing` | Platita está procesando… |
| `notSent` | No enviado |
| `failed` | No se pudo abrir la conversación |
| `pollFailed` | No se pudo buscar mensajes nuevos. Se reintenta en unos segundos. |
| `authorUser` | Vos |
| `authorPlatita` | Platita |
| `common.apiFailures` | La causa de un error, compartida con las otras pantallas |
| `common.retry` | Reintentar, compartido con las otras pantallas |
