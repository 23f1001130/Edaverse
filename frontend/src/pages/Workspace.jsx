import React, { useState, useEffect } from 'react'
import Uploader from '../components/Uploader.jsx'
import WorkspaceResults from '../components/WorkspaceResults.jsx'
import HistoryPanel from '../components/HistoryPanel.jsx'
import { fetchDataset, uploadFile, loadDemo, apiFetch } from '../services/api.js'
import { getSetting, saveSettings, TOUR_REPLAY_EVENT } from '../services/toast.js'
import './Workspace.css'

export default function Workspace({ onHome, autoDemo }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFile, setLastFile] = useState(null)
  const [reparsing, setReparsing] = useState(false)
  const [nav, setNav] = useState('upload')  // upload | history | settings
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('edaverse_theme') || 'dark' } catch { return 'dark' }
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : '')
    try { localStorage.setItem('edaverse_theme', theme) } catch {}
  }, [theme])

  const themeControl = (
    <button
      className="ws-theme-toggle"
      onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      type="button"
    >
      {theme === 'dark' ? (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      ) : (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
      <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
    </button>
  )

  function handleResult(data, file) {
    setResult(data); setLastFile(file || null); setError(null); setNav('upload')
  }
  function handleError(msg) { setError(msg); setResult(null) }
  function reset() { setResult(null); setError(null); setLastFile(null); setNav('upload') }

  async function handleDemo() {
    setLoading(true)
    try {
      const data = await loadDemo()
      if (data.success) { setResult(data); setLastFile(null); setError(null) }
      else setError('Demo failed to load')
    } catch { setError('Demo failed to load') }
    finally { setLoading(false) }
  }

  useEffect(() => { if (autoDemo) handleDemo() }, [])

  async function handleSelectDataset(id) {
    try {
      const data = await fetchDataset(id)
      setResult(data); setLastFile(null); setError(null); setNav('upload')
    } catch { setError('Could not load dataset') }
  }

  async function handleReparse(headerRow) {
    if (!lastFile) return
    setReparsing(true)
    try {
      const data = await uploadFile(lastFile, null, headerRow)
      if (data.success) setResult(data)
      else setError(data.error || 'Re-parse failed')
    } catch { setError('Re-parse failed') }
    finally { setReparsing(false) }
  }

  return (
    <div className="ws">
      {/* Icon sidebar */}
      <aside className="ws-iconbar">
        <button className="ws-logo" onClick={onHome} title="Home" type="button">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1.5"/>
            <rect x="14" y="3" width="7" height="7" rx="1.5"/>
            <rect x="3" y="14" width="7" height="7" rx="1.5"/>
            <rect x="14" y="14" width="7" height="7" rx="1.5"/>
          </svg>
        </button>
        <button
          className={`ws-icon ${nav === 'upload' && !result ? 'active' : ''}`}
          onClick={() => { setNav('upload'); reset() }}
          title="New upload"
          type="button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </button>
        <button
          className={`ws-icon ${!result ? 'disabled' : nav === 'upload' ? 'active' : ''}`}
          onClick={() => result && setNav('upload')}
          title={result ? 'Analysis' : 'Upload a file first'}
          type="button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
        </button>
        <button
          className={`ws-icon ${nav === 'history' ? 'active' : ''}`}
          onClick={() => setNav('history')}
          title="History"
          type="button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </button>
        <button
          className={`ws-icon ${nav === 'settings' ? 'active' : ''}`}
          onClick={() => setNav('settings')}
          title="Settings"
          type="button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </aside>

      <div className="ws-content">
        {nav === 'history' ? (
          <HistoryPanel onSelect={handleSelectDataset} onClose={() => setNav('upload')} themeControl={themeControl} />
        ) : nav === 'settings' ? (
          <SettingsPanel onClose={() => setNav('upload')} onNavUpload={() => setNav('upload')} themeControl={themeControl} />
        ) : !result ? (
          <div className="ws-upload-screen">
            <div className="ws-topbar">
              <div className="ws-breadcrumb">
                <span className="ws-bc-workspace">My Workspace</span>
                <span className="ws-bc-sep">/</span>
                <span className="ws-bc-current">Upload</span>
              </div>
              {themeControl}
            </div>
            <Uploader
              onResult={handleResult}
              onError={handleError}
              loading={loading}
              setLoading={setLoading}
            />
            {!loading && (
            <div className="ws-demo-link">
                <button onClick={handleDemo} type="button">Try with demo dataset</button>
              </div>
            )}
            {error && <div className="ws-error">{error}</div>}
          </div>
        ) : (
          <WorkspaceResults
            data={result}
            onReparse={lastFile ? handleReparse : null}
            reparsing={reparsing}
            onReset={reset}
            themeControl={themeControl}
          />
        )}
      </div>
    </div>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`ws-toggle ${checked ? 'on' : ''}`}
      type="button"
    >
      <span className="ws-toggle-thumb" />
    </button>
  )
}

