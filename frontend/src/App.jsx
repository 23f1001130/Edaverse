import React, { useState } from 'react'
import Landing from './pages/Landing.jsx'
import Workspace from './pages/Workspace.jsx'

export default function App() {
  const [view, setView] = useState('landing')
  const [startDemo, setStartDemo] = useState(false)

  if (view === 'landing') {
    return <Landing
      onGetStarted={() => { setStartDemo(false); setView('workspace') }}
      onDemo={() => { setStartDemo(true); setView('workspace') }}
    />
  }
  return <Workspace onHome={() => setView('landing')} autoDemo={startDemo} />
}
