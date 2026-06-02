import React, { useState, useRef, useEffect } from 'react'
import OllamaStatus from '../components/OllamaStatus.jsx'
import './AIChat.css'

const BASE = import.meta.env.VITE_API_URL || ''

const SUGGESTIONS = [
  "What are the main data quality issues?",
  "Which columns should I clean first?",
  "Write pandas code to find outliers",
  "Summarize the key statistics",
  "What patterns are worth investigating?",
  "Write code to plot the distributions",
]

function Message({ msg }) {
  if (msg.thinking) {
    return (
      <div className="msg assistant">
        <div className="msg-bubble thinking-bubble">
          <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
        </div>
      </div>
    )
  }
  return (
    <div className={`msg ${msg.role}`}>
      <div className="msg-bubble">
        {msg.content.split('\n').map((line, i) => {
          if (line.startsWith('```')) return null
          if (line.startsWith('    ') || line.match(/^(import |df\.|pd\.|plt\.)/)) {
            return <code key={i} className="msg-code-line">{line}</code>
          }
          return line ? <p key={i}>{line}</p> : <br key={i} />
        })}
        {msg.streaming && <span className="cursor">▋</span>}
      </div>
    </div>
  )
}


export default function AIChat({ datasetId, filename }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [model, setModel] = useState(null)
  const [insight, setInsight] = useState(null)
  const [insightLoading, setInsightLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadInsight() {
    setInsightLoading(true)
    try {
      const r = await fetch(`${BASE}/api/datasets/${datasetId}/insight`, { method: 'POST' })
      const data = await r.json()
      if (data.insight) setInsight(data)
      else setInsight({ error: data.detail || 'Failed to generate insight' })
    } catch (e) {
      setInsight({ error: e.message })
    } finally {
      setInsightLoading(false)
    }
  }

  async function sendMessage(text) {
    if (!text.trim() || loading) return
    const userMsg = { role: 'user', content: text }
    const newHistory = [...messages, userMsg]
    setMessages(newHistory)
    setInput('')
    setLoading(true)

    const assistantMsg = { role: 'assistant', content: '', streaming: true }
    setMessages(m => [...m, assistantMsg])

    try {
      const r = await fetch(`${BASE}/api/datasets/${datasetId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newHistory.map(m => ({ role: m.role, content: m.content })),
          model,
        }),
      })

      const reader = r.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6)
          if (payload === '[DONE]') break
          try {
            const { token } = JSON.parse(payload)
            accumulated += token
            setMessages(m => {
              const updated = [...m]
              updated[updated.length - 1] = {
                role: 'assistant',
                content: accumulated,
                streaming: true,
                thinking: false,
              }
              return updated
            })
          } catch {}
        }
      }

      setMessages(m => {
        const updated = [...m]
        updated[updated.length - 1] = { role: 'assistant', content: accumulated }
        return updated
      })
    } catch (e) {
      setMessages(m => {
        const updated = [...m]
        updated[updated.length - 1] = { role: 'assistant', content: `Error: ${e.message}` }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="ai-chat">
      {/* Header */}
      <div className="ai-header">
        <OllamaStatus onModel={setModel} />
      </div>

      {/* Insight panel */}
      <div className="insight-panel">
        <div className="insight-header">
          <span className="insight-title">Auto insight</span>
          <button
            className="insight-btn"
            onClick={loadInsight}
            disabled={insightLoading || !model}
          >
            {insightLoading ? 'Analyzing…' : insight ? 'Regenerate' : '✦ Generate report'}
          </button>
        </div>
        {insight?.error && <div className="insight-error">{insight.error}</div>}
        {insight?.insight && (
          <div className="insight-body">
            <div className="insight-model">via {insight.model}</div>
            {insight.insight.split('\n').filter(Boolean).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        )}
        {!insight && !insightLoading && (
          <div className="insight-empty">
            Click "Generate report" to get an AI analysis of your dataset.
          </div>
        )}
      </div>

      {/* Chat */}
      <div className="chat-area">
        {messages.length === 0 ? (
          <div className="suggestions">
            <p className="suggestions-label">Ask anything about <strong>{filename}</strong></p>
            <div className="suggestions-grid">
              {SUGGESTIONS.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => sendMessage(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((msg, i) => <Message key={i} msg={msg} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="chat-input-wrap">
        <textarea
          className="chat-input"
          placeholder={model ? `Ask about ${filename}… (Enter to send)` : 'Start Ollama to enable chat'}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={!model || loading}
          rows={1}
        />
        <button
          className="send-btn"
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || !model || loading}
        >
          {loading ? '…' : '↑'}
        </button>
      </div>
    </div>
  )
}
