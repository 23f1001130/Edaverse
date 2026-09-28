import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

vi.mock('../../services/api.js', () => ({
  apiFetch: vi.fn(() => Promise.resolve({ ok: false, json: () => Promise.resolve({}) })),
  getAuthHeaders: vi.fn(() => Promise.resolve({})),
}))

const { default: TargetTab } = await import('./TargetTab.jsx')

const schema = [
  { name: 'age', type: 'integer' },
  { name: 'tenure_months', type: 'float' },
  { name: 'contract_type', type: 'categorical' },
  { name: 'churn', type: 'boolean' },
  { name: 'signup_date', type: 'datetime' },
]

function makeData() {
  return { id: 'dataset-1', schema }
}

describe('TargetTab column picker', () => {
  it('groups candidate columns by type with counts', () => {
    render(<TargetTab data={makeData()} />)

    expect(screen.getByText(/Numeric.*2/)).toBeInTheDocument()
    expect(screen.getByText(/Categorical.*2/)).toBeInTheDocument()
    expect(screen.getByText(/Datetime.*1/)).toBeInTheDocument()
  })

  it('filters columns as the user types in the search box', async () => {
    const user = userEvent.setup()
    render(<TargetTab data={makeData()} />)

    const search = screen.getByPlaceholderText('Search columns…')
    await user.type(search, 'tenure')

    expect(screen.getByText('tenure_months')).toBeInTheDocument()
    expect(screen.queryByText('age')).not.toBeInTheDocument()
    expect(screen.queryByText('contract_type')).not.toBeInTheDocument()
  })

  it('shows an empty state when the search matches nothing', async () => {
    const user = userEvent.setup()
    render(<TargetTab data={makeData()} />)

    const search = screen.getByPlaceholderText('Search columns…')
    await user.type(search, 'zzz-no-match')

    expect(screen.getByText(/No columns match/)).toBeInTheDocument()
  })
})
