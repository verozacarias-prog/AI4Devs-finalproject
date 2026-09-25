# Platita

Asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos, ingresos y presupuestos conversando en lenguaje natural, y una capa de IA interpreta, categoriza y guarda cada movimiento en la cuenta correspondiente.
Un módulo complementario lee automáticamente los emails de notificación bancaria y de servicios para reducir la carga manual.
Toda la información —cuentas y su saldo, presupuestos multimoneda, comparación contra inflación y consejos financieros generados con RAG— se visualiza desde una aplicación web con dashboards.

**Estado:** Entrega 1 — documentación. Fecha límite de entrega: 24 de septiembre de 2026.

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
| [4. Especificación de la API](docs/04-api.md) | Los endpoints principales con sus contratos de request y response. |
| [5. Historias de usuario](docs/05-historias-de-usuario.md) | Las seis historias con sus criterios de aceptación, prioridad y estimación. |
| [6. Tickets de trabajo](docs/06-tickets.md) | Los tres tickets de backend, frontend y base de datos. |
| [7. Pull requests](docs/07-pull-requests.md) | Los pull requests de la entrega final. |
| [8. Convenciones de documentación](docs/08-convenciones-de-documentacion.md) | Idioma, diagramas, nombres de archivo y estructura de `docs/`. |
| [Recorrido completo](docs/recorrido-completo.md) | El recorrido del usuario de punta a punta: qué proceso actúa, si la llamada es HTTPS o SQL y qué tablas escribe cada paso. |
| [Reglas de dominio](docs/reglas-de-dominio.md) | Dueño único de las reglas de negocio, agrupadas por tema. |
| [Convenciones de desarrollo](docs/convenciones-de-desarrollo.md) | Cortes verticales y los cuatro estados de una pantalla. |
| [Términos y privacidad](docs/terminos-y-privacidad.md) | Qué tienen que cubrir los términos y la política de privacidad, antes de redactarlos. |
| [Validación por casos de uso](docs/use-case-walkthrough.md) | Registro, no especificación: 42 casos cotidianos de usuarios argentinos recorridos sobre el diseño, las decisiones pendientes que dejan y los escenarios para las pruebas. |
| [Hoja de ruta](docs/hoja-de-ruta.md) | Qué queda para la entrega 2 y para la app móvil, y por qué. |
| [Operación](docs/operacion.md) | Propuesta sin decidir: entornos, pipeline, despliegue, copias de respaldo y observabilidad. |
| [Flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md) | Contratos, skill, commands, verificadores y hooks. |
| [Documentación viva](docs/documentacion-viva.md) | Cómo se mantiene sincronizada la documentación: fuente única, portal, `llms.txt` y las tres barreras de validación. |

La documentación también se publica como sitio navegable en
**<https://verozacarias-prog.github.io/AI4Devs-finalproject/>**, generado desde `docs/` en cada
integración a `main`.

Las decisiones de arquitectura, una por archivo y en formato Michael Nygard, viven en [`docs/adr/`](docs/adr/).

Las plantillas que se copian al abrir una funcionalidad nueva están en [`docs/features/`](docs/features/).

El registro de uso de IA durante el proyecto está en [`prompts.md`](prompts.md), con la [conversación completa de la reestructuración](docs/conversacion-reestructuracion-docs.md) como anexo.

---

## Flujo de trabajo con IA

El proyecto se desarrolla con asistentes de IA y la configuración está versionada en el
repositorio: un skill, dos commands, dos verificadores y un hook de pre-commit.
Todo está descrito en el [flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md).

## Verificación

```sh
git config core.hooksPath .githooks       # una vez por clon
python3 scripts/verify_docs.py            # enlaces, anclas, duplicación, Mermaid
python3 scripts/verify_architecture.py    # regla hexagonal, acceso a la base y aislamiento del frontend
```

El hook de pre-commit los corre solo, y GitHub Actions los repite en cada pull request junto con
el formato del Markdown, los enlaces externos y la construcción del portal. El sistema completo
está en [documentación viva](docs/documentacion-viva.md).

## Cómo ejecutar localmente

Se completa en la entrega 2.
