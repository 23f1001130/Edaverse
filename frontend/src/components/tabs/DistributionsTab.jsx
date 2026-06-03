import React, { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line } from 'recharts'
import './tabs.css'

const tooltipStyle = { background:'#121829', border:'1px solid #242d42', borderRadius:8, fontSize:12, color:'#e8edf7' }

// Small multiple — compact chart for the grid
function MiniChart({ d, onClick }) {
  const isHist = d.type === 'histogram'
  const isTime = d.type === 'timeline'
  const data = isHist ? d.bins : isTime ? d.timeline : d.values

  return (
    <button className="dist-mini" onClick={onClick}>
      <div className="dist-mini-head">
        <span className="dist-mini-name">{d.column}</span>
        <span className={`col-row-tag ${isHist?'num':isTime?'':'cat'}`} style={isTime?{background:'var(--amber-bg)',color:'var(--amber)'}:{}}>
          {isHist ? 'NUM' : isTime ? 'TIME' : 'CAT'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={90}>
        {isTime ? (
          <LineChart data={data} margin={{top:4,right:4,left:4,bottom:0}}>
            <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
          </LineChart>
        ) : isHist ? (
          <BarChart data={data} margin={{top:4,right:2,left:2,bottom:0}}>
            <Bar dataKey="count" fill="#3b82f6" radius={[2,2,0,0]} />
          </BarChart>
        ) : (
          <BarChart data={data} margin={{top:4,right:2,left:2,bottom:0}}>
            <Bar dataKey="count" fill="#34d399" radius={[2,2,0,0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
      {isHist && d.stats && (
        <div className="dist-mini-stats">μ {d.stats.mean} · σ {d.stats.std}</div>
      )}
      {!isHist && !isTime && (
        <div className="dist-mini-stats">{d.total_unique} unique</div>
      )}
      {isTime && <div className="dist-mini-stats">{d.count} points</div>}
    </button>
  )
}

// Expanded single-column view
function Expanded({ d, onClose }) {
  const isHist = d.type === 'histogram'
  const isTime = d.type === 'timeline'
  return (
    <div className="dist-expanded">
      <div className="dist-exp-head">
        <div className="panel-title" style={{margin:0}}>
          {d.column}
          <span className={`col-row-tag ${isHist?'num':isTime?'':'cat'}`} style={{marginLeft:10, ...(isTime?{background:'var(--amber-bg)',color:'var(--amber)'}:{})}}>
            {isHist?'numeric':isTime?'timeline':'categorical'}
          </span>
        </div>
        <button className="dist-exp-close" onClick={onClose}>← back to all columns</button>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        {isTime ? (
          <LineChart data={d.timeline} margin={{top:8,right:12,left:-12,bottom:4}}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2638" />
            <XAxis dataKey="period" tick={{fontSize:10,fill:'#5f6b82'}} axisLine={false} tickLine={false} />
            <YAxis tick={{fontSize:11,fill:'#5f6b82'}} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={2} dot={{r:2}} />
          </LineChart>
        ) : isHist ? (
          <BarChart data={d.bins} margin={{top:8,right:12,left:-12,bottom:4}}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2638" />
            <XAxis dataKey="range" tick={{fontSize:10,fill:'#5f6b82'}} axisLine={false} tickLine={false} />
            <YAxis tick={{fontSize:11,fill:'#5f6b82'}} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} cursor={{fill:'rgba(59,130,246,0.08)'}} />
            <Bar dataKey="count" fill="#3b82f6" radius={[4,4,0,0]} />
          </BarChart>
        ) : (
          <BarChart data={d.values} layout="vertical" margin={{top:8,right:16,left:8,bottom:4}}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2638" horizontal={false} />
            <XAxis type="number" tick={{fontSize:11,fill:'#5f6b82'}} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="value" tick={{fontSize:11,fill:'#9aa7bd'}} axisLine={false} tickLine={false} width={110} tickFormatter={v=>v.length>14?v.slice(0,14)+'…':v} />
            <Tooltip contentStyle={tooltipStyle} cursor={{fill:'rgba(52,211,153,0.08)'}} />
            <Bar dataKey="count" fill="#34d399" radius={[0,4,4,0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
      {isHist && d.stats && (
        <div className="tab-grid-4" style={{marginTop:16}}>
          {[['Mean','mean'],['Std Dev','std'],['Min','min'],['Max','max'],['Median','median'],['Q1','q25'],['Q3','q75']].map(([l,k])=>(
            <div key={k} className="stat-box"><div className="stat-box-label">{l}</div><div className="stat-box-value" style={{fontSize:'20px'}}>{d.stats[k]}</div></div>
          ))}
        </div>
      )}
      {!isHist && !isTime && d.cat_stats && (
        <div className="tab-grid-4" style={{marginTop:16}}>
          <div className="stat-box"><div className="stat-box-label">Unique</div><div className="stat-box-value" style={{fontSize:'20px'}}>{d.cat_stats.unique}</div></div>
          <div className="stat-box"><div className="stat-box-label">Top value</div><div className="stat-box-value" style={{fontSize:'16px'}}>{d.cat_stats.top}</div></div>
          <div className="stat-box"><div className="stat-box-label">Top frequency</div><div className="stat-box-value" style={{fontSize:'20px'}}>{d.cat_stats.freq}</div><div className="stat-box-sub">{d.cat_stats.freq_pct}% of non-null</div></div>
          <div className="stat-box"><div className="stat-box-label">Non-null count</div><div className="stat-box-value" style={{fontSize:'20px'}}>{d.cat_stats.count}</div></div>
        </div>
      )}
    </div>
  )
}

export default function DistributionsTab({ eda, activeCol, setActiveCol }) {
  const dists = (eda?.distributions || []).filter(d => d.type !== 'skipped')
  const skipped = (eda?.distributions || []).filter(d => d.type === 'skipped')
  const [filter, setFilter] = useState('all')
  const [showSkipped, setShowSkipped] = useState(false)

  if (!dists.length) return <div className="tab-empty">No distributions available.</div>

  const expanded = activeCol ? dists.find(d => d.column === activeCol) : null
  if (expanded) {
    return <Expanded d={expanded} onClose={() => setActiveCol(null)} />
  }

  const counts = {
    all: dists.length,
    num: dists.filter(d=>d.type==='histogram').length,
    cat: dists.filter(d=>d.type==='barchart').length,
    time: dists.filter(d=>d.type==='timeline').length,
  }
  const filtered = filter==='all' ? dists
    : filter==='num' ? dists.filter(d=>d.type==='histogram')
    : filter==='cat' ? dists.filter(d=>d.type==='barchart')
    : dists.filter(d=>d.type==='timeline')

  return (
    <div>
      <div className="dist-toolbar">
        <div className="dist-filters">
          <button className={`dist-filter ${filter==='all'?'active':''}`} onClick={()=>setFilter('all')}>All <span>{counts.all}</span></button>
          <button className={`dist-filter ${filter==='num'?'active':''}`} onClick={()=>setFilter('num')}>Numeric <span>{counts.num}</span></button>
          <button className={`dist-filter ${filter==='cat'?'active':''}`} onClick={()=>setFilter('cat')}>Categorical <span>{counts.cat}</span></button>
          {counts.time>0 && <button className={`dist-filter ${filter==='time'?'active':''}`} onClick={()=>setFilter('time')}>Time series <span>{counts.time}</span></button>}
        </div>
        <span className="dist-hint">Click any chart to expand</span>
      </div>

      <div className="dist-grid">
        {filtered.map(d => (
          <MiniChart key={d.column} d={d} onClick={() => setActiveCol(d.column)} />
        ))}
      </div>

      {skipped.length > 0 && (
        <div className="dist-skipped">
          <button className="dist-skipped-toggle" onClick={()=>setShowSkipped(s=>!s)}>
            {showSkipped?'▼':'▶'} {skipped.length} columns not charted
          </button>
          {showSkipped && (
            <div className="dist-skipped-list">
              {skipped.map(s=>(
                <div key={s.column} className="dist-skipped-item">
                  <span style={{fontFamily:'var(--font-mono)',color:'var(--text-secondary)'}}>{s.column}</span>
                  <span style={{color:'var(--text-tertiary)'}}>{s.reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
