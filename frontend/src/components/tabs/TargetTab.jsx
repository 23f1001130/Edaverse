import React, { useState } from 'react'
import './tabs.css'

export default function TargetTab({ data, eda }) {
  const [target, setTarget] = useState(null)

  const corr = eda?.correlation
  const candidates = data.schema.map(c => c.name)

  // If target chosen and it's numeric, show correlations against it
  let relations = []
  if (target && corr) {
    const lookup = {}
    corr.matrix.forEach(({x,y,value}) => { lookup[`${x}||${y}`] = value })
    relations = corr.columns
      .filter(c => c !== target)
      .map(c => ({ col: c, value: lookup[`${c}||${target}`] }))
      .filter(r => r.value !== null && r.value !== undefined)
      .sort((a,b) => Math.abs(b.value) - Math.abs(a.value))
  }

  return (
    <div>
      <div className="panel" style={{marginBottom:16}}>
        <div className="panel-title">Select a target column</div>
        <p style={{fontSize:'13px',color:'var(--text-secondary)',marginBottom:'14px'}}>
          Choose the column you want to predict. We'll show how strongly each numeric feature relates to it.
        </p>
        <div style={{display:'flex',flexWrap:'wrap',gap:'6px'}}>
          {candidates.map(c => (
            <button key={c}
              onClick={() => setTarget(c)}
              style={{
                fontSize:'12px',fontFamily:'var(--font-mono)',padding:'6px 14px',borderRadius:'20px',cursor:'pointer',
                border:'1px solid var(--border-subtle)',
                background: c===target?'var(--accent-glow)':'var(--bg-card)',
                color: c===target?'var(--accent-light)':'var(--text-secondary)',
              }}>{c}</button>
          ))}
        </div>
      </div>

      {target && (
        relations.length > 0 ? (
          <div className="panel">
            <div className="panel-title">Feature relationship to <span style={{fontFamily:'var(--font-mono)',color:'var(--accent-light)'}}>{target}</span></div>
            <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
              {relations.map(r => (
                <div key={r.col} style={{display:'flex',alignItems:'center',gap:'12px'}}>
                  <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',color:'var(--text-secondary)',width:'160px'}}>{r.col}</span>
                  <div style={{flex:1,height:'6px',background:'var(--border-subtle)',borderRadius:'3px',overflow:'hidden'}}>
                    <div style={{height:'100%',width:`${Math.abs(r.value)*100}%`,background:r.value>=0?'var(--accent)':'var(--green)'}} />
                  </div>
                  <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',minWidth:'48px',textAlign:'right',color:r.value>=0?'var(--accent-light)':'var(--green)'}}>
                    {r.value>=0?'+':''}{r.value.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="tab-empty">
            <span style={{fontFamily:'var(--font-mono)',color:'var(--accent-light)'}}>{target}</span> is categorical or has no numeric relationships to show. Pick a numeric target for correlation analysis.
          </div>
        )
      )}
    </div>
  )
}
