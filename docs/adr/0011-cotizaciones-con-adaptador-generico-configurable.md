# 0011 — Cotizaciones con un adaptador genérico, configurable por fuente

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

Platita convierte montos entre monedas en dos lugares. El primero es cuando el usuario nombra una
moneda distinta de la de la cuenta ("gasté 50 dólares con la Galicia pesos"). El segundo es
cuando un movimiento se imputa a un presupuesto de otra moneda. En los dos casos el asistente
propone el valor convertido y el usuario lo confirma, así que la cotización es una sugerencia y
no un dato que se aplique en silencio. Aun así, una sugerencia vieja o ausente empeora la
experiencia en cada gasto en otra moneda.

La especificación original preveía una cotización cargada a mano por el usuario, con la búsqueda
automática como could-have. Con público general, la carga manual tiene un costo escondido: la
mayoría de los usuarios no va a actualizarla nunca, y cada conversión propondría un valor viejo.

Se decidió buscar la cotización automáticamente, empezando por Argentina, que es el caso
difícil porque conviven varias cotizaciones del dólar (oficial, MEP, blue, tarjeta) y cada
usuario elige cuál usa como referencia. La primera propuesta fue un adaptador por país. La
autora la objetó: sumar un país no debería costar código nuevo, solo configuración.

Casi todos los proveedores de cotizaciones hacen lo mismo: una consulta HTTP que devuelve un
documento con un número adentro. Lo que cambia entre ellos es la URL, la autenticación, el
formato y dónde está cada dato dentro de la respuesta.

## Decisión

Un solo adaptador HTTP genérico detrás del puerto de cotizaciones, y cada fuente descrita como un
bloque de configuración.

1. **Configuración en un archivo versionado del repositorio**, no en la base de datos. Cada
   fuente declara su identificador (por ejemplo `DOLAR_MEP`), país, moneda de origen y de
   destino, URL, formato de la respuesta, ruta al valor y a la fecha dentro de ella, frecuencia
   de actualización y, si hace falta, el header de autenticación con el **nombre** de la variable
   de entorno que guarda la clave, nunca la clave. Sumar un país pasa por pull request y por la
   integración continua como cualquier otro cambio.
2. **La configuración se valida al arrancar.** Un bloque incompleto o mal escrito impide que la
   aplicación arranque, en vez de fallar más tarde dentro de un proceso programado.
3. **Las rutas dentro de la respuesta son simples**: puntos e índices, del tipo
   `data.rates[0].sell`. Se implementan con código propio, sin una librería nueva.
4. **Lectores de formato, no adaptadores por país.** JSON se soporta desde el principio. Si una
   fuente publica en XML o CSV, se escribe una vez el lector de ese formato y las fuentes lo
   eligen por configuración.
5. **Un proceso programado actualiza las cotizaciones** según la frecuencia de cada fuente y las
   guarda en una tabla por fuente, par de monedas y fecha, compartida por todos los usuarios.
   **La conversión nunca consulta al proveedor en el momento**: usa la última cotización
   guardada. Si el proveedor se cae, se sigue usando la última conocida, con su fecha a la vista.
6. **Controles antes de guardar.** El valor tiene que ser positivo, y si varía respecto del
   anterior más de un umbral configurable, no se guarda y se avisa. Así un cambio de formato del
   proveedor no mete valores absurdos en las sugerencias.
7. **Cada fuente tiene un test con una respuesta real grabada**, de modo que la integración
   continua detecte una ruta mal configurada sin llamar al proveedor.
8. **La ausencia de fuente no es un error.** Un país sin fuente configurada, o una cotización
   guardada que ya envejeció, dejan al asistente sin sugerencia. En ese caso el valor lo aporta
   el usuario en la conversación, y el adaptador no interviene.

En el MVP se configuran solo fuentes argentinas.

## Consecuencias

### Positivas

- Sumar un país que publica en un formato ya soportado es agregar un bloque de configuración y
  una respuesta de ejemplo para su test, sin tocar código ni el esquema de la base.
- El dominio no sabe nada de proveedores: pide una cotización por fuente y fecha, y el adaptador
  es un detalle reemplazable.
- Una caída del proveedor no bloquea el registro de gastos, porque la conversión trabaja sobre
  lo guardado.
- La cotización está al día para todos los usuarios sin que tengan que hacer nada.

### Negativas y costos asumidos

- Se depende de proveedores externos, y los de cotizaciones argentinas no oficiales pueden cambiar
  su formato o desaparecer sin aviso. Los controles antes de guardar evitan datos absurdos, pero
  no reemplazan tener que reconfigurar la fuente.
- Un formato nuevo o una autenticación fuera de lo común (por ejemplo, un token que se renueva
  con otra llamada) sí requieren código. La promesa de "solo configuración" vale para los
  formatos y autenticaciones que ya estén soportados.
- Más trabajo inicial que un adaptador concreto para una sola fuente: el lector de rutas, la
  validación de la configuración y los controles.
- Los usuarios de países sin fuente configurada tienen un paso más en cada gasto en otra moneda.

## Alternativas descartadas

- **Carga manual por el usuario:** menos trabajo inicial y ninguna dependencia externa, pero la
  cotización se desactualiza sola y, con público general, la sugerencia sería vieja para la
  mayoría. Queda como posible complemento para países sin fuente, no como mecanismo principal.
- **Un adaptador por país:** es lo más directo de escribir la primera vez, pero cada país nuevo
  cuesta código, tests y revisión, para repetir casi siempre el mismo comportamiento.
- **Un único proveedor global de cotizaciones para todos los países:** un solo formato y una sola
  integración, pero no resuelve el caso argentino, cuyas cotizaciones de referencia (MEP, blue,
  tarjeta) no las publica un proveedor global, y ata el producto a un solo tercero.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
