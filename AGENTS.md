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
de LLM y cualquier otra librería de IA. Los casos de uso hablan solo con puertos.

No se usa ningún framework de orquestación de IA: los adaptadores usan el SDK directo del
proveedor. La única excepción es `langchain-text-splitters`, importado solo en
`adapters/outbound/text_splitter/` ([ADR 0020](docs/adr/0020-sin-framework-de-orquestacion-de-ia.md)).

Backend y frontend están desacoplados y se comunican únicamente por API REST. `frontend/` no
importa nada de `backend/` ni accede a la base de datos.

Solo el backend toca la base. Desde afuera se entra únicamente por la API HTTP. Adentro, la API,
el worker de mensajes, los procesos programados y los comandos de operación son adaptadores de
entrada que llaman a casos de uso, y ninguno llama a otro por HTTP. Ningún archivo fuera de los repositorios, las
migraciones y los tests puede importar una librería de base de datos. El LLM nunca accede a la
base ni genera SQL. La regla completa, con sus
excepciones, está en el [ADR 0001](docs/adr/0001-arquitectura-hexagonal.md).

`app/shared/` tiene las utilidades técnicas que usan el dominio y los adaptadores, como el
reloj. Un módulo de `shared/` importa solo la librería estándar, no importa nada del resto de
`app/`, y hay uno por tema: no existe un `helpers.py` general. La lógica de negocio va en
`domain/` aunque sea una función suelta. Un caso de uso recibe el reloj al construirse y nunca
lee la hora por su cuenta.

Los errores que una regla de negocio prevé se declaran en `domain/errors.py`, con un código
estable y una categoría, y no saben nada de HTTP ni de la base. Un adaptador de salida traduce
el error de su librería al del dominio. Cada adaptador de entrada tiene un solo lugar que
convierte un error en su salida y lo registra: ningún router ni comando atrapa errores por su
cuenta.

Estas reglas se verifican con `python3 scripts/verify_architecture.py`, que corre en el hook
de pre-commit. No son una recomendación: rompen el commit.

## 4. Mapa de carpetas

- `backend/app/domain/entities/` — User, Session, Account, BudgetPeriod, FamilyGroup, FinancialProfile, Budget, Transaction, Category, RecurringRule, CardStatement, Transfer, AdviceDocument, AdviceChunk.
- `backend/app/domain/use_cases/` — CreateTestUser, SeedTestData, ListTestUsers, OpenDevSession, AuthenticateSession, CloseSession, RegisterTransaction, GetBudgetStatus, ListAccounts, GenerateProactiveAlert.
- `backend/app/domain/ports/` — interfaces que el dominio declara y no implementa.
- `backend/app/domain/errors.py` — los errores que una regla de negocio prevé, cada uno con su código y su categoría.
- `backend/app/domain/local_date.py` — qué día es para un usuario, en su zona horaria.
- `backend/app/domain/account_balance.py` — el saldo de una cuenta, calculado con lo que ya ocurrió en ella.
- `backend/app/shared/` — utilidades técnicas que usan todas las capas, solo con la librería estándar. `clock.py` tiene el protocolo del reloj y su implementación con el reloj de la máquina.
- `backend/app/adapters/inbound/api/` — routers de FastAPI: traducen HTTP a llamadas a casos de uso. Incluye el chat web de desarrollo, que guarda el mensaje y no lo procesa.
- `backend/app/adapters/inbound/whatsapp_webhook/` — traduce payloads de WhatsApp a llamadas a casos de uso.
- `backend/app/adapters/inbound/message_worker/` — punto de entrada del worker: toma los mensajes guardados y los pasa a casos de uso.
- `backend/app/adapters/inbound/scheduler/` — punto de entrada de los procesos programados: recurrentes, cierres de resumen, alertas, vencimientos, cotizaciones y borrado de cuentas, siempre por casos de uso.
- `backend/app/adapters/inbound/cli/` — comandos de operación: datos de prueba del entorno `local`, carga de la base de conocimiento, habilitación de números, y enlaces personales del entorno `demo`, siempre por casos de uso.
- `backend/app/adapters/outbound/postgres/` — repositorios SQLAlchemy que implementan los puertos `*_repository`, la unidad de trabajo y la creación de la conexión.
- `backend/app/adapters/outbound/pgvector/` — implementación de `VectorStorePort`.
- `backend/app/adapters/outbound/whatsapp_client/` — envío de mensajes salientes de WhatsApp.
- `backend/app/adapters/outbound/email_reader/` — integración IMAP/Gmail (could-have, fuera del MVP).
- `backend/app/adapters/outbound/exchange_rate_client/` — proveedor de cotizaciones e indicadores de mercado (tasa de plazo fijo, inflación).
- `backend/app/adapters/outbound/llm_client/` — cliente de LLM: clasificación, interpretación y respuestas, con el SDK del proveedor.
- `backend/app/adapters/outbound/embedding_client/` — cliente del proveedor de embeddings.
- `backend/app/adapters/outbound/text_splitter/` — particionado de documentos; el único lugar que importa `langchain-text-splitters`.
- `backend/app/adapters/outbound/observability/` — envoltorios de los puertos de LLM y de embeddings, que registran cada llamada sin su contenido, y el formato JSON de los registros con su filtro.
- `backend/tests/` — tests unitarios, de integración y end-to-end.
- `backend/migrations/` — migraciones de Alembic.
- `frontend/` — dashboard web, en React con TypeScript y Vite ([ADR 0026](docs/adr/0026-react-typescript-y-vite-para-el-dashboard.md)), con Tailwind CSS y shadcn/ui ([ADR 0027](docs/adr/0027-tailwind-y-shadcn-ui-para-el-dashboard.md)). `src/api/` tiene el contrato exportado y los tipos generados, `src/pages/` una pantalla por archivo con su test al lado, `src/components/ui/` los componentes de shadcn/ui, y `src/design-tokens.css` los tokens de diseño.
- `site/` — portal de documentación (Astro Starlight). Se genera desde `docs/`; no es fuente.
- `docs/` — la especificación del proyecto.

