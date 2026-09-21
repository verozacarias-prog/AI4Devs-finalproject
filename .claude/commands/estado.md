---
description: Verifica que una pantalla del dashboard implementa y testea los cuatro estados obligatorios. Usar antes de cerrar el slice 2 de cualquier funcionalidad con interfaz.
---

Revisá la pantalla indicada contra la regla de los cuatro estados de
`docs/convenciones-de-desarrollo.md`.

Para cada uno de los cuatro —cargando, con contenido, vacío y error— reportá:

- Si está **implementado** en el código, con el archivo y la línea donde se resuelve.
- Si está **testeado**, con el test que lo cubre.
- Qué se le muestra al usuario.

Prestá atención especial a esto, que es donde se falla: **vacío y error no son el mismo estado.**
Una consulta que funcionó y no devolvió datos está vacía, no falló. En Platita el caso típico es
un presupuesto confirmado sin movimientos todavía: mostrarle un error al usuario sería mentirle.

Si encontrás que el estado vacío está resuelto como error, como pantalla en blanco o como un
spinner infinito, marcalo como error del slice, no como mejora pendiente.

Terminá con un veredicto de una línea: si los cuatro estados están completos y testeados, el
slice 2 puede cerrarse; si no, listá exactamente qué falta.
