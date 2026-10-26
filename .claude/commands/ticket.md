---
description: Recorre el flujo de trabajo de un corte, de la issue al pull request, con una pausa en cada punto que decide una persona. Usar al empezar un corte de una historia o una tarea, con el número de sus issues y el del corte.
argument-hint: <issues> c<corte>, por ejemplo 70 71 c2
---

Recorré el flujo de [cómo colaborar](../../docs/como-colaborar.md) para las issues y el corte que se
te indican. Los números son las issues, y el corte va con una `c` delante, como `c2`; una tarea
no tiene cortes y lleva solo sus issues.

Lo que manda es `AGENTS.md`: este comando lo ordena, no lo reemplaza. Cada **pausa** es un punto
en el que te detenés y esperás a la persona. No la saltes aunque el paso siguiente parezca
obvio, y no tomes un "dale" de una pausa como permiso para la siguiente. Ningún commit ni push
se hace sin que la persona lo pida, sea del tipo que sea, y ninguna revisión se lanza sin que la
pida: una verificación se corre cuando la persona decide.

Las dudas se preguntan de a una, con una escena concreta de uso y no con el nombre técnico, y
con una recomendación. `gh` se usa con `unset GITHUB_TOKEN`.

## 1. Arrancar

- Leé cada issue con `gh issue view`, la historia de usuario de la que sale y lo que la
  [sección 12 de `AGENTS.md`](../../AGENTS.md#12-qué-leer-antes-de-qué) pide para ese tipo de cambio.
  Si toca movimientos, cuentas, presupuestos o categorías, usá el skill `domain-rules`.
- Creá la rama desde la rama de la entrega, `hu<N>-c<corte>-<tema>` o `tarea-<tema>`, y pasá la
  tarjeta de cada issue a "En curso".

## 2. Especificar

- En una historia, escribí o actualizá `docs/features/FEAT-XXX/spec.md`, y `ui_contract.md` si
  hay pantalla, desde [`docs/features/TEMPLATE/`](../../docs/features/TEMPLATE/).
- Si la especificación y el código no coinciden, o dos documentos de `docs/` se contradicen,
  frená y reportalo: la decisión es de la persona.

## 3. Proponer los casos del corte

Proponé los casos del corte, cada uno con qué prueba, su tipo y de qué criterio sale. En una
tarea no hay `spec.md`: proponé cada caso en una línea, con su resultado esperado, o decí que no
hay lógica que probar. Los casos aprobados de una tarea van en la descripción del pull request.

**Pausa.** La persona los aprueba. En una historia, la línea de aprobación de `spec.md` la
escribe ella: no la completes vos.

## 4. Escribir los tests y verlos fallar

Escribí los tests tal como se aprobaron, sin sumar ni cambiar casos, y corrélos. Mostrá cuáles
fallan y por qué, y cuáles ya pasan y por qué: un test que pasa antes de implementar se dice, no
se esconde.

**Pausa.** El commit `test(alcance): …`, solo si la persona lo pide.

## 5. Implementar

Implementá lo mínimo para que pasen y corré todos los controles de la
[sección 11 de `AGENTS.md`](../../AGENTS.md#11-comandos-de-verificación) que el cambio toca. Si un test
parece mal, frená y mostralo: no se modifica sin aprobación. La documentación que el cambio
afecta entra en la misma rama.

**Pausa.** El commit `feat(alcance): …`, y los `docs(alcance): …` de la documentación, solo si
la persona los pide. Si cambió `docs/`, antes `cd site && npm run build`.

## 6. Cerrar el corte

**Pausa.** Preguntá si corrés `/spec-drift`, y `/ui-states` si el cambio tiene pantalla. Lo que
encuentren se resuelve con la persona.

## 7. Probar a mano

Dale los pasos exactos para verlo andar como lo usaría una persona: Compose, los datos de
prueba, el script de `scripts/` si hace falta y qué mirar. Decí también qué no se puede probar a
mano y qué test lo cubre.

**Pausa.** La persona prueba. Lo que surja se corrige en la misma rama. Si pide un test nuevo
o cambiar uno, es un caso nuevo: vuelve al paso 3, se propone, se aprueba y recién ahí se
escribe.

## 8. Revisar

**Pausa.** Preguntá si corrés el agente `pr-reviewer` sobre la rama. Resumí su veredicto con
los hallazgos por gravedad y resolvé con la persona qué se corrige ahora y qué queda anotado. Una
corrección que pide un test nuevo vuelve al paso 3, como en el paso 7.

## 9. Entregar

- **Pausa.** Subí la rama solo si la persona lo pide.
- Escribí la descripción desde [`pr.md`](../../docs/features/TEMPLATE/pr.md), con el resumen de
  `pr-reviewer` en su sección "Revisión", en `../pr-platita/<rama>.md`, y copiala al
  portapapeles. Un corte que no es el último lleva `Parte de #N`; el último, `Closes #N` de
  cada issue y también de la historia de usuario.
- **Pausa.** La persona abre el pull request y lo integra: vos no lo abrís ni hacés merge.
- Cuando lo abre, pasá las tarjetas a "En revisión". Cuando lo integra, confirmá que las issues
  que cerró quedaron en "Hecho".
