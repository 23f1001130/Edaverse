import React, { useEffect, useState } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { fetchDatasets, deleteDataset } from '../services/api.js'
import './HistoryPanel.css'

function timeAgo(iso) {
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function FileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  )
}

const PAGE_SIZE = 20

export default function HistoryPanel({ onSelect, themeControl }) {
  const { isSignedIn, isLoaded } = useAuth()
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [delId, setDelId] = useState(null)

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) { setLoading(false); return }
    fetchDatasets({ limit: PAGE_SIZE, offset: 0 })
      .then(data => {
        setDatasets(data)
        setHasMore(data.length === PAGE_SIZE)
        setOffset(PAGE_SIZE)
      })
      .finally(() => setLoading(false))
  }, [isLoaded, isSignedIn])

  async function loadMore() {
    setLoadingMore(true)
    try {
      const data = await fetchDatasets({ limit: PAGE_SIZE, offset })
      setDatasets(prev => [...prev, ...data])
      setHasMore(data.length === PAGE_SIZE)
      setOffset(o => o + PAGE_SIZE)
    } finally {
      setLoadingMore(false)
    }
  }

  async function del(e, id) {
    e.stopPropagation()
    setDelId(id)
    try {
      await deleteDataset(id)
      setDatasets(d => d.filter(x => x.id !== id))
    } finally {
      setDelId(null)
    }
  }

  function renderBody() {
    if (loading) {
      return <div className="hist-state">Loading…</div>
    }

    if (!isSignedIn) {
      return (
        <div className="hist-signin-prompt">
          <div className="hist-signin-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="hist-signin-title">Sign in to view history</div>
          <p className="hist-signin-copy">Your uploaded datasets and analysis sessions are saved to your account when you're signed in.</p>
        </div>
      )
    }

    if (!datasets.length) {
      return <div className="hist-state">No datasets yet — upload a file to get started.</div>
    }

    return (
      <>
        {datasets.map(ds => (
          <div key={ds.id} className="hist-item" onClick={() => onSelect(ds.id)}>
            <div className="hist-icon"><FileIcon /></div>
            <div className="hist-info">
              <div className="hist-name">{ds.filename}</div>
              <div className="hist-meta">
                {ds.shape?.rows?.toLocaleString()} rows · {ds.shape?.columns} cols · {timeAgo(ds.saved_at)}
              </div>
            </div>
            <button className="hist-del" onClick={(e) => del(e, ds.id)} disabled={delId === ds.id} title="Delete">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        ))}
        {hasMore && (
          <button className="hist-load-more" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? 'Loading…' : 'Load more'}
          </button>
        )}
      </>
    )
  }

  return (
    <div className="ws-panel">
      <div className="ws-topbar">
        <div className="ws-breadcrumb">
          <span className="ws-bc-workspace">My Workspace</span>
          <span className="ws-bc-sep">/</span>
          <span className="ws-bc-current">History</span>
        </div>
        {themeControl}
      </div>
      <div className="hist">
        {renderBody()}
      </div>
    </div>
  )
}
