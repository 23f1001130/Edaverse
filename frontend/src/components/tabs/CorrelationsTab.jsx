import React from 'react'
import './tabs.css'

function cellColor(v) {
  if (v === null || v === undefined) return 'var(--bg-input)'
  const a = Math.abs(v)
  if (v >= 0) return `rgba(59,130,246,${0.15 + a*0.6})`
  return `rgba(16,185,129,${0.15 + a*0.6})`
}

export default function CorrelationsTab({ eda }) {
  const corr = eda?.correlation
  if (!corr) return <div className="tab-empty">Need at least 2 numeric columns for correlation analysis.</div>

  const { columns, matrix } = corr
  const lookup = {}
  matrix.forEach(({x,y,value}) => { lookup[`${x}||${y}`] = value })

  // top pairs
  const seen = new Set(); const pairs = []
  matrix.forEach(({x,y,value}) => {
    if (x===y || value===null) return
    const k = [x,y].sort().join('|')
    if (seen.has(k)) return; seen.add(k)
    pairs.push({x,y,value})
  })
  pairs.sort((a,b) => Math.abs(b.value)-Math.abs(a.value))

  return (
    <div>
      <div className="panel" style={{marginBottom:16, overflowX:'auto'}}>
        <div className="panel-title">Pearson correlation matrix — numeric columns</div>
        <table style={{borderCollapse:'separate', borderSpacing:'3px', fontSize:'11px'}}>
          <thead>
            <tr>
              <th></th>
              {columns.map(c => <th key={c} style={{color:'var(--text-tertiary)',fontWeight:500,padding:'4px',fontFamily:'var(--font-mono)'}}>{c.length>8?c.slice(0,8):c}</th>)}
            </tr>
          </thead>
          <tbody>
            {columns.map(row => (
              <tr key={row}>
                <td style={{color:'var(--text-tertiary)',textAlign:'right',paddingRight:'8px',fontFamily:'var(--font-mono)',whiteSpace:'nowrap'}}>{row.length>10?row.slice(0,10):row}</td>
                {columns.map(col => {
                  const v = lookup[`${row}||${col}`]
                  return (
                    <td key={col} style={{
                      background: cellColor(v), borderRadius:'6px', padding:'10px 8px',
                      textAlign:'center', minWidth:'62px', fontFamily:'var(--font-mono)',
                      color: Math.abs(v||0)>0.5?'#fff':'var(--text-secondary)', fontWeight: v===1?700:500,
                    }}>{v!==null&&v!==undefined?v.toFixed(2):'–'}</td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div className="panel-title">Top correlated pairs</div>
        <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
          {pairs.slice(0,6).map((p,i) => (
            <div key={i} style={{display:'flex',alignItems:'center',gap:'12px'}}>
              <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',color:'var(--text-secondary)',flex:1}}>
                {p.x} × {p.y}
              </span>
              <div style={{flex:1,height:'6px',background:'var(--border-subtle)',borderRadius:'3px',overflow:'hidden'}}>
                <div style={{height:'100%',width:`${Math.abs(p.value)*100}%`,background:p.value>=0?'var(--accent)':'var(--green)',borderRadius:'3px'}} />
              </div>
              <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',minWidth:'48px',textAlign:'right',color:p.value>=0?'var(--accent-light)':'var(--green)'}}>
                {p.value>=0?'+':''}{p.value.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
