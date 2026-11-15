// Sprout's voice in the browser (Web Speech API): high and soft, like a kitten, in Spanish or English.
// Used when the server sends no audio (TTS_ENGINE=browser, the default): nothing to download, works offline on most systems.
let voices = []
const load = () => { voices = window.speechSynthesis?.getVoices() ?? [] }
if (window.speechSynthesis) { load(); window.speechSynthesis.onvoiceschanged = load }

// Prefer a light, young-sounding voice of the language (female or child voices sound closer to a small cat).
const GENTLE = /(child|kid|girl|female|woman|helena|laura|paulina|monica|sabina|lucia|elvira|dalia|google español|samantha|zira|aria|jenny|ana|amy|kristin|google us english)/i
function pick(lang) {
  const all = voices.filter(v => v.lang?.toLowerCase().startsWith(lang))
  return all.find(v => GENTLE.test(v.name)) || all.find(v => v.localService) || all[0] || null
}

export const canSpeak = () => !!window.speechSynthesis

// Says the text; resolves when it ends. Returns a handle with stop().
export function speak(text, { lang = 'es', onStart, onEnd } = {}) {
  let ended = false
  const end = () => { if (!ended) { ended = true; onEnd?.() } }
  if (!canSpeak() || !text) { end(); return { stop: end } }
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  const v = pick(lang)
  if (v) u.voice = v
  u.lang = v?.lang || (lang === 'en' ? 'en-US' : 'es-ES')
  u.pitch = 1.75          // high: a small cat (the API allows 0-2)
  u.rate = 1.04
  u.volume = 0.95
  u.onstart = () => onStart?.()
  u.onend = end
  u.onerror = end
  window.speechSynthesis.speak(u)
  return { stop() { window.speechSynthesis.cancel(); end() } }
}

// Sprout's own voice: Piper on the ML API (POST /assistant/speak, a soft voice pitched up like a kitten, in Spanish or
// English). If the server has no voice (204) or cannot be reached, the browser's voice says it instead.
import { ML_API } from '../lib/mlApi.js'
let serverVoice = true          // turns false after a failure, so Sprout does not wait on a dead server for every line

export function voiceLine(text, { lang = 'es', onStart, onEnd } = {}) {
  let ended = false, audio = null, browser = null
  const ctrl = new AbortController()
  const end = () => { if (!ended) { ended = true; onEnd?.() } }
  const handle = { stop() { ctrl.abort(); audio?.pause(); browser?.stop(); end() } }
  const fallback = () => { if (!ended && !ctrl.signal.aborted) browser = speak(text, { lang, onStart, onEnd: end }) }
  if (!text) { end(); return handle }
  if (!serverVoice || !ML_API) { fallback(); return handle }
  fetch(`${ML_API}/assistant/speak`, { method: 'POST', signal: ctrl.signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text.slice(0, 600), lang: lang === 'en' ? 'en' : 'es' }) })
    .then(async r => {
      if (r.status === 204) return fallback()
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const url = URL.createObjectURL(await r.blob())
      if (ctrl.signal.aborted) return URL.revokeObjectURL(url)
      audio = new Audio(url)
      audio.onplay = () => onStart?.()
      audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); end() }
      await audio.play().catch(() => { URL.revokeObjectURL(url); end() })   // autoplay blocked until the first tap
    })
    .catch(e => { if (e.name !== 'AbortError') { serverVoice = false; fallback() } })
  return handle
}
