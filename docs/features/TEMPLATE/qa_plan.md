# Plan de pruebas — FEAT-XXX · <título>

## Camino feliz

Qué se prueba cuando todo sale bien, de punta a punta.

## Casos límite

Los propios del dominio: montos en cero, moneda distinta a la primaria, período sin confirmar,
usuario sin cuentas, usuario en más de un grupo familiar.

## Errores

Qué se prueba cuando falla la consulta, el LLM no interpreta el mensaje, o el proveedor de
WhatsApp no responde.

## Reglas de dominio bajo prueba

Un test por cada invariante que esta funcionalidad podría romper. Enlazar el grupo de
[`reglas-de-dominio.md`](../../reglas-de-dominio.md) que cubre cada uno.

| Regla | Test que la cubre |
|---|---|

## Cobertura

Qué quedó sin cubrir y por qué.
