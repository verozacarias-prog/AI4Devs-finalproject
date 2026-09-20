# 4. Especificación de la API

> Los tres endpoints principales del flujo descrito en esta entrega. El contrato completo (OpenAPI autogenerado por FastAPI en `/docs`) se agrega en la Entrega 2.

### `POST /webhook/whatsapp`

Recibe los mensajes entrantes desde el proveedor de WhatsApp Business y dispara la interpretación por IA. El contenido del mensaje viaja en el idioma real del usuario (español).

```yaml
requestBody:
  content:
    application/json:
      example:
        from: "+5491100000000"
        message: "gasté 3500 pesos en el super con la Galicia"
        timestamp: "2026-09-15T14:32:00Z"
responses:
  200:
    description: Message processed; the assistant replies over the same channel
    content:
      application/json:
        example:
          status: "processed"
          transaction_created: true
```

### `GET /budgets/{budget_id}`

Devuelve el estado actual del límite de **una categoría** dentro de un período de presupuesto: límite, gastado hasta el momento (convertido a la moneda primaria del período) y movimientos asociados. El dashboard arma la vista completa del período ([HU2](05-historias-de-usuario.md)) iterando los `BUDGET` de un mismo `budget_period_id` — agregar un endpoint de rollup a nivel de período es candidato para la Entrega 2, no se fuerza acá para no superar los 3 endpoints de esta entrega.

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

Registra un movimiento manualmente (usado por el dashboard, y también internamente por el flujo de WhatsApp una vez confirmado, y por el motor de recurrentes). `amount`, `type`, `category_id`, `account_id` y `budget_period_id` son obligatorios: si falta alguno se rechaza con `422`. Los dos últimos no se derivan acá porque dependen de una decisión del usuario, que se resuelve antes de llegar a este endpoint. `transaction_date` y `currency` son opcionales y se resuelven por defecto (hoy y moneda primaria del usuario, respectivamente). Antes de insertar, el caso de uso corre el chequeo de duplicados contra la vía automática (ver [3.2](03-modelo-de-datos.md#32-descripción-de-entidades-principales), [HU1](05-historias-de-usuario.md) y [reglas de dominio § 7](reglas-de-dominio.md#7-chequeo-de-duplicados-entre-origen-manual-y-automático)).

```yaml
requestBody:
  content:
    application/json:
      example:
        user_id: "u1..."
        account_id: "a1..."
        budget_period_id: "bp1..."
        amount: 3500
        type: "expense"
        category_id: "cat-food"
        source: "manual"
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
```
