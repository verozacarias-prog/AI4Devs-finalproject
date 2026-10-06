# 0024 — Tests primero en el backend, con los casos aprobados por una persona

- Estado: Aceptada
- Fecha: 2026-10-06

## Contexto

Platita se escribe con asistentes de IA. Hasta acá la especificación pedía que cada cambio
trajera sus tests y que pasaran, sin decir cuándo se escriben. El plan de pruebas de una
funcionalidad se escribía antes del corte 2, es decir, después de programar el camino feliz.

Un asistente, si nadie se lo impide, escribe primero el código y después los tests, o las dos
cosas a la vez. Esos tests confirman lo que el código hace, no lo que debería hacer. Ante un
test que falla, además, tiende a cambiar el test en vez del código. El módulo de testing del
máster lo pone como regla: lo que define el comportamiento esperado lo escribe o lo aprueba una
persona, y la implementación se delega, nunca al revés.

En Platita un error de lógica es plata que no existe: un saldo mal calculado o un gasto imputado
al presupuesto equivocado. La entrega 2 no exige tests, y la final exige unitarios, de
integración y al menos uno de punta a punta.

## Decisión

1. **En el backend, el test se escribe antes que el código.** Vale para el dominio, los casos
   de uso y los adaptadores, incluidas las restricciones de la base. Primero el test, se lo ve
   fallar, y recién después se escribe lo mínimo para que pase. Se refactoriza solo con todo en
   verde.
2. **En las pantallas, los tests son obligatorios y van después.** Primero se arma la pantalla;
   con ella a la vista se aprueban los casos de sus cuatro estados, y después se escriben sus
   tests, dentro del mismo corte. Las reglas de orden de los puntos 1 y 7 no les aplican.
3. **Los tests de punta a punta se escriben con la pantalla ya construida,** en la entrega
   final. Uno es fijo: el flujo principal de
   [2.6](../02-arquitectura.md#26-tests). Si se suman otros, se eligen por riesgo.
4. **Los casos de prueba los aprueba una persona.** Antes de cada corte, `qa_plan.md` lista los
   casos de ese corte: de qué criterio de aceptación sale cada uno, con qué entrada y qué
   resultado esperado. El asistente puede proponerlos; no escribe ningún test hasta que una
   persona los aprueba, y los escribe tal como quedaron aprobados. La línea de aprobación la
   escribe la persona: el asistente no la completa nunca.

   Una tarea que no es de una historia, como el scaffold o un arreglo, no tiene carpeta de
   funcionalidad. Sigue la misma regla con un lugar más liviano: el asistente propone los
   casos, la persona los aprueba antes de que se escriba ningún test, y quedan en la
   descripción del pull request, en la misma tabla. Lo que no tiene lógica que probar, como un
   Dockerfile o un archivo de configuración, no lleva casos, y el pull request lo dice.
5. **Cada criterio de aceptación tiene un identificador,** y cada caso y cada test dicen de cuál
   salen.
6. **Un test no se modifica, no se deshabilita y no se borra sin la aprobación de una persona.**
   Si al implementar un test resulta estar mal, el asistente frena y lo muestra.
7. **El orden queda en el historial.** Cada corte que toca el backend tiene dos commits:
   primero el de los tests, hecho con esos tests fallando, y después el de la implementación.
   El agente revisor comprueba que el commit de implementación tenga antes el de sus tests. Un
   corte que no toca el backend tiene un solo commit. Los pull requests se integran con un
   commit de merge, no aplastados en uno, para que ese orden no se pierda.
8. **Un hook corre los tests unitarios después de cada edición del asistente** en `backend/`, e
   informa el resultado. No bloquea: en la fase en rojo los tests fallan a propósito. Se
   configura cuando exista el código.
9. **La cobertura no es un objetivo.** No se exige un porcentaje. Lo que se exige es que cada
   criterio de aceptación y cada invariante en riesgo tengan su test.

## Consecuencias

### Positivas

- Lo que se prueba lo decide una persona, leyendo casos en castellano y no código de tests.
- Un test que se vio fallar prueba algo: no puede estar confirmando un error del código.
- Cualquiera comprueba el orden mirando el historial, sin confiar en la palabra del asistente.
- La entrega final llega con los tests unitarios y de integración ya escritos.
- De cada test se sabe qué criterio de aceptación protege.

### Negativas y costos asumidos

- Cada corte arranca más lento: antes de la primera línea de código hay que aprobar los casos
  y escribir los tests. Pesa sobre la entrega 2, que no pide tests.
- Cada corte pasa de un commit a dos, y el commit de los tests deja la rama de trabajo con
  tests en rojo. Por eso el pull request se abre recién con el corte en verde.
- La aprobación de los casos depende de una persona, y sin ella el trabajo no avanza.
- Un caso que aparece mientras se implementa obliga a volver al plan de pruebas y aprobarlo.
- En las pantallas el orden no queda garantizado: solo que los tests existen.
- El hook hace más lenta cada edición.

## Alternativas descartadas

- **Tests primero en todo, pantallas incluidas:** una sola regla, pero en una pantalla recién
  se sabe qué probar cuando está armada, y los tests escritos antes se reescriben.
- **Tests primero solo en el dominio:** más rápido, pero los adaptadores de la base, donde
  viven las restricciones, quedarían sin un test previo.
- **Que una persona revise cada test antes de implementar:** el control más fuerte, y el más
  lento: son decenas de tests en código por historia. Revisar los casos cubre lo que importa.
- **Que el asistente proponga y escriba los tests, y se vean en el pull request:** es lo que la
  decisión busca evitar.
- **Exceptuar de la regla a las tareas que no son de una historia:** más rápido, pero las
  migraciones, con sus restricciones, entran por una tarea y son lo que más conviene probar
  antes.
- **Exigir una carpeta de funcionalidad para todo código de backend:** una sola regla, a
  cambio de escribir una especificación para un scaffold o para un arreglo de una línea.
- **Dejar el orden librado a una regla escrita,** sin commits separados: no deja evidencia.
- **Exigir un porcentaje de cobertura:** empuja a escribir tests que ejecutan código sin
  comprobar nada.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
