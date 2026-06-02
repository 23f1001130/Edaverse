import React, { useEffect, useState } from 'react'
import './OllamaStatus.css'

const BASE = import.meta.env.VITE_API_URL || ''

export default function OllamaStatus({ onModel }) {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    fetch(`${BASE}/api/ai/status`)
      .then(r => r.json())
      .then(s => {
        setStatus(s)
        if (s.active_model && onModel) onModel(s.active_model)
      })
      .catch(() => setStatus({ running: false }))
  }, [])

  if (!status) return null

  if (!status.running) return (
    <div className="ollama-badge offline">
      <span className="ollama-dot" />
      Ollama offline —
      <a href="https://ollama.com" target="_blank" rel="noreferrer"> install</a>
      , then run <code>ollama pull llama3.2:3b</code>
    </div>
  )

  return (
    <div className="ollama-badge online">
      <span className="ollama-dot" />
      {status.active_model}
    </div>
  )
}
