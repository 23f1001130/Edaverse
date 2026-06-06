import React from 'react'
import { useAuth, UserButton } from '@clerk/clerk-react'
import './Landing.css'

const metricCards = [
  ['Rows profiled', '7,043'],
  ['Quality score', '91'],
  ['Missing cells', '8.4%'],
  ['Feature ideas', '18'],
]

const columns = [
  ['age', 'NUM', 86],
  ['tenure_months', 'NUM', 62],
  ['monthly_charges', 'NUM', 78],
  ['contract_type', 'CAT', 42],
  ['churn', 'CAT', 54],
]

export default function Landing({ onSignIn, onGetStarted, onDemo }) {
  const { isSignedIn } = useAuth()

  return (
    <div className="landing">
      <nav className="lnav">
        <button className="lnav-logo" onClick={onGetStarted} type="button" aria-label="Open edaverse">
          <span className="lnav-mark">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1.5"/>
              <rect x="14" y="3" width="7" height="7" rx="1.5"/>
              <rect x="3" y="14" width="7" height="7" rx="1.5"/>
              <rect x="14" y="14" width="7" height="7" rx="1.5"/>
            </svg>
          </span>
          <span className="lnav-name">edaverse</span>
        </button>
        <div className="lnav-actions">
          {isSignedIn ? (
            <>
              <UserButton afterSignOutUrl="/" />
              <button className="lnav-cta" onClick={onGetStarted} type="button">Workspace</button>
            </>
          ) : (
            <>
              <button className="lnav-signin" onClick={onSignIn} type="button">Sign in</button>
              <button className="lnav-cta" onClick={onGetStarted} type="button">Get started</button>
            </>
          )}
        </div>
      </nav>

      <main>
        <section className="hero" id="product">
          <div className="hero-copy">
            <div className="hero-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="hero-badge-star">
                <path d="m12 2 2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17.2l-6.2 4.1 2.4-7.4L2 9.4h7.6z"/>
              </svg>
              with AI-powered EDA — no code required
            </div>
            <h1 className="hero-title">
              Drop data.<br /><span className="hero-title-gradient">Get answers.</span>
            </h1>
            <p className="hero-sub">
              edaverse profiles, cleans, and engineers features from your raw datasets — so analysts can focus on decisions, not data wrangling.
            </p>
            <div className="hero-actions">
              <button className="hero-primary" onClick={onGetStarted} type="button">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Upload your dataset
              </button>
              <button className="hero-secondary" onClick={onDemo} type="button">
                View demo
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"/>
                  <polyline points="12 5 19 12 12 19"/>
                </svg>
              </button>
            </div>
            <div className="hero-trust">
              <span>✓ No credit card required</span>
              <span>◇ Runs locally &amp; private</span>
              <span>⟨⟩ Open data formats</span>
            </div>
          </div>

          <div className="hero-product" aria-label="edaverse product preview">
            <div className="product-shell">
              <aside className="product-sidebar">
                <span className="product-dot" />
                <span />
                <span />
                <span />
              </aside>
              <div className="product-main">
                <div className="product-top">
                  <div>
                    <span className="product-kicker">customer_churn.csv</span>
                    <strong>Exploratory analysis</strong>
                  </div>
                  <button type="button">Report</button>
                </div>
                <div className="product-metrics">
                  {metricCards.map(([label, value]) => (
                    <div key={label}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
                <div className="product-grid">
                  <div className="product-panel product-columns">
                    <div className="product-panel-title">Column health</div>
                    {columns.map(([name, type, value]) => (
                      <div className="product-column" key={name}>
                        <div>
                          <span>{name}</span>
                          <em>{type}</em>
                        </div>
                        <div className="product-track">
                          <i style={{ width: `${value}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="product-panel product-chart">
                    <div className="product-panel-title">Distribution</div>
                    <div className="product-bars">
                      {[34, 52, 68, 84, 61, 76, 46, 89, 58, 70].map((height, index) => (
                        <span key={index} style={{ height: `${height}%` }} />
                      ))}
                    </div>
                    <div className="product-note">AI narrative found 3 cleanup priorities.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
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
            <h2>From raw file to trustworthy next step.</h2>
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

        <section className="cta">
          <div>
            <span>Ready when your next dataset is.</span>
            <h2>Open the workspace and start profiling.</h2>
          </div>
          <button className="hero-primary" onClick={onGetStarted} type="button">
            Start now
          </button>
        </section>
      </main>
    </div>
  )
}
