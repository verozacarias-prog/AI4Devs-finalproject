# 0028 — El modelo interpreta, el código controla las invariantes

- Estado: Aceptada
- Fecha: 2026-10-17

## Contexto

Registrar un movimiento conversando es, en buena parte, entender lo que la persona escribe: "con
MP", "fueron 12 lucas", "la de pesos", "sí, creala", "fue ayer". El corte 2 de
[FEAT-003](../features/FEAT-003/spec.md) sumó la continuación de un pendiente, y con ella
apareció una pregunta tras otra de la forma "¿qué pasa si el usuario contesta X?": una moneda sin
cuenta, una fecha que cambia, un sí que llega con otra fecha.

Cada respuesta se puede resolver con una regla de código particular: cómo combinar lo que dijo
con lo que ya se sabía, qué cuenta como corrección, qué alcanza para elegir una cuenta. Pero las
formas de contestar no se terminan. El código crece con cada caso, y cada regla nueva es un lugar
más donde equivocarse.

Al mismo tiempo, hay reglas que no pueden depender de que el modelo acierte, porque romperlas
rompe los datos del usuario y no se nota leyendo la respuesta. Son las invariantes de
[AGENTS.md § 5](../../AGENTS.md#5-invariantes-que-un-asistente-rompe-por-defecto). El modelo se
puede equivocar, y un mensaje armado puede manipularlo
([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md); LLM01 y LLM06 en
[seguridad-llm.md](../seguridad-llm.md)).

## Decisión

1. **Entender el lenguaje es del modelo.** Qué pide un mensaje, qué datos trae, si contesta un
   pendiente, qué cambió de lo que ya se sabía, si acepta lo que se le ofreció. El código no
   interpreta frases. Si una forma de contestar se entiende mal, se corrige en el prompt o en
   la salida estructurada que el modelo devuelve, no con una regla de código para esa forma.
2. **El código controla las invariantes y valida la salida del modelo.** Solo esto lleva reglas de
   código, con sus casos de prueba:
   - Una cuenta se usa solo si el mensaje la escribe y nombra una sola, y nunca por defecto
     ([reglas de dominio § 1](../reglas-de-dominio.md#1-registro-de-un-movimiento-qué-se-asume-y-qué-se-confirma)).
   - Un movimiento se imputa a un período solo si es el único posible y está confirmado, o si el
     usuario confirmó el que se le mostró (§ 1 y § 3).
   - Una categoría nueva se crea solo con un sí a la que se le ofreció (§ 4).
   - Los montos viajan en `Decimal` y con su moneda.
   - Todo texto del modelo que llega al usuario o a la base se valida antes
     ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md), punto 10).
3. **El código aplica lo que el modelo devuelve, sin reinterpretarlo.** Combina los datos de una
   respuesta con los del pendiente de la forma más simple posible, campo por campo, y después
   corre los mismos controles que para un mensaje nuevo.
4. **Antes de proponer un caso de prueba para una respuesta del usuario, se clasifica.** Si es
   interpretación, va al modelo y, como mucho, al prompt. Si es una invariante, va al código, con
   su caso.

## Consecuencias

### Positivas

- El código del registro queda acotado a un conjunto de controles que no crece con cada forma de
  contestar.
- Las garantías que importan no dependen de que el modelo acierte: un modelo equivocado o
  manipulado puede entender mal, pero no puede registrar en una cuenta que el mensaje no escribe,
  ni imputar a un período sin confirmar, ni crear una categoría sin un sí.
- Una interpretación que falla se arregla en un solo lugar, el prompt, y se mide con las métricas
  de calidad del [ADR 0023](0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md).

### Negativas y costos asumidos

- Una respuesta ambigua puede quedar mal entendida hasta que se ajuste el prompt. Lo acotan los
  controles del código, y la confirmación, que muestra lo que se registró.
- Lo que el modelo decide no lo prueba ningún test, porque ningún test llama al proveedor: se
  prueba a mano, con el modelo real, y con las métricas.
- Algunas medidas quedan algo ruidosas mientras el modelo no las devuelva él. Por ejemplo, el
  contador de correcciones cuenta cualquier dato que cambia, también una fecha que se había
  asumido.

## Alternativas descartadas

- **Una regla de código por cada forma de contestar:** el comportamiento es explícito y se
  prueba, pero el código crece sin límite y cada regla es un error posible.
- **Dejar todo en el modelo, también las invariantes:** el código sería mínimo, pero una cuenta o
  un período mal elegidos rompen el saldo y el presupuesto sin que se note, y un mensaje armado
  podría provocarlo.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
