# AGENTS.md — contrato para asistentes de IA

Contrato único para cualquier agente de IA que trabaje en este repositorio, sea cual sea la
herramienta. `CLAUDE.md` es un enlace simbólico a este archivo: hay una sola fuente y no puede
desincronizarse de sí misma.

No es la especificación. La especificación vive en [`docs/`](docs/) y manda sobre este archivo:
cuando difieran, ver la [sección 10](#10-especificación-contra-código).

> **Lo que un asistente rompe por defecto.** Si vas a leer una sola cosa antes de escribir
> código, que sean estas dos: la [regla de dependencia hexagonal](#3-regla-de-dependencia-hexagonal)
> y las [siete invariantes de dominio](#5-invariantes-que-un-asistente-rompe-por-defecto). Su
> violación no se nota leyendo el resultado.

## 1. Qué es Platita

Asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos,
ingresos y presupuestos conversando en lenguaje natural y los consulta en un dashboard web.
Una capa de IA interpreta, categoriza e imputa cada movimiento a una cuenta y a un presupuesto.

Qué **no** es: no es un agregador bancario y no scrapea bancos. No se conecta a home banking,
no pide credenciales bancarias y no lee saldos de ninguna entidad. Todo dato entra por el canal
conversacional, por una regla recurrente, o por los emails de aviso que el usuario habilita.

## 2. Idioma

Toda la documentación va en español. El código, las entidades, las columnas de base de datos,
los endpoints y los nombres de archivo de código van en inglés. Los mensajes al usuario final
(WhatsApp) van en español.

El resto de las convenciones de documentación —diagramas, nombres de archivo, estructura de
`docs/`— está en [`docs/08-convenciones-de-documentacion.md`](docs/08-convenciones-de-documentacion.md).

## 3. Regla de dependencia hexagonal

`domain/` no importa nada de `adapters/` ni de librerías de infraestructura.

Imports prohibidos dentro de `domain/`: `sqlalchemy`, `fastapi`, `httpx`, `psycopg`, el cliente
de LLM. Los casos de uso hablan solo con puertos.

Backend y frontend están desacoplados y se comunican únicamente por API REST. `frontend/` no
importa nada de `backend/` ni accede a la base de datos. Fundamento en el
[ADR 0001](docs/adr/0001-arquitectura-hexagonal.md).

Las dos reglas se verifican con `python3 scripts/verify_architecture.py`, que corre en el hook
de pre-commit. No son una recomendación: rompen el commit.

## 4. Mapa de carpetas

- `backend/app/domain/entities/` — User, Account, Budget, Transaction, Category, RecurringRule, CardStatement, Transfer, AdviceDocument.
- `backend/app/domain/use_cases/` — RegisterTransaction, GetBudgetStatus, CalculateAccountBalance, GenerateProactiveAlert.
- `backend/app/domain/ports/` — interfaces que el dominio declara y no implementa.
- `backend/app/adapters/inbound/api/` — routers de FastAPI: traducen HTTP a llamadas a casos de uso.
- `backend/app/adapters/inbound/whatsapp_webhook/` — traduce payloads de WhatsApp a llamadas a casos de uso.
- `backend/app/adapters/outbound/postgres/` — repositorios SQLAlchemy que implementan los puertos `*_repository`.
- `backend/app/adapters/outbound/pgvector/` — implementación de `VectorStorePort`.
- `backend/app/adapters/outbound/whatsapp_client/` — envío de mensajes salientes de WhatsApp.
- `backend/app/adapters/outbound/email_reader/` — integración IMAP/Gmail (could-have, fuera del MVP).
- `backend/app/adapters/outbound/exchange_rate_client/` — proveedor de cotizaciones.
- `backend/app/adapters/outbound/llm_client/` — cliente de LLM (interpretación y RAG).
- `backend/tests/` — tests unitarios, de integración y end-to-end.
- `backend/migrations/` — migraciones de Alembic.
- `frontend/` — dashboard web.
- `site/` — portal de documentación (Astro Starlight). Se genera desde `docs/`; no es fuente.
- `docs/` — la especificación del proyecto.

## 5. Invariantes que un asistente rompe por defecto

- Nunca usar una cuenta por defecto. Si el mensaje no la menciona, preguntar.
- Nunca asignar `budget_period_id` sin confirmación explícita del usuario.
- Los defaults derivables permitidos son solo fecha, moneda y categoría, y los tres van siempre listados en el mensaje de confirmación.
- Montos en `Decimal`, nunca `float`.
- La moneda viaja siempre junto al monto, nunca implícita.
- El saldo de una cuenta se calcula, no se almacena como campo mutable.
- Una categoría nueva no se crea sin confirmación.

Para cualquier ticket de dominio, leer [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md)
completo antes de escribir código.

## 6. Convenciones de código

- Tipado obligatorio en todas las firmas.
- Pydantic solo en el borde, es decir en los adaptadores. El dominio no conoce Pydantic.
- Sin lógica de negocio en adaptadores: traducen y delegan.
- Sin `Any`.

## 7. Seguridad

- Nunca loggear teléfono, monto ni texto del usuario sin enmascarar.
- Secretos solo por variables de entorno, nunca hardcodeados ni versionados.
- Verificar la firma del webhook antes de procesar.
- Todo acceso a datos se limita al usuario autenticado, que sale de la sesión y nunca del request. Un
  recurso de otro usuario responde `404`, y cada endpoint tiene un test que lo prueba.

## 8. Base de datos

- Todo cambio de esquema va en una migración Alembic nueva.
- Jamás editar una migración ya aplicada.
- Los `CHECK` van en la base, no solo en la aplicación.

## 9. Librerías

Antes de proponer una librería nueva, justificar por qué no alcanza lo instalado.

## 10. Especificación contra código

**Qué es la especificación.** Los archivos versionados de `docs/`, y nada más:

- [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md) — las reglas de negocio. Autoridad sobre qué debe hacer el sistema.
- `docs/01-producto.md` a `docs/07-pull-requests.md` — alcance, arquitectura, modelo de datos, contrato de la API, historias de usuario y tickets.
- [`docs/adr/`](docs/adr/) — las decisiones de arquitectura. Autoridad sobre por qué el sistema es como es. Un ADR con Estado `Aceptada` sigue vigente; uno `Reemplazada por NNNN` no. Un ADR sin la marca `En producción desde` todavía se corrige en su archivo; con la marca, es inmutable.

**Qué no es la especificación**, aunque lo parezca: los comentarios y docstrings del código, los
mensajes de commit, las descripciones de los pull requests, los tests, este archivo, `README.md`,
`prompts.md`, y cualquier cosa dicha en una conversación con un asistente. Este archivo es el
contrato operativo, no la especificación: cuando resume una regla, la versión que manda es la de
`docs/`.

Si dos archivos de `docs/` se contradicen entre sí, eso también es una divergencia y se reporta
igual, sin elegir uno por tu cuenta.

Cuando la especificación y el código difieran, detenete y reportá la divergencia. No asumas que
la documentación describe la realidad, ni corrijas la documentación para que coincida con el
código. La divergencia se resuelve decidiendo cuál de los dos lados está mal, y esa decisión es
humana. Por defecto la especificación manda y lo que se corrige es el código. Para conocer el
estado real, analizá el código; para decidir qué es correcto, la autoridad es la especificación.

## 11. Comandos de verificación

- Documentación: `python3 scripts/verify_docs.py`.
- Arquitectura: `python3 scripts/verify_architecture.py`. Valida la regla de dependencia del
  dominio, que ninguna anotación del dominio cuyo nombre sea monetario (`amount`, `balance`,
  `limit`, `income`, `total`, `price`, `monto`, `saldo`) use `float`, y el aislamiento del
  frontend. No detecta un monto con otro nombre. Tolerante mientras `backend/` y `frontend/` no
  existan, pero falla si `backend/` existe y el dominio no está en `backend/app/domain/`.
- Los dos tienen que pasar sin errores antes de commitear; el hook de pre-commit los corre solo,
  y el flujo `.github/workflows/docs-quality.yml` los repite en cada pull request junto con
  `markdownlint-cli2` y `lychee`.
- Tests y linters: se completa en la entrega 2.

## 12. Qué leer antes de qué

- Ticket de dominio → [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md) y [`docs/03-modelo-de-datos.md`](docs/03-modelo-de-datos.md).
- Ticket de API → [`docs/04-api.md`](docs/04-api.md).
- Pantalla nueva → [`docs/convenciones-de-desarrollo.md`](docs/convenciones-de-desarrollo.md).
- Decisión de arquitectura → [`docs/adr/`](docs/adr/).

## 13. Método de trabajo

Toda funcionalidad se parte en tres cortes verticales —camino feliz, errores y estado vacío,
observabilidad—. Un corte vertical atraviesa todas las capas, de la base de datos a la pantalla
o al mensaje de WhatsApp, queda funcionando de punta a punta y termina en su propio commit.
Lo contrario, cortar por capa, deja la interfaz para el final y es como se llega a una entrega
sin nada que mostrar.
Toda pantalla implementa y testea los cuatro estados: cargando, con contenido, vacío y error.

Vacío y error no son el mismo estado. Detalle y gates en [`docs/convenciones-de-desarrollo.md`](docs/convenciones-de-desarrollo.md).
