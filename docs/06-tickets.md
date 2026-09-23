# 6. Tickets de trabajo

**Ticket 1 — Backend**

**Título:** Implementar webhook de recepción de mensajes de WhatsApp e interpretación por IA
**HU relacionada:** [HU3](05-historias-de-usuario.md)
**Descripción:** Endpoint `POST /webhook/whatsapp` (adaptador de entrada) que recibe el mensaje y lo pasa al caso de uso `RegisterTransaction`, el cual extrae los datos, exige los que dependen del usuario, y responde por el mismo canal.
**Alcance técnico:**

- Verificación de la firma del webhook antes de procesar.
- Extracción estructurada del mensaje vía LLM (puerto `LLMPort`) con salida validada (monto, moneda, tipo, fecha, categoría candidata, cuenta si se menciona).
- Las reglas de resolución de defaults, cuenta, categoría y presupuesto, y el contenido del mensaje de confirmación, están en [reglas de dominio](reglas-de-dominio.md) § 1, § 3 y § 4. Se implementan tal como están escritas ahí; este ticket no las redefine.
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

- Migración inicial con las tablas `user`, `family_group`, `user_group`, `account`, `budget_period`, `budget`, `category`, `transaction` (con `account_id`, `budget_period_id` y `category_id` `NOT NULL`; `duplicate_of` nullable y autoreferenciado al mismo usuario por clave foránea compuesta `(user_id, duplicate_of)` → `(user_id, id)`), `pending_transaction`, `recurring_expense`, `advice_document`.
- Índice sobre `transaction (user_id, source, amount, transaction_date)` para que el chequeo de duplicados del Ticket 1 sea una consulta rápida, no un escaneo completo.
- Extensión `pgvector` habilitada para `advice_document.embedding`.
- Seed con las categorías base del sistema.
**Criterios de aceptación:** las migraciones corren limpias sobre una base vacía, y la base de datos —no la aplicación— rechaza cada uno de estos inserts: en `budget_period` y en `recurring_expense`, ambos campos de dueño nulos o ambos no nulos; en `transaction`, sin `account_id` o sin `budget_period_id`; en `budget`, un segundo límite para el mismo `(budget_period_id, category_id)`; en `transaction`, un `amount` igual a cero o negativo; un valor fuera del enumerado en `transaction.type`, `transaction.source`, `budget_period.period_type` y `budget_period.status`; y un `duplicate_of` que apunte a una transacción de otro usuario, que la clave foránea compuesta tiene que rechazar.
**Riesgos:** cambios futuros al modelo de datos requieren migraciones adicionales, no reescritura (mitigación: mantener las migraciones versionadas desde el día uno, no editar la inicial).
