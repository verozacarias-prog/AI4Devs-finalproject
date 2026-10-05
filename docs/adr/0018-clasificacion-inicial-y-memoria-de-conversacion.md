# 0018 — Una llamada inicial que clasifica el mensaje, y memoria de conversación leída de las tablas de mensajes

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

El worker recibe cualquier mensaje: un gasto, una pregunta sobre los propios datos o un pedido de
consejo. Cada uno sigue un camino distinto y gasta una cuota distinta: registro, consultas o
consejos. Las cuotas están separadas para que hacer muchas preguntas no bloquee el registro.

La especificación decía que la cuota se consulta antes de llamar al LLM. Eso no se puede cumplir:
sin interpretar el mensaje no se sabe a cuál de las tres cuotas pertenece. Tampoco decía cuánta
conversación ve el modelo. Dos reglas ya escritas la necesitan: corregir el alcance de una
consulta con una respuesta corta, y reconocer que el usuario insiste sobre una pregunta de
decisión. Todo lo que se le envía al proveedor está limitado por el
[ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md).

Los mensajes ya se guardan, por otros motivos, en `INBOUND_MESSAGE` y `OUTBOUND_MESSAGE`
([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md)).

## Decisión

1. **Una sola llamada inicial clasifica el mensaje** en una de tres **clases de mensaje**:
   registro, consulta o consejo. La salida es estructurada y el adaptador la valida.
2. **Esa misma llamada adelanta el trabajo de la clase.** Si es un registro, devuelve qué se
   quiere registrar y sus campos. Si es una consulta, devuelve los primeros pedidos a las
   funciones de solo lectura, así que una consulta se resuelve en dos llamadas y no en tres: la
   segunda redacta con los datos ya leídos. Si es un consejo, devuelve solo la clase y, cuando se
   reconoce, el tema.
3. **Antes de clasificar hay un tope diario total por usuario.** Cuenta las llamadas de
   clasificación del día, en un contador propio de `LLM_USAGE`, y no descuenta de ninguna de las
   tres cuotas. Vale 100 por día, y es configuración. Un mensaje que llega con el tope alcanzado
   no se clasifica: se guarda y se procesa al día siguiente, y el usuario recibe un solo aviso
   por día.
4. **La cuota de la clase se cobra después de clasificar.** Si está agotada, sale un texto fijo
   sin otra llamada al modelo. Un registro se demora hasta el día siguiente, porque un gasto
   escrito no se pierde. En una consulta o un consejo se descarta lo que la llamada inicial pidió.
5. **Un mensaje demorado no traba a los siguientes.** El que espera al día siguiente, por la
   cuota de registro o por el tope total, deja pasar los mensajes posteriores del mismo
   remitente, igual que uno fallido. Los demorados conservan el orden entre ellos.
6. **Lo que no encaja en ninguna clase** recibe un texto fijo que pide una aclaración, y no cobra
   ninguna cuota. Lo acota el tope total.
7. **Las clases de respuesta se resuelven después.** Información, educación y decisión son
   clases de respuesta de un consejo, y se deciden dentro de esa rama, no en la llamada inicial.
8. **Una clase sin código detrás responde un texto fijo.** El paso de clasificación existe desde
   el inicio con las tres clases. Lo que todavía no está construido contesta que no se puede
   hacer, sin cobrar cuota.
9. **Memoria de conversación, según la tarea.** Un intercambio es un mensaje del usuario y la
   respuesta de Platita.
   - **Registro:** sin historial. El contexto es el estado del pendiente abierto.
   - **Clasificación:** solo el último intercambio.
   - **Consulta y consejo:** los últimos 3 intercambios dentro de los últimos 30 minutos. Los dos
     valores son configuración.
10. **El historial se lee de las tablas de mensajes.** No hay un almacén aparte, ni resumen, ni
    compresión. Lo que la retención borra deja de estar en el historial.
11. **Cada respuesta guarda qué tipo de respuesta fue,** dentro de su contenido. Con eso, el
    código y no el modelo aplica la regla de insistencia: si en el historial reciente ya hay una
    explicación del límite, la respuesta siguiente es el texto fijo.

## Consecuencias

### Positivas

- Registrar un gasto cuesta una sola llamada, y una consulta, dos.
- La regla de las cuotas pasa a ser implementable: primero se sabe la clase, después se cobra.
- El costo de clasificar está acotado por usuario y por día, aunque las tres cuotas estén
  agotadas.
- El historial no se duplica. Vive en tablas que ya se purgan a los 60 días y con el borrado de
  la cuenta.
- La secuencia de la insistencia, primero la explicación y después el texto fijo, se puede
  probar sin un modelo real.

### Negativas y costos asumidos

- Cada mensaje carga la descripción de las funciones de lectura, también cuando resulta ser un
  gasto, que es lo más frecuente. Son más tokens de entrada por mensaje.
- Una llamada que clasifica, extrae y pide datos puede clasificar peor que una que solo
  clasifica. Lo mide la evaluación de proveedores ([ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md)).
  Si baja la calidad, se separan.
- Clasificar un mensaje cuya cuota resulta agotada es una llamada sin resultado, y un registro
  demorado se clasifica dos veces.
- Los mensajes de un remitente dejan de procesarse en orden estricto cuando uno queda demorado.
- La memoria depende de una ventana de tiempo. Una repregunta que llega pasados los 30 minutos
  se procesa sin contexto, y el conteo de la insistencia se reinicia: el usuario recibe otra vez
  la explicación en vez del texto fijo. Nunca recibe un veredicto.
- Que un mensaje es una insistencia lo sigue detectando el modelo. El código garantiza la
  secuencia, no la detección.
- El historial enviado contiene respuestas anteriores, con cifras del usuario.

## Alternativas descartadas

- **Clasificar en una llamada e interpretar en otra:** cada tarea queda más simple, pero
  registrar un gasto, que es el caso más frecuente, cuesta el doble.
- **Clasificar con reglas o palabras clave, sin modelo:** no cuesta nada, pero el lenguaje
  coloquial lo rompe. "Me quedé sin un mango, ¿cuánto llevo?" no tiene ninguna palabra fija.
- **Una sola cuota para todo:** evita clasificar antes de cobrar, pero muchas preguntas dejarían
  al usuario sin poder registrar.
- **Contar el tope total sobre los mensajes recibidos, sin un contador propio:** no acota el
  costo. Los registros que se demoran por su cuota ya fueron clasificados y pasan al día
  siguiente sin contarse.
- **Enviar el historial completo o un resumen:** el modelo tendría más contexto, pero salen más
  datos de los que la tarea necesita y cada mensaje cuesta más.
- **La memoria de un framework:** guarda una segunda copia de los mensajes, que también habría
  que purgar ([ADR 0020](0020-sin-framework-de-orquestacion-de-ia.md)).
- **Buscar la última respuesta de consejo sin límite de tiempo, para la insistencia:** una
  insistencia de hoy recibiría el texto fijo por una explicación vieja sobre otro tema.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
