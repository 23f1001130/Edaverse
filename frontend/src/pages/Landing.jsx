import React from 'react'
import './Landing.css'

export default function Landing({ onGetStarted, onDemo }) {
  return (
    <div className="landing">
      {/* Nav */}
      <nav className="lnav">
        <div className="lnav-logo">
          <span className="lnav-mark">◧</span>
          <span className="lnav-name">edaverse</span>
        </div>
        <div className="lnav-links">
          <a href="#product">Product</a>
          <a href="#features">Features</a>
        </div>
        <div className="lnav-actions">
          <button className="lnav-signin" onClick={onGetStarted}>Sign in</button>
          <button className="lnav-cta" onClick={onGetStarted}>Get started</button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-left">
          <div className="hero-badge">
            <span className="hero-badge-dot">✦</span> Now with AI-powered narrative
          </div>
          <h1 className="hero-title">
            Drop data.<br />Get answers.
          </h1>
          <p className="hero-sub">
            edaverse profiles, cleans, and engineers features from your raw
            datasets automatically — so you can focus on building the model.
          </p>
          <div className="hero-actions">
            <button className="hero-primary" onClick={onGetStarted}>
              <span>↑</span> Upload your dataset
            </button>
            <button className="hero-secondary" onClick={onDemo}>
              View demo →
            </button>
          </div>
          <div className="hero-trust">
            <span>✓ No credit card required</span>
            <span>◇ Runs locally &amp; private</span>
            <span>⟨⟩ Open data formats</span>
          </div>
        </div>

        <div className="hero-right">
          <div className="hero-window">
            <div className="hw-bar">
              <span className="hw-dot red"></span>
              <span className="hw-dot amber"></span>
              <span className="hw-dot green"></span>
              <span className="hw-title">customer_churn.csv — edaverse</span>
            </div>
            <div className="hw-body">
              <div className="hw-sidebar">
                <div className="hw-search"></div>
                <div className="hw-col"><span>age</span><span className="hw-tag num">NUM</span></div>
                <div className="hw-col"><span>tenure_months</span><span className="hw-tag num">NUM</span></div>
                <div className="hw-col"><span>monthly_charges</span><span className="hw-tag num">NUM</span></div>
                <div className="hw-col"><span>contract_type</span><span className="hw-tag cat">CAT</span></div>
                <div className="hw-col"><span>churn</span><span className="hw-tag cat">CAT</span></div>
              </div>
              <div className="hw-main">
                <div className="hw-stats">
                  <div className="hw-stat"><div className="hw-stat-l">Rows</div><div className="hw-stat-v">7,043</div></div>
                  <div className="hw-stat"><div className="hw-stat-l">Columns</div><div className="hw-stat-v">12</div></div>
                  <div className="hw-stat"><div className="hw-stat-l">Null %</div><div className="hw-stat-v">8.4%</div></div>
                  <div className="hw-stat"><div className="hw-stat-l">Dupes</div><div className="hw-stat-v">23</div></div>
                </div>
                <div className="hw-chart">
                  <div className="hw-chart-label">age distribution</div>
                  <div className="hw-bars">
                    {[40,55,70,95,60,75,50,85,65,70,55,35].map((h,i) => (
                      <div key={i} className="hw-bar" style={{height: `${h}%`}}></div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="hero-stats-bar">
        <span>Works with CSV · Excel · JSON · Parquet</span>
        <span>Private — your data never leaves your machine</span>
        <span>&lt; 30s average processing time</span>
        <span>Trustworthy stats, computed not guessed</span>
      </div>

      {/* Features */}
      <section className="features" id="features">
        <h2 className="features-title">Everything between raw data and model training</h2>
        <p className="features-sub">edaverse handles the 80% of data science work that isn't modeling.</p>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon" style={{background:'var(--accent-glow)', color:'var(--accent-light)'}}>↑</div>
            <h3>Ingest anything</h3>
            <p>Drop a CSV, Excel workbook, JSON, or Parquet file. We detect encoding, schema, and structure automatically — even messy multi-header files.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon" style={{background:'var(--green-bg)', color:'var(--green)'}}>▥</div>
            <h3>Deep profiling</h3>
            <p>Column-level quality scores, null analysis, outlier detection, cardinality, and correlation heatmaps — all in one pass.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon" style={{background:'var(--purple-bg)', color:'var(--purple)'}}>✦</div>
            <h3>AI narrative</h3>
            <p>A plain-English summary of what your data contains, what's wrong with it, and which features to engineer first — running locally via Ollama.</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta">
        <h2>Your data, cleaned and ready.</h2>
        <p>Start with your first dataset — no setup, no infrastructure.</p>
        <button className="hero-primary" onClick={onGetStarted}>
          <span>↑</span> Upload your dataset
        </button>
      </section>

      <footer className="lfooter">
        <span>edaverse</span>
        <span>Built for analysts who'd rather not babysit a notebook.</span>
      </footer>
    </div>
  )
}
