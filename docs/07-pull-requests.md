# 7. Pull requests

`No aplica a esta entrega — es documentación previa al código. Se completa en la Entrega final con 3 PRs reales enlazados.`

Los tres pull requests de la entrega final son los tres cortes verticales de una misma
funcionalidad, no tres recortes arbitrarios. Un corte vertical atraviesa base de datos, backend
y frontend, y queda funcionando de punta a punta. Ver
[convenciones de desarrollo](convenciones-de-desarrollo.md#1-cortes-verticales).

## Definition of Done

Un pull request no se abre hasta que todo esto está. El checklist se copia en el cuerpo del PR
desde [`features/TEMPLATE/pr.md`](features/TEMPLATE/pr.md).

### Funcionalidad

- [ ] Cumple los criterios de aceptación de la historia de usuario enlazada.
- [ ] Si toca una pantalla, los cuatro estados están implementados y se ven en las capturas.
- [ ] El corte está completo de punta a punta: no quedó backend sin frontend ni al revés.

### Dominio

- [ ] Ninguna invariante de [`AGENTS.md`](../AGENTS.md) quedó violada.
- [ ] Los grupos de [`reglas-de-dominio.md`](reglas-de-dominio.md) que aplican están listados en la especificación y tienen un test que los cubre.
- [ ] Ningún valor que exige confirmación del usuario se resolvió con un default.

### Arquitectura

- [ ] `python3 scripts/verify_architecture.py` pasa sin errores.
- [ ] No se agregaron dependencias nuevas sin justificar por qué no alcanzaba lo instalado.
- [ ] Si hubo una decisión de arquitectura, tiene su [ADR](adr/).

### Calidad

- [ ] Tipado completo, sin `Any`.
- [ ] Tests nuevos para el comportamiento agregado, y pasan.
- [ ] Ningún texto visible al usuario escrito en el código.

### Seguridad

- [ ] Ningún dato personal se loggea sin enmascarar.
- [ ] Ningún secreto quedó en el código ni en el historial.
- [ ] Si toca el webhook, la firma se verifica antes de procesar.

### Base de datos

- [ ] Todo cambio de esquema va en una migración de Alembic nueva.
- [ ] Ninguna migración ya aplicada fue editada.
- [ ] Las restricciones nuevas están en la base, no sólo en la aplicación.

### Documentación

- [ ] `python3 scripts/verify_docs.py` pasa sin errores.
- [ ] Si el comportamiento cambió respecto de lo documentado, la divergencia se resolvió según [`CLAUDE.md`](../CLAUDE.md) sección 10, no ajustando la documentación al código.

## Los tres pull requests

Se enlazan acá en la entrega final.

| # | Corte | Pull request |
|---|---|---|
| 1 | Camino feliz y carga | `[pendiente]` |
| 2 | Errores, estado vacío y confirmaciones | `[pendiente]` |
| 3 | Observabilidad, multimoneda y accesibilidad | `[pendiente]` |
