import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const { uploadFile, fetchConfig } = vi.hoisted(() => ({
  uploadFile: vi.fn(),
  fetchConfig: vi.fn(),
}))
vi.mock('../services/api.js', () => ({ uploadFile, fetchConfig }))

const { fireToast } = vi.hoisted(() => ({ fireToast: vi.fn() }))
vi.mock('../services/toast.js', () => ({ fireToast }))

const { default: Uploader } = await import('./Uploader.jsx')

function makeFile(sizeMb, name = 'data.csv') {
  const bytes = Math.round(sizeMb * 1024 * 1024)
  return new File([new Uint8Array(bytes)], name, { type: 'text/csv' })
}

describe('Uploader size limits', () => {
  beforeEach(() => {
    uploadFile.mockReset()
    fetchConfig.mockReset()
    fireToast.mockReset()
    fetchConfig.mockResolvedValue({ max_upload_mb: 100, large_file_threshold_mb: 50 })
  })

  it('shows the configured max size instead of a hardcoded value', async () => {
    render(<Uploader onResult={vi.fn()} onError={vi.fn()} loading={false} setLoading={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Maximum file size: 100 MB')).toBeInTheDocument())
  })

  it('rejects a file over the configured max without ever calling uploadFile', async () => {
    const onError = vi.fn()
    render(<Uploader onResult={vi.fn()} onError={onError} loading={false} setLoading={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Maximum file size: 100 MB')).toBeInTheDocument())

    const input = document.querySelector('input[type="file"]')
    await userEvent.upload(input, makeFile(120))

    await waitFor(() => expect(onError).toHaveBeenCalled())
    expect(onError.mock.calls[0][0]).toMatch(/over the 100MB limit/)
    expect(uploadFile).not.toHaveBeenCalled()
  })

  it('warns but still uploads a file over the large-file threshold', async () => {
    uploadFile.mockResolvedValue({ success: true })
    const onResult = vi.fn()
    render(<Uploader onResult={onResult} onError={vi.fn()} loading={false} setLoading={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Maximum file size: 100 MB')).toBeInTheDocument())

    const input = document.querySelector('input[type="file"]')
    await userEvent.upload(input, makeFile(60))

    await waitFor(() => expect(uploadFile).toHaveBeenCalled())
    expect(fireToast).toHaveBeenCalledWith(expect.stringMatching(/Large file/), 'info')
  })

  it('uploads a normal-sized file with no warning at all', async () => {
    uploadFile.mockResolvedValue({ success: true })
    render(<Uploader onResult={vi.fn()} onError={vi.fn()} loading={false} setLoading={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Maximum file size: 100 MB')).toBeInTheDocument())

    const input = document.querySelector('input[type="file"]')
    await userEvent.upload(input, makeFile(1))

    await waitFor(() => expect(uploadFile).toHaveBeenCalled())
    expect(fireToast).not.toHaveBeenCalled()
  })
})
