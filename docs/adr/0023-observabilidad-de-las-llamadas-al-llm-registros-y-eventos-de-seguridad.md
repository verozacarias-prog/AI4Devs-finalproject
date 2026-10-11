# 0023 — Una fila por llamada al LLM, registros en JSON y eventos de seguridad en el mismo registro

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

Platita depende de un modelo de lenguaje para su función central, y hoy no hay forma de saber
cuánto tarda, cuánto cuesta, cuántas veces responde algo que no sirve ni cuántas respuestas
frena la validación. `LLM_USAGE` cuenta mensajes y tokens por usuario y por día para aplicar las
cuotas ([ADR 0018](0018-clasificacion-inicial-y-memoria-de-conversacion.md)); no dice nada de
una llamada en particular.

Tampoco está definido qué eventos de seguridad se registran. La
[hoja de ruta](../hoja-de-ruta.md#decisiones-abiertas) lo tenía como decisión abierta: sin ese
registro, una fuerza bruta sobre los códigos o un abuso del modelo pasan sin que nadie se
entere.

Lo que ya está decidido acota la solución:

- Nada personal va a un registro, y a un tercero se le envía lo mínimo
  ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md)).
- El dominio no conoce infraestructura, y los casos de uso hablan solo con puertos
  ([ADR 0001](0001-arquitectura-hexagonal.md)).
- La llamada al modelo ocurre fuera de toda transacción, y la transacción final del worker se
  deshace entera si otro worker tomó el mensaje
  ([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md)).
- Los consejos con la base de conocimiento son parte del producto y llegan en la entrega final.
  Lo que se construya antes no puede obligar a rediseñar para sumarlos
  ([ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md)).

## Decisión

### Llamadas al modelo