function SettingsRow({ label, description, checked, onChange }) {
  return (
    <div className="ws-setting-row">
      <div className="ws-setting-row-text">
        <div className="ws-setting-row-label">{label}</div>
        {description && <div className="ws-setting-row-desc">{description}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  )
}

function SelectRow({ label, description, value, options, onChange }) {
  return (
    <div className="ws-setting-row">
      <div className="ws-setting-row-text">
        <div className="ws-setting-row-label">{label}</div>
        {description && <div className="ws-setting-row-desc">{description}</div>}
      </div>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="ws-setting-select"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function SettingsPanel({ onClose, onNavUpload, themeControl }) {
  const BASE = import.meta.env.VITE_API_URL || ''
  const [health, setHealth] = useState(null)

  // Settings state — read from localStorage on mount
  const [notifEda,      setNotifEda]      = useState(() => getSetting('notifications.eda_complete', true))
  const [notifClean,    setNotifClean]    = useState(() => getSetting('notifications.cleaning_applied', true))
  const [notifFeatures, setNotifFeatures] = useState(() => getSetting('notifications.features_engineered', true))
  const [corrDefault,   setCorrDefault]   = useState(() => getSetting('analysis.default_correlation', 'pearson'))
  const [heatmapCols,   setHeatmapCols]   = useState(() => getSetting('analysis.heatmap_max_cols', 20))
  const [autoSelClean,  setAutoSelClean]  = useState(() => getSetting('cleaning.auto_select_all', true))

  useEffect(() => {
    apiFetch(`${BASE}/health`).then(r => r.ok ? r.json() : null).then(setHealth).catch(() => {})
  }, [])

  function set(path, value) {
    const keys = path.split('.')
    const patch = {}
    let cur = patch
    keys.forEach((k, i) => {
      if (i === keys.length - 1) cur[k] = value
      else { cur[k] = {}; cur = cur[k] }
    })
    saveSettings(patch)
  }

  function replayTour() {
    try { localStorage.removeItem('edaverse_workspace_tour_seen') } catch {}
    window.dispatchEvent(new CustomEvent(TOUR_REPLAY_EVENT))
    onNavUpload()
  }

  return (
    <div className="ws-panel">
      <div className="ws-topbar">
        <div className="ws-breadcrumb">
          <span className="ws-bc-workspace">My Workspace</span>
          <span className="ws-bc-sep">/</span>
          <span className="ws-bc-current">Settings</span>
        </div>
        {themeControl}
      </div>

      <div className="ws-settings">
        <div className="ws-settings-head">
          <h3>Settings</h3>
          <p>Preferences are saved in your browser and applied immediately.</p>
        </div>

        {/* Notifications */}
        <div className="ws-settings-section">
          <div className="ws-settings-section-title">Notifications</div>
          <div className="ws-setting-card" style={{ padding: 0, overflow: 'hidden' }}>
            <SettingsRow
              label="EDA analysis ready"
              description="Show a notification when the analysis stream finishes loading."
              checked={notifEda}
              onChange={v => { setNotifEda(v); set('notifications.eda_complete', v) }}
            />
            <SettingsRow
              label="Cleaning applied"
              description="Notify when you promote cleaned data as the active dataset."
              checked={notifClean}
              onChange={v => { setNotifClean(v); set('notifications.cleaning_applied', v) }}
            />
            <SettingsRow
              label="Features engineered"
              description="Notify when you promote engineered features as the active dataset."
              checked={notifFeatures}
              onChange={v => { setNotifFeatures(v); set('notifications.features_engineered', v) }}
            />
          </div>
        </div>

        {/* Analysis defaults */}
        <div className="ws-settings-section">
          <div className="ws-settings-section-title">Analysis defaults</div>
          <div className="ws-setting-card" style={{ padding: 0, overflow: 'hidden' }}>
            <SelectRow
              label="Default correlation method"
              description="Which method is pre-selected when you open the Correlations tab."
              value={corrDefault}
              options={[{ value: 'pearson', label: 'Pearson (linear)' }, { value: 'spearman', label: 'Spearman (rank)' }]}
              onChange={v => { setCorrDefault(v); set('analysis.default_correlation', v) }}
            />
            <SelectRow
              label="Heatmap max columns"
              description="Default column limit in the correlation heatmap for large datasets."
              value={String(heatmapCols)}
              options={[10, 20, 30, 50].map(n => ({ value: String(n), label: `${n} columns` }))}
              onChange={v => { setHeatmapCols(Number(v)); set('analysis.heatmap_max_cols', Number(v)) }}
            />
            <SettingsRow
              label="Auto-select all cleaning fixes"
              description="Pre-check all suggested fixes when you open the Cleaning Report."
              checked={autoSelClean}
              onChange={v => { setAutoSelClean(v); set('cleaning.auto_select_all', v) }}
            />
          </div>
        </div>

        {/* Server status */}
        <div className="ws-settings-section">
          <div className="ws-settings-section-title">Server status</div>
          <div className="ws-settings-status-grid">
            <div className="ws-status-item">
              <span className="ws-status-label">Storage</span>
              <span className="ws-status-val">{health ? health.storage : '…'}</span>
            </div>
            <div className="ws-status-item">
              <span className="ws-status-label">Datasets stored</span>
              <span className="ws-status-val">{health ? health.datasets_count : '…'}</span>
            </div>
            <div className="ws-status-item">
              <span className="ws-status-label">API</span>
              <span className="ws-status-val" style={{ color: health ? 'var(--green)' : 'var(--text-tertiary)' }}>
                {health ? 'Online' : 'Checking…'}
              </span>
            </div>
          </div>
        </div>

        {/* Tour */}
        <div className="ws-settings-section">
          <div className="ws-settings-section-title">Onboarding</div>
          <div className="ws-setting-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <div className="ws-setting-row-label">Workspace tour</div>
              <div className="ws-setting-row-desc">Re-run the guided tour that highlights every feature. Opens on your next dataset view.</div>
            </div>
            <button className="ws-tour-btn" onClick={replayTour} type="button">Replay tour</button>
          </div>
        </div>
      </div>
    </div>
  )
}
