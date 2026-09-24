# 0015 — Borrar un movimiento es marcarlo como borrado, no eliminar la fila

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

El usuario puede borrar un movimiento que ya confirmó: un gasto que cargó dos veces, una
transferencia que no ocurrió, una compra con tarjeta que se anuló. La especificación no decía
cómo.

La decisión anterior sobre correcciones marca cada movimiento corregido con cuándo y quién lo
cambió por última vez, para que los miembros de un grupo familiar sepan que el gastado de un
período se movió por una corrección y no por un gasto nuevo. Un borrado es el caso extremo de
una corrección. Si eliminara la fila, el gastado del presupuesto familiar bajaría sin dejar
ningún rastro, que es justamente lo que esa decisión quiso evitar.

Además, varias restricciones de la base apuntan a un movimiento o dependen de que exista. Una
regla recurrente genera como mucho un movimiento por fecha, con una clave única: si el
movimiento de octubre se eliminara, el motor podría volver a generarlo en una segunda corrida.

## Decisión

1. **Borrar es marcar.** `TRANSACTION`, `TRANSFER` y `CARD_PURCHASE` suman `deleted_at` y
   `deleted_by`. Borrar un movimiento es fijar `deleted_at`; la fila sigue en la tabla. El
   trigger que ya marca las correcciones completa `deleted_by` con el usuario que la aplicación
   indicó en la transacción.
2. **Un movimiento borrado no cuenta en ninguna agregación**: ni en el saldo de una cuenta, ni
   en el gastado de un presupuesto, ni en las alertas. Es el mismo criterio que ya se aplica a
   una fila marcada como duplicado.
3. **La aplicación no puede eliminar filas.** El rol de la aplicación no tiene permiso de
   `DELETE` sobre esas tres tablas. Solo el proceso de borrado de cuenta, que ejecuta el derecho
   de supresión con un rol propio, elimina filas de verdad: ahí la supresión prevalece sobre la
   trazabilidad.
4. **Borrar una compra con tarjeta corta las cuotas futuras.** Una compra borrada no genera más
   cuotas. Las que ya se generaron son movimientos comunes y se borran una por una, porque
   pueden estar en un resumen ya cerrado que el banco efectivamente cobró.
5. **Qué muestra la interfaz no se decide acá.** Si los movimientos borrados aparecen en los
   listados marcados, o si se pueden restaurar, se define al especificar cada pantalla.

## Consecuencias

### Positivas

- Los miembros de un grupo familiar pueden saber que un movimiento se borró, cuándo y quién lo
  hizo.
- Las restricciones que dependen de un movimiento siguen funcionando: una regla recurrente no
  vuelve a generar un movimiento que el usuario borró, porque su fila sigue ocupando esa fecha.
- Un borrado por error se puede deshacer, porque el dato no se perdió.
- Es coherente con la marca de las correcciones: el mismo trigger y el mismo origen de quién
  hizo el cambio.

### Negativas y costos asumidos

- Toda consulta que agrega montos tiene que excluir las filas borradas, además de las marcadas
  como duplicado. Olvidarlo en una consulta nueva suma dinero que no existe. Mitigación: los
  repositorios exponen las consultas de saldo y de gastado ya filtradas, y cada una tiene un test
  con un movimiento borrado.
- Las filas borradas siguen ocupando espacio y siguen en los índices. Con el volumen esperado es
  despreciable.
- Un movimiento borrado sigue siendo un dato del usuario: se elimina de verdad recién cuando el
  usuario borra su cuenta.

## Alternativas descartadas

- **Eliminar la fila:** es lo más simple y no obliga a filtrar en cada consulta, pero el gastado
  de un presupuesto familiar cambia sin rastro, y la clave única de las reglas recurrentes deja
  de proteger contra una segunda generación del mismo movimiento.
- **Registrar el borrado como un movimiento inverso:** un gasto de 3.500 se compensaría con un
  ingreso de 3.500. Deja rastro sin filtrar nada, pero el usuario vería en sus listados un
  ingreso que nunca existió, y el ingreso inverso necesitaría una categoría de ingreso que no
  corresponde al gasto original.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
