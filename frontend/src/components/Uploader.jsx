import React, { useCallback, useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadFile, fetchConfig } from '../services/api.js'
import { fireToast } from '../services/toast.js'
import './Uploader.css'

const ACCEPTED = {
  'text/csv': ['.csv'],
  'text/plain': ['.txt', '.tsv'],
  'application/json': ['.json'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'application/octet-stream': ['.parquet'],
}

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
  const [progress, setProgress] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [maxUploadMb, setMaxUploadMb] = useState(100)
  const [largeFileThresholdMb, setLargeFileThresholdMb] = useState(10)

  useEffect(() => {
    fetchConfig()
      .then(cfg => {
        if (cfg.max_upload_mb) setMaxUploadMb(cfg.max_upload_mb)
        if (cfg.large_file_threshold_mb) setLargeFileThresholdMb(cfg.large_file_threshold_mb)
      })
      .catch(() => {}) // keep the sensible defaults if config isn't reachable yet
  }, [])

  useEffect(() => {
    if (!loading) { setElapsed(0); return }
    const timer = setInterval(() => {
      setElapsed(i => i + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [loading])

  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    const file = accepted[0]
    const fileMb = file.size / (1024 * 1024)

    if (fileMb > maxUploadMb) {
      onError(`File is ${fileMb.toFixed(1)}MB, which is over the ${maxUploadMb}MB limit.`)
      return
    }
    if (fileMb > largeFileThresholdMb) {
      fireToast(`Large file (${fileMb.toFixed(0)}MB) — this may take longer to process than usual.`, 'info')
    }

    setFilename(file.name)
    setProgress(0)
    setLoading(true)
    try {
      const data = await uploadFile(file, setProgress)
      if (data.success) onResult(data, file)
      else onError(data.error || 'Parse failed')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') onError(detail)
      else if (!err.response) onError('Connection to the processing server was interrupted. The server may be restarting or the connection timed out. Please retry; if it keeps failing, try a smaller file or CSV instead of Excel.')
      else onError(`Upload failed (HTTP ${err.response.status}). Please retry.`)
    } finally {
      setLoading(false)
    }
  }, [onResult, onError, setLoading, maxUploadMb, largeFileThresholdMb])

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
            <div className="up-proc-status" role="status">{progress === null ? 'Loading dataset…' : progress < 100 ? `Uploading… ${progress}%` : 'Upload sent — profiling and saving dataset…'}</div>
          </div>
          <div className="up-spinner" />
        </div>

        <div className="up-steps">
          {progress !== null && <progress aria-label="File transfer" max="100" value={progress} style={{ width: '100%', accentColor: 'var(--accent)' }} />}
          <p className="up-processing-note">{elapsed}s elapsed. {progress === null ? 'The server is preparing your dataset.' : progress < 100 ? 'Sending your file to the server.' : 'Transfer finished. Large datasets can take longer to profile; keep this page open.'}</p>
          {elapsed >= 30 && <p className="up-processing-note">Still waiting for the server. It may need extra time to start up or process this file.</p>}
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
        <div className="up-zone-limit">Maximum file size: {maxUploadMb} MB</div>
      </div>

      <div className="up-types">
        <span>CSV</span><span>Excel</span><span>JSON</span><span>Parquet</span><span>TSV</span>
      </div>
    </div>
  )
}
