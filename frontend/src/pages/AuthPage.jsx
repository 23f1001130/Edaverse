import React from 'react'
import { SignIn, SignUp } from '@clerk/clerk-react'
import './AuthPage.css'

export default function AuthPage({ onSuccess, onBack }) {
  const [mode, setMode] = React.useState('signup') // signup | signin

  const appearance = {
    layout: {
      logoPlacement: 'none',
      showOptionalFields: false,
    },
    variables: {
      colorPrimary: '#3b82f6',
      colorBackground: '#0d1117',
      colorInputBackground: '#161b22',
      colorInputText: '#e8edf7',
      colorText: '#e8edf7',
      colorTextSecondary: '#8b949e',
      colorNeutral: '#30363d',
      borderRadius: '10px',
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: '14px',
    },
    elements: {
      rootBox: { width: '100%' },
      card: { background: 'transparent', border: 'none', boxShadow: 'none', padding: '0' },
      headerTitle: { color: '#e8edf7', fontSize: '22px', fontWeight: '700' },
      headerSubtitle: { color: '#8b949e' },
      socialButtonsBlockButton: { background: '#161b22', border: '1px solid #30363d', color: '#e8edf7', fontWeight: '500' },
      dividerLine: { background: '#30363d' },
      dividerText: { color: '#8b949e' },
      formFieldInput: { background: '#161b22', border: '1px solid #30363d', color: '#e8edf7' },
      formFieldLabel: { color: '#8b949e' },
      formButtonPrimary: { background: '#3b82f6', fontWeight: '600' },
      footerActionLink: { color: '#3b82f6' },
    },
  }

  return (
    <div className="auth-page">
      <div className="auth-bg" />
      <div className="auth-container">
        {/* Header */}
        <div className="auth-header">
          <button className="auth-back" onClick={onBack}>← Back</button>
          <div className="auth-logo">
            <span className="auth-logo-mark">◧</span>
            <span className="auth-logo-name">edaverse</span>
          </div>
        </div>

        {/* Toggle */}
        <div style={{ display: 'flex', gap: 8, background: 'var(--bg-card)', border: '0.5px solid var(--border-default)', borderRadius: 10, padding: 4, width: '100%' }}>
          <button onClick={() => setMode('signup')} style={{ flex: 1, padding: '8px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, background: mode === 'signup' ? 'var(--accent)' : 'transparent', color: mode === 'signup' ? '#fff' : 'var(--text-secondary)', transition: 'all .15s' }}>
            Create account
          </button>
          <button onClick={() => setMode('signin')} style={{ flex: 1, padding: '8px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, background: mode === 'signin' ? 'var(--accent)' : 'transparent', color: mode === 'signin' ? '#fff' : 'var(--text-secondary)', transition: 'all .15s' }}>
            Sign in
          </button>
        </div>

        {/* Clerk component */}
        <div className="auth-card">
          {mode === 'signup' ? (
            <SignUp afterSignUpUrl="/" appearance={appearance} />
          ) : (
            <SignIn afterSignInUrl="/" appearance={appearance} />
          )}
        </div>

        <p className="auth-footer">
          Your data never leaves your machine. We only use your account to save your work.
        </p>
      </div>
    </div>
  )
}