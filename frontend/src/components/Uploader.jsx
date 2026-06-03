import React, { useCallback, useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadFile } from '../services/api.js'
import './Uploader.css'

const ACCEPTED = {
  'text/csv': ['.csv'],
  'text/plain': ['.txt', '.tsv'],
  'application/json': ['.json'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'application/octet-stream': ['.parquet'],
}

const STEPS = [
  'Detecting encoding',
  'Inferring schema',
  'Analysing columns',
  'Computing statistics',
  'Generating profile',
]

export default function Uploader({ onResult, onError, loading, setLoading }) {
  const [filename, setFilename] = useState('')
  const [stepIndex, setStepIndex] = useState(0)

  // Animate through steps while loading
  useEffect(() => {
    if (!loading) { setStepIndex(0); return }
    const timer = setInterval(() => {
      setStepIndex(i => Math.min(i + 1, STEPS.length - 1))
    }, 600)
    return () => clearInterval(timer)
  }, [loading])

  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    const file = accepted[0]
    setFilename(file.name)
    setLoading(true)
    try {
      const data = await uploadFile(file)
      if (data.success) onResult(data, file)
      else onError(data.error || 'Parse failed')
    } catch (err) {
      onError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }, [onResult, onError, setLoading])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPTED, maxFiles: 1, disabled: loading,
  })

  if (loading) {
    return (
      <div className="up-loading">
        <div className="up-file-card">
          <div className="up-file-icon">▦</div>
          <div className="up-file-info">
            <div className="up-file-name">{filename}</div>
            <div className="up-file-status">Processing…</div>
          </div>
          <div className="up-spinner" />
        </div>
        <div className="up-steps">
          {STEPS.map((step, i) => (
            <div key={step} className={`up-step ${i < stepIndex ? 'done' : i === stepIndex ? 'active' : ''}`}>
              <span className="up-step-icon">
                {i < stepIndex ? '✓' : i === stepIndex ? <span className="up-step-spin" /> : '○'}
              </span>
              <span className="up-step-text">{step}…</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="up-wrap">
      <div className="up-hero">
        <h1>Upload your dataset</h1>
        <p>Drag and drop your file, or click to browse. We'll handle the rest.</p>
      </div>
      <div {...getRootProps()} className={`up-zone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        <div className="up-zone-icon">↑</div>
        <div className="up-zone-main">Drop your CSV, Excel, JSON or Parquet file here</div>
        <div className="up-zone-sub">or <span>browse to upload</span></div>
        <div className="up-zone-limit">Maximum file size: 100 MB</div>
      </div>
      <div className="up-types">
        <span>CSV</span><span>Excel</span><span>JSON</span><span>Parquet</span><span>TSV</span>
      </div>
    </div>
  )
}
