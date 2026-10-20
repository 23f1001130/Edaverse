import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import WorkspaceResults from './WorkspaceResults.jsx'

vi.mock('./tabs/OverviewTab.jsx', () => ({ default: () => <div>Dataset overview</div> }))
vi.mock('./tabs/DistributionsTab.jsx', () => ({ default: ({ activeCol }) => <div>Distribution for {activeCol || 'all columns'}</div> }))
vi.mock('./tabs/StepsTab.jsx', () => ({ default: () => <div>Dataset preparation steps</div> }))

const data = { filename: 'sample.csv', schema: [
  { name: 'age', type: 'integer', null_pct: 0 },
  { name: 'monthly_charges', type: 'float', null_pct: 2 },
  { name: 'contract', type: 'string', null_pct: 0 },
] }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('Analysis navigation', () => {
  it('lets the user retry failed analysis without another upload', async () => {
    localStorage.setItem('edaverse_workspace_tour_seen', 'true')
    const fetchAnalysis = vi.fn().mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce({
      ok: true,
      body: { getReader: () => ({ read: vi.fn()
        .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"progress":1,"data":{}}\n\n') })
        .mockResolvedValueOnce({ done: true }) }) },
    })
    vi.stubGlobal('fetch', fetchAnalysis)
    render(<WorkspaceResults data={{ ...data, id: 'retry-sample' }} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Retry without uploading')
    await userEvent.click(screen.getByRole('button', { name: 'Retry analysis' }))
    expect(await screen.findByText('Dataset overview')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(fetchAnalysis).toHaveBeenCalledTimes(2)
  })

  it('explains empty column searches and lets the user restore the list', async () => {
    render(<WorkspaceResults data={data} />)
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search dataset columns' }), 'missing column')
    expect(screen.getByRole('status')).toHaveTextContent('No columns match')
    expect(screen.queryByRole('button', { name: /monthly_charges/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Show all columns' }))
    expect(screen.getByRole('button', { name: /monthly_charges/ })).toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('')
  })

  it('can hide and reopen columns without losing the search', async () => {
    render(<WorkspaceResults data={data} />)
    await userEvent.type(screen.getByRole('searchbox'), 'age')
    await userEvent.click(screen.getByRole('button', { name: 'Hide columns' }))
    expect(screen.queryByRole('complementary', { name: 'Dataset columns' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show columns' })).toHaveAttribute('aria-expanded', 'false')
    await userEvent.click(screen.getByRole('button', { name: 'Show columns' }))
    expect(screen.getByRole('searchbox')).toHaveValue('age')
  })

  it('opens the distribution for the chosen column', async () => {
    render(<WorkspaceResults data={data} />)
    await userEvent.click(screen.getByRole('button', { name: /monthly_charges/ }))
    expect(await screen.findByText('Distribution for monthly_charges')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Distributions' })).toHaveAttribute('aria-selected', 'true')
  })

  it('supports arrow keys, wrapping, Home, and End in the analysis tabs', async () => {
    render(<WorkspaceResults data={data} />)
    screen.getByRole('tab', { name: 'Overview' }).focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Distributions' })).toHaveFocus()
    expect(await screen.findByRole('tabpanel', { name: 'Distributions' })).toHaveTextContent('Distribution for all columns')
    await userEvent.keyboard('{End}')
    expect(screen.getByRole('tab', { name: 'Steps Applied' })).toHaveFocus()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveFocus()
    await userEvent.keyboard('{ArrowLeft}')
    expect(screen.getByRole('tab', { name: 'Steps Applied' })).toHaveFocus()
    await userEvent.keyboard('{Home}')
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveFocus()
  })
})
