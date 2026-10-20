import React, { useEffect, useRef, useState } from 'react'
import { previewSamples } from './previewSamples.js'
import './ProductPreview.css'

export default function ProductPreview({ onDemo }) {
  const [sampleIndex, setSampleIndex] = useState(0)
  const [columnIndex, setColumnIndex] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  const [visible, setVisible] = useState(true)
  const [inView, setInView] = useState(true)
  const [reportOpen, setReportOpen] = useState(false)
  const region = useRef(null)
  const sample = previewSamples[sampleIndex]
  const column = sample.columns[columnIndex]
  const maximum = Math.max(...column.values)

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const respectMotion = () => { if (media?.matches) setPlaying(false) }
    respectMotion()
    media?.addEventListener?.('change', respectMotion)
    const onVisibility = () => setVisible(!document.hidden)
    onVisibility()
    document.addEventListener('visibilitychange', onVisibility)
    const observer = typeof IntersectionObserver !== 'undefined'
      ? new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.2 }) : null
    if (region.current) observer?.observe(region.current)
    return () => {
      media?.removeEventListener?.('change', respectMotion)
      document.removeEventListener('visibilitychange', onVisibility)
      observer?.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!playing || hovered || focused || !visible || !inView) return
    const timer = window.setInterval(() => {
      setSampleIndex(index => (index + 1) % previewSamples.length)
      setColumnIndex(0)
    }, 8000)
    return () => window.clearInterval(timer)
  }, [playing, hovered, focused, visible, inView])

  function chooseSample(index) {
    setSampleIndex(index); setColumnIndex(0); setPlaying(false); setReportOpen(false)
  }

  return <div className="hero-product interactive-preview" role="region" aria-label="Interactive sample analysis" ref={region}
    onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
    onFocusCapture={() => setFocused(true)}
    onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false) }}>
    <div className="product-shell">
      <aside className="product-sidebar" aria-hidden="true"><span className="product-dot" /><span /><span /><span /></aside>
      <div className="product-main">
        <div className="preview-caption"><span className="preview-indicator" aria-hidden="true" />Interactive sample · illustrative data</div>
        <div className="product-top">
          <div><span className="product-kicker">{sample.filename}</span><strong>Exploratory analysis</strong></div>
          <button type="button" aria-expanded={reportOpen} aria-controls="sample-analysis-report"
            onClick={() => { setReportOpen(open => !open); setPlaying(false) }}>Report</button>
        </div>
        <div className="preview-datasets" role="group" aria-label="Sample datasets">
          {previewSamples.map((item, index) => <button key={item.filename} type="button" aria-pressed={sampleIndex === index}
            aria-label={`Show ${item.name} sample`} onClick={() => chooseSample(index)}>{item.shortName}</button>)}
        </div>
        <div className="product-metrics">
          {[['Rows profiled', sample.rows], ['Quality score', sample.quality], ['Missing cells', sample.missing], ['Feature ideas', sample.ideas]].map(([label, value]) =>
            <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </div>
        <div className="product-grid">
          <div className="product-panel product-columns">
            <div className="product-panel-title">Column health</div>
            <span className="preview-instruction">Select a column to explore</span>
            {sample.columns.map((item, index) => <button className="product-column" key={item.name} type="button"
              aria-label={`Explore ${item.name}`} aria-pressed={columnIndex === index}
              title={`${item.name}: ${item.health}% complete`}
              onClick={() => { setColumnIndex(index); setPlaying(false) }}>
              <div><span>{item.name}</span><em>{item.type}</em></div>
              <div className="product-track"><i style={{ width: `${item.health}%` }} /></div>
            </button>)}
          </div>
          <div className="product-panel product-chart">
            <div className="product-panel-title">{column.type === 'CAT' ? 'Category counts' : 'Distribution'}</div>
            <div className="preview-column-name">{column.name}</div>
            <div className="product-bars" role="img" aria-label={`${column.name} ${column.type === 'CAT' ? 'category counts' : 'distribution'} in ${sample.filename}`}>
              {column.values.map((value, index) => <span key={index} style={{ height: `${Math.max(4, value / maximum * 100)}%` }}
                title={`${column.bins[index]}: ${value.toLocaleString('en-US')} rows`} />)}
            </div>
            <div className="preview-axis"><span>{column.bins[0]}</span><span>{column.bins.at(-1)}</span></div>
            <div className="product-note">{column.note}</div>
          </div>
        </div>
        {reportOpen && <section className="preview-report" id="sample-analysis-report" aria-label="Sample analysis report">
          <h3>{sample.name}: sample report</h3>
          <p>{sample.rows} rows · quality score {sample.quality} · {sample.missing} missing cells</p>
          <ul>{sample.priorities.map(priority => <li key={priority}>{priority}</li>)}</ul>
          <p>Illustrative sample. Open the full demo to explore a working dataset.</p>
          <a href="/?demo=1" onClick={event => { if (onDemo) { event.preventDefault(); onDemo() } }}>Open full demo →</a>
        </section>}
        <div className="preview-footer">
          <span>{playing ? hovered || focused ? 'Paused while you explore' : 'Samples change every 8 seconds' : 'Sample tour paused'}</span>
          <button type="button" onClick={() => setPlaying(value => !value)} aria-label={playing ? 'Pause sample tour' : 'Resume sample tour'}>{playing ? 'Pause' : 'Resume'}</button>
        </div>
      </div>
    </div>
  </div>
}
