# Especificación — FEAT-002 · Chat web y worker de mensajes

- **Historia de usuario:** [HU3](../../05-historias-de-usuario.md)
- **Estado:** borrador
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
- **CA-26.** Con el chat web encendido, cada proceso lo avisa en su registro al arrancar.

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
- **Total:** 10 casos, 1 unitario y 9 de integración.

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

### Corte 2 — errores y estado vacío

- **Aprobado por:** pendiente

Los casos se escriben antes de empezar el corte. Salen de CA-3, CA-4, CA-7, CA-9, CA-14 a CA-23 y
CA-27: la clave repetida, el texto vacío, la transacción final que falla, el mensaje de un
worker que se cayó y que se retoma cuando vence su lock, dos workers con el mismo mensaje, dos
mensajes con la misma hora que no se pierden al preguntar con el cursor, un cursor que no es
de la conversación del usuario, lo que llegó por WhatsApp que no aparece, la sesión que no se renueva al preguntar, Pablo que no ve lo de Lucía, la sesión que
falta o venció, el chat apagado, la cita a un mensaje ajeno, el arranque en `production`, el
mensaje purgado, y en la pantalla el vacío, el error y el envío que falla.

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

Los casos se escriben antes de empezar el corte. Salen de CA-24 a CA-26 y de la accesibilidad
del [contrato de UI](ui_contract.md#accesibilidad).

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
