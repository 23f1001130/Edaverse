import React, { useState, useEffect, useCallback } from 'react'
import { TOUR_REPLAY_EVENT } from '../services/toast.js'
import './WorkspaceTour.css'

const PAD = 8
const TW = 296
const TH = 180

const STEPS = [
  {
    selector: '[data-tour="colbar"]',
    title: 'Column explorer',
    body: 'Every column is listed here with a null-% bar. Click any row to jump straight to its distribution profile.',
    position: 'right',
  },
  {
    selector: '[data-tour="tabs"]',
    title: 'Analysis tabs',
    body: 'Seven views of your data: Overview, Distributions, Correlations, Target Analysis, Cleaning, Feature Engineering, and Steps Applied.',
    position: 'bottom',
  },
  {
    selector: '[data-tour="eda-badge"]',
    title: 'Progress tracker',
    body: 'Tracks how many of 7 analysis milestones you\'ve completed. Hover it anytime to see what\'s left.',
    position: 'bottom',
  },
  {
    selector: '[data-tour="ai-btn"]',
    title: 'AI Narrative',
    body: 'Generate a plain-English summary of your dataset — patterns, anomalies, and key relationships — powered by AI.',
    position: 'bottom',
  },
  {
    selector: '[data-tour="actions"]',
    title: 'Export & reports',
    body: 'Download a cleaned CSV, generate a full HTML EDA report, or open your workflow as a Jupyter notebook in Colab.',
    position: 'bottom',
  },
  {
    selector: '[data-tour="tab-cleaning-report"]',
    title: 'Smart cleaning',
    body: 'Edaverse detects data quality issues — nulls, outliers, duplicates — and suggests one-click fixes. Visit here after EDA.',
    position: 'bottom',
  },
  {
    selector: '[data-tour="tab-feature-engineering"]',
    title: 'Feature engineering',
    body: 'Add new columns with scaling, encoding, binning, date extraction, and more. One click applies the transformation.',
    position: 'bottom',
  },
]

function spotlight(selector) {
  const el = document.querySelector(selector)
  if (!el) return null
  const r = el.getBoundingClientRect()
  return { x: r.left - PAD, y: r.top - PAD, w: r.width + PAD * 2, h: r.height + PAD * 2 }
}

function tooltipPos(s, position) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const gap = 16
  const cx = s.x + s.w / 2
  const cy = s.y + s.h / 2

  if (position === 'right') {
    let left = s.x + s.w + gap
    if (left + TW > vw - gap) left = s.x - TW - gap
    const top = Math.max(gap, Math.min(cy - TH / 2, vh - TH - gap))
    return { left, top, arrow: left > s.x ? 'left' : 'right' }
  }
  // bottom
  let left = Math.max(gap, Math.min(cx - TW / 2, vw - TW - gap))
  let top = s.y + s.h + gap
  if (top + TH > vh - gap) top = s.y - TH - gap
  return { left, top, arrow: top > s.y ? 'top' : 'bottom' }
}

export default function WorkspaceTour({ onDone }) {
  const [idx, setIdx] = useState(() => {
    // Start at the first step whose element actually exists
    for (let i = 0; i < STEPS.length; i++) {
      if (document.querySelector(STEPS[i].selector)) return i
    }
    return 0
  })
  const [spot, setSpot] = useState(null)
  const [tip, setTip] = useState(null)

  const step = STEPS[idx]

  const reposition = useCallback(() => {
    const s = spotlight(step.selector)
    if (!s) return
    setSpot(s)
    setTip(tooltipPos(s, step.position))
  }, [idx])

  useEffect(() => {
    reposition()
    const id = requestAnimationFrame(reposition)
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    return () => {
      cancelAnimationFrame(id)
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
    }
  }, [reposition])

  function advance(dir) {
    let next = idx + dir
    while (next >= 0 && next < STEPS.length && !document.querySelector(STEPS[next].selector)) {
      next += dir
    }
    if (next < 0 || next >= STEPS.length) finish()
    else setIdx(next)
  }

  function finish() {
    try { localStorage.setItem('edaverse_workspace_tour_seen', '1') } catch {}
    onDone()
  }

  if (!spot || !tip) return null

  const vw = window.innerWidth
  const vh = window.innerHeight
  const isLast = idx === STEPS.length - 1 || !STEPS.slice(idx + 1).some(s => document.querySelector(s.selector))

  return (
    <>
      <svg className="wt-overlay" width={vw} height={vh} onClick={finish}>
        <defs>
          <mask id="wt-mask">
            <rect width="100%" height="100%" fill="white"/>
            <rect x={spot.x} y={spot.y} width={spot.w} height={spot.h} rx="8" fill="black"/>
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(5,8,18,0.8)" mask="url(#wt-mask)"/>
      </svg>

      <div className="wt-ring" style={{ left: spot.x, top: spot.y, width: spot.w, height: spot.h }}/>

      <div
        className={`wt-popover wt-arrow-${tip.arrow}`}
        style={{ left: tip.left, top: tip.top }}
        onClick={e => e.stopPropagation()}
      >
        <div className="wt-counter">{idx + 1} / {STEPS.length}</div>
        <div className="wt-title">{step.title}</div>
        <p className="wt-body">{step.body}</p>
        <div className="wt-foot">
          <button className="wt-skip" onClick={finish}>Skip tour</button>
          <div style={{ display: 'flex', gap: 8 }}>
            {idx > 0 && <button className="wt-btn wt-back" onClick={() => advance(-1)}>Back</button>}
            <button className="wt-btn wt-next" onClick={() => advance(1)}>
              {isLast ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
