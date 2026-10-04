# 5. Historias de usuario

> Siete historias de usuario: seis **must-have**, que componen el flujo end-to-end comprometido para el MVP, y una **should-have**. El orden sigue la secuencia real de uso, salvo la HU6 y la HU7, que se sumaron después y conservan su número para no renumerar las referencias existentes: en el uso real, la HU6 va primera, porque es el alta, y la HU7 va antes de armar un presupuesto de grupo. Después configuro mis cuentas, después armo el presupuesto del período, ahí empiezo a registrar movimientos, los reviso en el dashboard, y el sistema me avisa si me estoy pasando.

**Historia de Usuario 1** · *must-have*

**Como** usuario que maneja varias cuentas y billeteras
**Quiero** dar de alta mis cuentas y ver cuánto tengo en cada una
**Para** saber mi situación real sin entrar a cada banco o billetera por separado

*Criterios de aceptación:*

- Puedo crear una cuenta indicando nombre, institución, tipo (banco, billetera, broker, efectivo, tarjeta o "me deben"), moneda y saldo inicial.
- El saldo de cada cuenta se muestra calculado a partir del saldo inicial más los movimientos imputados a ella, no como un valor que yo tenga que actualizar.
- Una cuenta de broker solo recibe lo que le aporto y lo que retiro, y muestra lo aportado neto: Platita no sigue el valor de mis inversiones.
- El dashboard lista mis cuentas con su saldo actual, agrupadas por moneda. Las cuentas de inversión van aparte, con lo aportado neto, que no suma en ningún total.
- Tengo una cuenta de inversión por moneda. Comprar dólares adentro del broker lo registro como una transferencia entre las dos.
- Un plazo fijo es una cuenta más: al vencer, su interés entra como rendimiento.
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
- El borrador del próximo período se arma solo, copiando el ingreso estimado y los topes del período anterior. Lo cambio o armo uno nuevo desde el dashboard.
- El período puede empezar el día que yo elija, por ejemplo el día que cobro.
- Al confirmarlo queda activo y los movimientos pueden imputarse a él.
- Si el período no está confirmado y su fecha de inicio se acerca, recibo un recordatorio por WhatsApp con su resumen, y puedo confirmarlo respondiendo.
- El recordatorio lista también los gastos e ingresos recurrentes que cambian de monto, como el alquiler o la luz, con el último monto. Al confirmar, confirmo esos montos o los corrijo, y puedo dejar sin confirmar los que todavía no sé: esos me los pregunta cuando vencen. En la misma respuesta puedo corregir el ingreso estimado.
- Si es familiar, solo el dueño del grupo lo arma y lo confirma.

*Prioridad:* Alta
*Estimación:* 8 puntos

---

**Historia de Usuario 3** · *must-have*

**Como** usuario del asistente
**Quiero** poder registrar un gasto o ingreso escribiéndole a Platita por WhatsApp en lenguaje natural
**Para** no tener que abrir una app ni completar un formulario cada vez que gasto algo

*Criterios de aceptación:*

- El mensaje se interpreta y se ubica la categoría entre las existentes del usuario; si ninguna encaja, el asistente sugiere crear una nueva en vez de forzar una que no corresponde.
- Si el mensaje no indica fecha, se toma la del día; si no indica moneda, se toma la de la cuenta que nombré, o mi moneda primaria si no nombré ninguna.
- El asistente propone a qué presupuesto imputar el gasto (según la fecha y los períodos activos del usuario) y **el usuario lo confirma siempre** — ninguna transacción manual se imputa a un presupuesto sin visto bueno explícito.
- **El movimiento no se registra si falta el monto, la cuenta, la confirmación del presupuesto, o el tipo cuando el mensaje no deja claro si es gasto o ingreso.** Esos no se dan por supuestos.
- Cuando falta más de uno, se piden todos juntos en un solo mensaje, ofreciendo las opciones disponibles del usuario (sus cuentas dadas de alta, sus presupuestos activos) para que responder sea elegir, no escribir. Lo ya interpretado se conserva: el usuario no repite el mensaje entero.
- Si queda sin responder, el movimiento no se registra a medias ni se descarta en silencio: queda pendiente y el asistente lo recuerda una vez antes de expirarlo.
- El asistente confirma el registro por el mismo canal, listando de forma explícita todo lo que quedó guardado —incluidos los valores que resolvió solo (fecha, moneda, categoría)—, y acepta correcciones sobre cualquiera de ellos: respondiendo con una cita a esa confirmación, en cualquier momento, o describiendo el movimiento para que el asistente lo busque. Nunca corrige un movimiento que yo no señalé.
- Puedo borrar un movimiento, o recuperar uno que borré, por WhatsApp. Antes de hacerlo, el asistente me pide confirmación.
- Si lo que escribí es plata que moví entre mis cuentas, el asistente lo registra como transferencia y me lo dice en la confirmación, aclarando que no cuenta como gasto. Si se equivocó de tipo, lo corrijo con una respuesta corta.
- Si otro miembro del grupo ya cargó el mismo monto al mismo presupuesto ese día o el anterior, el asistente me pregunta si es el mismo gasto antes de registrarlo.
- El movimiento queda marcado con `source = manual`.
- Si prefiero la computadora, también puedo cargar gastos, ingresos y transferencias desde el dashboard, eligiendo yo la cuenta y el presupuesto. Las compras con tarjeta y los movimientos recurrentes los cargo conversando, no por formulario.

