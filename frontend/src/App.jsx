import React, { lazy, Suspense, useState, useEffect } from 'react'
import { useAuth, useClerk, UserButton } from '@clerk/clerk-react'
import Landing from './pages/Landing.jsx'
const Workspace = lazy(() => import('./pages/Workspace.jsx'))
const AuthPage = lazy(() => import('./pages/AuthPage.jsx'))

const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: 'var(--bg-base)', gap: 16,
        }}>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            Something went wrong. Please reload the page.
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{ padding: '8px 20px', borderRadius: 6, cursor: 'pointer' }}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function SSOCallback() {
  const { handleRedirectCallback } = useClerk()

  useEffect(() => {
    handleRedirectCallback({
      afterSignInUrl: APP_URL,
      afterSignUpUrl: APP_URL,
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

function AppContent() {
  const { isSignedIn, isLoaded } = useAuth()
  const params = new URLSearchParams(window.location.search)
  const [view, setView] = useState(() => params.has('demo') ? 'workspace' : params.has('start') ? 'auth' : 'landing')
  const [startDemo, setStartDemo] = useState(() => params.has('demo'))

  useEffect(() => {
    if (params.has('start') || params.has('demo')) {
      params.delete('start')
      params.delete('demo')
      const query = params.toString()
      window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`)
    }
  }, [])

  useEffect(() => {
    if (isLoaded && isSignedIn && view === 'auth') {
      setView('workspace')
    }
  }, [isLoaded, isSignedIn])

  // Handle SSO callback URL — match on pathname only to avoid false positives.
  const _path = window.location.pathname.replace(/\/+$/, '') || '/'
  if (_path === '/sso-callback' || _path.endsWith('/sso-callback')) {
    return <SSOCallback />
  }

  if (!isLoaded && view !== 'landing') {
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
      <ErrorBoundary>
        <Landing
          isSignedIn={isSignedIn}
          userButton={isSignedIn ? <UserButton afterSignOutUrl="/" /> : null}
          onSignIn={() => setView('auth')}
          onGetStarted={() => {
            if (isSignedIn) { setStartDemo(false); setView('workspace') }
            else setView('auth')
          }}
          onDemo={() => { setStartDemo(true); setView('workspace') }}
        />
      </ErrorBoundary>
    )
  }

  if (view === 'auth') {
    return (
      <ErrorBoundary>
        <AuthPage onSuccess={() => setView('workspace')} onBack={() => setView('landing')} />
      </ErrorBoundary>
    )
  }

  return (
    <ErrorBoundary>
      <Workspace onHome={() => setView('landing')} autoDemo={startDemo} />
    </ErrorBoundary>
  )
}

export default function App() {
  return <Suspense fallback={<div className="app-loading" role="status">Opening workspace…</div>}><AppContent /></Suspense>
}
