---
name: domain-rules
description: Determina qué reglas de dominio de Platita aplican a un ticket antes de escribir código, y qué valores exigen confirmación del usuario en vez de resolverse por defecto. Usar al empezar cualquier trabajo que toque movimientos, cuentas, presupuestos, categorías o transacciones pendientes, tanto en el backend como en el asistente de WhatsApp.
---

Antes de escribir una línea de código para este ticket, hacé lo siguiente y no avances hasta
terminarlo.

1. Leé `docs/reglas-de-dominio.md` **completo**. No lo resumas de memoria ni asumas qué dice.
2. Leé `AGENTS.md`, sección «Invariantes de dominio».
3. Si el ticket toca una entidad, leé también su descripción en `docs/03-modelo-de-datos.md`.

Después devolvé, sin escribir código todavía:

- **Grupos que aplican.** Cuáles de los once grupos de `docs/reglas-de-dominio.md` rigen este
  ticket, con el número y el título de cada uno, y una línea diciendo por qué aplica.
- **Qué se resuelve solo.** Qué valores puede completar el sistema sin preguntar. Recordá que los
  únicos defaults derivables permitidos son fecha, moneda y categoría.
- **Qué exige confirmación del usuario.** Qué valores no se pueden deducir. Si aparece la cuenta
  o el período de presupuesto, decilo explícitamente: son los dos que más se rompen.
- **Qué invariante podría romper este ticket.** Cuál de las siete es la que está en riesgo acá, y
  qué test la cubriría.
- **Qué falta en la especificación.** Si una regla no alcanza para decidir un caso del ticket,
  reportalo y pará. No lo completes vos: la decisión es humana.

Si el ticket es de API, agregá el contrato de `docs/04-api.md` a la lista de lecturas previas.
