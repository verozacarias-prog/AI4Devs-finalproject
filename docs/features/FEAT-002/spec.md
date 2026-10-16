# Especificación — FEAT-002 · Chat web y worker de mensajes

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Estado:** aprobada para los cortes 1, 2 y 3. Un caso sumado después de aprobado su corte lleva
  su propia línea de aprobación
- **Fecha:** 2026-10-14

## Alcance

Entra el camino asíncrono completo de un mensaje, sin el modelo de lenguaje: `POST` y
`GET /chat/messages`, el worker que toma cada mensaje de `INBOUND_MESSAGE` y deja su respuesta
en `OUTBOUND_MESSAGE`, y la pantalla del chat en el dashboard. Mientras no haya modelo, el worker
responde un texto fijo. Es la parte de la HU3 que la
[hoja de ruta](../../hoja-de-ruta.md#alcance-de-la-entrega-2) pone primero en la entrega 2: el
chat web, por el mismo camino asíncrono que WhatsApp
([ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md)).

El worker se suma a Docker Compose como cuarto servicio, con la misma imagen que la API
([ADR 0021](../../adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md)).

No entran, y llegan con la funcionalidad siguiente, la del registro de un gasto y de un ingreso:

- La clasificación del mensaje y todo lo que hace el modelo. El texto fijo de esta funcionalidad
  es lo que ese registro reemplaza.
- Los reintentos con espera creciente, el estado `failed` y el aviso al usuario de que su
  mensaje no se pudo procesar. Lo primero que puede fallar al procesar un mensaje es la llamada
  al modelo, y se prueban con ella.

No entra el botón "Responder" de cada mensaje de Platita. Se decidió el 14 de octubre de 2026:
llega en la entrega final, con corregir, borrar y restaurar, como dice la hoja de ruta. La API
igual acepta y valida `quoted_message_id`, porque está en su contrato, pero la pantalla no lo
manda.

## Reglas de dominio que aplican

Esta funcionalidad no registra movimientos, así que no aplica ninguna regla de registro. Rigen
las decisiones de arquitectura del canal:

- [ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md) — la tabla de entrada, el
  worker, el orden por remitente, la transacción final y el chat web por el mismo camino.
- [ADR 0016](../../adr/0016-sesion-de-servidor-en-el-mismo-origen.md) — el chat web existe solo
  encendido, la consulta periódica no cuenta como actividad, y todo se muestra como texto.
- [ADR 0023](../../adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md)
  — los registros sin datos del usuario, `GET /queuez` y el aviso al arrancar.
- [§ 5 — Citar un mensaje](../../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración),
  solo en que el mensaje citado tiene que ser de Platita al mismo usuario.

## Criterios de aceptación

Una regla por criterio. Cada caso de [Casos de prueba](#casos-de-prueba) nombra el criterio
que ejemplifica.

### Escribir un mensaje

Lo que el usuario escribe queda guardado enseguida, y la respuesta llega después.

- **CA-1.** Quien entró al dashboard escribe en el chat y su mensaje queda guardado como pendiente, sin esperar la respuesta de Platita.
- **CA-2.** El mensaje se guarda a nombre del usuario de la sesión, con su teléfono, y con la hora en que lo recibió el servidor, no la del navegador.
- **CA-3.** El mismo mensaje enviado dos veces con la misma clave queda guardado una sola vez, y la segunda vez se responde con el que se guardó la primera.
- **CA-4.** Un mensaje sin texto, o sin clave, no se guarda.

### Platita responde

Cada mensaje recibe su respuesta, de a uno por usuario y en orden.

- **CA-5.** Todo mensaje pendiente recibe una respuesta de Platita, que aparece en el chat sin recargar la pantalla.
- **CA-6.** Mientras no haya modelo, la respuesta es un texto fijo.
- **CA-7.** El mensaje queda procesado y su respuesta queda guardada juntos, o no pasa ninguna de las dos cosas.
- **CA-8.** Los mensajes de un usuario se responden de a uno y en el orden en que llegaron; los de usuarios distintos no se esperan entre sí.
- **CA-9.** Si dos workers terminan de procesar el mismo mensaje, solo uno deja su respuesta.

### Ver la conversación

La pantalla se parece a un chat de WhatsApp.

- **CA-10.** El chat muestra los mensajes del usuario y las respuestas de Platita en el orden en que ocurrieron: los del usuario a la derecha y los de Platita a la izquierda, cada uno con su hora.
- **CA-11.** Mientras el último mensaje del usuario no tiene respuesta, se ve "Platita está procesando…".
- **CA-12.** Con el chat abierto, la pantalla pregunta cada pocos segundos si hay mensajes nuevos, y trae solo los posteriores al último que ya tiene. Con otra pantalla abierta, no pregunta.
- **CA-13.** Lo que escribió el usuario y lo que responde Platita se muestran como texto, nunca como HTML.
- **CA-14.** Preguntar por mensajes nuevos no mantiene viva la sesión; escribir un mensaje sí.

### Cada uno ve solo lo suyo, y el chat existe solo encendido

- **CA-15.** Cada usuario ve solo sus mensajes y las respuestas a ellos.
- **CA-16.** Sin una sesión válida no se lee ni se escribe ningún mensaje.
- **CA-17.** Con el chat web apagado, los dos endpoints responden `404` y el menú no muestra la opción del chat.
- **CA-18.** Un mensaje que cita algo que no es una respuesta de Platita a ese mismo usuario no se guarda.
- **CA-19.** Con el chat web encendido y el entorno en `production`, ningún proceso arranca.
- **CA-20.** Un mensaje cuyo contenido se purgó no aparece en la conversación.
- **CA-27.** La conversación del chat tiene solo lo que pasó por el chat web: un mensaje de WhatsApp, o un aviso que Platita mandó por WhatsApp, no aparece.

### Sin mensajes, y cuando algo falla

Una conversación que todavía no empezó está vacía; una consulta que no llegó es un error.

- **CA-21.** Un usuario que nunca escribió ve una invitación con un ejemplo de gasto, sin un mensaje de error.
- **CA-22.** Si la consulta de la conversación falla, se ve qué pasó y se puede reintentar.
- **CA-23.** Un envío que falla queda en la conversación como no enviado, con la opción de reintentar, y el reintento usa la misma clave, así que el mensaje nunca queda guardado dos veces.

### Lo que queda en los registros y la salud del worker

- **CA-24.** Ninguna línea de los registros lleva el texto de un mensaje ni un teléfono; el procesamiento de un mensaje se sigue por su identificador.
- **CA-25.** `GET /queuez` responde `503` si un mensaje pendiente espera hace más de 10 minutos, y `200` si no hay ninguno.
- **CA-26.** Con el chat web encendido, la API y el worker lo avisan en su registro al arrancar. Los comandos de operación no lo avisan.

## Casos de prueba

Cada caso es un ejemplo concreto de un criterio, y se entiende solo, sin leer los demás:
**Dado** es el estado inicial completo, **cuando** es una sola acción y **entonces** es el
estado final.

- En un caso **unitario** la acción es un caso de uso, con los puertos reemplazados por dobles,
  sin base de datos.
- En un caso de **integración** los datos están guardados en PostgreSQL y la acción es un
  pedido a [la API](../../04-api.md) o una ronda del worker, que toma un mensaje y lo procesa.
- Los de **componente**, uno por estado de la pantalla, llegan con la pantalla armada, y se
  aprueban entonces.

Salvo que el caso diga otra cosa: la base tiene los datos de prueba de `local`; Lucía es de
Buenos Aires y su teléfono es +000000000001; Pablo, +000000000002; el chat web está encendido;
Lucía tiene una sesión abierta; y el reloj marca el 15 de octubre de 2026 a las 18:00:00 UTC,
las 15:00:00 en Buenos Aires.

### Corte 1 — camino feliz

- **Aprobado por:** Veronica Zacarias 14/10/2026
- **Los de la pantalla, C1-11 a C1-18, escritos ya armada:** Veronica Zacarias 15/10/2026
- **C1-19 y C1-20, el intervalo de la consulta según haya o no una respuesta pendiente:** Veronica Zacarias 15/10/2026
- **C1-21 y C1-22, sumados con la revisión de pr-reviewer:** Veronica Zacarias 15/10/2026
- **C1-22, borrado el 15/10/2026 por decisión de Vero:** desde el C2-28 la pantalla no pregunta mientras un envío está en curso, así que ninguna consulta puede traer el mensaje antes de que responda el envío. Su número no se reutiliza.
- **Total:** 21 casos, 1 unitario, 9 de integración y 11 de componente.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | Lucía escribe y su mensaje queda guardado, pendiente | Integración | CA-1 y CA-2 |
| C1-02 | La hora del mensaje es la del reloj del servidor | Unitario | CA-2 |
| C1-03 | El worker contesta un mensaje pendiente con el texto fijo | Integración | CA-5, CA-6 y CA-7 |
| C1-04 | El worker toma primero el mensaje que llegó primero | Integración | CA-8 |
| C1-05 | Con un mensaje de Lucía en proceso, el siguiente suyo espera y el de Pablo no | Integración | CA-8 |
| C1-10 | Un mensaje ya respondido no frena al siguiente | Integración | CA-8 |
| C1-06 | La conversación viene en orden, con la respuesta en su lugar | Integración | CA-10 |
| C1-07 | Con un cursor, vienen solo los mensajes posteriores | Integración | CA-12 |
| C1-08 | Con un cursor y nada nuevo, la lista viene vacía | Integración | CA-12 |
| C1-09 | Escribir, procesar y leer la respuesta | Integración | CA-1, CA-5 y CA-10 |
| C1-11 | Mientras se abre la conversación, lo dice y no deja escribir | Componente | CA-10 |
| C1-12 | La conversación de Lucía, cada mensaje de su lado y con su hora | Componente | CA-10 |
| C1-13 | Sin respuesta al último mensaje, Platita está procesando | Componente | CA-11 |
| C1-14 | Escribir y enviar con Enter | Componente | CA-1 |
| C1-15 | La respuesta aparece sola, preguntando desde el último mensaje | Componente | CA-5 y CA-12 |
| C1-16 | Con otra pantalla abierta, no pregunta | Componente | CA-12 |
| C1-17 | Un mensaje con etiquetas se ve como texto | Componente | CA-13 |
| C1-18 | Con el chat encendido, el menú lleva a la conversación | Componente | CA-17 |
| C1-19 | Mientras espera una respuesta, pregunta cada medio segundo | Componente | CA-5 y CA-12 |
| C1-20 | Con la conversación respondida, pregunta cada 3 segundos | Componente | CA-12 |
| C1-21 | Al escribir en una conversación respondida, la consulta se adelanta | Componente | CA-5 y CA-12 |

#### C1-01 · Lucía escribe y su mensaje queda guardado, pendiente

- **Sale de:** CA-1 y CA-2 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta y ningún mensaje en `INBOUND_MESSAGE`,
- **cuando** pide `POST /chat/messages` con el header `Idempotency-Key`
  `9d2b7c1e-5a4f-4c3b-8e21-7f6a5b4c3d2e` y el cuerpo `{"text": "gasté 3500 en el súper"}`,
- **entonces** responde `202` con el `id` del mensaje y `"status": "pending"`; y
  `INBOUND_MESSAGE` tiene una sola fila, con ese `id`, `provider = 'web'`, el `user_id` de
  Lucía, `from_phone = '+000000000001'`, un `provider_message_id` formado por el `id` de Lucía
  seguido de la clave, el texto "gasté 3500 en el súper" en `payload`,
  `sent_at = 2026-10-15T18:00:00Z`, `status = 'pending'`, `attempts = 0` y
  `quoted_outbound_message_id` nulo.
- **Test:** `tests/integration/test_chat_messages.py::test_lucia_writes_and_her_message_is_stored_as_pending`

#### C1-02 · La hora del mensaje es la del reloj del servidor

- **Sale de:** CA-2 · **Tipo:** unitario
- **Dado** el reloj del caso de uso en 15 de octubre de 2026 a las 18:00:00 UTC, y un
  repositorio de mensajes vacío,
- **cuando** Lucía manda el mensaje "gasté 3500 en el súper" con la clave
  `9d2b7c1e-5a4f-4c3b-8e21-7f6a5b4c3d2e`,
- **entonces** el repositorio recibe un mensaje con `sent_at` 2026-10-15T18:00:00Z, que es lo
  que marca el reloj: el pedido no trae ninguna hora.
- **Test:** `tests/unit/test_send_chat_message.py::test_the_time_of_the_message_is_the_one_of_the_server_clock`

#### C1-03 · El worker contesta un mensaje pendiente con el texto fijo

- **Sale de:** CA-5, CA-6 y CA-7 · **Tipo:** integración
- **Dado** un mensaje web de Lucía, "gasté 3500 en el súper", con `status = 'pending'`,
  `sent_at` 2026-10-15T17:59:55Z, `attempts = 0`, y ninguna fila en `OUTBOUND_MESSAGE`,
- **cuando** el worker hace una ronda,
- **entonces** el mensaje queda con `status = 'processed'`, `attempts = 1` y
  `processed_at = 2026-10-15T18:00:00Z`; y `OUTBOUND_MESSAGE` tiene una sola fila, con
  `provider = 'web'`, el `user_id` de Lucía, `to_phone = '+000000000001'`, el
  `inbound_message_id` de ese mensaje, `status = 'sent'`, `sent_at = 2026-10-15T18:00:00Z`,
  `provider_message_id` nulo, y en `content` el texto "Recibí tu mensaje. Todavía no puedo
  procesarlo." con `response_kind = 'fixed_text'`.
- **Test:** `tests/integration/test_message_worker.py::test_the_worker_answers_a_pending_message_with_the_fixed_text`

#### C1-04 · El worker toma primero el mensaje que llegó primero

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** el lock del worker configurado en 2 minutos, y dos mensajes web pendientes de Lucía,
  guardados en este orden: "y 1200 de nafta",
  con `sent_at` 2026-10-15T17:59:05Z, y "gasté 3500 en el súper", con `sent_at`
  2026-10-15T17:59:00Z,
- **cuando** el worker toma el siguiente mensaje,
- **entonces** toma "gasté 3500 en el súper", que tiene el `sent_at` menor aunque se guardó
  segundo: queda con `status = 'processing'`, `attempts = 1` y `locked_until`
  2026-10-15T18:02:00Z: las 18:00:00 del reloj más los 2 minutos del lock. "y 1200 de nafta" sigue `pending`, con `attempts = 0`.
- **Test:** `tests/integration/test_message_worker.py::test_the_worker_takes_first_the_message_that_arrived_first`

#### C1-05 · Con un mensaje de Lucía en proceso, el siguiente suyo espera y el de Pablo no

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** tres mensajes web: "gasté 3500 en el súper", de Lucía, con `status = 'processing'`
  y `locked_until` 2026-10-15T18:02:00Z; "y 1200 de nafta", de Lucía, pendiente, con `sent_at`
  2026-10-15T17:59:05Z; y "cobré 50000", de Pablo, pendiente, con `sent_at`
  2026-10-15T17:59:10Z,
- **cuando** otro worker toma el siguiente mensaje,
- **entonces** toma "cobré 50000", de Pablo, aunque llegó después, y "y 1200 de nafta" sigue
  `pending`: Lucía tiene un mensaje en proceso con el lock vigente.
- **Test:** `tests/integration/test_message_worker.py::test_with_a_message_of_lucia_in_process_her_next_waits_and_pablos_does_not`

#### C1-10 · Un mensaje ya respondido no frena al siguiente

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** dos mensajes web de Lucía: "gasté 3500 en el súper", con `sent_at`
  2026-10-15T17:59:00Z, ya respondido, con `status = 'processed'`; y "y 1200 de nafta", con
  `sent_at` 2026-10-15T17:59:05Z, pendiente,
- **cuando** el worker toma el siguiente mensaje,
- **entonces** toma "y 1200 de nafta": solo un mensaje en proceso con el lock vigente hace
  esperar a los siguientes del mismo usuario.
- **Test:** `tests/integration/test_message_worker.py::test_a_message_already_answered_does_not_hold_the_next_one`

#### C1-06 · La conversación viene en orden, con la respuesta en su lugar

- **Sale de:** CA-10 · **Tipo:** integración
- **Dado** que Lucía mandó "gasté 3500 en el súper" a las 14:58:00 de Buenos Aires, Platita le
  contestó "Recibí tu mensaje. Todavía no puedo procesarlo." a las 14:58:04, y Lucía mandó "y
  1200 de nafta" a las 14:59:00, todo por el chat web,
- **cuando** Lucía pide `GET /chat/messages`, sin cursor,
- **entonces** responde `200` con tres mensajes, en este orden: "gasté 3500 en el súper", con
  `direction = "inbound"`, `quoted_message_id` nulo y `created_at`
  `2026-10-15T14:58:00-03:00`; la respuesta, con `direction = "outbound"`,
  `response_kind = "fixed_text"` y `created_at` `2026-10-15T14:58:04-03:00`; y "y 1200 de
  nafta", `inbound`, con `created_at` `2026-10-15T14:59:00-03:00`. `next_cursor` es el `id` de
  "y 1200 de nafta".
- **Test:** `tests/integration/test_chat_messages.py::test_the_conversation_comes_in_order_with_the_reply_in_its_place`

#### C1-07 · Con un cursor, vienen solo los mensajes posteriores

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** los mismos tres mensajes de Lucía del caso C1-06,
- **cuando** Lucía pide `GET /chat/messages?after=` con el `id` de la respuesta de Platita,
- **entonces** responde `200` con un solo mensaje, "y 1200 de nafta", y `next_cursor` es su
  `id`.
- **Test:** `tests/integration/test_chat_messages.py::test_with_a_cursor_only_the_later_messages_come`

#### C1-08 · Con un cursor y nada nuevo, la lista viene vacía

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** los mismos tres mensajes de Lucía del caso C1-06,
- **cuando** Lucía pide `GET /chat/messages?after=` con el `id` de "y 1200 de nafta", que es el
  último,
- **entonces** responde `200` con la lista de mensajes vacía, y `next_cursor` sigue siendo el
  `id` de "y 1200 de nafta", para que la consulta siguiente pregunte desde el mismo lugar.
- **Test:** `tests/integration/test_chat_messages.py::test_with_a_cursor_and_nothing_new_the_list_is_empty`

#### C1-09 · Escribir, procesar y leer la respuesta

- **Sale de:** CA-1, CA-5 y CA-10 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta y sin ningún mensaje,
- **cuando** manda "gasté 3500 en el súper" con `POST /chat/messages`, el worker hace una
  ronda, y Lucía pide `GET /chat/messages`,
- **entonces** la conversación tiene dos mensajes: el suyo, `inbound`, y después "Recibí tu
  mensaje. Todavía no puedo procesarlo.", `outbound`, con `response_kind = "fixed_text"`.
- **Test:** `tests/integration/test_chat_messages.py::test_write_process_and_read_the_reply`

En los casos de componente se arma el dashboard entero, con la API simulada a nivel de red,
y Lucía ya entró. La pantalla pregunta por mensajes nuevos cada pocos segundos; los tests le
pasan un intervalo corto.

#### C1-11 · Mientras se abre la conversación, lo dice y no deja escribir

- **Sale de:** CA-10 · **Tipo:** componente
- **Dado** que `GET /chat/messages` todavía no respondió,
- **cuando** Lucía abre el chat,
- **entonces** se ve "Abriendo la conversación…", y no se ve ningún mensaje ni el campo para
  escribir.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-11: while the conversation opens, it says so and there is nowhere to write"

#### C1-12 · La conversación de Lucía, cada mensaje de su lado y con su hora

- **Sale de:** CA-10 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde "gasté 3500 en el súper", de Lucía, a las 14:58,
  y "Recibí tu mensaje. Todavía no puedo procesarlo.", de Platita, a las 14:58, con la hora de
  Buenos Aires,
- **cuando** Lucía abre el chat,
- **entonces** se ven los dos en ese orden: el suyo a la derecha y el de Platita a la
  izquierda, cada uno con "14:58" y con quién lo escribió dicho en palabras, "Vos" y "Platita",
  para un lector de pantalla.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-12: the conversation of Lucía, each message on its side and with its time"

#### C1-13 · Sin respuesta al último mensaje, Platita está procesando

- **Sale de:** CA-11 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde un solo mensaje, "gasté 3500 en el súper", de
  Lucía, todavía sin respuesta,
- **cuando** Lucía abre el chat,
- **entonces** se ve "Platita está procesando…".
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-13: with no reply to the last message, Platita is processing"

#### C1-14 · Escribir y enviar con Enter

- **Sale de:** CA-1 · **Tipo:** componente
- **Dado** que la conversación de Lucía está vacía, y `POST /chat/messages` responde `202`,
- **cuando** escribe "gasté 3500 en el súper" y aprieta Enter,
- **entonces** se manda un solo `POST` con ese texto y un header `Idempotency-Key` que es un
  UUID; el mensaje aparece de su lado, el campo para escribir queda vacío, y se ve "Platita
  está procesando…".
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-14: write and send with Enter"

#### C1-15 · La respuesta aparece sola, preguntando desde el último mensaje

- **Sale de:** CA-5 y CA-12 · **Tipo:** componente
- **Dado** que el chat de Lucía muestra "gasté 3500 en el súper", con `next_cursor` en ese
  mensaje, y que la siguiente consulta trae la respuesta de Platita,
- **cuando** pasa el intervalo de la consulta,
- **entonces** la consulta lleva `after` con el `id` de "gasté 3500 en el súper", la respuesta
  aparece debajo sin recargar la pantalla, y "Platita está procesando…" desaparece.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-15: the reply shows up by itself, asking from the last message"

#### C1-16 · Con otra pantalla abierta, no pregunta

- **Sale de:** CA-12 · **Tipo:** componente
- **Dado** que Lucía tiene el chat abierto, que ya preguntó al menos una vez,
- **cuando** elige "Cuentas" en el menú y pasan varios intervalos,
- **entonces** no llega ningún otro pedido a `GET /chat/messages`.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-16: with another screen open, it does not ask"

#### C1-17 · Un mensaje con etiquetas se ve como texto

- **Sale de:** CA-13 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde un mensaje de Platita con el texto
  `<script>alert(1)</script><b>hola</b>`,
- **cuando** Lucía abre el chat,
- **entonces** ese texto se ve tal cual, con sus etiquetas como caracteres, y la página no
  tiene ningún elemento `script` ni `b` que venga de él.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-17: a message with tags is shown as text"

#### C1-18 · Con el chat encendido, el menú lleva a la conversación

- **Sale de:** CA-17 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde `200`, porque el chat está encendido,
- **cuando** Lucía entra,
- **entonces** la sección "Pruebas" del menú tiene "Chat", antes de "Estado del sistema", y
  elegirlo muestra "Chat con Platita" y lo marca como la pantalla actual. Que no aparezca con
  el chat apagado es del corte 2.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-18: with the chat on, the menu leads to the conversation"

En los dos casos que siguen, los tests achican los dos intervalos en la misma proporción: lo que
se comprueba es cuál de los dos usa la pantalla.

#### C1-19 · Mientras espera una respuesta, pregunta cada medio segundo

- **Sale de:** CA-5 y CA-12 · **Tipo:** componente
- **Dado** que la conversación de Lucía termina en "gasté 3500 en el súper", suyo y todavía sin
  respuesta, y que la API no trae nada nuevo,
- **cuando** pasan 2 segundos con el chat abierto,
- **entonces** la pantalla ya preguntó por mensajes nuevos al menos 3 veces, porque pregunta
  cada medio segundo. Con 3 segundos de intervalo no habría preguntado ninguna.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-19: while it waits for a reply, it asks every half second"

#### C1-20 · Con la conversación respondida, pregunta cada 3 segundos

- **Sale de:** CA-12 · **Tipo:** componente
- **Dado** que la conversación de Lucía termina en la respuesta de Platita, y que la API no
  trae nada nuevo,
- **cuando** pasan 2 segundos con el chat abierto,
- **entonces** la pantalla no preguntó ninguna vez por mensajes nuevos: la primera consulta
  llega a los 3 segundos.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-20: with the conversation answered, it asks every 3 seconds"

#### C1-21 · Al escribir en una conversación respondida, la consulta se adelanta

- **Sale de:** CA-5 y CA-12 · **Tipo:** componente
- **Dado** que la conversación de Lucía termina en la respuesta de Platita, así que la pantalla
  pregunta cada 3 segundos, y que `POST /chat/messages` responde `202`,
- **cuando** escribe "y 1200 de nafta" y aprieta Enter,
- **entonces** antes de que pase 1 segundo desde el envío la pantalla ya preguntó por mensajes
  nuevos: pasa a preguntar cada medio segundo apenas hay un mensaje esperando respuesta, sin
  esperar los 3 segundos que tenía programados.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C1-21: writing in an answered conversation brings the next read forward"

### Corte 2 — errores y estado vacío

- **Aprobado por:** Veronica Zacarias 15/10/2026
- **C2-29 y C2-30, sumados con la revisión de pr-reviewer, y el C2-08 con un reloj distinto para cada worker:** Veronica Zacarias 15/10/2026
- **Total:** 30 casos, 3 unitarios, 19 de integración y 8 de componente.

Salvo que el caso diga otra cosa, valen las condiciones del corte 1: los datos de prueba de
`local`, el chat encendido, Lucía con una sesión abierta y el reloj en las 18:00:00 UTC del 15
de octubre de 2026.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C2-01 | La misma clave dos veces deja un mensaje y responde el original | Integración | CA-3 |
| C2-02 | La misma clave de otro usuario es otro mensaje | Integración | CA-3 |
| C2-03 | Un texto vacío o de solo espacios no se guarda | Integración | CA-4 |
| C2-04 | Sin clave, el mensaje no se guarda | Integración | CA-4 |
| C2-05 | Si guardar la respuesta falla, el mensaje no queda procesado | Unitario | CA-7 |
| C2-06 | Un mensaje con el lock vencido se vuelve a tomar | Integración | CA-5 |
| C2-07 | Un mensaje con el lock vencido sigue antes que los siguientes | Integración | CA-8 |
| C2-08 | Dos workers terminan el mismo mensaje: queda una sola respuesta | Integración | CA-9 |
| C2-09 | Preguntar no renueva la sesión | Integración | CA-14 |
| C2-10 | Escribir sí renueva la sesión | Integración | CA-14 |
| C2-11 | Pablo no ve la conversación de Lucía | Integración | CA-15 |
| C2-12 | Un cursor de la conversación de otro usuario responde 404 | Integración | CA-15 |
| C2-13 | Sin sesión, o con una vencida, no se lee ni se escribe | Integración | CA-16 |
| C2-14 | Con el chat apagado, los dos endpoints responden 404 | Integración | CA-17 |
| C2-15 | Citar una respuesta de Platita a otro usuario no guarda nada | Integración | CA-18 |
| C2-16 | Citar un mensaje que no es una respuesta de Platita no guarda nada | Integración | CA-18 |
| C2-17 | Citar una respuesta de Platita al mismo usuario se guarda | Integración | CA-18 |
| C2-18 | Con el chat encendido en `production`, nada arranca | Unitario | CA-19 |
| C2-19 | Un mensaje purgado no aparece | Integración | CA-20 |
| C2-20 | Lo que llegó por WhatsApp no aparece en el chat | Integración | CA-27 |
| C2-21 | Dos mensajes con la misma hora no se pierden con el cursor | Integración | CA-12 |
| C2-22 | Sin mensajes, una invitación y no un error | Componente | CA-21 |
| C2-23 | Si la primera consulta falla, se ve por qué y se reintenta | Componente | CA-22 |
| C2-24 | Un envío que falla se reintenta con la misma clave | Componente | CA-23 |
| C2-25 | Si una consulta periódica falla, la conversación sigue | Componente | CA-22 |
| C2-26 | Con el chat apagado, el menú no lo ofrece | Componente | CA-17 |
| C2-27 | Si la sesión venció, vuelve la entrada | Componente | CA-16 |
| C2-28 | Un mensaje no se ve dos veces mientras su envío sigue en curso | Componente | CA-10 |
| C2-29 | Un envío que vence después de guardarse queda una sola vez al reintentarlo | Componente | CA-10, CA-11 y CA-23 |
| C2-30 | Dos pedidos a la vez con la misma clave responden el mensaje original | Unitario | CA-3 |

#### C2-01 · La misma clave dos veces deja un mensaje y responde el original

- **Sale de:** CA-3 · **Tipo:** integración
- **Dado** que Lucía ya mandó "gasté 3500 en el súper" con la clave
  `9d2b7c1e-5a4f-4c3b-8e21-7f6a5b4c3d2e`, y recibió `202` con su `id`,
- **cuando** repite el `POST /chat/messages` con la misma clave y el mismo texto,
- **entonces** responde `200` con el mismo `id` y `"status": "pending"`, y `INBOUND_MESSAGE`
  sigue teniendo una sola fila.
- **Test:** `tests/integration/test_chat_errors.py::test_the_same_key_twice_leaves_one_message_and_answers_the_original`

#### C2-02 · La misma clave de otro usuario es otro mensaje

- **Sale de:** CA-3 · **Tipo:** integración
- **Dado** que Lucía mandó un mensaje con la clave `9d2b7c1e-5a4f-4c3b-8e21-7f6a5b4c3d2e`,
- **cuando** Pablo, con su sesión, manda "cobré 50000" con la misma clave,
- **entonces** responde `202` con otro `id`, e `INBOUND_MESSAGE` tiene dos filas, una de cada
  uno.
- **Test:** `tests/integration/test_chat_errors.py::test_the_same_key_of_another_user_is_another_message`

#### C2-03 · Un texto vacío o de solo espacios no se guarda

- **Sale de:** CA-4 · **Tipo:** integración
- **Dado** Lucía sin mensajes,
- **cuando** manda un `POST /chat/messages` con el texto `""`, y otro con el texto `"   "`, cada
  uno con su clave,
- **entonces** los dos responden `422` con `{"error": "invalid_request"}`, e
  `INBOUND_MESSAGE` queda vacía.
- **Test:** `tests/integration/test_chat_errors.py::test_an_empty_text_or_one_of_only_spaces_is_not_stored`

#### C2-04 · Sin clave, el mensaje no se guarda

- **Sale de:** CA-4 · **Tipo:** integración
- **Dado** Lucía sin mensajes,
- **cuando** manda "gasté 3500 en el súper" sin el header `Idempotency-Key`,
- **entonces** responde `422` con `{"error": "invalid_request"}`, e `INBOUND_MESSAGE` queda vacía.
- **Test:** `tests/integration/test_chat_errors.py::test_without_a_key_the_message_is_not_stored`

#### C2-05 · Si guardar la respuesta falla, el mensaje no queda procesado

- **Sale de:** CA-7 · **Tipo:** unitario
- **Dado** un mensaje de Lucía tomado por el worker, y un repositorio de respuestas que falla al
  guardar,
- **cuando** el worker hace la ronda,
- **entonces** la ronda termina con el error, la unidad de trabajo no hizo commit, y el
  mensaje no quedó marcado como procesado.
- **Test:** `tests/unit/test_process_next_message.py::test_if_storing_the_reply_fails_the_message_is_not_left_processed`

#### C2-06 · Un mensaje con el lock vencido se vuelve a tomar

- **Sale de:** CA-5 · **Tipo:** integración
- **Dado** el lock del worker en 2 minutos, y "gasté 3500 en el súper", de Lucía, con
  `status = 'processing'`, `attempts = 1` y `locked_until` 2026-10-15T17:59:00Z, que ya pasó: el
  worker que lo tomó se cayó,
- **cuando** el worker toma el siguiente mensaje,
- **entonces** toma ese: queda con `attempts = 2` y `locked_until` 2026-10-15T18:02:00Z.
- **Test:** `tests/integration/test_message_worker_errors.py::test_a_message_whose_lock_ended_is_taken_again`

#### C2-07 · Un mensaje con el lock vencido sigue antes que los siguientes

- **Sale de:** CA-8 · **Tipo:** integración
- **Dado** "gasté 3500 en el súper", de Lucía, en proceso con el lock vencido como en C2-06, y
  "y 1200 de nafta", suyo, pendiente y posterior,
- **cuando** el worker toma el siguiente mensaje,
- **entonces** toma "gasté 3500 en el súper", y "y 1200 de nafta" sigue `pending`.
- **Test:** `tests/integration/test_message_worker_errors.py::test_a_message_whose_lock_ended_still_goes_before_the_next_ones`

#### C2-08 · Dos workers terminan el mismo mensaje: queda una sola respuesta

- **Sale de:** CA-9 · **Tipo:** integración
- **Dado** que un worker tomó "gasté 3500 en el súper" con `attempts = 1`, se demoró más que su
  lock, y otro worker lo volvió a tomar con `attempts = 2`,
- **cuando** los dos terminan de procesarlo, primero el de `attempts = 1`, a las 18:03:10, y
  después el otro, a las 18:03:20,
- **entonces** `OUTBOUND_MESSAGE` tiene una sola respuesta a ese mensaje, la del segundo, con
  `created_at` 18:03:20, y el mensaje queda `processed`.
- **Test:** `tests/integration/test_message_worker_errors.py::test_two_workers_finish_the_same_message_and_only_one_reply_is_left`

#### C2-09 · Preguntar no renueva la sesión

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** que la sesión de Lucía registró su última actividad a las 17:50,
- **cuando** a las 18:00 pide `GET /chat/messages`,
- **entonces** responde `200`, y la última actividad de la sesión sigue en las 17:50.
- **Test:** `tests/integration/test_chat_errors.py::test_asking_does_not_renew_the_session`

#### C2-10 · Escribir sí renueva la sesión

- **Sale de:** CA-14 · **Tipo:** integración
- **Dado** que la sesión de Lucía registró su última actividad a las 17:50,
- **cuando** a las 18:00 manda un mensaje,
- **entonces** responde `202`, y la última actividad de la sesión pasa a las 18:00.
- **Test:** `tests/integration/test_chat_errors.py::test_writing_renews_the_session`

#### C2-11 · Pablo no ve la conversación de Lucía

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** que Lucía tiene "gasté 3500 en el súper" y su respuesta, y Pablo no tiene mensajes,
- **cuando** Pablo pide `GET /chat/messages`,
- **entonces** responde `200` con la lista vacía y `next_cursor` nulo.
- **Test:** `tests/integration/test_chat_errors.py::test_pablo_does_not_see_the_conversation_of_lucia`

#### C2-12 · Un cursor de la conversación de otro usuario responde 404

- **Sale de:** CA-15 · **Tipo:** integración
- **Dado** que Lucía tiene "gasté 3500 en el súper",
- **cuando** Pablo pide `GET /chat/messages` con `after` igual al `id` de ese mensaje, y después
  con un UUID que no es de ningún mensaje,
- **entonces** los dos responden `404` con `{"error": "not_found"}`: un cursor ajeno y uno que no
  existe no se distinguen.
- **Test:** `tests/integration/test_chat_errors.py::test_a_cursor_of_the_conversation_of_another_user_answers_404`

#### C2-13 · Sin sesión, o con una vencida, no se lee ni se escribe

- **Sale de:** CA-16 · **Tipo:** integración
- **Dado** un pedido sin cookie de sesión, y otro con una sesión de Lucía creada hace 12 horas,
- **cuando** cada uno pide `GET /chat/messages` y `POST /chat/messages`,
- **entonces** los cuatro responden `401` con `{"error": "unauthorized"}`, e `INBOUND_MESSAGE`
  queda vacía.
- **Test:** `tests/integration/test_chat_errors.py::test_without_a_session_or_with_an_expired_one_nothing_is_read_or_written`

#### C2-14 · Con el chat apagado, los dos endpoints responden 404

- **Sale de:** CA-17 · **Tipo:** integración
- **Dado** la API arrancada sin `WEB_CHAT_ENABLED`, y Lucía con una sesión abierta,
- **cuando** pide `GET /chat/messages` y `POST /chat/messages`,
- **entonces** los dos responden `404` con `{"error": "not_found"}`.
- **Test:** `tests/integration/test_chat_errors.py::test_with_the_chat_off_both_endpoints_answer_404`

#### C2-15 · Citar una respuesta de Platita a otro usuario no guarda nada

- **Sale de:** CA-18 · **Tipo:** integración
- **Dado** una respuesta de Platita a Pablo,
- **cuando** Lucía manda un mensaje con `quoted_message_id` igual al `id` de esa respuesta,
- **entonces** responde `404` con `{"error": "not_found"}`, y Lucía no tiene ningún mensaje
  guardado.
- **Test:** `tests/integration/test_chat_errors.py::test_quoting_a_reply_of_platita_to_another_user_stores_nothing`

#### C2-16 · Citar un mensaje que no es una respuesta de Platita no guarda nada

- **Sale de:** CA-18 · **Tipo:** integración
- **Dado** que Lucía ya mandó "gasté 3500 en el súper",
- **cuando** manda otro mensaje con `quoted_message_id` igual al `id` de ese mensaje suyo, y
  otro con un UUID que no es de ningún mensaje,
- **entonces** los dos responden `404`, y Lucía sigue teniendo un solo mensaje guardado.
- **Test:** `tests/integration/test_chat_errors.py::test_quoting_a_message_that_is_not_a_reply_of_platita_stores_nothing`

#### C2-17 · Citar una respuesta de Platita al mismo usuario se guarda

- **Sale de:** CA-18 · **Tipo:** integración
- **Dado** una respuesta de Platita a Lucía,
- **cuando** Lucía manda "era con Galicia" con `quoted_message_id` igual al `id` de esa
  respuesta,
- **entonces** responde `202`, y el mensaje guardado tiene `quoted_outbound_message_id` igual a
  ese `id`.
- **Test:** `tests/integration/test_chat_errors.py::test_quoting_a_reply_of_platita_to_the_same_user_is_stored`

#### C2-18 · Con el chat encendido en `production`, nada arranca

- **Sale de:** CA-19 · **Tipo:** unitario
- **Dado** el entorno con `APP_ENV=production` y `WEB_CHAT_ENABLED=true`,
- **cuando** se lee la configuración,
- **entonces** falla con un mensaje que nombra `WEB_CHAT_ENABLED` y el entorno, y no dice
  ningún otro valor.
- **Test:** `tests/unit/test_settings.py::test_the_web_chat_enabled_in_production_stops_startup`

#### C2-19 · Un mensaje purgado no aparece

- **Sale de:** CA-20 · **Tipo:** integración
- **Dado** que Lucía tiene "gasté 3500 en el súper", con su contenido purgado, y "y 1200 de
  nafta", sin purgar,
- **cuando** pide `GET /chat/messages`,
- **entonces** responde solo "y 1200 de nafta".
- **Test:** `tests/integration/test_chat_errors.py::test_a_purged_message_does_not_show_up`

#### C2-20 · Lo que llegó por WhatsApp no aparece en el chat

- **Sale de:** CA-27 · **Tipo:** integración
- **Dado** que Lucía tiene un mensaje por WhatsApp, con `provider = 'meta'`, y una alerta de
  Platita por WhatsApp, y en el chat web "gasté 3500 en el súper",
- **cuando** pide `GET /chat/messages`,
- **entonces** responde solo "gasté 3500 en el súper".
- **Test:** `tests/integration/test_chat_errors.py::test_what_came_by_whatsapp_does_not_show_up_in_the_chat`

#### C2-21 · Dos mensajes con la misma hora no se pierden con el cursor

- **Sale de:** CA-12 · **Tipo:** integración
- **Dado** que Lucía tiene "gasté 3500 en el súper" y "y 1200 de nafta", los dos con la misma
  hora, las 17:59:00,
- **cuando** pide `GET /chat/messages` con `after` igual al primero de los dos en el orden que
  devolvió la conversación completa,
- **entonces** responde el otro: ninguno de los dos se pierde ni se repite.
- **Test:** `tests/integration/test_chat_errors.py::test_two_messages_at_the_same_time_are_not_lost_with_the_cursor`

Los casos que siguen son de la pantalla, con el dashboard entero, Lucía adentro y la API
simulada, como en el corte 1.

#### C2-22 · Sin mensajes, una invitación y no un error

- **Sale de:** CA-21 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde la lista vacía,
- **cuando** Lucía abre el chat,
- **entonces** ve "Todavía no le escribiste a Platita", el ejemplo de gasto y el campo para
  escribir, sin ninguna alerta.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-22: with no messages, an invitation and not an error"

#### C2-23 · Si la primera consulta falla, se ve por qué y se reintenta

- **Sale de:** CA-22 · **Tipo:** componente
- **Dado** que la primera consulta responde `500`, y la siguiente trae "gasté 3500 en el súper",
- **cuando** Lucía abre el chat, ve el error y aprieta Reintentar,
- **entonces** primero ve "No se pudo abrir la conversación" con "La API respondió con un
  error.", sin el campo para escribir, y después del reintento ve la conversación.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-23: if the first read fails, it says why and it is retried"

#### C2-24 · Un envío que falla se reintenta con la misma clave

- **Sale de:** CA-23 · **Tipo:** componente
- **Dado** que el primer `POST /chat/messages` responde `500` y el segundo `202`,
- **cuando** Lucía envía "gasté 3500 en el súper", ve "No enviado" y aprieta Reintentar,
- **entonces** los dos pedidos llevaron la misma `Idempotency-Key`, el mensaje se ve una sola
  vez, y "No enviado" desaparece.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-24: a send that fails is retried with the same key"

#### C2-25 · Si una consulta periódica falla, la conversación sigue

- **Sale de:** CA-22 · **Tipo:** componente
- **Dado** que el chat de Lucía muestra su conversación, y una consulta periódica responde `500`
  antes de que la siguiente vuelva a responder bien,
- **cuando** pasan las dos consultas,
- **entonces** mientras falla se ve "No se pudo buscar mensajes nuevos. Se reintenta en unos
  segundos." con la conversación en pantalla, y con la consulta buena el aviso desaparece.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-25: if a periodic read fails, the conversation stays"

#### C2-26 · Con el chat apagado, el menú no lo ofrece

- **Sale de:** CA-17 · **Tipo:** componente
- **Dado** que `GET /chat/messages` responde `404`,
- **cuando** Lucía entra,
- **entonces** la sección "Pruebas" del menú tiene solo "Estado del sistema".
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-26: with the chat off, the menu does not offer it"

#### C2-27 · Si la sesión venció, vuelve la entrada

- **Sale de:** CA-16 · **Tipo:** componente
- **Dado** que el chat de Lucía está abierto, y la siguiente consulta responde `401`,
- **cuando** pasa el intervalo de la consulta,
- **entonces** el menú y el chat desaparecen, y se ve la entrada de desarrollo.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-27: if the session expired, the entry comes back"

#### C2-28 · Un mensaje no se ve dos veces mientras su envío sigue en curso

- **Sale de:** CA-10 · **Tipo:** componente
- **Dado** que Lucía envió "gasté 3500 en el súper", y una consulta periódica trae ese mensaje
  mientras el `POST` todavía no respondió,
- **cuando** llega esa consulta,
- **entonces** el mensaje se ve una sola vez, también antes de que responda el `POST`.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-28: a message is not shown twice while its send is still on its way"

#### C2-29 · Un envío que vence después de guardarse queda una sola vez al reintentarlo

- **Sale de:** CA-10, CA-11 y CA-23 · **Tipo:** componente
- **Dado** que Lucía envió "gasté 3500 en el súper", el servidor lo guardó como `im1`, pero el
  `POST` no respondió a tiempo, así que se ve "No enviado"; y que después una consulta trajo
  `im1`,
- **cuando** Lucía aprieta Reintentar, el `POST` responde `200` con `im1`, y la consulta
  siguiente trae la respuesta de Platita,
- **entonces** "gasté 3500 en el súper" se ve una sola vez, "No enviado" desaparece, la
  respuesta de Platita aparece debajo, y "Platita está procesando…" desaparece.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C2-29: a send that timed out after being stored is shown once after its retry"

#### C2-30 · Dos pedidos a la vez con la misma clave responden el mensaje original

- **Sale de:** CA-3 · **Tipo:** unitario
- **Dado** que al buscar la clave de Lucía todavía no hay ningún mensaje, pero al guardarlo
  la base lo rechaza porque otro pedido con la misma clave lo guardó un instante antes,
- **cuando** Lucía manda "gasté 3500 en el súper" con esa clave,
- **entonces** el caso de uso devuelve el mensaje que guardó el otro pedido, como uno que ya
  existía, y no termina con un error.
- **Test:** `tests/unit/test_send_chat_message.py::test_two_requests_at_once_with_the_same_key_answer_the_original_message`

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** Veronica Zacarias 16/10/2026
- **C3-12, sumado para probar contra la base lo que el C2-05 prueba con dobles:** Veronica Zacarias 16/10/2026
- **C3-13 a C3-20, sumados con la revisión de spec-drift:** Veronica Zacarias 16/10/2026
- **C3-21 y C3-22, sumados con la revisión de pr-reviewer:** Veronica Zacarias 16/10/2026
- **Total:** 22 casos, 3 unitarios, 17 de integración y 2 de componente.

Valen las condiciones del corte 1. En los casos de los registros, la API y el worker escriben
sus líneas en un registro que el test lee, y Lucía manda "gasté 3500 en el súper".

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C3-01 | Escribir y leer el chat no deja el texto ni el teléfono en los registros | Integración | CA-24 |
| C3-02 | El worker deja una línea por mensaje respondido, con su identificador | Integración | CA-24 |
| C3-03 | Un error al procesar un mensaje deja su línea con el identificador del mensaje | Integración | CA-24 |
| C3-04 | Sin mensajes esperando, `GET /queuez` responde 200 | Integración | CA-25 |
| C3-05 | Con un mensaje esperando hace más de 10 minutos, responde 503 | Integración | CA-25 |
| C3-06 | Un mensaje reciente, o demorado a propósito, no cuenta | Integración | CA-25 |
| C3-07 | Con el chat encendido, la API lo avisa al arrancar | Integración | CA-26 |
| C3-08 | Con el chat o la entrada encendidos, el worker lo avisa al arrancar | Integración | CA-26 |
| C3-09 | Con los dos apagados, ningún proceso avisa | Integración | CA-26 |
| C3-10 | Los controles del chat tienen nombre y se usan con el teclado | Componente | Accesibilidad |
| C3-11 | Una respuesta nueva se anuncia sin mover el foco | Componente | Accesibilidad |
| C3-12 | Si la base rechaza la respuesta, el mensaje no queda a medias | Integración | CA-7 |
| C3-13 | Sin base, `GET /queuez` responde 503 | Integración | CA-25 |
| C3-14 | Un worker desplazado no deja `message.answered` | Unitario | CA-24 |
| C3-15 | La espera máxima de `/queuez` sale de una variable de entorno | Integración | CA-25 |
| C3-16 | La duración del lock del worker sale de una variable de entorno | Integración | ADR 0010 |
| C3-17 | Con una espera o un lock inválidos, ningún proceso arranca | Unitario | CA-25 y ADR 0010 |
| C3-18 | El error del worker lleva el usuario del mensaje | Integración | CA-24 |
| C3-19 | Un error previsto de un pedido con sesión lleva su usuario | Integración | CA-24 |
| C3-20 | Un error imprevisto de un pedido con sesión lleva su usuario | Integración | CA-24 |
| C3-21 | Cerrar la sesión deja su línea con el usuario | Integración | CA-24 |
| C3-22 | Los identificadores de la línea también pasan por el filtro | Unitario | CA-24 |

#### C3-01 · Escribir y leer el chat no deja el texto ni el teléfono en los registros

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta, y la API escribiendo sus registros,
- **cuando** manda "gasté 3500 en el súper" y pide `GET /chat/messages`,
- **entonces** hay una línea `http.request` con `POST /chat/messages` y otra con
  `GET /chat/messages`, las dos con su `user_id`; y ninguna línea contiene "3500", "súper",
  `+000000000001` ni el nombre "Lucía".
- **Test:** `tests/integration/test_chat_logs.py::test_writing_and_reading_the_chat_leaves_no_text_or_phone_in_the_logs`

#### C3-02 · El worker deja una línea por mensaje respondido, con su identificador

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** un mensaje pendiente de Lucía, "gasté 3500 en el súper", y el worker escribiendo sus
  registros,
- **cuando** el worker hace una ronda,
- **entonces** hay una sola línea `message.answered`, del proceso `worker`, con el `message_id`
  de ese mensaje, el `user_id` de Lucía y su duración; y ninguna línea contiene "3500",
  "súper", `+000000000001` ni "Lucía".
- **Test:** `tests/integration/test_chat_logs.py::test_the_worker_leaves_one_line_per_answered_message_with_its_identifier`

#### C3-03 · Un error al procesar un mensaje deja su línea con el identificador del mensaje

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** un mensaje pendiente de Lucía, y una base que rechaza guardar la respuesta,
- **cuando** el worker hace una ronda en su ciclo,
- **entonces** hay una línea `error.unexpected` con el `message_id` de ese mensaje, la clase
  del error y sin su mensaje; y el worker sigue con la ronda siguiente.
- **Test:** `tests/integration/test_chat_logs.py::test_an_error_processing_a_message_leaves_its_line_with_the_message_identifier`

#### C3-04 · Sin mensajes esperando, `GET /queuez` responde 200

- **Sale de:** CA-25 · **Tipo:** integración
- **Dado** que la tabla de entrada no tiene mensajes pendientes,
- **cuando** se pide `GET /queuez`, sin sesión,
- **entonces** responde `200` con `{"status": "ok"}`.
- **Test:** `tests/integration/test_queue_health.py::test_with_no_message_waiting_queuez_is_ok`

#### C3-05 · Con un mensaje esperando hace más de 10 minutos, responde 503

- **Sale de:** CA-25 · **Tipo:** integración
- **Dado** un mensaje pendiente con `next_attempt_at` a las 17:49:00 UTC, y el reloj a las
  18:00:00,
- **cuando** se pide `GET /queuez`,
- **entonces** responde `503` con `{"status": "unavailable"}`: espera hace 11 minutos.
- **Test:** `tests/integration/test_queue_health.py::test_with_a_message_waiting_more_than_10_minutes_queuez_is_unavailable`

#### C3-06 · Un mensaje reciente, o demorado a propósito, no cuenta

- **Sale de:** CA-25 · **Tipo:** integración
- **Dado** un mensaje pendiente con `next_attempt_at` a las 17:51:00, que espera hace 9
  minutos, y otro con `next_attempt_at` al día siguiente, demorado por un límite de uso,
- **cuando** se pide `GET /queuez`, con el reloj a las 18:00:00,
- **entonces** responde `200` con `{"status": "ok"}`.
- **Test:** `tests/integration/test_queue_health.py::test_a_recent_message_or_one_delayed_on_purpose_does_not_count`

#### C3-07 · Con el chat encendido, la API lo avisa al arrancar

- **Sale de:** CA-26 · **Tipo:** integración
- **Dado** el entorno `local` con `WEB_CHAT_ENABLED=true` y sin la entrada de desarrollo,
- **cuando** arranca la API,
- **entonces** su registro tiene una línea `dev.scaffold_enabled`, de nivel WARNING.
- **Test:** `tests/integration/test_scaffold_warnings.py::test_with_the_chat_on_the_api_says_so_when_it_starts`

#### C3-08 · Con el chat o la entrada encendidos, el worker lo avisa al arrancar

- **Sale de:** CA-26 · **Tipo:** integración
- **Dado** el entorno `local`, una vez con `WEB_CHAT_ENABLED=true` y otra con
  `DEV_ENTRY_ENABLED=true`,
- **cuando** arranca el worker cada vez,
- **entonces** cada vez su registro tiene una línea `dev.scaffold_enabled`, de nivel WARNING,
  del proceso `worker`.
- **Test:** `tests/integration/test_scaffold_warnings.py::test_with_the_chat_or_the_entry_on_the_worker_says_so_when_it_starts`

#### C3-09 · Con los dos apagados, ningún proceso avisa

- **Sale de:** CA-26 · **Tipo:** integración
- **Dado** el entorno `local` sin `WEB_CHAT_ENABLED` ni `DEV_ENTRY_ENABLED`,
- **cuando** arrancan la API y el worker,
- **entonces** ninguno de los dos registros tiene una línea `dev.scaffold_enabled`.
- **Test:** `tests/integration/test_scaffold_warnings.py::test_with_both_off_no_process_says_anything`

#### C3-10 · Los controles del chat tienen nombre y se usan con el teclado

- **Sale de:** la accesibilidad del [contrato de UI](ui_contract.md#accesibilidad) · **Tipo:**
  componente
- **Dado** el chat de Lucía abierto, con un envío que quedó "No enviado",
- **cuando** se recorren sus controles,
- **entonces** el campo se anuncia como "Tu mensaje", y Enviar y Reintentar son botones nativos
  con su nombre, que se alcanzan con Tab; y Enter en el campo envía.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C3-10: the controls of the chat have a name and are used with the keyboard"

#### C3-11 · Una respuesta nueva se anuncia sin mover el foco

- **Sale de:** la accesibilidad del [contrato de UI](ui_contract.md#accesibilidad) · **Tipo:**
  componente
- **Dado** que Lucía tiene el foco en el campo para escribir, y la conversación espera una
  respuesta,
- **cuando** la consulta trae la respuesta de Platita,
- **entonces** la conversación es una región que un lector de pantalla anuncia cuando cambia
  (`role="log"`), la respuesta aparece en ella, y el foco sigue en el campo.
- **Test:** `src/pages/ChatPage.test.tsx` › "case C3-11: a new reply is announced without moving the focus"

#### C3-12 · Si la base rechaza la respuesta, el mensaje no queda a medias

- **Sale de:** CA-7 · **Tipo:** integración
- **Dado** un mensaje pendiente de Lucía, "gasté 3500 en el súper", y una base que rechaza
  guardar la respuesta,
- **cuando** el worker hace una ronda en su ciclo,
- **entonces** en `OUTBOUND_MESSAGE` no hay ninguna respuesta a ese mensaje, y el mensaje sigue
  en `INBOUND_MESSAGE` con `status = 'processing'`, `attempts = 1` y sin `processed_at`: lo
  tomó, y no lo marcó procesado. Cuando venza su lock, un worker lo vuelve a tomar, como en el
  C2-06.
- **Test:** `tests/integration/test_message_worker_errors.py::test_if_the_database_rejects_the_reply_the_message_is_not_left_half_done`

#### C3-13 · Sin base, `GET /queuez` responde 503

- **Sale de:** CA-25 · **Tipo:** integración
- **Dado** una API que no llega a la base,
- **cuando** se pide `GET /queuez`, sin sesión,
- **entonces** responde `503` con `{"status": "unavailable"}`, el mismo cuerpo que su `200`,
  como `GET /readyz`.
- **Test:** `tests/integration/test_queue_health.py::test_without_the_database_queuez_is_unavailable`

#### C3-14 · Un worker desplazado no deja `message.answered`

- **Sale de:** CA-24 · **Tipo:** unitario
- **Dado** un mensaje de Lucía que el worker tomó, y que otro worker volvió a tomar cuando venció
  su lock, antes de que este lo respondiera,
- **cuando** el worker termina la ronda,
- **entonces** no guardó ninguna respuesta y no dejó ninguna línea `message.answered`: esa
  línea la deja solo el worker que respondió.
- **Test:** `tests/unit/test_displaced_worker.py::test_a_displaced_worker_leaves_no_answered_line`

#### C3-15 · La espera máxima de `/queuez` sale de una variable de entorno

- **Sale de:** CA-25 · **Tipo:** integración
- **Dado** la API con `QUEUE_MAX_WAIT_MINUTES=5`, y un mensaje pendiente con `next_attempt_at`
  a las 17:54:00, que espera hace 6 minutos,
- **cuando** se pide `GET /queuez`, con el reloj a las 18:00:00,
- **entonces** responde `503` con `{"status": "unavailable"}`. Sin la variable, la espera es de
  10 minutos, como en el C3-05 y el C3-06.
- **Test:** `tests/integration/test_queue_health.py::test_the_longest_wait_of_queuez_comes_from_an_environment_variable`

#### C3-16 · La duración del lock del worker sale de una variable de entorno

- **Sale de:** el [ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md), que la
  hace configuración · **Tipo:** integración
- **Dado** el worker con `WORKER_LOCK_SECONDS=30`, y un mensaje pendiente de Lucía,
- **cuando** el worker lo toma, con el reloj a las 18:00:00,
- **entonces** el mensaje queda en `processing` con `locked_until` a las 18:00:30. Sin la
  variable, el lock es de 120 segundos.
- **Test:** `tests/integration/test_message_worker_errors.py::test_the_lock_of_the_worker_comes_from_an_environment_variable`

#### C3-17 · Con una espera o un lock inválidos, ningún proceso arranca

- **Sale de:** CA-25 y el ADR 0010 · **Tipo:** unitario
- **Dado** `QUEUE_MAX_WAIT_MINUTES` o `WORKER_LOCK_SECONDS` con un valor que no es un entero
  mayor que cero, como `0`, `-5`, `diez` o `1.5`,
- **cuando** se lee la configuración al arrancar,
- **entonces** falla con un error que nombra la variable y no repite el valor, como con
  `APP_ENV`.
- **Test:** `tests/unit/test_settings.py::test_a_wait_or_a_lock_that_is_not_a_positive_integer_stops_startup`

#### C3-18 · El error del worker lleva el usuario del mensaje

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** un mensaje pendiente de Lucía, y una base que rechaza guardar la respuesta,
- **cuando** el worker hace una ronda en su ciclo,
- **entonces** la línea `error.unexpected` lleva el `user_id` de Lucía, además del
  `message_id` del mensaje.
- **Test:** `tests/integration/test_chat_logs.py::test_the_error_of_the_worker_carries_the_user_of_the_message`

#### C3-19 · Un error previsto de un pedido con sesión lleva su usuario

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta, y un mensaje de Pablo,
- **cuando** Lucía pide `GET /chat/messages?after=` con el id del mensaje de Pablo,
- **entonces** responde `404`, y la línea `error.expected` lleva el `user_id` de Lucía.
- **Test:** `tests/integration/test_chat_logs.py::test_a_foreseen_error_of_a_request_with_a_session_carries_its_user`

#### C3-20 · Un error imprevisto de un pedido con sesión lleva su usuario

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta, y una base que rechaza guardar cualquier mensaje
  entrante,
- **cuando** Lucía manda "gasté 3500 en el súper",
- **entonces** responde `500`, y la línea `error.unexpected` lleva el `user_id` de Lucía.
- **Test:** `tests/integration/test_chat_logs.py::test_an_unforeseen_error_of_a_request_with_a_session_carries_its_user`

#### C3-21 · Cerrar la sesión deja su línea con el usuario

- **Sale de:** CA-24 · **Tipo:** integración
- **Dado** Lucía con una sesión abierta,
- **cuando** pide `POST /auth/logout`,
- **entonces** responde `204`, y la línea `http.request` de `POST /auth/logout` lleva el
  `user_id` de Lucía: el de la sesión que cerró.
- **Test:** —

#### C3-22 · Los identificadores de la línea también pasan por el filtro

- **Sale de:** CA-24 · **Tipo:** unitario
- **Dado** que lo que el proceso tiene como identificador del pedido, del mensaje y del usuario
  no tiene forma de identificador: `+000000000001`, `gasté 3500 en el súper` y `Lucía`,
- **cuando** se escribe una línea de registro,
- **entonces** los campos `request_id`, `message_id` y `user_id` salen como `[redacted]`, y
  ninguno de esos tres textos aparece en la línea. Con un UUID en cada uno, los tres pasan tal
  cual.
- **Test:** —

El contraste de la hora sobre cada burbuja no tiene caso: se calcula con los colores de los
tokens y queda anotado en el [contrato de UI](ui_contract.md#accesibilidad), como en la pantalla
de cuentas.

## Estados de pantalla

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | Mientras la primera consulta de `GET /chat/messages` no respondió | Un indicador de carga, sin el campo para escribir |
| Con contenido | La consulta trajo al menos un mensaje | La conversación, con el campo para escribir abajo |
| Vacío | La consulta respondió sin mensajes | Una invitación con un ejemplo de gasto, y el campo para escribir |
| Error | La primera consulta falló, no respondió a tiempo o no llegó | Qué pasó y un botón para reintentar |

Sin sesión no es un estado de esta pantalla: se muestra la entrada. Una consulta periódica que
falla con la conversación ya en pantalla no la borra: se sigue preguntando, y se ve un aviso
mientras falle. Su detalle va en el corte 2.

## Mensajes al usuario

El texto fijo que responde el worker mientras no haya modelo, en `backend/app/messages.py`:

> Recibí tu mensaje. Todavía no puedo procesarlo.

Lo reemplaza la clasificación, en la funcionalidad siguiente. Los textos de la pantalla van en
`frontend/src/messages.ts`, y están en el [contrato de UI](ui_contract.md#textos).

## Reglas de dominio bajo prueba

Esta funcionalidad no toca movimientos, cuentas ni presupuestos. Las reglas en riesgo son las
del canal.

| Regla | Caso que la cubre |
|---|---|
| Un mensaje nunca queda procesado sin su respuesta ([ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md)) | C1-03, y en el corte 2 la transacción que falla |
| Un usuario a la vez, en orden de llegada ([ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md)) | C1-04, C1-05, C1-10 |
| El usuario sale de la sesión, no del pedido | C1-01, y en el corte 2 Pablo que no ve lo de Lucía |

## Sin cubrir

- Que el worker llegue a la base solo por los casos de uso y los repositorios: lo valida
  `scripts/verify_architecture.py`.
- Que el proceso del worker repita las rondas mientras está vivo, y que `docker compose up` lo
  levante como cuarto servicio: se comprueba a mano, escribiendo en el chat y viendo llegar la
  respuesta. Los tests llaman a una ronda por vez.

## Fuera de alcance

- La clasificación, el registro de un gasto o un ingreso, y toda llamada al modelo.
- Los reintentos con espera creciente, el estado `failed` y su aviso: llegan con el modelo.
- El botón "Responder" y la cita en la pantalla: entrega final.
- La purga del contenido de los mensajes, que es un proceso programado. Lo que entra es que un
  mensaje purgado no se muestre.
- El webhook de WhatsApp.

## Decisiones tomadas al especificar

Las preguntas que se abrieron al escribir este documento, ya resueltas.

1. ~~El texto fijo de la respuesta.~~ Resuelta el 14 de octubre de 2026: "Recibí tu mensaje.
   Todavía no puedo procesarlo.", en `backend/app/messages.py`. Vive hasta que entre la
   clasificación.
2. ~~El nombre de la variable que enciende el chat web.~~ Resuelta el 14 de octubre de 2026:
   `WEB_CHAT_ENABLED`, con las mismas reglas que `DEV_ENTRY_ENABLED`: vale `true` o `false`, sin
   ella queda apagado, con otro valor el proceso no arranca, y encendida con el entorno en
   `production` tampoco arranca. El
   [ADR 0016](../../adr/0016-sesion-de-servidor-en-el-mismo-origen.md) dice que cada opción tiene
   la suya y solo nombraba la de la entrada de desarrollo.
3. ~~Dónde van los reintentos, el estado `failed` y su aviso.~~ Resuelta el 14 de octubre de
   2026: en la funcionalidad del registro de un gasto y de un ingreso, con el modelo, que es lo
   primero que puede fallar al procesar un mensaje
   ([Alcance](#alcance)).
4. ~~Si el worker va en esta funcionalidad o en una aparte.~~ Resuelta el 14 de octubre de 2026:
   va en esta. El chat web no tiene un camino síncrono
   ([ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md)), así que sin el worker
   ningún mensaje recibe respuesta y el corte 1 no llegaría a la pantalla.
5. ~~El botón "Responder".~~ Resuelta el 14 de octubre de 2026: entrega final, con corregir,
   borrar y restaurar ([Alcance](#alcance)).
6. ~~Dónde está el texto de un mensaje en `payload`.~~ Resuelta el 15 de octubre de 2026: un
   mensaje web guarda `{"text": "..."}`, y el worker y la conversación leen el texto de esa
   clave. Un mensaje de Meta lo trae en `text.body`, así que el adaptador de WhatsApp tiene que
   hacer que la lectura del texto dependa del canal, en el repositorio, con un test sobre un
   mensaje real de Meta. Se deja para entonces porque hoy no habría con qué probarlo.
7. ~~El índice de la cola.~~ Resuelta el 15 de octubre de 2026: la consulta que toma el
   siguiente mensaje identifica al remitente por su usuario, o por su teléfono si no tiene,
   como pide el [ADR 0010](../../adr/0010-webhook-asincrono-con-tabla-de-entrada.md). Por eso no
   usa el índice `ix_inbound_message_sender_queue`, que es por teléfono. Con el volumen
   previsto no se nota; si llega a pesar, se suma otro índice en una migración nueva.
