import React, { useState } from 'react'
import './HeaderPicker.css'

export default function HeaderPicker({ rawRows, suggestion, onReparse, reparsing }) {
  const [open, setOpen] = useState(!!suggestion)
  if (!rawRows || rawRows.length === 0) return null
  const suggestedRow = suggestion?.suggested_row

  return (
    <div className={`hp ${suggestion ? 'hint' : ''}`}>
      <div className="hp-bar" onClick={() => setOpen(o => !o)}>
        <div className="hp-bar-left">
          <span className="hp-icon">{suggestion ? '↻' : '☰'}</span>
          <span className="hp-title">{suggestion ? suggestion.message : 'Header row'}</span>
        </div>
        <span className="hp-chevron">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="hp-body">
          <p className="hp-help">Click the row that contains your column names:</p>
          <div className="hp-rows">
            {rawRows.map(row => (
              <button key={row.index} className={`hp-row ${row.index===suggestedRow?'suggested':''}`}
                onClick={() => onReparse(row.index)} disabled={reparsing}>
                <span className="hp-num">{row.index}{row.index===suggestedRow && <span className="hp-tag">suggested</span>}</span>
                <span className="hp-cells">{row.cells.map((c,i)=><span key={i} className="hp-cell">{c||'—'}</span>)}</span>
              </button>
            ))}
          </div>
          {reparsing && <div className="hp-reparsing">Re-parsing…</div>}
        </div>
      )}
    </div>
  )
}
