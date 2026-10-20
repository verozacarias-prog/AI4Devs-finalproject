# 7. Pull requests

Todo cambio entra a la rama de la entrega por un pull request, desde una rama de trabajo. Los
tres que se muestran de cada entrega son los tres cortes verticales de una misma funcionalidad,
no tres recortes arbitrarios. Un corte vertical atraviesa base de datos, backend y frontend, y
queda funcionando de punta a punta. Ver
[convenciones de desarrollo](convenciones-de-desarrollo.md#1-cortes-verticales).

## Entrega 2

### Los tres cortes de FEAT-003

[FEAT-003](features/FEAT-003/spec.md), el registro de un gasto y de un ingreso desde el chat, es
la funcionalidad que muestra la entrega 2. Cada corte tiene sus casos aprobados en el `spec.md`,
el commit de sus tests antes que el de su implementación, y el informe de `pr-reviewer` pegado
en el pull request. La excepción la declara el #54: en tres tandas, la línea de aprobación quedó
en git después de sus tests, y dos tests cambiaron después de su commit.

| # | Corte | Pull request |
|---|---|---|
| 1 | Camino feliz: el modelo interpreta el mensaje y el movimiento queda registrado | [#49](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/49) |
| 2 | Lo que falta y los fallos del modelo: el pendiente pregunta, y un fallo no pierde el mensaje | [#50](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/50) |
| 3 | Límites de uso y observabilidad: el tope diario, la cuota de registro y las métricas del modelo | [#54](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/54) |

### El resto de la entrega

| Qué | Pull requests |
|---|---|
| [FEAT-001](features/FEAT-001/spec.md), la pantalla de cuentas | [#38](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/38) y [#39](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/39) |
| [FEAT-002](features/FEAT-002/spec.md), el chat web y el worker | [#44](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/44), [#45](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/45), [#47](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/47) y [#48](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/48) |
| El scaffold: backend, dashboard, Docker, el pipeline y CodeQL | [#18](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/18), [#24](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/24), [#28](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/28) y [#29](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/29) |
| La migración del esquema, con tests primero | [#30](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/30) y [#31](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/31) |
| Los datos de prueba y la referencia de la API, con su verificador | [#33](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/33) y [#34](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/34) |
| Tailwind CSS y shadcn/ui | [#42](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/42) |
| La elección del modelo de lenguaje | [#16](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/16) y [#17](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/17) |
| Refactors: los errores, `shared/` y la resolución de movimientos | [#32](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/32), [#52](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/52) y [#53](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/53) |
| Las claves de los datos del prompt, y el proveedor sin guardar respuestas | [#51](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/51) |
| El `/spec-drift` de todo el proyecto, con sus 34 divergencias decididas | [#65](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/65) |
| La forma de trabajo: colaborar, tests primero, qué es especificación, y qué pasa a la entrega final | [#12](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/12), [#13](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/13), [#15](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/15), [#37](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/37) y [#46](https://github.com/verozacarias-prog/AI4Devs-finalproject/pull/46) |

Las actualizaciones de dependencias las abre Dependabot y quedan fuera de esta lista.

## Definition of Done

Un pull request no se abre hasta que todo esto está. El checklist se copia en el cuerpo del PR
desde [`features/TEMPLATE/pr.md`](features/TEMPLATE/pr.md).

### Funcionalidad

- [ ] Cumple los criterios de aceptación de la historia de usuario enlazada.
- [ ] Si toca una pantalla, sus estados están implementados y se ven en las capturas: los cuatro, o tres si no muestra datos del usuario.
- [ ] El corte está completo de punta a punta: no quedó backend sin frontend ni al revés.

### Dominio

- [ ] Ninguna invariante de [`AGENTS.md`](../AGENTS.md) quedó violada.
- [ ] Los grupos de [`reglas-de-dominio.md`](reglas-de-dominio.md) que aplican están listados en la especificación y tienen un test que los cubre.
- [ ] Ningún valor que exige confirmación del usuario se resolvió con un default.

### Arquitectura

- [ ] `python3 scripts/verify_architecture.py` pasa sin errores.
- [ ] `python3 scripts/verify_api_contract.py` pasa sin errores.
- [ ] No se agregaron dependencias nuevas sin justificar por qué no alcanzaba lo instalado.
- [ ] Si hubo una decisión de arquitectura, tiene su [ADR](adr/).

### Calidad

- [ ] Tipado completo, sin `Any`.
- [ ] Tests nuevos para el comportamiento agregado, y pasan.
- [ ] Los casos del corte están aprobados en `spec.md`, y cada criterio de aceptación tiene al menos un caso. En una tarea que no es de una historia, los casos aprobados están en la descripción del pull request.
- [ ] En el backend, el commit de los tests es anterior al de la implementación ([ADR 0024](adr/0024-tests-primero-en-el-backend.md)).
- [ ] Ningún test se modificó, se deshabilitó ni se borró sin aprobación.
- [ ] Ningún texto visible al usuario escrito en el código.

### Seguridad

- [ ] Todo endpoint o caso de uso que lee o escribe datos de un usuario los limita al usuario autenticado, y tiene un test en el que otro usuario recibe `404` (ver [4. API](04-api.md)).
- [ ] Ningún dato personal se loggea sin enmascarar.
- [ ] Ningún secreto quedó en el código ni en el historial.
- [ ] Si toca el webhook, la firma se verifica antes de procesar.

- [ ] Si el cambio toca el uso del modelo —un prompt, una función de lectura, la base de conocimiento o la validación de salida—, la tabla de [seguridad de la capa de IA](seguridad-llm.md) va actualizada en este mismo pull request.

### Base de datos

- [ ] Todo cambio de esquema va en una migración de Alembic nueva.
- [ ] Ninguna migración ya aplicada fue editada.
- [ ] Las restricciones nuevas están en la base, no sólo en la aplicación.

### Documentación

- [ ] `python3 scripts/verify_docs.py` pasa sin errores.
- [ ] Si el pull request cambia un endpoint o el contrato de uno —ruta, método, campos de entrada o de salida, códigos de error—, [`04-api.md`](04-api.md) va actualizado **en este mismo pull request**.
- [ ] Si el pull request cambia el esquema de la base de datos, [`03-modelo-de-datos.md`](03-modelo-de-datos.md) va actualizado en este mismo pull request.
- [ ] Si el pull request cambia una regla de negocio, [`reglas-de-dominio.md`](reglas-de-dominio.md) va actualizado en este mismo pull request.
- [ ] `/spec-drift` corrió antes del último commit del corte y no quedó ninguna divergencia sin reportar.
- [ ] Si el comportamiento cambió respecto de lo documentado, la divergencia se resolvió según [`AGENTS.md`](../AGENTS.md) sección 10, no ajustando la documentación al código.

### Revisión

- [ ] El agente `pr-reviewer` corrió sobre la última versión del cambio, y su informe está pegado en el pull request ([ADR 0022](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md)).
- [ ] La aprobación y el merge los hace una persona.

## Entrega final

Los tres cortes de la funcionalidad de la entrega final se enlazan acá cuando estén integrados.

| # | Corte | Pull request |
|---|---|---|
| 1 | Camino feliz y carga | `[pendiente]` |
| 2 | Errores, estado vacío y confirmaciones | `[pendiente]` |
| 3 | Observabilidad, multimoneda y accesibilidad | `[pendiente]` |
