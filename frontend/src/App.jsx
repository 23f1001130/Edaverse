import React, { useState, useEffect } from 'react'
import { useAuth, useClerk } from '@clerk/clerk-react'
import Landing from './pages/Landing.jsx'
import Workspace from './pages/Workspace.jsx'
import AuthPage from './pages/AuthPage.jsx'

function SSOCallback() {
  const { handleRedirectCallback } = useClerk()

  useEffect(() => {
    handleRedirectCallback({
      afterSignInUrl: '/',
      afterSignUpUrl: '/',
    }).catch(console.error)
  }, [])

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-base)', gap: 16
    }}>
      <div style={{
        width: 32, height: 32,
        border: '3px solid var(--border-default)',
        borderTopColor: 'var(--accent)', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Signing you in…</div>
    </div>
  )
}

export default function App() {
  const { isSignedIn, isLoaded } = useAuth()
  const [view, setView] = useState('landing')
  const [startDemo, setStartDemo] = useState(false)

  // Handle SSO callback URL
  if (window.location.href.includes('sso-callback')) {
    return <SSOCallback />
  }

  useEffect(() => {
    if (isLoaded && isSignedIn && view === 'auth') {
      setView('workspace')
    }
  }, [isLoaded, isSignedIn])

  if (!isLoaded) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'var(--bg-base)'
      }}>
        <div style={{
          width: 32, height: 32,
          border: '3px solid var(--border-default)',
          borderTopColor: 'var(--accent)', borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
      </div>
    )
  }

  if (view === 'landing') {
    return (
      <Landing
        onSignIn={() => setView('auth')}
        onGetStarted={() => {
          if (isSignedIn) { setStartDemo(false); setView('workspace') }
          else setView('auth')
        }}
        onDemo={() => { setStartDemo(true); setView('workspace') }}
      />
    )
  }

  if (view === 'auth') {
    return <AuthPage onSuccess={() => setView('workspace')} onBack={() => setView('landing')} />
  }

  return <Workspace onHome={() => setView('landing')} autoDemo={startDemo} />
}