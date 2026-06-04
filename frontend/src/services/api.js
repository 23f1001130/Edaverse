import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

// Get the Clerk session token and attach it to every request
async function getAuthHeaders() {
  try {
    // window.Clerk is injected by @clerk/clerk-react's ClerkProvider
    const token = await window.Clerk?.session?.getToken()
    if (token) return { Authorization: `Bearer ${token}` }
  } catch {}
  return {}
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

export async function fetchDatasets() {
  const headers = await getAuthHeaders()
  const res = await axios.get(`${BASE}/api/datasets`, { headers })
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