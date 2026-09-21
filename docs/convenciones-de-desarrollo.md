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
tres cortes verticales, y cada uno termina en un commit propio.

| Corte | Qué entra | Commit |
|---|---|---|
| 1 | Camino feliz completo y estado de carga | `feat(xxx): implementar camino feliz` |
| 2 | Estados vacío y de error, reintento, y lo que exija confirmación del usuario | `feat(xxx): agregar manejo de errores y estado vacío` |
| 3 | Enmascarado de logs, multimoneda, accesibilidad y observabilidad | `feat(xxx): agregar observabilidad y accesibilidad` |

Los tres commits de una funcionalidad son los tres pull requests que pide
[7. Pull requests](07-pull-requests.md).

**Por qué el corte 2 existe por separado.** En Platita el camino no feliz *es* el producto. La
[HU3](05-historias-de-usuario.md) es casi enteramente eso: falta la cuenta, falta confirmar el
presupuesto, el movimiento queda como `PENDING_TRANSACTION`, el asistente pregunta, recuerda y
expira. Si entra junto con el camino feliz, se recorta. Con su propio commit, no.

**Gate para cerrar un corte:** compila, los tests pasan, el linter pasa, no hay strings visibles
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
| `spec.md` | Antes del corte 1 | Alcance, criterios de aceptación, reglas de dominio que aplican y los cuatro estados |
| `ui_contract.md` | Antes del corte 1, si hay pantalla | Componentes, tokens del Design System, máquina de estados y accesibilidad |
| `qa_plan.md` | Antes del corte 2 | Camino feliz, casos límite, errores, y un test por invariante en riesgo |
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