1. **Una tabla `LLM_CALL` con una fila por llamada, sin ningún contenido.** Guarda el mensaje
   que la originó, el propósito (clasificar, interpretar, consulta, consejo o embedding), el
   proveedor, el modelo, la versión del prompt, los tokens de entrada y de salida, la duración,
   el costo estimado y el resultado: bien, salida inválida, bloqueada por la validación, error
   del proveedor o tiempo agotado. Nunca texto, montos ni nombres. Las columnas están en el
   [modelo de datos](../03-modelo-de-datos.md#llm_call).
2. **Un campo reservado para la recuperación.** Guarda qué fragmentos de la base de conocimiento
   se trajeron y con qué similitud. Queda vacío hasta que existan los consejos. Para llenarlo,
   los fragmentos llegan al puerto del LLM con su identificador y su similitud.
3. **La captura la hace un envoltorio.** Implementa el mismo puerto que el adaptador real y lo
   envuelve. Hay uno para el puerto del LLM y otro para el de embeddings. Los puntos de entrada
   inyectan siempre el envoltorio, así que ninguna llamada lo saltea, y un test lo comprueba.
   El propósito sale del método del puerto que se llamó, no de un parámetro.
4. **El envoltorio escribe por un puerto propio.** No importa ninguna librería de base de
   datos: usa un puerto de registro de llamadas, que implementa el adaptador de PostgreSQL.
5. **La fila se guarda en su propia transacción corta,** fuera de la transacción final del
   worker. Si esa se deshace por el fencing del ADR 0010, la llamada igual costó y tiene que
   quedar.
6. **El resultado de cada llamada trae la referencia de su fila.** Es parte del resultado del
   puerto desde el diseño. Cuando la validación de salida rechaza una respuesta, el caso de uso
   pasa esa referencia al puerto de registro, que marca la fila como bloqueada, también en una
   transacción corta.
7. **El mensaje sale del contexto del proceso.** El punto de entrada fija el identificador del
   mensaje que está procesando, y el envoltorio lo lee de ahí. Una llamada que no nace de un
   mensaje, como la carga de la base de conocimiento, queda sin mensaje.
8. **El costo se guarda ya calculado,** en dólares, con los precios por modelo que están en la
   configuración. Un cambio de precio no reescribe las filas viejas.
9. **Retención.** Las filas no se borran por plazo, porque no tienen contenido. Cuando se borra
   una cuenta, sus filas pierden el vínculo con el mensaje y conservan el resto.
10. **Un contador de correcciones en el pendiente.** `PENDING_TRANSACTION` cuenta cuántos campos
    interpretados por el modelo cambió el usuario antes de confirmar. Qué cuenta como corrección
    está en las [reglas de dominio § 5](../reglas-de-dominio.md#5-pending_transaction-creación-continuación-de-la-conversación-promoción-y-expiración).
11. **Las métricas salen de consultas SQL en un script del repositorio,** no de código de la
    aplicación. Son cuatro:
    - latencia, por propósito;
    - costo, por día y por propósito;
    - calidad: el porcentaje de registros confirmados sin correcciones, y el de salidas con
      formato inválido;
    - alucinaciones: el porcentaje de respuestas bloqueadas por la validación.

    Con los consejos se suma el porcentaje de respuestas sin ningún fragmento por encima de un
    umbral de similitud. Ese umbral es un parámetro de la métrica: no cambia qué fragmentos se
    recuperan. Más adelante, las mismas consultas alimentan el resumen diario de
    [Operación](../operacion.md#62-métricas).
12. **Sin plataforma externa de observabilidad de LLM.** Recibiría los prompts y las
    respuestas, que es lo que el ADR 0013 no deja salir.

### Registros y eventos de seguridad

1. **Registros en JSON,** de una línea, a la salida estándar. Cada línea lleva el identificador
   del mensaje, que lo sigue desde que entra hasta la respuesta. Es el `id` de
   `INBOUND_MESSAGE`, el mismo que guarda `LLM_CALL`, así que no hace falta ninguna columna
   nueva. Un pedido a la API que no es un mensaje lleva un identificador que se genera al
   recibirlo.
2. **Un filtro quita los datos personales,** y un test lo prueba: registra un gasto de ejemplo y
   falla si algún registro contiene el teléfono, el monto o el texto. El mismo filtro quita las
   credenciales: códigos, cookies, tokens de sesión y el valor de un enlace personal del entorno
   de pruebas, y el test también entra con un enlace y falla si su valor aparece.
3. **Los eventos de seguridad son eventos de ese mismo registro,** sin tabla ni herramienta
   nueva: código de acceso pedido y fallido, sesión creada, límite de intentos alcanzado, cuota
   o tope diario superado, y respuesta bloqueada por la validación. El teléfono va como el mismo
   HMAC que usa `AUTH_THROTTLE` ([ADR 0017](0017-limites-del-login-y-codigos-con-proposito.md)),
   nunca el número.
4. **Cada evento llega con la funcionalidad que lo produce.** Los del código de acceso y el
   límite de intentos, con el login por código. Los propios de WhatsApp, como una firma
   inválida, con ese adaptador.
5. **Un aviso al arrancar** si el chat web o la entrada de desarrollo están encendidos
   ([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md)).
6. **Tres rutas de salud:** una dice si el proceso vive, otra si llega a la base, y la tercera
   falla cuando hay un mensaje esperando hace más de 10 minutos. El contrato está en
   [la API](../04-api.md#get-healthz-get-readyz-y-get-queuez).

### Con el primer despliegue

1. **Sentry, en su plan gratuito, para los errores,** con el filtro de datos personales. Pasa a
   ser un proveedor más en [términos y privacidad](../terminos-y-privacidad.md).
2. **Un monitor externo** sobre las rutas de salud.
3. **Dos alertas, las críticas:** servicio caído y mensajes sin procesar. Las dos las da ese
   monitor: la primera mira si la API llega a la base, y la segunda, la ruta de la cola. Las
   otras cinco de [Operación](../operacion.md#64-alertas) esperan a que haya usuarios reales.

## Consecuencias

### Positivas

- Latencia, costo, calidad y respuestas bloqueadas se miden desde el primer mensaje, con datos
  que ya están en la base.
- Una llamada cuyo trabajo se descartó por el fencing queda registrada con su costo.
- Los casos de uso no saben que se los mide: el envoltorio se puede quitar o cambiar sin
  tocarlos.
- Sumar los consejos no cambia la tabla: el campo de la recuperación ya está.
- Los eventos de seguridad no exigen nada nuevo que operar.
- El worker colgado se detecta sin sumar un proveedor, con el mismo monitor que mira la API.

### Negativas y costos asumidos

- Una escritura más por cada llamada al modelo, en su propia transacción.
- Si el proceso muere entre la respuesta del proveedor y esa escritura, la llamada no queda
  registrada. El costo real sigue siendo el de la factura del proveedor.
- El costo es una estimación: depende de que los precios de la configuración estén al día.
- El identificador del mensaje viaja por el contexto del proceso y no como parámetro. Es menos
  visible al leer el código, y lo cubre el test del envoltorio.
- Los eventos de seguridad duran lo que el proveedor de alojamiento retenga los registros. Para
  investigar algo viejo puede no alcanzar.
- Quedan sin definir, y siguen en la hoja de ruta, los eventos de exportación, de pedido de
  borrado y de cambio de miembros, y qué evento dispara una alerta.
- La ruta de la cola no avisa si lo que se cayó es la API entera; eso lo cubre la otra alerta.
- La tabla crece sin límite. Con este volumen no pesa, y se revisa junto con los metadatos de
  los mensajes.

## Alternativas descartadas

- **Una plataforma externa de observabilidad de LLM:** trae los tableros hechos, pero recibe
  cada prompt y cada respuesta.
- **Medir dentro de cada caso de uso:** no hace falta el envoltorio, pero el dominio pasa a
  ocuparse de la medición, y una llamada nueva puede olvidarse de registrar.
- **Guardar la fila en la transacción final del worker:** una escritura menos, pero una
  transacción deshecha borraría el registro de una llamada que sí se pagó.
- **Derivar todo de `LLM_USAGE`:** ya tiene los tokens, pero por usuario y por día. No tiene
  duración, ni resultado, ni modelo.
- **Calcular el costo al consultar,** con los precios vigentes: un cambio de precio cambiaría el
  costo de los meses anteriores.
- **Borrar las filas a los 60 días, como el texto de los mensajes:** se perdería el historial de
  costo, sin ganar privacidad, porque no guardan contenido.
- **Una tabla para los eventos de seguridad:** se podrían consultar con SQL y conservar más
  tiempo, a cambio de otra tabla con su retención y su redacción. Se revisa si los registros
  no alcanzan.
- **Un servicio de avisos por ausencia para el worker,** como proponía Operación: detecta lo
  mismo, a cambio de un proveedor más y de una dirección secreta que configurar.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
