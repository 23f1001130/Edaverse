import React, { useEffect, useState } from 'react'
import './tabs.css'

const BASE = import.meta.env.VITE_API_URL || ''

const SEV = {
  high:   { label: 'Error',   color: '#fca5a5',             bg: 'var(--red-bg)',      icon: '⚠' },
  medium: { label: 'Warning', color: '#fcd34d',             bg: 'var(--amber-bg)',    icon: '!' },
  low:    { label: 'Info',    color: 'var(--accent-light)', bg: 'var(--accent-glow)', icon: 'i' },
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

    fetch(`${BASE}/api/datasets/${data.id}/suggestions`)
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

    return () => { cancelled = true }
  }, [scanKey])   // scanKey is the sole trigger — data.id never changes for the same dataset

  function toggle(id) {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  async function apply() {
    setApplying(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/clean`, {
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

  async function useCleaned() {
    setPromoting(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/use-cleaned`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fix_ids: result?.applied_fix_ids || [...selected] }),
      })
      const d = await r.json()
      if (d.ok) {
        if (onDataUpdate && d.dataset) onDataUpdate(d.dataset)
        // Always bump scanKey — shape may be identical (only nulls filled),
        // so we can't rely on prop comparison to trigger a re-fetch
        setScanKey(k => k + 1)
      }
    } catch {}
    finally { setPromoting(false) }
  }

  async function restoreOriginal() {
    setRestoring(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/restore-original`, { method: 'POST' })
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
    <div className="tab-empty">
      <div>✓ No cleaning issues detected — this dataset looks clean.</div>
      {hasBackup && (
        <div style={{ marginTop: 16 }}>
          <button onClick={restoreOriginal} disabled={restoring}
            style={{ fontSize: 13, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '7px 16px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            {restoring ? 'Restoring…' : '↩ Restore original dataset'}
          </button>
        </div>
      )}
    </div>
  )

  const errors   = suggestions.filter(s => s.severity === 'high').length
  const warnings = suggestions.filter(s => s.severity === 'medium').length
  const infos    = suggestions.filter(s => s.severity === 'low').length

  return (
    <div>
      <div className="tab-grid-4">
        <div className="stat-box"><div className="stat-box-label">Issues found</div><div className="stat-box-value">{suggestions.length}</div></div>
        <div className="stat-box"><div className="stat-box-label">Errors</div><div className="stat-box-value" style={{ color: 'var(--red)' }}>{errors}</div></div>
        <div className="stat-box"><div className="stat-box-label">Warnings</div><div className="stat-box-value" style={{ color: 'var(--amber)' }}>{warnings}</div></div>
        <div className="stat-box"><div className="stat-box-label">Info</div><div className="stat-box-value" style={{ color: 'var(--accent-light)' }}>{infos}</div></div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-title">Issues detected</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {suggestions.map(s => {
            const sv = SEV[s.severity] || SEV.low
            const checked = selected.has(s.id)
            return (
              <label key={s.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', padding: '14px 8px', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer' }}>
                <input type="checkbox" checked={checked} onChange={() => toggle(s.id)}
                  style={{ marginTop: '3px', width: '15px', height: '15px', cursor: 'pointer' }} />
                <span style={{ color: sv.color, fontSize: '16px', marginTop: '-1px' }}>{sv.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '14px', fontWeight: 600 }}>{s.issue}</span>
                    <span style={{ fontSize: '10px', fontWeight: 600, padding: '2px 8px', borderRadius: '6px', background: sv.bg, color: sv.color }}>{sv.label}</span>
                    {s.column && <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{s.column}</span>}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--green)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>✓</span> {s.label} — {s.detail}
                  </div>
                </div>
              </label>
            )
          })}
        </div>
      </div>

      {/* ── Action area ── */}
      {!result ? (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={apply} disabled={applying || selected.size === 0}
            style={{ background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '10px', padding: '12px 24px', fontSize: '14px', fontWeight: 600, cursor: 'pointer', opacity: (applying || selected.size === 0) ? 0.5 : 1 }}>
            {applying ? 'Applying…' : `Apply ${selected.size} fix${selected.size !== 1 ? 'es' : ''}`}
          </button>
          {hasBackup && (
            <button onClick={restoreOriginal} disabled={restoring}
              style={{ fontSize: 13, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '9px 16px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              {restoring ? 'Restoring…' : '↩ Restore original'}
            </button>
          )}
        </div>
      ) : result.error ? (
        <div>
          <div className="ws-error" style={{ marginBottom: 12 }}>{result.error}</div>
          <button onClick={() => setResult(null)}
            style={{ fontSize: 13, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '7px 16px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            ← Try again
          </button>
        </div>
      ) : (
        <div className="panel" style={{ borderColor: 'rgba(16,185,129,0.3)', background: 'var(--green-bg)' }}>
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--green)', marginBottom: '8px' }}>✓ Fixes applied and ready</div>
          <div style={{ fontSize: '13px', color: '#6ee7b7', marginBottom: '12px' }}>
            {result.rows_after?.toLocaleString()} rows · {result.cols_after} columns
            {result.rows_before !== result.rows_after && ` · ${result.rows_before - result.rows_after} duplicate rows removed`}
          </div>

          {result.log?.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              {result.log.map((l, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', padding: '2px 0' }}>· {l}</div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button onClick={useCleaned} disabled={promoting}
              style={{ background: 'var(--green)', color: '#04231a', border: 'none', borderRadius: '8px', padding: '9px 18px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', opacity: promoting ? 0.6 : 1 }}>
              {promoting ? 'Switching…' : '↻ Continue with cleaned data'}
            </button>
            <button onClick={() => window.open(`${BASE}/api/datasets/${data.id}/download`, '_blank')}
              style={{ background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '9px 18px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
              ↓ Download cleaned CSV
            </button>
            <button onClick={() => setResult(null)}
              style={{ background: 'none', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '9px 18px', fontSize: '13px', cursor: 'pointer' }}>
              ← Back to issues
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
