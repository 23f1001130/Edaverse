import React from 'react'

export default function NullsChart({ nulls }) {
  const hasSomeNulls = nulls.some(n => n.null_count > 0)

  return (
    <div className="chart-card full-width">
      <div className="chart-header">
        <span className="chart-col">Missing values</span>
        <span className="chart-badge neutral">all columns</span>
      </div>
      {!hasSomeNulls ? (
        <div className="nulls-clean">✓ No missing values across all columns</div>
      ) : (
        <div className="nulls-grid">
          {nulls.map(n => (
            <div key={n.column} className="null-row">
              <span className="null-col-name" title={n.column}>
                {n.column.length > 18 ? n.column.slice(0, 18) + '…' : n.column}
              </span>
              <div className="null-track">
                <div
                  className="null-fill"
                  style={{
                    width: `${n.null_pct}%`,
                    background: n.null_pct === 0 ? '#16a34a' : n.null_pct < 10 ? '#d97706' : '#dc2626'
                  }}
                />
              </div>
              <span
                className="null-pct-label"
                style={{ color: n.null_pct === 0 ? '#16a34a' : n.null_pct < 10 ? '#d97706' : '#dc2626' }}
              >
                {n.null_pct}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
