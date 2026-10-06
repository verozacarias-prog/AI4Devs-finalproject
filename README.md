# Platita

Asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos, ingresos y presupuestos conversando en lenguaje natural, y una capa de IA interpreta, categoriza y guarda cada movimiento en la cuenta correspondiente.
Más adelante, un módulo complementario leerá los emails de notificación bancaria y de servicios para reducir la carga manual; no forma parte del MVP.
Toda la información —cuentas y su saldo, presupuestos multimoneda y consejos financieros generados con RAG— se visualiza desde una aplicación web con dashboards, y la comparación contra la inflación queda prevista para una versión futura.

**Estado:** Entrega 1 — documentación. Fecha límite de entrega: 24 de septiembre de 2026.

---

## 0. Ficha del proyecto

### 0.1. Tu nombre completo:

Verónica Noemi Zacarías

### 0.2. Nombre del proyecto:

**Platita** — asistente financiero personal y familiar por WhatsApp

> *(Nombre de producto en español porque el público objetivo es hispanohablante; el código, el modelo de datos y la API van en inglés — ver [nota de idioma](docs/08-convenciones-de-documentacion.md#81-idioma).)*

### 0.3. Descripción breve del proyecto:

Platita es un asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos, ingresos y presupuestos conversando en lenguaje natural, y una capa de IA interpreta, categoriza y guarda cada movimiento en la cuenta correspondiente. Más adelante, un módulo complementario leerá los emails de notificación bancaria y de servicios para reducir la carga manual; no forma parte del MVP. Toda la información —incluyendo cuentas y su saldo, presupuestos multimoneda y consejos financieros generados con RAG— se visualiza en detalle desde una aplicación web con dashboards. La comparación contra la inflación queda prevista para una versión futura.

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
| [5. Historias de usuario](docs/05-historias-de-usuario.md) | Las siete historias con sus criterios de aceptación, prioridad y estimación. |
| [6. Tickets de trabajo](docs/06-tickets.md) | Los tres tickets de backend, frontend y base de datos. |
| [7. Pull requests](docs/07-pull-requests.md) | Los pull requests de la entrega final. |
| [8. Convenciones de documentación](docs/08-convenciones-de-documentacion.md) | Idioma, diagramas, nombres de archivo y estructura de `docs/`. |
| [Recorrido completo](docs/recorrido-completo.md) | El recorrido del usuario de punta a punta: qué proceso actúa, si la llamada es HTTPS o SQL y qué tablas escribe cada paso. |
| [Reglas de dominio](docs/reglas-de-dominio.md) | Dueño único de las reglas de negocio, agrupadas por tema. |
| [Convenciones de desarrollo](docs/convenciones-de-desarrollo.md) | Cortes verticales y los cuatro estados de una pantalla. |
| [Términos y privacidad](docs/terminos-y-privacidad.md) | Qué tienen que cubrir los términos y la política de privacidad, antes de redactarlos. |
| [Validación por casos de uso](docs/use-case-walkthrough.md) | Registro, no especificación: 51 casos cotidianos de usuarios argentinos recorridos sobre el diseño, las decisiones pendientes que dejan y los escenarios para las pruebas. |
| [Hoja de ruta](docs/hoja-de-ruta.md) | Qué queda para la entrega 2 y para la app móvil, y por qué. |
| [Operación](docs/operacion.md) | Entornos, pipeline, despliegue, copias de respaldo y observabilidad, con lo decidido separado de lo que sigue como propuesta. |
| [Seguridad de la capa de IA](docs/seguridad-llm.md) | Platita contra el OWASP Top 10 para aplicaciones LLM: qué cubre cada riesgo y qué falta. |
| [Flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md) | Contratos, skill, commands, agente revisor, verificadores y hooks. |
| [Documentación viva](docs/documentacion-viva.md) | Cómo se mantiene sincronizada la documentación: fuente única, portal, `llms.txt` y las tres barreras de validación. |

La documentación también se publica como sitio navegable en
**<https://verozacarias-prog.github.io/AI4Devs-finalproject/>**, generado desde `docs/` en cada
integración a la rama de la entrega en curso y a `main`.

Las decisiones de arquitectura, una por archivo y en formato Michael Nygard, viven en [`docs/adr/`](docs/adr/).

Las plantillas que se copian al abrir una funcionalidad nueva están en [`docs/features/`](docs/features/).

El registro de uso de IA durante el proyecto está en [`prompts.md`](prompts.md), con la [conversación completa de la reestructuración](docs/conversacion-reestructuracion-docs.md) como anexo.

---

## Flujo de trabajo con IA

El proyecto se desarrolla con asistentes de IA y la configuración está versionada en el
repositorio: un skill, tres commands, un agente revisor, dos verificadores y un hook de pre-commit.
Todo está descrito en el [flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md).

## Cómo colaborar

Los pasos para incluir un cambio, en orden. El detalle de cada uno está en el documento enlazado.
En el backend se trabaja con tests primero ([ADR 0024](docs/adr/0024-tests-primero-en-el-backend.md)).

**Ramas.** Cada entrega tiene su rama, `feature/entrega-N-VNZ`, que sale de `main` y vuelve a
`main` cuando la entrega se cierra. El trabajo no se hace ahí: cada cambio va en una rama corta
que sale de la rama de la entrega y vuelve a ella por pull request. La rama de la entrega
despliega el entorno de pruebas, y `main`, producción. El porqué está en
[documentación viva](docs/documentacion-viva.md#7-el-modelo-de-ramas).

| Rama | Sale de | Nombre | Ejemplo |
|---|---|---|---|
| De entrega | `main` | `feature/entrega-<N>-VNZ` | `feature/entrega-2-VNZ` |
| De un corte de una historia | La rama de la entrega | `hu<N>-c<corte>-<tema>` | `hu3-c1-registro-de-gasto` |
| De lo que no es una historia | La rama de la entrega | `tarea-<tema>` | `tarea-scaffold-y-docker` |

**Una vez por clon.**

```sh
git config core.hooksPath .githooks   # activa el hook de pre-commit
cd site && npm install                # solo para ver o regenerar el portal
```

**Para incluir un cambio.**

1. **Crear la rama** desde la rama de la entrega, con el nombre de la tabla. Una historia son
   tres ramas, una por [corte vertical](docs/convenciones-de-desarrollo.md#1-cortes-verticales).
2. **Leer antes de escribir.** [`AGENTS.md`](AGENTS.md) es el contrato, y su sección 12 dice qué
   leer según el cambio. Si toca movimientos, cuentas, presupuestos o categorías, el skill
   `domain-rules` se activa solo y dice qué reglas aplican.
3. **Especificar.** Copiar [`docs/features/TEMPLATE/`](docs/features/TEMPLATE/) a
   `docs/features/FEAT-XXX/` y completar `spec.md`, con los criterios de aceptación numerados, y
   `ui_contract.md` si hay pantalla.
4. **Aprobar los casos de prueba** del corte en `qa_plan.md`. El asistente los propone; sin la
   aprobación de una persona no se escribe ningún test. En una rama `tarea-…` no hay carpeta:
   los casos aprobados van en la descripción del pull request.
5. **Escribir los tests del backend y verlos fallar.** Es el primer commit del corte,
   `test(alcance): …`. Desde ahí, un test no se modifica ni se borra sin aprobación.
6. **Implementar lo mínimo para que pasen,** y refactorizar en verde. Es el segundo commit,
   `feat(alcance): …`. Los tests de los cuatro estados de una pantalla van en este mismo corte.
   La documentación que el cambio afecta —API, modelo de datos, reglas de dominio— va en el
   mismo commit, y una decisión de arquitectura lleva su [ADR](docs/adr/).
7. **Verificar antes de cada commit.** El hook corre solo los dos verificadores de
   [Verificación](#verificación). Si cambió `docs/`, además `cd site && npm run build`, que
   regenera `llms.txt`. Un documento nuevo se suma a la tabla de arriba y a la barra lateral de
   `site/astro.config.mjs`.
8. **Escribir cada commit** con el [formato de mensaje](docs/convenciones-de-desarrollo.md#1-cortes-verticales)
   `tipo(alcance): qué cambia`, en español.
9. **Cerrar el corte** con `/spec-drift`, y con `/ui-states` si tiene pantalla.
10. **Abrir el pull request contra la rama de la entrega,** con el corte en verde y el cuerpo de
   [`pr.md`](docs/features/TEMPLATE/pr.md) y el [Definition of Done](docs/07-pull-requests.md#definition-of-done).
   Correr el agente `pr-reviewer` y pegar su informe.
11. **Integrar** cuando todos los controles pasan, con un commit de merge y sin aplastar los
    commits, para que se vea que los tests fueron primero. La aprobación y el merge son de una
    persona; un asistente hace commit solo si se lo piden, y nunca hace merge.

**Para abrir y cerrar una entrega.**

- **Abrir:** crear `feature/entrega-<N>-VNZ` desde `main`; ponerla como rama por defecto del
  repositorio, porque de ahí se publica el portal y ahí abre Dependabot sus pull requests; y
  protegerla, con los controles como obligatorios.
- **Cerrar:** correr `/security-audit` y `/spec-drift` sobre todo el proyecto, registrar los
  prompts en [`prompts.md`](prompts.md) y abrir el pull request de la rama de la entrega a
  `main`.
- **Cada lunes:** revisar los pull requests de Dependabot.

Los commands, el skill y el agente están descritos en el
[flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md).

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
