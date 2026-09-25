---
description: Compara la especificación de docs/ contra el código real y reporta las diferencias sin resolverlas. Usar al cerrar un corte vertical, antes de su último commit, y como barrido antes de cada entrega.
---

Compará lo que dice la especificación con lo que hace el código, en el alcance que se te indique.

La especificación son los archivos de `docs/`. El código es la realidad. **No son lo mismo y no
se ajustan entre sí automáticamente.**

Procedé así:

1. Leé la parte de `docs/` que cubre el alcance indicado: `docs/04-api.md` para endpoints,
   `docs/03-modelo-de-datos.md` para entidades y columnas, `docs/reglas-de-dominio.md` para
   comportamiento.
2. Leé el código correspondiente.
3. Listá cada diferencia encontrada, en una tabla con tres columnas: qué dice la especificación,
   qué hace el código, y cuál de los dos parece estar mal.

Reglas de este comando, sin excepción:

- **No modifiques nada.** Ni el código ni la documentación.
- **No corrijas la documentación para que coincida con el código.** Es la tentación por defecto y
  es exactamente lo que no hay que hacer.
- Por defecto la especificación manda y lo que se corrige es el código, pero la decisión final es
  humana: vos reportás, no resolvés.
- Si no encontrás ninguna divergencia, decilo en una línea y terminá.

El criterio completo está en `AGENTS.md`, sección 10.
