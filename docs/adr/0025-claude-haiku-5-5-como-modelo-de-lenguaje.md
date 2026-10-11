# 0025 — Claude Haiku 5.5, de Anthropic, como modelo de lenguaje

- Estado: Aceptada
- Fecha: 2026-10-11

## Contexto

Platita necesita un modelo de lenguaje para clasificar cada mensaje, extraer los campos de un
movimiento, pedir datos a las funciones de solo lectura y redactar consultas y consejos
([ADR 0018](0018-clasificacion-inicial-y-memoria-de-conversacion.md)). El
[ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md) dejó la elección
para una evaluación, antes de escribir el código de la entrega 2, y el
[ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md) puso un filtro obligatorio: que el
proveedor no entrene con lo que recibe por la API y lo retenga el menor tiempo posible.

La cuenta del proveedor tiene un tope de 20 dólares por mes
([2.4](../02-arquitectura.md#24-infraestructura-y-despliegue)), y el modelo se usa en cada mensaje. Alcanza un
modelo chico: la tarea es interpretar un mensaje corto, no razonar largo.

## Decisión

1. **El modelo de lenguaje es Claude Haiku 5.5, de Anthropic,** con el identificador
   `claude-haiku-5-5`. Se usa con el SDK directo del proveedor
   ([ADR 0020](0020-sin-framework-de-orquestacion-de-ia.md)), con salida estructurada y con
   esfuerzo de razonamiento bajo, que es como se lo evaluó.
2. **Pasa el filtro de privacidad.** Según la documentación del proveedor, verificada el
   2026-10-11: no entrena con los datos de la API salvo permiso expreso; por defecto no retiene
   el contenido de los pedidos ni de las respuestas para este modelo; el esquema de una salida
   estructurada queda en caché hasta 24 horas, y un esquema no lleva datos de ningún usuario; y
   lo que sus sistemas de seguridad marcan puede retenerse hasta 2 años. Estas condiciones se
   vuelven a revisar si el proveedor cambia sus términos.
3. **Se eligió con una evaluación.** Tres candidatos, 27 casos y tres corridas:
   - Los candidatos fueron Claude Haiku 5.5, GPT-5.4 mini y GPT-5.4 nano, de OpenAI.
   - Los casos son 20 de la [validación por casos de uso](../use-case-walkthrough.md), 2 que
     responden con fragmentos de una base de conocimiento y 5 de inyección de prompts. El
     resultado esperado de cada uno lo aprobó la autora antes de correr.
   - Los casos y el programa que los corre están en
     [`scripts/llm_eval/`](../../scripts/llm_eval/run_eval.py).

   | | Claude Haiku 5.5 | GPT-5.4 mini | GPT-5.4 nano |
   |---|---|---|---|
   | Casos bien, de 27, en cada corrida | 25, 25, 25 | 25, 25, 26 | 20, 19, 23 |
   | Registros bien en una llamada, de 14 | 13, 13, 13 | 14, 14, 14 | 11, 11, 13 |
   | Registros bien en dos llamadas, de 14 | 13, 13, 13 | 13, 14, 14 | 11, 10, 11 |
   | Latencia mediana por llamada | 1,8 s | 1,2 s | 1,3 s |
   | Costo de los 27 casos, en dólares | 0,016 | 0,075 | 0,019 |
   | Precio por millón de tokens, entrada y salida | 0,10 y 0,50 | 0,75 y 4,50 | 0,20 y 1,25 |

4. **Haiku y mini empatan en calidad, y decide el costo.** Haiku cuesta casi cinco veces menos
   por la misma corrida. Mini responde unos 0,6 segundos más rápido por llamada.
5. **GPT-5.4 nano queda descartado por romper invariantes.** En las tres corridas eligió una
   cuenta cuando el mensaje coincidía con dos, y no reconoció la insistencia de quien pide que
   decidan por él.
6. **Clasificar y extraer en una sola llamada no baja la calidad.** Los dos mejores registran
   igual en una llamada que en dos. Se mantiene la llamada inicial única del ADR 0018.
7. **Lo que Haiku falló queda como caso de prueba del prompt del producto.** Fueron dos casos,
   los mismos en las tres corridas:
   - a una vianda cobrada le puso la categoría "Otros ingresos" en vez de "Ventas", que es un
     valor que el usuario ve y corrige en la confirmación;
   - clasificó bien "¿cuánto paga hoy un plazo fijo?" como consulta, pero no pidió la función
     Indicadores.
8. **El proveedor de embeddings es otro, y se elige después.** Anthropic no ofrece un modelo de
   embeddings propio. La elección sigue el ADR 0019: una evaluación aparte, antes de la rama de
   consejos.

## Consecuencias

### Positivas

- Con el tope de 20 dólares por mes entran del orden de 80.000 llamadas, a unos 0,00025 dólares
  cada una en la evaluación.
- El contenido de los mensajes no queda guardado en el proveedor por defecto.
- Una caída del proveedor de embeddings no afecta el registro de gastos, y cambiar de modelo de
  lenguaje no obliga a recalcular los vectores.
- La evaluación se puede volver a correr tal cual ante un modelo nuevo o un cambio de precios.

### Negativas y costos asumidos

- Los consejos dependen de dos empresas: dos cuentas, dos claves, dos contratos de privacidad
  que verificar, y la pregunta de un consejo sale hacia las dos.
- La evaluación es chica: 27 casos y tres corridas. Alcanza para descartar a nano, no para
  afirmar que Haiku y mini son iguales en todo.
- Las respuestas en prosa, de consejos e inyección, las revisó el asistente en una sola
  corrida; el control automático solo busca frases. La autora no las leyó una por una.
- Los pedidos a las funciones de solo lectura se midieron con salida estructurada, no con
  llamadas a herramientas reales, para usar el mismo programa con los dos proveedores.
- El modelo puede negarse a responder un pedido, y no tiene un modelo de respaldo del lado del
  proveedor. El adaptador tiene que mirar el motivo de corte de cada respuesta. Qué recibe el
  usuario en ese caso todavía no está definido.
- El prompt de la evaluación es un borrador. El del producto se escribe con sus propios tests.
- Quien propuso los candidatos y corrió la evaluación es un asistente de Anthropic. Los casos,
  los resultados esperados y la elección los aprobó la autora.

## Alternativas descartadas

- **GPT-5.4 mini, con todo en OpenAI:** una sola cuenta, un solo contrato y los datos en una
  sola empresa, porque OpenAI también ofrece embeddings. Se descartó por costo: casi cinco veces
  más en el modelo que se usa en cada mensaje, por la misma calidad. OpenAI retiene los pedidos
  hasta 30 días para el control de abuso.
- **GPT-5.4 nano:** el más parecido en precio. Descartado por lo que dice el punto 5.
- **Un modelo más grande:** no se evaluó. Los modelos chicos ya resuelven los casos, y uno
  grande multiplica el costo de cada mensaje.
- **Un intermediario que ofrece varios modelos con una sola clave:** suma una empresa más que
  recibe los mensajes, y el ADR 0020 pide el SDK directo del proveedor.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
