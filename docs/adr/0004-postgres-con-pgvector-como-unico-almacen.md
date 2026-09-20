# 0004 — PostgreSQL con pgvector como único almacén

- Estado: Aceptada
- Fecha: 2026-09-20

## Contexto

El producto necesita dos cosas de su capa de persistencia: los datos relacionales del usuario
(usuarios, cuentas, grupos familiares, presupuestos, movimientos, categorías) y los embeddings
de la base de conocimiento financiero que alimenta el motor de RAG. Resolverlo con dos motores
distintos es la opción por defecto de la industria, pero implica operar dos bases de datos.

## Decisión

PostgreSQL como único almacén, con la extensión pgvector para los embeddings de
`ADVICE_DOCUMENT`. Es una decisión de arranque, no definitiva: el acceso a la base vectorial se
aísla detrás de un puerto propio, de forma que el motor real sea un detalle de infraestructura
reemplazable.

## Consecuencias

### Positivas

- No se paga el costo operativo de un segundo motor de base de datos hasta que haya una razón
  real para necesitarlo.
- pgvector con índice HNSW sostiene sin problema volúmenes bastante mayores al de este proyecto.
- pgvector está soportado como extensión estándar del Postgres gestionado de Render, sin
  depender de elegir la plantilla correcta como sí pasa en otras plataformas.
- Si en el futuro el volumen de consultas o el tamaño de la base de conocimiento lo justifica, se
  cambia el adaptador por otro motor sin tocar el servicio de RAG.

### Negativas y costos asumidos

- Se asume que un motor generalista con una extensión rinde menos que un motor vectorial
  dedicado en escenarios de alto volumen; el reemplazo ya está identificado como probable.
- Queda una dependencia de que el Postgres gestionado siga ofreciendo la extensión.

## Alternativas descartadas

- **Base vectorial dedicada (Pinecone, Qdrant, Weaviate):** descartada como decisión de arranque
  porque obliga a operar un segundo motor de base de datos sin una razón real todavía. Queda
  identificada como el reemplazo probable, y el puerto propio existe justamente para que ese
  cambio sea reemplazar un adaptador.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
