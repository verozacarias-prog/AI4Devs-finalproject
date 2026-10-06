# Convenciones de desarrollo

Cómo se construye una funcionalidad en Platita: en qué orden, con qué cortes y qué tiene que
estar terminado en cada uno. No describe el producto ni el dominio: describe el método.

Las reglas de negocio están en [`reglas-de-dominio.md`](reglas-de-dominio.md). Las reglas que un
asistente de IA rompe por defecto están en [`AGENTS.md`](../AGENTS.md).

## 1. Cortes verticales

**Qué es un corte vertical.** Es un recorte de una funcionalidad que atraviesa todas las capas
—base de datos, backend y frontend o mensaje de WhatsApp— y queda funcionando de punta a punta.
Lo contrario es cortar por capa: primero todas las tablas, después todos los endpoints, después
todas las pantallas.

La diferencia está en qué tenés cuando terminás el primer tramo:

| Forma de cortar | Al terminar el primer tramo tenés |
|---|---|
| Por capa | Tablas. No se ve nada todavía |
| Vertical | Una pantalla que muestra un presupuesto real |

Cortar por capa parece más ordenado y es la trampa más común en un proyecto individual: si el
último tramo se complica, llegás a la entrega con una base de datos impecable, una API completa y
ninguna pantalla. Un corte vertical incompleto siempre es mejor que una capa perfecta aislada,
porque se puede mostrar y se puede probar.

**Los tres cortes.** Una funcionalidad no se implementa de una sola vez ni por capas. Se parte en
tres cortes verticales, y cada uno termina en dos commits: primero el de sus tests y después el
de su implementación.

| Corte | Qué entra | Commit de los tests | Commit de la implementación |
|---|---|---|---|
| 1 | Camino feliz completo y estado de carga | `test(xxx): casos del camino feliz` | `feat(xxx): implementar camino feliz` |
| 2 | Estados vacío y de error, reintento, y lo que exija confirmación del usuario | `test(xxx): casos de error y estado vacío` | `feat(xxx): agregar manejo de errores y estado vacío` |
| 3 | Enmascarado de logs, multimoneda, accesibilidad y observabilidad | `test(xxx): casos de observabilidad y accesibilidad` | `feat(xxx): agregar observabilidad y accesibilidad` |

**Formato del mensaje de commit.** `tipo(alcance): qué cambia`, en español. Los tipos son
`feat`, `fix`, `docs`, `test` y `chore`. El alcance es la funcionalidad, y se puede omitir
cuando el cambio no es de una sola, como `docs: guía para colaborar`.

Los tres cortes de una funcionalidad son los tres pull requests que pide
[7. Pull requests](07-pull-requests.md).

**Tests primero.** En el backend el test se escribe antes que el código ([ADR 0024](adr/0024-tests-primero-en-el-backend.md)).
Cada corte sigue este orden:

1. **Casos.** Antes de empezar el corte, `qa_plan.md` lista sus casos de prueba: de qué criterio
   de aceptación sale cada uno, la entrada y el resultado esperado. Un asistente puede
   proponerlos. Una persona los aprueba, y sin eso no se escribe ningún test.
2. **Rojo.** Se escriben los tests del backend tal como quedaron aprobados, se corren y se los
   ve fallar. Ese es el commit de los tests.
3. **Verde.** Se implementa lo mínimo para que pasen, de a un caso, empezando por el más simple.
4. **Refactor.** Se ordena el código con todos los tests en verde. Ese es el commit de la
   implementación.

Tres reglas acompañan ese orden:

- **Un test no se modifica, no se deshabilita y no se borra sin la aprobación de una persona.**
  Si al implementar un test resulta estar mal, el asistente frena y lo muestra; no lo ajusta
  para que pase.
- **Un caso nuevo vuelve al plan.** Si aparece mientras se implementa, se suma a `qa_plan.md`, se
  aprueba, y su test se escribe antes que su código.
- **El pull request se abre con el corte en verde.** El commit de los tests deja la rama de
  trabajo en rojo a propósito; la rama de la entrega no lo ve nunca así.

Qué va primero según la capa:

| Capa | Tipo de test | Cuándo se escribe |
|---|---|---|
| Dominio y casos de uso | Unitario, con dobles de los puertos | Antes que el código |
| Adaptadores y restricciones de la base | De integración, contra PostgreSQL real | Antes que el código |
| Pantallas | De componente, uno por cada uno de los cuatro estados | En el mismo corte, antes o después de armar la pantalla |
| Flujo completo | De punta a punta | En la entrega final, con la pantalla ya construida |

