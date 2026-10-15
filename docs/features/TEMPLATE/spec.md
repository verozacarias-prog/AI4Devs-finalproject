# Especificación — FEAT-XXX · <título>

- **Historia de usuario:** [HU-X](../../05-historias-de-usuario.md)
- **Estado:** borrador | aprobada
- **Fecha:** AAAA-MM-DD

## Alcance

Qué entra y qué no. Si algo se deja afuera, decir por qué: decisión de alcance, no omisión.

## Reglas de dominio que aplican

Listar los grupos de [`reglas-de-dominio.md`](../../reglas-de-dominio.md) que rigen esta
funcionalidad. No copiar su texto: enlazar.

- § N — <grupo>

## Criterios de aceptación

Cada criterio es una regla, en una frase, dicha desde lo que hace o ve la persona. Vale para
cualquier dato. Van agrupados por requisito, y cada uno lleva un identificador, `CA-1`,
`CA-2`…, que no se reutiliza ni se renumera: los casos y los tests lo citan.

### <Requisito>

<La regla general, en una frase.>

- **CA-1.** <El criterio.>

## Casos de prueba

Cada caso es un ejemplo concreto de un criterio, con datos que se pueden revisar a mano, y se
entiende solo, sin leer los demás. Se escriben antes de cada corte y los aprueba una persona:
hasta entonces no se escribe ningún test
([convenciones de desarrollo](../../convenciones-de-desarrollo.md#1-cortes-verticales)). La
línea "Aprobado por" la completa esa persona, nunca un asistente. Los casos de componente, los
de los estados de una pantalla, se suman y se aprueban cuando la pantalla está armada.

### Corte 1 — camino feliz

- **Aprobado por:** <nombre>, AAAA-MM-DD | pendiente
- **Total:** N casos, N unitarios y N de integración.

| Caso | Qué prueba | Tipo | Sale de |
|---|---|---|---|
| C1-01 | | Unitario | CA-1 |

#### C1-01 · <qué prueba el caso>

- **Sale de:** CA-1 · **Tipo:** unitario | integración | componente
- **Dado** <el estado inicial completo>,
- **cuando** <una sola acción>,
- **entonces** <el estado final, con la cuenta escrita si hay un cálculo>.
- **Test:** — <el archivo y el nombre del test, cuando existe>

### Corte 2 — errores y estado vacío

- **Aprobado por:** pendiente

Qué pasa cuando falla la consulta, el LLM no interpreta el mensaje o el proveedor no responde, y
los casos límite del dominio: montos en cero, moneda distinta a la primaria, período sin
confirmar, usuario sin cuentas, usuario en más de un grupo familiar.

Siempre, si la funcionalidad lee o escribe datos de un usuario: otro usuario autenticado que
pide el mismo recurso recibe `404`, y uno que salió del grupo familiar solo ve los períodos en
que fue miembro.

### Corte 3 — observabilidad y accesibilidad

- **Aprobado por:** pendiente

## Estados de pantalla

Obligatorio para toda pantalla del dashboard. Ver
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).

| Estado | Cuándo ocurre en esta pantalla | Qué muestra |
|---|---|---|
| Cargando | | |
| Con contenido | | |
| Vacío | | |
| Error | | |

## Mensajes al usuario

Los textos de WhatsApp van en español. Incluir el mensaje de confirmación con los valores
asumidos, cuando corresponda.

## Reglas de dominio bajo prueba

Un caso por cada invariante que esta funcionalidad podría romper. Enlazar el grupo de
[`reglas-de-dominio.md`](../../reglas-de-dominio.md) que cubre cada uno.

| Regla | Caso que la cubre |
|---|---|

## Sin cubrir

Qué criterio o qué regla quedó sin caso, y por qué.

## Fuera de alcance

## Preguntas abiertas
