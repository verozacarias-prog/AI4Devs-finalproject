# Notas de Platita para `/fastapi-harness:ticket`

Lo propio de Platita en cada paso del comando. Lo que manda es `AGENTS.md`.

- **El flujo** es el de [cómo colaborar](../../docs/como-colaborar.md).
- **`gh`** se usa siempre con `unset GITHUB_TOKEN`.

## 1. Arrancar

- Lo que hay que leer para cada tipo de cambio está en la
  [sección 12 de `AGENTS.md`](../../AGENTS.md#12-qué-leer-antes-de-qué). Si toca movimientos,
  cuentas, presupuestos o categorías, usá la skill `domain-rules`.
- La rama se llama `hu<N>-c<corte>-<tema>` para un corte de una historia y `tarea-<tema>` para
  el resto ([cómo colaborar](../../docs/como-colaborar.md#1-incluir-un-cambio)).
- Las tarjetas están en el tablero del proyecto en GitHub.

## 2. Especificar

- La especificación de una historia va en `docs/features/FEAT-XXX/spec.md`, y `ui_contract.md`
  si hay pantalla, desde [`docs/features/TEMPLATE/`](../../docs/features/TEMPLATE/).

## 5. Implementar

- Los controles están en la [sección 11 de `AGENTS.md`](../../AGENTS.md#11-comandos-de-verificación).
- Si cambió `docs/`, antes del commit corré `cd site && npm run build`.

## 6. Cerrar el corte

- La hoja de ruta es [`docs/hoja-de-ruta.md`](../../docs/hoja-de-ruta.md).

## 7. Probar a mano

- Los pasos usan Docker Compose, los datos de prueba y, si hace falta, un script de `scripts/`.

## 9. Entregar

- La descripción sale de [`pr.md`](../../docs/features/TEMPLATE/pr.md) y se escribe en
  `../pr-platita/<rama>.md`, fuera del repo. Después se copia al portapapeles.
- El pull request lo abrís vos contra `platita-v2`, con `gh pr create`, junto con el commit y
  el push que pide la persona. El merge lo hace siempre ella.
- Cuando lo abrís, pasá las tarjetas a "En revisión". Cuando ella lo integra, confirmá que las
  issues que cerró quedaron en "Hecho".
