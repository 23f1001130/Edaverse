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

function GridIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  )
}

export default function Uploader({ onResult, onError, loading, setLoading }) {
  const [filename, setFilename] = useState('')
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!loading) { setStepIndex(0); return }
    const timer = setInterval(() => {
      setStepIndex(i => Math.min(i + 1, STEPS.length - 1))
    }, 700)
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
        <div className="up-proc-card">
          <div className="up-proc-icon"><GridIcon /></div>
          <div className="up-proc-info">
            <div className="up-proc-name">{filename || 'Uploading…'}</div>
            <div className="up-proc-status">Processing…</div>
          </div>
          <div className="up-spinner" />
        </div>

        <div className="up-steps">
          {STEPS.map((step, i) => {
            const done   = i < stepIndex
            const active = i === stepIndex
            return (
              <div key={step} className={`up-step ${done ? 'done' : active ? 'active' : ''}`}>
                <span className="up-step-dot">
                  {done   ? <CheckIcon /> :
                   active ? <span className="up-step-spin" /> :
                            <span className="up-step-circle" />}
                </span>
                <span className="up-step-text">{step}…</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="up-wrap">
      <div className="up-hero">
        <span>New analysis</span>
        <h1>Upload your dataset</h1>
        <p>Drop a file and edaverse will profile quality, structure, and modeling readiness in one pass.</p>
      </div>

      <div {...getRootProps()} className={`up-zone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        <div className="up-zone-icon"><UploadIcon /></div>
        <div className="up-zone-main">Drop a CSV, Excel, JSON, TSV, or Parquet file</div>
        <div className="up-zone-sub">or click anywhere in this area to browse</div>
        <div className="up-zone-limit">Maximum file size: 100 MB</div>
      </div>

      <div className="up-types">
        <span>CSV</span><span>Excel</span><span>JSON</span><span>Parquet</span><span>TSV</span>
      </div>
    </div>
  )
}
