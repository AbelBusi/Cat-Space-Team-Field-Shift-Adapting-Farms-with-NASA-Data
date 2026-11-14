<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { PAL } from '../lib/palette.js'

// Night sky of the landing scene: twinkling stars, a dusk glow over the horizon, and a satellite crossing
// on its orbit, sending signal rings down to the land. Always night, whatever the page theme.
const canvas = ref(null)
let raf
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const stars = Array.from({ length: 170 }, (_, i) => ({ x: (i * 7919 % 1000) / 1000, y: (i * 104729 % 1000) / 1000 * 0.72, r: i % 9 === 0 ? 1.6 : 0.9, p: i * 0.37 }))

function draw(t) {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d'), w = c.clientWidth, h = c.clientHeight, dpr = devicePixelRatio || 1
  if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr) }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const sky = ctx.createLinearGradient(0, 0, 0, h)   // the only gradient allowed by DESIGN.md: the sky
  sky.addColorStop(0, PAL.bg); sky.addColorStop(0.55, PAL.line); sky.addColorStop(0.85, PAL.deep); sky.addColorStop(1, PAL.deep)
  ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h)
  const glow = ctx.createRadialGradient(w * 0.5, h * 0.92, 0, w * 0.5, h * 0.92, w * 0.42)
  glow.addColorStop(0, 'rgba(242,165,65,.38)'); glow.addColorStop(1, 'rgba(242,165,65,0)')
  ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h)

  for (const s of stars) {
    ctx.globalAlpha = reduce ? 0.8 : 0.45 + 0.45 * Math.sin(t / 900 + s.p)
    ctx.fillStyle = PAL.ink
    ctx.fillRect(s.x * w, s.y * h, s.r, s.r)
  }
  ctx.globalAlpha = 1

  // Orbit: a wide dashed arc, and the satellite moving along it.
  const cx = w * 0.5, cy = h * 2.3, R = h * 2.05
  ctx.setLineDash([3, 9]); ctx.strokeStyle = 'rgba(140,155,196,.35)'; ctx.lineWidth = 1
  ctx.beginPath(); ctx.arc(cx, cy, R, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke(); ctx.setLineDash([])
  const a = reduce ? Math.PI * 1.62 : Math.PI * 1.15 + ((t / 16000) % 1) * Math.PI * 0.7
  const sx = cx + Math.cos(a) * R, sy = cy + Math.sin(a) * R
  for (let k = 0; k < 3; k++) {
    const ph = reduce ? k / 3 : ((t / 1700) + k / 3) % 1
    ctx.beginPath(); ctx.arc(sx, sy, 8 + ph * 46, a + Math.PI - 0.5, a + Math.PI + 0.5)
    ctx.strokeStyle = PAL.teal; ctx.globalAlpha = 0.55 * (1 - ph); ctx.lineWidth = 1.5; ctx.stroke()
  }
  ctx.globalAlpha = 1
  ctx.save(); ctx.translate(sx, sy); ctx.rotate(a + Math.PI / 2)
  ctx.fillStyle = PAL.ink; ctx.fillRect(-3, -3, 6, 6)
  ctx.fillStyle = PAL.teal; ctx.fillRect(-14, -2, 9, 4); ctx.fillRect(5, -2, 9, 4)
  ctx.restore()
}
let odd = false
function loop(t) { if ((odd = !odd)) draw(t); if (!reduce) raf = requestAnimationFrame(loop) }
const redraw = () => draw(performance.now())
onMounted(() => { redraw(); raf = requestAnimationFrame(loop); addEventListener('resize', redraw) })
onBeforeUnmount(() => { cancelAnimationFrame(raf); removeEventListener('resize', redraw) })
</script>

<template><canvas ref="canvas" class="block" aria-hidden="true" /></template>
