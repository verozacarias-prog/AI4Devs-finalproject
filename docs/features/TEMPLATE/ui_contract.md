# Contrato de UI — FEAT-XXX · <pantalla>

- **Historia de usuario:** [HU-X](../../05-historias-de-usuario.md)
- **Especificación:** [spec.md](spec.md)
- **Se escribe:** antes del corte vertical 1, junto con la especificación

Este documento vive separado de los componentes a propósito. Los tokens y la máquina de estados
pertenecen al contrato de la pantalla, no a la tecnología que la renderiza: cuando exista la
aplicación móvil, reutiliza este contrato y sólo cambia la capa de render. Si estas decisiones
vivieran dentro de los componentes, habría que reconstruirlas leyendo código.

## Componentes

Qué se usa y qué se crea. Si se crea uno nuevo, decir por qué no alcanzaba uno existente.

| Componente | ¿Existe o es nuevo? | Para qué |
|---|---|---|

## Tokens del Design System

Sólo tokens, nunca valores sueltos. Un color, un espaciado o un tamaño escrito a mano en el
componente es una decisión que la app móvil no puede heredar.

| Uso | Token |
|---|---|

## Máquina de estados

Los cuatro estados son obligatorios. Ver
[convenciones de desarrollo](../../convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla).

| Estado | Qué lo dispara | Qué muestra | Cómo se sale |
|---|---|---|---|
| Cargando | | | |
| Con contenido | | | |
| Vacío | | | |
| Error | | | |

Recordá que vacío y error no son el mismo estado: una consulta que funcionó y no devolvió datos
está vacía, no falló.

## Datos que consume

Qué endpoint de [`04-api.md`](../../04-api.md) alimenta la pantalla, y qué campos usa.

## Accesibilidad

- [ ] Todo control tiene nombre accesible.
- [ ] El contraste cumple el mínimo de la guía del Design System.
- [ ] La pantalla se puede operar sólo con teclado.
- [ ] Los montos y porcentajes se anuncian con su moneda y su unidad, no como número suelto.

## Textos

Ningún texto visible al usuario se escribe en el componente. Listar acá las claves y su contenido
en español.
