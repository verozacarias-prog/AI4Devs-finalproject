# 2. Arquitectura del sistema

> **Nota de idioma:** todo el desarrollo (código, nombres de tablas y campos, endpoints, payloads) va en **inglés**, de acá en adelante en todo el documento. El texto explicativo de esta entrega queda en español porque es el idioma de la documentación del curso; lo que el usuario final lee o le dice al asistente por WhatsApp también sigue en español, porque el público objetivo del producto es hispanohablante.

### **2.1. Diagrama de arquitectura:**

La arquitectura se documenta siguiendo el **modelo C4 de Simon Brown**, en tres niveles de zoom: contexto (quién usa el sistema y con qué se integra), contenedores (las piezas desplegables) y componentes (el interior del backend). Los diagramas están escritos en **Mermaid** con sintaxis `flowchart` y no con la extensión `C4Context`/`C4Container`: el renderizador Mermaid de GitHub no soporta esa extensión, así que los diagramas no se verían en el repositorio. Usar `flowchart` con subgrafos es la práctica habitual para representar C4 en Markdown de GitHub y mantiene el diagrama versionado junto al código, sin depender de imágenes exportadas que quedan desactualizadas.

#### Nivel 1 — Contexto

Quién usa Platita y de qué sistemas externos depende.

```mermaid
flowchart TB
    USER(["👤 Usuario<br/><i>persona que registra y consulta sus finanzas</i>"])
    FAMILY(["👥 Grupo familiar<br/><i>otros miembros con presupuesto compartido</i>"])

    PLATITA["<b>Platita</b><br/>Asistente financiero personal y familiar<br/><i>[Sistema de software]</i>"]

    WACLOUD["<b>WhatsApp Business API</b><br/><i>[Sistema externo]</i><br/>Canal de mensajería"]
    LLM["<b>Proveedor de LLM</b><br/><i>[Sistema externo]</i><br/>Interpretación y generación"]
    FX["<b>Servicio de cotizaciones</b><br/><i>[Sistema externo]</i><br/>Tipo de cambio de referencia"]
    MAILBOX["<b>Casilla de email del usuario</b><br/><i>[Sistema externo — could-have]</i><br/>Avisos de banco y servicios"]

    USER -->|"registra gastos por chat<br/>y revisa el dashboard"| PLATITA
    FAMILY -->|"comparte presupuesto"| PLATITA
    PLATITA -->|"envía y recibe mensajes"| WACLOUD
    PLATITA -->|"interpreta mensajes<br/>y genera respuestas"| LLM
    PLATITA -->|"consulta cotización"| FX
    MAILBOX -.->|"movimientos detectados<br/>(no implementado en el MVP)"| PLATITA

    style PLATITA fill:#1f6feb,stroke:#0d419d,color:#fff
    style MAILBOX stroke-dasharray: 5 5
```

#### Nivel 2 — Contenedores

Las piezas desplegables del sistema y cómo se comunican entre sí.

```mermaid
flowchart TB
    USER(["👤 Usuario"])

    subgraph EXTERNOS["Sistemas externos"]
        direction LR
        WACLOUD["WhatsApp<br/>Business API"]
        LLM["Proveedor<br/>de LLM"]
    end

    subgraph PLATITA["Platita"]
        SPA["<b>Aplicación web</b><br/><i>[Contenedor: SPA]</i><br/>Dashboard de presupuestos,<br/>saldos y configuración"]
        API["<b>API Backend</b><br/><i>[Contenedor: Python + FastAPI]</i><br/>Casos de uso, reglas de negocio<br/>y orquestación de integraciones"]
        WORKER["<b>Procesos programados</b><br/><i>[Contenedor: Python]</i><br/>Gastos recurrentes, alertas de<br/>presupuesto y expiración de pendientes"]
        DB[("<b>Base de datos</b><br/><i>[Contenedor: PostgreSQL + pgvector]</i><br/>Datos del usuario y base de<br/>conocimiento vectorizada")]
    end

    USER -->|"mensajes"| WACLOUD
    USER -->|"HTTPS"| SPA
    WACLOUD <-->|"webhook y respuestas<br/>(firma verificada)"| API
    SPA -->|"JSON/HTTPS"| API
    API -->|"SQL"| DB
    API -->|"API"| LLM
    WORKER -->|"SQL"| DB
    WORKER -->|"alertas"| WACLOUD

    style API fill:#1f6feb,stroke:#0d419d,color:#fff
    style PLATITA fill:#f6f8fa,stroke:#8b949e
    style EXTERNOS fill:#f6f8fa,stroke:#8b949e
```

