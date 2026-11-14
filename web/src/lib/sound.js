// Tiny WebAudio sounds: Sprout's meows, its talking blips and the "listen to your field" melody.
// Everything is synthesized here, with no audio files, so it is original and needs no license.
let ctx = null

// Browsers only allow audio after a click or key press, so call this from event handlers.
export function unlock() {
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)()
    if (ctx.state === 'suspended') ctx.resume()
  } catch { ctx = null }
}

function tone(freq, start, length, gain, type) {
  const o = ctx.createOscillator(), g = ctx.createGain()
  o.type = type; o.frequency.value = freq
  g.gain.setValueAtTime(0.0001, start)
  g.gain.exponentialRampToValueAtTime(gain, start + 0.01)
  g.gain.exponentialRampToValueAtTime(0.0001, start + length)
  o.connect(g).connect(ctx.destination)
  o.start(start); o.stop(start + length + 0.02)
}

// One synthesized "mew": the pitch rises then falls while a filter sweeps like a mouth opening and closing.
// base = pitch in Hz, up / end = pitch multipliers at the peak and at the end, len = seconds, gain = 0..1.
function mew(start, { base, up, end, len, gain = 1 }) {
  const o = ctx.createOscillator(), f = ctx.createBiquadFilter(), g = ctx.createGain()
  o.type = 'sawtooth'
  o.frequency.setValueAtTime(base, start)
  o.frequency.exponentialRampToValueAtTime(base * up, start + len * 0.35)
  o.frequency.exponentialRampToValueAtTime(base * end, start + len)
  f.type = 'bandpass'; f.Q.value = 3
  f.frequency.setValueAtTime(800, start)
  f.frequency.linearRampToValueAtTime(2000, start + len * 0.4)
  f.frequency.linearRampToValueAtTime(900, start + len)
  g.gain.setValueAtTime(0.0001, start)
  g.gain.exponentialRampToValueAtTime(0.22 * gain, start + 0.015)
  g.gain.exponentialRampToValueAtTime(0.0001, start + len)
  o.connect(f).connect(g).connect(ctx.destination)
  o.start(start); o.stop(start + len + 0.02)
}

// A short meow per mood. `at` delays a second sound. Tune these numbers by ear.
const MEOW = {
  neutral: [{ base: 640, up: 1.3, end: 0.85, len: 0.22 }],
  happy: [{ base: 720, up: 1.45, end: 0.95, len: 0.26 }],
  surprised: [{ base: 560, up: 1.9, end: 1.7, len: 0.16 }],
  sad: [{ base: 660, up: 1.05, end: 0.55, len: 0.42 }],
  worried: [{ base: 640, up: 1.2, end: 0.8, len: 0.12 }, { base: 600, up: 1.15, end: 0.75, len: 0.16, at: 0.15 }],
  thinking: [{ base: 420, up: 1.1, end: 0.9, len: 0.3, gain: 0.8 }],
  shy: [{ base: 900, up: 1.2, end: 0.9, len: 0.14, gain: 0.5 }],
}
export const meowLength = mood => Math.max(...(MEOW[mood] || MEOW.neutral).map(m => (m.at || 0) + m.len))

export function meow(mood = 'neutral') {
  if (ctx?.state !== 'running') return
  const t = ctx.currentTime
  for (const m of MEOW[mood] || MEOW.neutral) mew(t + (m.at || 0), m)
}

// Talking voice: a tiny mew every couple of letters, like an RPG text box.
export function blip(pitch = 1) {
  if (ctx?.state === 'running') mew(ctx.currentTime, { base: 620 * pitch * (0.96 + Math.random() * 0.08), up: 1.25, end: 0.9, len: 0.055, gain: 0.45 })
}

// values in 0..1 → one note per month, low = less, high = more.
export function melody(values, step = 0.32) {
  unlock()
  if (!ctx) return
  const t0 = ctx.currentTime + 0.05
  values.forEach((v, i) => tone(220 * 2 ** (v * 2), t0 + i * step, step * 0.95, 0.16, 'triangle'))
}
