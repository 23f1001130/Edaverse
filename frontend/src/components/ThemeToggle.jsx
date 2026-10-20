import React, { useEffect, useState } from 'react'
import './ThemeToggle.css'

function readTheme() {
  try { return localStorage.getItem('edaverse_theme') === 'light' ? 'light' : 'dark' }
  catch { return 'dark' }
}

export default function ThemeToggle() {
  // Match the prerendered button during hydration; the head script has already
  // applied the saved page colours before this component mounts.
  const [theme, setTheme] = useState('dark')

  useEffect(() => {
    function sync() {
      const saved = readTheme()
      setTheme(saved)
      document.documentElement.dataset.theme = saved
    }
    function onStorage(event) {
      if (event.key === 'edaverse_theme' || event.key === null) sync()
    }
    sync()
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('edaverse_theme', next) } catch {}
  }

  const label = `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`
  return <button className="theme-toggle" type="button" onClick={toggle} title={label} aria-label={label}>
    {theme === 'dark' ? (
      <svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5" />
        <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    ) : (
      <svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    )}
    <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
  </button>
}
