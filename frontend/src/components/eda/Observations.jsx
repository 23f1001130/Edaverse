import React from 'react'

const ICONS = {
  missing: '○', key: '🔑', correlation: '⟂', outlier: '◆',
  timeseries: '📈', clean: '✓',
}
const SEV_COLORS = {
  high: { bg: '#fef2f2', border: '#fecaca', text: '#b91c1c' },
  medium: { bg: '#fffbeb', border: '#fcd34d', text: '#92400e' },
  info: { bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
}

export default function Observations({ observations }) {
  if (!observations?.length) return null
  return (
    <div className="chart-card full-width">
      <div className="chart-header">
        <span className="chart-col">Key observations</span>
        <span className="chart-badge numeric">auto-detected</span>
      </div>
      <div className="obs-list">
        {observations.map((o, i) => {
          const c = SEV_COLORS[o.severity] || SEV_COLORS.info
          return (
            <div key={i} className="obs-item" style={{ background: c.bg, borderColor: c.border }}>
              <span className="obs-icon">{ICONS[o.type] || '•'}</span>
              <span className="obs-text" style={{ color: c.text }}>{o.text}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
