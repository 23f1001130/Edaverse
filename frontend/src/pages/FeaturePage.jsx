import React from 'react'
import { FeatureLinks, MarketingFooter, Questions } from '../components/MarketingContent.jsx'
import './Landing.css'

export default function FeaturePage({ page }) {
  return <div className="landing">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <nav className="lnav" aria-label="Main navigation">
      <a className="lnav-logo" href="/">edaverse</a>
      <a className="lnav-cta" href="/?start=1">Get started</a>
    </nav>
    <main id="main-content">
      <header className="seo-section feature-intro">
        <nav className="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true"> / </span><span>{page.label}</span></nav>
        <p className="seo-eyebrow">{page.label}</p>
        <h1>{page.heading}</h1><p>{page.intro}</p>
        <div className="hero-actions"><a className="hero-primary" href="/?start=1">Analyze your dataset</a><a className="hero-secondary" href="/?demo=1">Try the demo</a></div>
      </header>
      <article className="seo-section feature-article" aria-label={`${page.label} guide`}>
        {page.sections.map(([title, text]) => <section key={title}><h2>{title}</h2><p>{text}</p></section>)}
        <section><h2>How to get started</h2><ol>{page.steps.map(step => <li key={step}>{step}</li>)}</ol></section>
      </article>
      <Questions items={page.faqs} /><FeatureLinks />
    </main>
    <MarketingFooter />
  </div>
}
