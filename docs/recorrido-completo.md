# Recorrido completo

El recorrido de un usuario por Platita de punta a punta, desde el primer mensaje hasta el
consejo. En cada paso se ve qué proceso actúa, cómo se hace la llamada y qué tablas se leen o se
escriben. No agrega reglas: las reglas están en [reglas de dominio](reglas-de-dominio.md), las
tablas en el [modelo de datos](03-modelo-de-datos.md) y los contratos en [la API](04-api.md).
Cuando un paso no está especificado, el diagrama lo marca en vez de completarlo.

## 1. Cómo se habla cada pieza

Hay dos formas de llamada y ninguna más:

| Tipo de llamada | Entre quiénes | Cómo |
|---|---|---|
| **HTTPS** | Todo lo que cruza el borde de Platita: el navegador con la API, Meta con el webhook, el worker con Meta y con el proveedor de LLM, los procesos programados con las fuentes de cotización | Requests HTTP con TLS. Meta firma lo que envía y el navegador lleva la cookie de sesión |
| **SQL** | Los tres procesos del backend con PostgreSQL | Siempre a través de un caso de uso y un repositorio. Ningún proceso del backend llama a otro por HTTP: se coordinan por tablas |

Los tres procesos del backend son el servicio web (la API, que además sirve el dashboard), el
worker de mensajes y los procesos programados. La regla completa está en el
[ADR 0001](adr/0001-arquitectura-hexagonal.md).

Dos tablas hacen de cola entre procesos: `INBOUND_MESSAGE`, de la API al worker, y
`OUTBOUND_MESSAGE`, de cualquier proceso al worker, que es el único que envía mensajes
([ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md)).

## 2. Vista general

Las seis etapas y quién actúa en cada una. Las flechas continuas son HTTPS y las punteadas, SQL.

```mermaid
flowchart TB
    U(["👤 Usuario"])
    META["WhatsApp<br/>Meta Cloud API"]
    NAV(["💻 Navegador"])
    LLM["Proveedor de LLM"]
    FX["Fuentes de cotización"]

    subgraph BACKEND["Backend de Platita"]
        API["Servicio web<br/>API FastAPI y dashboard en /app"]
        WK["Worker de mensajes"]
        SCH["Procesos programados"]
    end

    subgraph DB["PostgreSQL"]
        COLAS[("INBOUND_MESSAGE<br/>OUTBOUND_MESSAGE")]
        USUARIO[("APP_USER · ACCOUNT<br/>CATEGORY · FINANCIAL_PROFILE")]
        PRESU[("BUDGET_PERIOD · BUDGET")]
        MOV[("PENDING_BATCH · PENDING_TRANSACTION<br/>TRANSACTION · TRANSFER<br/>RECURRING_RULE · CARD_STATEMENT")]
        APOYO[("EXCHANGE_RATE · SENT_ALERT<br/>ADVICE_DOCUMENT · LLM_USAGE")]
        ACCESO[("LOGIN_CODE · SESSION<br/>AUTH_THROTTLE")]
    end

    U -->|"mensajes"| META
    META -->|"POST /webhook/whatsapp<br/>firmado"| API
    WK -->|"envía respuestas<br/>y plantillas"| META
    WK -->|"interpreta y responde<br/>sin identificadores"| LLM
    SCH -->|"descarga cotizaciones"| FX
    U --> NAV
    NAV -->|"JSON y cookie<br/>de sesión"| API

    API -.->|"guarda el mensaje"| COLAS
    API -.->|"login y lecturas"| ACCESO
    API -.-> PRESU
    API -.-> MOV
    WK -.->|"toma mensajes,<br/>encola respuestas"| COLAS
    WK -.->|"alta y cuentas"| USUARIO
    WK -.->|"pendientes y movimientos"| MOV
    WK -.->|"cuotas y RAG"| APOYO
    SCH -.->|"recurrentes y resúmenes"| MOV
    SCH -.->|"alertas y cotizaciones"| APOYO
    SCH -.->|"avisos"| COLAS

    style BACKEND fill:#f6f8fa,stroke:#8b949e
    style DB fill:#f6f8fa,stroke:#8b949e
```

