# 0029 — El entorno `demo` en Render, en sus planes pagos más chicos

- Estado: Aceptada
- Fecha: 2026-10-29

## Contexto

La entrega final tiene que mostrar Platita desplegado: el entorno `demo`, con el chat web y la
entrada por un enlace personal, para que otra persona lo pruebe siendo dueña de sus datos
([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md),
[hoja de ruta](../hoja-de-ruta.md#alcance-de-la-entrega-final)). El
[ADR 0021](0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md) decidió que la rama
de la entrega despliega `demo` y que cada entorno tiene su propia base, pero dejó sin decidir
dónde se aloja.

[Operación](../operacion.md) propone, sin decidir, Render en sus planes pagos más chicos por
unos US$23 a 25 por mes, con una copia de la base fuera de Render, un cron despachador, un
dominio propio y monitoreo. Esa propuesta está pensada para `production` con WhatsApp: el plan
pago, por ejemplo, se justifica porque el webhook de Meta tiene que estar siempre despierto.
`demo` no tiene WhatsApp ni procesos programados, y sus datos son de prueba. Lo que necesita es
otra cosa: que quien evalúa abra su enlace, escriba un gasto y reciba la respuesta enseguida.

Los límites del plan gratuito de Render, verificados en su
[documentación](https://render.com/docs/free) el 2026-10-29:

- Un servicio web gratuito se duerme a los 15 minutos sin pedidos y tarda cerca de un minuto en
  despertar.
- No hay workers gratuitos: solo servicios web, bases y sitios estáticos.
- Una base gratuita vence a los 30 días de creada, con 14 días de gracia antes de borrarse, y no
  tiene recuperación ([copias de PostgreSQL](https://render.com/docs/postgresql-backups)).

## Decisión

1. **El entorno `demo` se aloja en Render, en la región de Virginia,** con tres piezas que usan
   la misma imagen del [ADR 0021](0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md):
   - Un servicio web de 512 MB, la instancia `0.5c-512mb`, con la API y el dashboard bajo `/app`, en el mismo origen
     ([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md)).
   - Un worker de 512 MB, la misma instancia, con el worker de mensajes
     ([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md)).
   - Una base Render Postgres de 256 MB, la instancia `0.1c-256mb`, con PostgreSQL 16, la versión de Compose, y la
     extensión pgvector, que Render admite con `CREATE EXTENSION vector`
     ([extensiones](https://render.com/docs/postgresql-extensions)).
2. **Plan pago y no gratuito.** El gratuito no tiene workers. Para usarlo habría que correr el
   worker dentro del servicio web, en contra del ADR 0010. Además, la primera respuesta de cada
   rato tardaría un minuto y la base podría vencer antes de la evaluación. Según la
   [página de precios](https://render.com/pricing), vista el 2026-10-29, cuesta US$20 por mes:
   US$7 por cada servicio y US$6 por la base, que incluye 1 GB de disco; cada GB más cuesta
   US$0,30. Lo que se paga es el cómputo de cada pieza, no la cuenta: el workspace es el Hobby,
   que no cobra nada aparte del cómputo e incluye la
   recuperación a un punto en el tiempo, el paso previo al despliegue y 500 minutos de
   compilación por mes. El tope del proveedor de LLM va aparte y no cambia
   ([2.4](../02-arquitectura.md#24-infraestructura-y-despliegue)).
3. **Las migraciones corren como paso previo al despliegue,** con `alembic upgrade head`. Render
   lo admite en servicios pagos y corre antes de cambiar la versión: si la migración falla, el
   despliegue se cancela y sigue la versión anterior
   ([despliegues](https://render.com/docs/deploys)). Es el equivalente del servicio de
   migraciones de Compose: ni la API ni el worker migran al arrancar.
4. **Despliega la rama de la entrega, `final-project-VNZ`, después de que pasan los controles.**
   El despliegue automático usa la opción de Render que espera a que pasen los checks del
   commit. Los flujos de la aplicación ya corren por push en `final-project-*`.
5. **La infraestructura queda versionada en un `render.yaml`,** sin el valor de ningún secreto.
   Las variables de entorno son las de [operación § 2](../operacion.md#2-entornos), con
   `APP_ENV=demo`. Los secretos, como la clave del modelo y la del servidor, se cargan en Render
   y nunca en el repositorio.
6. **Lo que la propuesta de operación suma para `production` no entra en `demo`:**
   - La copia diaria fuera de Render, porque los datos son de prueba y el aviso de prueba ya
     advierte que pueden borrarse.
   - El cron despachador, porque la entrega final no tiene procesos programados.
   - El dominio propio. `demo` se sirve desde un subdominio de `onrender.com`, y el dominio
     propio sigue siendo requisito antes de abrir a usuarios reales
     ([hoja de ruta](../hoja-de-ruta.md#decisiones-abiertas)).
   - Sentry, el monitor externo y las dos alertas críticas del
     [ADR 0023](0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md).
     `demo` se vigila con los registros de Render y con `/readyz` como control de salud del
     servicio web. Llegan con el primer despliegue de `production`, como corrige el ADR 0023.
7. **`demo` vive mientras dura la evaluación de la entrega final.** Después se suspende o se
   borra. Sus datos son de usuarios de prueba, y borrarlos es lo que el aviso de prueba
   advierte.
8. **`production` no queda decidido.** Su proveedor, su plan y sus copias siguen como propuesta
   en operación y como decisión abierta en la hoja de ruta.

## Consecuencias

### Positivas

- Quien evalúa recibe la respuesta del chat sin esperar a que el servicio despierte, y la base
  sigue ahí durante toda la evaluación, aunque haya prórroga.
- El despliegue respeta la arquitectura: el worker sigue aparte y una migración que falla no
  deja la aplicación a medias.
- Es la misma topología que la propuesta de producción, así que lo que se aprenda en `demo`
  sirve para ella.

### Negativas y costos asumidos

- US$20 por mes durante la evaluación, que el plan gratuito no cobraría.
- `demo` no tiene copia fuera de Render. Si se pierde la cuenta, se pierden los datos de prueba,
  y se vuelven a crear con los comandos de operación.
- La recuperación a un punto en el tiempo de la base es la del workspace Hobby: 3 días.
- Quedan por verificar en el primer despliegue:
  - Que 512 MB de memoria alcancen para la API y para el worker.
  - Que la migración del esquema pueda crear el rol `platita_app` en la base gestionada
    ([ADR 0015](0015-borrado-logico-de-movimientos.md)).
  - Que la redirección de `/app` a `/app/` salga con `https` detrás del proxy de Render.

## Alternativas descartadas

- **Render en sus planes gratuitos:** cuesta cero, pero no tiene workers, se duerme y su base
  vence a los 30 días.
- **Un servidor virtual único con Docker Compose, por unos US$6 por mes:** reproduce el entorno
  local tal cual, pero suma parchear el sistema, administrar PostgreSQL, renovar el certificado
  y escribir los despliegues, todo a cargo de una sola persona en las semanas de la entrega.
- **Otros proveedores de aplicaciones gestionadas:** no se evaluaron. Render ya era la
  propuesta de [2.4](../02-arquitectura.md#24-infraestructura-y-despliegue) por pgvector y por
  la simplicidad, y la entrega no deja tiempo para una comparación nueva.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
