import React from 'react'
import './StepsTab.css'

function stepIcon(type) {
  if (type === 'cleaning') return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
  if (type === 'feature_engineering') return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
    </svg>
  )
  if (type === 'restore') return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.47"/>
    </svg>
  )
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  )
}

function typeLabel(type) {
  if (type === 'cleaning') return 'Cleaning'
  if (type === 'feature_engineering') return 'Feature Engineering'
  if (type === 'restore') return 'Restore'
  return type
}

function typeClass(type) {
  if (type === 'cleaning') return 'steps-badge--clean'
  if (type === 'feature_engineering') return 'steps-badge--feat'
  if (type === 'restore') return 'steps-badge--restore'
  return ''
}

function timeAgo(iso) {
  if (!iso) return ''
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function opLabel(id) {
  if (!id) return ''
  const [action, col] = id.split('::', 2)
  const a = action.replace(/_/g, ' ')
  return col ? `${a} → ${col}` : a
}

function entryTitle(entry) {
  if (entry.description) return entry.description
  if (entry.op) return entry.op.replace(/_/g, ' ')
  return 'Operation applied'
}

function entryMeta(entry) {
  const items = []
  if (entry.op) items.push(`op: ${entry.op}`)
  if (entry.columns?.length) items.push(`columns: ${entry.columns.join(', ')}`)
  if (entry.method) items.push(`method: ${entry.method}`)
  return items
}

export default function StepsTab({ data }) {
  const log = data?.operations_log || []
  const workflow = data?.workflow || {}
  const cleanIds = workflow.applied_cleaning_fix_ids || []
  const featIds = workflow.applied_feature_op_ids || []

  const hasActivity = log.length > 0 || cleanIds.length > 0 || featIds.length > 0

  if (!hasActivity) {
    return (
      <div className="steps-empty">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        <p>No operations applied yet.</p>
        <span>Use the Cleaning and Feature Engineering tabs to transform your data. Every action will be logged here and exported to your Jupyter notebook.</span>
      </div>
    )
  }

  return (
    <div className="steps-root">
      {log.length > 0 && (
        <section className="steps-section">
          <div className="steps-section-head">Operation History</div>
          <div className="steps-timeline">
            {log.map((entry, i) => (
              <div key={i} className="steps-entry">
                <div className={`steps-badge ${typeClass(entry.type)}`}>
                  {stepIcon(entry.type)}
                  {typeLabel(entry.type)}
                </div>
                <div className="steps-entry-body">
                  <div className="steps-entry-desc">{entryTitle(entry)}</div>
                  {entryMeta(entry).length > 0 && (
                    <ul className="steps-meta">
                      {entryMeta(entry).map(item => <li key={item}>{item}</li>)}
                    </ul>
                  )}
                  {(entry.fix_ids || entry.op_ids || []).length > 0 && (
                    <ul className="steps-ids">
                      {(entry.fix_ids || entry.op_ids || []).map(id => (
                        <li key={id}><code>{opLabel(id)}</code></li>
                      ))}
                    </ul>
                  )}
                  {entry.id && (
                    <ul className="steps-ids">
                      <li><code>{opLabel(entry.id)}</code></li>
                    </ul>
                  )}
                </div>
                <div className="steps-time">{timeAgo(entry.timestamp)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {(cleanIds.length > 0 || featIds.length > 0) && (
        <section className="steps-section">
          <div className="steps-section-head">Current Applied State</div>
          {cleanIds.length > 0 && (
            <div className="steps-state-group">
              <div className="steps-state-label">Cleaning operations ({cleanIds.length})</div>
              <ul className="steps-ids">
                {cleanIds.map(id => <li key={id}><code>{opLabel(id)}</code></li>)}
              </ul>
            </div>
          )}
          {featIds.length > 0 && (
            <div className="steps-state-group">
              <div className="steps-state-label">Feature engineering operations ({featIds.length})</div>
              <ul className="steps-ids">
                {featIds.map(id => <li key={id}><code>{opLabel(id)}</code></li>)}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="steps-notebook-hint">
        All operations above are reproduced as runnable Python cells in your <strong>Notebook export</strong>.
      </div>
    </div>
  )
}
