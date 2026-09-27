// Renderiza los bloques ```mermaid de la documentación. Se carga desde el head
// del sitio. Sigue el tema claro/oscuro de Starlight.
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

const theme = () =>
  document.documentElement.dataset.theme === 'dark' ? 'dark' : 'default';

async function render() {
  const blocks = document.querySelectorAll('div.mermaid:not([data-rendered])');
  if (!blocks.length) return;

  mermaid.initialize({ startOnLoad: false, theme: theme() });

  for (const [i, block] of [...blocks].entries()) {
    const source = block.dataset.source ?? '';
    try {
      const { svg } = await mermaid.render(`mermaid-${Date.now()}-${i}`, source);
      block.innerHTML = svg;
      block.dataset.rendered = 'true';
    } catch (error) {
      // Un diagrama con sintaxis inválida no puede romper la página entera:
      // se deja el código fuente a la vista, que es lo que muestra GitHub.
      block.dataset.rendered = 'error';
      console.error('mermaid: no se pudo renderizar el diagrama', error);
    }
  }
}

render();
// Starlight navega sin recargar la página.
document.addEventListener('astro:after-swap', render);
