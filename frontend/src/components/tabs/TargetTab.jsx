import React, { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { apiFetch } from '../../services/api.js'
import './tabs.css'

const BASE = import.meta.env.VITE_API_URL || ''
const tooltipStyle = { background:'#121829', border:'1px solid #242d42', borderRadius:8, fontSize:12, color:'#e8edf7' }
const GRID = '#242d42'
const TICK = '#5f6b82'
const C_NUM = '#3b82f6'
const C_CAT = '#a78bfa'

function scoreLabel(score) {
  if (score == null) return 'n/a'
  if (score >= 0.5) return 'strong'
  if (score >= 0.25) return 'moderate'
  return 'weak'
}

function TargetDistribution({ analysis }) {
  const dist = analysis?.distribution
  if (!dist) return null
  const isHist = dist.type === 'histogram'
  const data = isHist ? dist.bins : dist.values
  return (
    <div className="panel">
      <div className="panel-title">Target distribution</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{top:8,right:12,left:-12,bottom:4}}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
          <XAxis dataKey={isHist ? 'range' : 'value'} tick={{fontSize:10,fill:TICK}} axisLine={false} tickLine={false} />
          <YAxis tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill={isHist ? C_NUM : C_CAT} radius={[4,4,0,0]} />
        </BarChart>
      </ResponsiveContainer>
      {isHist && dist.stats && (
        <div className="target-statline">
          mean {dist.stats.mean} · std {dist.stats.std} · range {dist.stats.min} to {dist.stats.max}
        </div>
      )}
    </div>
  )
}

