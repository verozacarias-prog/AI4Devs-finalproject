# Plan de pruebas — FEAT-XXX · <título>

Los casos de prueba de la funcionalidad, corte por corte. Se escriben antes de cada corte y los
aprueba una persona: hasta entonces no se escribe ningún test
([convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales)).

Cada caso sale de un criterio de aceptación de [spec.md](spec.md) o de una regla de dominio, y
se escribe en castellano, sin código. Un test no se modifica ni se borra sin aprobación.

La línea "Aprobado por" la completa la persona que aprueba, nunca un asistente. Los casos de
componente, los de los cuatro estados de una pantalla, se suman y se aprueban cuando la pantalla
está armada; los demás, antes de empezar el corte.

## Casos del corte 1 — camino feliz

- **Aprobado por:** <nombre>, AAAA-MM-DD | pendiente

| Caso | Sale de | Tipo | Entrada | Resultado esperado | Test |
|---|---|---|---|---|---|
| C1-01 | CA-1 | Unitario | | | |

`Tipo` es unitario, de integración o de componente. `Test` se completa cuando el test existe,
con su archivo y su nombre.

## Casos del corte 2 — errores y estado vacío

- **Aprobado por:** pendiente

Qué pasa cuando falla la consulta, el LLM no interpreta el mensaje o el proveedor no responde, y
los casos límite del dominio: montos en cero, moneda distinta a la primaria, período sin
confirmar, usuario sin cuentas, usuario en más de un grupo familiar.

Siempre, si la funcionalidad lee o escribe datos de un usuario: otro usuario autenticado que
pide el mismo recurso recibe `404`, y uno que salió del grupo familiar solo ve los períodos en
que fue miembro.

| Caso | Sale de | Tipo | Entrada | Resultado esperado | Test |
|---|---|---|---|---|---|
| C2-01 | CA-N | | | | |

## Casos del corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

| Caso | Sale de | Tipo | Entrada | Resultado esperado | Test |
|---|---|---|---|---|---|
| C3-01 | CA-N | | | | |

## Reglas de dominio bajo prueba

Un caso por cada invariante que esta funcionalidad podría romper. Enlazar el grupo de
[`reglas-de-dominio.md`](../../reglas-de-dominio.md) que cubre cada uno.

| Regla | Caso que la cubre |
|---|---|

## Sin cubrir

Qué criterio o qué regla quedó sin caso, y por qué.
