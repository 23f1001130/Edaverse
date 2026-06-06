import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import * as Sentry from '@sentry/react'
import App from './App.jsx'
import './index.css'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

if (!PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY in environment')
}

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_SENTRY_RELEASE,
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.1),
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ClerkProvider
      publishableKey={PUBLISHABLE_KEY}
      fallbackRedirectUrl={APP_URL}
      afterSignOutUrl={APP_URL}
    >
      <Sentry.ErrorBoundary fallback={<div className="app-error">Something went wrong.</div>}>
        <App />
      </Sentry.ErrorBoundary>
    </ClerkProvider>
  </React.StrictMode>
)
