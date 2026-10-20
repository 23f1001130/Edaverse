import React from 'react'
import { renderToString } from 'react-dom/server'
import Landing from './pages/Landing.jsx'
import FeaturePage from './pages/FeaturePage.jsx'
import { home, featurePages, SITE_URL } from './seo/pages.js'

export const pages = [home, ...featurePages]

export function renderPage(page) {
  return renderToString(page.path === '/' ? <React.Suspense fallback={null}><Landing /></React.Suspense> : <FeaturePage page={page} />)
}

export function structuredData(page) {
  const url = `${SITE_URL}${page.path}`
  const graph = [
    { '@type': 'WebSite', '@id': `${SITE_URL}/#website`, url: `${SITE_URL}/`, name: 'edaverse' },
    { '@type': 'WebPage', '@id': `${url}#webpage`, url, name: page.title, description: page.description, isPartOf: { '@id': `${SITE_URL}/#website` }, inLanguage: 'en' },
  ]
  if (page.path === '/') {
    graph.push({ '@type': 'SoftwareApplication', '@id': `${SITE_URL}/#app`, name: 'edaverse', url, description: page.description, applicationCategory: 'BusinessApplication', operatingSystem: 'Web', offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' }, featureList: ['Data profiling', 'Exploratory data analysis', 'Guided data cleaning', 'Feature engineering', 'Dataset and notebook export'] })
  } else {
    graph.push({ '@type': 'BreadcrumbList', itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: page.label, item: url },
    ] })
  }
  return { '@context': 'https://schema.org', '@graph': graph }
}
