# 0001 — Arquitectura hexagonal (ports & adapters)

- Estado: Aceptada
- Fecha: 2026-09-20

## Contexto

Platita depende de varias integraciones externas —WhatsApp, email, LLM, base vectorial,
cotizaciones, REM— que van a cambiar con el tiempo, y donde ya se identificó al menos un
reemplazo probable: el motor de vectores. Además está previsto un dashboard web desacoplado y,
más adelante, la posibilidad de una app móvil sobre la misma API.

## Decisión

Arquitectura hexagonal (ports & adapters), con el dominio —entidades y casos de uso— aislado de
los detalles de infraestructura detrás de puertos. Backend y frontend quedan desacoplados,
comunicados únicamente por API REST.

**Quién accede a la base de datos.** El backend es el único que la toca, y el backend no es solo
la API: son los tres procesos que comparten el código del dominio.

1. **Desde afuera, solo por HTTP.** El dashboard, una futura app móvil y Meta (por el webhook)
   entran únicamente por la API. Ningún cliente externo recibe credenciales de la base ni se
   conecta a ella.
2. **Adentro, tres puntos de entrada y un solo camino.** La API (`adapters/inbound/api/` y
   `adapters/inbound/whatsapp_webhook/`), el worker de mensajes
   (`adapters/inbound/message_worker/`) y los procesos programados
   (`adapters/inbound/scheduler/`) son adaptadores de entrada: traducen su disparador (un
   request, un mensaje guardado, una hora) a llamadas a casos de uso, y los casos de uso usan
   los repositorios a través de puertos. Ninguno escribe SQL propio.
3. **Ningún proceso llama a otro por HTTP.** El worker y los procesos programados no llaman a la
   API: usan los mismos casos de uso en su propio proceso. Una llamada HTTP interna partiría en
   dos lo que tiene que ser una sola transacción, y sumaría una credencial de servicio que hoy no
   existe.
4. **La transacción la abre el caso de uso, a través de un puerto.** Cuando un caso de uso
   necesita que varios cambios se confirmen juntos, como los efectos de un mensaje, su paso a
   procesado y la respuesta encolada ([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md)),
   los pide a un puerto de unidad de trabajo. Lo implementa `adapters/outbound/postgres/`, así el
   dominio sigue sin importar SQLAlchemy.
5. **El SQL vive en un solo lugar.** Las librerías de acceso a la base (`sqlalchemy`, `psycopg`,
   `asyncpg`) solo se importan en `adapters/outbound/postgres/`, `adapters/outbound/pgvector/`,
   `backend/migrations/` y `backend/tests/`. Ahí se crea también la conexión que los puntos de
   entrada inyectan al arrancar.
6. **Excepciones, y son todas.** Tocan la base sin pasar por un caso de uso solamente:
   - las migraciones de Alembic, que cambian el esquema en el paso previo al despliegue;
   - el script de datos de prueba, que se niega a correr contra producción;
   - el acceso operativo de una persona para copias, restauraciones y diagnóstico, descrito en
     [Operación](../operacion.md). Ninguna funcionalidad del producto puede depender de él.

   El proceso de borrado de cuenta no es una excepción: es un proceso programado más, que usa
   su propio rol de base con permiso de `DELETE`
   ([ADR 0015](0015-borrado-logico-de-movimientos.md)).
7. **Solo los procesos del backend reciben la credencial.** La variable de conexión a la base se
   configura en el servicio web, en el worker y en los procesos programados, y en ningún otro
   lado. El proveedor de LLM tampoco accede a la base
   ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md)).

## Consecuencias

### Positivas

- El dominio no conoce los detalles de cada integración: cada una es un adaptador detrás de un
  puerto, y cambiarla es reemplazar el adaptador, no tocar la lógica de negocio.
- Los casos de uso (registrar un movimiento, evaluar un presupuesto, generar un consejo) se
  pueden testear sin levantar WhatsApp, un LLM real ni una base de datos: se testean contra los
  puertos, con dobles de prueba.
- Separar front de back deja la puerta abierta a una futura app móvil que consuma la misma API
  sin tocar lógica de negocio.
- Es el mismo patrón que ya se usa en otros proyectos propios en Go, así que la disciplina de
  diseño ya es conocida, solo cambia el lenguaje.
- Una regla de negocio se implementa una sola vez: la API, el worker y los procesos programados
  la ejecutan por el mismo caso de uso, en vez de repetirla en un script con SQL propio.
- Que el SQL viva en un solo lugar es verificable: un script falla el commit si una librería de
  acceso a la base aparece fuera de los directorios permitidos.

### Negativas y costos asumidos

- Más carpetas e indirección que un CRUD directo controlador-a-base de datos. Para un proyecto
  de este tamaño el volumen de casos de uso reales lo justifica.
- Mitigación: mantener los puertos chicos y con una sola responsabilidad cada uno, en vez de una
  interfaz gigante.
- La API, el worker y los procesos programados se despliegan con el mismo código. Un cambio en
  un caso de uso reinicia los tres, aunque solo lo use uno.
- Una consulta de lectura simple, como listar movimientos para el dashboard, también pasa por un
  caso de uso y un repositorio, aunque un router con SQL directo sería más corto.

## Alternativas descartadas

- **CRUD directo controlador-a-base de datos:** menos carpetas e indirección, descartado porque
  con este número de integraciones externas cambiantes el dominio quedaría acoplado a detalles
  de infraestructura y los casos de uso no serían testeables sin levantar servicios reales.
- **El worker y los procesos programados como clientes HTTP de la API:** dejaría a la API como
  única puerta a la base también por dentro, pero rompe la atomicidad del procesamiento de un
  mensaje: si el proceso se cae entre la llamada a la API y la marca de procesado, el reintento
  registra el movimiento dos veces. Además exige una credencial de servicio y hace que una caída
  de la API detenga también el worker.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
