# 6. Tickets de trabajo

**Ticket 1 — Backend**

**Título:** Implementar webhook de recepción de mensajes de WhatsApp e interpretación por IA
**HU relacionada:** [HU3](05-historias-de-usuario.md)
**Descripción:** Endpoint `POST /webhook/whatsapp` (adaptador de entrada) que recibe el mensaje y lo pasa al caso de uso `RegisterTransaction`, el cual extrae los datos, exige los que dependen del usuario, y responde por el mismo canal.
**Alcance técnico:**

- Verificación de la firma del webhook antes de procesar, y verificación de la URL por `GET` con `hub.challenge`.
- El webhook no procesa: guarda cada mensaje en `INBOUND_MESSAGE`, sin duplicar reintentos del proveedor, y responde `200`. Un worker toma los mensajes de a uno por remitente y en orden, los procesa con reintentos, y envía las respuestas desde `OUTBOUND_MESSAGE`. Contrato en [la API](04-api.md) y fundamento en el [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md).
- Extracción estructurada del mensaje vía LLM (puerto `LLMPort`) con salida validada (monto, moneda, tipo, fecha, categoría candidata, cuenta si se menciona).
- Las reglas de resolución de defaults, cuenta, categoría y presupuesto, y el contenido del mensaje de confirmación, están en [reglas de dominio](reglas-de-dominio.md) § 1, § 3 y § 4. Se implementan tal como están escritas ahí; este ticket no las redefine.
- Pendientes agrupados en lotes, un solo lote en conversación por usuario, preguntas numeradas y respuestas generales o por número, según [reglas de dominio § 5](reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración).
- Promoción de `PENDING_TRANSACTION` a `TRANSACTION` cuando se completan todos los campos, en una transacción de base de datos.
- Job de expiración de `PENDING_TRANSACTION` vencidas, con un recordatorio previo.
- Endpoint `GET /budgets/{budget_id}` (adaptador de entrada) sobre el caso de uso `GetBudgetStatus`, con el contrato de [la API](04-api.md): límite, gastado convertido a la moneda primaria del período y movimientos asociados. Va en este ticket porque es lo único que consume el Ticket 2 y ninguna otra parte del sistema lo provee: el webhook escribe movimientos, no los expone.
- *Fuera del alcance de este ticket (could-have):* el chequeo de duplicados contra movimientos de origen automático, que depende de la carga por email. El punto de inserción queda identificado dentro del caso de uso para poder sumarlo después sin reescribirlo.
**Criterios de aceptación:** cubren lo definido en [HU3](05-historias-de-usuario.md); además, un mensaje que el LLM no logra interpretar responde pidiendo una aclaración en vez de fallar en silencio.
**Riesgos:** fricción excesiva si el asistente pregunta de más (mitigación: aplicar default a todo lo derivable —fecha, moneda, categoría— y preguntar solo lo que no lo tiene, todo junto en un mensaje con opciones elegibles); un default silencioso que el usuario no note (mitigación: el mensaje de confirmación lista siempre los valores asumidos y acepta corregirlos); interpretación errónea del LLM sobre montos o tipo de movimiento (mitigación: salida estructurada validada y confirmación explícita antes de registrar).

---

**Ticket 2 — Frontend**

**Título:** Vista de detalle de presupuesto por categoría
**HU relacionada:** [HU4](05-historias-de-usuario.md)
**Descripción:** Pantalla del dashboard que consume `GET /budgets/{id}` y muestra límite, gastado y porcentaje usado, con el detalle de movimientos de esa categoría en el período.
**Alcance técnico:**

- Componente de barra de progreso con estado (normal / cerca del límite / excedido).
- Tabla de movimientos del período, con badge de `source` (manual / automático) y de la cuenta afectada.
- Manejo de estado de carga y error de la petición.
- *Should-have:* desglose por moneda original con la cotización usada visible, cuando el soporte multimoneda esté implementado.
**Criterios de aceptación:** cubren lo definido en [HU4](05-historias-de-usuario.md).
**Riesgos:** ninguno de infraestructura; depende de que `GET /budgets/{budget_id}`, que implementa el Ticket 1, esté disponible primero.

---

**Ticket 3 — Base de datos**

**Título:** Esquema inicial y migraciones (users, accounts, budget_periods, budgets, transactions, categories)
**Descripción:** Migraciones de Alembic para las entidades del [modelo de datos](03-modelo-de-datos.md), incluida la restricción de integridad de `BUDGET_PERIOD` (individual XOR familiar), el `UNIQUE (budget_period_id, category_id)` de `BUDGET`, el índice de soporte para el chequeo de duplicados, y los `CHECK` de `TRANSACTION.amount > 0`, `TRANSACTION.type`, `TRANSACTION.source`, `BUDGET_PERIOD.period_type` y `BUDGET_PERIOD.status`.
**Alcance técnico:**

