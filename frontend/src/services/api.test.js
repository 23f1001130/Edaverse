import { afterEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import { uploadFile } from './api.js'

afterEach(() => { vi.restoreAllMocks(); delete window.Clerk })

describe('Upload authentication', () => {
  it('requests a fresh session token before sending a potentially long upload', async () => {
    const getToken = vi.fn().mockResolvedValue('fresh-token')
    window.Clerk = { session: { getToken } }
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { success: true } })
    await uploadFile(new File(['value\n1'], 'data.csv'))
    expect(getToken).toHaveBeenCalledWith({ skipCache: true })
    expect(post.mock.calls[0][2].headers.Authorization).toBe('Bearer fresh-token')
  })

  it('stops an authenticated upload when token refresh fails', async () => {
    window.Clerk = { session: { getToken: vi.fn().mockRejectedValue(new Error('Session expired')) } }
    const post = vi.spyOn(axios, 'post')
    await expect(uploadFile(new File(['value\n1'], 'data.csv'))).rejects.toMatchObject({ code: 'UPLOAD_AUTH_REQUIRED', message: expect.stringContaining('sign in again') })
    expect(post).not.toHaveBeenCalled()
  })

  it('still permits an intentional guest upload without a session', async () => {
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { success: true } })
    await uploadFile(new File(['value\n1'], 'data.csv'))
    expect(post).toHaveBeenCalled()
    expect(post.mock.calls[0][2].headers.Authorization).toBeUndefined()
  })
})
