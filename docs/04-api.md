# 4. Especificación de la API

> Los tres endpoints principales del flujo descrito en esta entrega. El contrato completo (OpenAPI autogenerado por FastAPI en `/docs`) se agrega en la Entrega 2.

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

Devuelve el estado actual del límite de **una categoría** dentro de un período de presupuesto: límite, gastado hasta el momento (convertido a la moneda primaria del período) y movimientos asociados. El dashboard arma la vista completa del período ([HU2](05-historias-de-usuario.md)) iterando los `BUDGET` de un mismo `budget_period_id` — agregar un endpoint de rollup a nivel de período es candidato para la Entrega 2, no se fuerza acá para no superar los 3 endpoints de esta entrega.

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

Lo que el cliente **no** manda:

- `user_id` no viaja en el cuerpo: sale del `sub` del JWT autenticado. Aceptarlo del cliente sería dejar que cualquiera escriba movimientos en la cuenta de otro.
- `source` lo fija el servidor en `"manual"`, ignorando cualquier valor recibido. Los movimientos `automatic` —el motor de recurrentes y, cuando se implemente, la carga por email— nacen del caso de uso `RegisterTransaction` por dentro, no de este endpoint. Lo que el usuario escribe por WhatsApp y confirma también es `manual`, igual que lo cargado acá, porque lo ingresó él (ver [HU3](05-historias-de-usuario.md)). Así, así que la trazabilidad de origen ([reglas de dominio § 9](reglas-de-dominio.md#9-trazabilidad-de-origen-source)) no depende de la buena fe del cliente.

Validaciones de pertenencia, antes de insertar: `account_id` tiene que ser una cuenta del usuario autenticado; `budget_period_id`, un período de ese usuario o de un grupo familiar al que pertenezca; y `category_id`, una categoría propia del usuario o una del catálogo base del sistema (`user_id` nulo e `is_base = true`), que es exactamente lo que el catálogo mixto de [CATEGORY](03-modelo-de-datos.md#32-descripción-de-entidades-principales) permite. Si no, `404` —no `403`— para no confirmar que el recurso existe.

`transaction_date` y `currency` son opcionales y se resuelven por defecto (hoy y moneda primaria del usuario, respectivamente). El chequeo de duplicados contra la vía automática **no corre en esta entrega**: depende de la carga por email, que es could-have, y el [Ticket 1](06-tickets.md) lo deja fuera de alcance dejando identificado el punto de inserción dentro del caso de uso. Por eso `duplicate_of` viene siempre `null` en la respuesta por ahora. El criterio, para cuando llegue, está en [reglas de dominio § 7](reglas-de-dominio.md#7-chequeo-de-duplicados-entre-origen-manual-y-automático) (ver también [3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales) y [HU1](05-historias-de-usuario.md)).

```yaml
requestBody:
  content:
    application/json:
      example:
        # user_id no se manda: se deriva del JWT
        account_id: "a1..."
        budget_period_id: "bp1..."
        amount: 3500
        type: "expense"
        category_id: "cat-food"
        currency: "ARS"              # opcional — default: user's primary_currency
        transaction_date: "2026-09-15" # opcional — default: today
responses:
  201:
    content:
      application/json:
        example:
          id: "t1..."
          budget_period_id: "bp1..."
          converted_amount: 3500
          duplicate_of: null
          status: "created"
  422:
    description: Missing fields that require a user decision or have no safe default
    content:
      application/json:
        example:
          detail: "missing required fields"
          missing_fields: ["account_id", "budget_period_id"]
  404:
    description: account_id or budget_period_id does not belong to the authenticated user
```
