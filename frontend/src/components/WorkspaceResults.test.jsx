import { act, cleanup, render, screen } from '@testing-library/react'
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
  it('shows the preview while processing continues and replaces it with full-data results', async () => {
    localStorage.setItem('edaverse_workspace_tour_seen', 'true')
    let finish
    const encode = event => new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)
    const read = vi.fn()
      .mockResolvedValueOnce({ done: false, value: encode({ stage: 'preview', progress: .03, label: 'Preview ready', data: {
        analysis: { status: 'preview', rows: 10000, total_rows: 525461 },
      } }) })
      .mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
      .mockResolvedValueOnce({ done: true })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: { getReader: () => ({ read }) } }))
    render(<WorkspaceResults data={{ ...data, id: 'progressive' }} />)
    expect(await screen.findByRole('note')).toHaveTextContent('Preview: first 10,000 of 525,461 rows')
    expect(await screen.findByText('Dataset overview')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Full dataset analysis' })).toBeInTheDocument()
    await act(async () => finish({ done: false, value: encode({ stage: 'complete', progress: 1, data: {
      analysis: { status: 'complete', full_metrics: ['histograms'], rows: 525461, sample_rows: 10000 },
    } }) }))
    expect(screen.getByRole('note')).toHaveTextContent('Full dataset analyzed: 525,461 rows')
    expect(screen.getByRole('note')).toHaveTextContent('sample drawn across the dataset')
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('keeps the preview and offers retry when the stream closes before completion', async () => {
    localStorage.setItem('edaverse_workspace_tour_seen', 'true')
    const read = vi.fn()
      .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"stage":"preview","progress":0.03,"data":{"analysis":{"status":"preview","rows":10000,"total_rows":500000}}}\n\n') })
      .mockResolvedValueOnce({ done: true })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: { getReader: () => ({ read }) } }))
    render(<WorkspaceResults data={{ ...data, id: 'interrupted' }} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Any results shown are partial')
    expect(screen.getByRole('note')).toHaveTextContent('Preview: first 10,000')
    expect(await screen.findByText('Dataset overview')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry analysis' })).toBeInTheDocument()
  })

  it('discloses when charts use a preview of the retained full dataset', async () => {
    localStorage.setItem('edaverse_workspace_tour_seen', 'true')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: { getReader: () => ({ read: vi.fn()
      .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"progress":1,"data":{"analysis":{"sampled":true,"rows":10000,"total_rows":500000}}}\n\n') })
      .mockResolvedValueOnce({ done: true }) }) } }))
    render(<WorkspaceResults data={{ ...data, id: 'large-sample' }} />)
    expect(await screen.findByRole('note')).toHaveTextContent('10,000 of 500,000 rows')
    expect(screen.getByRole('note')).toHaveTextContent('All parsed rows are retained')
  })
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
