import React from 'react'
import { FeatureLinks, MarketingFooter, Questions } from '../components/MarketingContent.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import ProductPreview from '../components/ProductPreview.jsx'
import './Landing.css'

export default function Landing({ onSignIn, onGetStarted, onDemo, isSignedIn = false, userButton = null }) {
  const activate = callback => event => {
    if (callback) { event.preventDefault(); callback() }
  }

  return (
    <div className="landing">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <nav className="lnav" aria-label="Main navigation">
        <a className="lnav-logo" href="/?start=1" onClick={activate(onGetStarted)} aria-label="Open edaverse">
          <span className="lnav-mark">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1.5"/>
              <rect x="14" y="3" width="7" height="7" rx="1.5"/>
              <rect x="3" y="14" width="7" height="7" rx="1.5"/>
              <rect x="14" y="14" width="7" height="7" rx="1.5"/>
            </svg>
          </span>
          <span className="lnav-name">edaverse</span>
        </a>
        <div className="lnav-actions">
          <ThemeToggle />
          {isSignedIn ? (
            <>
              {userButton}
              <a className="lnav-cta" href="/?start=1" onClick={activate(onGetStarted)}>Workspace</a>
            </>
          ) : (
            <>
              <a className="lnav-signin" href="/?start=1" onClick={activate(onSignIn)}>Sign in</a>
              <a className="lnav-cta" href="/?start=1" onClick={activate(onGetStarted)}>Get started</a>
            </>
          )}
        </div>
      </nav>

      <main id="main-content">
        <section className="hero" id="product">
          <div className="hero-copy">
            <div className="hero-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="hero-badge-star">
                <path d="m12 2 2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17.2l-6.2 4.1 2.4-7.4L2 9.4h7.6z"/>
              </svg>
              with AI-powered EDA — no code required
            </div>
            <h1 className="hero-title">
              No-code data analysis.<br /><span className="hero-title-gradient">CSV to clarity.</span>
            </h1>
            <p className="hero-sub">
              Explore CSV and Excel files with automated exploratory data analysis (EDA). Profile missing values, visualize relationships, review cleaning suggestions, and engineer features without writing code.
            </p>
            <div className="hero-actions">
              <a className="hero-primary" href="/?start=1" onClick={activate(onGetStarted)}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Upload your dataset
              </a>
              <a className="hero-secondary" href="/?demo=1" onClick={activate(onDemo)}>
                View demo
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"/>
                  <polyline points="12 5 19 12 12 19"/>
                </svg>
              </a>
            </div>
            <div className="hero-trust">
              <span>✓ No credit card required</span>
              <span>◇ Open source &amp; self-hostable</span>
              <span>⟨⟩ Open data formats</span>
            </div>
            <a className="github-star" href="https://github.com/23f1001130/Edaverse" target="_blank" rel="noopener noreferrer">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .3a12 12 0 0 0-3.8 23.38c.6.12.82-.26.82-.58L9 21.07c-3.34.72-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.08-.74.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49 1 .1-.78.42-1.3.76-1.6-2.67-.31-5.47-1.34-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6.02 0c2.28-1.55 3.29-1.23 3.29-1.23.66 1.66.25 2.88.12 3.18a4.65 4.65 0 0 1 1.24 3.22c0 4.61-2.8 5.62-5.48 5.92.43.37.81 1.1.81 2.22l-.01 3.29c0 .32.22.7.82.58A12 12 0 0 0 12 .3"/></svg>
              Star on GitHub
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
            </a>
          </div>

          <ProductPreview onDemo={onDemo} />
        </section>

        <section className="workflow-strip" id="workflow" aria-label="Workflow">
          <span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            Upload
          </span>
          <span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            Profile
          </span>
          <span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            Clean
          </span>
          <span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Engineer
          </span>
          <span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Export
          </span>
        </section>

        <section className="features" id="features">
          <div className="section-head">
            <span>Built for analysis work</span>
            <h2>Profile, clean, and prepare your data.</h2>
          </div>
          <div className="features-grid">
            <article className="feature-card">
              <span className="feature-icon data">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"/>
                  <line x1="12" y1="20" x2="12" y2="4"/>
                  <line x1="6" y1="20" x2="6" y2="14"/>
                </svg>
              </span>
              <h3>Deep profiling</h3>
              <p>Column-level quality scores, null analysis, outlier detection, cardinality, and correlation heatmaps — all in one pass.</p>
            </article>
            <article className="feature-card">
              <span className="feature-icon clean">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </span>
              <h3>Guided cleaning</h3>
              <p>Review suggested fixes before changing data, then export a cleaned file, notebook, or report.</p>
            </article>
            <article className="feature-card">
              <span className="feature-icon ai">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                </svg>
              </span>
              <h3>AI narrative</h3>
              <p>A plain-English summary of what your data contains, what's wrong with it, and which features to engineer first.</p>
            </article>
          </div>
        </section>

        <FeatureLinks />
        <section className="seo-section" aria-labelledby="workflow-guide-title">
          <h2 id="workflow-guide-title">From a raw dataset to a useful next step</h2>
          <ol className="seo-steps">
            <li><strong>Upload and inspect.</strong> Add a CSV or Excel file, then check the parsed columns, detected types, and warnings.</li>
            <li><strong>Explore and decide.</strong> Review missing values, distributions, outliers, and correlations before choosing cleaning operations.</li>
            <li><strong>Prepare and export.</strong> Apply suitable fixes, engineer features, and export a cleaned file, notebook, or report.</li>
          </ol>
          <p>Use edaverse for a course project, a first pass on a business export, or preparation for a modeling workflow. Review suggested changes using your knowledge of the data.</p>
        </section>
        <Questions />
        <section className="cta">
          <div>
            <span>Ready when your next dataset is.</span>
            <h2>Open the workspace and start profiling.</h2>
          </div>
          <a className="hero-primary" href="/?start=1" onClick={activate(onGetStarted)}>
            Start now
          </a>
        </section>
      </main>
      <MarketingFooter />
    </div>
  )
}
