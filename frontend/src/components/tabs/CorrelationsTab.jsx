import React, { useState } from 'react'
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { getSetting } from '../../services/toast.js'
import './tabs.css'

const GRID = '#242d42'
const TICK = '#5f6b82'

function cellColor(v) {
  if (v === null || v === undefined) return 'var(--bg-input)'
  const a = Math.abs(v)
  if (v >= 0) return `rgba(59,130,246,${0.12 + a*0.65})`
  return `rgba(239,68,68,${0.12 + a*0.65})`
}

const LIMIT_OPTIONS = [10, 20, 30, 50, 100]

export default function CorrelationsTab({ eda }) {
  const [method, setMethod] = useState('pearson')
  const [colSearch, setColSearch] = useState('')
  const [colLimit, setColLimit] = useState(() => getSetting('analysis.heatmap_max_cols', 20))

  const corr = method === 'spearman' ? (eda?.correlation_spearman || eda?.correlation) : eda?.correlation
  const pca = eda?.pca
  const pivot = eda?.pivot_heatmap
  if (!corr && !pca && !pivot) return <div className="tab-empty">Need at least 2 numeric or categorical columns for relationship analysis.</div>

  const { columns = [], matrix = [] } = corr || {}
  const lookup = {}
  matrix.forEach(({x,y,value}) => { lookup[`${x}||${y}`] = value })

  const searchLower = colSearch.toLowerCase()
  const visibleCols = columns
    .filter(c => !colSearch || c.toLowerCase().includes(searchLower))
    .slice(0, colLimit)

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
      {corr && (
        <div className="panel" style={{marginBottom:16}}>
          {/* Controls bar */}
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,marginBottom:12,flexWrap:'wrap'}}>
            <div style={{display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
              <div className="panel-title" style={{margin:0}}>{method === 'spearman' ? 'Spearman' : 'Pearson'} correlation matrix</div>
              <span style={{fontSize:11,color:'var(--text-tertiary)'}}>
                {visibleCols.length < columns.length
                  ? `showing ${visibleCols.length} of ${columns.length} columns`
                  : `${columns.length} columns`}
              </span>
            </div>
            <div style={{display:'flex',alignItems:'center',gap:8,flexWrap:'wrap'}}>
              <input
                value={colSearch}
                onChange={e => setColSearch(e.target.value)}
                placeholder="Filter columns…"
                style={{
                  background:'var(--bg-input)',border:'1px solid var(--border-subtle)',borderRadius:8,
                  padding:'5px 10px',fontSize:12,color:'var(--text-primary)',width:140,
                }}
              />
              <select
                value={colLimit}
                onChange={e => setColLimit(Number(e.target.value))}
                style={{background:'var(--bg-input)',border:'1px solid var(--border-subtle)',borderRadius:8,padding:'5px 8px',fontSize:12,color:'var(--text-primary)'}}
              >
                {LIMIT_OPTIONS.map(n => <option key={n} value={n}>Max {n}</option>)}
                <option value={999}>All</option>
              </select>
              <div className="dist-filters">
                <button className={`dist-filter ${method === 'pearson' ? 'active' : ''}`} onClick={() => setMethod('pearson')}>Pearson</button>
                <button className={`dist-filter ${method === 'spearman' ? 'active' : ''}`} onClick={() => setMethod('spearman')}>Spearman</button>
              </div>
            </div>
          </div>
          {columns.length > 20 && !colSearch && (
            <div style={{fontSize:11,color:'var(--amber)',marginBottom:10,background:'var(--amber-bg)',borderRadius:6,padding:'6px 10px'}}>
              Large dataset ({columns.length} numeric columns) — heatmap limited to {visibleCols.length} columns. Use Max or Filter to focus on specific columns.
            </div>
          )}
          <div style={{overflowX:'auto',overflowY:'auto',maxHeight:520}}>
            <table style={{borderCollapse:'separate', borderSpacing:'3px', fontSize:'11px'}}>
              <thead>
                <tr>
                  <th></th>
                  {visibleCols.map(c => (
                    <th key={c} style={{color:'var(--text-tertiary)',fontWeight:500,padding:'4px',fontFamily:'var(--font-mono)'}} title={c}>
                      {c.length > 8 ? c.slice(0, 8) + '…' : c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleCols.map(row => (
                  <tr key={row}>
                    <td style={{color:'var(--text-tertiary)',textAlign:'right',paddingRight:'8px',fontFamily:'var(--font-mono)',whiteSpace:'nowrap'}} title={row}>
                      {row.length > 12 ? row.slice(0, 12) + '…' : row}
                    </td>
                    {visibleCols.map(col => {
                      const v = lookup[`${row}||${col}`]
                      return (
                        <td key={col} title={`${row} × ${col}: ${v?.toFixed(4) ?? 'n/a'}`} style={{
                          background: cellColor(v), borderRadius:'6px', padding:'10px 8px',
                          textAlign:'center', minWidth:'56px', fontFamily:'var(--font-mono)',
                          color: Math.abs(v||0)>0.5?'#fff':'var(--text-secondary)', fontWeight: v===1?700:500,
                        }}>{v!==null&&v!==undefined?v.toFixed(2):'-'}</td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {pairs.length > 0 && (
        <div className="panel">
          <div className="panel-title">Top correlated pairs</div>
          <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
            {pairs.slice(0,6).map((p,i) => (
              <div key={i} style={{display:'grid', gridTemplateColumns:'minmax(0,1.4fr) 2fr 52px', alignItems:'center', gap:'12px'}}>
                <span
                  title={`${p.x} × ${p.y}`}
                  style={{fontSize:'12px', fontFamily:'var(--font-mono)', color:'var(--text-secondary)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}
                >
                  {p.x} × {p.y}
                </span>
                <div style={{height:'6px',background:'var(--border-subtle)',borderRadius:'3px',overflow:'hidden'}}>
                  <div style={{height:'100%',width:`${Math.abs(p.value)*100}%`,background:p.value>=0?'var(--accent)':'var(--green)',borderRadius:'3px'}} />
                </div>
                <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',textAlign:'right',color:p.value>=0?'var(--accent-light)':'var(--green)'}}>
                  {p.value>=0?'+':''}{p.value.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="tab-grid-2" style={{marginTop:16}}>
        {pca?.points?.length > 0 && (
          <div className="panel">
            <div className="panel-title">PCA structure map</div>
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart margin={{top:8,right:12,left:-12,bottom:4}}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis type="number" dataKey="x" name="PC1" tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
                <YAxis type="number" dataKey="y" name="PC2" tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
                <Tooltip cursor={{stroke:'#3b82f6',strokeWidth:1}} contentStyle={{ background:'#121829', border:'1px solid #242d42', borderRadius:8, fontSize:12, color:'#e8edf7' }} />
                <Scatter data={pca.points} fill="#3b82f6" opacity={0.72} />
              </ScatterChart>
            </ResponsiveContainer>
            <div style={{fontSize:12,color:'var(--text-tertiary)',marginTop:8}}>
              PC1 {pca.explained_variance?.[0]}% · PC2 {pca.explained_variance?.[1]}% variance using {pca.columns?.length} numeric columns.
            </div>
          </div>
        )}

        {pivot?.cells?.length > 0 && (
          <div className="panel">
            <div className="panel-title">Categorical pivot heatmap</div>
            <div className="pivot-wrap">
              <div className="pivot-grid" style={{gridTemplateColumns:`120px repeat(${pivot.x_values.length}, minmax(34px, 1fr))`}}>
                <span />
                {pivot.x_values.map(x => <span key={x} className="pivot-head" title={x}>{x}</span>)}
                {pivot.y_values.map(y => (
                  <React.Fragment key={y}>
                    <span className="pivot-row-head" title={y}>{y}</span>
                    {pivot.x_values.map(x => {
                      const cell = pivot.cells.find(c => c.x === x && c.y === y)
                      const intensity = pivot.max_count ? (cell?.count || 0) / pivot.max_count : 0
                      return <span key={`${y}-${x}`} className="pivot-cell" title={`${pivot.y}: ${y}\n${pivot.x}: ${x}\ncount ${cell?.count || 0}`} style={{background:`rgba(59,130,246,${0.08 + intensity * 0.72})`}}>{cell?.count || 0}</span>
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
            <div style={{fontSize:12,color:'var(--text-tertiary)',marginTop:8}}>
              Counts for {pivot.y} × {pivot.x}, limited to top categories.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
