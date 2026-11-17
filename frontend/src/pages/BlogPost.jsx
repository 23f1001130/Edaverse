import React from 'react'
import { FeatureLinks, MarketingFooter } from '../components/MarketingContent.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import { blogPosts } from '../seo/pages.js'
import './Landing.css'

export default function BlogPost({ page }) {
  return <div className="landing">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <nav className="lnav" aria-label="Main navigation">
      <a className="lnav-logo" href="/">edaverse</a>
      <div className="lnav-actions"><ThemeToggle /><a className="lnav-cta" href="/?start=1">Get started</a></div>
    </nav>
    <main id="main-content">
      <header className="seo-section feature-intro">
        <nav className="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true"> / </span><a href="/blog/">Blog</a><span aria-hidden="true"> / </span><span>{page.label}</span></nav>
        <h1>{page.heading}</h1>
        <p>{page.description}</p>
        <time className="blog-date" dateTime={page.published}>{new Date(page.published + 'T00:00:00').toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</time>
      </header>
      <article className="seo-section feature-article" aria-label={page.label}>
        {page.body.map(([title, text]) => <section key={title}><h2>{title}</h2><p>{text}</p></section>)}
        <section>
          <h2>Try it yourself</h2>
          <div className="hero-actions"><a className="hero-primary" href="/?start=1">Upload your dataset</a><a className="hero-secondary" href="/?demo=1">View demo</a></div>
        </section>
      </article>
      <FeatureLinks />
    </main>
    <MarketingFooter />
  </div>
}

export function BlogIndex() {
  return <div className="landing">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <nav className="lnav" aria-label="Main navigation">
      <a className="lnav-logo" href="/">edaverse</a>
      <div className="lnav-actions"><ThemeToggle /><a className="lnav-cta" href="/?start=1">Get started</a></div>
    </nav>
    <main id="main-content">
      <section className="seo-section feature-intro">
        <nav className="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true"> / </span><span>Blog</span></nav>
        <h1>Blog</h1>
        <p>Guides on exploratory data analysis, data cleaning, and working with CSV and Excel data.</p>
      </section>
      <section className="seo-section">
        <div className="seo-link-grid">{blogPosts.map(post => <a className="seo-link-card" href={post.path} key={post.path}>
          <h3>{post.label}</h3><p>{post.description}</p><span>Read article →</span>
        </a>)}</div>
      </section>
    </main>
    <MarketingFooter />
  </div>
}
