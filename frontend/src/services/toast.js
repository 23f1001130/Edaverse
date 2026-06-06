export const TOAST_EVENT = 'edaverse:toast'
export const TOUR_REPLAY_EVENT = 'edaverse:tour:replay'

export function fireToast(message, type = 'success') {
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, {
    detail: { message, type, id: `${Date.now()}-${Math.random()}` },
  }))
}

export function getSettings() {
  try { return JSON.parse(localStorage.getItem('edaverse_settings') || '{}') } catch { return {} }
}

export function saveSettings(patch) {
  try {
    const current = getSettings()
    const merged = deepMerge(current, patch)
    localStorage.setItem('edaverse_settings', JSON.stringify(merged))
    return merged
  } catch { return patch }
}

export function getSetting(path, fallback) {
  const s = getSettings()
  const keys = path.split('.')
  let cur = s
  for (const k of keys) {
    if (cur == null || typeof cur !== 'object') return fallback
    cur = cur[k]
  }
  return cur !== undefined ? cur : fallback
}

function deepMerge(target, source) {
  const out = { ...target }
  for (const k of Object.keys(source)) {
    if (source[k] && typeof source[k] === 'object' && !Array.isArray(source[k])) {
      out[k] = deepMerge(target[k] || {}, source[k])
    } else {
      out[k] = source[k]
    }
  }
  return out
}
