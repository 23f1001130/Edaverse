import React, { useEffect, useState } from 'react'
import './AINarrative.css'

const BASE = import.meta.env.VITE_API_URL || ''

const PROVIDERS = [
  { id:'local', name:'Local (Ollama)', needsKey:false, hint:'Private — runs on your machine', models:[] },
  { id:'groq', name:'Groq', needsKey:true, hint:'Fast & free tier · your key',
    models:['llama-3.3-70b-versatile','llama-3.1-8b-instant','mixtral-8x7b-32768','gemma2-9b-it'] },
  { id:'openai', name:'OpenAI', needsKey:true, hint:'Your key',
    models:['gpt-4o-mini','gpt-4o','gpt-4.1-mini','gpt-4.1'] },
  { id:'anthropic', name:'Anthropic', needsKey:true, hint:'Your key',
    models:['claude-haiku-4-5','claude-sonnet-4-6','claude-opus-4-8'] },
]

function loadKey(provider) {
  try { return localStorage.getItem(`edaverse_key_${provider}`) || '' } catch { return '' }
}
function saveKey(provider, key) {
  try { key ? localStorage.setItem(`edaverse_key_${provider}`, key) : localStorage.removeItem(`edaverse_key_${provider}`) } catch {}
}

function humanizeFetchError(err) {
  const s = (err?.message || '').toLowerCase()
  if (s.includes('failed to fetch') || s.includes('networkerror') || s.includes('network request failed'))
    return 'No connection — check your internet and try again.'
  if (s.includes('timeout') || s.includes('timed out'))
    return 'Request timed out. Try again.'
  return 'Something went wrong. Please try again.'
}

