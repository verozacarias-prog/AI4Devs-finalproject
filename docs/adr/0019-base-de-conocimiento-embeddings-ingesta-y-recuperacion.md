# 0019 — Base de conocimiento: embeddings por API en un puerto propio, carga desde archivos y recuperación por similitud

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

Los consejos responden con una base de conocimiento curada por el producto, guardada en
PostgreSQL con pgvector ([ADR 0004](0004-postgres-con-pgvector-como-unico-almacen.md)). Hasta
acá la especificación tenía una sola tabla, con el texto y su vector en la misma fila, y daba
por hecho que el embedding lo genera el proveedor del LLM. No decía cómo entra el contenido, en
qué pedazos se parte ni cuántos se recuperan.

Tres cosas obligan a decidirlo antes de escribir código:

- No todos los proveedores de LLM ofrecen embeddings.
- La columna del vector necesita una dimensión fija, que depende del modelo de embeddings, y ese
  modelo todavía no está elegido.
- Los consejos no se construyen en la entrega 2, pero lo que se construya no puede obligar a
  rediseñar para sumarlos.

## Decisión

1. **Dos puertos separados:** uno de LLM y otro de embeddings. Pueden resolverlos dos
   proveedores distintos.
2. **Embeddings por API, no con un modelo local.** Un modelo local no entra en la memoria del
   plan de despliegue propuesto. El texto de la pregunta sale hacia ese proveedor, así que lo
   alcanza la misma regla que al LLM: sin identificadores y sin uso para entrenar
   ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md)).
3. **El proveedor se elige con una evaluación, no ahora.** Unos 20 casos de la validación por
   casos de uso contra dos candidatos, midiendo calidad en español rioplatense, costo y
   latencia, con el filtro de privacidad del ADR 0013 y casos de inyección de prompts. Son dos
   evaluaciones, porque son dos elecciones con momentos distintos:
   - la del LLM, antes de escribir el código de la entrega 2, que ya necesita interpretar un
     gasto;
   - la de embeddings, antes de escribir la rama de consejos, con los documentos de ejemplo
     cargados, porque sin contenido no se puede medir si la búsqueda trae el fragmento correcto.

   El resultado de cada una se registra en un ADR cuando se haga.
4. **Las tablas se crean cuando se elija el modelo de embeddings.** La extensión pgvector se
   habilita en la primera migración; las dos tablas de la base de conocimiento van en una
   migración posterior, con la dimensión del modelo elegido.
5. **Documento y fragmento son dos tablas.** `ADVICE_DOCUMENT` guarda el texto original
   completo, el título, el tema, la fuente, las fechas y el estado. `ADVICE_CHUNK` guarda cada
   fragmento: su documento, su posición, su texto, su vector, el modelo con que se generó el
   vector y un hash de su texto.
6. **La base de datos es la fuente del contenido.** El contenido real no se versiona en el
   repositorio. Un comando de operación lee los archivos de una carpeta externa, crea o
   actualiza cada documento, y regenera solo los fragmentos cuyo hash cambió o cuyo vector es de
   otro modelo. Identifica cada documento por el nombre de su archivo. No borra: un documento
   que ya no está en la carpeta se informa, y quien cura el contenido cambia su estado. El
   comando es un adaptador de entrada más y pasa por un caso de uso
   ([ADR 0001](0001-arquitectura-hexagonal.md)).
7. **Partición.** Primero por los títulos del documento. Si una sección queda larga, partición
   recursiva en fragmentos de 800 a 1.200 caracteres, con 10 a 20 % de solape. Los valores
   concretos son configuración. El particionado está detrás de un puerto
   ([ADR 0020](0020-sin-framework-de-orquestacion-de-ia.md)).
8. **Recuperación.** Los 4 fragmentos más cercanos a la pregunta, solo de documentos con estado
   `current`, con un filtro opcional por tema. Sin búsqueda híbrida ni reordenamiento por ahora.
9. **Cada fragmento entra al prompt con su fuente.** La respuesta la cita por nombre y fecha, sin
   enlace.
10. **En el repositorio quedan tres o cuatro documentos de ejemplo,** como datos de prueba para
    los tests y para la evaluación de embeddings.

## Consecuencias

### Positivas

- Cambiar de proveedor de LLM no obliga a recalcular los vectores, y al revés.
- Cada fragmento dice con qué modelo se generó, así que un cambio de modelo se puede hacer de a
  poco y saber qué falta.
- Corregir un párrafo de un documento recalcula los fragmentos que cambiaron, no la base
  entera.
- El contenido se cura sin desplegar: se cambia un archivo y se corre el comando.
- Nada de la entrega 2 depende de una dimensión de vector elegida a ciegas.

### Negativas y costos asumidos

- Puede haber un segundo proveedor: otra cuenta, otro tope de gasto que configurar y otras
  condiciones de privacidad que revisar.
- El contenido real vive solo en la base y en la carpeta de quien lo cura. Las copias de
  respaldo pasan a ser también el respaldo de la base de conocimiento.
- Pasar a un modelo con otra dimensión exige una migración y recalcular todos los vectores.
- Con solape, cambiar un párrafo puede mover los límites de los fragmentos que siguen en su
  sección, y se recalculan más de los que cambiaron.
- Sin búsqueda híbrida, una pregunta que depende de una sigla o de un término exacto puede no
  traer el fragmento correcto. Se revisa con la evaluación.
- Un documento marcado para revisar deja de responder hasta que se lo vuelve a marcar vigente.
- La rama de consejos no se puede probar de punta a punta hasta que exista la migración de las
  dos tablas.

## Alternativas descartadas

- **Que el embedding lo genere el proveedor del LLM, por el mismo puerto:** una pieza menos,
  pero ata la elección del LLM a que ofrezca embeddings.
- **Un modelo de embeddings local:** el texto de la pregunta no saldría de la infraestructura
  propia, pero el modelo no entra en la memoria del servicio y habría que operarlo.
- **Una sola tabla, con el documento entero como fragmento:** más simple, pero un documento
  largo da un vector que no representa ninguna de sus partes, y el prompt recibiría el documento
  completo.
- **Versionar el contenido real en el repositorio:** tendría historial y revisión por pull
  request, pero ata la curaduría a un despliegue y publica el contenido con el código.
- **Búsqueda híbrida y reordenamiento desde el inicio:** mejoran la recuperación, pero suman
  piezas y costo antes de saber si hacen falta con una base de pocos documentos.
- **Crear las tablas en la primera migración, con una dimensión supuesta:** la entrega 2 tendría
  el esquema completo, a cambio de una migración que casi seguro habría que corregir.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