- Migración inicial con las tablas `user`, `family_group`, `user_group`, `account`, `budget_period`, `budget`, `category`, `transaction` (con `account_id`, `budget_period_id` y `category_id` `NOT NULL`; `duplicate_of` nullable y autoreferenciado al mismo usuario por clave foránea compuesta `(user_id, duplicate_of)` → `(user_id, id)`), `pending_transaction`, `recurring_rule`, `advice_document`, `inbound_message`, `outbound_message`, `pending_batch`, `exchange_rate`, `sent_alert`, `login_code`, `financial_profile`, `llm_usage`, `card_purchase`, `card_statement` y `transfer`.
- Índice sobre `transaction (user_id, source, amount, transaction_date)` para que el chequeo de duplicados del Ticket 1 sea una consulta rápida, no un escaneo completo.
- Extensión `pgvector` habilitada para `advice_document.embedding`.
- Índices para las lecturas frecuentes, porque PostgreSQL no indexa solas las claves foráneas: `transaction (account_id)` para el saldo, `transaction (budget_period_id, category_id)` para el estado de un presupuesto, `pending_transaction (batch_id)`, `inbound_message (from_phone, status, sent_at)` para que el worker tome el siguiente mensaje de cada remitente, y `outbound_message (status, next_attempt_at)`.
- Extensión `btree_gist` para las restricciones de exclusión de `budget_period`, y los dos triggers que impiden imputar a un período en `draft`.
- Seed con las categorías base del sistema, de gasto y de ingreso.
**Criterios de aceptación:** las migraciones corren limpias sobre una base vacía, y la base de datos —no la aplicación— rechaza cada uno de estos inserts: en `budget_period` y en `recurring_rule`, ambos campos de dueño nulos o ambos no nulos; en `transaction`, sin `account_id` o sin `budget_period_id`; en `budget`, un segundo límite para el mismo `(budget_period_id, category_id)`; en `transaction`, un `amount` igual a cero o negativo; un valor fuera del enumerado en `transaction.type`, `transaction.source`, `budget_period.period_type` y `budget_period.status`; y un `duplicate_of` que apunte a una transacción de otro usuario, que la clave foránea compuesta tiene que rechazar. También rechaza: en `user_group`, un `role` fuera de `owner`/`member`, un segundo dueño vigente del mismo grupo, un `left_at` anterior a `joined_at` y una membresía duplicada; en `pending_transaction`, un `status` fuera del enumerado, y un `status = 'promoted'` sin `resulting_transaction_id` o al revés; en `transaction` y en `recurring_rule`, una `currency` distinta de la de su cuenta; en `account`, un cambio de `currency` cuando ya tiene movimientos; y en `transaction`, `original_amount`, `original_currency` y `exchange_rate` informados en forma parcial, un `exchange_rate` cero o negativo, o una `original_currency` igual a `currency`; en `transaction`, un segundo movimiento de la misma regla recurrente con la misma `transaction_date`; en `inbound_message`, un segundo mensaje con el mismo `(provider, provider_message_id)`; en `pending_batch`, un segundo lote en conversación para el mismo usuario; y en `pending_transaction`, un `source` distinto del de su lote, un `position` fuera de 1 a 10 o repetido dentro del lote; y en `exchange_rate`, un `rate` cero o negativo, o una segunda cotización con la misma fuente, par de monedas y `rate_at`; en `budget_period`, un período que termina antes de empezar o que se solapa con otro del mismo dueño; en `transaction`, un movimiento imputado a un período en `draft`; en `budget_period`, volver a `draft` un período con movimientos; en `pending_transaction`, un segundo pendiente de la misma regla recurrente y fecha; en `sent_alert`, una segunda alerta para el mismo presupuesto y umbral; en `login_code`, más de 5 intentos; en `user`, un alta completada sin nombre, país o moneda; en `transaction` y en `recurring_rule`, una categoría de otro tipo que el movimiento; y en `category`, dos categorías del mismo usuario, o dos del catálogo base, con el mismo nombre sin distinguir mayúsculas.
**Riesgos:** cambios futuros al modelo de datos requieren migraciones adicionales, no reescritura (mitigación: mantener las migraciones versionadas desde el día uno, no editar la inicial).
