# Notas de Platita para `/fastapi-harness:security-audit`

- **El backend** es `backend/`. Platita usa un modelo de lenguaje, así que se audita contra las
  dos listas.
- **Lo que ya está decidido,** y hay que leer antes de reportar:
  - [`docs/seguridad-llm.md`](../../docs/seguridad-llm.md), con el cruce de Platita contra la
    lista de LLM;
  - [`docs/02-arquitectura.md`](../../docs/02-arquitectura.md), sección 2.5;
  - los ADR 0013, 0016, 0017 y 0023 de [`docs/adr/`](../../docs/adr/).
- **Un hallazgo que contradice la especificación** es una divergencia, según la
  [sección 10 de `AGENTS.md`](../../AGENTS.md#10-especificación-contra-código).
- **La corrección** respeta la arquitectura hexagonal y las convenciones de `AGENTS.md`.
