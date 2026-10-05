# 0020 — Sin framework de orquestación de IA

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

El módulo de RAG del máster propone construir el asistente sobre un framework como LangChain,
que trae cadenas de pasos, agentes, memoria de conversación, recuperadores, envoltorios de
proveedores y de bases vectoriales, y particionadores de texto.

En Platita, casi todo eso ya tiene dueño por decisiones anteriores:

- El flujo entre una llamada al modelo y la siguiente son reglas de negocio: mirar la cuota,
  exigir la confirmación de la cuenta y del presupuesto, guardar el pendiente, escribir todo en
  una sola transacción. Viven en los casos de uso, y el dominio no importa infraestructura
  ([ADR 0001](0001-arquitectura-hexagonal.md)).
- El historial está en las tablas de mensajes, que además son la cola del worker y se purgan
  ([ADR 0010](0010-webhook-asincrono-con-tabla-de-entrada.md),
  [ADR 0018](0018-clasificacion-inicial-y-memoria-de-conversacion.md)).
- La búsqueda vectorial es SQL sobre pgvector, detrás de un puerto
  ([ADR 0004](0004-postgres-con-pgvector-como-unico-almacen.md)).
- El adaptador de salida es el único lugar que arma lo que se le envía al proveedor, y un test
  lo verifica ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md)).

Lo único que no tiene dueño es partir un documento en fragmentos.

## Decisión

1. **El dominio no conoce ninguna librería de IA.** Ni el SDK de un proveedor ni un framework.
2. **Los adaptadores usan el SDK directo del proveedor** para clasificar, interpretar, llamar
   funciones y generar embeddings.
3. **No se usa un framework para orquestar.** Ni cadenas, ni agentes, ni memoria, ni
   recuperadores, ni envoltorios de proveedores o de bases vectoriales.
4. **Se permite un paquete de particionado de texto, `langchain-text-splitters`,** importado
   solo en el adaptador de particionado, detrás de su puerto. Lo usa la carga de la base de
   conocimiento ([ADR 0019](0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md)).
   Recibe un texto y devuelve fragmentos: no orquesta, no guarda nada y no llama a ningún
   proveedor.
5. **Lo hace cumplir el verificador de arquitectura,** que falla si un import de un framework de
   IA aparece en el dominio o en cualquier adaptador que no sea el de particionado.
6. **Al instalarlo se revisa qué dependencias entran** y que ninguna envíe datos afuera por su
   cuenta.

## Consecuencias

### Positivas

- Lo que se envía al proveedor se arma en un solo lugar, sin plantillas ni pasos intermedios de
  una librería. El test del ADR 0013 mira un pedido que el propio adaptador escribió.
- El flujo de un mensaje se lee en los casos de uso, con las reglas de dominio a la vista.
- No hay una segunda copia del historial que purgar.
- El particionado por títulos y recursivo sale de un paquete ya probado, en vez de escribirse a
  mano.

### Negativas y costos asumidos

- El ciclo de pedir funciones y volver a llamar al modelo, la validación de la salida
  estructurada y los reintentos se escriben a mano en el adaptador.
- Cambiar de proveedor es escribir otro adaptador. El framework lo resolvería cambiando una
  clase.
- `langchain-text-splitters` trae `langchain-core` y sus dependencias, que quedan instaladas
  aunque no se usen.
- La regla depende de un verificador que conoce los nombres de los frameworks. Uno nuevo hay que
  sumarlo a la lista.

## Alternativas descartadas

- **LangChain completo, con cadenas y memoria:** una cadena tendría que contener las reglas de
  negocio que van entre un paso y otro. O el dominio importa el framework, y se rompe la regla
  hexagonal, o el flujo se muda a un adaptador, y se rompe la regla de que los adaptadores solo
  traducen. La memoria guardaría una segunda copia de los mensajes, o exigiría una clase que le
  enseñe a leer las tablas propias, que es la misma consulta con más código.
- **LangChain solo dentro de los adaptadores, como cliente del modelo:** el dominio seguiría sin
  conocerlo, pero pone una capa entre el adaptador y lo que se envía, y son solo dos proveedores
  candidatos detrás de un puerto.
- **Particionado con código propio:** no entra ninguna dependencia, y son pocas líneas. Se
  prefirió el paquete porque ya tiene las dos piezas que hacen falta, probadas, y no toca
  ninguna de las razones de arriba.
- **Otro framework de RAG:** resuelve la carga y la recuperación juntas, pero trae sus propios
  almacenes y su propio flujo, con las mismas objeciones.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
