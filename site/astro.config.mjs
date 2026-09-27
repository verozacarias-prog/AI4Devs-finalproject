// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// El contenido de src/content/docs/ lo genera scripts/sync-docs.mjs desde docs/.
// No se edita a mano: se regenera en cada build.
export default defineConfig({
  site: 'https://verozacarias-prog.github.io',
  // Sin base, GitHub Pages sirve el sitio con todas las rutas rotas.
  base: '/AI4Devs-finalproject',
  integrations: [
    starlight({
      title: 'Platita',
      description: 'Especificación del asistente financiero personal y familiar por WhatsApp.',
      defaultLocale: 'root',
      locales: { root: { label: 'Español', lang: 'es' } },
      social: [{
        icon: 'github',
        label: 'GitHub',
        href: 'https://github.com/verozacarias-prog/AI4Devs-finalproject',
      }],
      // Starlight no renderiza Mermaid. Los diagramas llegan como <pre><code
      // class="language-mermaid">, y este script los convierte en el cliente.
      // La alternativa de build genera SVG pero arrastra un navegador headless
      // al CI, que es mucho coste para un sitio de documentación.
      head: [{
        tag: 'script',
        attrs: { type: 'module', src: '/AI4Devs-finalproject/mermaid.js' },
      }],
      sidebar: [
        {
          label: 'Especificación',
          items: [
            { label: '1. Producto', slug: '01-producto' },
            { label: '2. Arquitectura', slug: '02-arquitectura' },
            { label: '3. Modelo de datos', slug: '03-modelo-de-datos' },
            { label: '4. API', slug: '04-api' },
            { label: '5. Historias de usuario', slug: '05-historias-de-usuario' },
            { label: '6. Tickets', slug: '06-tickets' },
            { label: '7. Pull requests', slug: '07-pull-requests' },
            { label: '8. Convenciones de documentación', slug: '08-convenciones-de-documentacion' },
          ],
        },
        {
          label: 'Reglas y convenciones',
          items: [
            { label: 'Reglas de dominio', slug: 'reglas-de-dominio' },
            { label: 'Convenciones de desarrollo', slug: 'convenciones-de-desarrollo' },
            { label: 'Flujo de trabajo con IA', slug: 'flujo-de-trabajo-con-ia' },
            { label: 'Documentación viva', slug: 'documentacion-viva' },
            { label: 'Hoja de ruta', slug: 'hoja-de-ruta' },
            { label: 'Operación (propuesta)', slug: 'operacion' },
          ],
        },
        {
          label: 'Decisiones de arquitectura',
          items: [{ autogenerate: { directory: 'adr' } }],
        },
        {
          label: 'Plantillas',
          items: [{ autogenerate: { directory: 'features' } }],
        },
      ],
    }),
  ],
});
