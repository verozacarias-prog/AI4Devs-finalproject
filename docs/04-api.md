# 4. Especificación de la API

> Los endpoints principales del flujo descrito en esta entrega. El contrato completo (OpenAPI autogenerado por FastAPI en `/docs`) se agrega en la Entrega 2.

**Aislamiento entre usuarios, en todo endpoint autenticado.** El usuario sale siempre de la sesión autenticada, nunca del cuerpo, de la ruta ni de un parámetro. Toda lectura o escritura se limita a los recursos de ese usuario y de los grupos familiares a los que pertenece, según [reglas de dominio § 10](reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad). Un recurso que existe pero es de otro usuario responde `404`, igual que uno que no existe, para no confirmar su existencia. Cada endpoint lo detalla para sus propios recursos, pero la regla vale aunque no lo diga.

### `POST /webhook/whatsapp`

Recibe los mensajes entrantes desde la Cloud API de Meta. **No los procesa**: verifica la firma, los guarda y confirma la recepción. La interpretación por IA, el registro y la respuesta al usuario ocurren después, en el worker, y la respuesta viaja por WhatsApp, no en este response. El fundamento está en el [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md).

- La firma `X-Hub-Signature-256` se verifica sobre el cuerpo crudo antes de parsearlo. Si no es válida: `401` y no se guarda nada.
- Cada mensaje se guarda una sola vez por `(provider, provider_message_id)`, donde el identificador es el `wamid` de Meta. Un reintento de Meta del mismo mensaje responde `200` y no genera nada nuevo.
- Los eventos de estado (`statuses`: entregado, leído) responden `200` y no se guardan.
- El texto del mensaje viaja en el idioma real del usuario (español).

```yaml
parameters:
  - in: header
    name: X-Hub-Signature-256
    required: true
    example: "sha256=<HMAC-SHA256 of the raw body with the app secret>"
requestBody:
  content:
    application/json:
      example:
        # Recortado a los campos que se usan; el resto del payload de Meta se ignora.
        object: "whatsapp_business_account"
        entry:
          - changes:
              - field: "messages"
                value:
                  messages:
                    - id: "wamid.HBgN..."   # provider_message_id
                      from: "5491100000000"
                      timestamp: "1789482720"
                      type: "text"
                      context:                # only when the user replies quoting a message
                        id: "wamid.QUESTION..."  # the quoted outbound message; routes the reply to its batch
                      text:
                        body: "gasté 3500 pesos en el super con la Galicia"
responses:
  200:
    description: Received and stored (or already stored, or a status event); processing happens later
  401:
    description: Missing or invalid signature; nothing is stored
```

La misma ruta atiende la verificación de la URL que Meta hace al configurar el webhook: `GET /webhook/whatsapp` con `hub.mode=subscribe`, `hub.verify_token` y `hub.challenge`. Si el token coincide con el configurado, responde `200` con el valor de `hub.challenge` como texto plano. Si no, `403`.

### `GET /budgets/{budget_id}`

Devuelve el estado actual del límite de **una categoría** dentro de un período de presupuesto: límite, gastado hasta el momento (convertido a la moneda primaria del período) y movimientos asociados. El dashboard arma la vista completa del período ([HU2](05-historias-de-usuario.md)) iterando los `BUDGET` de un mismo `budget_period_id` — agregar un endpoint de rollup a nivel de período es candidato para la Entrega 2.

Quién puede leerlo: si el período es individual, solo su dueño. Si es familiar, cualquier miembro
vigente del grupo, que ve todos los movimientos del período sin importar quién los registró, y
quien haya salido del grupo, solo si el período se superpone con su intervalo de membresía
([reglas de dominio § 10](reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad)).
En cualquier otro caso, `404`, por el mismo criterio que `POST /transactions`.

```yaml
responses:
  200:
    content:
      application/json:
        example:
          id: "c1a2..."
          budget_period_id: "bp1..."
          category: "food"
          primary_currency: "ARS"
          limit_amount: 300000
          spent_amount: 214500
          used_percentage: 71.5
```

### `POST /transactions`

Registra un movimiento manualmente desde el dashboard. `amount`, `type`, `category_id`, `account_id` y `budget_period_id` son obligatorios: si falta alguno se rechaza con `422`. Los dos últimos no se derivan acá porque dependen de una decisión del usuario, que se resuelve antes de llegar a este endpoint.

**Un pedido repetido no crea un segundo movimiento.** El cliente manda un header `Idempotency-Key` con un UUID que genera una sola vez por cada movimiento que el usuario quiere cargar, y lo reenvía igual si repite el pedido, por un doble clic o porque se cortó la conexión antes de recibir la respuesta. El servidor lo guarda en `client_request_id`, con una clave única por usuario. Si llega una clave que ese usuario ya usó, no inserta nada y responde `200` con el movimiento que creó la primera vez. Si llegan dos pedidos con la misma clave a la vez, la clave única hace que uno solo inserte. Sin el header, `422`.

Lo que el cliente **no** manda:

