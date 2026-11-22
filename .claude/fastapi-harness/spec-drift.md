# Notas de Platita para `/fastapi-harness:spec-drift`

- **Qué documento cubre cada tema:** `docs/04-api.md` los endpoints,
  `docs/03-modelo-de-datos.md` las entidades y columnas, y `docs/reglas-de-dominio.md` el
  comportamiento. La `spec.md` de cada funcionalidad está en `docs/features/FEAT-XXX/`.
- **Qué es especificación y qué es registro:** lo dice la
  [sección 10 de `AGENTS.md`](../../AGENTS.md#10-especificación-contra-código), que también da el
  criterio completo para una divergencia.
- **En modo `proyecto`,** la lista de documentos suma `AGENTS.md` y `README.md`.
- **Las etiquetas de las issues:** `bug` si el código está mal, `documentation` si es la
  especificación, y `tarea` si falta decidir. El cuerpo sigue el formato de las issues de bug
  del repositorio.
- **`gh`** se usa siempre con `unset GITHUB_TOKEN`.
