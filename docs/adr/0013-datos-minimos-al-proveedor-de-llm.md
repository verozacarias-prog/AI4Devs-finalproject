# 0013 — Datos mínimos al proveedor de LLM, y un proveedor que no entrene con ellos

- Estado: Aceptada
- Fecha: 2026-09-24

## Contexto

Platita interpreta cada mensaje de WhatsApp con un modelo de lenguaje de un proveedor externo, y
responde consultas financieras con el mismo proveedor. Esos mensajes son de terceros: Platita
está abierta a cualquier persona, y lo que escriben son sus gastos, sus ingresos y, en las
consultas, su situación financiera. El perfil financiero opcional agrega datos sensibles, como
el rango de ingresos, las deudas y las personas a cargo.

Enviar un mensaje al proveedor es transferir esos datos a un tercero, fuera del control de
Platita y, en general, fuera del país. Qué se envía y qué hace el proveedor con eso son parte de
lo que la política de privacidad tiene que poder explicar.

Todavía no se eligió el proveedor.

## Decisión

1. **Se envía solo lo necesario para la tarea.** Para interpretar un mensaje: su texto y el
   contexto que el modelo necesita para resolverlo, como los nombres de las cuentas y de las
   categorías del usuario. Para responder una consulta: el texto, los fragmentos de la base de
   conocimiento y los datos agregados del usuario que la respuesta requiere.
2. **Nunca se envían identificadores.** Ni el teléfono, ni el nombre, ni el email, ni ningún id
   interno que permita al proveedor vincular dos pedidos con la misma persona. Para el
   proveedor, cada pedido es anónimo.
3. **El adaptador de salida es el único lugar que arma lo que se envía.** El dominio le pasa al
   puerto los datos de la tarea, y el adaptador no agrega nada por su cuenta. Así la regla se
   verifica en un solo lugar, con un test que falla si aparece un identificador en el pedido.
4. **Criterio obligatorio para elegir el proveedor:** que por contrato no use los datos enviados
   por la API para entrenar modelos, y que los retenga el menor tiempo posible. Las condiciones se
   verifican al elegirlo, se dejan registradas en la política de privacidad, y se vuelven a
   revisar si el proveedor cambia sus términos.
5. **El LLM no accede a la base.** No recibe herramientas que lean o escriban datos, ni genera
   SQL que Platita ejecute. Devuelve una salida estructurada, como los campos de un movimiento o
   la intención de una consulta, que el adaptador valida. Con eso, el caso de uso consulta o
   escribe por los repositorios, filtrando siempre por el usuario del mensaje. Lo que el modelo
   ve de los datos del usuario es solo lo que el caso de uso decidió enviarle, según el punto 1.

## Consecuencias

### Positivas

- Si el proveedor sufre una filtración, lo expuesto son textos sin identidad asociada.
- La política de privacidad puede describir con precisión qué sale de Platita y hacia dónde.
- Cambiar de proveedor no cambia la regla: vive en el adaptador, no en el proveedor.

### Negativas y costos asumidos

- El texto de un mensaje puede contener datos identificatorios que el usuario escribió él mismo,
  como un nombre propio en "le pagué a Juan". Eso no se filtra: filtrarlo con fiabilidad es
  difícil y rompería la interpretación. La regla evita que Platita agregue identificadores, no
  que el usuario los escriba.
- Algunos proveedores con buenas condiciones de privacidad pueden ser más caros o tener menos
  opciones de modelo.
- Depender de las condiciones contractuales de un tercero obliga a revisarlas periódicamente.
- Cada tipo de consulta que el asistente sabe responder necesita un caso de uso escrito para
  ella. Una pregunta que no encaja en ninguno no se responde, aunque el modelo pudiera armar la
  consulta. Se acepta porque un SQL generado por el modelo podría leer datos de otro usuario, o
  escribir, ante un mensaje malicioso.

## Alternativas descartadas

- **Enviar el contexto completo del usuario** para mejorar las respuestas. Simplifica el
  adaptador, pero expone datos que la tarea no necesita.
- **Un modelo propio alojado por Platita.** Los datos no saldrían de la infraestructura propia,
  pero operar un modelo exige capacidad de cómputo y mantenimiento que un equipo de una persona no
  puede sostener, y la calidad de interpretación sería menor que la de un proveedor.
- **Anonimizar el texto del mensaje antes de enviarlo.** Detectar y reemplazar nombres propios o
  datos personales dentro de un texto libre es poco fiable y degrada la interpretación, que es la
  función central del producto.
- **Que el modelo genere SQL, o consulte la base con herramientas, para responder preguntas
  sobre los datos del usuario.** Cubriría cualquier pregunta sin escribir un caso de uso por
  cada una, pero la consulta generada no pasa por la validación de pertenencia al usuario, y un
  mensaje escrito para engañar al modelo podría leer datos ajenos o modificar registros.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