- `user_id` no viaja en el cuerpo: sale de la sesión autenticada. Aceptarlo del cliente sería dejar que cualquiera escriba movimientos en la cuenta de otro.
- `source` lo fija el servidor en `"manual"`, ignorando cualquier valor recibido. Los movimientos `automatic` —el motor de recurrentes y, cuando se implemente, la carga por email— nacen del caso de uso `RegisterTransaction` por dentro, no de este endpoint. Lo que el usuario escribe por WhatsApp y confirma también es `manual`, igual que lo cargado acá, porque lo ingresó él (ver [HU3](05-historias-de-usuario.md)). Así, así que la trazabilidad de origen ([reglas de dominio § 9](reglas-de-dominio.md#9-trazabilidad-de-origen-source)) no depende de la buena fe del cliente.

Validaciones de pertenencia, antes de insertar: `account_id` tiene que ser una cuenta del usuario autenticado; `budget_period_id`, un período de ese usuario o de un grupo familiar al que pertenezca; y `category_id`, una categoría propia del usuario o una del catálogo base del sistema (`user_id` nulo e `is_base = true`), que es exactamente lo que el catálogo mixto de [CATEGORY](03-modelo-de-datos.md#category) permite. Si no, `404` —no `403`— para no confirmar que el recurso existe.

`transaction_date` y `currency` son opcionales. La fecha es hoy por defecto; la moneda es la de la cuenta indicada en `account_id`, porque un movimiento va siempre en la moneda de su cuenta ([reglas de dominio § 2](reglas-de-dominio.md#2-cuentas-y-saldo-calculado)). Si llega una `currency` distinta de la de la cuenta, se rechaza con `422`: este endpoint no convierte, y la conversión con `original_amount`, `original_currency` y `exchange_rate` es solo del flujo conversacional.

La conversión a la moneda del presupuesto sí ocurre acá. Si la moneda de la cuenta es distinta de la del período, `budget_exchange_rate` es obligatorio: es la cotización que el dashboard le sugirió al usuario y que él confirmó o corrigió en pantalla ([reglas de dominio § 6](reglas-de-dominio.md#6-multimoneda-y-cotización)). El servidor calcula `converted_amount` con ese valor y no lo reemplaza por otro. Si las monedas difieren y falta, o si coinciden y viene informado, se rechaza con `422`.

El chequeo de duplicados contra la vía automática **no corre en esta entrega**: depende de la carga por email, que es could-have, y el [Ticket 1](06-tickets.md) lo deja fuera de alcance dejando identificado el punto de inserción dentro del caso de uso. Por eso `duplicate_of` viene siempre `null` en la respuesta por ahora. El criterio, para cuando llegue, está en [reglas de dominio § 7](reglas-de-dominio.md#7-chequeo-de-duplicados-entre-origen-manual-y-automático) (ver también [3.2](03-modelo-de-datos.md#transaction) y [HU1](05-historias-de-usuario.md)).

```yaml
parameters:
  - in: header
    name: Idempotency-Key
    required: true
    example: "6f1c2a4e-8b3d-4f7a-9c21-0d5e7b3a9f10"  # one UUID per intended movement, reused on retries
requestBody:
  content:
    application/json:
      example:
        # user_id no se manda: se deriva de la sesión
        account_id: "a1..."
        budget_period_id: "bp1..."
        amount: 3500
        type: "expense"
        category_id: "cat-food"
        currency: "ARS"              # opcional — default: the account's currency; any other is 422
        transaction_date: "2026-09-15" # opcional — default: today in the user's time_zone
        budget_exchange_rate: null     # required only when the account and the period differ in currency
responses:
  201:
    content:
      application/json:
        example:
          id: "t1..."
          budget_period_id: "bp1..."
          converted_amount: 3500
          budget_exchange_rate: null
          duplicate_of: null
          status: "created"
  200:
    description: The Idempotency-Key was already used by this user; nothing is inserted and the body is the movement created the first time
  422:
    description: Missing fields that require a user decision or have no safe default, or missing Idempotency-Key
    content:
      application/json:
        example:
          detail: "missing required fields"
          missing_fields: ["account_id", "budget_period_id"]
  404:
    description: account_id, budget_period_id or category_id does not belong to the authenticated user (category_id may also be from the base catalog)
```

### `POST /auth/code`, `POST /auth/token`, `POST /auth/logout` y `POST /auth/logout-all`

El login del dashboard, sin contraseñas: el usuario pide un código, lo recibe por WhatsApp y lo canjea por una sesión. El fundamento está en el [ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md), los límites en el [ADR 0017](adr/0017-limites-del-login-y-codigos-con-proposito.md), y las restricciones del código y de la sesión en [LOGIN_CODE, SESSION y AUTH_THROTTLE](03-modelo-de-datos.md#32-descripción-de-entidades-principales).

**Cómo viaja la sesión.** En una cookie `__Host-sid` con `HttpOnly`, `Secure`, `SameSite=Strict` y `Path=/`, sin `Domain`. El dashboard se sirve desde el mismo origen que la API, bajo `/app`, y la API no habilita CORS. Un `POST`, `PUT`, `PATCH` o `DELETE` responde `403` si su `Origin` no es el de Platita o si su `Content-Type` no es `application/json`. `/webhook/whatsapp` está exceptuado, porque Meta lo llama sin cookie y firma cada pedido. Una request con una sesión inexistente, revocada o vencida responde `401`.

`POST /auth/code` pide un código para un número. Responde `202` **siempre igual**, exista o no un usuario con ese número, para no revelar quién usa Platita; solo si existe se genera y se envía un código de propósito `login`. Admite como mucho 3 pedidos por número cada 15 minutos y 20 por IP por hora, contados exista o no el usuario: pasado cualquiera de los dos responde `429` y no envía nada, porque cada envío es un mensaje de plantilla que se paga y que el dueño del número recibe.

`POST /auth/token` canjea un código de propósito `login`. Si es válido, no venció, no se usó y no agotó sus 5 intentos, lo marca como usado, crea una sesión y la devuelve en la cookie. En cualquier otro caso responde `401` con el mismo mensaje, sin decir cuál de las condiciones falló, y cuenta un fallo para el número y para la IP. Con 10 fallos por número o 50 por IP en el día, responde `429` sin mirar el código, exista o no el usuario. El intento se cuenta antes de comparar el código.

`POST /auth/logout` revoca la sesión de la request. `POST /auth/logout-all` revoca todas las sesiones del usuario, incluida la actual. Las dos responden `204` y borran la cookie.

```yaml
# POST /auth/code
requestBody:
  content:
    application/json:
      example:
        phone: "+5491100000000"
responses:
  202:
    description: Accepted; a code is sent over WhatsApp only if the number belongs to a user
  429:
    description: Too many code requests for this number or this IP; nothing is sent

# POST /auth/token
requestBody:
  content:
    application/json:
      example:
        phone: "+5491100000000"
        code: "482913"
responses:
  204:
    description: Session created
    headers:
      Set-Cookie:
        example: "__Host-sid=<random token>; HttpOnly; Secure; SameSite=Strict; Path=/"
  401:
    description: Invalid, expired, used or exhausted code — same response for all
  429:
    description: Too many failed exchanges today for this number or this IP; the code is not checked

# POST /auth/logout · POST /auth/logout-all
responses:
  204:
    description: Current session (logout) or every session of the user (logout-all) revoked; the cookie is cleared
  401:
    description: No valid session
```

### `GET /family-groups/{family_group_id}/export`

Descarga la exportación de un grupo familiar en Excel, con las hojas "Movimientos" y
"Presupuestos" descritas en [reglas de dominio § 10](reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad).
El archivo se genera en el momento y no se guarda. Incluye solo los períodos que el usuario
autenticado puede leer: todos si es miembro vigente, y los que se superponen con su membresía si
salió. Si nunca fue miembro del grupo, `404`.

Se genera con `openpyxl`: la librería estándar de Python no escribe archivos `.xlsx`, y un CSV,
que sí escribe, se abre mal en el Excel en español y no admite dos hojas (AGENTS.md §9).

```yaml
responses:
  200:
    content:
      application/vnd.openxmlformats-officedocument.spreadsheetml.sheet:
        example: "<binary .xlsx with sheets 'Movimientos' and 'Presupuestos'>"
  404:
    description: The authenticated user was never a member of this family group
```

### `GET /me/export`, `POST /me/deletion/code`, `POST /me/deletion` y `DELETE /me/deletion`

Los derechos de acceso y supresión de [reglas de dominio § 14](reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos).

- `GET /me/export` descarga todos los datos del usuario autenticado en Excel, generado en el
  momento, igual que la exportación de un grupo familiar.
- `POST /me/deletion/code` envía por WhatsApp un código de propósito `account_deletion`, con
  una plantilla que dice para qué es. Exige sesión, así que nadie puede hacerle llegar a otro un
  código de borrado. Comparte el límite de pedidos de `POST /auth/code` y responde `202`.
- `POST /me/deletion` pide el borrado de la cuenta. Exige un código obtenido con
  `POST /me/deletion/code`: uno de login no sirve. Responde `409` si el usuario es dueño de un grupo familiar y todavía no
  transfirió el rol. Si todo está en orden, desactiva la cuenta, revoca todas sus sesiones y
  devuelve cuándo se hará el borrado.
- `DELETE /me/deletion` cancela el borrado mientras dure el plazo de gracia. Como el pedido
  cerró todas las sesiones, para cancelar hay que volver a entrar con un código: una cuenta
  desactivada puede iniciar sesión mientras dure el plazo.

```yaml
# POST /me/deletion
requestBody:
  content:
    application/json:
      example:
        code: "482913"
responses:
  202:
    content:
      application/json:
        example:
          account_status: "deactivated"
          deletion_at: "2026-10-01T12:00:00Z"
  401:
    description: Invalid, expired, used or exhausted code, or a code with another purpose
  409:
    description: The user owns a family group and must transfer the role first
```