#### Nivel 3 — Componentes del backend

El interior del contenedor API, donde se ve el patrón arquitectónico elegido.

```mermaid
flowchart TB
    subgraph INBOUND["Adaptadores de entrada"]
        ROUTERS["Routers REST<br/><i>FastAPI</i>"]
        HOOK["Webhook handler<br/><i>WhatsApp</i>"]
        PARSE["Email parser<br/><i>could-have</i>"]
    end

    subgraph DOMAIN["Dominio — núcleo hexagonal"]
        UC["<b>Casos de uso</b><br/>RegisterTransaction · GetBudgetStatus<br/>CalculateAccountBalance · GenerateAlert"]
        ENT["<b>Entidades</b><br/>User · Account · Budget<br/>Transaction · Category"]
        PORTS["<b>Puertos</b><br/>interfaces que el dominio declara<br/>y no implementa"]
    end

    subgraph OUTBOUND["Adaptadores de salida"]
        REPO["Repositorios<br/><i>SQLAlchemy</i>"]
        VECADAPT["Vector store<br/><i>pgvector</i>"]
        WACLIENT["Cliente WhatsApp"]
        LLMCLIENT["Cliente LLM<br/><i>interpretación + RAG</i>"]
        FXCLIENT["Cliente de cotizaciones"]
    end

    DB[("PostgreSQL<br/>+ pgvector")]

    ROUTERS --> UC
    HOOK --> UC
    PARSE -.-> UC
    UC --> ENT
    UC --> PORTS
    PORTS --> REPO --> DB
    PORTS --> VECADAPT --> DB
    PORTS --> WACLIENT
    PORTS --> LLMCLIENT
    PORTS --> FXCLIENT

    style DOMAIN fill:#0d419d,stroke:#1f6feb,color:#fff
    style INBOUND fill:#f6f8fa,stroke:#8b949e
    style OUTBOUND fill:#f6f8fa,stroke:#8b949e
    style PARSE stroke-dasharray: 5 5
```

**Patrón elegido:** **arquitectura hexagonal (ports & adapters)**, con el dominio (entidades + casos de uso) aislado de los detalles de infraestructura detrás de puertos, y **backend y frontend desacoplados**, comunicados únicamente por API REST. Justificación:

- **Por qué este patrón y no otro:** con varias integraciones externas (WhatsApp, email, LLM, base vectorial, cotizaciones, REM) que van a cambiar con el tiempo —y donde ya se identificó al menos un reemplazo probable, el motor de vectores—, conviene que el dominio no conozca esos detalles. Cada integración es un adaptador detrás de un puerto; cambiarla es reemplazar el adaptador, no tocar la lógica de negocio. Separar front de back, además, deja la puerta abierta a una futura app móvil que consuma la misma API sin tocar lógica de negocio.
- **Beneficios:** los casos de uso (registrar un movimiento, evaluar un presupuesto, generar un consejo) se pueden testear sin levantar WhatsApp, un LLM real ni una base de datos — se testean contra los puertos, con dobles de prueba. Es además el mismo patrón que ya se usa en otros proyectos propios en Go, así que la disciplina de diseño ya es conocida, solo cambia el lenguaje.
- **Sacrificios:** más carpetas e indirección que un CRUD directo controlador-a-base de datos; para un proyecto de este tamaño el volumen de casos de uso reales (los tickets de la [sección 6](06-tickets.md) y los que sigan) justifica el costo. Se mitiga manteniendo los puertos chicos y con una sola responsabilidad cada uno, en vez de una interfaz gigante.

