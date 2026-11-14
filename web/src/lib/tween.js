import { ref, watch } from 'vue'

const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches
const mix = (a, b, t) => b == null || a == null ? b
  : typeof b === 'number' ? a + (b - a) * t
  : Array.isArray(b) ? b.map((v, i) => mix(a[i] ?? v, v, t))
  : Object.fromEntries(Object.keys(b).map(k => [k, mix(a[k] ?? b[k], b[k], t)]))

// Animates numbers, arrays of numbers or {key: number} objects toward the source's new value.
export function useTween(source, ms = 650) {
  const out = ref(source())
  let raf
  watch(source, to => {
    cancelAnimationFrame(raf)
    if (reduced() || document.hidden) { out.value = to; return }   // hidden tabs pause animation frames
    const from = out.value, t0 = performance.now()
    const step = t => {
      const k = Math.min(1, (t - t0) / ms)
      out.value = mix(from, to, 1 - (1 - k) ** 3)
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
  }, { deep: true })
  return out
}