export default function AINarrative({ datasetId, filename, schema = [], onClose }) {
  const [status, setStatus] = useState(null)
  const [provider, setProv] = useState('local')
  const [prevProvider, setPrevProvider] = useState(null)
  const [apiKey, setApiKey] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [insight, setInsight] = useState(null)
  const [insightLoading, setInsightLoading] = useState(false)

  // Per-provider state: { messages, isFirstMessage }
  const [sessions, setSessions] = useState({})
  const [input, setInput] = useState('')
  const [ollamaModel, setOllamaModel] = useState(null)
  const [chatting, setChatting] = useState(false)

  const chat = sessions[provider]?.messages || []
  const isFirst = sessions[provider]?.isFirst !== false  // default true

  useEffect(() => {
    fetch(`${BASE}/api/ai/status`).then(r=>r.json()).then(s => {
      setStatus(s); if (s.active_model) setOllamaModel(s.active_model)
    }).catch(()=>setStatus({running:false}))
  }, [])

  useEffect(() => { setApiKey(loadKey(provider)) }, [provider])

  useEffect(() => {
    const p = PROVIDERS.find(x=>x.id===provider)
    setSelectedModel(p?.models?.[0] || '')
  }, [provider])

  const cfg = PROVIDERS.find(p=>p.id===provider)
  const ready = provider==='local' ? status?.running : !!apiKey
  const canAsk = !!datasetId && !chatting
  const numericCol = schema.find(c => ['integer', 'float'].includes(c.type))
  const categoricalCol = schema.find(c => ['categorical', 'text', 'boolean'].includes(c.type))
  const quickPrompts = [
    'How many rows?',
    'What columns are there?',
    categoricalCol ? `Most common value in ${categoricalCol.name}?` : null,
    numericCol ? `Average ${numericCol.name}?` : null,
  ].filter(Boolean)

  function setChat(msgs) {
    setSessions(prev => ({
      ...prev,
      [provider]: { ...prev[provider], messages: typeof msgs==='function' ? msgs(prev[provider]?.messages||[]) : msgs }
    }))
  }

  function markNotFirst() {
    setSessions(prev => ({ ...prev, [provider]: { ...prev[provider], isFirst: false } }))
  }

  function aiBody(extra={}) {
    return {
      provider,
      model: provider==='local' ? ollamaModel : (selectedModel||null),
      api_key: provider==='local' ? null : apiKey,
      ...extra
    }
  }

  function switchProvider(newProv) {
    setPrevProvider(provider)
    setProv(newProv)
    setInsight(null)
  }

  async function loadInsight() {
    if (!ready) return
    setInsightLoading(true); setInsight(null)
    try {
      const r = await fetch(`${BASE}/api/datasets/${datasetId}/insight`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(aiBody())
      })
      const text = await r.text()
      let d
      try { d = JSON.parse(text) }
      catch { d = { error: r.status===503 ? 'Ollama is not running — start it or pick a cloud provider.' : `Server error (${r.status}). Check backend logs.` } }
      setInsight(d.insight ? d : { error: d.detail || d.error || 'Failed to generate insight' })
    } catch(e){ setInsight({ error: humanizeFetchError(e) }) }
    finally { setInsightLoading(false) }
  }

  async function send(text) {
    if (!text.trim() || chatting || !datasetId) return

    const reqProvider = provider
    const switchedProvider = prevProvider !== null &&
      reqProvider !== prevProvider &&
      (sessions[reqProvider]?.messages||[]).length === 0 &&
      (sessions[prevProvider]?.messages||[]).length > 0
    const isFirstMsg = sessions[reqProvider]?.isFirst !== false

    const writeTo = (msgs) => setSessions(prev => ({
      ...prev,
      [reqProvider]: {
        ...prev[reqProvider],
        messages: typeof msgs==='function' ? msgs(prev[reqProvider]?.messages||[]) : msgs,
        isFirst: false,
      }
    }))

    const hist = [...(sessions[reqProvider]?.messages||[]), {role:'user',content:text}]
    writeTo([...hist, {role:'assistant',content:'',streaming:true}])
    setInput(''); setChatting(true)
    if (reqProvider !== prevProvider) setPrevProvider(reqProvider)

    try {
      const r = await fetch(`${BASE}/api/datasets/${datasetId}/chat`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(aiBody({
          messages: hist.map(m=>({role:m.role,content:m.content})),
          is_first_message: isFirstMsg,
          switched_provider: switchedProvider,
        }))
      })

      if (!r.ok || !r.body) {
        let msg = `Couldn't reach the AI service (${r.status}).`
        try { const j = await r.json(); msg = j.detail || msg } catch {}
        writeTo([...hist, {role:'assistant',content:msg,error:true}]); return
      }

      const reader = r.body.getReader(); const dec = new TextDecoder()
      let acc = ''; let errored = false
      while (true) {
        const {done,value} = await reader.read(); if (done) break
        for (const line of dec.decode(value).split('\n')) {
          if (!line.startsWith('data: ')) continue
          const p = line.slice(6); if (p==='[DONE]') break
          try {
            const obj = JSON.parse(p)
            if (obj.error) { writeTo([...hist,{role:'assistant',content:obj.error,error:true}]); errored=true; break }
            acc += obj.token
            writeTo([...hist,{role:'assistant',content:acc,streaming:true}])
          } catch {}
        }
        if (errored) break
      }
      if (!errored) writeTo([...hist,{role:'assistant',content:acc}])
    } catch(e) {
      writeTo([...hist,{role:'assistant',content:humanizeFetchError(e),error:true}])
    } finally { setChatting(false) }
  }

  return (
    <>
      <div className="nar-overlay" onClick={onClose} />
      <div className="nar-panel">
        <div className="nar-header">
          <div className="nar-title"><span>AI</span> What your data is telling you</div>
          <button className="nar-close" onClick={onClose}>x</button>
        </div>

        {/* Provider picker */}
        <div className="nar-providers">
          <div className="nar-prov-row">
            {PROVIDERS.map(p => (
              <button key={p.id}
                className={`nar-prov ${provider===p.id?'active':''}`}
                onClick={()=>switchProvider(p.id)}>
                {p.name}
                {sessions[p.id]?.messages?.length > 0 && (
                  <span className="nar-prov-dot" title="Has conversation" />
                )}
              </button>
            ))}
          </div>
          <div className="nar-prov-hint">{cfg.hint}</div>

          {cfg.needsKey && (
            <div className="nar-key-row">
              <div className="nar-key-input-wrap">
                <input type="password" className="nar-key-input"
                  placeholder={`Paste your ${cfg.name} API key`}
                  value={apiKey}
                  onChange={e=>{ setApiKey(e.target.value); saveKey(provider,e.target.value) }}
                />
                {apiKey && (
                  <button className="nar-key-clear" onClick={()=>{ setApiKey(''); saveKey(provider,'') }}>
                    Remove
                  </button>
                )}
              </div>
              <div className="nar-model-row">
                <select className="nar-model-select"
                  value={cfg.models.includes(selectedModel)?selectedModel:'__custom__'}
                  onChange={e=>setSelectedModel(e.target.value==='__custom__'?'':e.target.value)}>
                  {cfg.models.map(m=><option key={m} value={m}>{m}</option>)}
              <option value="__custom__">Custom</option>
                </select>
                {!cfg.models.includes(selectedModel) && (
                  <input className="nar-model-custom" placeholder="Enter model name"
                    value={selectedModel} onChange={e=>setSelectedModel(e.target.value)} />
                )}
              </div>
              <span className="nar-key-note nar-key-warn">
                Stored in your browser only. Never saved on our servers.
              </span>
            </div>
          )}

          {provider==='local' && status && !status.running && (
            <div className="nar-key-note" style={{marginTop:8,color:'var(--amber)'}}>
              Ollama not detected. <a href="https://ollama.com" target="_blank" rel="noreferrer">Install</a> &amp; run <code>ollama pull llama3.2:3b</code>, or pick a cloud provider above.
              Factual dataset questions still work without a provider.
            </div>
          )}
          {provider==='local' && status?.running && (
            <div className="nar-key-note" style={{marginTop:4,color:'var(--green)'}}>
              {status.active_model} running locally
            </div>
          )}
        </div>

        <div className="nar-body">
          {!insight && !insightLoading && (
            <button className="nar-generate" onClick={loadInsight} disabled={!ready}>
              Generate insight report
            </button>
          )}
          {insightLoading && <div className="nar-loading"><div className="up-spinner"/>Analysing your dataset</div>}
          {insight?.error && (
            <div className="nar-msg assistant error" style={{marginBottom:14}}>{insight.error}</div>
          )}
          {insight?.insight && (
            <div className="nar-insight">
              <div className="nar-model">via {insight.model}</div>
              {insight.insight.split('\n').filter(Boolean).map((p,i)=><p key={i}>{p}</p>)}
            </div>
          )}

          {chat.length === 0 && quickPrompts.length > 0 && (
            <div className="nar-prompts">
              {quickPrompts.map(p => (
                <button key={p} onClick={() => send(p)} disabled={!canAsk}>
                  {p}
                </button>
              ))}
            </div>
          )}

          {chat.length > 0 && (
            <div className="nar-chat">
              <div className="nar-chat-head">
                <span>Conversation with {cfg.name}</span>
                <button className="nar-chat-clear" onClick={()=>setSessions(prev=>({...prev,[provider]:{messages:[],isFirst:true}}))}>
                  Clear
                </button>
              </div>
              {chat.map((m,i)=>(
                <div key={i} className={`nar-msg ${m.role}${m.error?' error':''}`}>
                  {m.content}{m.streaming && <span className="nar-cursor">▋</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="nar-input-wrap">
          <input className="nar-input"
            placeholder={ready ? `Ask about ${filename}` : 'Ask factual questions, or configure a provider for deeper analysis'}
            value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();send(input)}}}
            disabled={chatting||!datasetId}
          />
          <button className="nar-send" onClick={()=>send(input)} disabled={!input.trim()||chatting||!datasetId}>Go</button>
        </div>
      </div>
    </>
  )
}