### **2.2. Descripción de componentes principales:**

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Backend API | Python + FastAPI | Adaptador de entrada: expone la API REST y traduce requests HTTP a casos de uso del dominio |
| Dominio | Python puro (sin dependencias de framework) | Entidades, casos de uso y puertos — la lógica de negocio en sí |
| Auth | JWT + código de un solo uso enviado por WhatsApp | Login del dashboard web sin contraseñas, reutilizando el teléfono ya verificado como identidad (ver [2.5](#25-seguridad)) |
| Integración WhatsApp | API oficial de WhatsApp Business (Meta Cloud API / Twilio) | Adaptador de entrada/salida: recibe y envía mensajes vía webhook |
| Parser de emails *(could-have)* | Python (reglas + LLM para casos ambiguos) | Adaptador de entrada: detecta movimientos financieros en la casilla de correo del usuario (con consentimiento explícito). Diseñado, no implementado en el MVP — ver [1.2](01-producto.md#12-características-y-funcionalidades-principales) |
| Motor RAG | LLM + embeddings sobre pgvector, detrás de un puerto propio | Responde consultas financieras y genera alertas proactivas a partir de la base de conocimiento curada por el producto |
| Base de datos relacional | PostgreSQL | Adaptador de salida: usuarios, cuentas, grupos familiares, presupuestos, movimientos, categorías |
| Base de datos vectorial | pgvector (extensión de PostgreSQL) | Adaptador de salida: embeddings del contenido de consejos financieros |
| Frontend | Aplicación web responsiva | Dashboard de visualización y configuración de usuario |

*(pgvector sobre PostgreSQL en vez de una base vectorial dedicada, como decisión de arranque — no definitiva. El acceso a la base vectorial se aísla detrás de un puerto propio, de forma que el motor real sea un detalle de infraestructura reemplazable: si en el futuro el volumen de consultas o el tamaño de la base de conocimiento lo justifica, se cambia el adaptador por Pinecone/Qdrant/Weaviate sin tocar el servicio de RAG. Mientras tanto, pgvector con índice HNSW sostiene sin problema volúmenes bastante mayores al de este proyecto — la ventaja de arrancar así no es solo "es más simple ahora", es no pagar el costo operativo de un segundo motor de base de datos hasta que haya una razón real para necesitarlo.)*

### **2.3. Descripción de alto nivel del proyecto y estructura de ficheros**

`Se completa en la Entrega 2 junto con el scaffold real. Estructura prevista (arquitectura hexagonal dentro del backend, nombres de carpetas y ficheros en inglés):`

```
/backend
  /app
    /domain
      /entities         # User, Account, Budget, Transaction, Category, RecurringExpense, AdviceDocument
      /use_cases         # RegisterTransaction, GetBudgetStatus, CalculateAccountBalance, GenerateProactiveAlert...
      /ports             # interfaces the domain depends on but does not implement
        - transaction_repository_port.py
        - account_repository_port.py
        - vector_store_port.py
        - whatsapp_gateway_port.py
        - exchange_rate_port.py
        - llm_port.py
    /adapters
      /inbound
        /api               # FastAPI routers — translate HTTP into use case calls
        /whatsapp_webhook   # translate WhatsApp payloads into use case calls
      /outbound
        /postgres           # SQLAlchemy repositories implementing the *_repository ports
        /pgvector            # VectorStorePort implementation
        /whatsapp_client      # sends outbound WhatsApp messages
        /email_reader          # IMAP/Gmail integration (could-have, not in the MVP)
        /exchange_rate_client   # currency quote provider
        /llm_client              # LLM client (interpretation + RAG)
  /tests
  /migrations          # Alembic
/frontend
  ...
docs/
  01-producto.md
  02-arquitectura.md
  03-modelo-de-datos.md
  04-api.md
  05-historias-de-usuario.md
  06-tickets.md
  07-pull-requests.md
  reglas-de-dominio.md      # dueño único de las reglas de negocio
  adr/                      # decisiones de arquitectura, formato Michael Nygard
README.md                   # portada, ficha del proyecto e índice
CLAUDE.md                   # contrato operativo para asistentes de IA
AGENTS.md
LICENSE
prompts.md
```

`/backend` y `/frontend` son la estructura prevista para la Entrega 2; el resto es la estructura real del repositorio hoy.

### **2.4. Infraestructura y despliegue**

`Propuesto, a confirmar en la Entrega 2 contra el despliegue real:` Render para backend + PostgreSQL, por simplicidad de despliegue para un proyecto individual y porque pgvector está soportado como extensión estándar de su Postgres gestionado, sin depender de elegir la plantilla correcta como sí pasa en otras plataformas. El frontend se sirve como sitio estático.

```mermaid
flowchart TB
    subgraph CLIENTES["Clientes"]
        direction LR
        PHONE(["📱 WhatsApp<br/>del usuario"])
        BROWSER(["💻 Navegador"])
    end

    DEV["🗂 Repositorio GitHub<br/><i>push a main → deploy automático</i>"]
    WACLOUD["<b>WhatsApp Business Cloud API</b><br/><i>Meta</i>"]

    subgraph RENDER["Render"]
        direction LR
        STATIC["<b>Static Site</b><br/>dashboard web"]
        WEBSVC["<b>Web Service</b><br/><i>contenedor Python</i><br/>API FastAPI"]
        CRON["<b>Cron Jobs</b><br/><i>contenedor Python</i><br/>recurrentes · alertas · expiración"]
        PG[("<b>PostgreSQL gestionado</b><br/><i>extensión pgvector</i><br/>backups automáticos")]
    end

    subgraph EXT["Servicios externos"]
        direction LR
        LLMAPI["API del<br/>proveedor de LLM"]
        FXAPI["API de<br/>cotizaciones"]
    end

    PHONE <--> WACLOUD
    BROWSER -->|"HTTPS"| STATIC
    DEV -.->|"deploy"| RENDER
    WACLOUD <-->|"webhook y mensajes salientes<br/>(HTTPS, firma verificada)"| WEBSVC
    STATIC -->|"JSON/HTTPS"| WEBSVC
    WEBSVC --> PG
    CRON --> PG
    CRON -->|"alertas"| WACLOUD
    WEBSVC --> LLMAPI
    WEBSVC --> FXAPI

    style WEBSVC fill:#1f6feb,stroke:#0d419d,color:#fff
    style RENDER fill:#f6f8fa,stroke:#8b949e
    style EXT fill:#f6f8fa,stroke:#8b949e
    style CLIENTES fill:#f6f8fa,stroke:#8b949e
```

**Proceso de despliegue previsto:** push a `main` dispara el build y deploy automático del servicio web y del sitio estático. Las migraciones de Alembic corren como paso previo al arranque del contenedor. Los secretos (credenciales de WhatsApp, LLM y base de datos) se configuran como variables de entorno en la plataforma, nunca versionados. Los procesos programados corren como cron jobs separados del servicio web, de modo que un fallo en el motor de recurrentes o de alertas no afecte la disponibilidad del webhook — es la mitigación concreta del riesgo de acoplamiento señalado en [2.1](#21-diagrama-de-arquitectura).

### **2.5. Seguridad**

- **Login sin contraseñas**: el usuario pide acceder al dashboard, recibe un código de un solo uso por WhatsApp (mismo canal ya verificado) y lo intercambia por un JWT de corta duración. Se evita así almacenar y gestionar contraseñas, y se reutiliza la identidad que el sistema ya valida por otro lado. Rate limiting sobre el endpoint de login para evitar fuerza bruta sobre el código.
- **Consentimiento explícito y revocable** para el acceso a la casilla de email (configuración de usuario, no un permiso obligatorio del sistema).
- **Verificación de firma del webhook de WhatsApp** en cada request entrante, para descartar mensajes falsificados.
- **Nunca loggear en crudo** número de teléfono, montos ni texto de usuario sin enmascarar.
- **Secretos fuera del código**: credenciales de WhatsApp, LLM y base de datos vía variables de entorno, nunca hardcodeadas ni versionadas.
- **HTTPS** en toda comunicación externa.
- Validación de entrada tanto en el webhook de WhatsApp como en los endpoints propios del frontend (cliente y servidor).

### **2.6. Tests**

`Se define con detalle en la Entrega final. Estrategia prevista: tests unitarios sobre los casos de uso del dominio (conversión de moneda, cálculo de saldo por cuenta, categorización, presupuesto ajustado por inflación) usando dobles de prueba en lugar de los adaptadores reales — la ventaja directa de tener puertos —, tests de integración sobre los adaptadores (Postgres, pgvector) y los endpoints principales, y al menos un test end-to-end del flujo principal (registrar un gasto por WhatsApp → verlo reflejado en el saldo de la cuenta y en el presupuesto del dashboard).`
