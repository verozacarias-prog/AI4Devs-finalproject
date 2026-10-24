# Cómo colaborar

Los pasos para incluir un cambio en Platita, y cómo se verifica. Lo que un asistente de IA tiene
que respetar está en [`AGENTS.md`](../AGENTS.md).

## 1. Incluir un cambio

Los pasos para incluir un cambio, en orden. El detalle de cada uno está en el documento enlazado.
En el backend se trabaja con tests primero ([ADR 0024](adr/0024-tests-primero-en-el-backend.md)).

**Ramas.** Cada entrega tiene su rama (`feature/entrega-N-VNZ`; la final, `final-project-VNZ`),
que sale de `main` y vuelve a `main` cuando la entrega se cierra. El trabajo no se hace ahí: cada
cambio va en una rama corta que sale de la rama de la entrega y vuelve a ella por pull request. La
rama de la entrega despliega el entorno de pruebas, y `main`, producción. El porqué está en
[documentación viva](documentacion-viva.md#7-el-modelo-de-ramas).

| Rama | Sale de | Nombre | Ejemplo |
|---|---|---|---|
| De entrega | `main` | `feature/entrega-<N>-VNZ`, y `final-project-VNZ` para la final | `final-project-VNZ` |
| De un corte de una historia | La rama de la entrega | `hu<N>-c<corte>-<tema>` | `hu3-c1-registro-de-gasto` |
| De lo que no es una historia | La rama de la entrega | `tarea-<tema>` | `tarea-scaffold-y-docker` |

**Issues.** Cada historia de usuario y cada ticket de trabajo es una issue de GitHub, en el
milestone de la entrega, y su avance se sigue en el
[tablero](https://github.com/users/verozacarias-prog/projects/1).

- Una historia lleva la etiqueta `historia`, y sus tickets son sus sub-issues, con la etiqueta
  `ticket`. Lo que no sale de una historia lleva `tarea`, y lo que suma sin ser obligatorio,
  además `opcional`.
- El título de un ticket o una tarea empieza con su componente: `[Backend]`, `[FrontEnd]`,
  `[Worker]`, `[Base de datos]`, `[DevOps]`, `[Docs]` o `[Tests]`. Si toca dos, lleva los dos.
- Una issue organiza el trabajo y enlaza a `docs/`: la especificación sigue estando en `docs/`.
- El pull request que resuelve una issue la cierra con `Closes #N` en su descripción. Al
  integrarlo, la issue se cierra y su tarjeta pasa a "Hecho". Si la resuelve en parte, lleva
  `Parte de #N` y la issue queda abierta.

**Una vez por clon.**

```sh
git config core.hooksPath .githooks   # activa el hook de pre-commit
cd site && npm install                # solo para ver o regenerar el portal
```

**Para incluir un cambio.**

1. **Crear la rama** desde la rama de la entrega, con el nombre de la tabla, y pasar la
   tarjeta de su issue a "En curso". Una historia son
   tres ramas, una por [corte vertical](convenciones-de-desarrollo.md#1-cortes-verticales).
2. **Leer antes de escribir.** [`AGENTS.md`](../AGENTS.md) es el contrato, y su sección 12 dice qué
   leer según el cambio. Si toca movimientos, cuentas, presupuestos o categorías, el skill
   `domain-rules` se activa solo y dice qué reglas aplican.
3. **Especificar.** Copiar [`docs/features/TEMPLATE/`](features/TEMPLATE/) a
   `docs/features/FEAT-XXX/` y completar `spec.md`, con los criterios de aceptación numerados y,
   después, los casos de prueba de cada corte, y `ui_contract.md` si hay pantalla.
4. **Aprobar los casos de prueba** del corte en `spec.md`. El asistente los propone; sin la
   aprobación de una persona no se escribe ningún test. En una rama `tarea-…` no hay carpeta:
   los casos aprobados van en la descripción del pull request.
5. **Escribir los tests del backend y verlos fallar.** Es el primer commit del corte,
   `test(alcance): …`. Desde ahí, un test no se modifica ni se borra sin aprobación.
6. **Implementar lo mínimo para que pasen,** y refactorizar en verde. Es el segundo commit,
   `feat(alcance): …`. Los tests de los estados de una pantalla van en este mismo corte.
   La documentación que el cambio afecta —API, modelo de datos, reglas de dominio— entra en el
   mismo pull request, en sus propios commits `docs(alcance): …`, y una decisión de
   arquitectura lleva su [ADR](adr/).
7. **Verificar antes de cada commit.** El hook corre solo los tres verificadores de
   [Verificación](#2-verificación). Si cambió `docs/`, además `cd site && npm run build`, que
   regenera `llms.txt`. Un documento nuevo se suma a la tabla de documentación del
   [README](../README.md#documentación) y a la barra lateral de `site/astro.config.mjs`.
8. **Escribir cada commit** con el [formato de mensaje](convenciones-de-desarrollo.md#1-cortes-verticales)
   `tipo(alcance): qué cambia`, en español.
9. **Cerrar el corte** con `/spec-drift`, y con `/ui-states` si tiene pantalla.
10. **Abrir el pull request contra la rama de la entrega,** con el corte en verde y una
   descripción armada desde la plantilla [`pr.md`](features/TEMPLATE/pr.md), con el
   [Definition of Done](07-pull-requests.md#definition-of-done) y `Closes #N`.
   Correr el agente `pr-reviewer` y resumir su informe.
11. **Integrar** cuando todos los controles pasan, con un commit de merge y sin aplastar los
    commits, para que se vea que los tests fueron primero. La aprobación y el merge son de una
    persona; un asistente hace commit solo si se lo piden, y nunca hace merge.

**Para abrir y cerrar una entrega.**

- **Abrir:** crear `feature/entrega-<N>-VNZ`, o `final-project-VNZ` para la final, desde `main`;
  ponerla como rama por defecto del repositorio, porque de ahí se publica el portal y ahí abre
  Dependabot sus pull requests; y protegerla, con los controles como obligatorios.
- **Cerrar:** correr `/security-audit` y `/spec-drift` sobre todo el proyecto, registrar los
  prompts en el [registro completo](registro-ia.md), y los que cambiaron una decisión también en
  [`prompts.md`](../prompts.md), con hasta tres por sección, y abrir el pull request de la rama de
  la entrega a `main`.
- **Cada lunes:** revisar los pull requests de Dependabot.

Los commands, el skill y el agente están descritos en el
[flujo de trabajo con IA](flujo-de-trabajo-con-ia.md).

## 2. Verificación

```sh
git config core.hooksPath .githooks       # una vez por clon
python3 scripts/verify_docs.py            # enlaces, anclas, duplicación, Mermaid
python3 scripts/verify_architecture.py    # regla hexagonal, acceso a la base y aislamiento del frontend
python3 scripts/verify_api_contract.py    # la referencia de la API, completa y fiel a 04-api.md
```

El hook de pre-commit los corre solo, y GitHub Actions los repite en cada pull request junto con
el formato del Markdown, los enlaces externos y la construcción del portal. El sistema completo
está en [documentación viva](documentacion-viva.md).

## 3. Entorno de desarrollo

Cómo levantar Platita y probar el flujo está en el
[README](../README.md#cómo-ejecutar-localmente). Para trabajar sobre él:

- En los registros de Compose, cada línea empieza con el nombre de su contenedor:
  `platita-api-and-dashboard`, `platita-worker`, `platita-database` o `platita-migrations`.
- Si ya tenías un `.env` de antes, comparalo con `.env.example`: una variable nueva no llega
  sola. La que enciende la entrada de desarrollo es `DEV_ENTRY_ENABLED=true`, y la que enciende
  el chat web, `WEB_CHAT_ENABLED=true`.
- En Swagger se prueban las rutas de lectura. Las que modifican algo se prueban desde el
  dashboard, porque exigen venir de su página y como JSON.
- Para trabajar en el dashboard con recarga automática, con Compose levantado:

```sh
cd frontend
npm ci
npm run dev                               # http://127.0.0.1:5173/app/
```
