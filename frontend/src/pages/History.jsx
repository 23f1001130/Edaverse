import React, { useEffect, useState } from 'react'
import { fetchDatasets, deleteDataset } from '../services/api.js'
import './History.css'

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function History({ onSelect }) {
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    fetchDatasets()
      .then(setDatasets)
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(e, id) {
    e.stopPropagation()
    setDeletingId(id)
    try {
      await deleteDataset(id)
      setDatasets(ds => ds.filter(d => d.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return <div className="history-empty">Loading…</div>
  if (!datasets.length) return (
    <div className="history-empty">No datasets yet — upload a file to get started.</div>
  )

  return (
    <div className="history">
      <div className="history-header">
        <h2>Previous uploads</h2>
        <span className="history-count">{datasets.length} dataset{datasets.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="history-list">
        {datasets.map(ds => (
          <div
            key={ds.id}
            className="history-item"
            onClick={() => onSelect(ds.id)}
          >
            <div className="history-icon">📄</div>
            <div className="history-info">
              <div className="history-filename">{ds.filename}</div>
              <div className="history-meta">
                {ds.shape?.rows?.toLocaleString()} rows · {ds.shape?.columns} cols
                <span className="history-dot">·</span>
                {timeAgo(ds.saved_at)}
              </div>
              {ds.warnings?.length > 0 && (
                <div className="history-warn">⚠ {ds.warnings[0]}</div>
              )}
            </div>
            <button
              className="history-delete"
              onClick={(e) => handleDelete(e, ds.id)}
              disabled={deletingId === ds.id}
              title="Delete"
            >
              {deletingId === ds.id ? '…' : '✕'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}