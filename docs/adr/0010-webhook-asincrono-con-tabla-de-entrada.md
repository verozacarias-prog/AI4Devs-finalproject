# 0010 — Webhook de WhatsApp asíncrono, con tabla de entrada y de salida en PostgreSQL

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

El canal principal de registro es WhatsApp, por la API oficial de Meta (Cloud API). Twilio queda
como segunda opción si Meta deja de servir, pero hoy se diseña solo para Meta.

La especificación describía el webhook como síncrono: al recibir un mensaje, verificaba la firma,
llamaba al LLM para interpretarlo, escribía en la base y recién entonces respondía `200` con
`transaction_created`. Un diagnóstico de arquitectura encontró tres problemas en ese diseño:

- **Duplicados.** Meta reintenta la entrega de un webhook cuando no recibe `200` a tiempo. Si la
  llamada al LLM tarda, el mismo mensaje llega dos veces y se registra dos veces. El contrato ni
  siquiera tenía el identificador del mensaje (`wamid`) con el que detectar el reintento. En un
  producto cuyo dato central es el saldo, un movimiento duplicado es dinero que no existe.
- **Acoplamiento a la latencia del LLM.** Si el proveedor de LLM está lento o caído, el webhook
  falla y el mensaje del usuario se pierde, aunque la base y WhatsApp funcionen.
- **Contrato inventado.** El cuerpo documentado (`from`, `message`, `timestamp`) no es el de Meta,
  que anida los mensajes en `entry[].changes[].value.messages[]`, firma cada request con
  `X-Hub-Signature-256` y verifica la URL con un `GET` que devuelve `hub.challenge`. Además, por
  el mismo webhook llegan eventos de estado (entregado, leído) que no son mensajes.

El proyecto lo construye y lo opera una sola persona, con PostgreSQL como único almacén
([ADR 0004](0004-postgres-con-pgvector-como-unico-almacen.md)) y un volumen esperado muy por
debajo de un mensaje por segundo.

## Decisión

El webhook solo recibe y confirma; el procesamiento ocurre después, en un proceso aparte.

1. **Recepción.** `POST /webhook/whatsapp` verifica la firma `X-Hub-Signature-256` (HMAC-SHA256
   del cuerpo crudo con el secreto de la app, comparado en tiempo constante) antes de parsear
   nada. Si no es válida, responde `401` y no guarda nada. Si es válida, inserta cada mensaje en
   la tabla `INBOUND_MESSAGE` con `INSERT … ON CONFLICT DO NOTHING` sobre
   `UNIQUE (provider, provider_message_id)`, y responde `200` de inmediato. Un reintento de Meta
   choca con la clave única y no genera nada nuevo. Los eventos de estado se responden con `200`
   y no se guardan.
2. **Verificación de la URL.** `GET /webhook/whatsapp` responde `hub.challenge` solo si
   `hub.verify_token` coincide con el configurado.
3. **Procesamiento.** Un proceso worker, con el mismo código y otro punto de entrada, toma los
   mensajes pendientes de la tabla, sin una cola aparte. Procesa **un mensaje por remitente a la
   vez y en orden de llegada**, porque una respuesta como "Galicia, el familiar" solo tiene
   sentido después del mensaje que la originó. El remitente es `user_id` si existe y
   `from_phone` si no. La toma es una **transacción corta de claim**: con
   `SELECT … FOR UPDATE SKIP LOCKED` elige, de un remitente que no tenga ningún mensaje en
   `processing` con `locked_until` vigente, su mensaje pendiente de menor `sent_at` cuyo
   `next_attempt_at` ya pasó; lo marca `status = 'processing'`, incrementa `attempts`, fija
   `locked_until` y hace commit. El `locked_until` es el lock por remitente: mientras esté
   vigente, ningún otro worker toma mensajes de ese remitente; si el worker se cae, vence y el
   mensaje vuelve a estar disponible. La llamada al LLM ocurre después del claim y fuera de toda
   transacción de base de datos. Después, en **una sola transacción**, aplica los
   efectos (crear o completar el pendiente, promoverlo a movimiento), marca el mensaje como
   procesado y encola la respuesta. O pasa todo o no pasa nada: un mensaje nunca queda
   procesado sin sus efectos, ni con sus efectos aplicados dos veces.
