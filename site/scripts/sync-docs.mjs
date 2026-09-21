// Genera el contenido del portal desde docs/, que es la única fuente.
//
// docs/ tiene que seguir renderizando bien en GitHub, así que no se le agrega
// frontmatter ni se le tocan los enlaces. Este script produce una copia con lo
// que Starlight necesita:
//
//   1. frontmatter con el título, tomado del "# H1" del documento;
//   2. el H1 eliminado del cuerpo, porque Starlight ya lo pinta desde el título;
//   3. los enlaces reescritos: los internos a rutas del sitio y los que salen de
//      docs/ a URL absolutas de GitHub. Astro reescribe los enlaces .md sueltos
//      pero no los que llevan ancla, y casi todas las referencias cruzadas de
//      esta documentación llevan ancla;
//   4. los bloques ```mermaid convertidos en <div class="mermaid">, porque
//      Expressive Code se queda con el bloque de código y pierde la clase que
//      el renderizador del cliente necesita.
//
// La salida vive en src/content/docs/ y está en .gitignore: se regenera siempre.

import { readdir, readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = dirname(fileURLToPath(new URL('.', import.meta.url)));
const ROOT = join(SITE, '..');
const SOURCE = join(ROOT, 'docs');
const TARGET = join(SITE, 'src', 'content', 'docs');
const BLOB = 'https://github.com/verozacarias-prog/AI4Devs-finalproject/blob/main';
// Tiene que coincidir con `base` en astro.config.mjs.
const BASE = '/AI4Devs-finalproject';

// Registros: citan texto ajeno por definición. Mismo criterio que is_record()
// en scripts/verify_docs.py.
const isRecord = (name) => name === 'prompts.md' || name.startsWith('conversacion-');

async function markdownFiles(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await markdownFiles(full)));
    else if (entry.name.endsWith('.md') && !isRecord(entry.name)) out.push(full);
  }
  return out;
}

function titleOf(body, fallback) {
  const match = body.match(/^#\s+(.+)$/m);
  if (!match) return fallback;
  return match[1].replace(/[`*]/g, '').trim();
}

// Starlight sirve cada documento en una ruta propia, en minúsculas y sin .md.
const slugOf = (relPath) =>
  relPath.replace(/\.md$/, '').split(sep).join('/').toLowerCase();

// Reescribe todo enlace relativo que apunte a un .md. Si el destino sigue dentro
// de docs/ es una página del portal; si se escapa, es un archivo del repositorio
// que el portal no publica y se manda a GitHub.
function rewriteLinks(body, fileDir) {
  return body.replace(/\]\((\.[^)\s]*|[\w][^)\s:]*\.md[^)\s]*)\)/g, (whole, target) => {
    if (target === '.') return `](${BASE}/)`;
    if (!target.includes('.md')) return whole;

    const [path, hash] = target.split('#');
    const inside = relative(SOURCE, join(fileDir, path));
    const fragment = hash ? '#' + hash : '';

    if (inside.startsWith('..')) {
      const fromRoot = relative(ROOT, join(fileDir, path)).split(sep).join('/');
      return `](${BLOB}/${fromRoot}${fragment})`;
    }
    return `](${BASE}/${slugOf(inside)}/${fragment})`;
  });
}

// Expressive Code renderiza el bloque de código y descarta la clase que el
// renderizador necesita, así que el diagrama se saca del camino como HTML suelto.
//
// El diagrama va en un atributo y no dentro del elemento por una razón concreta:
// en CommonMark un bloque HTML termina en la primera línea en blanco, y los
// diagramas tienen líneas en blanco entre secciones. Con el cuerpo vacío el div
// ocupa una sola línea y el bloque no se puede partir.
const escapeAttribute = (s) =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '&#10;');

function extractMermaid(body) {
  return body.replace(/^```mermaid\n([\s\S]*?)^```$/gm, (_whole, source) =>
    `<div class="mermaid" data-source="${escapeAttribute(source.trimEnd())}"></div>`
  );
}

await rm(TARGET, { recursive: true, force: true });
await mkdir(TARGET, { recursive: true });

const files = await markdownFiles(SOURCE);
const sources = new Map(); // texto original, para llms-full.txt
for (const file of files) {
  const rel = relative(SOURCE, file);
  const raw = await readFile(file, 'utf8');
  sources.set(rel, raw);
  const title = titleOf(raw, rel);

  let body = raw.replace(/^#\s+.+$/m, '').replace(/^\n+/, '');
  body = rewriteLinks(body, dirname(file));
  body = extractMermaid(body);

  const frontmatter = `---\ntitle: ${JSON.stringify(title)}\n---\n\n`;
  const dest = join(TARGET, rel);
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, frontmatter + body, 'utf8');
}

// Portada del sitio. No sale de docs/ porque el README del repositorio es la
// portada de GitHub y tiene la ficha del proyecto, que acá no aporta.
await writeFile(
  join(TARGET, 'index.md'),
  `---
title: Platita
description: Documentación del asistente financiero personal y familiar por WhatsApp.
---

Platita es un asistente financiero personal y familiar que funciona por WhatsApp: el usuario
registra gastos, ingresos y presupuestos conversando en lenguaje natural y los consulta en un
dashboard web.

Este portal se genera desde el directorio \`docs/\` del repositorio, que es la especificación del
proyecto y su única fuente. Si el portal y el repositorio difieren, manda el repositorio.

- [Descripción general del producto](01-producto/)
- [Arquitectura del sistema](02-arquitectura/)
- [Reglas de dominio](reglas-de-dominio/)
- [Decisiones de arquitectura](adr/0001-arquitectura-hexagonal/)

El código vive en [GitHub](https://github.com/verozacarias-prog/AI4Devs-finalproject).
`,
  'utf8'
);

