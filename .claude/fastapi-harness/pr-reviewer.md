# Notas de Platita para el agente `fastapi-harness:pr-reviewer`

## Qué leer

- `AGENTS.md`, completo.
- De `docs/`, lo que el cambio toca: `reglas-de-dominio.md` si hay lógica de negocio,
  `03-modelo-de-datos.md` si hay migraciones, `04-api.md` si hay endpoints, y los ADR que citen
  esos documentos.

## Los verificadores

Los tres se pueden correr para leer: `python3 scripts/verify_architecture.py`,
`python3 scripts/verify_docs.py` y `python3 scripts/verify_api_contract.py`.

- **`verify_architecture.py`** mira los imports, dónde va cada tipo de archivo, que ninguno
  tenga un nombre general y que toda carpeta esté en el árbol de `docs/02-arquitectura.md`. Lo
  que no ve es lo que revisa el agente en los puntos 1 y 8.
- **`verify_api_contract.py`** compara del contrato hacia `04-api.md`. La otra dirección la
  mira el agente: un estado o una regla que `04-api.md` promete y el contrato no documenta, y un
  texto de la referencia de la API que diga algo que el código no hace.

## Por punto de la revisión

1. **Arquitectura:** la regla hexagonal, en la [sección 3 de `AGENTS.md`](../../AGENTS.md#3-regla-de-dependencia-hexagonal).
2. **Reglas de dominio:** las siete invariantes de la
   [sección 5 de `AGENTS.md`](../../AGENTS.md#5-invariantes-que-un-asistente-rompe-por-defecto),
   en especial: ninguna cuenta por defecto, ningún presupuesto sin confirmación salvo que sea el
   único posible, ningún default fuera de fecha, moneda y categoría.
3. **Datos identificatorios:** teléfono, nombre, ids internos, montos y texto del usuario no
   viajan al proveedor de LLM o de embeddings ni terminan en un registro (ADR 0013 y ADR 0023).
4. **Tests primero:** ADR 0024. Una rama `tarea-…` lleva sus casos en la descripción del pull
   request.
5. **Tests:** un recurso de otro usuario responde `404`. Una pantalla tiene los cuatro estados
   testeados, salvo la que no muestra datos del usuario, que no tiene estado vacío
   (`docs/convenciones-de-desarrollo.md`, sección 2).
6. **Documentación:** una divergencia se reporta según la
   [sección 10 de `AGENTS.md`](../../AGENTS.md#10-especificación-contra-código). Los diagramas
   son Mermaid.
7. **Uso del modelo:** la tabla de `docs/seguridad-llm.md`.
8. **Orden y nombres:** el árbol de `docs/02-arquitectura.md`.
