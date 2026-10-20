import React, { Suspense, act } from 'react'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderToString } from 'react-dom/server'
import { hydrateRoot } from 'react-dom/client'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'
import Landing from './pages/Landing.jsx'
import FeaturePage from './pages/FeaturePage.jsx'
import { featurePages } from './seo/pages.js'

const session = vi.hoisted(() => ({ isLoaded: true, isSignedIn: false }))
vi.mock('@clerk/clerk-react', () => ({
  useAuth: () => session,
  useClerk: () => ({ handleRedirectCallback: vi.fn().mockResolvedValue(undefined) }),
  UserButton: () => <span>Account</span>,
}))
vi.mock('./pages/Workspace.jsx', () => ({ default: ({ autoDemo }) => <div>Workspace: {autoDemo ? 'demo' : 'own data'}</div> }))
vi.mock('./pages/AuthPage.jsx', () => ({ default: () => <div>Sign-in form</div> }))

beforeEach(() => {
  window.history.replaceState(null, '', '/')
  session.isLoaded = true
  session.isSignedIn = false
})
afterEach(cleanup)

describe('Public pages and workspace entry', () => {
  it('shows the homepage before authentication has loaded', () => {
    session.isLoaded = false
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('No-code data analysis')
  })

  it.each(['/sso-callback', '/sso-callback/'])('preserves the sign-in callback at %s', path => {
    window.history.replaceState(null, '', path)
    render(<App />)
    expect(screen.getByText('Signing you in…')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })

  it('keeps the homepage demo action working', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('link', { name: /view demo/i }))
    expect(await screen.findByText('Workspace: demo')).toBeInTheDocument()
  })

  it('opens the sample dataset from a feature-page demo link', async () => {
    window.history.replaceState(null, '', '/?demo=1')
    render(<App />)
    expect(await screen.findByText('Workspace: demo')).toBeInTheDocument()
    expect(window.location.search).toBe('')
  })

  it('sends visitors from feature pages to sign-in and opens the workspace after sign-in', async () => {
    window.history.replaceState(null, '', '/?start=1')
    const { rerender } = render(<App />)
    expect(await screen.findByText('Sign-in form')).toBeInTheDocument()
    session.isSignedIn = true
    rerender(<App />)
    expect(await screen.findByText('Workspace: own data')).toBeInTheDocument()
    expect(window.location.search).toBe('')
  })

  it('hydrates the static homepage without replacing its content', async () => {
    const container = document.createElement('div')
    container.innerHTML = renderToString(<Suspense fallback={null}><Landing /></Suspense>)
    document.body.append(container)
    const originalHeading = container.querySelector('h1')
    const errors = vi.fn()
    let root
    await act(async () => { root = hydrateRoot(container, <App />, { onRecoverableError: errors }) })
    await waitFor(() => expect(container.querySelector('h1')).toBe(originalHeading))
    expect(errors).not.toHaveBeenCalled()
    await act(async () => root.unmount())
    container.remove()
  })

  it.each(featurePages)('hydrates $label without an auth provider', async page => {
    const container = document.createElement('div')
    container.innerHTML = renderToString(<FeaturePage page={page} />)
    document.body.append(container)
    const originalHeading = container.querySelector('h1')
    const errors = vi.fn()
    let root
    await act(async () => { root = hydrateRoot(container, <FeaturePage page={page} />, { onRecoverableError: errors }) })
    expect(container.querySelector('h1')).toBe(originalHeading)
    expect(errors).not.toHaveBeenCalled()
    await act(async () => root.unmount())
    container.remove()
  })
})
