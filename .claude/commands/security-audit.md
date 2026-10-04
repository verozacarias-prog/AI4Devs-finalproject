---
description: Audita todo el backend contra el OWASP Top 10 web y el OWASP Top 10 para aplicaciones LLM, de a un hallazgo por vez y por orden de criticidad. Usar antes de cada entrega, no en cada pull request.
---

Actuá como auditor de seguridad de aplicaciones. Analizá todo `backend/` contra dos listas:

- el OWASP Top 10 de aplicaciones web, en su edición vigente;
- el OWASP Top 10 para aplicaciones LLM, en su edición vigente.

Antes de empezar, confirmá cuál es la edición vigente de cada lista en el sitio de OWASP. No
uses la que recuerdes.

Leé primero qué ya está decidido, para no reportar como hallazgo algo que el diseño resuelve en
otro lado:

- `docs/seguridad-llm.md`, con el cruce de Platita contra la lista de LLM;
- `docs/02-arquitectura.md`, sección 2.5;
- los ADR 0013, 0016, 0017 y 0023 de `docs/adr/`.

Después recorré el código y armá la lista completa de hallazgos, ordenada de mayor a menor
criticidad. Mostralos **de a uno**. Para cada hallazgo:

1. **Categoría** de OWASP a la que corresponde y **criticidad**: crítica, alta, media o baja.
2. **Código vulnerable:** el archivo, la línea y el fragmento.
3. **Riesgo:** qué puede hacer un atacante con eso en Platita, en concreto. Quién es, qué manda
   y qué obtiene.
4. **Corrección:** el cambio de código propuesto, respetando la arquitectura hexagonal y las
   convenciones de `AGENTS.md`.

Después de cada hallazgo, frená y esperá la respuesta antes de mostrar el siguiente.

Reglas de este comando, sin excepción:

- **No modifiques nada.** Mostrás la corrección; no la aplicás.
- Si un hallazgo contradice lo que dice la especificación, es una divergencia: reportala como
  tal, según `AGENTS.md`, sección 10.
- Al citar un fragmento, no copies secretos ni datos personales: enmascaralos.
- Una categoría sin hallazgos se dice en una línea al final, con qué revisaste para afirmarlo.
- Si `backend/` todavía no existe, decilo en una línea y terminá.
