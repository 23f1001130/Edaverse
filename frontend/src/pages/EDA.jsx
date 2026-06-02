import React, { useEffect, useState } from 'react'
import HistogramChart from '../components/eda/HistogramChart.jsx'
import TopValuesChart from '../components/eda/BarChart.jsx'
import NullsChart from '../components/eda/NullsChart.jsx'
import CorrelationMatrix from '../components/eda/CorrelationMatrix.jsx'
import Observations from '../components/eda/Observations.jsx'
import ScatterPlot from '../components/eda/ScatterPlot.jsx'
import Timeline from '../components/eda/Timeline.jsx'
import './EDA.css'

const BASE = import.meta.env.VITE_API_URL || ''

export default function EDA({ datasetId }) {
  const [eda, setEda] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [showSkipped, setShowSkipped] = useState(false)

  useEffect(() => {
    if (!datasetId) return
    setLoading(true)
    fetch(`${BASE}/api/datasets/${datasetId}/eda`)
      .then(r => r.json())
      .then(data => { setEda(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [datasetId])

  if (loading) return <div className="eda-loading"><div className="eda-spinner" />Crunching your data…</div>
  if (error) return <div className="eda-error">EDA failed: {error}</div>
  if (!eda || eda.error) return <div className="eda-error">{eda?.error || 'No EDA data'}</div>

  const distributions = eda.distributions || []
  const charted = distributions.filter(d => d.type !== 'skipped')
  const skipped = distributions.filter(d => d.type === 'skipped')

  const filtered = filter === 'all' ? charted
    : filter === 'numeric' ? charted.filter(d => d.type === 'histogram')
    : filter === 'cat' ? charted.filter(d => d.type === 'barchart')
    : charted.filter(d => d.type === 'timeline')

  const numericCount = charted.filter(d => d.type === 'histogram').length
  const catCount = charted.filter(d => d.type === 'barchart').length
  const timeCount = charted.filter(d => d.type === 'timeline').length

  return (
    <div className="eda">
      {/* Observations — the analytical summary */}
      {eda.observations && <Observations observations={eda.observations} />}

      {/* Nulls heatmap */}
      {eda.nulls?.length > 0 && <NullsChart nulls={eda.nulls} />}

      {/* Scatter plots for correlated pairs */}
      {eda.scatter_pairs?.length > 0 && (
        <>
          <div className="eda-section-label">Relationships</div>
          <div className="charts-grid">
            {eda.scatter_pairs.map((s, i) => <ScatterPlot key={i} data={s} />)}
          </div>
        </>
      )}

      {/* Distribution filter */}
      <div className="eda-section-label">Distributions</div>
      <div className="eda-toolbar">
        <div className="eda-filters">
          <button className={`eda-filter ${filter==='all'?'active':''}`} onClick={() => setFilter('all')}>
            All <span>{charted.length}</span>
          </button>
          <button className={`eda-filter ${filter==='numeric'?'active':''}`} onClick={() => setFilter('numeric')}>
            Numeric <span>{numericCount}</span>
          </button>
          <button className={`eda-filter ${filter==='cat'?'active':''}`} onClick={() => setFilter('cat')}>
            Categorical <span>{catCount}</span>
          </button>
          {timeCount > 0 && (
            <button className={`eda-filter ${filter==='time'?'active':''}`} onClick={() => setFilter('time')}>
              Timeline <span>{timeCount}</span>
            </button>
          )}
        </div>
      </div>

      {filtered.length > 0 ? (
        <div className="charts-grid">
          {filtered.map(d => {
            if (d.type === 'histogram') return <HistogramChart key={d.column} data={d} />
            if (d.type === 'barchart') return <TopValuesChart key={d.column} data={d} />
            if (d.type === 'timeline') return <Timeline key={d.column} data={d} />
            return null
          })}
        </div>
      ) : (
        <div className="eda-empty">No columns to display for this filter.</div>
      )}

      {/* Skipped columns */}
      {skipped.length > 0 && (
        <div className="skipped-section">
          <button className="skipped-toggle" onClick={() => setShowSkipped(!showSkipped)}>
            {showSkipped ? '▼' : '▶'} {skipped.length} columns not charted
          </button>
          {showSkipped && (
            <div className="skipped-list">
              {skipped.map(s => (
                <div key={s.column} className="skipped-item">
                  <span className="skipped-col">{s.column}</span>
                  <span className="skipped-reason">{s.reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Correlation matrix */}
      {eda.correlation && <CorrelationMatrix correlation={eda.correlation} />}
    </div>
  )
}
