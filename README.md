# Platita

Asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos, ingresos y presupuestos conversando en lenguaje natural, y una capa de IA interpreta, categoriza y guarda cada movimiento en la cuenta correspondiente.
Un módulo complementario lee automáticamente los emails de notificación bancaria y de servicios para reducir la carga manual.
Toda la información —cuentas y su saldo, presupuestos multimoneda, comparación contra inflación y consejos financieros generados con RAG— se visualiza desde una aplicación web con dashboards.

**Estado:** Entrega 1 — documentación. Entregada el 24 de septiembre de 2026.

---

## 0. Ficha del proyecto

### 0.1. Tu nombre completo:

Verónica Noemi Zacarías

### 0.2. Nombre del proyecto:

**Platita** — asistente financiero personal y familiar por WhatsApp

> *(Nombre de producto en español porque el público objetivo es hispanohablante; el código, el modelo de datos y la API van en inglés — ver [nota de idioma](docs/08-convenciones-de-documentacion.md#81-idioma).)*

### 0.3. Descripción breve del proyecto:

Platita es un asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos, ingresos y presupuestos conversando en lenguaje natural, y una capa de IA interpreta, categoriza y guarda cada movimiento en la cuenta correspondiente. Un módulo complementario lee automáticamente los emails de notificación bancaria y de servicios para reducir la carga manual. Toda la información —incluyendo cuentas y su saldo, presupuestos multimoneda, comparación contra inflación y consejos financieros generados con RAG— se visualiza en detalle desde una aplicación web con dashboards.

### 0.4. URL del proyecto:

https://github.com/verozacarias-prog/AI4Devs-finalproject

### 0.5. URL o archivo comprimido del repositorio

https://github.com/verozacarias-prog/AI4Devs-finalproject

---

## Documentación

| Documento | Contiene |
|---|---|
| [1. Descripción general del producto](docs/01-producto.md) | Objetivo, catálogo must/should/could, flujo conversacional e instrucciones de instalación. |
| [2. Arquitectura del sistema](docs/02-arquitectura.md) | Diagramas C4, componentes, estructura de ficheros, infraestructura, seguridad y tests. |
| [3. Modelo de datos](docs/03-modelo-de-datos.md) | Diagrama entidad-relación y descripción de cada entidad. |
| [4. Especificación de la API](docs/04-api.md) | Los tres endpoints principales con sus contratos de request y response. |
| [5. Historias de usuario](docs/05-historias-de-usuario.md) | Las cinco historias con sus criterios de aceptación, prioridad y estimación. |
| [6. Tickets de trabajo](docs/06-tickets.md) | Los tres tickets de backend, frontend y base de datos. |
| [7. Pull requests](docs/07-pull-requests.md) | Los pull requests de la entrega final. |
| [8. Convenciones de documentación](docs/08-convenciones-de-documentacion.md) | Idioma, diagramas, nombres de archivo y estructura de `docs/`. |
| [Reglas de dominio](docs/reglas-de-dominio.md) | Dueño único de las reglas de negocio, agrupadas por tema. |
| [Convenciones de desarrollo](docs/convenciones-de-desarrollo.md) | Cortes verticales y los cuatro estados de una pantalla. |

Las decisiones de arquitectura, una por archivo y en formato Michael Nygard, viven en [`docs/adr/`](docs/adr/).

Las plantillas que se copian al abrir una funcionalidad nueva están en [`docs/features/`](docs/features/).

El registro de uso de IA durante el proyecto está en [`prompts.md`](prompts.md), con la [conversación completa de la reestructuración](docs/conversacion-reestructuracion-docs.md) como anexo.

---

## Flujo de trabajo con IA

El proyecto se desarrolla con asistentes de IA y la configuración está versionada en el
repositorio, no en la máquina de quien lo escribe.

### Contratos

| Archivo | Qué contiene | Quién lo lee |
|---|---|---|
| [`AGENTS.md`](AGENTS.md) | La regla de dependencia hexagonal y las siete invariantes de dominio | Cualquier asistente, sea cual sea la herramienta |
| [`CLAUDE.md`](CLAUDE.md) | El contrato operativo completo: carpetas, convenciones, seguridad, base de datos y qué leer antes de qué | Claude Code |
| [`docs/`](docs/) | La especificación del proyecto. Manda sobre los dos anteriores | Personas y asistentes |

### Commands

Tres comandos versionados en `.claude/commands/`. Imponen un orden de lectura y una forma de
responder; se invocan escribiendo `/nombre`.

| Command | Cuándo | Qué hace |
|---|---|---|
| `/domain-rules` | Al abrir un ticket de dominio | Lee las reglas completas y devuelve qué grupos aplican, qué se resuelve solo, qué exige confirmación del usuario y qué invariante está en riesgo |
| `/ui-states` | Al cerrar el corte vertical 2 | Verifica que la pantalla implemente y testee los cuatro estados, con foco en que *vacío* no esté resuelto como *error* |
| `/spec-drift` | Antes del último commit de un corte, y antes de cada entrega | Compara la especificación contra el código y reporta las diferencias **sin resolverlas** |

### Verificación automática

Dos scripts que corren solos en el hook de pre-commit. Lo que se responde con sí o no va acá; lo
que requiere criterio es un command.

| Script | Qué valida |
|---|---|
| [`scripts/verify_docs.py`](scripts/verify_docs.py) | Enlaces y anclas, documentos huérfanos, texto duplicado entre archivos, bloques Mermaid, nombres de archivo, plantilla de los ADR y frontmatter de los commands |
| [`scripts/verify_architecture.py`](scripts/verify_architecture.py) | Que `domain/` no importe infraestructura ni adaptadores, y que `frontend/` no alcance la base de datos. Tolerante mientras no exista el código |

### Método de trabajo

Toda funcionalidad se parte en tres [cortes verticales](docs/convenciones-de-desarrollo.md#1-cortes-verticales)
que atraviesan backend y frontend, y toda pantalla implementa
[cuatro estados](docs/convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).
Cada corte se cierra contra el [Definition of Done](docs/07-pull-requests.md#definition-of-done).

### Skills, subagentes y hooks

No se usan skills ni subagentes: para un proyecto individual, los tres commands cubren lo que
haría un subagente sin el costo de coordinarlos. El único hook es el de pre-commit, en
[`.githooks/`](.githooks/). Se activa con `git config core.hooksPath .githooks`, una vez por clon.

## Verificación

```
git config core.hooksPath .githooks       # una vez por clon
python3 scripts/verify_docs.py            # enlaces, anclas, duplicación, Mermaid
python3 scripts/verify_architecture.py    # regla hexagonal y aislamiento del frontend
```

El hook de pre-commit los corre solo. Detalle en las [convenciones de documentación](docs/08-convenciones-de-documentacion.md#87-verificación-automática).

## Cómo ejecutar localmente

Se completa en la entrega 2.
