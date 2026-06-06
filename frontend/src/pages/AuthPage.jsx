import React from 'react'
import { SignIn, SignUp } from '@clerk/clerk-react'
import './AuthPage.css'

const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

export default function AuthPage({ onSuccess, onBack }) {
  const [mode, setMode] = React.useState('signup') // signup | signin

  const appearance = {
    layout: {
      logoPlacement: 'none',
      showOptionalFields: false,
    },
    variables: {
      colorPrimary: '#3b82f6',
      colorBackground: '#0a0e1a',
      colorInputBackground: '#121829',
      colorInputText: '#e8edf7',
      colorText: '#e8edf7',
      colorTextSecondary: '#9aa7bd',
      colorNeutral: '#242d42',
      borderRadius: '10px',
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: '14px',
    },
    elements: {
      rootBox: { width: '100%' },
      card: { background: 'transparent', border: 'none', boxShadow: 'none', padding: '0', width: '100%' },
      header: { display: 'none' },
      socialButtonsBlockButton: {
        background: '#121829',
        border: '1px solid #242d42',
        color: '#e8edf7',
        fontWeight: '600',
        minHeight: '44px',
      },
      socialButtonsBlockButtonText: { color: '#e8edf7' },
      dividerLine: { background: '#242d42' },
      dividerText: { color: '#5f6b82', fontWeight: '600' },
      formFieldInput: {
        background: '#121829',
        border: '1px solid #242d42',
        color: '#e8edf7',
        minHeight: '44px',
      },
      formFieldInputShowPasswordButton: { color: '#5f6b82' },
      formFieldLabel: { color: '#9aa7bd', fontWeight: '600' },
      formButtonPrimary: {
        background: '#3b82f6',
        color: '#ffffff',
        fontWeight: '700',
        minHeight: '44px',
        boxShadow: '0 4px 20px rgba(59,130,246,0.3)',
      },
      footerAction: { display: 'none' },
      formFieldAction: { color: '#60a5fa', fontWeight: '600' },
      identityPreviewText: { color: '#e8edf7' },
      identityPreviewEditButton: { color: '#60a5fa' },
      formResendCodeLink: { color: '#60a5fa', fontWeight: '600' },
      otpCodeField: { gap: '8px' },
      otpCodeFieldInput: { background: '#121829', border: '1px solid #242d42', color: '#e8edf7' },
    },
  }

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <section className="auth-story" aria-label="Product preview">
          <button className="auth-back" onClick={onBack} type="button">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            Back
          </button>
          <div className="auth-logo">
            <span className="auth-logo-mark">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1.5"/>
                <rect x="14" y="3" width="7" height="7" rx="1.5"/>
                <rect x="3" y="14" width="7" height="7" rx="1.5"/>
                <rect x="14" y="14" width="7" height="7" rx="1.5"/>
              </svg>
            </span>
            <span className="auth-logo-name">edaverse</span>
          </div>

          <div className="auth-story-copy">
            <span className="auth-kicker">Private data workspace</span>
            <h1>Secure access for serious analysis.</h1>
            <p>Keep uploads, cleaning decisions, AI notes, and export-ready datasets attached to one protected workspace.</p>
          </div>

          <div className="auth-preview">
            <div className="auth-preview-head">
              <div>
                <span>workspace audit</span>
                <strong>customer_churn.csv</strong>
              </div>
              <em>Live</em>
            </div>
            <div className="auth-preview-metrics">
              <div><span>Datasets</span><strong>12</strong></div>
              <div><span>Exports</span><strong>31</strong></div>
              <div><span>Quality</span><strong>94</strong></div>
            </div>
            <div className="auth-preview-body">
              <div className="auth-preview-chart" aria-hidden="true">
                {[72, 46, 88, 62, 54, 79, 41].map((height, index) => (
                  <span key={index} style={{ height: `${height}%` }} />
                ))}
              </div>
              <div className="auth-preview-list">
                <span><i /> Email verified</span>
                <span><i /> Analysis history synced</span>
                <span><i /> Demo access available</span>
              </div>
            </div>
          </div>

          <div className="auth-assurance">
            <span>Verified sign-in</span>
            <span>No raw-data marketing use</span>
            <span>Domain-ready email links</span>
          </div>
        </section>

        <section className="auth-panel" aria-label="Authentication form">
          <div className="auth-panel-head">
            <span className="auth-panel-eyebrow">Account access</span>
            <h2>{mode === 'signup' ? 'Create your workspace' : 'Sign in to continue'}</h2>
            <p>{mode === 'signup' ? 'Start with secure access and saved analysis history.' : 'Open your saved datasets and continue your analysis.'}</p>
          </div>

          <div className="auth-switch" role="tablist" aria-label="Authentication mode">
            <button
              className={mode === 'signup' ? 'active' : ''}
              onClick={() => setMode('signup')}
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
            >
              Create account
            </button>
            <button
              className={mode === 'signin' ? 'active' : ''}
              onClick={() => setMode('signin')}
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
            >
              Sign in
            </button>
          </div>

          <div className="auth-card">
            {mode === 'signup' ? (
              <SignUp fallbackRedirectUrl={APP_URL} appearance={appearance} />
            ) : (
              <SignIn fallbackRedirectUrl={APP_URL} appearance={appearance} />
            )}
          </div>

          <div className="auth-footnotes" aria-label="Security details">
            <span>Session protected</span>
            <span>Private uploads</span>
            <span>Domain-ready emails</span>
          </div>
        </section>
      </div>
    </div>
  )
}
