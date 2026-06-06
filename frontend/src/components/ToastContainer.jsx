import React, { useState, useEffect } from 'react'
import { TOAST_EVENT } from '../services/toast.js'
import './ToastContainer.css'

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    function handle(e) {
      const t = e.detail
      setToasts(prev => [...prev.slice(-4), t])
      setTimeout(() => setToasts(prev => prev.filter(x => x.id !== t.id)), 4200)
    }
    window.addEventListener(TOAST_EVENT, handle)
    return () => window.removeEventListener(TOAST_EVENT, handle)
  }, [])

  if (!toasts.length) return null
  return (
    <div className="toast-stack">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span className="toast-icon">
            {t.type === 'success' && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            )}
            {t.type === 'info' && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            )}
            {t.type === 'error' && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            )}
          </span>
          {t.message}
        </div>
      ))}
    </div>
  )
}
