import React, { useEffect, useState } from 'react'
import './tabs.css'

const BASE = import.meta.env.VITE_API_URL || ''

const SEV = {
  high: { label:'Error', color:'#fca5a5', bg:'var(--red-bg)', icon:'⚠' },
  medium: { label:'Warning', color:'#fcd34d', bg:'var(--amber-bg)', icon:'!' },
  low: { label:'Info', color:'var(--accent-light)', bg:'var(--accent-glow)', icon:'i' },
}

export default function CleaningTab({ data, onDataUpdate }) {
  const [suggestions, setSuggestions] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [applying, setApplying] = useState(false)
  const [promoting, setPromoting] = useState(false)
  const [promoted, setPromoted] = useState(false)
  const [restoring, setRestoring] = useState(false)

  async function useCleaned() {
    setPromoting(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/use-cleaned`, {method:'POST'})
      const d = await r.json()
      if (d.ok) { setPromoted(true); if (onDataUpdate && d.dataset) onDataUpdate(d.dataset) }
    } catch {}
    finally { setPromoting(false) }
  }

  async function restoreOriginal() {
    setRestoring(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/restore-original`, {method:'POST'})
      const d = await r.json()
      if (d.ok) { setPromoted(false); if (onDataUpdate && d.dataset) onDataUpdate(d.dataset) }
    } catch {}
    finally { setRestoring(false) }
  }

  useEffect(() => {
    fetch(`${BASE}/api/datasets/${data.id}/suggestions`)
      .then(r => r.json())
      .then(d => {
        const order = {high:0,medium:1,low:2}
        const s = (d.suggestions||[]).sort((a,b)=>order[a.severity]-order[b.severity])
        setSuggestions(s); setSelected(new Set(s.map(x=>x.id))); setLoading(false)
      })
      .catch(()=>setLoading(false))
  }, [data.id])

  function toggle(id){ setSelected(s=>{const n=new Set(s); n.has(id)?n.delete(id):n.add(id); return n}) }

  async function apply(){
    setApplying(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${data.id}/clean`,{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({fix_ids:[...selected]})
      })
      setResult(await r.json())
    } catch(e){ setResult({error:e.message}) }
    finally { setApplying(false) }
  }

  if (loading) return <div className="wr-loading"><div className="up-spinner" />Scanning for issues…</div>
  if (!suggestions?.length) return <div className="tab-empty">✓ No cleaning issues detected — this dataset looks clean.</div>

  const errors = suggestions.filter(s=>s.severity==='high').length
  const warnings = suggestions.filter(s=>s.severity==='medium').length
  const infos = suggestions.filter(s=>s.severity==='low').length

  return (
    <div>
      <div className="tab-grid-4">
        <div className="stat-box"><div className="stat-box-label">Issues found</div><div className="stat-box-value">{suggestions.length}</div></div>
        <div className="stat-box"><div className="stat-box-label">Errors</div><div className="stat-box-value" style={{color:'var(--red)'}}>{errors}</div></div>
        <div className="stat-box"><div className="stat-box-label">Warnings</div><div className="stat-box-value" style={{color:'var(--amber)'}}>{warnings}</div></div>
        <div className="stat-box"><div className="stat-box-label">Info</div><div className="stat-box-value" style={{color:'var(--accent-light)'}}>{infos}</div></div>
      </div>

      <div className="panel" style={{marginBottom:16}}>
        <div className="panel-title">Issues detected</div>
        <div style={{display:'flex',flexDirection:'column',gap:'2px'}}>
          {suggestions.map(s => {
            const sv = SEV[s.severity] || SEV.low
            const checked = selected.has(s.id)
            return (
              <label key={s.id} style={{display:'flex',alignItems:'flex-start',gap:'14px',padding:'14px 8px',borderBottom:'1px solid var(--border-subtle)',cursor:'pointer'}}>
                <input type="checkbox" checked={checked} onChange={()=>toggle(s.id)} style={{marginTop:'3px',width:'15px',height:'15px',cursor:'pointer'}} />
                <span style={{color:sv.color,fontSize:'16px',marginTop:'-1px'}}>{sv.icon}</span>
                <div style={{flex:1}}>
                  <div style={{display:'flex',alignItems:'center',gap:'10px',marginBottom:'4px'}}>
                    <span style={{fontSize:'14px',fontWeight:600}}>{s.issue}</span>
                    <span style={{fontSize:'10px',fontWeight:600,padding:'2px 8px',borderRadius:'6px',background:sv.bg,color:sv.color}}>{sv.label}</span>
                    {s.column && <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',color:'var(--text-tertiary)'}}>{s.column}</span>}
                  </div>
                  <div style={{fontSize:'13px',color:'var(--green)',display:'flex',alignItems:'center',gap:'6px'}}>
                    <span>✓</span> {s.label} — {s.detail}
                  </div>
                </div>
              </label>
            )
          })}
        </div>
      </div>

      {!result ? (
        <button onClick={apply} disabled={applying||selected.size===0}
          style={{background:'var(--accent)',color:'#fff',border:'none',borderRadius:'10px',padding:'12px 24px',fontSize:'14px',fontWeight:600,cursor:'pointer',opacity:(applying||selected.size===0)?0.5:1}}>
          {applying ? 'Applying…' : `Apply ${selected.size} fix${selected.size!==1?'es':''}`}
        </button>
      ) : result.error ? (
        <div className="ws-error">{result.error}</div>
      ) : (
        <div className="panel" style={{borderColor:'rgba(16,185,129,0.3)',background:'var(--green-bg)'}}>
          <div style={{fontSize:'15px',fontWeight:600,color:'var(--green)',marginBottom:'8px'}}>✓ Dataset cleaned and ready</div>
          <div style={{fontSize:'13px',color:'#6ee7b7',marginBottom:'16px'}}>
            {result.rows_after.toLocaleString()} rows · {result.cols_after} columns · {result.rows_before-result.rows_after} duplicate rows removed · cleaning log attached
          </div>
          <div style={{display:'flex',gap:'10px',flexWrap:'wrap'}}>
            <button onClick={useCleaned} disabled={promoting}
              style={{background:'var(--green)',color:'#04231a',border:'none',borderRadius:'8px',padding:'9px 18px',fontSize:'13px',fontWeight:600,cursor:'pointer',opacity:promoting?0.6:1}}>
              {promoting ? 'Switching…' : '↻ Continue with cleaned data'}
            </button>
            <button onClick={()=>window.open(`${BASE}/api/datasets/${data.id}/download`,'_blank')}
              style={{background:'var(--bg-card)',color:'var(--text-primary)',border:'1px solid var(--border-default)',borderRadius:'8px',padding:'9px 18px',fontSize:'13px',fontWeight:600,cursor:'pointer'}}>
              ↓ Download cleaned CSV
            </button>
          </div>
          {promoted && (
            <div style={{marginTop:'12px',fontSize:'13px',color:'#6ee7b7'}}>
              ✓ Now working on cleaned data. All tabs reflect the cleaned dataset.
              <button onClick={restoreOriginal} disabled={restoring}
                style={{marginLeft:'10px',background:'none',border:'none',color:'var(--text-secondary)',textDecoration:'underline',cursor:'pointer',fontSize:'13px'}}>
                {restoring ? 'Restoring…' : 'Undo (restore original)'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
