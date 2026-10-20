import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { JSDOM } from 'jsdom'
import { home, featurePages, SITE_URL } from '../src/seo/pages.js'

const pages = [home, ...featurePages]
const titles = new Set()
const descriptions = new Set()
const sitemap = await readFile(new URL('../dist/sitemap.xml', import.meta.url), 'utf8')
const paths = new Set(pages.map(page => page.path))
for (const page of pages) {
  const html = await readFile(new URL(`../dist${page.path}index.html`, import.meta.url), 'utf8')
  // No JavaScript execution: this checks what a crawler receives in the response.
  const document = new JSDOM(html).window.document
  assert.equal(document.querySelectorAll('title').length, 1)
  assert.equal(document.title, page.title)
  assert(!titles.has(document.title), 'Duplicate title')
  titles.add(document.title)
  const description = document.querySelector('meta[name="description"]').content
  assert(!descriptions.has(description), 'Duplicate description')
  descriptions.add(description)
  assert.equal(document.querySelectorAll('h1').length, 1)
  assert(document.querySelector('main').textContent.length > 1200, 'Missing static page content')
  assert.equal(document.querySelectorAll('link[rel="canonical"]').length, 1)
  const canonical = `${SITE_URL}${page.path}`
  assert.equal(document.querySelector('link[rel="canonical"]').href, canonical)
  assert.equal(document.querySelector('meta[property="og:url"]').content, canonical)
  assert.equal(document.querySelector('meta[property="og:title"]').content, page.title)
  assert.equal(document.querySelector('meta[name="twitter:title"]').content, page.title)
  const image = document.querySelector('meta[property="og:image"]').content
  await readFile(new URL(`../dist${new URL(image).pathname}`, import.meta.url))
  assert(document.querySelector('link[rel="icon"]'), 'Missing favicon')
  assert(!document.querySelector('meta[name="robots"]').content.includes('noindex'))
  assert(sitemap.includes(`<loc>${canonical}</loc>`), 'Missing sitemap URL')
  const schema = JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent)
  assert(schema['@graph'].some(node => node['@type'] === 'WebPage' && node.url === canonical))
  for (const link of document.querySelectorAll('a[href^="/"]')) {
    const url = new URL(link.getAttribute('href'), SITE_URL)
    assert(paths.has(url.pathname), `Broken internal link: ${url.pathname}`)
  }
  for (const asset of document.querySelectorAll('script[src],link[rel="stylesheet"]')) {
    const path = asset.getAttribute('src') || asset.getAttribute('href')
    if (path.startsWith('/')) await readFile(new URL(`../dist${path}`, import.meta.url))
  }
}
const notFound = await readFile(new URL('../dist/404.html', import.meta.url), 'utf8')
assert(notFound.includes('content="noindex"'))
const callback = new JSDOM(await readFile(new URL('../dist/auth-callback.html', import.meta.url), 'utf8')).window.document
assert(callback.querySelector('meta[name="robots"]').content.includes('noindex'))
assert.equal(callback.querySelector('link[rel="canonical"]'), null)
assert.equal(callback.querySelector('#root').textContent, '')
assert.equal((sitemap.match(/<loc>/g) || []).length, pages.length)
console.log(`SEO checks passed: ${pages.length} static pages, unique metadata, canonicals, schema, internal links, assets, sitemap, and 404 noindex.`)
