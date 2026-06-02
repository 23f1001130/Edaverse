import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadFile } from '../services/api.js'
import './Uploader.css'

const ACCEPTED = {
  'text/csv': ['.csv'],
  'text/plain': ['.txt', '.tsv'],
  'application/json': ['.json'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
}

export default function Uploader({ onResult, onError, loading, setLoading }) {
  const [progress, setProgress] = useState(0)
  const [filename, setFilename] = useState('')

  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    const file = accepted[0]
    setFilename(file.name)
    setLoading(true)
    setProgress(0)

    try {
      const data = await uploadFile(file, setProgress)
      if (data.success) {
        onResult(data, file)
      } else {
        onError(data.error || 'Parse failed')
      }
    } catch (err) {
      onError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setLoading(false)
      setProgress(0)
    }
  }, [onResult, onError, setLoading])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled: loading,
  })

  return (
    <div className="uploader-wrap">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${loading ? 'loading' : ''}`}
      >
        <input {...getInputProps()} />
        {loading ? (
          <div className="upload-progress">
            <div className="spinner" />
            <p className="progress-filename">{filename}</p>
            <div className="progress-bar-wrap">
              <div className="progress-bar" style={{ width: `${progress}%` }} />
            </div>
            <p className="progress-pct">{progress}%</p>
          </div>
        ) : (
          <div className="dropzone-content">
            <div className="drop-icon">↑</div>
            <p className="drop-main">
              {isDragActive ? 'Drop it here' : 'Drop your file here'}
            </p>
            <p className="drop-sub">or click to browse</p>
            <div className="drop-types">
              <span>CSV</span><span>Excel</span><span>JSON</span><span>TSV</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
