# 0012 — Tarjetas de crédito como cuentas, con compras que generan cuotas, y transferencias entre cuentas propias

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

La tarjeta de crédito es el medio de pago más común de los usuarios de Platita, y el modelo no
la contemplaba: los tipos de cuenta eran banco, billetera, broker y efectivo. En la práctica, una
tarjeta tiene cuatro características que un movimiento común no tiene:

- **La compra y el pago son momentos distintos.** Se compra hoy, y la plata sale de una cuenta
  recién al pagar el resumen, semanas después.
- **Cierre y vencimiento.** Lo comprado hasta la fecha de cierre entra en ese resumen, y lo
  comprado después, en el siguiente. El resumen se paga hasta la fecha de vencimiento.
- **Cuotas.** Una compra en 6 cuotas aparece en 6 resúmenes sucesivos.
- **Dos monedas.** En Argentina el resumen trae un saldo en pesos y otro en dólares. El de dólares
  se paga con dólares propios o con pesos, y en ese caso se suma una percepción impositiva.

Las apps de finanzas personales más difundidas (YNAB, Actual Budget) tratan la tarjeta como una
cuenta con saldo negativo, registran la compra como gasto e imputan el pago del resumen como una
transferencia, no como un gasto, para no contar dos veces el mismo dinero.

La autora definió un criterio distinto para el presupuesto: **un gasto con tarjeta pesa en el
presupuesto del período en que vence, no en el de la compra**, porque el presupuesto se piensa
como flujo de caja. Una compra del 20 de septiembre que vence el 5 de octubre afecta octubre.

Ese criterio choca con una regla existente: todo `TRANSACTION` tiene un período de presupuesto
confirmado, con `budget_period_id NOT NULL`. En el momento de comprar, el período del vencimiento
suele no existir todavía, y en una compra en 12 cuotas seguro no existe para las últimas.

Al analizarlo apareció además un hueco independiente de las tarjetas: el modelo no tenía
**transferencias entre cuentas propias**. Sacar efectivo, pasar plata de un banco a una billetera
o comprar dólares no tenían forma correcta de registrarse: como gasto más ingreso inflaban el
presupuesto, y sin registrar dejaban mal los saldos.

## Decisión

1. **La tarjeta es una cuenta.** Nuevo tipo de cuenta `credit_card`, con día de cierre y día de
   vencimiento. Como cada cuenta tiene una sola moneda, los saldos en pesos y en dólares de un
   mismo plástico son dos cuentas.
2. **La compra con tarjeta no es un movimiento, es una regla que genera movimientos.** Se
   registra como `CARD_PURCHASE`: monto, moneda, categoría, fecha, cuenta de la tarjeta y
   cantidad de cuotas, una si es en un pago. El usuario confirma al comprar, **una sola vez**, a
   qué dueño de presupuesto va, individual o familiar, igual que al dar de alta una regla
   recurrente.
3. **Los resúmenes se registran.** Cada tarjeta tiene sus `CARD_STATEMENT`, con fecha de cierre y
   de vencimiento, que se generan a partir de los días fijos de la cuenta y que el usuario puede
   corregir para un resumen puntual, porque los bancos a veces los corren.
4. **Al cerrar un resumen, se generan las cuotas.** Por cada compra con una cuota que entra en ese
   resumen, el sistema genera un `TRANSACTION` de gasto sobre la cuenta de la tarjeta, con fecha
   igual al vencimiento, imputado al período del dueño confirmado que cubre esa fecha. Ese
   movimiento es un gasto común y cumple todas las reglas existentes, incluido el período
   confirmado. Si el período no está confirmado, la cuota queda como pendiente y se recuerda cada
   3 días sin vencer, con la misma regla que las recurrentes.
5. **Transferencias entre cuentas propias.** Nueva entidad `TRANSFER`, con cuenta de origen y de
   destino y un monto en la moneda de cada una. No es un gasto ni un ingreso: no entra en ningún
   presupuesto, solo mueve saldos. Pagar el resumen es una transferencia de una cuenta bancaria a
   la tarjeta. Una transferencia entre monedas distintas guarda los dos montos, y el recargo
   impositivo de pagar dólares con pesos es un gasto separado, confirmado por el usuario.
6. **El saldo de una tarjeta es lo facturado y no pagado**, igual que en el resumen del banco: las
   cuotas generadas menos las transferencias recibidas. Lo comprometido a futuro, las cuotas
   todavía no generadas, se calcula desde las compras con tarjeta y se muestra aparte, por
   período, en el dashboard.

## Consecuencias

### Positivas

- El presupuesto refleja el flujo de caja real, que es como la autora lo piensa: cada cuota pesa
  en el mes en que se paga.
- Se mantiene intacta la regla de que todo movimiento tiene período confirmado. Lo que todavía no
  tiene período no es un movimiento, es una compra con tarjeta.
- Reutiliza mecanismos que ya existían: la moneda por cuenta, el dueño de presupuesto confirmado
  una vez, la unicidad por regla y fecha, y los pendientes que no vencen.
- El saldo de la tarjeta coincide con el del resumen del banco, lo que permite contrastarlos.
- Las transferencias resuelven casos que no dependen de la tarjeta: el efectivo, las billeteras y
  la compra de dólares.

### Negativas y costos asumidos

- Cuatro conceptos nuevos: un tipo de cuenta, compras con tarjeta, resúmenes y transferencias.
  Es la parte más compleja del modelo.
- Un gasto con tarjeta no se ve en el presupuesto del mes en que se hizo. Si el usuario gasta
  mucho con tarjeta en un mes, ese mes se ve bien y el siguiente viene cargado. Mitigación: el
  dashboard muestra lo comprometido para los próximos períodos.
- Un proceso programado más, el que genera las cuotas al cierre de cada resumen, con su propia
  necesidad de ser idempotente.
- Las fechas de cierre y vencimiento son fijas por defecto y el usuario tiene que corregirlas
  cuando el banco las corre. Si no lo hace, una cuota puede caer en el período equivocado.

## Alternativas descartadas

- **Imputar el gasto al presupuesto en la fecha de compra**, como hacen YNAB y Actual Budget. Es
  más simple, porque la compra sería un movimiento común, pero no refleja cuándo sale la plata,
  que es el criterio de presupuesto que definió la autora.
- **La tarjeta como medio de pago, sin saldo propio.** La compra se marcaría "con tarjeta" y el
  pago del resumen descontaría de la cuenta bancaria. Es más simple, pero el usuario no ve cuánto
  debe en la tarjeta, que es lo que más importa para llegar bien al vencimiento, y no hay forma de
  contrastar lo pagado con lo gastado.
- **Registrar solo el pago del resumen.** Pierde la categoría de cada compra, así que el
  presupuesto no sabría en qué se gastó.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
