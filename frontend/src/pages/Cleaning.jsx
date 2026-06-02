import React, { useEffect, useState } from 'react'
import './Cleaning.css'

const BASE = import.meta.env.VITE_API_URL || ''

const SEV_ORDER = { high: 0, medium: 1, low: 2 }
const SEV_STYLE = {
  high: { color: '#b91c1c', bg: '#fef2f2', border: '#fecaca' },
  medium: { color: '#92400e', bg: '#fffbeb', border: '#fcd34d' },
  low: { color: '#1e40af', bg: '#eff6ff', border: '#bfdbfe' },
}

export default function Cleaning({ datasetId, filename }) {
  const [suggestions, setSuggestions] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetch(`${BASE}/api/datasets/${datasetId}/suggestions`)
      .then(r => r.json())
      .then(data => {
        const sorted = (data.suggestions || []).sort(
          (a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity]
        )
        setSuggestions(sorted)
        setSelected(new Set(sorted.map(s => s.id)))  // pre-select all
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [datasetId])

  function toggle(id) {
    setSelected(s => {
      const next = new Set(s)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function applyFixes() {
    setApplying(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${datasetId}/clean`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fix_ids: [...selected] }),
      })
      setResult(await r.json())
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setApplying(false)
    }
  }

  function download() {
    window.open(`${BASE}/api/datasets/${datasetId}/download`, '_blank')
  }

  if (loading) return <div className="clean-loading"><div className="eda-spinner" />Scanning for issues…</div>

  if (!suggestions?.length) return (
    <div className="clean-empty">
      <div className="clean-empty-icon">✓</div>
      <p>No cleaning issues detected — this dataset looks clean.</p>
    </div>
  )

  return (
    <div className="cleaning">
      <div className="clean-intro">
        <p>Found <strong>{suggestions.length}</strong> suggested fixes. Review and apply — your original file is never modified.</p>
      </div>

      <div className="clean-list">
        {suggestions.map(s => {
          const st = SEV_STYLE[s.severity]
          const checked = selected.has(s.id)
          return (
            <label key={s.id} className={`clean-item ${checked ? 'checked' : ''}`}>
              <input type="checkbox" checked={checked} onChange={() => toggle(s.id)} />
              <div className="clean-info">
                <div className="clean-label">{s.label}</div>
                <div className="clean-meta">
                  <span className="clean-issue" style={{ background: st.bg, color: st.color, borderColor: st.border }}>
                    {s.issue}
                  </span>
                  <span className="clean-detail">{s.detail}</span>
                </div>
              </div>
            </label>
          )
        })}
      </div>

      <div className="clean-actions">
        <button className="clean-apply" onClick={applyFixes} disabled={applying || selected.size === 0}>
          {applying ? 'Applying…' : `Apply ${selected.size} fix${selected.size !== 1 ? 'es' : ''}`}
        </button>
      </div>

      {result && !result.error && (
        <div className="clean-result">
          <div className="clean-result-header">
            <span className="clean-check">✓</span> Cleaning applied
          </div>
          <div className="clean-stats">
            <span>{result.rows_before.toLocaleString()} → {result.rows_after.toLocaleString()} rows</span>
            <span>{result.cols_before} → {result.cols_after} columns</span>
          </div>
          <ul className="clean-log">
            {result.log.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
          <button className="clean-download" onClick={download}>
            ↓ Download cleaned CSV
          </button>
        </div>
      )}

      {result?.error && <div className="clean-error">Error: {result.error}</div>}
    </div>
  )
}
