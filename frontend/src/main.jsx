import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import * as Sentry from '@sentry/react'
import App from './App.jsx'
import FeaturePage from './pages/FeaturePage.jsx'
import { findPage } from './seo/pages.js'
import './index.css'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_SENTRY_RELEASE,
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.1),
  })
}

const page = findPage(window.location.pathname)
const isFeaturePage = page && page.path !== '/'
const root = document.getElementById('root')
const query = new URLSearchParams(window.location.search)
const interactiveEntry = query.has('start') || query.has('demo')

// Public guides are independent of authentication. Without a configured auth key,
// retain the generated HTML so marketing content remains available.
if (isFeaturePage) {
  const content = <React.StrictMode><FeaturePage page={page} /></React.StrictMode>
  if (root.dataset.prerendered) ReactDOM.hydrateRoot(root, content)
  else ReactDOM.createRoot(root).render(content)
} else if (PUBLISHABLE_KEY) {
  const content = (
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
  if (root.dataset.prerendered && page?.path === '/' && !interactiveEntry) ReactDOM.hydrateRoot(root, content)
  else ReactDOM.createRoot(root).render(content)
} else {
  console.error('Workspace unavailable: missing VITE_CLERK_PUBLISHABLE_KEY')
}
