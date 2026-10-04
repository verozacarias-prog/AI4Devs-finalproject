# 0022 — Cada pull request lo revisa un agente definido en el repositorio, a mano

- Estado: Aceptada
- Fecha: 2026-10-04

## Contexto

El proyecto lo escribe una sola persona, con asistentes de IA. Nadie más lee un cambio antes de
que se integre, y quien lo escribió, persona o asistente, lo revisa con el mismo contexto con
que lo hizo: ve lo que quiso hacer, no lo que quedó.

Los controles automáticos cubren lo que se responde con sí o no
([ADR 0021](0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md)). Queda afuera lo que
pide criterio: una regla de negocio contradicha, lógica de negocio dentro de un adaptador, un
dato identificatorio que termina en un registro.

La [hoja de ruta](../hoja-de-ruta.md) tenía abierta la decisión de si definir subagentes, a la
espera de una tarea que lo justificara. Un subagente corre en su propio contexto, y eso, que
para otras tareas es un costo, acá es lo que se busca.

## Decisión

1. **Un agente revisor definido en el repositorio,** en `.claude/agents/pr-reviewer.md`. Corre
   en un contexto propio, separado del de quien escribió el cambio, y sus criterios están
   versionados en ese archivo.
2. **Se corre a mano, antes de pedir el merge.** No lo dispara ningún hook ni ningún flujo.
3. **Qué revisa:**
   - la regla hexagonal, más allá de lo que detecta el verificador;
   - que el cambio no contradiga las [reglas de dominio](../reglas-de-dominio.md);
   - que nada identificatorio viaje al proveedor ni termine en un registro
     ([ADR 0013](0013-datos-minimos-al-proveedor-de-llm.md));
   - que el cambio traiga sus tests;
   - que la documentación refleje lo que cambió;
   - y, si el cambio toca el uso del modelo, que la tabla de
     [seguridad de la capa de IA](../seguridad-llm.md) esté actualizada.
4. **El revisor solo lee e informa.** No edita, no hace commit y no hace merge. Tiene
   herramientas de lectura y nada más.
5. **La plantilla del pull request lo recuerda,** con una casilla y un lugar para pegar el
   informe. Es la plantilla que ya existe, [`features/TEMPLATE/pr.md`](../features/TEMPLATE/pr.md).
6. **La aprobación final es de una persona.** El merge lo hace siempre una persona. Un asistente
   hace commit solo cuando una persona se lo pide.

## Consecuencias

### Positivas

- Cada cambio tiene una segunda lectura que no arrastra los supuestos de quien lo escribió.
- Los criterios se discuten y se corrigen en un pull request, como el resto del repositorio.
- No hace falta ninguna credencial en el pipeline.
- Cierra la decisión abierta sobre subagentes con una tarea concreta, no con una estructura
  armada por si acaso.

### Negativas y costos asumidos

- Depende de que la persona se acuerde de correrlo. La casilla lo recuerda, pero no lo obliga.
- El informe se pega a mano, y nada comprueba que corresponda a la última versión del cambio.
- El revisor puede equivocarse en los dos sentidos: marcar algo que está bien, o dejar pasar
  algo que está mal. Por eso no reemplaza la lectura de la persona.
- Cada corrida cuesta tokens, porque el agente lee desde cero las reglas y el cambio.

## Alternativas descartadas

- **Un hook de git que lo corra solo:** cuándo se hace commit o push depende de cómo trabaje
  cada persona, y una revisión que tarda minutos en cada commit termina salteada.
- **Un revisor que corra en GitHub al abrir el pull request:** no depende de la memoria de
  nadie, pero obliga a guardar la credencial del proveedor en el pipeline, que hoy no guarda
  ningún secreto.
- **Revisar en la misma sesión que escribió el cambio:** no cuesta nada extra, pero es la
  lectura con el mismo contexto que se quiere evitar.
- **Un command en vez de un agente:** un command corre en el contexto de la conversación en
  curso. Sirve para `/spec-drift`, que compara dos cosas escritas, y no para una revisión que
  necesita partir de cero.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
