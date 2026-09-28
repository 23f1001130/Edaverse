import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import OverviewTab from './OverviewTab.jsx'

function makeData(schema) {
  return {
    shape: { rows: 100, columns: schema.length },
    encoding: { encoding: 'utf-8', confidence: 1 },
    schema,
  }
}

describe('OverviewTab missingness list', () => {
  it('only shows columns that actually have missing values', () => {
    const schema = [
      { name: 'complete_a', type: 'integer', null_pct: 0 },
      { name: 'complete_b', type: 'text', null_pct: 0 },
      { name: 'sparse', type: 'float', null_pct: 12.5 },
    ]
    render(<OverviewTab data={makeData(schema)} eda={{}} />)

    expect(screen.getByText('sparse')).toBeInTheDocument()
    expect(screen.queryByText('complete_a')).not.toBeInTheDocument()
    expect(screen.queryByText('complete_b')).not.toBeInTheDocument()
  })

  it('shows a clean empty state when nothing is missing', () => {
    const schema = [
      { name: 'complete_a', type: 'integer', null_pct: 0 },
      { name: 'complete_b', type: 'text', null_pct: 0 },
    ]
    render(<OverviewTab data={makeData(schema)} eda={{}} />)

    expect(screen.getByText(/dataset is complete/i)).toBeInTheDocument()
  })

  it('does not pad the list with 0%-null columns when fewer than 8 have gaps', () => {
    const schema = [
      { name: 'a', type: 'integer', null_pct: 0 },
      { name: 'b', type: 'integer', null_pct: 0 },
      { name: 'c', type: 'integer', null_pct: 0 },
      { name: 'd', type: 'integer', null_pct: 0 },
      { name: 'e', type: 'integer', null_pct: 0 },
      { name: 'gap', type: 'float', null_pct: 4.0 },
    ]
    render(<OverviewTab data={makeData(schema)} eda={{}} />)

    expect(screen.getByText('gap')).toBeInTheDocument()
    // "0%" would only appear if a complete column got padded into the list
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
  })
})
