# 0014 — Las correcciones de un movimiento se marcan con cuándo y quién, sin guardar versiones anteriores

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

Un movimiento confirmado se puede corregir. El asistente registra el gasto y responde listando
lo que guardó ("Listo. $3.500 · comida · Galicia · presupuesto familiar de septiembre"), y el
usuario puede contestar "eran 3.800" o "fue ayer". Además, el derecho de rectificación permite
corregir movimientos desde el dashboard y por WhatsApp en cualquier momento.

El modelo guardaba cada movimiento como una fila que se actualiza en su lugar, sin ninguna marca
de que cambió. En un presupuesto familiar, los miembros ven todos los movimientos imputados al
período, sin importar quién los registró. Si uno corrige un monto, los demás ven otro porcentaje
de gastado y nada les indica que hubo una corrección, ni quién la hizo. Lo mismo pasa cuando el
dueño del grupo resuelve los pendientes de un miembro que sale.

Un diagnóstico de la capa de datos propuso guardar el historial completo de cada movimiento: una
tabla con la fila antes y después de cada cambio, llenada por un trigger. Su argumento era poder
reconstruir qué mostraba Platita en una fecha pasada. Al revisarlo con la autora se separaron
dos preguntas:

- **Cuánto se gastó hasta una fecha.** Se responde sin historial: es la suma de los movimientos
  con fecha hasta ese día, con los datos actuales. Es la función de un registro de gastos.
- **Qué mostraba Platita ese día, antes de una corrección posterior.** Solo se responde con
  historial. Es una pregunta de auditoría, propia de un sistema contable, y rara en un producto
  de finanzas personales y familiares.

Antes de la confirmación no hay nada que marcar: un pendiente se corrige libremente, nadie más lo
ve y no pesa en ningún saldo ni presupuesto.

## Decisión

1. **Dos columnas en las tablas de movimientos confirmados.** `TRANSACTION`, `TRANSFER` y
   `CARD_PURCHASE` suman `updated_at` (cuándo se modificó por última vez) y `updated_by` (quién).
   Las dos son nulas mientras el movimiento no se modificó, así que un movimiento está corregido
   si y solo si `updated_at` está informado.
2. **Las llena la base.** Un trigger `BEFORE UPDATE` en cada una de las tres tablas fija
   `updated_at` con la hora del cambio y `updated_by` con el usuario que la aplicación indicó en
   la transacción (`SET LOCAL app.actor_id`). Ningún camino de escritura puede modificar un
   movimiento sin actualizar la marca. Si el cambio lo hace un proceso programado, `updated_by`
   queda nulo y `updated_at` informado.
3. **No se guardan versiones anteriores.** Una corrección reemplaza el valor anterior, que no se
   conserva. No se puede saber qué valor tenía un movimiento antes de corregirse, ni reconstruir
   qué mostraba Platita en una fecha pasada.
4. **Qué muestra la interfaz no se decide acá.** Esta decisión garantiza que el dato exista.
   Cómo se muestra, por ejemplo con una marca de "editado" junto al movimiento, se define al
   especificar la pantalla.

## Consecuencias

### Positivas

- Los miembros de un grupo familiar pueden saber que un movimiento se corrigió, cuándo y quién
  lo hizo, incluido el dueño del grupo cuando resolvió pendientes de otro miembro.
- Dos columnas y un trigger corto: sin tablas nuevas, sin cambios en las consultas de saldo ni
  de presupuesto, y sin nada que borrar aparte cuando un usuario borra su cuenta.
- Ampliarlo después a un historial completo no requiere deshacer nada: las columnas siguen
  sirviendo y el historial se suma al lado.

### Negativas y costos asumidos

- Se pierde el valor anterior de cada corrección. Si alguien pregunta por qué el gastado de una
  categoría pasó de 71% a 74%, Platita puede mostrar qué movimiento se corrigió y quién lo hizo,
  pero no de cuánto era antes.
- Solo queda la última corrección: si un movimiento se corrigió dos veces, la primera no deja
  rastro.
- No se puede reconstruir un saldo o un gastado tal como se veía en una fecha pasada.
- Alembic no detecta triggers al autogenerar migraciones: se escriben a mano, con un test de
  integración que verifique que una corrección actualiza la marca.

## Alternativas descartadas

- **Historial completo en una tabla llenada por trigger:** conserva cada versión, con quién y por
  qué, y permite reconstruir el pasado. Es la opción correcta para un sistema contable, pero la
  pregunta que resuelve, qué mostraba el sistema antes de una corrección, no es una necesidad de
  este producto. Suma una tabla que crece con cada corrección, un trigger con permisos
  especiales, y un paso más en el borrado de cuenta, porque el historial guardaría los datos que
  la supresión tiene que eliminar. Queda como ampliación posible si aparece la necesidad.
- **Libro contable con reversiones:** un movimiento nunca se modifica, y corregirlo es anular el
  original con un asiento inverso y crear uno nuevo. Una corrección conversacional como "eran
  3.800" produciría tres filas, y cada consulta de saldo, de presupuesto y de listado tendría que
  saber manejar reversiones.
- **Sin ninguna marca:** es lo que había. Deja a los miembros de un grupo sin forma de saber que
  el gastado cambió por una corrección y no por un gasto nuevo.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
