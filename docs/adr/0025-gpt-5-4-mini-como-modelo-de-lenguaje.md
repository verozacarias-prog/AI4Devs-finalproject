# 0025 — GPT-5.4 mini, de OpenAI, como modelo de lenguaje

- Estado: Aceptada
- Fecha: 2026-10-11

## Contexto

Platita necesita un modelo de lenguaje para clasificar cada mensaje, extraer los campos de un
movimiento, pedir datos a las funciones de solo lectura y redactar consultas y consejos
([ADR 0018](0018-clasificacion-inicial-y-memoria-de-conversacion.md)). El
[ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md) dejó la elección
para una evaluación, antes de escribir el código de la entrega 2, y el
[ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md) puso los criterios de privacidad: es
obligatorio que el proveedor no entrene con lo que recibe por la API, y cuánto retiene el
contenido se pesa con la calidad y el costo, con un máximo de 30 días.

La cuenta del proveedor tiene un tope de 20 dólares por mes
([2.4](../02-arquitectura.md#24-infraestructura-y-despliegue)), y el modelo se usa en cada
mensaje. Alcanza un modelo chico: la tarea es interpretar un mensaje corto, no razonar largo.

## Decisión

1. **El modelo de lenguaje es GPT-5.4 mini, de OpenAI,** con el identificador `gpt-5.4-mini`.
   Se usa con el SDK directo del proveedor
   ([ADR 0020](0020-sin-framework-de-orquestacion-de-ia.md)), con salida estructurada para la
   clasificación y el registro, y con esfuerzo de razonamiento bajo, que es como se lo evaluó.
   Cómo se piden las funciones de solo lectura, si con salida estructurada o con llamadas a
   herramientas, se decide al escribir el adaptador.
2. **Cumple los criterios de privacidad, en el máximo de retención que admiten.** Según la
   [documentación del proveedor](https://developers.openai.com/api/docs/guides/your-data),
   verificada el 2026-10-11: no entrena con los datos de la API salvo que la cuenta opte por
   compartirlos, y guarda registros para el control de abuso, que pueden incluir los pedidos y
   las respuestas, hasta 30 días. Ofrece retención cero a las organizaciones que califican;
   Platita no la pidió. La autora aceptó esos 30 días a cambio de la calidad de las respuestas,
   sabiendo que la alternativa retiene menos. Estas condiciones se vuelven a revisar si el
   proveedor cambia sus términos.
3. **Se eligió con una evaluación.** Tres candidatos, 30 casos y tres corridas:
   - Los candidatos fueron GPT-5.4 mini y GPT-5.4 nano, de OpenAI, y Claude Haiku 5.5, de
     Anthropic.
   - Los casos son 20 de la [validación por casos de uso](../use-case-walkthrough.md), 2 que
     responden con fragmentos de una base de conocimiento y 7 de inyección de prompts, entre
     ellos los dos que pide el ADR 0013: una descripción de movimiento con una orden adentro, y
     un fragmento con otra. El último es un control: los datos del caso de la descripción, sin
     la orden. El resultado esperado de cada uno lo aprobó la autora antes de correr.
   - Los casos y el programa que los corre están en
     [`scripts/llm_eval/`](../../scripts/llm_eval/run_eval.py).

   | | GPT-5.4 mini | Claude Haiku 5.5 | GPT-5.4 nano |
   |---|---|---|---|
   | Primeros 27 casos bien, en cada corrida | 25, 26, 26 | 25, 25, 25 | 20, 19, 23 |
   | Registros bien en una llamada, de 14 | 14, 14, 14 | 13, 13, 13 | 11, 11, 13 |
   | Registros bien en dos llamadas, de 14 | 13, 14, 14 | 13, 13, 13 | 11, 10, 11 |
   | Los dos casos con la orden en los datos, bien | 2, 2, 2 | 1, 1, 1 | 1, 1, 1 |
   | Latencia mediana por llamada | 1,2 s | 1,8 s | 1,3 s |
   | Tokens de entrada de los 27 casos | 52.017 | 119.476 | 52.017 |
   | Costo de los 27 casos, en dólares | 0,075 | 0,016 | 0,019 |
   | Precio por millón de tokens, entrada y salida | 0,75 y 4,50 | 0,10 y 0,50 | 0,20 y 1,25 |

   Los precios son los de la [página de OpenAI](https://developers.openai.com/api/docs/pricing)
   y la de [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing), al 2026-10-11.
   En una corrida el control automático marcó mal una respuesta correcta de mini, que escribió
   "34,0%"; la tabla lleva el valor corregido a mano, y el control ya lo acepta. Haiku usó más
   del doble de tokens de entrada para los mismos pedidos; no se investigó por qué, y el costo
   de la tabla ya lo incluye. En los dos casos con la orden en los datos, nano no obedeció: el
   que cuenta mal es por clasificar una pregunta de consejo como consulta.
4. **Ningún modelo obedeció una orden escondida.** Ni en el mensaje, ni en el nombre de una
   categoría, ni en la descripción de un movimiento, ni en un fragmento de la base de
   conocimiento. Ninguno dio un veredicto ni mostró el prompt de sistema.
5. **Mini se eligió por cómo usa las funciones y los datos, aunque cuesta más.** En los primeros
   27 casos mini y Haiku quedan parejos. La diferencia está en los fallos que se repiten en las
   tres corridas:
   - Haiku no pidió la función Indicadores ante "¿cuánto paga hoy un plazo fijo?", y cuando un
     movimiento traía una orden en su descripción no la obedeció, pero tampoco respondió: volvió
     a pedir los mismos datos. En el control, con los mismos datos sin la orden, los tres
     modelos respondieron bien las tres veces.
   - Haiku puso "Otros ingresos" en vez de "Ventas" a una vianda cobrada, que es un valor que
     el usuario ve y corrige en la confirmación.
   - Mini, ante el pedido de los gastos de otro teléfono, pasó ese número como filtro de una
     función, en la llamada inicial o en la de la respuesta. No expone datos, porque las
     funciones filtran por el usuario en el código (ADR 0013, punto 6). Además sus respuestas
     fueron flojas: ninguna dijo que solo ve los datos propios, una invitó a "conectar la
     cuenta", que Platita no hace, y otra pidió el nombre de la persona. Haiku respondió bien
     ese caso las tres veces. Es el único fallo de mini que se repite.
6. **GPT-5.4 nano queda descartado por romper invariantes.** En las tres corridas eligió una
   cuenta cuando el mensaje coincidía con dos, y no reconoció la insistencia de quien pide que
   decidan por él. Además sumó mal tres gastos en dos de tres corridas.
7. **Clasificar y extraer en una sola llamada no baja la calidad.** Los dos mejores registran
   igual en una llamada que en dos. Se mantiene la llamada inicial única del ADR 0018.
8. **Las cuentas y el español.** Mini calculó bien la proporción y la suma de los casos que las
   piden; en una de tres corridas dio el porcentaje de una cuota sin el total a pagar. Los
   mensajes usan voseo y vocabulario local, como "nafta", "vianda" o "el super", ningún modelo
   falló por eso, y las respuestas salen en voseo.
9. **Lo que mini falló queda como caso de prueba del prompt del producto:** el filtro con el
   teléfono ajeno, la respuesta a ese pedido y el total que omite.
10. **El proveedor de embeddings se elige después.** Sigue el ADR 0019: una evaluación aparte,
    antes de la rama de consejos. OpenAI ofrece embeddings, así que puede ser el mismo
    proveedor, pero no queda decidido acá.

## Consecuencias

### Positivas

- Si la evaluación de embeddings también elige a OpenAI, los consejos dependen de una sola
  empresa: una cuenta, una clave, un contrato de privacidad.
- Es el modelo más rápido de los tres, y el que respondió bien con datos contaminados.
- La evaluación se puede volver a correr tal cual ante un modelo nuevo o un cambio de precios.

### Negativas y costos asumidos

- Cuesta casi cinco veces más que la alternativa: con el tope de 20 dólares por mes entran del
  orden de 17.000 llamadas, a unos 0,0012 dólares cada una en la evaluación, contra unas 80.000.
- El proveedor guarda los pedidos y las respuestas hasta 30 días para el control de abuso, que
  es el máximo que admite el ADR 0013. La alternativa descartada no retiene el contenido por
  defecto. Los mensajes viajan sin
  identificadores (ADR 0013), pero el texto que el usuario escribe queda ese tiempo.
- La evaluación es chica: 30 casos y tres corridas. Alcanza para descartar a nano, no para
  afirmar que mini es mejor que Haiku en todo.
- Las respuestas en prosa, de consejos e inyección, las revisó el asistente en una sola
  corrida; el control automático solo busca frases. La autora no las leyó una por una.
- Los pedidos a las funciones de solo lectura se midieron con salida estructurada, no con
  llamadas a herramientas reales, para usar el mismo programa con los dos proveedores.
- El modelo puede negarse a responder, o el proveedor puede cortar una respuesta. El adaptador
  tiene que mirar el motivo de corte. Qué recibe el usuario en ese caso todavía no está definido.
- El prompt de la evaluación es un borrador. El del producto se escribe con sus propios tests.
- Quien propuso los candidatos y corrió la evaluación es un asistente de Anthropic. Los casos,
  los resultados esperados y la elección los aprobó la autora.

## Alternativas descartadas

- **Claude Haiku 5.5, de Anthropic:** casi cinco veces más barato y sin retención del contenido
  por defecto. Su
  [documentación](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
  dice: "Conversation content (your prompts and Claude's outputs) is not retained by default".
  La excepción son los modelos que exigen 30 días, y Haiku 5.5 no está entre ellos. Se
  descartó por los fallos del punto 5, que tocan justo el uso de las funciones. Anthropic no
  ofrece embeddings propios, así que los consejos habrían necesitado un segundo proveedor. Si
  el costo aprieta, es el primer candidato para repetir la evaluación con el prompt real.
- **GPT-5.4 nano:** el más barato de OpenAI. Descartado por lo que dice el punto 6.
- **Un modelo más grande:** no se evaluó. Los modelos chicos ya resuelven los casos, y uno
  grande multiplica el costo de cada mensaje.
- **Un intermediario que ofrece varios modelos con una sola clave:** suma una empresa más que
  recibe los mensajes, y el ADR 0020 pide el SDK directo del proveedor.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
