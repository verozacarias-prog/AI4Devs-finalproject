---
description: Compara la especificación de docs/ contra el código real y reporta las diferencias sin resolverlas. Usar al cerrar un corte vertical, antes de su último commit, y como barrido antes de cada entrega.
argument-hint: corte | proyecto
---

Compará lo que dice la especificación con lo que hace el código, en el modo que se te indique.

La especificación son los archivos de `docs/`. El código es la realidad. **No son lo mismo y no
se ajustan entre sí automáticamente.**

## Los dos modos

- **`corte`** (por defecto): lo que cambió la rama actual contra la rama de la entrega. Leé el
  diff con `git diff` y, de `docs/`, lo que ese cambio toca: `04-api.md` para endpoints,
  `03-modelo-de-datos.md` para entidades y columnas, `reglas-de-dominio.md` para comportamiento,
  y la `spec.md` de la funcionalidad. Buscá además, con `grep` sobre `docs/`, todo documento que
  nombre lo que cambió (una regla, un código de error, un caso, un endpoint): si dice otra cosa,
  también es una diferencia.
- **`proyecto`**: todo `docs/` contra todo el código. Armá la lista de documentos listando
  `docs/` con sus subcarpetas, más `AGENTS.md` y `README.md`; no la escribas de memoria. Cada
  documento de la lista se revisa o se declara no revisado, con el motivo. Mirá en particular lo
  que un documento afirma como estado: "todavía no", "hoy", "en la entrega N", "falta".

En los dos modos, los diagramas Mermaid de los documentos entran como cualquier texto: un
diagrama de entidad-relación se compara con las migraciones, uno de arquitectura con las
carpetas y los procesos, y uno de secuencia con el recorrido real del código, paso por paso.

## Procedimiento

1. Leé la especificación del alcance y el código correspondiente.
2. Listá cada diferencia en una tabla con tres columnas: qué dice la especificación, qué hace
   el código, y cuál de los dos parece estar mal. En modo `proyecto`, agrupá las que son la
   misma diferencia en varios documentos.
3. En modo `proyecto`, terminá con la lista de documentos que no revisaste y por qué. Si no
   queda ninguno, decilo.
4. **Proponé una issue por hallazgo**, o por grupo de hallazgos que se resuelven juntos: título,
   etiqueta (`bug` si el código está mal, `documentation` si es la especificación, `tarea` si
   falta decidir) y cuerpo, con el formato de las issues de bug del repositorio: qué pasa, qué se
   espera y qué hay que decidir antes. Así ningún hallazgo queda solo en la conversación.
5. **Pausa.** La persona elige cuáles se crean, cuáles se descartan y cuáles se juntan. Recién
   entonces creá las que aprobó, con `gh issue create` y `unset GITHUB_TOKEN`, y pasale los
   enlaces. Sin su ok no se crea ninguna.

## Reglas de este comando, sin excepción

- **No modifiques nada.** Ni el código ni la documentación.
- **No corrijas la documentación para que coincida con el código.** Es la tentación por defecto y
  es exactamente lo que no hay que hacer.
- Por defecto la especificación manda y lo que se corrige es el código, pero la decisión final es
  humana: vos reportás, no resolvés.
- Ninguna issue se crea sin que la persona la apruebe.
- Si no encontrás ninguna divergencia, decilo en una línea y terminá. En modo `proyecto`, sumá
  igual la lista de lo que no revisaste.

El criterio completo está en `AGENTS.md`, sección 10.
