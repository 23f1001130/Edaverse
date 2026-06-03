import React from 'react'
import './tabs.css'

export default function OverviewTab({ data, eda }) {
  const numeric = data.schema.filter(c => ['integer','float'].includes(c.type)).length
  const categorical = data.schema.length - numeric
  const totalNullPct = data.schema.length
    ? (data.schema.reduce((s,c) => s + (c.null_pct||0), 0) / data.schema.length).toFixed(1)
    : 0
  const nulls = (eda?.nulls || [...data.schema].map(c => ({column:c.name, null_pct:c.null_pct||0})))
    .slice().sort((a,b) => b.null_pct - a.null_pct).slice(0, 8)

  return (
    <div>
      <div className="tab-grid-4">
        <div className="stat-box">
          <div className="stat-box-label">Total Rows</div>
          <div className="stat-box-value">{data.shape.rows.toLocaleString()}</div>
          <div className="stat-box-sub">in this dataset</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Columns</div>
          <div className="stat-box-value">{data.shape.columns}</div>
          <div className="stat-box-sub">{numeric} numeric · {categorical} categorical</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Null Rate</div>
          <div className="stat-box-value">{totalNullPct}%</div>
          <div className="stat-box-sub">across all columns</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Encoding</div>
          <div className="stat-box-value" style={{fontSize:'18px'}}>{data.encoding?.encoding}</div>
          <div className="stat-box-sub">{Math.round((data.encoding?.confidence||0)*100)}% confidence</div>
        </div>
      </div>

      <div className="tab-grid-2">
        {eda?.observations?.length > 0 && (
          <div className="panel">
            <div className="panel-title">Key observations</div>
            <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
              {eda.observations.map((o,i) => (
                <div key={i} style={{
                  fontSize:'13px', lineHeight:'1.5', padding:'10px 12px', borderRadius:'8px',
                  background: o.severity==='high'?'var(--red-bg)':o.severity==='medium'?'var(--amber-bg)':'var(--accent-glow)',
                  color: o.severity==='high'?'#fca5a5':o.severity==='medium'?'#fcd34d':'var(--accent-light)'
                }}>{o.text}</div>
              ))}
            </div>
          </div>
        )}
        <div className="panel">
          <div className="panel-title">Missingness by column</div>
          <div className="mini-bars">
            {nulls.map(n => {
              const c = n.null_pct === 0 ? 'var(--green)' : n.null_pct < 10 ? 'var(--amber)' : 'var(--red)'
              return (
                <div key={n.column} className="mini-bar-row">
                  <span className="mini-bar-name">{n.column}</span>
                  <div className="mini-bar-track"><div className="mini-bar-fill" style={{width:`${Math.max(n.null_pct,1)}%`, background:c}} /></div>
                  <span className="mini-bar-val" style={{color:c}}>{n.null_pct}%</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
