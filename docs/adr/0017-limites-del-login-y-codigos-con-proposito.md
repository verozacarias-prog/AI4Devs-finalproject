# 0017 — Límites del login que no dependen de que el número exista, y códigos atados a su propósito

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

El dashboard se abre con un código de un solo uso que llega por WhatsApp y se canjea por una
sesión ([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md)). El mismo tipo de código
confirma el borrado de una cuenta. Un modelo de amenazas del diseño encontró tres problemas en
cómo estaba especificado.

**Los límites delatan quién usa Platita.** Pedir un código responde siempre lo mismo, exista o
no un usuario con ese número, justamente para no revelarlo. Pero el límite de 3 pedidos cada 15
minutos se calculaba contando los códigos recientes del usuario, y un número que no es de nadie
no tiene códigos. Pasado el límite, un número registrado responde `429` y uno no registrado
sigue respondiendo `202`. Con cuatro pedidos se sabe si un número usa una aplicación de
finanzas personales.

**Los límites no frenan una fuerza bruta paciente.** Cada código admite 5 intentos, y se pueden
pedir 3 códigos cada 15 minutos. Son 15 intentos cada 15 minutos, unos 1.440 por día sobre un
código de 6 dígitos: cerca de un 4 % de probabilidad de entrar en un mes contra una sola
víctima, sin ningún límite por origen. Además, si varias requests llegan a la vez, cada una
puede comparar el código antes de que se cuenten los intentos de las otras. Y el hash del código
no protege una tabla filtrada: con un millón de valores posibles, se recorre entero en segundos.

**Un código sirve para cualquier cosa.** Un código pedido para entrar al dashboard también
confirma el borrado de la cuenta, y el mensaje que lo trae no dice para qué es. La
especificación justificaba el código de borrado diciendo que evita que alguien borre la cuenta
de otro con acceso a su teléfono. Pero el código llega a ese mismo teléfono: a quien lo tiene en
la mano, no lo frena.

## Decisión

1. **Los límites se cuentan por número y por origen, exista o no el usuario.** Cada pedido de
   código y cada canje fallido se registran en una tabla `auth_throttle`, que no depende de que
   el usuario exista. La clave es un HMAC-SHA256 del teléfono, normalizado a E.164, o de la IP
   de origen, con una clave del servidor en una variable de entorno. Así la tabla no guarda
   teléfonos ni IPs en claro. Un número registrado y uno que no lo es llegan al mismo `429` con
   la misma cantidad de pedidos.
2. **Límites.** Pedir un código: 3 por número cada 15 minutos, y 20 por IP por hora. Canjear:
   10 fallos por número por día, y 50 por IP por día. Superado un límite de canje, la API
   responde `429` sin mirar el código. Con 10 intentos por día, la probabilidad de adivinar el
   código de una víctima en un mes baja del 4 % a alrededor del 0,03 %. Las filas se borran a
   las 24 horas.
3. **El intento se cuenta antes de comparar.** El canje incrementa los intentos del código en la
   misma sentencia que verifica que siga vigente y por debajo de 5, y compara recién si esa
   sentencia devolvió una fila. Dos requests simultáneas no pueden sumar más intentos de los
   permitidos.
4. **El código se guarda como HMAC** con la misma clave del servidor, en vez de como un hash
   simple. Sin la clave, una copia filtrada de la tabla no permite recorrer los valores posibles.
5. **Cada código tiene un propósito**, `login` o `account_deletion`, y solo sirve para eso. El
   mensaje de WhatsApp dice cuál es, con una plantilla distinta para cada uno. Un código de
   borrado que llega sin haberlo pedido es una señal que el usuario puede reconocer.
6. **Qué protege el código de borrado, dicho con precisión.** Desde el dashboard, exige tener el
   teléfono además de la sesión: quien tenga solo una sesión, por una computadora que quedó
   abierta, no puede borrar la cuenta. Por WhatsApp, el código llega al mismo chat y no agrega
   seguridad. Ahí sirve como confirmación que no sale de interpretar un mensaje: el borrado
   exige escribir el código tal cual, así que ninguna frase mal interpretada lo dispara. Contra
   quien tiene el teléfono en la mano, la única defensa es el plazo de gracia.

## Consecuencias

### Positivas

- Pedir códigos ya no revela si un número usa Platita.
- Adivinar un código deja de ser una estrategia práctica, incluso con paciencia.
- Una filtración de la base no expone ni teléfonos en los límites ni códigos vigentes.
- Rotar la clave del servidor cuesta poco: invalida códigos que vencen en 5 minutos y límites
  que se borran a las 24 horas.
- La especificación deja de prometer una protección que el diseño no da.

### Negativas y costos asumidos

- Una tabla más, que se escribe en cada pedido y en cada fallo, y un proceso programado que la
  purga.
- En Argentina muchas conexiones móviles comparten IP. El límite por IP es holgado para no
  bloquear a usuarios legítimos, pero una red grande podría llegar a él.
- La IP real la informa el proxy de Render en un header, y hay que tomarla solo de ahí. Si se
  toma del header que manda el cliente, cualquiera la falsifica y el límite por IP no sirve.
- Pedir un código sigue tardando un poco más si el usuario existe, porque solo entonces se crea
  el código y se encola el mensaje. La diferencia es de milisegundos, dentro del ruido de la red.
  Se acepta.
- Una plantilla más para aprobar en Meta: el código de borrado.
- Si alguien fuerza los 10 fallos diarios de un número, su dueño no puede entrar al dashboard
  hasta el día siguiente. Por WhatsApp sigue funcionando todo.
- Contra quien tiene el teléfono, el borrado sigue sin protección más allá del plazo de gracia.
  Resolverlo exige un segundo factor que no dependa del teléfono, y eso es otra decisión.

## Alternativas descartadas

- **Contar los códigos del usuario, como estaba:** no necesita tabla, pero delata a los
  usuarios registrados.
- **Responder `202` siempre, incluso pasado el límite:** no delata a nadie, pero un usuario
  legítimo que pide de más no sabe por qué no le llega el código.
- **Límites en memoria del proceso:** no necesitan tabla, pero se pierden en cada despliegue y
  no se comparten si la API corre en más de una instancia.
- **Un captcha en el formulario de login:** frena la automatización, pero suma un tercero y
  fricción para todos, cuando los límites alcanzan a este volumen. Queda como respuesta si
  aparece abuso.
- **Un código más largo:** reduce la probabilidad de adivinar, pero es más incómodo de tipear, y
  el límite diario logra el mismo efecto.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
