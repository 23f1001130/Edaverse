import React, { useEffect, useState } from 'react'
import { getAuthHeaders } from '../../services/api.js'
import { fireToast, getSetting } from '../../services/toast.js'
import './tabs.css'

const BASE = import.meta.env.VITE_API_URL || ''

const SEV = {
  high:   { label: 'Errors',   singular: 'Error',   className: 'danger', icon: '!' },
  medium: { label: 'Warnings', singular: 'Warning', className: 'warning', icon: '!' },
  low:    { label: 'Info',     singular: 'Info',    className: 'info',    icon: 'i' },
}

function pct(n, d) {
  if (!d) return 0
  return Math.round((n / d) * 100)
}

function plural(n, word) {
  return `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`
}

export default function CleaningTab({ data, onDataUpdate }) {
  // scanKey is the single source of truth for "re-fetch now"
  // Incrementing it unconditionally triggers a fresh suggestions call
  const [scanKey, setScanKey]     = useState(0)
  const [suggestions, setSuggestions] = useState(null)
  const [selected, setSelected]   = useState(new Set())
  const [loading, setLoading]     = useState(true)
  const [result, setResult]       = useState(null)
  const [applying, setApplying]   = useState(false)
  const [promoting, setPromoting] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [hasBackup, setHasBackup] = useState(false)

  // Fetch fresh suggestions from the live parquet file every time scanKey changes
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setResult(null)
    setSuggestions(null)

    getAuthHeaders().then(headers =>
    fetch(`${BASE}/api/datasets/${data.id}/suggestions`, { headers })
      .then(r => r.json())
      .then(d => {
        if (cancelled) return
        const order = { high: 0, medium: 1, low: 2 }
        const s = (d.suggestions || []).sort((a, b) => order[a.severity] - order[b.severity])
        setSuggestions(s)
        setSelected(new Set(s.map(x => x.id)))
        setHasBackup(d.has_backup || false)
        setLoading(false)
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    )

    return () => { cancelled = true }
  }, [scanKey])   // scanKey is the sole trigger — data.id never changes for the same dataset

  function toggle(id) {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  async function apply() {
    setApplying(true)
    try {
      const authHeaders = await getAuthHeaders()
      const r = await fetch(`${BASE}/api/datasets/${data.id}/clean`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ fix_ids: [...selected] }),
      })
      setResult(await r.json())
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setApplying(false)
    }
  }

  async function useCleaned() {
    setPromoting(true)
    try {
      const authHeaders = await getAuthHeaders()
      const r = await fetch(`${BASE}/api/datasets/${data.id}/use-cleaned`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ fix_ids: result?.applied_fix_ids || [...selected] }),
      })
      const d = await r.json()
      if (d.ok) {
        if (onDataUpdate && d.dataset) onDataUpdate(d.dataset)
        setScanKey(k => k + 1)
        if (getSetting('notifications.cleaning_applied', true)) {
          fireToast('Cleaned dataset is now active', 'success')
        }
      }
    } catch {}
    finally { setPromoting(false) }
  }

  async function restoreOriginal() {
    setRestoring(true)
    try {
      const authHeaders = await getAuthHeaders()
      const r = await fetch(`${BASE}/api/datasets/${data.id}/restore-original`, { method: 'POST', headers: authHeaders })
      const d = await r.json()
      if (d.ok) {
        if (onDataUpdate && d.dataset) onDataUpdate(d.dataset)
        setScanKey(k => k + 1)
      }
    } catch {}
    finally { setRestoring(false) }
  }

  // ── render ────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="wr-loading"><div className="up-spinner" />Scanning for issues…</div>
  )

  if (!suggestions?.length) return (
    <div className="clean-empty">
      <div className="clean-empty-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
      </div>
      <div className="clean-empty-title">This dataset is clean</div>
      <div className="clean-empty-copy">No quality issues were detected. The data is structured correctly and ready for analysis or export.</div>
      <div className="clean-empty-badges">
        <span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          No nulls flagged
        </span>
        <span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          No duplicates found
        </span>
        <span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          Schema consistent
        </span>
      </div>
      {hasBackup && (
        <button className="clean-empty-restore" onClick={restoreOriginal} disabled={restoring}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
          {restoring ? 'Restoring…' : 'Restore original dataset'}
        </button>
      )}
    </div>
  )

  const errors   = suggestions.filter(s => s.severity === 'high').length
  const warnings = suggestions.filter(s => s.severity === 'medium').length
  const infos    = suggestions.filter(s => s.severity === 'low').length
  const selectedItems = suggestions.filter(s => selected.has(s.id))
  const selectedErrors = selectedItems.filter(s => s.severity === 'high').length
  const selectedWarnings = selectedItems.filter(s => s.severity === 'medium').length
  const selectedInfos = selectedItems.filter(s => s.severity === 'low').length
  const selectedPct = pct(selected.size, suggestions.length)
  const issueColumns = [...new Set(suggestions.map(s => s.column).filter(Boolean))]
  const issueColumnLabel = issueColumns.length
    ? plural(issueColumns.length, 'affected column')
    : 'Dataset-level checks'
  const healthClass = errors ? 'danger' : warnings ? 'warning' : 'info'
  const healthLabel = errors ? 'Needs attention' : warnings ? 'Review recommended' : 'Low risk'
  const healthCopy = errors
    ? `${plural(errors, 'blocking issue')} should be handled before modeling or export.`
    : warnings
      ? `${plural(warnings, 'warning')} may affect quality, but the dataset can continue.`
      : 'Only informational checks were found.'

  return (
    <div className="clean-report">
      <section className={`clean-hero ${healthClass}`}>
        <div className="clean-hero-main">
          <div className="clean-eyebrow">Cleaning report</div>
          <div className="clean-hero-title">{healthLabel}</div>
          <div className="clean-hero-copy">{healthCopy}</div>
        </div>
        <div className="clean-score">
          <span>{suggestions.length}</span>
          <small>issues found</small>
        </div>
        <div className="clean-hero-meta">
          <div>
            <span>{plural(data.shape.rows, 'row')}</span>
            <small>current dataset</small>
          </div>
          <div>
            <span>{issueColumnLabel}</span>
            <small>{data.shape.columns.toLocaleString()} total columns</small>
          </div>
        </div>
      </section>

      <div className="clean-summary-grid">
        <div className="clean-metric danger">
          <div className="clean-metric-label">Errors</div>
          <div className="clean-metric-value">{errors}</div>
          <div className="clean-metric-note">{selectedErrors} selected</div>
        </div>
        <div className="clean-metric warning">
          <div className="clean-metric-label">Warnings</div>
          <div className="clean-metric-value">{warnings}</div>
          <div className="clean-metric-note">{selectedWarnings} selected</div>
        </div>
        <div className="clean-metric info">
          <div className="clean-metric-label">Info</div>
          <div className="clean-metric-value">{infos}</div>
          <div className="clean-metric-note">{selectedInfos} selected</div>
        </div>
        <div className="clean-metric selected">
          <div className="clean-metric-label">Selected fixes</div>
          <div className="clean-metric-value">{selected.size}</div>
          <div className="clean-progress" aria-hidden="true">
            <span style={{ width: `${selectedPct}%` }} />
          </div>
          <div className="clean-metric-note">{selectedPct}% of report</div>
        </div>
      </div>

      <div className="clean-panel">
        <div className="clean-panel-head">
          <div>
            <div className="panel-title">Issues detected</div>
            <div className="clean-panel-subtitle">Select the fixes you want to apply to this dataset.</div>
          </div>
          <div className="clean-selection-pill">{selected.size} / {suggestions.length} selected</div>
        </div>
        <div className="clean-issue-list">
          {suggestions.map(s => {
            const sv = SEV[s.severity] || SEV.low
            const checked = selected.has(s.id)
            return (
              <label key={s.id} className={`clean-issue ${sv.className} ${checked ? 'selected' : ''}`}>
                <input type="checkbox" checked={checked} onChange={() => toggle(s.id)} />
                <span className="clean-issue-icon">{sv.icon}</span>
                <div className="clean-issue-body">
                  <div className="clean-issue-top">
                    <span className="clean-issue-title">{s.issue}</span>
                    <span className={`clean-severity ${sv.className}`}>{sv.singular}</span>
                    {s.column && <span className="clean-column">{s.column}</span>}
                  </div>
                  <div className="clean-fix-line">
                    <span>Fix</span>{' '}
                    {s.label} — {s.detail}
                  </div>
                </div>
              </label>
            )
          })}
        </div>
      </div>

      {/* ── Action area ── */}
      {!result ? (
        <div className="clean-actions">
          <button className="clean-primary-btn" onClick={apply} disabled={applying || selected.size === 0}>
            {applying ? 'Applying…' : `Apply ${selected.size} fix${selected.size !== 1 ? 'es' : ''}`}
          </button>
          {hasBackup && (
            <button className="clean-ghost-btn" onClick={restoreOriginal} disabled={restoring}>
              {restoring ? 'Restoring…' : '↩ Restore original'}
            </button>
          )}
        </div>
      ) : result.error ? (
        <div>
          <div className="ws-error" style={{ marginBottom: 12 }}>{result.error}</div>
          <button className="clean-ghost-btn" onClick={() => setResult(null)}>
            ← Try again
          </button>
        </div>
      ) : (
        <div className="clean-result">
          <div className="clean-result-head">
            <div className="clean-result-mark">✓</div>
            <div>
              <div className="clean-result-title">Fixes applied and ready</div>
              <div className="clean-result-meta">
                {result.rows_after?.toLocaleString()} rows · {result.cols_after} columns
                {result.rows_before !== result.rows_after && ` · ${result.rows_before - result.rows_after} duplicate rows removed`}
              </div>
            </div>
          </div>

          {result.log?.length > 0 && (
            <div className="clean-log">
              {result.log.map((l, i) => (
                <div key={i}>{l}</div>
              ))}
            </div>
          )}

          <div className="clean-actions">
            <button className="clean-success-btn" onClick={useCleaned} disabled={promoting}>
              {promoting ? 'Switching…' : '↻ Continue with cleaned data'}
            </button>
            <button className="clean-secondary-btn" onClick={() => window.open(`${BASE}/api/datasets/${data.id}/download`, '_blank')}>
              ↓ Download cleaned CSV
            </button>
            <button className="clean-ghost-btn" onClick={() => setResult(null)}>
              ← Back to issues
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
