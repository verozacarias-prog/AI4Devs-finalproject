# Pull request — FEAT-XXX · <título>

- **Corte vertical:** 1 (camino feliz) | 2 (errores y vacío) | 3 (observabilidad)
- **Historia de usuario:** [HU-X](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)

## Qué cambia

Dos o tres líneas. Qué hace el sistema después de este PR que antes no hacía.

## Cómo probarlo

Pasos concretos para reproducir el comportamiento.

## Tests primero

- **Casos aprobados:** enlace a la sección del corte en [qa_plan.md](qa_plan.md), con quién los aprobó y cuándo.
  En una tarea que no es de una historia, la tabla de casos va acá mismo, con caso, entrada y
  resultado esperado, y quién la aprobó; o "sin lógica que probar", si es el caso.
- **Commit de los tests:** `<hash>`, anterior al de la implementación | no aplica: el corte no toca el backend.
- **Tests modificados o borrados después de ese commit:** ninguno | cuáles, y quién lo aprobó.

## Capturas

Para cambios de dashboard, una por estado de pantalla.

## Definition of Done

Ver el checklist completo en
[7. Pull requests](../../07-pull-requests.md#definition-of-done).

## Revisión con el agente

- [ ] Corrí el agente `pr-reviewer` sobre la última versión de este cambio.

Informe del revisor:

```text
Pegar acá el informe completo.
```

## Decisiones tomadas

Si hubo una decisión de arquitectura, enlazar el ADR. Si no hubo, decir "ninguna".
