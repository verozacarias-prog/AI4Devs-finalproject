# 0021 — Una imagen, Docker Compose para levantar todo y un pipeline de cinco controles

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

[Operación](../operacion.md) propone cómo construir, probar y desplegar Platita, pero como
propuesta sin decidir, y es más de lo que hace falta para empezar a escribir código. La entrega 2
necesita dos cosas concretas: que el proyecto se levante en una máquina con un solo comando, y
que cada cambio pase por controles automáticos desde el primer commit de código.

Tres decisiones anteriores acotan la respuesta:

- La API y el worker son el mismo código con distinto punto de entrada
  ([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md)).
- La API sirve el build del dashboard bajo `/app`
  ([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md)).
- Las migraciones corren una sola vez, antes de que arranque cualquier proceso, y ningún proceso
  migra al arrancar ([2.4](../02-arquitectura.md#24-infraestructura-y-despliegue)).

El repositorio es un fork del repositorio del curso: los flujos se disparan con push a
`feature/**`, y un pull request contra el repositorio de origen ejecuta los flujos de allá
([documentación viva](../documentacion-viva.md#7-el-modelo-de-ramas-condiciona-el-despliegue)).

## Decisión

1. **Una sola imagen para la API y el worker.** El Dockerfile tiene dos etapas: la primera
   compila el dashboard, y la final lleva el backend con ese build, que la API sirve bajo
   `/app`. La imagen corre con un usuario sin privilegios y declara un chequeo de salud contra
   `GET /healthz`.
2. **Docker Compose con cuatro servicios.** La base, con la imagen `pgvector/pgvector:pg16`;
   las migraciones, que corren `alembic upgrade head` una vez y terminan; la API; y el worker.
   La API y el worker esperan a que las migraciones terminen bien, y ninguno de los dos migra al
   arrancar. El worker no escucha HTTP, así que en su servicio el chequeo de salud de la imagen
   queda desactivado.
3. **Lo que todavía no entra usa la misma imagen.** Los procesos programados serán un quinto
   servicio cuando se construyan. El comando que carga la base de conocimiento
   ([ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md)) corre con ella,
   a pedido.
4. **Secretos fuera del repositorio.** Un `.env` sin versionar tiene los valores, y un
   `.env.example` versionado lista los nombres de las variables.
5. **Sin adaptador falso de LLM dentro de la aplicación.** Los dobles del LLM y de embeddings
   viven solo en los tests automáticos. Las pruebas manuales, en local y en demostración, usan
   el modelo real, así que necesitan la clave del proveedor.
6. **Cinco controles en paralelo, desde el primer commit de código:**
   1. Formato, lint y tipos. En el backend, `ruff` y `mypy` en modo estricto. En el dashboard,
      su linter, su verificación de tipos y la compilación.
   2. Tests unitarios y de integración, con `pytest` contra un PostgreSQL real con pgvector y
      con dobles para el LLM y los embeddings. Cada corrida aplica las migraciones desde una
      base vacía. Incluye los tests del dashboard, con los cuatro estados de cada pantalla.
   3. Los dos verificadores del repositorio.
   4. Secretos en el código, con `gitleaks`.
   5. Vulnerabilidades en dependencias. En Python, `pip-audit`, que bloquea ante cualquier
      vulnerabilidad que tenga arreglo: la herramienta no filtra por severidad. En el dashboard,
      `npm audit`, que bloquea desde severidad alta. Además, Dependabot propone una vez por
      semana la actualización de las dependencias y de las acciones.
7. **Solo lectura y acciones fijadas.** Los flujos corren con permiso de solo lectura sobre el
   repositorio. Cada acción se referencia por el hash de su commit, con la versión en un
   comentario. El flujo que publica el portal conserva los permisos de Pages, que necesita para
   desplegar.
8. **El pipeline no guarda secretos.** Ningún control necesita una credencial. Es la regla de
   [Operación](../operacion.md#3-pipeline-de-la-aplicación), y no cambia.
9. **Qué bloquea el merge.** Los controles corren en cada push a la rama de trabajo y en cada
   pull request. Para que además impidan un merge, la rama de la entrega tiene que estar
   protegida en este repositorio, con esos controles como obligatorios. Es una configuración de
   GitHub, que se hace a mano.
10. **Se aplica ahora lo que no depende del código:** el control de secretos, las acciones
    fijadas por hash y Dependabot para las acciones y para `site/`. El resto se crea con el
    primer commit de código, no antes: un flujo sin nada que compilar ni testear fallaría.
11. **Quedan para la entrega final:** el escaneo de la imagen, la prueba de la migración desde
    el esquema de la versión anterior y el inventario de componentes de la imagen.

## Consecuencias

### Positivas

- Quien clona el repositorio levanta la base, las migraciones, la API y el worker con un
  comando, con la misma imagen que después se despliega.
- El orden de arranque repite el de producción: primero migra un solo proceso, después arranca
  el resto.
- Una acción fijada por hash no cambia sola si alguien mueve su etiqueta.
- El flujo conversacional que se prueba a mano es el real: no hay un camino con respuestas
  inventadas que pueda quedar encendido.

### Negativas y costos asumidos

- Probar a mano cuesta tokens y exige una clave del proveedor en cada máquina.
- Las acciones fijadas por hash hay que actualizarlas. Dependabot abre un pull request por
  semana, que alguien tiene que mirar.
- En un fork, Dependabot y la protección de la rama se habilitan a mano en GitHub. Si nadie lo
  hace, los controles avisan pero no bloquean.
- En Python el control de vulnerabilidades es más estricto que en el dashboard: bloquea también
  una vulnerabilidad baja, si tiene arreglo.
- `gitleaks` marca ejemplos que no son secretos. Los seis que encontró en el historial, cinco
  heredados del repositorio del curso, están exceptuados uno por uno en `.gitleaksignore`.
- Hasta la entrega final nadie revisa las vulnerabilidades de la imagen base.

## Alternativas descartadas

- **Un adaptador falso de LLM para desarrollo y demostración:** levantar todo sin clave y sin
  costo, pero es código de la aplicación que responde sin modelo, y hay que impedir que quede
  activo en producción. Lo que mostraría tampoco sería el producto.
- **Que la API o el worker migren al arrancar:** un servicio menos en Compose, pero es justo lo
  que 2.4 prohíbe: dos procesos que arrancan a la vez compiten por aplicar la misma migración.
- **Una imagen para la API y otra para el worker:** cada una más chica, a cambio de dos
  construcciones que pueden quedar en versiones distintas del mismo código.
- **Escanear la imagen desde el inicio:** es parte de la propuesta de Operación. Se posterga
  porque hasta el primer despliegue la imagen no sale de la máquina de desarrollo.
- **Referenciar las acciones por su etiqueta de versión mayor,** como estaban: se actualizan
  solas, pero también si alguien reescribe la etiqueta.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
