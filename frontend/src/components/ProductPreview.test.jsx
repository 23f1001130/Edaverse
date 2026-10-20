import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ProductPreview from './ProductPreview.jsx'

beforeEach(() => { vi.spyOn(document, 'hidden', 'get').mockReturnValue(false) })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('Interactive homepage sample', () => {
  it('changes the chart and insight when a visitor selects a column', async () => {
    render(<ProductPreview />)
    expect(screen.getByRole('img', { name: 'age distribution in customer_churn.csv' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Explore contract_type' }))
    expect(screen.getByRole('img', { name: 'contract_type category counts in customer_churn.csv' })).toBeInTheDocument()
    expect(screen.getByText(/Monthly contracts are the largest group/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Resume sample tour' })).toBeInTheDocument()
  })

  it('switches sample metrics and opens a useful report with the working demo action', async () => {
    const openDemo = vi.fn()
    render(<ProductPreview onDemo={openDemo} />)
    await userEvent.click(screen.getByRole('button', { name: 'Show Sales export sample' }))
    expect(screen.getByText('sales_export.csv')).toBeInTheDocument()
    expect(screen.getByText('24,816')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'order_value distribution in sales_export.csv' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Report', exact: true }))
    expect(screen.getByRole('region', { name: 'Sample analysis report' })).toHaveTextContent('Review missing shipping durations')
    await userEvent.click(screen.getByRole('link', { name: 'Open full demo →' }))
    expect(openDemo).toHaveBeenCalledTimes(1)
  })

  it('cycles samples and stops while hovered or focused', () => {
    vi.useFakeTimers()
    render(<ProductPreview />)
    act(() => vi.advanceTimersByTime(8000))
    expect(screen.getByText('sales_export.csv')).toBeInTheDocument()
    const preview = screen.getByRole('region', { name: 'Interactive sample analysis' })
    fireEvent.mouseEnter(preview)
    act(() => vi.advanceTimersByTime(16000))
    expect(screen.getByText('sales_export.csv')).toBeInTheDocument()
    fireEvent.mouseLeave(preview)
    act(() => screen.getByRole('button', { name: 'Report', exact: true }).focus())
    act(() => vi.advanceTimersByTime(16000))
    expect(screen.getByText('sales_export.csv')).toBeInTheDocument()
    act(() => screen.getByRole('button', { name: 'Report', exact: true }).blur())
    act(() => vi.advanceTimersByTime(8000))
    expect(screen.getByText('sensor_readings.csv')).toBeInTheDocument()
  })

  it('lets visitors pause and resume the automatic tour', () => {
    vi.useFakeTimers()
    render(<ProductPreview />)
    fireEvent.click(screen.getByRole('button', { name: 'Pause sample tour' }))
    act(() => vi.advanceTimersByTime(16000))
    expect(screen.getByText('customer_churn.csv')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Resume sample tour' }))
    act(() => vi.advanceTimersByTime(8000))
    expect(screen.getByText('sales_export.csv')).toBeInTheDocument()
  })

  it('starts paused for visitors who prefer reduced motion', () => {
    vi.useFakeTimers()
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
    render(<ProductPreview />)
    expect(screen.getByRole('button', { name: 'Resume sample tour' })).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(24000))
    expect(screen.getByText('customer_churn.csv')).toBeInTheDocument()
  })
})
