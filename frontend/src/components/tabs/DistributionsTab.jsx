import React, { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line, ReferenceLine, Cell } from 'recharts'
import './tabs.css'

const tooltipStyle = { background:'#121829', border:'1px solid #242d42', borderRadius:8, fontSize:12, color:'#e8edf7' }

function SkewBadge({ skewness }) {
  if (skewness === null || skewness === undefined) return null
  const abs = Math.abs(skewness)
  if (abs < 0.5) return <span style={{fontSize:'10px',padding:'1px 6px',borderRadius:'4px',background:'var(--green-bg)',color:'var(--green)'}}>symmetric</span>
  if (abs < 1.0) return <span style={{fontSize:'10px',padding:'1px 6px',borderRadius:'4px',background:'var(--amber-bg)',color:'var(--amber)'}}>mod. skew {skewness > 0 ? '→' : '←'}</span>
  return <span style={{fontSize:'10px',padding:'1px 6px',borderRadius:'4px',background:'var(--red-bg)',color:'#fca5a5'}}>skewed {skewness > 0 ? '→' : '←'} {skewness.toFixed(2)}</span>
}

// SVG box plot
function BoxPlot({ bp }) {
  if (!bp || bp.q25 == null || bp.q75 == null) return null
  const { min, q25, median, q75, max, whisker_lo, whisker_hi, outlier_count } = bp
  const lo = whisker_lo ?? min
  const hi = whisker_hi ?? max
  const range = hi - lo
  if (range === 0) return null
  const pct = v => ((v - lo) / range * 100).toFixed(1) + '%'
  return (
    <div style={{marginTop:16,padding:'14px 20px',background:'var(--bg-input)',borderRadius:8}}>
      <div style={{fontSize:11,color:'var(--text-tertiary)',marginBottom:8,fontWeight:600}}>BOX PLOT (IQR)</div>
      <div style={{position:'relative',height:40}}>
        {/* whisker line */}
        <div style={{position:'absolute',top:'50%',left:'2%',right:'2%',height:1,background:'var(--border-default)',transform:'translateY(-50%)'}} />
        {/* IQR box */}
        <div style={{position:'absolute',top:'15%',height:'70%',left:pct(q25),width:`calc(${pct(q75)} - ${pct(q25)})`,background:'var(--accent)',opacity:0.7,borderRadius:3}} />
        {/* median line */}
        <div style={{position:'absolute',top:'10%',height:'80%',left:pct(median),width:2,background:'#fff',borderRadius:1}} />
        {/* whisker caps */}
        <div style={{position:'absolute',top:'20%',height:'60%',left:pct(lo),width:2,background:'var(--border-strong)'}} />
        <div style={{position:'absolute',top:'20%',height:'60%',left:pct(hi),width:2,background:'var(--border-strong)'}} />
      </div>
      <div style={{display:'flex',justifyContent:'space-between',fontSize:10,color:'var(--text-tertiary)',fontFamily:'var(--font-mono)',marginTop:6}}>
        <span>{lo?.toFixed?.(2) ?? lo}</span>
        <span style={{color:'var(--text-secondary)'}}>Q1: {q25?.toFixed?.(2) ?? q25}</span>
        <span style={{color:'#fff',fontWeight:600}}>Med: {median?.toFixed?.(2) ?? median}</span>
        <span style={{color:'var(--text-secondary)'}}>Q3: {q75?.toFixed?.(2) ?? q75}</span>
        <span>{hi?.toFixed?.(2) ?? hi}</span>
      </div>
      {outlier_count > 0 && (
        <div style={{fontSize:11,color:'var(--amber)',marginTop:6}}>⚠ {outlier_count} outlier{outlier_count !== 1 ? 's' : ''} outside fences</div>
      )}
    </div>
  )
}

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
        <div className="dist-mini-stats">
          μ {d.stats.mean} · σ {d.stats.std}
          {d.stats.skewness != null && Math.abs(d.stats.skewness) > 1 && (
            <span style={{marginLeft:6,color:'var(--amber)'}}>skew {d.stats.skewness > 0 ? '→' : '←'}</span>
          )}
        </div>
      )}
      {!isHist && !isTime && (
        <div className="dist-mini-stats">{d.total_unique} unique</div>
      )}
      {isTime && <div className="dist-mini-stats">{d.count} points</div>}
    </button>
  )
}

