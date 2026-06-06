import React, { useState, useEffect, useRef } from 'react'
import OverviewTab from './tabs/OverviewTab.jsx'
import DistributionsTab from './tabs/DistributionsTab.jsx'
import CorrelationsTab from './tabs/CorrelationsTab.jsx'
import TargetTab from './tabs/TargetTab.jsx'
import CleaningTab from './tabs/CleaningTab.jsx'
import FeatureEngineeringTab from './tabs/FeatureEngineeringTab.jsx'
import StepsTab from './tabs/StepsTab.jsx'
import AINarrative from './AINarrative.jsx'
import HeaderPicker from './HeaderPicker.jsx'
import WorkspaceTour from './WorkspaceTour.jsx'
import ToastContainer from './ToastContainer.jsx'
import { fireToast, getSetting, TOUR_REPLAY_EVENT } from '../services/toast.js'
import './WorkspaceResults.css'

const BASE = import.meta.env.VITE_API_URL || ''

const TABS = ['Overview', 'Distributions', 'Correlations', 'Target Analysis', 'Cleaning Report', 'Feature Engineering', 'Steps Applied']

async function getAuthHeaders() {
  try {
    const token = await window.Clerk?.session?.getToken()
    if (token) return { Authorization: `Bearer ${token}` }
  } catch {}
  return {}
}

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