No se exige un porcentaje de cobertura. Se exige que cada criterio de aceptación y cada
invariante en riesgo tengan su test, y que cada test diga de qué criterio sale.

**Por qué el corte 2 existe por separado.** En Platita el camino no feliz *es* el producto. La
[HU3](05-historias-de-usuario.md) es casi enteramente eso: falta la cuenta, falta confirmar el
presupuesto, el movimiento queda como `PENDING_TRANSACTION`, el asistente pregunta, recuerda y
expira. Si entra junto con el camino feliz, se recorta. Con sus propios commits, no.

**Gate para cerrar un corte:** compila, el commit de los tests está antes que el de la
implementación, los tests pasan, el linter pasa, no hay strings visibles
al usuario escritos en el código, ninguna invariante de [`AGENTS.md`](../AGENTS.md) quedó
violada, y `/spec-drift` no reporta diferencias sobre lo que tocaste. Todo eso **antes** del
último commit del corte, no después.

## 2. Los cuatro estados de una pantalla

Toda pantalla del dashboard tiene cuatro estados, y los cuatro se implementan y se testean:

| Estado | Cuándo | Qué muestra |
|---|---|---|
| **Cargando** | Hay una consulta en curso | Indicador de carga, nunca una pantalla en blanco |
| **Con contenido** | La consulta trajo datos | Los datos |
| **Vacío** | La consulta funcionó y no hay nada que mostrar | Explicación de por qué está vacío y qué hacer |
| **Error** | La consulta falló | Qué pasó y una acción de reintento |

**Vacío y error no son el mismo estado**, y confundirlos es el error habitual. En Platita la
diferencia es de dominio, no cosmética:

- Un **presupuesto confirmado sin movimientos todavía** está vacío, y es correcto: el usuario
  armó el período y aún no gastó nada. Mostrarle un error sería mentirle.
- Un **usuario sin ninguna cuenta dada de alta** está vacío, y el estado tiene que llevarlo a
  crear la primera, que es el paso que le falta.
- Que **falle la consulta del saldo** es un error, y el saldo calculado no se puede mostrar
  parcial: o está completo o no está.

Esta regla aplica igual a la futura aplicación móvil: la máquina de estados es del contrato de
la pantalla, no de la tecnología que la renderiza.

## 3. Artefactos de una funcionalidad

Cada funcionalidad tiene su carpeta en `docs/features/FEAT-XXX/`, creada copiando
[`features/TEMPLATE/`](features/TEMPLATE/):

| Archivo | Cuándo se escribe | Para qué |
|---|---|---|
| `spec.md` | Antes del corte 1 | Alcance, criterios de aceptación numerados, reglas de dominio que aplican y los cuatro estados |
| `ui_contract.md` | Antes del corte 1, si hay pantalla | Componentes, tokens del Design System, máquina de estados y accesibilidad |
| `qa_plan.md` | Antes de cada corte, los casos de ese corte | Los casos de prueba con su criterio, su entrada y su resultado esperado, y un test por invariante en riesgo. Se aprueba antes de escribir tests |
| `pr.md` | Al cerrar cada corte | Cuerpo del pull request, con el Definition of Done |

Son cuatro y no siete a propósito. Se dejó afuera el registro de riesgos, que para un proyecto
individual es ceremonia: lo que aportaría ya vive en `spec.md`. El contrato de UI **sí** está
separado, y no por simetría: los tokens y la máquina de estados pertenecen al contrato de la
pantalla y no a la tecnología que la renderiza, así que la aplicación móvil prevista los
reutiliza tal cual. Si vivieran dentro de los componentes del dashboard, habría que
reconstruirlos leyendo código.

La carpeta va sin número, porque la serie de `docs/` está cerrada en 08.

## 4. Relación con los otros documentos

- Qué debe hacer el sistema → [`reglas-de-dominio.md`](reglas-de-dominio.md)
- Qué se le promete al usuario en cada pantalla → [`05-historias-de-usuario.md`](05-historias-de-usuario.md)
- Cómo está construido → [`02-arquitectura.md`](02-arquitectura.md)
- Cómo se escribe la documentación → [`08-convenciones-de-documentacion.md`](08-convenciones-de-documentacion.md)