| Etapa | Por dónde entra | Quién la procesa | Qué escribe | Detalle |
|---|---|---|---|---|
| 1. Alta | WhatsApp | Worker | `APP_USER`, `ACCOUNT`, `FINANCIAL_PROFILE` | [§ 3](#3-alta) |
| 2. Presupuesto del período | Sin especificar | Sin especificar | `BUDGET_PERIOD`, `BUDGET` | [§ 4](#4-presupuesto-del-período) |
| 3. Registro diario | WhatsApp o dashboard | Worker o API | `PENDING_*`, luego `TRANSACTION`, `TRANSFER` o `RECURRING_RULE` | [§ 5](#5-registro-de-un-movimiento-por-whatsapp) |
| 4. Lo que corre solo | Una hora del día | Procesos programados | `TRANSACTION` o `PENDING_TRANSACTION`, `CARD_STATEMENT`, `EXCHANGE_RATE` | [§ 6](#6-recurrentes-y-cuotas-de-tarjeta) y [§ 7](#7-cierre-y-conciliación-de-un-resumen) |
| 5. Avisos y contrastes | Una hora del día | Procesos programados, y el worker para las respuestas | `SENT_ALERT`, `OUTBOUND_MESSAGE`, ajustes en `TRANSACTION` | [§ 8](#8-alertas-y-contraste-mensual-de-saldos) |
| 6. Consulta y consejos | Navegador o WhatsApp | API o worker | `SESSION`, `LLM_USAGE` | [§ 9](#9-dashboard) y [§ 10](#10-consejo-por-whatsapp) |

## 3. Alta

El primer contacto de un número desconocido. Hasta que acepta los términos, solo existe su
mensaje en `INBOUND_MESSAGE`, y no se procesa con IA
([reglas de dominio § 11](reglas-de-dominio.md#11-alta-de-usuario-consentimiento-y-mensajes-proactivos)).

```mermaid
sequenceDiagram
    actor U as Usuario
    participant M as Meta Cloud API
    participant API as Servicio web
    participant W as Worker
    participant DB as PostgreSQL
    participant L as LLM

    U->>M: "gasté 4500 en fotocopias"
    M->>API: HTTPS POST /webhook/whatsapp, firmado
    API->>DB: SQL INSERT INBOUND_MESSAGE, user_id nulo
    API-->>M: 200
    W->>DB: SQL toma el mensaje, sin usuario registrado
    W->>DB: SQL INSERT OUTBOUND_MESSAGE, pedido de términos
    W->>M: HTTPS envía el pedido
    M->>U: términos y política
    U->>M: "acepto"
    M->>API: HTTPS POST /webhook/whatsapp
    API->>DB: SQL INSERT INBOUND_MESSAGE
    W->>DB: SQL INSERT APP_USER con terms_accepted_at
    Note over W,DB: Nombre, país, moneda, zona horaria,<br/>permiso de avisos: UPDATE APP_USER
    W->>L: HTTPS interpreta las cuentas dadas en texto
    W->>DB: SQL INSERT ACCOUNT, una fila por cuenta
    W->>DB: SQL UPDATE APP_USER onboarding_status = completed
    W->>DB: SQL INSERT PENDING_BATCH y PENDING_TRANSACTION<br/>con el primer gasto
    Note over W,DB: Sin especificar: el alta no crea ningún BUDGET_PERIOD,<br/>y el pendiente no tiene período que proponer
    W->>M: HTTPS pregunta por el pendiente
    opt Perfil financiero, se puede saltear
        U->>M: respuestas
        W->>DB: SQL INSERT FINANCIAL_PROFILE
    end
```

## 4. Presupuesto del período

El período tiene que estar confirmado antes de que empiece, y solo un período confirmado recibe
movimientos ([reglas de dominio § 3](reglas-de-dominio.md#3-presupuestos-individual-o-familiar-períodos-y-confirmación-previa-al-inicio)).

```mermaid
sequenceDiagram
    actor U as Usuario
    participant C as Canal sin especificar
    participant S as Procesos programados
    participant DB as PostgreSQL
    participant W as Worker
    participant M as Meta Cloud API

    Note over U,C: Sin especificar: por qué canal se crea y se confirma un período.<br/>La HU2 lo describe, pero 04-api no tiene endpoint y no hay flujo por WhatsApp
    U->>C: arma el período con ingreso estimado y topes
    C->>DB: SQL INSERT BUDGET_PERIOD en draft y un BUDGET por tope
    S->>DB: SQL busca períodos en draft cerca de su period_start
    S->>DB: SQL INSERT OUTBOUND_MESSAGE, plantilla Período sin confirmar
    W->>M: HTTPS envía la plantilla
    M->>U: recordatorio
    U->>C: confirma el período
    C->>DB: SQL UPDATE BUDGET_PERIOD status = confirmed
```

## 5. Registro de un movimiento por WhatsApp

El camino más frecuente. La versión centrada en la experiencia está en
[1.3](01-producto.md#13-diseño-y-experiencia-de-usuario); esta muestra procesos y tablas.

```mermaid
sequenceDiagram
    actor U as Usuario
    participant M as Meta Cloud API
    participant API as Servicio web
    participant DB as PostgreSQL
    participant W as Worker
    participant L as LLM

    U->>M: "gasté 3500 en el super"
    M->>API: HTTPS POST /webhook/whatsapp, firmado
    API->>DB: SQL INSERT INBOUND_MESSAGE, único por wamid
    API-->>M: 200, sin procesar
    W->>DB: SQL claim corto: status processing,<br/>attempts + 1, locked_until
    W->>DB: SQL lee LLM_USAGE, cuota de registro
    W->>L: HTTPS interpreta, con nombres de cuentas<br/>y categorías y sin identificadores
    L-->>W: monto, tipo, categoría candidata
    rect rgb(240, 246, 252)
        Note over W,DB: Una sola transacción SQL
        W->>DB: UPDATE INBOUND_MESSAGE processed<br/>solo si attempts no cambió
        W->>DB: lee ACCOUNT, CATEGORY y BUDGET_PERIOD candidatos
        W->>DB: INSERT PENDING_BATCH y PENDING_TRANSACTION
        W->>DB: INSERT OUTBOUND_MESSAGE con la pregunta
        W->>DB: UPDATE LLM_USAGE
    end
    W->>M: HTTPS envía la pregunta
    W->>DB: SQL UPDATE OUTBOUND_MESSAGE sent
    M->>U: "¿De qué cuenta salió y a qué presupuesto va?"
    U->>M: "Galicia, el familiar"
    M->>API: HTTPS POST /webhook/whatsapp
    API->>DB: SQL INSERT INBOUND_MESSAGE
    W->>L: HTTPS interpreta la respuesta
    rect rgb(240, 246, 252)
        Note over W,DB: Una sola transacción SQL
        W->>DB: UPDATE INBOUND_MESSAGE processed, con el mismo fencing
        W->>DB: INSERT TRANSACTION, o TRANSFER, o RECURRING_RULE<br/>si es una compra con tarjeta
        W->>DB: UPDATE PENDING_TRANSACTION promoted<br/>y cierra el PENDING_BATCH
        W->>DB: INSERT OUTBOUND_MESSAGE con la confirmación
    end
    W->>M: HTTPS envía la confirmación
    M->>U: "Listo. $3.500 · comida · Galicia · familiar"
```

Desde el dashboard, el mismo movimiento entra por `POST /transactions` y el servicio web escribe
`TRANSACTION` en una sola transacción SQL, sin pendiente, porque la pantalla ya pidió todos los
datos ([la API](04-api.md)). Que el dashboard sea un canal de carga está en discusión: el
[ADR 0002](adr/0002-whatsapp-como-canal-principal.md) dice que no.

## 6. Recurrentes y cuotas de tarjeta

Lo que genera un proceso programado sin que el usuario escriba nada
([reglas de dominio § 8](reglas-de-dominio.md#8-movimientos-recurrentes-la-excepción-a-la-confirmación)).
Las reglas sobre una tarjeta no se generan en su fecha: esperan al cierre del resumen (§ 7).

```mermaid
sequenceDiagram
    participant S as Procesos programados
    participant DB as PostgreSQL
    participant W as Worker
    participant M as Meta Cloud API
    actor U as Usuario

    S->>DB: SQL lee RECURRING_RULE activas, sin borrar,<br/>con next_execution hasta hoy y cuenta que no es tarjeta
    alt Hay período confirmado del dueño y la moneda coincide
        rect rgb(240, 246, 252)
            Note over S,DB: Una sola transacción SQL
            S->>DB: INSERT TRANSACTION source automatic,<br/>único por regla y ocurrencia
            S->>DB: UPDATE RECURRING_RULE next_execution<br/>y generated_occurrences
        end
    else Sin período confirmado, o hay que convertir moneda
        rect rgb(240, 246, 252)
            Note over S,DB: Una sola transacción SQL
            S->>DB: INSERT PENDING_TRANSACTION sin vencimiento
            S->>DB: UPDATE RECURRING_RULE
            S->>DB: INSERT OUTBOUND_MESSAGE, plantilla<br/>Recurrente o cuota por confirmar
        end
        W->>M: HTTPS envía la plantilla
        M->>U: "Se generó el alquiler, ¿lo confirmás?"
    end
```

## 7. Cierre y conciliación de un resumen

La tarjeta es una cuenta, cada compra es una regla y pagar el resumen es una transferencia
([reglas de dominio § 13](reglas-de-dominio.md#13-tarjetas-de-crédito-y-transferencias)).

```mermaid
sequenceDiagram
    participant S as Procesos programados
    participant DB as PostgreSQL
    participant W as Worker
    participant M as Meta Cloud API
    actor U as Usuario

    S->>DB: SQL busca CARD_STATEMENT open con closing_date hasta hoy
    rect rgb(240, 246, 252)
        Note over S,DB: Una sola transacción SQL
        S->>DB: UPDATE CARD_STATEMENT closed
        S->>DB: INSERT TRANSACTION por cada ocurrencia del resumen,<br/>con fecha de vencimiento, o PENDING_TRANSACTION
        S->>DB: UPDATE RECURRING_RULE de cada compra
        S->>DB: INSERT OUTBOUND_MESSAGE, plantilla Conciliación del resumen
    end
    W->>M: HTTPS envía la plantilla
    M->>U: "¿Cuál es el total a pagar de tu resumen?"
    U->>M: "184.300"
    Note over W,DB: Entra por el webhook como cualquier mensaje (§ 5)
    W->>DB: SQL compara con la deuda del próximo vencimiento
    W->>DB: SQL INSERT PENDING_TRANSACTION con el ajuste
    U->>M: confirma el ajuste
    rect rgb(240, 246, 252)
        Note over W,DB: Una sola transacción SQL
        W->>DB: INSERT TRANSACTION en Intereses, impuestos y cargos,<br/>o en Devoluciones y reintegros
        W->>DB: UPDATE CARD_STATEMENT reconciled
    end
    U->>M: "pagué la visa con la Galicia"
    W->>DB: SQL INSERT TRANSFER de Galicia a la tarjeta,<br/>tras confirmar como en § 5
```

## 8. Alertas y contraste mensual de saldos

Dos avisos que inicia Platita, solo si el usuario dio permiso
([reglas de dominio § 11](reglas-de-dominio.md#11-alta-de-usuario-consentimiento-y-mensajes-proactivos)).

```mermaid
sequenceDiagram
    participant S as Procesos programados
    participant DB as PostgreSQL
    participant W as Worker
    participant L as LLM
    participant M as Meta Cloud API
    actor U as Usuario

    S->>DB: SQL suma el gastado de cada BUDGET de períodos confirmados,<br/>sin borrados ni duplicados
    opt Pasó un umbral y no hay SENT_ALERT para ese umbral
        Note over S,L: En discusión: la alerta lleva un consejo del RAG,<br/>pero los procesos programados no llegan al LLM
        rect rgb(240, 246, 252)
            Note over S,DB: Una sola transacción SQL
            S->>DB: INSERT SENT_ALERT
            S->>DB: INSERT OUTBOUND_MESSAGE, plantilla Alerta de presupuesto
        end
        W->>M: HTTPS envía la alerta
    end
    Note over S,DB: Al terminar el mes de presupuesto
    S->>DB: SQL calcula el saldo de cada cuenta que no es tarjeta:<br/>ACCOUNT, TRANSACTION y TRANSFER hasta ese día
    S->>DB: SQL INSERT OUTBOUND_MESSAGE, plantilla Saldos del mes
    W->>M: HTTPS envía los saldos
    M->>U: "¿Coinciden con lo que tenés?"
    U->>M: "en MP tengo 12.000 menos"
    W->>L: HTTPS interpreta la respuesta
    W->>DB: SQL INSERT PENDING_TRANSACTION con el ajuste
    Note over W,DB: Confirmado, se promueve a TRANSACTION en<br/>Faltantes o Sobrantes sin identificar (§ 5)
```

## 9. Dashboard

El dashboard es una aplicación que el servicio web sirve bajo `/app`, en el mismo origen que la
API. No tiene acceso a la base: todo lo que muestra lo pide por HTTPS
([ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md)).

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant API as Servicio web
    participant DB as PostgreSQL
    participant W as Worker
    participant M as Meta Cloud API

    N->>API: HTTPS GET /app
    API-->>N: la aplicación del dashboard
    N->>API: HTTPS POST /auth/code con el teléfono
    rect rgb(240, 246, 252)
        Note over API,DB: Una sola transacción SQL
        API->>DB: INSERT AUTH_THROTTLE y cuenta los pedidos recientes
        API->>DB: INSERT LOGIN_CODE, solo si el número es de un usuario
        API->>DB: INSERT OUTBOUND_MESSAGE, plantilla Código de login
    end
    API-->>N: 202, igual exista o no el usuario
    W->>M: HTTPS envía el código
    M->>U: código de 6 dígitos
    N->>API: HTTPS POST /auth/token con el código
    API->>DB: SQL valida LOGIN_CODE, marca used_at, INSERT SESSION
    API-->>N: 204 y cookie __Host-sid
    N->>API: HTTPS GET /budgets/id con la cookie
    API->>DB: SQL valida SESSION y actualiza last_seen_at
    API->>DB: SQL lee BUDGET, BUDGET_PERIOD y TRANSACTION,<br/>solo del usuario y de sus grupos
    API-->>N: JSON con tope, gastado y porcentaje
```

## 10. Consejo por WhatsApp

Una pregunta financiera usa la otra cuota diaria y la base de conocimiento
([reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente)). El modelo nunca
consulta la base: recibe solo lo que el caso de uso le envía
([ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md)).

```mermaid
sequenceDiagram
    actor U as Usuario
    participant M as Meta Cloud API
    participant API as Servicio web
    participant DB as PostgreSQL
    participant W as Worker
    participant L as LLM

    U->>M: "¿cómo me conviene pagar la tarjeta?"
    M->>API: HTTPS POST /webhook/whatsapp
    API->>DB: SQL INSERT INBOUND_MESSAGE
    W->>DB: SQL claim del mensaje y lectura de LLM_USAGE, cuota de consejos
    W->>L: HTTPS genera el embedding de la pregunta
    W->>DB: SQL busca en ADVICE_DOCUMENT por similitud, con pgvector
    W->>DB: SQL lee datos agregados: deuda de la tarjeta,<br/>gastado del período, FINANCIAL_PROFILE
    W->>L: HTTPS pregunta, fragmentos y agregados, sin identificadores
    L-->>W: respuesta
    rect rgb(240, 246, 252)
        Note over W,DB: Una sola transacción SQL
        W->>DB: UPDATE INBOUND_MESSAGE processed, con fencing
        W->>DB: UPDATE LLM_USAGE
        W->>DB: INSERT OUTBOUND_MESSAGE con la respuesta
    end
    W->>M: HTTPS envía la respuesta
```

## 11. Lo que el recorrido deja a la vista

Los diagramas marcan cuatro puntos que la especificación todavía no resuelve:

- **El alta no crea un período** (§ 3). El primer gasto queda pendiente sin un período que
  proponer.
- **No hay canal para armar y confirmar un período** (§ 4). La HU2 lo pide, pero no hay endpoint
  en [la API](04-api.md) ni un flujo por WhatsApp.
- **Las alertas usan el LLM, pero los procesos programados no llegan a él** (§ 8). Ya está en
  las decisiones abiertas de la [hoja de ruta](hoja-de-ruta.md#decisiones-abiertas).
- **El dashboard como canal de carga** (§ 5). El ADR 0002 y la API dicen cosas distintas.

El alta de cuentas desde el dashboard, que pide la HU1, tampoco tiene endpoint en
[la API](04-api.md), que por ahora documenta solo los endpoints principales.
