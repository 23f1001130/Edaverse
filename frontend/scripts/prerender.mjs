import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { pages, renderPage, structuredData } from '../.prerender/render.js'

const frontend = fileURLToPath(new URL('../', import.meta.url))
const dist = resolve(frontend, 'dist')
const template = await readFile(resolve(dist, 'index.html'), 'utf8')
const escape = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')

for (const page of pages) {
  const url = `https://edaverse.app${page.path}`
  const head = `<title>${escape(page.title)}</title>
    <meta name="description" content="${escape(page.description)}" />
    <meta name="robots" content="index,follow,max-image-preview:large" />
    <link rel="canonical" href="${url}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="edaverse" />
    <meta property="og:url" content="${url}" />
    <meta property="og:title" content="${escape(page.title)}" />
    <meta property="og:description" content="${escape(page.description)}" />
    <meta property="og:image" content="https://edaverse.app/og-image.png" />
    <meta property="og:image:alt" content="edaverse: exploratory data analysis for CSV and Excel" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${escape(page.title)}" />
    <meta name="twitter:description" content="${escape(page.description)}" />
    <meta name="twitter:image" content="https://edaverse.app/og-image.png" />
    <script type="application/ld+json">${JSON.stringify(structuredData(page)).replaceAll('<', '\\u003c')}</script>`
  const html = template.replace(/<!-- SEO_START -->[\s\S]*?<!-- SEO_END -->/, `<!-- SEO_START -->\n    ${head}\n    <!-- SEO_END -->`)
    .replace('<div id="root"></div>', () => `<div id="root" data-prerendered="true">${renderPage(page)}</div>`)
  const folder = resolve(dist, `.${page.path}`)
  if (folder !== dist && !folder.startsWith(`${dist}/`) && !folder.startsWith(`${dist}\\`)) throw new Error('Invalid output path')
  await mkdir(folder, { recursive: true })
  await writeFile(resolve(folder, 'index.html'), html)
}

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages.map(page => `  <url><loc>https://edaverse.app${page.path}</loc></url>`).join('\n')}\n</urlset>\n`
await writeFile(resolve(dist, 'sitemap.xml'), sitemap)
console.log(`Prerendered ${pages.length} public pages and generated sitemap.xml`)
