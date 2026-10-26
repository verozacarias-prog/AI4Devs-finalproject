# Platita

Quien maneja varias cuentas y billeteras, en pesos y en dólares, y comparte un presupuesto con su
familia, hoy lo ordena a mano en planillas. Platita es un asistente financiero al que se le
escribe en lenguaje natural —"gasté 3500 en el súper con Mercado Pago"—: una capa de IA
interpreta el mensaje, pregunta lo que falta y registra el movimiento en su cuenta y su
presupuesto, que se consultan en un dashboard web. Está pensado para WhatsApp; en el MVP se usa
desde el chat del dashboard, que recorre el mismo camino.

**Estado:** entrega final en curso, para el 12 de noviembre de 2026. El avance está en el
[tablero](https://github.com/users/verozacarias-prog/projects/1) y en el milestone
[Entrega final](https://github.com/verozacarias-prog/AI4Devs-finalproject/milestones).

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

Pendiente: llega con el despliegue del entorno `demo`, en la entrega final.

### 0.5. URL o archivo comprimido del repositorio

https://github.com/verozacarias-prog/AI4Devs-finalproject

---

## Cómo se trabajó con IA

Todo el proyecto, de la idea al código, se hizo con asistentes de IA, y su configuración está
versionada en el repositorio. El código se escribe con especificación y tests primero: la IA
propone los casos de prueba de cada corte, la autora los aprueba antes de que exista un test, y
cada pull request lo revisa un agente en un contexto separado antes de que la autora lo pruebe e
integre. La IA no escribe un test sin casos aprobados, y nunca integra.

- [`prompts.md`](prompts.md): la metodología en un diagrama, las herramientas y modelos por fase,
  los prompts clave de cada sección y los ajustes humanos sobre el output de la IA.
- [Flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md): el contrato `AGENTS.md`, el agente
  revisor, los commands, el skill, los verificadores y el hook de pre-commit.
- [Registro completo](docs/registro-ia.md) y la
  [conversación de la reestructuración](docs/conversacion-reestructuracion-docs.md), como anexos.

## Documentación

| Documento | Contiene |
|---|---|
| [1. Descripción general del producto](docs/01-producto.md) | Objetivo, catálogo must/should/could, flujo conversacional e instrucciones de instalación. |
| [2. Arquitectura del sistema](docs/02-arquitectura.md) | Diagramas C4, componentes, estructura de ficheros, infraestructura, seguridad y tests. |
| [3. Modelo de datos](docs/03-modelo-de-datos.md) | Diagrama entidad-relación y descripción de cada entidad. |
| [4. Especificación de la API](docs/04-api.md) | Los endpoints principales con sus contratos de request y response. |
| [5. Historias de usuario](docs/05-historias-de-usuario.md) | Las siete historias con sus criterios de aceptación, prioridad y estimación. |
| [6. Tickets de trabajo](docs/06-tickets.md) | Los tres tickets de backend, frontend y base de datos. |
| [7. Pull requests](docs/07-pull-requests.md) | Los pull requests de cada entrega y la Definition of Done. |
| [8. Convenciones de documentación](docs/08-convenciones-de-documentacion.md) | Idioma, diagramas, nombres de archivo y estructura de `docs/`. |
| [Recorrido completo](docs/recorrido-completo.md) | El recorrido del usuario de punta a punta: qué proceso actúa, si la llamada es HTTPS o SQL y qué tablas escribe cada paso. |
| [Reglas de dominio](docs/reglas-de-dominio.md) | Dueño único de las reglas de negocio, agrupadas por tema. |
| [Convenciones de desarrollo](docs/convenciones-de-desarrollo.md) | Cortes verticales y los cuatro estados de una pantalla. |
| [Términos y privacidad](docs/terminos-y-privacidad.md) | Qué tienen que cubrir los términos y la política de privacidad, antes de redactarlos. |
| [Validación por casos de uso](docs/use-case-walkthrough.md) | Registro, no especificación: 51 casos cotidianos de usuarios argentinos recorridos sobre el diseño, las decisiones pendientes que dejan y los escenarios para las pruebas. |
| [Hoja de ruta](docs/hoja-de-ruta.md) | Qué entra en la entrega 2, qué en la final y qué en una segunda versión, y por qué. |
| [Operación](docs/operacion.md) | Entornos, pipeline, despliegue, copias de respaldo y observabilidad, con lo decidido separado de lo que sigue como propuesta. |
| [Seguridad de la capa de IA](docs/seguridad-llm.md) | Platita contra el OWASP Top 10 para aplicaciones LLM: qué cubre cada riesgo y qué falta. |
| [Flujo de trabajo con IA](docs/flujo-de-trabajo-con-ia.md) | Contratos, skill, commands, agente revisor, verificadores y hooks. |
| [Cómo colaborar](docs/como-colaborar.md) | Ramas, issues, los pasos para incluir un cambio y cómo se verifica. |
| [Documentación viva](docs/documentacion-viva.md) | Cómo se mantiene sincronizada la documentación: fuente única, portal, `llms.txt` y las tres barreras de validación. |

La documentación se publica también como sitio navegable en
**<https://verozacarias-prog.github.io/AI4Devs-finalproject/>**. Las decisiones de arquitectura
están en [`docs/adr/`](docs/adr/), y las plantillas de una funcionalidad nueva, en
[`docs/features/`](docs/features/).

## Cómo ejecutar localmente

Hace falta Docker y una clave de OpenAI en `OPENAI_API_KEY`, en `.env` o exportada en la
terminal. Compose levanta la base, las migraciones, la API, que sirve también el dashboard, y el
worker, que responde los mensajes del chat con el modelo.

```sh
cp .env.example .env
docker compose up --build
# en otra terminal: tres usuarios inventados, con sus cuentas y su primer período
docker compose exec api python -m app.adapters.inbound.operator_commands.seed_test_data
```

| Dirección | Qué es |
|---|---|
| <http://127.0.0.1:8000/app/> | El dashboard, con la entrada de desarrollo: se elige un usuario de prueba y se abre una sesión real, sin código. Mejor en Chrome o Firefox, que aceptan la cookie `Secure` sin HTTPS en la propia máquina |
| <http://127.0.0.1:8000/docs> | La referencia de la API en Swagger, generada desde el código |
| `127.0.0.1:5433` | PostgreSQL, con el usuario, la clave y la base de `.env` |

Qué trae cada usuario de prueba está en [operación](docs/operacion.md#2-entornos).

### Probar el flujo

1. Abrir <http://127.0.0.1:8000/app/>, elegir a Lucía en la entrada de desarrollo e ir al chat.
2. Escribir un gasto que nombre la cuenta, como "gasté 3500 en el súper con Mercado Pago". El
   asistente confirma qué anotó, con la fecha, la moneda, la categoría y el presupuesto.
3. Ir a Cuentas: Mercado Pago muestra $3.500 menos.
4. Probar lo que exige preguntar: un gasto sin cuenta ("gasté 3500 en el súper"), y responder
   la pregunta con "con MP"; o uno que no encaja en ninguna categoría ("gasté 9000 en la
   peluquería con MP"), y aceptar la que propone con "sí".

### Probar el presupuesto

Armar los topes de un período todavía no se puede desde la aplicación, así que un script le
carga a Lucía un ingreso estimado, tres topes y algunos movimientos, en su período actual. Se
corre una sola vez, después de los datos de prueba:

```sh
docker compose exec -T db psql -U platita -d platita < scripts/budget_test_data.sql
```

En Presupuesto, Supermercado queda por debajo del tope, Salud cerca y Transporte excedido; las
categorías sin tope muestran solo lo gastado, y desde Supermercado se ve el detalle, con un
gasto en dólares y su cotización y un reintegro que resta.

Los límites de uso por día son 100 mensajes clasificados y 50 registros, y se bajan al levantar
para verlos actuar. Cada llamada al modelo queda en la tabla `llm_call`, sin ningún contenido, y
sus métricas de latencia, costo, calidad y alucinaciones salen de un script:

```sh
LLM_DAILY_REGISTRATION_LIMIT=2 LLM_DAILY_CLASSIFICATION_LIMIT=5 docker compose up --build
docker compose exec -T db psql -U platita -d platita < scripts/llm_metrics.sql
```

### Tests

Los del backend, con la base de Compose levantada, y los del dashboard:

```sh
(cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest)
(cd frontend && npm ci && npm test)
```

Y el de punta a punta, que levanta todo con Compose en otros puertos, con un proveedor del
modelo simulado, entra como Lucía, anota un gasto en el chat y mira el saldo nuevo. No necesita
`.env` ni clave, y al terminar borra lo que levantó:

```sh
(cd frontend && npx playwright install chromium && npm run test:e2e)
```

## Cómo colaborar

Las ramas, las issues, los pasos para incluir un cambio y los verificadores están en
[cómo colaborar](docs/como-colaborar.md).