## 5. Invariantes que un asistente rompe por defecto

- Nunca usar una cuenta por defecto. Si el mensaje no la menciona, preguntar.
- Nunca asignar `budget_period_id` sin confirmación explícita del usuario. La única excepción es
  que haya un solo período posible para esa fecha: ahí se imputa a ese sin preguntar.
- Los defaults derivables permitidos son solo fecha, moneda y categoría, y los tres van siempre listados en el mensaje de confirmación, junto con el presupuesto cuando se imputó por ser el único.
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
- Sin textos ni valores sueltos en el código: van como constantes, en un lugar por tipo. En el
  backend, `app/constants.py` (entornos, variables de entorno, valores por defecto),
  `app/test_data.py` (la plantilla de un usuario de prueba y los usuarios de `local`),
  `app/messages.py` (todo mensaje para una persona), `adapters/inbound/api/routes.py` (las
  rutas de la API y los valores de sus respuestas), `adapters/inbound/api/reference.py` (los
  textos de la referencia de la API), `adapters/inbound/api/security_headers.py`
  (los encabezados de seguridad), `adapters/outbound/observability/events.py`
  (eventos, campos, nombres y reglas de los registros) y `adapters/outbound/postgres/queries.py`
  (el SQL escrito a mano). Quedan en su lugar solo las palabras que define una librería, como
  el nombre de un parámetro suyo, el SQL de cada migración, que es su contenido, y lo que
  vive en un archivo estático del dashboard: el título de `index.html` y el ícono. En el dashboard, `src/messages.ts` (todo texto que se muestra),
  `src/api/routes.ts` (las rutas de la API) y `src/constants.ts` (el resto). Los tests sí escriben el valor literal de lo que comprueban, que es lo que se ve desde
  afuera; lo que varios tests repiten va como constante, y vive en la aplicación en cuanto esta
  lo necesita. El detalle está en las
  [convenciones de desarrollo](docs/convenciones-de-desarrollo.md#1-cortes-verticales).

## 7. Seguridad

- Nunca loggear teléfono, monto ni texto del usuario sin enmascarar. De un error se registran
  su clase, su camino en el código, los identificadores de lo que tocaba y sus valores de
  catálogo, nunca su mensaje. La única excepción es el entorno `local`, con usuarios
  inventados, donde un error se escribe además completo.
- Secretos solo por variables de entorno, nunca hardcodeados ni versionados.
- Verificar la firma del webhook antes de procesar.
- Todo acceso a datos se limita al usuario autenticado, que sale de la sesión y nunca del request. Un
  recurso de otro usuario responde `404`, y cada endpoint tiene un test que lo prueba.
- El chat web y la entrada de desarrollo, que abre una sesión sin código, existen solo en los
  entornos `local` y `demo`. Con alguno encendido en `production`, ningún proceso arranca. En
  `demo` no hay lista de usuarios: se entra solo con el enlace personal de cada usuario de prueba
  ([ADR 0016](docs/adr/0016-sesion-de-servidor-en-el-mismo-origen.md)).
- Todo dato que entra a un prompt va delimitado como información, y la salida del modelo se valida
  en código antes de enviarla ([ADR 0013](docs/adr/0013-datos-minimos-al-proveedor-de-llm.md)).
- El prompt de sistema no lleva secretos ni datos de ningún usuario: se escribe como si fuera
  público. El chat web muestra la respuesta del modelo como texto, nunca como HTML.
- Toda llamada al LLM o al proveedor de embeddings pasa por el envoltorio que la registra, sin
  texto, montos ni nombres. No se envía nada a una plataforma externa de observabilidad de LLM
  ([ADR 0023](docs/adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md)).
- El cruce contra el OWASP Top 10 para aplicaciones LLM está en
  [`docs/seguridad-llm.md`](docs/seguridad-llm.md). Si un cambio toca el uso del modelo, esa
  tabla se actualiza en el mismo cambio.

## 8. Base de datos

- Todo cambio de esquema va en una migración Alembic nueva.
- Jamás editar una migración ya aplicada.
- Los `CHECK` van en la base, no solo en la aplicación.

## 9. Librerías

Antes de proponer una librería nueva, justificar por qué no alcanza lo instalado.

## 10. Especificación contra código

**Qué es la especificación.** Los archivos versionados de `docs/`, salvo los registros que se
nombran más abajo, y nada más. Entre ellos:

- [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md) — las reglas de negocio. Autoridad sobre qué debe hacer el sistema.
- `docs/01-producto.md` a `docs/07-pull-requests.md` — alcance, arquitectura, modelo de datos, contrato de la API, historias de usuario y tickets.
- [`docs/adr/`](docs/adr/) — las decisiones de arquitectura. Autoridad sobre por qué el sistema es como es. Un ADR con Estado `Aceptada` sigue vigente; uno `Reemplazada por NNNN` no. Un ADR sin la marca `En producción desde` todavía se corrige en su archivo; con la marca, es inmutable.
- El resto de `docs/` — las convenciones, la hoja de ruta, operación, la seguridad de la capa de IA y la carpeta `docs/features/` de cada funcionalidad. De [`docs/operacion.md`](docs/operacion.md), lo que sigue como propuesta no se implementa hasta que exista su ADR.

**Qué no es la especificación**, aunque lo parezca: los comentarios y docstrings del código, los
mensajes de commit, las descripciones de los pull requests, los tests, este archivo, `README.md`,
`prompts.md`, los registros que viven en `docs/` (`docs/conversacion-*.md` y
`docs/use-case-walkthrough.md`), y cualquier cosa dicha en una conversación con un asistente.
Una recomendación de `use-case-walkthrough.md` no se implementa hasta que su regla esté escrita en
la especificación. Este archivo es el
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
  `limit`, `income`, `total`, `price`, `monto`, `saldo`) use `float`, que las librerías de acceso
  a la base no se importen fuera de los directorios permitidos, que ningún framework de IA se
  importe fuera del adaptador de particionado, y el aislamiento del frontend. No detecta un
  monto con otro nombre, una llamada HTTP de un proceso del backend a la API, ni el SDK de un
  proveedor de IA que no esté en su lista. Valida que un módulo de `app/shared/` importe solo
  la librería estándar y no se llame como un módulo general, y que ningún adaptador de entrada
  importe a otro: la API, el worker, los comandos y los procesos programados llegan cada uno a
  los casos de uso por su cuenta. No valida que los errores se
  traduzcan en un solo lugar, ni que un caso de uso no lea la hora por su cuenta.
  Tolerante mientras `backend/` y `frontend/` no
  existan, pero falla si `backend/` existe y el dominio no está en `backend/app/domain/`.
