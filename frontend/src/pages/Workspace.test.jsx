import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Workspace from './Workspace.jsx'

vi.mock('../components/Uploader.jsx', () => ({ default: () => <div>Upload a dataset</div> }))
vi.mock('../components/WorkspaceResults.jsx', () => ({ default: () => <div>Analysis</div> }))
vi.mock('../components/HistoryPanel.jsx', () => ({ default: () => <div>History</div> }))
vi.mock('../services/api.js', () => ({ fetchDataset: vi.fn(), uploadFile: vi.fn(), loadDemo: vi.fn(), apiFetch: vi.fn() }))

beforeEach(() => { localStorage.clear(); document.documentElement.removeAttribute('data-theme') })
afterEach(cleanup)

describe('Workspace appearance', () => {
  it('restores light mode and persists a switch back to dark', async () => {
    localStorage.setItem('edaverse_theme', 'light')
    render(<Workspace />)
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    await userEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(localStorage.getItem('edaverse_theme')).toBe('dark')
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeInTheDocument()
  })

  it('recovers from an invalid saved theme and disables analysis until data exists', () => {
    localStorage.setItem('edaverse_theme', 'unexpected')
    render(<Workspace />)
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(screen.getByRole('button', { name: 'Upload a file first' })).toBeDisabled()
  })
})
