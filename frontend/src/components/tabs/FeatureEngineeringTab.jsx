import React, { useEffect, useState } from 'react'
import './tabs.css'

const BASE = import.meta.env.VITE_API_URL || ''

const CAT_META = {
  transform: { label: 'Transforms', color: 'var(--accent-light)', bg: 'var(--accent-glow)',         icon: '∿' },
  scale:     { label: 'Scaling',    color: 'var(--green)',         bg: 'var(--green-bg)',             icon: '⇔' },
  encode:    { label: 'Encoding',   color: 'var(--amber)',         bg: 'var(--amber-bg)',             icon: '⊞' },
  datetime:  { label: 'Datetime',   color: '#c084fc',              bg: 'rgba(192,132,252,0.12)',      icon: '⌚' },
  selection: { label: 'Selection',  color: '#fb7185',              bg: 'rgba(251,113,133,0.12)',      icon: '⊗' },
  missingness:{ label: 'Missingness', color: '#38bdf8',             bg: 'rgba(56,189,248,0.12)',       icon: '◐' },
  bin:       { label: 'Binning',     color: '#a3e635',              bg: 'rgba(163,230,53,0.12)',       icon: '▤' },
  timeseries:{ label: 'Time Series', color: '#f472b6',              bg: 'rgba(244,114,182,0.12)',      icon: '↝' },
}

function PreviewDiff({ preview }) {
  if (!preview || preview.error)
    return preview?.error ? <span style={{ color: 'var(--red)', fontSize: 12 }}>{preview.error}</span> : null
  const { before, after, note } = preview
  return (
    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-tertiary)' }}>
      <span style={{ fontFamily: 'var(--font-mono)' }}>
        skew {before.skewness?.toFixed(2) ?? '?'} → {after.skewness?.toFixed(2) ?? '?'}
        <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
        std {before.std?.toFixed(2) ?? '?'} → {after.std?.toFixed(2) ?? '?'}
      </span>
      {note && <span style={{ marginLeft: 8, fontStyle: 'italic' }}>{note}</span>}
    </div>
  )
}