4. **Reintentos.** Si el procesamiento falla (el LLM no responde, por ejemplo), el mensaje vuelve
   a quedar disponible con espera creciente entre intentos. Superado un máximo de intentos queda
   como `failed` y el usuario recibe un aviso de que su mensaje no se pudo procesar. Un mensaje
   nunca se descarta en silencio. Mientras se reintenta, los mensajes siguientes del mismo
   remitente esperan detrás, para respetar el orden; una vez en `failed` deja de bloquearlos, y
   el siguiente se procesa normalmente.
5. **Salida.** Las respuestas al usuario se escriben en la tabla `OUTBOUND_MESSAGE` dentro de la
   misma transacción que las origina, y el worker las envía después. Los procesos programados
   (alertas, recordatorios) usan la misma tabla para mandar sus mensajes. Una respuesta nunca se
   pierde por una caída entre el cambio en la base y el envío. En el peor caso se envía dos
   veces, que es un mensaje repetido y no un movimiento repetido.
6. **Proveedor.** Las tablas guardan `provider` y el identificador del proveedor, y el puerto de
   WhatsApp no expone conceptos de Meta. Pasar a Twilio es escribir otro adaptador de entrada y
   de salida, sin migrar datos.

Los procesos programados (gastos recurrentes, alertas de presupuesto, expiración de pendientes)
siguen siendo cron jobs separados. Esta decisión no los cambia, salvo que envían por la tabla de
salida.

## Consecuencias

### Positivas

- Un reintento de Meta no puede duplicar un movimiento: lo impide una clave única en la base, no
  la lógica de la aplicación.
- Una caída o lentitud del LLM demora la respuesta al usuario, pero no pierde su mensaje.
- No entra tecnología nueva: la cola es una tabla de PostgreSQL, y el worker es el mismo código
  que la API. Se mantiene un único almacén.
- El orden por usuario hace que la continuación de un pendiente sea determinista.
- La tabla de entrada deja un registro auditable de todo lo que llegó por el canal, procesado o
  no.

### Negativas y costos asumidos

- Un servicio más para desplegar y vigilar: el worker. Si se cae, los mensajes se acumulan sin
  perderse, pero nadie recibe respuesta hasta que vuelve.
- La respuesta al usuario ya no sale en el mismo request, así que la confirmación llega con la
  demora del worker además de la del LLM.
- Hay que escribir el ciclo de toma de mensajes, los reintentos con espera y el envío de la
  salida, que un sistema de colas daría hechos. Se estima en uno o dos días.
- La tabla de entrada guarda el texto y el teléfono del usuario. Hace falta una política de
  retención, que queda por definir, y nunca se loggea su contenido sin enmascarar.
- A partir de cientos de mensajes por minuto, una tabla como cola empieza a competir con el resto
  de la carga de la base. Ahí conviene una cola dedicada, y el puerto de entrada permite
  cambiarla sin tocar el dominio.

## Alternativas descartadas

- **Webhook síncrono con una clave de idempotencia:** guardar el `wamid` y seguir procesando
  dentro del request. Resuelve el duplicado, pero no el acoplamiento a la latencia del LLM: si
  tarda más que el tiempo de espera de Meta, el reintento llega mientras el primero todavía
  procesa. Descartado porque deja el flujo principal a merced de un tercero.
- **Tarea en segundo plano dentro del proceso web** (`BackgroundTasks` de FastAPI): responde
  rápido sin un servicio más, pero la tarea vive en memoria. Un reinicio o un despliegue la pierde
  sin dejar rastro. Descartado porque un mensaje perdido es un movimiento perdido.
- **Una cola dedicada (Redis, SQS o similar):** reintentos y visibilidad resueltos por la
  herramienta, a cambio de operar un segundo sistema y de perder la atomicidad entre marcar el
  mensaje y aplicar sus efectos, que hoy es una sola transacción de PostgreSQL. Descartado a este
  volumen; queda como el reemplazo natural si la tabla como cola deja de alcanzar.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
