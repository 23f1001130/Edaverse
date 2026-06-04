import React, { useEffect, useState } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { fetchDatasets, deleteDataset } from '../services/api.js'
import './HistoryPanel.css'

function timeAgo(iso) {
  const m = Math.floor((Date.now()-new Date(iso).getTime())/60000)
  if (m<1) return 'just now'; if (m<60) return `${m}m ago`
  const h=Math.floor(m/60); if (h<24) return `${h}h ago`
  return `${Math.floor(h/24)}d ago`
}

export default function HistoryPanel({ onSelect }) {
  const { isSignedIn } = useAuth()
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)
  const [delId, setDelId] = useState(null)

  useEffect(() => {
    fetchDatasets().then(setDatasets).finally(() => setLoading(false))
  }, [])

  async function del(e, id) {
    e.stopPropagation(); setDelId(id)
    try { await deleteDataset(id); setDatasets(d => d.filter(x => x.id !== id)) }
    finally { setDelId(null) }
  }

  return (
    <div className="ws-panel">
      <div className="ws-topbar">
        <div className="ws-breadcrumb">
          <span className="ws-bc-workspace">My Workspace</span>
          <span className="ws-bc-sep">/</span>
          <span className="ws-bc-current">History</span>
        </div>
      </div>



      <div className="hist">
        {loading
          ? <div className="tab-empty">Loading…</div>
          : !datasets.length
            ? <div className="tab-empty">No datasets yet — upload a file to get started.</div>
            : datasets.map(ds => (
              <div key={ds.id} className="hist-item" onClick={() => onSelect(ds.id)}>
                <div className="hist-icon">▦</div>
                <div className="hist-info">
                  <div className="hist-name">{ds.filename}</div>
                  <div className="hist-meta">
                    {ds.shape?.rows?.toLocaleString()} rows · {ds.shape?.columns} cols · {timeAgo(ds.saved_at)}
                  </div>
                </div>
                <button className="hist-del" onClick={(e) => del(e, ds.id)} disabled={delId === ds.id}>×</button>
              </div>
            ))
        }
      </div>
    </div>
  )
}