export default function FeatureEngineeringTab({ data, onDataUpdate }) {
  const [scanKey, setScanKey]     = useState(0)
  const [suggestions, setSuggestions] = useState(null)
  const [selected, setSelected]   = useState(new Set())
  const [loading, setLoading]     = useState(true)
  const [applying, setApplying]   = useState(false)
  const [result, setResult]       = useState(null)
  const [promoting, setPromoting] = useState(false)
  const [catFilter, setCatFilter] = useState('all')
  const [target, setTarget]       = useState('')

  // Re-fetch suggestions whenever scanKey changes (same pattern as CleaningTab)
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setResult(null)
    setSuggestions(null)

    const qs = target ? `?target=${encodeURIComponent(target)}` : ''
    fetch(`${BASE}/api/datasets/${data.id}/feature-suggestions${qs}`)
      .then(r => r.json())
      .then(d => {
        if (cancelled) return
        const s = d.suggestions || []
        setSuggestions(s)
        // Pre-select transforms + datetime by default
        setSelected(new Set(
          s.filter(x => ['transform', 'datetime'].includes(x.category)).map(x => x.id)
        ))
        setLoading(false)
      })
      .catch(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [scanKey, target])   // scanKey + target control suggestion refresh

  function toggle(id) {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  function toggleAll(ids, force) {
    setSelected(s => {
      const n = new Set(s)
      ids.forEach(id => force ? n.add(id) : n.delete(id))
      return n
    })
  }

  async function apply() {
    setApplying(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/engineer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op_ids: [...selected] }),
      })
      setResult(await r.json())
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setApplying(false)
    }
  }

  // Promote the engineered dataset as the active one (mirrors CleaningTab)
  async function useEngineered() {
    setPromoting(true)
    try {
      // The engineered file lives at {id}_feat.parquet — we promote it by
      // copying it over the main parquet via the backend, then refreshing
      const r = await fetch(`${BASE}/api/datasets/${data.id}/use-engineered`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op_ids: result?.applied_op_ids || [...selected] }),
      })
      const d = await r.json()
      if (d.ok) {
        if (onDataUpdate && d.dataset) onDataUpdate(d.dataset)
        setScanKey(k => k + 1)   // re-scan suggestions for the new dataset
      }
    } catch {}
    finally { setPromoting(false) }
  }

  if (loading) return (
    <div className="wr-loading"><div className="up-spinner" />Scanning for feature opportunities…</div>
  )

  if (!suggestions?.length) return (
    <div className="tab-empty">No feature engineering opportunities found — dataset may already be well-prepared.</div>
  )

  const cats = Object.keys(CAT_META)
  const filtered = catFilter === 'all' ? suggestions : suggestions.filter(s => s.category === catFilter)
  const catCounts = {}
  cats.forEach(c => { catCounts[c] = suggestions.filter(s => s.category === c).length })

  const grouped = {}
  filtered.forEach(s => {
    grouped[s.category] = grouped[s.category] || []
    grouped[s.category].push(s)
  })

  return (
    <div>
      {/* Summary */}
      <div className="tab-grid-4" style={{ marginBottom: 20 }}>
        <div className="stat-box">
          <div className="stat-box-label">Opportunities</div>
          <div className="stat-box-value">{suggestions.length}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Selected</div>
          <div className="stat-box-value" style={{ color: 'var(--accent-light)' }}>{selected.size}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">New columns</div>
          <div className="stat-box-value">{result?.new_columns?.length ?? '—'}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Output shape</div>
          <div className="stat-box-value" style={{ fontSize: 16 }}>
            {result ? `${result.shape?.rows} × ${result.shape?.columns}` : '—'}
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-title" style={{ marginBottom: 8 }}>Target-aware encoding</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <select value={target} onChange={e => { setTarget(e.target.value); setScanKey(k => k + 1) }}
            style={{ background: 'var(--bg-input)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '8px 10px', fontSize: 13 }}>
            <option value="">No target selected</option>
            {data.schema.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
            Select a target to unlock leakage-reduced target encoding for high-cardinality categoricals.
          </span>
        </div>
      </div>

      {/* Category filter */}
      <div className="dist-toolbar" style={{ marginBottom: 16 }}>
        <div className="dist-filters">
          <button className={`dist-filter ${catFilter === 'all' ? 'active' : ''}`} onClick={() => setCatFilter('all')}>
            All <span>{suggestions.length}</span>
          </button>
          {cats.map(key => catCounts[key] > 0 && (
            <button key={key} className={`dist-filter ${catFilter === key ? 'active' : ''}`} onClick={() => setCatFilter(key)}>
              {CAT_META[key].icon} {CAT_META[key].label} <span>{catCounts[key]}</span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => toggleAll(filtered.map(s => s.id), true)}
            style={{ fontSize: 12, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 6, padding: '4px 10px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            Select all
          </button>
          <button onClick={() => toggleAll(filtered.map(s => s.id), false)}
            style={{ fontSize: 12, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 6, padding: '4px 10px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            Clear all
          </button>
        </div>
      </div>

      {/* Grouped suggestions */}
      {Object.entries(grouped).map(([cat, items]) => {
        const meta = CAT_META[cat] || CAT_META.transform
        return (
          <div key={cat} className="panel" style={{ marginBottom: 14 }}>
            <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: meta.color }}>{meta.icon}</span>
              {meta.label}
              <span style={{ fontSize: 11, background: meta.bg, color: meta.color, padding: '1px 8px', borderRadius: 20, fontWeight: 500 }}>{items.length}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {items.map(s => {
                const checked = selected.has(s.id)
                return (
                  <label key={s.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 8px', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer', borderRadius: 6, background: checked ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <input type="checkbox" checked={checked} onChange={() => toggle(s.id)}
                      style={{ marginTop: 3, width: 14, height: 14, cursor: 'pointer' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 2 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{s.label}</span>
                        {s.column && <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{s.column}</span>}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.detail}</div>
                      {s.preview && <PreviewDiff preview={s.preview} />}
                    </div>
                  </label>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Action area — mirrors CleaningTab exactly */}
      <div style={{ marginTop: 16 }}>
        {!result ? (
          <button onClick={apply} disabled={applying || selected.size === 0}
            style={{ background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 10, padding: '12px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer', opacity: (applying || selected.size === 0) ? 0.5 : 1 }}>
            {applying ? 'Engineering…' : `Apply ${selected.size} operation${selected.size !== 1 ? 's' : ''}`}
          </button>
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
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--green)', marginBottom: 8 }}>✓ Feature engineering complete</div>
            <div style={{ fontSize: 13, color: '#6ee7b7', marginBottom: 12 }}>
              {result.new_columns?.length} new columns added · {result.shape?.rows?.toLocaleString()} rows × {result.shape?.columns} columns total
            </div>

            {result.log?.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                {result.log.map((l, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', padding: '2px 0' }}>· {l}</div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={useEngineered} disabled={promoting}
                style={{ background: 'var(--green)', color: '#04231a', border: 'none', borderRadius: 8, padding: '9px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: promoting ? 0.6 : 1 }}>
                {promoting ? 'Switching…' : '↻ Continue with engineered data'}
              </button>
              <button onClick={() => window.open(`${BASE}/api/datasets/${data.id}/download-engineered`, '_blank')}
                style={{ background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-default)', borderRadius: 8, padding: '9px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                ↓ Download engineered CSV
              </button>
              <button onClick={() => setResult(null)}
                style={{ background: 'none', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '9px 18px', fontSize: 13, cursor: 'pointer' }}>
                ← Back to operations
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
