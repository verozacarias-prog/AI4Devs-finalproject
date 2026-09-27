# 0002 — WhatsApp como canal principal de registro

- Estado: Aceptada
- Fecha: 2026-09-20

## Contexto

El problema que originó el producto es la fricción de llevar un control financiero real: el
usuario típico maneja varias cuentas y monedas, comparte presupuesto con su familia, y hoy
resuelve todo manualmente en planillas. El paso que hace fracasar el hábito es "sentarse a
cargar todo". Un dashboard web no lo resuelve: sigue exigiendo abrir una app y completar un
formulario cada vez que se gasta algo.

## Decisión

WhatsApp es el canal principal de registro, mediante la API oficial de WhatsApp Business (Meta
Cloud API / Twilio). El dashboard web es el canal de visualización y de configuración, y además
un canal secundario de carga, para quien prefiere un formulario: desde ahí se cargan gastos,
ingresos y transferencias. Las compras con tarjeta y las reglas recurrentes se cargan solo por
WhatsApp, porque su conversación resuelve cuotas, dueño del presupuesto y montos variables que en
un formulario serían varias pantallas.

## Consecuencias

### Positivas

- Elimina el paso de "sentarse a cargar todo" trasladando el registro a un canal que la persona
  ya usa todos los días.
- Cargar un gasto es un solo mensaje en tono coloquial, sin formularios.
- El teléfono queda verificado por el propio canal, lo que habilita reutilizarlo como identidad
  para el login del dashboard (ver [ADR 0003](0003-login-por-codigo-unico.md)).
- La misma vía sirve para las alertas proactivas de presupuesto y los recordatorios de período
  sin construir un canal de notificaciones aparte.

### Negativas y costos asumidos

- Se depende de un sistema externo de un tercero para la función central del producto.
- El canal exige conectividad, lo que descarta de entrada un modo offline de carga.
- Cada request entrante obliga a verificar la firma del webhook para descartar mensajes
  falsificados.
- WhatsApp no resuelve bien la visualización, así que hace falta igual un dashboard web: son dos
  superficies a mantener, no una.
- Hay dos canales de carga, y las reglas de confirmación tienen que valer igual en los dos. En un
  formulario, la cuenta y el presupuesto no vienen preseleccionados: un campo ya elegido que el
  usuario envía sin mirar sería un valor por defecto encubierto.
- Una compra con tarjeta o una regla recurrente no se puede cargar desde la computadora.

## Alternativas descartadas

- **El dashboard solo para ver:** era la decisión anterior. Es la más simple, pero deja sin forma
  de cargar a quien prefiere hacerlo desde la computadora, como una persona mayor ayudada por un
  familiar.
- **El dashboard con carga completa**, incluidas las compras con tarjeta y las reglas
  recurrentes: suma al MVP dos formularios complejos, con sus endpoints, para cargas que por
  WhatsApp ya se resuelven bien.

- **Solo dashboard web para la carga:** descartado porque reintroduce exactamente la fricción
  que el producto quiere eliminar; queda como canal de visualización, que es lo que sí resuelve.
- **Lectura de capturas de pantalla:** cada banco o billetera tiene su propio layout, que cambia
  con cada actualización de su app, así que no alcanza con reglas y necesitaría un pipeline de
  visión (OCR + LLM) específico por entidad, más trabajo que el resto de las vías de carga
  juntas. Candidato para un segundo MVP, no descartado para siempre.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
