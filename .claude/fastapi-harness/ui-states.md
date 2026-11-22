# Notas de Platita para `/fastapi-harness:ui-states`

- **La regla** de los cuatro estados está en las
  [convenciones de desarrollo](../../docs/convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).
  La excepción es una pantalla que no muestra datos del usuario, que no tiene estado vacío.
- **El caso típico de estado vacío** en Platita es un presupuesto confirmado sin movimientos
  todavía: mostrarle un error al usuario sería mentirle.
