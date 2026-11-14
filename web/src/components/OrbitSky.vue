<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

// A satellite crossing a planet's horizon, sending signal rings down and scanning a strip of ground.
const canvas = ref(null)
let raf
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches

function draw(t) {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d'), w = c.clientWidth, h = c.clientHeight, dpr = devicePixelRatio || 1
  if (c.width !== Math.round(w * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr) }
  const css = getComputedStyle(document.documentElement), v = n => css.getPropertyValue(n).trim()
  const accent = v('--accent'), line = v('--line')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  const cx = w * 0.98, cy = h + w * 0.62, R = w * 0.7, orbit = R + 70
  ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2)
  ctx.globalAlpha = 0.9; ctx.fillStyle = v('--surface-2'); ctx.fill(); ctx.globalAlpha = 1
  ctx.lineWidth = 1.5; ctx.strokeStyle = line; ctx.stroke()
  ctx.setLineDash([4, 8]); ctx.beginPath(); ctx.arc(cx, cy, orbit, Math.PI * 1.08, Math.PI * 1.92); ctx.stroke(); ctx.setLineDash([])

  const a = reduce ? Math.PI * 1.62 : Math.PI * 1.08 + ((t / 9000) % 1) * Math.PI * 0.84
  const sx = cx + Math.cos(a) * orbit, sy = cy + Math.sin(a) * orbit

  // Ground footprint: the strip of land the satellite is "listening to" right now.
  ctx.beginPath(); ctx.arc(cx, cy, R, a - 0.035, a + 0.035)
  ctx.lineWidth = 6; ctx.strokeStyle = accent; ctx.globalAlpha = 0.55; ctx.stroke()
  ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(cx + Math.cos(a - 0.035) * R, cy + Math.sin(a - 0.035) * R)
  ctx.lineTo(cx + Math.cos(a + 0.035) * R, cy + Math.sin(a + 0.035) * R); ctx.closePath()
  ctx.fillStyle = accent; ctx.globalAlpha = 0.07; ctx.fill(); ctx.globalAlpha = 1

  for (let k = 0; k < 3; k++) {
    const ph = reduce ? k / 3 : ((t / 1600) + k / 3) % 1
    ctx.beginPath(); ctx.arc(sx, sy, 10 + ph * 60, a + Math.PI - 0.6, a + Math.PI + 0.6)
    ctx.strokeStyle = accent; ctx.globalAlpha = 0.6 * (1 - ph); ctx.lineWidth = 2; ctx.stroke()
  }
  ctx.globalAlpha = 1
  ctx.save(); ctx.translate(sx, sy); ctx.rotate(a + Math.PI / 2)
  ctx.fillStyle = accent; ctx.fillRect(-4, -4, 8, 8)
  ctx.fillStyle = v('--info-ink'); ctx.fillRect(-18, -2.5, 12, 5); ctx.fillRect(6, -2.5, 12, 5)
  ctx.restore()
}
function loop(t) { draw(t); if (!reduce) raf = requestAnimationFrame(loop) }
const redraw = () => draw(performance.now())
onMounted(() => { raf = requestAnimationFrame(loop); addEventListener('resize', redraw) })
onBeforeUnmount(() => { cancelAnimationFrame(raf); removeEventListener('resize', redraw) })
</script>

<template><canvas ref="canvas" class="sky" aria-hidden="true" /></template>
