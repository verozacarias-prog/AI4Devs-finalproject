# 0026 — React, TypeScript y Vite para el dashboard

- Estado: Aceptada
- Fecha: 2026-10-11

## Contexto

El dashboard es la parte web de Platita. En la entrega 2 tiene tres pantallas: la entrada de
desarrollo, el chat web y la de cuentas ([hoja de ruta](../hoja-de-ruta.md#alcance-de-la-entrega-2)).
La especificación no decía con qué se construye, pero ya fijaba cuatro condiciones:

- Se compila a archivos estáticos, que la API sirve bajo `/app`
  ([ADR 0016](0016-sesion-de-servidor-en-el-mismo-origen.md)). No hay un servidor aparte para
  el frontend.
- El cliente que habla con la API se genera desde el contrato que publica FastAPI
  ([ADR 0005](0005-python-fastapi-en-vez-de-go.md)).
- Cada pantalla se prueba en sus estados contra una API simulada
  ([convenciones de desarrollo](../convenciones-de-desarrollo.md#2-los-cuatro-estados-de-una-pantalla)).
- Los tokens de diseño y la máquina de estados de cada pantalla tienen que poder reutilizarse
  en una futura aplicación móvil.

## Decisión

1. **El dashboard se escribe en React con TypeScript y se compila con Vite.** Vive en
   `frontend/`, no importa nada de `backend/` y habla con la API solo por HTTP, con rutas
   relativas, porque comparte origen con ella.
2. **Los tipos de la API se generan, no se escriben a mano.** Un comando del backend exporta el
   contrato a `frontend/src/api/openapi.json`, y de ahí se generan los tipos con
   `openapi-typescript`. Los dos archivos se versionan, y el pipeline falla si alguno quedó
   desactualizado respecto de la API.
3. **Los tests de pantalla usan Vitest y Testing Library, con la API simulada a nivel de red**
   con `msw`. Así la pantalla y su llamada a la API se prueban juntas, y cada test busca lo que
   ve una persona: un texto, un botón, un aviso.
4. **Los tokens de diseño son variables CSS en un solo archivo,** `frontend/src/design-tokens.css`.
   Ningún componente usa un color, un tamaño o un espaciado suelto.
5. **Sin librerías de rutas, de estado ni de componentes todavía.** Cada una se suma con la
   primera pantalla que la necesite, con su justificación. La primera fue la de componentes, con
   el menú lateral y el chat ([ADR 0027](0027-tailwind-y-shadcn-ui-para-el-dashboard.md)).
6. **El linter es `oxlint`,** el que trae la plantilla de Vite. La verificación de tipos la hace
   el compilador de TypeScript.
7. **TypeScript 5, no 6.** La herramienta que genera los tipos todavía no admite la versión 6.
   Se sube cuando la admita.
8. **Mientras se desarrolla, Vite sirve el dashboard** con recarga automática y reenvía a la API
   los pedidos de datos. En los entornos desplegados no hay servidor de Vite: la API sirve el
   resultado de la compilación.

## Consecuencias

### Positivas

- La compilación da archivos estáticos comunes, que es lo que pide el ADR 0016, y que mañana
  puede servir cualquier otro servidor sin cambiar el código del dashboard.
- Si la API cambia una respuesta, el dashboard deja de compilar en vez de fallar en el
  navegador.
- React Native reutiliza la lógica y los tokens si llega la aplicación móvil.
- Es el ecosistema con más herramientas y más material, para una sola persona que mantiene todo.

### Negativas y costos asumidos

- React deja más decisiones a cargo de quien desarrolla que un framework completo: las rutas y
  el manejo de datos se van a elegir cuando hagan falta.
- Quedar en TypeScript 5 obliga a rechazar la actualización a la 6 que proponga Dependabot,
  hasta que la herramienta de tipos la admita.
- El contrato exportado y los tipos generados son dos archivos más para regenerar cuando cambia
  la API. El pipeline lo recuerda, pero no lo hace solo.
- Node entra al proyecto, aunque solo para compilar: no queda en la imagen final.

## Alternativas descartadas

- **Vue con TypeScript y Vite:** cumple las cuatro condiciones y es más simple de leer. No tiene
  un camino tan directo hacia la aplicación móvil.
- **Next.js:** su valor principal es un servidor propio que renderiza páginas, y acá no se
  usaría, porque la API sirve archivos estáticos. Sería cargar con una herramienta más grande
  para aprovechar una parte.
- **Escribir a mano los tipos de la API:** menos herramientas, pero es justo lo que deja que el
  frontend y el backend se desincronicen sin que nada falle.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
