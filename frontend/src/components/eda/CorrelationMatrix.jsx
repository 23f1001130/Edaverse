import React from 'react'

function getColor(value) {
  if (value === null) return '#f3f4f6'
  const abs = Math.abs(value)
  if (value > 0) {
    const intensity = Math.round(abs * 220)
    return `rgb(${255 - intensity}, ${255 - intensity}, 255)`
  } else {
    const intensity = Math.round(abs * 220)
    return `rgb(255, ${255 - intensity}, ${255 - intensity})`
  }
}

function getTextColor(value) {
  if (value === null) return '#9ca3af'
  return Math.abs(value) > 0.5 ? '#fff' : '#374151'
}

export default function CorrelationMatrix({ correlation }) {
  if (!correlation) return null
  const { columns, matrix } = correlation

  const lookup = {}
  matrix.forEach(({ x, y, value }) => { lookup[`${x}||${y}`] = value })

  return (
    <div className="chart-card full-width">
      <div className="chart-header">
        <span className="chart-col">Correlation matrix</span>
        <span className="chart-badge numeric">Pearson</span>
      </div>
      <div className="corr-scroll">
        <table className="corr-table">
          <thead>
            <tr>
              <th></th>
              {columns.map(c => (
                <th key={c} title={c}>
                  {c.length > 8 ? c.slice(0, 8) + '…' : c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {columns.map(row => (
              <tr key={row}>
                <td className="corr-row-label" title={row}>
                  {row.length > 10 ? row.slice(0, 10) + '…' : row}
                </td>
                {columns.map(col => {
                  const val = lookup[`${row}||${col}`]
                  return (
                    <td
                      key={col}
                      style={{ background: getColor(val), color: getTextColor(val) }}
                      title={`${row} × ${col}: ${val?.toFixed(3) ?? 'n/a'}`}
                    >
                      {val !== null && val !== undefined ? val.toFixed(2) : '–'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="corr-legend">
        <span style={{color:'#2563eb'}}>■ positive</span>
        <span style={{color:'#dc2626'}}>■ negative</span>
        <span style={{color:'#9ca3af'}}>■ no data</span>
      </div>
    </div>
  )
}
