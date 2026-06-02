import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

export async function uploadFile(file, onProgress, headerRow = null) {
  const form = new FormData()
  form.append('file', file)
  if (headerRow !== null) form.append('header_row', headerRow)

  const res = await axios.post(`${BASE}/api/upload`, form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    }
  })
  return res.data
}

export async function fetchDatasets() {
  const res = await axios.get(`${BASE}/api/datasets`)
  return res.data
}

export async function fetchDataset(id) {
  const res = await axios.get(`${BASE}/api/datasets/${id}`)
  return res.data
}

export async function deleteDataset(id) {
  const res = await axios.delete(`${BASE}/api/datasets/${id}`)
  return res.data
}
