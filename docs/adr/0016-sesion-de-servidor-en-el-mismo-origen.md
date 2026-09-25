# 0016 — Sesión de servidor revocable en una cookie, con el dashboard servido desde la API

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

El [ADR 0003](0003-login-por-codigo-unico.md) decidió el login del dashboard sin contraseñas: el
usuario pide un código, lo recibe por WhatsApp y lo canjea por un JWT de corta duración. La API
lo concretó en un token de 15 minutos, sin renovación.

Un modelo de amenazas del diseño encontró que un JWT así no se puede revocar. Un token emitido
sigue sirviendo hasta que vence, sin que importe lo que pase después:

- Cerrar sesión no corta nada: el token sigue siendo válido en el lugar de donde lo copiaron.
- Pedir el borrado de la cuenta la desactiva, pero no invalida las sesiones abiertas.
- Si el usuario pierde el teléfono o sospecha que alguien entró, no tiene cómo cerrar las
  sesiones de otros dispositivos.

En Platita eso pesa más que en otros productos, porque el teléfono es el único factor: quien
controla el número de WhatsApp recibe el código. La única defensa después de un acceso indebido
es poder cortar sesiones.

Además, el cliente tiene que guardar el JWT en algún lado, y ninguna opción es buena. En
`localStorage` lo puede leer y llevarse cualquier script inyectado en la página. En memoria se
pierde al recargar, y cada recarga obliga a pedir otro código, que es un mensaje de plantilla
que se paga.

Revocar un JWT exige consultar una lista en la base en cada request, y eso elimina la única
ventaja que tiene sobre una sesión guardada en la base.

Una cookie `HttpOnly` resuelve el almacenamiento, porque ningún script la puede leer. Pero el
navegador la trata como de terceros, y la bloquea, cuando la página y la API están en sitios
distintos. Ese es el despliegue previsto: el dashboard como Static Site y la API como Web
Service en Render, cada uno en su propio subdominio de `onrender.com`. Ese dominio está en la
Public Suffix List, así que dos subdominios suyos son dos sitios distintos. Un dominio propio lo
resolvería, pero es un costo y algo más para administrar en un MVP que construye y opera una sola
persona, todavía sin usuarios.

El volumen esperado es muy bajo, y la aplicación móvil es a futuro, sin fecha estimada.

## Decisión

El login conserva el código de un solo uso por WhatsApp, y el código se canjea por una sesión
guardada en la base, no por un JWT. El dashboard se sirve desde el mismo servicio que la API,
para que la cookie de sesión funcione sin un dominio propio.

1. **El código no cambia.** El usuario pide acceder, recibe por WhatsApp un código de un solo
   uso, de vencimiento corto y con intentos limitados, y lo canjea. Lo único que cambia es lo que
   recibe a cambio.
2. **Sesión en PostgreSQL.** Al canjear el código se crea una fila en una tabla `session`, con
   el usuario, el hash del token, la creación, la última actividad, el vencimiento y
   `revoked_at`. El token es un valor aleatorio de 256 bits, y la base guarda solo su hash. Cada
   login genera un token nuevo. La sesión vence a los 30 minutos sin actividad o a las 12 horas
   de creada, lo que ocurra primero.
3. **Cookie.** El token viaja en una cookie `__Host-sid` con `HttpOnly`, `Secure`,
   `SameSite=Strict` y `Path=/`, sin `Domain`. El prefijo `__Host-` hace que el navegador la
   rechace si le falta alguno de esos atributos.
4. **Revocación.** Cada request autenticada verifica que la sesión exista, no esté revocada y no
   haya vencido. Cerrar sesión revoca la actual, y el dashboard ofrece cerrar todas las del
   usuario. Pedir el borrado de la cuenta revoca todas.
5. **Mismo origen.** El Web Service de la API sirve también el build del dashboard, bajo el
   prefijo `/app`. Las rutas de la API no cambian. El frontend sigue en `frontend/` sin importar
   nada del backend y se comunica solo por la API REST. Lo único nuevo es que su build se copia
   al servicio en el paso de despliegue. Desaparece el Static Site.
6. **Sin CORS.** La API no habilita CORS: una página de otro origen no puede hacerle requests
   con la cookie.
7. **CSRF.** Además de `SameSite=Strict`, toda request que modifica algo exige que el header
   `Origin` sea el propio y que el cuerpo sea JSON. El webhook de WhatsApp queda fuera de esta
   regla: no usa cookie y se autentica con su firma.

## Consecuencias

### Positivas

- Revocar es inmediato: cerrar sesión, cerrar todas y pedir el borrado cortan el acceso en el
  próximo request.
- Ningún script de la página puede leer el token, así que una inyección de código en el
  dashboard no se lo puede llevar.
- No hay clave de firma que custodiar ni que rotar.
- Sin CORS no hay configuración de orígenes permitidos que pueda quedar mal escrita.
- Un servicio menos para desplegar en Render.
- Recargar la página no pide un código nuevo mientras la sesión esté vigente.

### Negativas y costos asumidos

- Una consulta a la base por request autenticada. A este volumen, sobre una clave indexada, no
  se nota.
- Una tabla más, y un proceso programado que borre las sesiones vencidas.
- El dashboard se sirve desde Python y pierde la red de distribución del Static Site. Con pocos
  usuarios no se nota.
- El dashboard y la API se despliegan juntos: un cambio solo visual reinicia también el servicio
  que recibe el webhook. Meta reintenta lo que no recibió `200`, así que no se pierden mensajes.
- Como el servicio sirve HTML, también le corresponde enviar los headers de seguridad de la
  página, incluida una política de contenido (CSP), que antes eran configuración del Static
  Site.
- Una aplicación móvil nativa no puede usar la cookie tal cual: necesitará el mismo token en un
  header `Authorization`. Se decide cuando exista la aplicación, que es también el momento de
  revisar este registro.
- No resuelve el phishing. Un usuario no distingue con facilidad el subdominio real de
  `onrender.com` de uno parecido. Antes de abrir Platita a usuarios reales conviene un dominio
  propio. Con él se podría volver a un Static Site aparte, en un subdominio del mismo sitio, sin
  cambiar la sesión.

## Alternativas descartadas

- **Mantener el JWT de 15 minutos:** no se puede revocar, y obliga a guardar el token donde un
  script lo puede leer o a pedir un código en cada recarga.
- **JWT corto más un token de renovación opaco guardado en la base:** permite revocar, pero son
  dos mecanismos y una clave de firma para lograr lo mismo que una sesión. Además, el token de
  renovación también necesita viajar en una cookie, así que no evita el problema del mismo sitio.
- **Token opaco en `sessionStorage`, enviado como header, con el Static Site aparte:** funciona
  entre orígenes distintos y sin dominio propio, y se puede revocar. Pero cualquier script
  inyectado lo lee y se lo lleva, y exige habilitar CORS.
- **Dominio propio, con el dashboard y la API en dos subdominios suyos:** conserva el Static
  Site y la cookie funciona. Es el camino para cuando haya usuarios reales, pero hoy es un costo
  y una administración más sin nadie a quien proteger.
- **Un proveedor de identidad gestionado:** ninguno ofrece de forma nativa el código por
  WhatsApp. Suma un costo y un tercero más con datos personales.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
