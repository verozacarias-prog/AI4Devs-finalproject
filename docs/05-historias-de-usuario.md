# 5. Historias de usuario

> Cinco historias de usuario: cuatro **must-have**, que componen el flujo end-to-end comprometido para el MVP, y una **should-have**. El orden sigue la secuencia real de uso: primero configuro mis cuentas, después armo el presupuesto del período, ahí empiezo a registrar movimientos, los reviso en el dashboard, y el sistema me avisa si me estoy pasando.

**Historia de Usuario 1** · *must-have*

**Como** usuario que maneja varias cuentas y billeteras
**Quiero** dar de alta mis cuentas y ver cuánto tengo en cada una
**Para** saber mi situación real sin entrar a cada banco o billetera por separado

*Criterios de aceptación:*

- Puedo crear una cuenta indicando nombre, institución, tipo (banco, billetera, broker, efectivo), moneda y saldo inicial.
- El saldo de cada cuenta se muestra calculado a partir del saldo inicial más los movimientos imputados a ella, no como un valor que yo tenga que actualizar.
- El dashboard lista mis cuentas con su saldo actual, agrupadas por moneda.
- Puedo editar los datos de una cuenta sin perder el historial de movimientos asociados.

*Prioridad:* Alta
*Estimación:* 5 puntos

---

**Historia de Usuario 2** · *must-have*

**Como** usuario que planifica sus gastos
**Quiero** armar y confirmar el presupuesto del próximo período antes de que arranque
**Para** empezar el mes sabiendo con cuánto cuento y cuánto puedo gastar en cada rubro

*Criterios de aceptación:*

- Puedo crear un período de presupuesto individual o familiar, eligiendo cadencia mensual o quincenal.
- Cargo el ingreso estimado del período y un tope por cada categoría que quiera controlar.
- Mientras está en armado, el período figura como borrador y no se usa para calcular nada.
- Al confirmarlo queda activo y los movimientos pueden imputarse a él.
- Si el período no está confirmado y su fecha de inicio se acerca, recibo un recordatorio por WhatsApp.

*Prioridad:* Alta
*Estimación:* 8 puntos

---

**Historia de Usuario 3** · *must-have*

**Como** usuario del asistente
**Quiero** poder registrar un gasto o ingreso escribiéndole a Platita por WhatsApp en lenguaje natural
**Para** no tener que abrir una app ni completar un formulario cada vez que gasto algo

*Criterios de aceptación:*

- El mensaje se interpreta y se ubica la categoría entre las existentes del usuario; si ninguna encaja, el asistente sugiere crear una nueva en vez de forzar una que no corresponde.
- Si el mensaje no indica fecha, se toma la del día; si no indica moneda, se toma la primaria del usuario.
- El asistente propone a qué presupuesto imputar el gasto (según la fecha y los períodos activos del usuario) y **el usuario lo confirma siempre** — ninguna transacción manual se imputa a un presupuesto sin visto bueno explícito.
- **El movimiento no se registra si falta el monto, la cuenta, la confirmación del presupuesto, o el tipo cuando el mensaje no deja claro si es gasto o ingreso.** Esos no se dan por supuestos.
- Cuando falta más de uno, se piden todos juntos en un solo mensaje, ofreciendo las opciones disponibles del usuario (sus cuentas dadas de alta, sus presupuestos activos) para que responder sea elegir, no escribir. Lo ya interpretado se conserva: el usuario no repite el mensaje entero.
- Si queda sin responder, el movimiento no se registra a medias ni se descarta en silencio: queda pendiente y el asistente lo recuerda una vez antes de expirarlo.
- El asistente confirma el registro por el mismo canal, listando de forma explícita todo lo que quedó guardado —incluidos los valores que resolvió solo (fecha, moneda, categoría)—, y acepta correcciones sobre cualquiera de ellos en la respuesta.
- El movimiento queda marcado con `source = manual`.

*Prioridad:* Alta
*Estimación:* 13 puntos

---

**Historia de Usuario 4** · *must-have*

**Como** usuario con presupuesto familiar
**Quiero** ver cuánto llevamos gastado del presupuesto del período
**Para** saber si estamos dentro de lo planeado sin tener que sumar manualmente

*Criterios de aceptación:*

- El dashboard muestra, para el período seleccionado, el ingreso estimado y el tope, lo gastado y el porcentaje usado de cada categoría.
- Se distingue visualmente entre presupuestos individuales y familiares.
- Puedo ver el detalle de movimientos de una categoría, con la cuenta afectada y el origen (manual / automático) de cada uno.
- *(Should-have)* Los movimientos en moneda distinta a la primaria se muestran convertidos, con la cotización usada visible.

*Prioridad:* Alta
*Estimación:* 5 puntos

---

**Historia de Usuario 5** · *should-have*

**Como** usuario
**Quiero** recibir una alerta por WhatsApp cuando mi gasto en una categoría se acerca al límite del presupuesto
**Para** poder corregir antes de pasarme, sin tener que estar revisando el dashboard

*Criterios de aceptación:*

- El sistema revisa periódicamente los presupuestos activos contra lo gastado hasta el momento.
- Al superar un umbral configurado (ej. 80%) se envía una alerta proactiva por WhatsApp.
- La alerta incluye un consejo relacionado, generado por el sistema de RAG a partir de la base de conocimiento curada por el producto.
- No se envía más de una alerta por presupuesto y período para evitar spam.

*Prioridad:* Media
*Estimación:* 8 puntos
