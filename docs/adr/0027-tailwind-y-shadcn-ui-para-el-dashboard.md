# 0027 — Tailwind CSS y shadcn/ui para el dashboard

- Estado: Aceptada
- Fecha: 2026-10-14

## Contexto

El [ADR 0026](0026-react-typescript-y-vite-para-el-dashboard.md) dejó el dashboard sin librerías
de componentes, y dijo que cada una se suma con la primera pantalla que la necesite. Cuando se
tomó esta decisión había tres pantallas, el estado del sistema, la entrada de desarrollo y las
cuentas; el chat web llegó después, ya con estas clases. Las tres estaban escritas con CSS
propio sobre los tokens de `frontend/src/design-tokens.css`. Se ven correctas, pero no hay un
diseño detrás: cada pieza se resolvió a mano.

Lo que viene lo pide: un menú lateral que separa las pantallas del producto de las herramientas de
prueba, y el chat web, con burbujas, un campo de texto, botones de responder y avisos de envío. Son
componentes que se repiten, y la accesibilidad de cada uno, como el foco o el nombre que anuncia un
lector de pantalla, hoy se resolvería pieza por pieza.

El material del máster, en su módulo de frontend, recomienda Tailwind CSS v4 para los estilos y
shadcn/ui para los componentes, como el conjunto que hoy domina en React. La autora quiere que el
dashboard se vea cuidado en la demo.

## Decisión

1. **Los estilos se escriben con Tailwind CSS v4**, con su complemento para Vite.
2. **Los componentes base salen de shadcn/ui.** No es una dependencia que se actualiza sola: su
   herramienta copia cada componente en `frontend/src/components/ui/`, hecho sobre las primitivas
   de Radix, y desde ahí es código del proyecto, que se lee, se prueba y se cambia como el resto.
   Se suma un componente cuando una pantalla lo usa, no el catálogo entero. Si se suma con la
   herramienta de shadcn/ui, esta escribe sus propias variables de color en `index.css`: hay que
   sacarlas de ahí y llevar lo que falte a `design-tokens.css`.
3. **Los tokens siguen en `frontend/src/design-tokens.css`, y son el tema entero de Tailwind.**
   El archivo borra la escala por defecto de Tailwind y declara la propia: colores, espaciado,
   tipografía, radios, sombras y el punto de corte del celular. Una clase que pide un valor de
   esas escalas sin un token detrás no existe, y la compilación no la genera. Hay dos excepciones,
   que Tailwind genera igual y se aceptan: las clases fijas, que no son un valor de diseño, como
   `rounded-full` para un círculo o `leading-none`; y la transparencia aplicada a un color del
   tema, como `bg-primary/90`, que no crea un color nuevo sino que usa uno de los tokens. Lo que no
   es un paso de una escala, como el ancho del menú o el grosor del foco, va como variable en el
   mismo archivo. Lo que hereda la aplicación móvil sigue estando en un solo archivo.
4. **Cada dependencia nueva se fija en una versión publicada hace al menos dos semanas,** y Dependabot
   propone las siguientes. Una versión recién publicada no tuvo tiempo de mostrar un problema.
5. **El menú lateral es un estado de la pantalla, sin una librería de rutas.** Con dos o tres
   pantallas no hace falta una; se suma cuando haga falta que cada pantalla tenga su dirección.

## Consecuencias

### Positivas

- El dashboard se ve como un producto actual sin diseñar cada detalle, y los componentes traen
  resuelto el teclado, el foco y los nombres accesibles.
- Es el conjunto que enseña el máster y que genera la mayoría de las herramientas de IA, así que
  un asistente lo escribe con menos errores.
- Los componentes son del proyecto: si uno no sirve, se cambia sin esperar a nadie.

### Negativas y costos asumidos

- Entran dependencias nuevas: `class-variance-authority`, `clsx`, `tailwind-merge` y los íconos de
  `lucide-react`, y para compilar, Tailwind y su complemento para Vite. Radix y las animaciones de
  shadcn/ui entran con el primer componente que las use: el botón y la tarjeta no las necesitan.
- Una clase de Tailwind que se lee en su documentación puede no existir acá, si su valor no tiene
  un token. Es a propósito, pero sorprende: la clase no da error, solo no tiene estilo.
- Las tres pantallas que ya existen se migran a las clases nuevas, y su CSS propio se borra.
- El código de los componentes copiados no se actualiza solo: una corrección de shadcn/ui hay que
  traerla a mano.
- La aplicación móvil no reutiliza los componentes, porque son para el navegador. Reutiliza los
  tokens y el contrato de cada pantalla, igual que antes.

## Alternativas descartadas

- **Seguir con CSS propio:** cero dependencias, pero cada componente, su aspecto y su
  accesibilidad se resuelven a mano, y el resultado depende de cuánto tiempo se le dedique.
- **MUI (Material UI):** el catálogo más amplio, pero impone el aspecto de Material y su propio
  sistema de estilos, que convive mal con los tokens en variables CSS.
- **Una librería de rutas, como React Router, ya ahora:** con un menú de dos o tres pantallas sería
  una dependencia más sin uso real.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
