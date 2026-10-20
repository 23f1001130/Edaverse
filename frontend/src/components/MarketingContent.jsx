import React from 'react'
import { featurePages, homeFaqs } from '../seo/pages.js'

export function FeatureLinks() {
  return <section className="seo-section" aria-labelledby="explore-title">
    <h2 id="explore-title">Explore your next data task</h2>
    <div className="seo-link-grid">{featurePages.map(page => <a className="seo-link-card" href={page.path} key={page.path}>
      <h3>{page.label}</h3><p>{page.description}</p><span>Explore the workflow →</span>
    </a>)}</div>
  </section>
}

export function Questions({ items = homeFaqs }) {
  return <section className="seo-section seo-faq" aria-labelledby="faq-title">
    <h2 id="faq-title">Questions before you start</h2>
    {items.map(([question, answer]) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}
  </section>
}

export function MarketingFooter() {
  return <footer className="marketing-footer">
    <a href="/">edaverse</a>
    <nav aria-label="Explore edaverse">{featurePages.map(page => <a href={page.path} key={page.path}>{page.label}</a>)}
      <a href="https://github.com/23f1001130/Edaverse">Source code &amp; self-hosting</a>
    </nav>
  </footer>
}
