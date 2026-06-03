import React, { useState, useEffect } from 'react'
import Uploader from '../components/Uploader.jsx'
import WorkspaceResults from '../components/WorkspaceResults.jsx'
import HistoryPanel from '../components/HistoryPanel.jsx'
import { fetchDataset, uploadFile, loadDemo } from '../services/api.js'
import './Workspace.css'

export default function Workspace({ onHome, autoDemo }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFile, setLastFile] = useState(null)
  const [reparsing, setReparsing] = useState(false)
  const [nav, setNav] = useState('upload')  // upload | history | settings

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
        <button className="ws-logo" onClick={onHome} title="Home">◧</button>
        <button
          className={`ws-icon ${nav === 'upload' && !result ? 'active' : ''}`}
          onClick={() => { setNav('upload'); reset() }}
          title="New upload"
        >↑</button>
        <button
          className={`ws-icon ${!result ? 'disabled' : nav === 'upload' ? 'active' : ''}`}
          onClick={() => result && setNav('upload')}
          title={result ? 'Analysis' : 'Upload a file first'}
        >▥</button>
        <button
          className={`ws-icon ${nav === 'history' ? 'active' : ''}`}
          onClick={() => setNav('history')}
          title="History"
        >◷</button>
        <button
          className={`ws-icon ${nav === 'settings' ? 'active' : ''}`}
          onClick={() => setNav('settings')}
          title="Settings"
        >⚙</button>
      </aside>

      <div className="ws-content">
        {nav === 'history' ? (
          <HistoryPanel onSelect={handleSelectDataset} onClose={() => setNav('upload')} />
        ) : nav === 'settings' ? (
          <SettingsPanel onClose={() => setNav('upload')} />
        ) : !result ? (
          <div className="ws-upload-screen">
            <div className="ws-topbar">
              <div className="ws-breadcrumb">
                <span className="ws-bc-workspace">My Workspace</span>
                <span className="ws-bc-sep">/</span>
                <span className="ws-bc-current">Upload</span>
              </div>
            </div>
            <Uploader
              onResult={handleResult}
              onError={handleError}
              loading={loading}
              setLoading={setLoading}
            />
            {!loading && (
              <div className="ws-demo-link">
                <button onClick={handleDemo}>Try with demo dataset →</button>
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
          />
        )}
      </div>
    </div>
  )
}

function SettingsPanel({ onClose }) {
  return (
    <div className="ws-panel">
      <div className="ws-topbar">
        <div className="ws-breadcrumb">
          <span className="ws-bc-workspace">My Workspace</span>
          <span className="ws-bc-sep">/</span>
          <span className="ws-bc-current">Settings</span>
        </div>
      </div>
      <div className="ws-settings">
        <h3>Settings</h3>
        <p className="ws-settings-note">edaverse runs entirely on your machine. Your data is never uploaded to any third-party server.</p>
        <div className="ws-setting-row">
          <span>Large file threshold</span>
          <span className="ws-setting-val">50 MB</span>
        </div>
        <div className="ws-setting-row">
          <span>AI provider</span>
          <span className="ws-setting-val">Ollama (local)</span>
        </div>
        <div className="ws-setting-row">
          <span>Max upload size</span>
          <span className="ws-setting-val">100 MB</span>
        </div>
      </div>
    </div>
  )
}
