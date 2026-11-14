<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LANDMASK } from '../lib/landmask.js'
import { PAL } from '../lib/palette.js'

// A small pixel-art Earth that spins slowly, turns to the chosen place and marks it with a campfire pixel.
// Land comes from NASA GRACE's land mask. A little moon orbits it, like the reference art.
const props = defineProps({ lat: Number, lon: Number, size: { type: Number, default: 112 } })
const RES = 56                       // canvas pixels; scaled up with image-rendering: pixelated
const R = RES * 0.36, C = RES / 2
const canvas = ref(null)
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16))
const COL = { ocean: rgb(PAL.deep), sage: rgb(PAL.sage), sand: rgb(PAL.sand), ice: rgb(PAL.ink), night: rgb(PAL.bg), glow: rgb(PAL.teal), moon: rgb(PAL.muted), fire: rgb(PAL.fire) }
const LIGHT = (() => { const v = [-0.55, 0.45, 0.7], n = Math.hypot(...v); return v.map(x => x / n) })()
const d2r = Math.PI / 180

let lon0 = props.lon ?? -60, raf

function landColor(lat) {
  const a = Math.abs(lat)
  return a > 62 ? COL.ice : a > 14 && a < 34 ? COL.sand : COL.sage
}
function draw(t) {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d'), img = ctx.createImageData(RES, RES), px = img.data
  if (props.lon == null) lon0 += reduce ? 0 : 0.2                              // idle spin
  else lon0 += (((props.lon - lon0 + 540) % 360) - 180) * 0.06                 // turn to the chosen place
  const phi0 = Math.max(-30, Math.min(30, (props.lat ?? 10) * 0.7)) * d2r
  const sp = Math.sin(phi0), cp = Math.cos(phi0)
  const moonA = reduce ? 2.3 : t / 2600, mx = C + Math.cos(moonA) * RES * 0.46, my = C + Math.sin(moonA) * RES * 0.16
  const moonBehind = Math.sin(moonA) < 0
  const put = (x, y, col, a = 255) => { const i = (y * RES + x) * 4; px[i] = col[0]; px[i + 1] = col[1]; px[i + 2] = col[2]; px[i + 3] = a }
  const moon = () => { for (let y = -2; y <= 2; y++) for (let x = -2; x <= 2; x++) if (x * x + y * y <= 5) put(Math.round(mx + x), Math.round(my + y), x + y > 1 ? COL.night : COL.moon) }
  if (moonBehind) moon()
  for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
    const X = (x + 0.5 - C) / R, Y = -(y + 0.5 - C) / R, rho2 = X * X + Y * Y
    if (rho2 > 1) { if (rho2 < 1.18 && rho2 > 1.0) put(x, y, COL.glow, 110); continue }
    const z = Math.sqrt(1 - rho2)
    const lat = Math.asin(z * sp + Y * cp) / d2r
    const lon = lon0 + Math.atan2(X, z * cp - Y * sp) / d2r
    const col = Math.floor(((((lon + 180) % 360) + 360) % 360) / 3), row = Math.min(59, Math.floor((90 - lat) / 3))
    let rgbv = LANDMASK[row][col] === '#' ? landColor(lat) : COL.ocean
    const lit = X * LIGHT[0] + Y * LIGHT[1] + z * LIGHT[2]
    if (lit < 0.05) rgbv = rgbv.map((v, i) => Math.round(v * 0.35 + COL.night[i] * 0.65))   // night side
    put(x, y, rgbv)
  }
  if (!moonBehind) moon()
  if (props.lat != null) {   // the chosen place, if it faces us
    const la = props.lat * d2r, dl = (props.lon - lon0) * d2r
    const cosc = sp * Math.sin(la) + cp * Math.cos(la) * Math.cos(dl)
    if (cosc > 0 && (reduce || Math.floor(t / 450) % 2 === 0)) {
      const sx = Math.round(C + R * Math.cos(la) * Math.sin(dl)), sy = Math.round(C - R * (cp * Math.sin(la) - sp * Math.cos(la) * Math.cos(dl)))
      for (const [dx, dy] of [[0, 0], [1, 0], [0, 1], [1, 1]]) put(sx + dx - 1, sy + dy - 1, COL.fire)
    }
  }
  ctx.putImageData(img, 0, 0)
}
function loop(t) { draw(t); if (!reduce) raf = requestAnimationFrame(loop) }
onMounted(() => { raf = requestAnimationFrame(loop) })
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <canvas ref="canvas" class="pixel-globe" :width="RES" :height="RES" :style="{ width: size + 'px', height: size + 'px' }"
          role="img" :aria-label="lat != null ? t('Pixel globe turned to {pos}', { pos: `${lat.toFixed(1)}, ${lon.toFixed(1)}` }) : t('Pixel globe')" />
</template>
