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
| [Convenciones de desarrollo](docs/convenciones-de-desarrollo.md) | Vertical slices y los cuatro estados de una pantalla. |

Las decisiones de arquitectura, una por archivo y en formato Michael Nygard, viven en [`docs/adr/`](docs/adr/).

El registro de uso de IA durante el proyecto está en [`prompts.md`](prompts.md), con la [conversación completa de la reestructuración](docs/conversacion-reestructuracion-docs.md) como anexo.

---

## Verificación

```
git config core.hooksPath .githooks       # una vez por clon
python3 scripts/verify_docs.py            # enlaces, anclas, duplicación, Mermaid
python3 scripts/verify_architecture.py    # regla hexagonal y aislamiento del frontend
```

El hook de pre-commit los corre solo. Detalle en las [convenciones de documentación](docs/08-convenciones-de-documentacion.md#87-verificación-automática).

## Cómo ejecutar localmente

Se completa en la entrega 2.
