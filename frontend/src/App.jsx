import React, { useState } from 'react'
import Uploader from './components/Uploader.jsx'
import Results from './components/Results.jsx'
import History from './pages/History.jsx'
import { fetchDataset, uploadFile } from './services/api.js'
import './App.css'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loadingDataset, setLoadingDataset] = useState(false)
  const [lastFile, setLastFile] = useState(null)
  const [reparsing, setReparsing] = useState(false)

  function handleResult(data, file) {
    setResult(data)
    setLastFile(file || null)
    setError(null)
  }

  function handleError(msg) {
    setError(msg)
    setResult(null)
  }

  function reset() {
    setResult(null)
    setError(null)
    setLastFile(null)
  }

  async function handleSelectDataset(id) {
    setLoadingDataset(true)
    try {
      const data = await fetchDataset(id)
      setResult(data)
      setLastFile(null)
      setError(null)
    } catch (err) {
      setError('Could not load dataset')
    } finally {
      setLoadingDataset(false)
    }
  }

  async function handleReparse(headerRow) {
    if (!lastFile) return
    setReparsing(true)
    try {
      const data = await uploadFile(lastFile, null, headerRow)
      if (data.success) {
        setResult(data)
      } else {
        setError(data.error || 'Re-parse failed')
      }
    } catch (err) {
      setError('Re-parse failed')
    } finally {
      setReparsing(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">Dataflow</span>
          </div>
          {result && (
            <button className="btn-ghost" onClick={reset}>← Upload another</button>
          )}
        </div>
      </header>

      <main className="app-main">
        {!result ? (
          <div className="upload-view">
            <div className="hero">
              <h1>Understand your data instantly</h1>
              <p>Drop any CSV, Excel, or JSON file. Get schema, types, nulls, and sample rows — immediately.</p>
            </div>
            <Uploader
              onResult={handleResult}
              onError={handleError}
              loading={loading}
              setLoading={setLoading}
            />
            {error && (
              <div className="error-banner"><strong>Error:</strong> {error}</div>
            )}
            {loadingDataset ? (
              <div className="loading-dataset">Loading dataset…</div>
            ) : (
              <History onSelect={handleSelectDataset} />
            )}
          </div>
        ) : (
          <Results
            data={result}
            onReparse={lastFile ? handleReparse : null}
            reparsing={reparsing}
          />
        )}
      </main>
    </div>
  )
}