function RecommendationList({ items }) {
  if (!items?.length) return null
  return (
    <div className="panel">
      <div className="panel-title">Recommended feature attention</div>
      <div className="target-rec-list">
        {items.map(item => (
          <div key={item.feature} className="target-rec">
            <span className={`profile-pill ${item.strength === 'strong' ? 'warn' : item.strength === 'moderate' ? 'info' : 'ok'}`}>{item.strength}</span>
            <span className="mono">{item.feature}</span>
            <span>{item.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function RankedRelationships({ title, rows }) {
  if (!rows?.length) return null
  return (
    <div className="panel">
      <div className="panel-title">{title}</div>
      <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
        {rows.map(r => (
          <div key={r.feature} style={{display:'flex',alignItems:'center',gap:'12px'}}>
            <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',color:'var(--text-secondary)',width:'170px'}}>{r.feature}</span>
            <div style={{flex:1,height:'6px',background:'var(--border-subtle)',borderRadius:'3px',overflow:'hidden'}}>
              <div style={{height:'100%',width:`${Math.min((r.score || Math.abs(r.correlation || 0)) * 100, 100)}%`,background:'var(--accent)',borderRadius:'3px'}} />
            </div>
            <span style={{fontSize:'12px',minWidth:'72px',color:'var(--accent-light)',fontFamily:'var(--font-mono)',textAlign:'right'}}>
              {(r.score ?? Math.abs(r.correlation ?? 0))?.toFixed?.(2) ?? 'n/a'}
            </span>
            <span className={`profile-pill ${scoreLabel(r.score ?? Math.abs(r.correlation ?? 0)) === 'strong' ? 'warn' : scoreLabel(r.score ?? Math.abs(r.correlation ?? 0)) === 'moderate' ? 'info' : 'ok'}`}>
              {scoreLabel(r.score ?? Math.abs(r.correlation ?? 0))}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScatterPanels({ rows, target }) {
  const scatters = (rows || []).filter(r => r.kind === 'numeric_scatter' && r.points?.length).slice(0, 3)
  if (!scatters.length) return null
  return (
    <div className="target-chart-grid">
      {scatters.map(r => (
        <div key={r.feature} className="panel">
          <div className="panel-title">{r.feature} vs {target}</div>
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart margin={{top:8,right:12,left:-12,bottom:4}}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis type="number" dataKey="x" name={r.feature} tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
              <YAxis type="number" dataKey="y" name={target} tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Scatter data={r.points} fill={C_NUM} opacity={0.7} />
            </ScatterChart>
          </ResponsiveContainer>
          <div className="target-statline">correlation {r.correlation > 0 ? '+' : ''}{r.correlation?.toFixed?.(2)}</div>
        </div>
      ))}
    </div>
  )
}

function GroupPanels({ rows, target }) {
  const groups = (rows || []).filter(r => ['numeric_by_class', 'category_vs_numeric'].includes(r.kind) && r.groups?.length).slice(0, 3)
  if (!groups.length) return null
  return (
    <div className="target-chart-grid">
      {groups.map(r => {
        const key = r.kind === 'numeric_by_class' ? 'class' : 'value'
        return (
          <div key={r.feature} className="panel">
            <div className="panel-title">{r.feature} grouped by {target}</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={r.groups} margin={{top:8,right:12,left:-12,bottom:4}}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis dataKey={key} tick={{fontSize:10,fill:TICK}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize:11,fill:TICK}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="mean" fill={C_CAT} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="target-statline">score {r.score?.toFixed?.(2) ?? 'n/a'}</div>
          </div>
        )
      })}
    </div>
  )
}

function CrosstabPanel({ rows, target }) {
  const table = (rows || []).find(r => r.kind === 'category_crosstab' && r.cells?.length)
  if (!table) return null
  return (
    <div className="panel">
      <div className="panel-title">{table.feature} × {target}</div>
      <div className="pivot-wrap">
        <div className="pivot-grid" style={{gridTemplateColumns:`120px repeat(${table.x_values.length}, minmax(34px, 1fr))`}}>
          <span />
          {table.x_values.map(x => <span key={x} className="pivot-head" title={x}>{x}</span>)}
          {table.y_values.map(y => (
            <React.Fragment key={y}>
              <span className="pivot-row-head" title={y}>{y}</span>
              {table.x_values.map(x => {
                const cell = table.cells.find(c => c.x === x && c.y === y)
                const intensity = table.max_count ? (cell?.count || 0) / table.max_count : 0
                return <span key={`${y}-${x}`} className="pivot-cell" title={`${table.feature}: ${y}\n${target}: ${x}\ncount ${cell?.count || 0}`} style={{background:`rgba(59,130,246,${0.08 + intensity * 0.72})`}}>{cell?.count || 0}</span>
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
      <div className="target-statline">association score {table.score?.toFixed?.(2) ?? 'n/a'}</div>
    </div>
  )
}

export default function TargetTab({ data }) {
  const [target, setTarget] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [importance, setImportance] = useState(null)
  const [loading, setLoading] = useState(false)
  const [importanceLoading, setImportanceLoading] = useState(false)
  const [error, setError] = useState(null)
  const candidates = data.schema.map(c => c.name)

  useEffect(() => {
    if (!target || !data.id) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setAnalysis(null)
    setImportance(null)
    apiFetch(`${BASE}/api/datasets/${data.id}/target-analysis?target=${encodeURIComponent(target)}`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(new Error(d.detail || 'Target analysis failed'))))
      .then(d => { if (!cancelled) setAnalysis(d) })
      .catch(e => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    setImportanceLoading(true)
    apiFetch(`${BASE}/api/datasets/${data.id}/model-importance?target=${encodeURIComponent(target)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (!cancelled) setImportance(d) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setImportanceLoading(false) })
    return () => { cancelled = true }
  }, [target, data.id])

  return (
    <div>
      <div className="panel" style={{marginBottom:16}}>
        <div className="panel-title">Select a target column</div>
        <p style={{fontSize:'13px',color:'var(--text-secondary)',marginBottom:'14px'}}>
          Choose the column you want to predict. The analysis adapts for regression or classification targets.
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

      {loading && <div className="wr-loading"><div className="up-spinner" />Computing target relationships…</div>}
      {error && <div className="ws-error">{error}</div>}

      {analysis && !loading && (
        <>
          <div className="tab-grid-4">
            <div className="stat-box"><div className="stat-box-label">Task</div><div className="stat-box-value" style={{fontSize:18}}>{analysis.target.task}</div><div className="stat-box-sub">{analysis.target.type} target</div></div>
            <div className="stat-box"><div className="stat-box-label">Unique</div><div className="stat-box-value">{analysis.target.unique}</div><div className="stat-box-sub">target values</div></div>
            <div className="stat-box"><div className="stat-box-label">Numeric Links</div><div className="stat-box-value">{analysis.numeric_relationships.length}</div><div className="stat-box-sub">ranked features</div></div>
            <div className="stat-box"><div className="stat-box-label">Categorical Links</div><div className="stat-box-value">{analysis.categorical_relationships.length}</div><div className="stat-box-sub">ranked features</div></div>
          </div>

          <div className="tab-grid-2">
            <TargetDistribution analysis={analysis} />
            <RecommendationList items={analysis.recommendations} />
          </div>

          <div className="tab-grid-2" style={{marginTop:16}}>
            <RankedRelationships title="Numeric feature ranking" rows={analysis.numeric_relationships} />
            <RankedRelationships title="Categorical feature ranking" rows={analysis.categorical_relationships} />
          </div>

          <div style={{marginTop:16}}>
            <ScatterPanels rows={analysis.numeric_relationships} target={target} />
            <GroupPanels rows={[...analysis.numeric_relationships, ...analysis.categorical_relationships]} target={target} />
            <CrosstabPanel rows={analysis.categorical_relationships} target={target} />
          </div>

          {(importanceLoading || importance?.importance?.length > 0) && (
            <div className="panel" style={{marginTop:16}}>
              <div className="panel-title">Model-based feature importance</div>
              {importanceLoading ? (
                <div className="wr-loading" style={{padding:20}}><div className="up-spinner" />Training baseline model…</div>
              ) : (
                <>
                  <div className="target-statline" style={{marginBottom:12}}>
                    {importance.task} baseline {importance.metric}: {importance.baseline_score} · {importance.rows_used} rows · {importance.features_used} encoded features
                  </div>
                  <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
                    {importance.importance.slice(0, 12).map(r => (
                      <div key={r.feature} style={{display:'flex',alignItems:'center',gap:'12px'}}>
                        <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',color:'var(--text-secondary)',width:'180px'}}>{r.feature}</span>
                        <div style={{flex:1,height:'6px',background:'var(--border-subtle)',borderRadius:'3px',overflow:'hidden'}}>
                          <div style={{height:'100%',width:`${Math.min((r.permutation_importance || r.coefficient_importance || 0) * 100, 100)}%`,background:'var(--amber)',borderRadius:'3px'}} />
                        </div>
                        <span style={{fontSize:'12px',fontFamily:'var(--font-mono)',minWidth:'74px',textAlign:'right',color:'var(--amber)'}}>
                          {r.permutation_importance}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="target-statline">{importance.note}</div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
