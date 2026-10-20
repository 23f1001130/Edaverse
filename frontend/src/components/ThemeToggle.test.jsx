import { cleanup, render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import Landing from '../pages/Landing.jsx'
import FeaturePage from '../pages/FeaturePage.jsx'
import { featurePages } from '../seo/pages.js'

beforeEach(() => { localStorage.clear(); document.documentElement.dataset.theme = 'dark' })
afterEach(cleanup)

describe('Theme choice before sign-in', () => {
  it('lets a signed-out visitor change theme and keeps the choice on another public page', async () => {
    const landing = render(<Landing />)
    expect(screen.getByRole('link', { name: 'Sign in', exact: true })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(localStorage.getItem('edaverse_theme')).toBe('light')
    landing.unmount()
    render(<FeaturePage page={featurePages[0]} />)
    expect(screen.getByRole('button', { name: 'Switch to dark mode' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })

  it('updates the public-page button when the preference changes in another tab', () => {
    render(<Landing />)
    act(() => {
      localStorage.setItem('edaverse_theme', 'light')
      window.dispatchEvent(new StorageEvent('storage', { key: 'edaverse_theme', newValue: 'light' }))
    })
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(screen.getByRole('button', { name: 'Switch to dark mode' })).toBeInTheDocument()
  })
})
