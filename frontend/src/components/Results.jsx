import React, { useState } from 'react'
import EDA from '../pages/EDA.jsx'
import AIChat from '../pages/AIChat.jsx'
import Cleaning from '../pages/Cleaning.jsx'
import './Results.css'

const TYPE_COLORS = {
  integer: { bg: '#eff6ff', text: '#1d4ed8', label: 'int' },
  float: { bg: '#f0fdf4', text: '#15803d', label: 'float' },
  text: { bg: '#fafafa', text: '#374151', label: 'text' },
  categorical: { bg: '#fdf4ff', text: '#7e22ce', label: 'cat' },
  datetime: { bg: '#fff7ed', text: '#c2410c', label: 'date' },
  boolean: { bg: '#f0fdf4', text: '#166534', label: 'bool' },
  empty: { bg: '#f9fafb', text: '#9ca3af', label: 'empty' },
}

function TypeBadge({ type }) {
  const c = TYPE_COLORS[type] || TYPE_COLORS.text
  return <span className="type-badge" style={{ background: c.bg, color: c.text }}>{c.label}</span>
}

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function NullBar({ pct }) {
  const safe = Math.min(Math.max(pct, 0), 100)
  const color = safe === 0 ? '#16a34a' : safe < 10 ? '#d97706' : '#dc2626'
  return (
    <div className="null-bar-wrap" title={`${safe}% null`}>
      <div className="null-bar-track">
        <div className="null-bar-fill" style={{ width: `${safe}%`, background: color }} />
      </div>
      <span className="null-bar-label" style={{ color }}>{safe}%</span>
    </div>
  )
}

function HeaderPicker({ rawRows, suggestion, onReparse, reparsing }) {
  const [open, setOpen] = useState(!!suggestion)
  const suggestedRow = suggestion?.suggested_row

  return (
    <div className={`header-picker ${suggestion ? 'has-hint' : ''}`}>
      <div className="hp-bar" onClick={() => setOpen(o => !o)}>
        <div className="hp-bar-left">
          <span className="hp-icon">{suggestion ? '↻' : '☰'}</span>
          <span className="hp-title">
            {suggestion
              ? suggestion.message
              : 'Header row'}
          </span>
        </div>
        <span className="hp-chevron">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="hp-body">
          <p className="hp-help">Click the row that contains your column names:</p>
          <div className="hp-rows">
            {rawRows.map(row => (
              <button
                key={row.index}
                className={`hp-row ${row.index === suggestedRow ? 'suggested' : ''}`}
                onClick={() => onReparse(row.index)}
                disabled={reparsing}
              >
                <span className="hp-row-num">
                  {row.index}
                  {row.index === suggestedRow && <span className="hp-tag">suggested</span>}
                </span>
                <span className="hp-cells">
                  {row.cells.map((c, i) => (
                    <span key={i} className="hp-cell">{c || '—'}</span>
                  ))}
                </span>
              </button>
            ))}
          </div>
          {reparsing && <div className="hp-reparsing">Re-parsing…</div>}
        </div>
      )}
    </div>
  )
}

export default function Results({ data, onReparse, reparsing }) {
  const [tab, setTab] = useState('schema')
  const nullCols = data.schema.filter(c => c.null_count > 0).length
  const types = [...new Set(data.schema.map(c => c.type))]
  const hs = data.header_suggestion

  return (
    <div className="results">
      <div className="results-header">
        <div className="file-title">
          <span className="file-icon">📄</span>
          <div>
            <div className="file-name">{data.filename}</div>
            <div className="file-meta">
              Encoding: <strong>{data.encoding?.encoding}</strong>
              {data.encoding?.confidence < 0.9 && <span className="low-conf"> (low confidence)</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Rows" value={data.shape.rows.toLocaleString()} />
        <StatCard label="Columns" value={data.shape.columns} />
        <StatCard label="Cols with nulls" value={nullCols} sub={`of ${data.shape.columns}`} />
        <StatCard label="Data types" value={types.length} sub={types.join(', ')} />
      </div>

      {data.raw_rows?.length > 0 && onReparse && (
        <HeaderPicker
          rawRows={data.raw_rows}
          suggestion={hs}
          onReparse={onReparse}
          reparsing={reparsing}
        />
      )}

      {data.warnings?.length > 0 && (
        <div className="warnings">
          {data.warnings.map((w, i) => (
            <div key={i} className="warning-item">⚠ {w}</div>
          ))}
        </div>
      )}

      <div className="tabs">
        <button className={`tab ${tab === 'schema' ? 'active' : ''}`} onClick={() => setTab('schema')}>Schema</button>
        <button className={`tab ${tab === 'sample' ? 'active' : ''}`} onClick={() => setTab('sample')}>Sample rows</button>
        {data.id && (
          <button className={`tab ${tab === 'eda' ? 'active' : ''}`} onClick={() => setTab('eda')}>Analysis ✦</button>
        )}
        {data.id && (
          <button className={`tab ${tab === 'clean' ? 'active' : ''}`} onClick={() => setTab('clean')}>Clean ✦</button>
        )}
        {data.id && (
          <button className={`tab ${tab === 'ai' ? 'active' : ''}`} onClick={() => setTab('ai')}>Ask AI ✦</button>
        )}
      </div>

      {tab === 'schema' && (
        <div className="schema-table-wrap">
          <table className="schema-table">
            <thead>
              <tr><th>#</th><th>Column</th><th>Type</th><th>Nulls</th><th>Details</th></tr>
            </thead>
            <tbody>
              {data.schema.map((col, i) => (
                <tr key={col.name}>
                  <td className="col-index">{i + 1}</td>
                  <td className="col-name">{col.name}</td>
                  <td><TypeBadge type={col.type} /></td>
                  <td><NullBar pct={col.null_pct} /></td>
                  <td className="col-details">
                    {col.min !== undefined && <span>min {col.min} · max {col.max} · mean {col.mean}</span>}
                    {col.top_values && <span>{col.top_values.slice(0, 3).join(', ')}{col.top_values.length > 3 ? '…' : ''}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'sample' && (
        <div className="sample-wrap">
          <div className="sample-scroll">
            <table className="sample-table">
              <thead>
                <tr>{data.schema.map(col => <th key={col.name}>{col.name}</th>)}</tr>
              </thead>
              <tbody>
                {data.sample_rows.map((row, i) => (
                  <tr key={i}>
                    {data.schema.map(col => (
                      <td key={col.name}>
                        {row[col.name] === null || row[col.name] === undefined
                          ? <span className="null-cell">null</span>
                          : String(row[col.name])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'eda' && data.id && <EDA datasetId={data.id} filename={data.filename} />}
      {tab === 'clean' && data.id && <Cleaning datasetId={data.id} filename={data.filename} />}
      {tab === 'ai' && data.id && <AIChat datasetId={data.id} filename={data.filename} />}
    </div>
  )
}