// --- llms.txt: qué leer y en qué orden, para un agente de IA -----------------
// El estándar pide un archivo corto con enlaces, y uno expandido con el texto
// completo serializado. Los dos se generan; ninguno se escribe a mano.

const SITE_URL = `https://verozacarias-prog.github.io${BASE}`;

const linkList = (paths) =>
  paths
    .map((rel) => {
      const title = titleOf(sources.get(rel), rel);
      return `- [${title}](${SITE_URL}/${slugOf(rel)}/)`;
    })
    .join('\n');

const spec = files.map((f) => relative(SOURCE, f)).filter((r) => !r.startsWith('adr'));
const adrs = files.map((f) => relative(SOURCE, f)).filter((r) => r.startsWith('adr'));

const llms = `# Platita

> Asistente financiero personal y familiar que funciona por WhatsApp: el usuario registra gastos,
> ingresos y presupuestos conversando en lenguaje natural y los consulta en un dashboard web. Una
> capa de IA interpreta, categoriza e imputa cada movimiento a una cuenta y a un presupuesto.

Platita no es un agregador bancario: no se conecta a home banking, no pide credenciales y no
scrapea bancos. Todo dato entra por la conversación, por una regla recurrente o por los emails de
aviso que el usuario habilita.

La documentación está en español. El código, las entidades, las columnas, los endpoints y los
nombres de archivo de código están en inglés.

## Stack técnico

- Backend: Python + FastAPI, arquitectura hexagonal (puertos y adaptadores)
- Persistencia: PostgreSQL con pgvector como único almacén, migraciones con Alembic
- IA: cliente de LLM para interpretación de lenguaje natural, y RAG sobre pgvector
- Canal principal: webhook de WhatsApp
- Frontend: aplicación web de dashboards, desacoplada del backend y comunicada solo por API REST

## Especificación

${linkList(spec)}

## Decisiones de arquitectura

${linkList(adrs)}

## Contrato para asistentes de IA

- [AGENTS.md](${BLOB}/AGENTS.md): regla de dependencia hexagonal, invariantes de dominio,
  convenciones de código, seguridad y qué leer antes de qué. \`CLAUDE.md\` es un enlace simbólico
  a ese mismo archivo.

## Optional

- [Documentación completa serializada](${SITE_URL}/llms-full.txt)
`;

const full = [
  '# Platita — documentación completa',
  '',
  'Generado desde docs/ por site/scripts/sync-docs.mjs. La fuente es el repositorio.',
  '',
  ...files.map((f) => {
    const rel = relative(SOURCE, f);
    return `\n\n---\n\n<!-- docs/${rel.split(sep).join('/')} -->\n\n${sources.get(rel)}`;
  }),
].join('\n');

await mkdir(join(SITE, 'public'), { recursive: true });
await writeFile(join(SITE, 'public', 'llms.txt'), llms, 'utf8');
await writeFile(join(SITE, 'public', 'llms-full.txt'), full, 'utf8');
// El de la raíz del repositorio es el mismo: un agente que clona no ve el sitio.
await writeFile(join(ROOT, 'llms.txt'), llms, 'utf8');

console.log(
  `sync-docs: ${files.length} documentos + portada -> src/content/docs/, ` +
  `llms.txt y llms-full.txt generados`
);
