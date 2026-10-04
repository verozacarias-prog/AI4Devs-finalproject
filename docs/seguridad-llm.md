# Seguridad de la capa de IA

Cómo responde Platita a cada riesgo del
[OWASP Top 10 para aplicaciones LLM](https://genai.owasp.org/llm-top-10/), edición 2025, que es
la vigente. La lista se verificó en el sitio de OWASP el 2026-10-04.

Este documento no decide nada: cruza la lista con decisiones que ya están en los ADR y en las
reglas de dominio, y dice qué falta. Si un cambio toca el uso del modelo —un prompt, una función
de lectura, la base de conocimiento, la validación de salida—, la tabla se actualiza en el mismo
pull request, y el [agente revisor](adr/0022-revision-de-pull-requests-con-un-agente-del-repositorio.md)
lo comprueba.

## 1. Las diez categorías

| Categoría | Estado | Cómo la cubre Platita | Dónde está | Qué falta |
|---|---|---|---|---|
| LLM01 Inyección de prompts | Cubierta | El modelo no escribe ni puede pedir datos de otro usuario, así que una orden escondida no tiene con qué hacer daño. Además, todo dato que entra al prompt va delimitado, y la salida se valida en código | [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), puntos 5, 6, 8, 9 y 10 | Correr los casos de inyección en la evaluación de proveedores |
| LLM02 Divulgación de información sensible | Cubierta | Al proveedor no le llega ningún identificador, solo lo necesario para la tarea, y por contrato no entrena con eso. Los registros y la tabla de llamadas no guardan contenido | [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), puntos 1 a 4 y 7 · [ADR 0023](adr/0023-observabilidad-de-las-llamadas-al-llm-registros-y-eventos-de-seguridad.md) | Un nombre que el usuario escribe en su mensaje no se filtra. Es un costo asumido |
| LLM03 Cadena de suministro | Parcial | Los adaptadores usan el SDK del proveedor, sin framework. El pipeline revisa las dependencias y las actualiza cada semana, y las acciones van fijadas por hash. El proveedor se elige con una evaluación | [ADR 0020](adr/0020-sin-framework-de-orquestacion-de-ia.md) · [ADR 0021](adr/0021-una-imagen-docker-compose-y-pipeline-de-la-aplicacion.md) · [ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md) | El escaneo de la imagen y su inventario de componentes, que van en la entrega final. Revisar qué trae el paquete de particionado al instalarlo |
| LLM04 Envenenamiento de datos y del modelo | Cubierta | Platita no entrena ni ajusta ningún modelo. La base de conocimiento la cura el producto y la carga quien opera, con un comando. Ningún usuario puede sumarle contenido | [ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md), puntos 6 y 8 | Nada de diseño |
| LLM05 Manejo inseguro de la salida | Regla nueva | El chat web muestra la respuesta del modelo como texto y nunca como HTML. La salida estructurada la valida el adaptador, el modelo no genera SQL, y una respuesta no puede traer enlaces que no sean del dashboard | [ADR 0016](adr/0016-sesion-de-servidor-en-el-mismo-origen.md), punto 10 · [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), puntos 5 y 10 | Implementarla con su test, y la política de contenido del dashboard |
| LLM06 Exceso de permisos | Cubierta | El modelo no recibe herramientas que escriban. Para leer tiene un conjunto cerrado de funciones, que filtran por el usuario del mensaje en el código. Todo registro lo confirma el usuario | [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), puntos 5 y 6 · [reglas de dominio § 1 y § 17](reglas-de-dominio.md) | Nada de diseño |
| LLM07 Fuga del prompt de sistema | Regla nueva | El prompt de sistema no contiene secretos ni datos de ningún usuario: se escribe asumiendo que puede filtrarse. Ninguna garantía depende de que el modelo lo obedezca | [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), punto 12 | Implementarla con su test |
| LLM08 Debilidades en vectores y embeddings | Cubierta | La base de conocimiento es contenido compartido, no datos de usuarios, así que una búsqueda no puede traer algo ajeno. Solo se recuperan documentos vigentes. Al proveedor de embeddings le vale la misma regla de privacidad que al del modelo | [ADR 0019](adr/0019-base-de-conocimiento-embeddings-ingesta-y-recuperacion.md) · [ADR 0004](adr/0004-postgres-con-pgvector-como-unico-almacen.md) | Nada de diseño |
| LLM09 Desinformación | Parcial | Los datos del usuario salen siempre de una función, y el código comprueba cada cifra de la respuesta y rehace las cuentas. Un consejo cita su fuente por nombre y fecha, y uno de decisión tiene una estructura fija | [Reglas de dominio § 17 y § 18](reglas-de-dominio.md#17-preguntas-sobre-los-propios-datos) · [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md), punto 10 | Se construye con las consultas, en la entrega final. Que un consejo sea correcto depende de quien cura el contenido |
| LLM10 Consumo sin límite | Parcial | Solo escriben los números habilitados. Cada usuario tiene tres cuotas y un tope diario total, y el proveedor, un tope mensual de gasto. Una pregunta admite como mucho 5 llamadas a funciones | [Reglas de dominio § 11, § 12 y § 17](reglas-de-dominio.md#12-límites-de-uso-del-asistente) · [ADR 0018](adr/0018-clasificacion-inicial-y-memoria-de-conversacion.md) | Un tope de tokens por mensaje, cuotas menores para cuentas nuevas y una alerta de gasto diario. Están en la [hoja de ruta](hoja-de-ruta.md#decisiones-abiertas) |

## 2. Auditoría antes de cada entrega

El command [`/security-audit`](../.claude/commands/security-audit.md) analiza todo el backend
contra el OWASP Top 10 web y contra el de aplicaciones LLM. Muestra un hallazgo por vez, del más
crítico al menos, con el código vulnerable, el riesgo y la corrección.

Se corre antes de cada entrega, no en cada pull request: recorre el backend entero, y lo que
cambia en un pull request ya lo mira el agente revisor. No modifica nada.