function Expanded({ d, onClose }) {
  const isHist = d.type === 'histogram'
  const isTime = d.type === 'timeline'
  return (
    <div className="dist-expanded">
      <div className="dist-exp-head">
        <div className="panel-title" style={{margin:0,display:'flex',alignItems:'center',gap:10}}>
          {d.column}
          <span className={`col-row-tag ${isHist?'num':isTime?'':'cat'}`} style={{...(isTime?{background:'var(--amber-bg)',color:'var(--amber)'}:{})}}>
            {isHist?'numeric':isTime?'timeline':'categorical'}
          </span>
          {isHist && d.stats && <SkewBadge skewness={d.stats.skewness} />}
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
        <>
          <div className="tab-grid-4" style={{marginTop:16}}>
            {[['Mean','mean'],['Std Dev','std'],['Min','min'],['Max','max'],['Median','median'],['Q1','q25'],['Q3','q75'],['Skewness','skewness']].map(([l,k])=>(
              <div key={k} className="stat-box">
                <div className="stat-box-label">{l}</div>
                <div className="stat-box-value" style={{fontSize:'18px'}}>
                  {d.stats[k] != null ? d.stats[k] : '–'}
                </div>
                {k === 'skewness' && d.stats[k] != null && (
                  <div className="stat-box-sub">{Math.abs(d.stats[k]) < 0.5 ? 'symmetric' : Math.abs(d.stats[k]) < 1 ? 'moderate' : 'high — consider transform'}</div>
                )}
              </div>
            ))}
          </div>
          <BoxPlot bp={d.boxplot} />
        </>
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

function NumericProfile({ profile }) {
  const cols = (profile?.columns || []).slice(0, 10)
  if (!cols.length) return null
  return (
    <div className="panel" style={{marginBottom:16}}>
      <div className="panel-title">Numeric triage — skew and outliers</div>
      <div className="profile-table">
        <div className="profile-head"><span>Column</span><span>Skew</span><span>Outliers</span><span>Action signal</span></div>
        {cols.map(c => {
          const skew = c.skewness ?? 0
          const signal = Math.abs(skew) > 1 ? 'transform' : c.outlier_count > 0 ? 'inspect outliers' : 'stable'
          return (
            <div key={c.column} className="profile-row">
              <span className="mono">{c.column}</span>
              <span style={{color:Math.abs(skew)>1?'var(--amber)':'var(--text-secondary)'}}>{skew > 0 ? '+' : ''}{skew?.toFixed?.(2) ?? '–'}</span>
              <span>{c.outlier_count} <small>{c.outlier_pct}%</small></span>
              <span className={`profile-pill ${signal === 'stable' ? 'ok' : signal === 'transform' ? 'warn' : 'info'}`}>{signal}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CategoricalProfile({ profile }) {
  const cols = (profile?.columns || []).slice(0, 10)
  if (!cols.length) return null
  return (
    <div className="panel" style={{marginBottom:16}}>
      <div className="panel-title">Categorical triage — cardinality and imbalance</div>
      <div className="profile-table">
        <div className="profile-head"><span>Column</span><span>Unique</span><span>Top share</span><span>Encoding signal</span></div>
        {cols.map(c => (
          <div key={c.column} className="profile-row">
            <span className="mono">{c.column}</span>
            <span>{c.unique}</span>
            <span style={{color:c.freq_pct >= 95 ? 'var(--amber)' : 'var(--text-secondary)'}}>{c.freq_pct}%</span>
            <span className={`profile-pill ${c.strategy === 'one-hot' ? 'ok' : c.strategy === 'identifier' || c.strategy === 'high-cardinality' ? 'warn' : 'info'}`}>{c.strategy}</span>
          </div>
        ))}
      </div>
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
      <div className="tab-grid-2" style={{marginBottom:16}}>
        <NumericProfile profile={eda?.numeric_profile} />
        <CategoricalProfile profile={eda?.categorical_profile} />
      </div>
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
