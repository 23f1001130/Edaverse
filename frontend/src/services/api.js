import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

// Retry GET requests up to 2 times on network errors or 5xx responses.
axios.interceptors.response.use(null, async (error) => {
  const config = error.config
  if (!config || config.method !== 'get') return Promise.reject(error)
  config._retryCount = (config._retryCount || 0) + 1
  if (config._retryCount > 2) return Promise.reject(error)
  const status = error.response?.status
  if (status && status < 500) return Promise.reject(error)
  await new Promise(r => setTimeout(r, config._retryCount * 600))
  return axios(config)
})

export async function getAuthHeaders() {
  const headers = {}
  try {
    const token = await window.Clerk?.session?.getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  } catch {}
  try {
    headers['X-Request-ID'] = crypto.randomUUID()
  } catch {}
  return headers
}

export async function uploadFile(file, onProgress, headerRow = null) {
  const form = new FormData()
  form.append('file', file)
  if (headerRow !== null) form.append('header_row', headerRow)
  const headers = await getAuthHeaders()

  const res = await axios.post(`${BASE}/api/upload`, form, {
    headers,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    }
  })
  return res.data
}

export async function fetchDatasets({ limit = 20, offset = 0 } = {}) {
  const headers = await getAuthHeaders()
  const res = await axios.get(`${BASE}/api/datasets`, { headers, params: { limit, offset } })
  return res.data
}

export async function fetchDataset(id) {
  const headers = await getAuthHeaders()
  const res = await axios.get(`${BASE}/api/datasets/${id}`, { headers })
  return res.data
}

export async function deleteDataset(id) {
  const headers = await getAuthHeaders()
  const res = await axios.delete(`${BASE}/api/datasets/${id}`, { headers })
  return res.data
}

export async function loadDemo() {
  const headers = await getAuthHeaders()
  const res = await axios.post(`${BASE}/api/demo`, {}, { headers })
  return res.data
}

export async function fetchConfig() {
  const headers = await getAuthHeaders()
  const res = await axios.get(`${BASE}/api/config`, { headers })
  return res.data
}

// Wraps fetch() with automatic auth headers and retry-on-failure for GET requests.
// Use for regular (non-streaming) API calls instead of bare fetch().
export async function apiFetch(url, options = {}) {
  const authHeaders = await getAuthHeaders()
  const merged = { ...options, headers: { ...authHeaders, ...options.headers } }
  const isRead = !options.method || options.method.toUpperCase() === 'GET'
  const maxAttempts = isRead ? 3 : 1
  let lastErr
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (attempt > 0) await new Promise(r => setTimeout(r, attempt * 600))
    try {
      const res = await fetch(url, merged)
      if (isRead && !res.ok && res.status >= 500 && attempt < maxAttempts - 1) {
        lastErr = new Error(`HTTP ${res.status}`)
        continue
      }
      return res
    } catch (err) {
      if (err.name === 'AbortError') throw err
      lastErr = err
    }
  }
  throw lastErr
}