*Prioridad:* Alta
*Estimación:* 13 puntos

---

**Historia de Usuario 4** · *must-have*

**Como** usuario con presupuesto familiar
**Quiero** ver cuánto llevamos gastado del presupuesto del período
**Para** saber si estamos dentro de lo planeado sin tener que sumar manualmente

*Criterios de aceptación:*

- El dashboard muestra, para el período seleccionado, el ingreso estimado y el real, y el tope, lo gastado y el porcentaje usado de cada categoría. Las categorías sin tope también aparecen, con lo gastado, así veo en qué se me fue la plata.
- *(Should-have)* Puedo preguntarle al asistente por WhatsApp lo que quiera sobre mis gastos, ingresos, saldos y presupuesto, como "¿gasté más en el super que el mes pasado?", y me responde con mis datos. Si no puede responder algo, me lo dice y me manda al dashboard.
- Un reintegro o una devolución que vinculé a un gasto resta del gastado de su categoría, en el período en que llegó, y se ve junto a ese gasto.
- Lo que presté, o lo que otros me deben de un gasto compartido, se ve aparte como "me deben", por persona, y no cuenta como gastado.
- Se distingue visualmente entre presupuestos individuales y de grupo, sea una familia o una actividad como un consultorio.
- En un presupuesto de grupo veo cuánto imputó cada miembro al período.
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
- Al pasar el 80% y al pasar el 100% del tope de una categoría se envía una alerta proactiva por WhatsApp. Los dos umbrales son iguales para todos y se ajustan por configuración.
- La alerta incluye un consejo relacionado, generado por el sistema de RAG a partir de la base de conocimiento curada por el producto.
- No se envía más de una alerta por umbral, categoría y período para evitar spam: como mucho dos por categoría.
- Si el presupuesto es familiar, la alerta me llega a mí y a los demás miembros, a cada uno que aceptó recibir avisos.

*Prioridad:* Media
*Estimación:* 8 puntos

---

**Historia de Usuario 6** · *must-have*

**Como** persona que le escribe a Platita por primera vez
**Quiero** darme de alta conversando por WhatsApp, en pocos minutos
**Para** empezar a registrar mis gastos sin instalar nada ni completar un formulario

*Criterios de aceptación:*

- Platita me responde porque mi número fue habilitado antes. Si no lo está, recibo un aviso de que no está habilitado y no empieza ningún alta.
- Lo primero que recibo es el pedido de aceptar los términos y la política de privacidad. Si no acepto, no se guarda nada mío más allá del mensaje que mandé.
- La parte obligatoria me pide nombre, país, confirmar mi moneda primaria, si quiero recibir avisos y al menos una cuenta. Puedo dar de alta varias cuentas en un solo mensaje.
- Al terminar el alta ya tengo un presupuesto del mes en curso, sin topes, para que mi primer gasto tenga dónde imputarse. Le pongo ingreso y topes cuando quiera, desde el dashboard.
- Si mi primer mensaje fue un gasto, al terminar el alta se retoma sin que tenga que repetirlo.
- Al terminar, el asistente me ofrece configurar mis categorías y responder unas preguntas para mejorar los consejos. Puedo saltear cualquiera, o todas, y completarlas después desde el dashboard.
- Si no acepto recibir avisos, Platita nunca me escribe por su cuenta, pero sí me puede mencionar una alerta dentro de una respuesta a algo que escribí. Puedo cambiar ese permiso cuando quiera.

*Prioridad:* Alta
*Estimación:* 8 puntos

---

**Historia de Usuario 7** · *must-have*

**Como** usuario que comparte gastos con su familia o que tiene una actividad propia
**Quiero** crear un grupo e invitar a quien corresponda
**Para** llevar un presupuesto compartido, o el de mi actividad, separado del personal

*Criterios de aceptación:*

- Creo un grupo dándole un nombre, por WhatsApp o desde el dashboard, y quedo como su dueño. Una actividad es un grupo al que no invito a nadie.
- Al crearlo ya tiene un presupuesto del mes en curso, sin topes, para que el primer movimiento tenga dónde imputarse.
- No puedo tener dos grupos con el mismo nombre: el asistente reconoce cada presupuesto por el nombre de su grupo.
- Para invitar a alguien, Platita me da un enlace de WhatsApp con un código, que le mando yo. Platita no le escribe a la persona invitada.
- El código sirve para una sola persona, una sola vez, y vence a los 7 días. Veo las invitaciones abiertas y puedo revocarlas.
- Al invitar se me advierte que quien entre va a ver todo el historial del grupo.
- Quien recibe el enlace le escribe a Platita; si no es usuario, primero se da de alta. Antes de sumarse ve el nombre del grupo y el de su dueño, y confirma.
- Un código vencido, usado o inexistente recibe siempre la misma respuesta.
- Si acepté recibir avisos, me llega uno cuando alguien se suma.

*Prioridad:* Alta
*Estimación:* 5 puntos
