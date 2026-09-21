# AGENTS.md

Contrato mínimo para cualquier agente de IA que trabaje en este repositorio, sea cual sea la
herramienta. Es corto a propósito: son las reglas que un asistente rompe por defecto y cuya
violación no se nota leyendo el resultado.

El contrato operativo completo —mapa de carpetas, convenciones de código, seguridad, base de
datos, qué leer antes de qué— está en [`CLAUDE.md`](CLAUDE.md). La especificación del proyecto
está en [`docs/`](docs/) y manda sobre los dos.

## Regla de dependencia hexagonal

`domain/` no importa nada de `adapters/` ni de librerías de infraestructura.

Imports prohibidos dentro de `domain/`: `sqlalchemy`, `fastapi`, `httpx`, `psycopg`, el cliente
de LLM. Los casos de uso hablan solo con puertos.

Backend y frontend están desacoplados y se comunican únicamente por API REST. `frontend/` no
importa nada de `backend/` ni accede a la base de datos. Fundamento en el
[ADR 0001](docs/adr/0001-arquitectura-hexagonal.md).

## Invariantes de dominio

- Nunca usar una cuenta por defecto. Si el mensaje no la menciona, preguntar.
- Nunca asignar `budget_period_id` sin confirmación explícita del usuario.
- Los defaults derivables permitidos son solo fecha, moneda y categoría, y los tres van siempre listados en el mensaje de confirmación.
- Montos en `Decimal`, nunca `float`.
- La moneda viaja siempre junto al monto, nunca implícita.
- El saldo de una cuenta se calcula, no se almacena como campo mutable.
- Una categoría nueva no se crea sin confirmación.

Para cualquier ticket de dominio, leer [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md)
completo antes de escribir código.

## Especificación contra código

Cuando la especificación y el código difieran, detenete y reportá la divergencia. No corrijas la
documentación para que coincida con el código: esa decisión es humana. El procedimiento completo
está en [`CLAUDE.md`](CLAUDE.md), sección 10.

## Antes de escribir código

- Ticket de dominio → [`docs/reglas-de-dominio.md`](docs/reglas-de-dominio.md) y [`docs/03-modelo-de-datos.md`](docs/03-modelo-de-datos.md)
- Ticket de API → [`docs/04-api.md`](docs/04-api.md)
- Pantalla nueva → [`docs/convenciones-de-desarrollo.md`](docs/convenciones-de-desarrollo.md)
- Decisión de arquitectura → [`docs/adr/`](docs/adr/)
