import React from 'react'
import './tabs.css'

function MissingnessMatrix({ matrix }) {
  if (!matrix?.columns?.length || !matrix?.rows?.length) return null
  return (
    <div className="panel" style={{marginTop:16}}>
      <div className="panel-title">Missingness matrix</div>
      <div className="miss-matrix-wrap">
        <div className="miss-matrix-cols" style={{gridTemplateColumns:`repeat(${matrix.columns.length}, 10px)`}}>
          {matrix.columns.map(c => <span key={c} title={c}>{c.slice(0, 3)}</span>)}
        </div>
        <div className="miss-matrix">
          {matrix.rows.map((r, i) => (
            <div key={`${r.row}-${i}`} className="miss-matrix-row" style={{gridTemplateColumns:`repeat(${matrix.columns.length}, 10px)`}}>
              {r.values.map((missing, j) => (
                <span key={j} title={`${matrix.columns[j]} · row ${r.row}`} className={missing ? 'missing' : 'present'} />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div style={{marginTop:10,fontSize:12,color:'var(--text-tertiary)'}}>
        Sampled up to 80 rows across columns with missing values. Amber cells are missing.
      </div>
    </div>
  )
}

export default function OverviewTab({ data, eda }) {
  const numeric = data.schema.filter(c => ['integer','float'].includes(c.type)).length
  const categorical = data.schema.length - numeric
  const totalNullPct = data.schema.length
    ? (data.schema.reduce((s,c) => s + (c.null_pct||0), 0) / data.schema.length).toFixed(1)
    : 0
  const nulls = (eda?.nulls || [...data.schema].map(c => ({column:c.name, null_pct:c.null_pct||0})))
    .slice().sort((a,b) => b.null_pct - a.null_pct).slice(0, 8)

  const missingness = eda?.missingness
  const flaggedPairs = missingness?.flagged_pairs || []
  const numericProfile = eda?.numeric_profile
  const categoricalProfile = eda?.categorical_profile

  // Skew summary from schema
  const skewedCols = data.schema.filter(c => c.skewness != null && Math.abs(c.skewness) > 1)
    .sort((a,b) => Math.abs(b.skewness) - Math.abs(a.skewness)).slice(0,5)

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
                  <span className="mini-bar-name" title={n.column}>{n.column}</span>
                  <div className="mini-bar-track"><div className="mini-bar-fill" style={{width:`${Math.max(n.null_pct,1)}%`, background:c}} /></div>
                  <span className="mini-bar-val" style={{color:c}}>{n.null_pct}%</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="tab-grid-4" style={{marginTop:16}}>
        <div className="stat-box">
          <div className="stat-box-label">Skewed Numerics</div>
          <div className="stat-box-value">{numericProfile?.skewed_count ?? 0}</div>
          <div className="stat-box-sub">abs(skew) above 1</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Outlier Columns</div>
          <div className="stat-box-value">{numericProfile?.outlier_columns ?? 0}</div>
          <div className="stat-box-sub">IQR fence hits</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">High Cardinality</div>
          <div className="stat-box-value">{categoricalProfile?.high_cardinality_count ?? 0}</div>
          <div className="stat-box-sub">categorical risk</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Imbalanced Cats</div>
          <div className="stat-box-value">{categoricalProfile?.imbalanced_count ?? 0}</div>
          <div className="stat-box-sub">top value dominates</div>
        </div>
      </div>

      <MissingnessMatrix matrix={eda?.missingness_matrix} />

      {/* Missingness co-occurrence — MNAR signals */}
      {flaggedPairs.length > 0 && (
        <div className="panel" style={{marginTop:16,borderColor:'rgba(251,191,36,0.3)'}}>
          <div className="panel-title" style={{display:'flex',alignItems:'center',gap:8}}>
            <span style={{color:'var(--amber)'}}>⚠</span> Possible MNAR patterns detected
            <span style={{fontSize:11,color:'var(--text-tertiary)',fontWeight:400}}>— columns whose missingness is correlated (not random)</span>
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:8}}>
            {flaggedPairs.map((p,i) => (
              <div key={i} style={{display:'flex',alignItems:'center',gap:12,padding:'10px 12px',background:'var(--amber-bg)',borderRadius:8}}>
                <div style={{flex:1}}>
                  <span style={{fontFamily:'var(--font-mono)',fontSize:13,color:'var(--amber)'}}>{p.a}</span>
                  <span style={{margin:'0 8px',color:'var(--text-tertiary)'}}>+</span>
                  <span style={{fontFamily:'var(--font-mono)',fontSize:13,color:'var(--amber)'}}>{p.b}</span>
                  <span style={{marginLeft:10,fontSize:12,color:'var(--text-secondary)'}}>both missing in {p.actual_pct}% of rows</span>
                </div>
                <div style={{textAlign:'right'}}>
                  <div style={{fontSize:11,color:'var(--amber)',fontWeight:600}}>lift {p.lift}×</div>
                  <div style={{fontSize:10,color:'var(--text-tertiary)'}}>vs {p.expected_pct}% expected</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{marginTop:10,fontSize:12,color:'var(--text-tertiary)'}}>
            High lift means these columns are missing together far more than random chance — a sign the missing data is Not Missing At Random (MNAR). Consider a missingness indicator feature rather than imputing.
          </div>
        </div>
      )}

      {/* Skewness summary */}
      {skewedCols.length > 0 && (
        <div className="panel" style={{marginTop:16}}>
          <div className="panel-title">Skewed numeric columns</div>
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {skewedCols.map(c => {
              const isHigh = Math.abs(c.skewness) > 2
              const barColor = isHigh ? 'var(--red)' : 'var(--amber)'
              const valColor = isHigh ? '#fca5a5' : 'var(--amber)'
              return (
                <div
                  key={c.name}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(0, 1.4fr) 2fr 54px 78px',
                    alignItems: 'center',
                    gap: 12,
                  }}
                >
                  <span
                    title={c.name}
                    style={{
                      fontFamily: 'var(--font-mono)', fontSize: 12,
                      color: 'var(--text-secondary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}
                  >{c.name}</span>
                  <div style={{height:6, background:'var(--border-subtle)', borderRadius:3, overflow:'hidden'}}>
                    <div style={{height:'100%', width:`${Math.min(Math.abs(c.skewness)/3*100,100)}%`, background:barColor, borderRadius:3}} />
                  </div>
                  <span style={{fontSize:12, fontFamily:'var(--font-mono)', textAlign:'right', color:valColor}}>
                    {c.skewness > 0 ? '+' : ''}{c.skewness.toFixed(2)}
                  </span>
                  <span style={{fontSize:11, color:'var(--text-tertiary)', whiteSpace:'nowrap'}}>
                    {c.skewness > 0 ? 'right' : 'left'}-skewed
                  </span>
                </div>
              )
            })}
          </div>
          <div style={{marginTop:8,fontSize:12,color:'var(--text-tertiary)'}}>Consider log or Box-Cox transforms in the Feature Engineering tab.</div>
        </div>
      )}
    </div>
  )
}