export default function WorkspaceResults({ data: initialData, onReparse, reparsing, onReset, themeControl }) {
  const [data, setData] = useState(initialData)
  const [tab, setTab] = useState('Overview')
  const [visitedTabs, setVisitedTabs] = useState(new Set(['Overview']))
  const [search, setSearch] = useState('')
  const [activeCol, setActiveCol] = useState(null)
  const [eda, setEda] = useState(null)
  const [edaLoading, setEdaLoading] = useState(true)
  const [edaStage, setEdaStage] = useState({ label: 'Initializing…', progress: 0 })
  const [edaError, setEdaError] = useState(false)
  const [narrativeOpen, setNarrativeOpen] = useState(false)
  const [showTour, setShowTour] = useState(false)
  const edaAbortRef = useRef(null)
  const edaDoneRef = useRef(false)  // fire EDA toast only once per dataset

  useEffect(() => { setData(initialData); edaDoneRef.current = false }, [initialData])

  // Listen for tour replay event from Settings
  useEffect(() => {
    function handle() { setShowTour(true) }
    window.addEventListener(TOUR_REPLAY_EVENT, handle)
    return () => window.removeEventListener(TOUR_REPLAY_EVENT, handle)
  }, [])

  function refreshEda() {
    if (!data?.id) return
    if (edaAbortRef.current) edaAbortRef.current.abort()
    const controller = new AbortController()
    edaAbortRef.current = controller
    setEdaLoading(true)
    setEdaError(false)
    setEdaStage({ label: 'Initializing…', progress: 0 })

    getAuthHeaders().then(headers => {
      fetch(`${BASE}/api/datasets/${data.id}/eda/stream`, { headers, signal: controller.signal })
        .then(r => {
          if (!r.ok || !r.body) {
            return r.json().catch(() => ({})).then(d => { setEda(d); setEdaError(true); setEdaLoading(false) })
          }
          const reader = r.body.getReader()
          const dec = new TextDecoder()
          let buf = ''
          function pump() {
            return reader.read().then(({ done, value }) => {
              if (done) { setEdaLoading(false); return }
              buf += dec.decode(value, { stream: true })
              const lines = buf.split('\n')
              buf = lines.pop()
              for (const line of lines) {
                if (!line.startsWith('data: ')) continue
                try {
                  const ev = JSON.parse(line.slice(6))
                  setEdaStage({ label: ev.label || ev.stage, progress: ev.progress })
                  if (ev.progress >= 1.0 && ev.data) {
                    setEda(ev.data)
                    setEdaLoading(false)
                    if (!edaDoneRef.current) {
                      edaDoneRef.current = true
                      if (getSetting('notifications.eda_complete', true)) {
                        fireToast('EDA analysis ready', 'success')
                      }
                      // Show workspace tour on first-ever EDA load
                      if (!localStorage.getItem('edaverse_workspace_tour_seen')) {
                        setTimeout(() => setShowTour(true), 600)
                      }
                    }
                  }
                  if (ev.stage === 'error') { setEdaError(true); setEdaLoading(false) }
                } catch {}
              }
              return pump()
            })
          }
          return pump()
        })
        .catch(err => { if (err.name !== 'AbortError') { setEdaError(true); setEdaLoading(false) } })
    })
  }

  function goTab(t) {
    setTab(t)
    setVisitedTabs(prev => { const n = new Set(prev); n.add(t); return n })
  }

  function handleDataUpdate(updated) {
    if (updated) { setData(updated); setActiveCol(null); }
    refreshEda()
  }

  async function openNotebookInColab() {
    if (!data.id) return
    try {
      const headers = await getAuthHeaders()
      const r = await fetch(`${BASE}/api/datasets/${data.id}/notebook`, { headers })
      if (!r.ok) return
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = (data.filename?.replace(/\.[^.]+$/, '') || 'workflow') + '_workflow.ipynb'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 30000)
    } catch {}
    setTimeout(() => window.open('https://colab.research.google.com/#create=true', '_blank'), 0)
  }

  useEffect(() => {
    if (!data.id) { setEdaLoading(false); setEdaError(false); return }
    refreshEda()
  }, [data.id])

  const filteredCols = data.schema.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="wr">
      {showTour && <WorkspaceTour onDone={() => setShowTour(false)} />}
      <ToastContainer />
      <div className="wr-topbar" data-tour="topbar">
        <div className="wr-breadcrumb">
          <span className="wr-bc-workspace" onClick={onReset} style={{cursor:'pointer'}}>My Workspace</span>
          <span className="wr-bc-sep">/</span>
          <span className="wr-bc-file">{data.filename}</span>
          {(() => {
            if (edaError) return <span className="wr-eda-badge error">EDA unavailable</span>
            if (edaLoading) return <span className="wr-eda-badge running">{edaStage.label}</span>
            const milestones = [
              { label: 'EDA analyzed',          done: eda !== null },
              { label: 'Distributions explored', done: visitedTabs.has('Distributions') },
              { label: 'Correlations explored',  done: visitedTabs.has('Correlations') },
              { label: 'Target analysis done',   done: visitedTabs.has('Target Analysis') },
              { label: 'Cleaning reviewed',      done: visitedTabs.has('Cleaning Report') },
              { label: 'Cleaning applied',       done: (data.workflow?.applied_cleaning_fix_ids?.length || 0) > 0 },
              { label: 'Features engineered',    done: (data.workflow?.applied_feature_op_ids?.length || 0) > 0 },
            ]
            const done = milestones.filter(m => m.done).length
            const total = milestones.length
            const tooltip = milestones.map(m => `${m.done ? '✓' : '○'} ${m.label}`).join('\n')
            return (
              <span
                className={`wr-eda-badge ${done === total ? 'complete' : 'running'}`}
                data-tour="eda-badge"
                title={tooltip}
                style={{cursor:'default'}}
              >
                {done} / {total} steps
                <span style={{
                  display:'inline-block', marginLeft:6, width:32, height:4,
                  background:'rgba(255,255,255,0.15)', borderRadius:2, verticalAlign:'middle',
                }}>
                  <span style={{
                    display:'block', height:'100%', borderRadius:2,
                    width:`${Math.round(done/total*100)}%`,
                    background: done === total ? 'var(--green)' : 'var(--accent)',
                    transition:'width .4s',
                  }} />
                </span>
              </span>
            )
          })()}
        </div>
        <div className="wr-actions" data-tour="actions">
          {themeControl}
          <button className="wr-narrative-btn" data-tour="ai-btn" onClick={() => setNarrativeOpen(true)} title="AI Narrative">
            <svg className="wr-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
              <path d="M5 3v4M3 5h4M19 17v4M17 19h4"/>
            </svg>
            AI Narrative
          </button>
          <button className="wr-export-btn" onClick={() => data.id && window.open(`${BASE}/api/datasets/${data.id}/download`, '_blank')} title="Export CSV">
            <svg className="wr-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export
          </button>
          <button className="wr-export-btn" onClick={() => data.id && window.open(`${BASE}/api/datasets/${data.id}/report`, '_blank')} title="HTML Report">
            <svg className="wr-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Report
          </button>
          <button className="wr-export-btn" onClick={openNotebookInColab} title="Open as Jupyter Notebook">
            <svg className="wr-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"/>
              <polyline points="8 6 2 12 8 18"/>
            </svg>
            Notebook
          </button>
        </div>
      </div>

      <div className="wr-body">
        <aside className="wr-colbar" data-tour="colbar">
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
                onClick={() => { setActiveCol(col.name); goTab('Distributions') }}
              />
            ))}
          </div>
        </aside>

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

          <div className="wr-tabs" data-tour="tabs">
            {TABS.map(t => (
              <button
                key={t}
                className={`wr-tab ${tab === t ? 'active' : ''}`}
                data-tour={`tab-${t.toLowerCase().replace(/\s+/g, '-')}`}
                onClick={() => goTab(t)}
              >{t}</button>
            ))}
          </div>

          <div className="wr-tab-content">
            {edaLoading && tab !== 'Cleaning Report' && tab !== 'Feature Engineering' && tab !== 'Steps Applied' ? (
              <div className="wr-loading">
                <div className="wr-progress-bar">
                  <div className="wr-progress-fill" style={{ width: `${Math.round(edaStage.progress * 100)}%` }} />
                </div>
                <div className="wr-loading-stage">{edaStage.label}</div>
              </div>
            ) : (
              <>
                {tab === 'Overview' && <OverviewTab data={data} eda={eda} />}
                {tab === 'Distributions' && <DistributionsTab data={data} eda={eda} activeCol={activeCol} setActiveCol={setActiveCol} />}
                {tab === 'Correlations' && <CorrelationsTab eda={eda} />}
                {tab === 'Target Analysis' && <TargetTab data={data} eda={eda} />}
                {tab === 'Cleaning Report' && <CleaningTab data={data} onDataUpdate={handleDataUpdate} />}
                {tab === 'Feature Engineering' && <FeatureEngineeringTab data={data} onDataUpdate={handleDataUpdate} />}
                {tab === 'Steps Applied' && <StepsTab data={data} />}
              </>
            )}
          </div>
        </main>
      </div>

      {narrativeOpen && (
        <AINarrative datasetId={data.id} filename={data.filename} schema={data.schema || []} onClose={() => setNarrativeOpen(false)} />
      )}
    </div>
  )
}