- Contrato de la API: `python3 scripts/verify_api_contract.py`. Lee el contrato versionado,
  `frontend/src/api/openapi.json`. Valida que cada operación diga para qué sirve, con un
  título escrito a mano, que cada respuesta diga cuándo ocurre, que cada parámetro y cada
  campo tengan su descripción, que todo error tenga el cuerpo de un error, que lo que pide
  sesión documente su `401` y lo que modifica algo su `403`, y que cada operación y cada
  estado que responde estén en `docs/04-api.md`. No valida que `04-api.md` describa cada
  campo, que un endpoint especificado esté implementado, ni que lo especificado para una
  operación esté en el contrato: compara del contrato hacia la especificación.
- Los tres tienen que pasar sin errores antes de commitear; el hook de pre-commit los corre solo,
  y el flujo `.github/workflows/docs-quality.yml` los repite en cada pull request junto con
  `markdownlint-cli2` y `lychee`.
- Backend, desde `backend/` y con su entorno activado: `pytest` corre los tests, `ruff check .`
  y `ruff format --check .` el lint y el formato, `mypy` los tipos en modo estricto, y
  `pip-audit -r requirements.txt` las vulnerabilidades. Los tests de integración necesitan la
  base de `docker compose up db`. Los seis controles del pipeline están en el
  [ADR 0021](docs/adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md), y los
  corre el flujo `.github/workflows/app-quality.yml`. El otro flujo busca secretos con
  `gitleaks`; una excepción se anota en `.gitleaksignore`, nunca se desactiva el control.
  El sexto, el análisis de seguridad con CodeQL, corre en `.github/workflows/codeql.yml` y no
  tiene comando local: una alerta que no es un problema se descarta en GitHub con su motivo.
