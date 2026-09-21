# Hoja de ruta

Qué queda por hacer, cuándo se desbloquea y por qué importa. No es una lista de deseos: cada
punto salió de una decisión ya tomada y documentada, y está acá porque **depende de que exista
código** y no se puede adelantar sin inventar.

Los pendientes del registro de uso de IA —qué prompts falta documentar, el MCP de GitHub— viven
en [`prompts.md`](../prompts.md), no acá.

## Entrega 2

| Qué | Se desbloquea cuando | Por qué importa |
|---|---|---|
| Generar el cliente del dashboard desde el OpenAPI de FastAPI | Corra la API | Es lo que impide que el frontend se desincronice del backend sin que falle la compilación, y lo que deja el cliente resuelto para una futura app móvil. Decidido en el [ADR 0005](adr/0005-python-fastapi-en-vez-de-go.md) |
| `scripts/verify_api_contract.py` | Exista el OpenAPI | Compara el contrato generado contra [`04-api.md`](04-api.md) y entra al hook de pre-commit. Automatiza la parte de `/spec-drift` que sí es binaria; lo que requiere criterio sigue siendo el command |
| Tokens del Design System, documentados aparte de los componentes | Haya diseño del dashboard | Para que la app móvil los reutilice en vez de reconstruirlos leyendo código |
| Rellenar un [`ui_contract.md`](features/TEMPLATE/ui_contract.md) por pantalla | Haya pantallas | La plantilla ya está; el contenido sale al escribir cada especificación |
| Completar `CLAUDE.md` §11 con los comandos de tests y linters | Exista el scaffold | Hoy están los dos verificadores; faltan las herramientas de código |
| Los tres pull requests de [7. Pull requests](07-pull-requests.md) | Se implemente la primera funcionalidad | Salen solos de los tres [cortes verticales](convenciones-de-desarrollo.md#1-cortes-verticales), no hay que fabricarlos al cierre |
| Definir hooks y subagentes | Exista el scaffold | Se evaluaron y se aplazaron a la fase de código, donde tienen sentido |

## Más adelante — aplicación móvil

| Qué | Por qué es barato si se hace en orden |
|---|---|
| Reutilizar el contrato de UI y los tokens en la app nativa | La máquina de estados pertenece al contrato de la pantalla, no a la tecnología que la renderiza |
| Regenerar el cliente de API desde el mismo OpenAPI | Es la promesa que justifica la arquitectura hexagonal en el [ADR 0001](adr/0001-arquitectura-hexagonal.md): una app móvil que consume la misma API sin tocar lógica de negocio |
| Evaluar auditorías de seguridad específicas de móvil | Recién tiene sentido cuando exista superficie móvil que auditar |

## Decisiones abiertas

- Los grupos 6 (multimoneda) y 9 (trazabilidad de origen) de
  [`reglas-de-dominio.md`](reglas-de-dominio.md) son grupos de enlace, sin texto propio: su
  contenido normativo vive en el catálogo de funcionalidades de
  [1.2](01-producto.md#12-características-y-funcionalidades-principales) y no se duplicó. Darles
  texto propio exige escribir contenido nuevo, no reorganizar el existente.
- El `README.md` superó el límite que tenía de portada e índice para incluir el flujo de trabajo
  con IA. Si vuelve a crecer, esa sección sale a un documento propio.
