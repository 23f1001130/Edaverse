import React, { useState, useEffect } from 'react'
import OverviewTab from './tabs/OverviewTab.jsx'
import DistributionsTab from './tabs/DistributionsTab.jsx'
import CorrelationsTab from './tabs/CorrelationsTab.jsx'
import TargetTab from './tabs/TargetTab.jsx'
import CleaningTab from './tabs/CleaningTab.jsx'
import AINarrative from './AINarrative.jsx'
import HeaderPicker from './HeaderPicker.jsx'
import './WorkspaceResults.css'

const BASE = import.meta.env.VITE_API_URL || ''

const TABS = ['Overview', 'Distributions', 'Correlations', 'Target Analysis', 'Cleaning Report']

function ColumnRow({ col, active, onClick }) {
  const isNum = ['integer', 'float'].includes(col.type)
  const pct = col.null_pct || 0
  const barColor = pct === 0 ? 'var(--green)' : pct < 10 ? 'var(--amber)' : 'var(--red)'
  return (
    <button className={`col-row ${active ? 'active' : ''}`} onClick={onClick}>
      <div className="col-row-top">
        <span className="col-row-name">{col.name}</span>
        <span className={`col-row-tag ${isNum ? 'num' : 'cat'}`}>{isNum ? 'NUM' : 'CAT'}</span>
      </div>
      <div className="col-row-bar">
        <div className="col-row-bar-track">
          <div className="col-row-bar-fill" style={{ width: `${Math.max(pct, 1)}%`, background: barColor }} />
        </div>
        <span className="col-row-pct">{pct}%</span>
      </div>
    </button>
  )
}

export default function WorkspaceResults({ data: initialData, onReparse, reparsing, onReset }) {
  const [data, setData] = useState(initialData)
  const [tab, setTab] = useState('Overview')
  const [search, setSearch] = useState('')
  const [activeCol, setActiveCol] = useState(null)
  const [eda, setEda] = useState(null)
  const [edaLoading, setEdaLoading] = useState(true)
  const [narrativeOpen, setNarrativeOpen] = useState(false)

  useEffect(() => { setData(initialData) }, [initialData])

  function refreshEda() {
    if (!data.id) return
    setEdaLoading(true)
    fetch(`${BASE}/api/datasets/${data.id}/eda`)
      .then(r => r.json())
      .then(d => { setEda(d); setEdaLoading(false) })
      .catch(() => setEdaLoading(false))
  }

  function handleDataUpdate(updated) {
    if (updated) { setData(updated); setActiveCol(null); }
    refreshEda()
  }

  useEffect(() => {
    if (!data.id) { setEdaLoading(false); return }
    refreshEda()
  }, [data.id])

  const filteredCols = data.schema.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="wr">
      {/* Top bar */}
      <div className="wr-topbar">
        <div className="wr-breadcrumb">
          <span className="wr-bc-workspace" onClick={onReset} style={{cursor:'pointer'}}>My Workspace</span>
          <span className="wr-bc-sep">/</span>
          <span className="wr-bc-file">{data.filename}</span>
          <span className="wr-badge-complete">EDA complete</span>
        </div>
        <div className="wr-actions">
          <button className="wr-narrative-btn" onClick={() => setNarrativeOpen(true)}>
            <span>✦</span> AI Narrative
          </button>
          <button className="wr-export-btn" onClick={() => data.id && window.open(`${BASE}/api/datasets/${data.id}/download`, '_blank')}>
            ↓ Export
          </button>
        </div>
      </div>

      <div className="wr-body">
        {/* Column sidebar */}
        <aside className="wr-colbar">
          <div className="wr-colbar-header">
            <span>COLUMNS</span>
            <span className="wr-colbar-count">{data.schema.length}</span>
          </div>
          <div className="wr-colsearch">
            <span className="wr-colsearch-icon">⌕</span>
            <input
              placeholder="Search columns…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="wr-collist">
            {filteredCols.map(col => (
              <ColumnRow
                key={col.name}
                col={col}
                active={activeCol === col.name}
                onClick={() => { setActiveCol(col.name); setTab('Distributions') }}
              />
            ))}
          </div>
        </aside>

        {/* Main panel */}
        <main className="wr-main">
          {onReparse && (
            <div className="wr-header-picker-wrap">
              <HeaderPicker
                rawRows={data.raw_rows || []}
                suggestion={data.header_suggestion}
                onReparse={onReparse}
                reparsing={reparsing}
              />
            </div>
          )}

          <div className="wr-tabs">
            {TABS.map(t => (
              <button
                key={t}
                className={`wr-tab ${tab === t ? 'active' : ''}`}
                onClick={() => setTab(t)}
              >{t}</button>
            ))}
          </div>

          <div className="wr-tab-content">
            {edaLoading ? (
              <div className="wr-loading"><div className="up-spinner" />Computing analysis…</div>
            ) : (
              <>
                {tab === 'Overview' && <OverviewTab data={data} eda={eda} />}
                {tab === 'Distributions' && <DistributionsTab data={data} eda={eda} activeCol={activeCol} setActiveCol={setActiveCol} />}
                {tab === 'Correlations' && <CorrelationsTab eda={eda} />}
                {tab === 'Target Analysis' && <TargetTab data={data} eda={eda} />}
                {tab === 'Cleaning Report' && <CleaningTab data={data} onDataUpdate={handleDataUpdate} />}
              </>
            )}
          </div>
        </main>
      </div>

      {narrativeOpen && (
        <AINarrative datasetId={data.id} filename={data.filename} onClose={() => setNarrativeOpen(false)} />
      )}
    </div>
  )
}