- Dashboard, desde `frontend/`: `npm test` corre los tests de las pantallas, `npm run lint` el
  linter, `npm run typecheck` los tipos, `npm run build` la compilación y
  `npm audit --audit-level=high` las vulnerabilidades.
- Si cambia una ruta o una respuesta de la API, se regenera el contrato y sus tipos: desde
  `backend/`, `python -m app.adapters.inbound.api.export_openapi > ../frontend/src/api/openapi.json`,
  y desde `frontend/`, `npm run api:generate`. El pipeline y un test del backend fallan si
  quedaron desactualizados. Una ruta nueva lleva sus textos en `reference.py`: sin ellos el
  verificador del contrato falla.
- Antes de pedir el merge de un pull request se corre a mano el agente `pr-reviewer`, y su
  informe se pega en el pull request
  ([ADR 0022](docs/adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md)).
- Antes de cada entrega se corre `/security-audit`.

## 12. Qué leer antes de qué

- Ticket de dominio → [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md) y [`docs/03-modelo-de-datos.md`](docs/03-modelo-de-datos.md).
- Ticket de API → [`docs/04-api.md`](docs/04-api.md).
- Pantalla nueva → [`docs/convenciones-de-desarrollo.md`](docs/convenciones-de-desarrollo.md).
- Decisión de arquitectura → [`docs/adr/`](docs/adr/).
- Qué entra en la entrega 2 y qué no → [`docs/hoja-de-ruta.md`](docs/hoja-de-ruta.md#alcance-de-la-entrega-2).
- Docker, pipeline, registros, métricas del modelo o rutas de salud → los ADR [0021](docs/adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md) y [0023](docs/adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md), y [`docs/operacion.md`](docs/operacion.md), que separa lo decidido de lo propuesto.
- Clasificación, memoria, base de conocimiento o prompts → los ADR [0013](docs/adr/0013-datos-minimos-al-proveedor-de-llm.md), [0018](docs/adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md), [0019](docs/adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md), [0020](docs/adr/0020-sin-framework-de-orquestacion-de-ia.md) y [0025](docs/adr/0025-gpt-5-4-mini-como-modelo-de-lenguaje.md).

## 13. Método de trabajo

Toda funcionalidad se parte en tres cortes verticales —camino feliz, errores y estado vacío,
observabilidad—. Un corte vertical atraviesa todas las capas, de la base de datos a la pantalla
o al mensaje de WhatsApp, queda funcionando de punta a punta y, si toca el backend, termina en
dos commits, el de sus tests y el de su implementación.
Lo contrario, cortar por capa, deja la interfaz para el final y es como se llega a una entrega
sin nada que mostrar.
Toda pantalla implementa y testea los cuatro estados: cargando, con contenido, vacío y error. La única excepción está en las [convenciones de desarrollo](docs/convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla): una pantalla que no muestra datos del usuario no tiene estado vacío.

En el backend el test va antes que el código
([ADR 0024](docs/adr/0024-tests-primero-en-el-backend.md)):

- No escribas ningún test hasta que una persona haya aprobado los casos del corte en el
  `spec.md` de la funcionalidad. Escribilos tal como están ahí, sin sumar ni cambiar casos. La línea de
  aprobación la completa la persona: no la escribas vos.
- En una tarea que no es de una historia no hay `spec.md`: proponé los casos, esperá la
  aprobación, y dejalos listos para la descripción del pull request.
- Corré los tests y confirmá que fallan antes de implementar. El commit de los tests va antes
  que el de la implementación.
- Implementá lo mínimo para que pasen. Refactorizá solo con todo en verde.
- Nunca modifiques, deshabilites ni borres un test para que la suite pase. Si un test está mal,
  frená y mostralo: la decisión es de una persona.
- Si alguien pide implementar sin que existan los casos aprobados o los tests, avisalo antes de
  escribir código.

Nadie escribe directo en la rama de la entrega, `feature/entrega-N-VNZ`. Las ramas de trabajo
se llaman `hu<N>-c<corte>-<tema>` para un corte de una historia y `tarea-<tema>` para el resto,
y entran por pull request. Los pasos están en el [README](README.md#cómo-colaborar).

Un asistente hace commit solo cuando una persona se lo pide, y nunca hace merge: la aprobación
final de un pull request es de una persona.

Vacío y error no son el mismo estado. Detalle y gates en [`docs/convenciones-de-desarrollo.md`](docs/convenciones-de-desarrollo.md).
