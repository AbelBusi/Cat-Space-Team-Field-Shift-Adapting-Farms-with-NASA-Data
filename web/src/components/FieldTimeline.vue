<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import PixelIcon from './PixelIcon.vue'
import { state } from '../store.js'
import { getTimeline, ML_API } from '../lib/mlApi.js'
import { MONTHS, M1 } from '../content.js'
import { PAL } from '../lib/palette.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'

// The field's log, drawn like the ship log of a space camp: a dark grid, the deep soil water of the 2 km square at the
// field's centre every month since 1998, the big events as log entries joined by arrows, and the coming year (2026)
// as the one entry still marked "?". It opens pointing at 2026. Dragging it (or playing it) fills the soil layers of the
// 3D block with that month's water, and in the projection it moves the month shown on the map (state.ahead.month).
// Observed (ERA5-Land), projected and missing values are drawn apart and named; nothing is filled in.
const props = defineProps({ box: { type: Object, required: true } })
const emit = defineEmits(['layers', 'size'])
const root = ref(null), plot = ref(null)
const data = ref(null), error = ref(null), at = ref(0), playing = ref(false), width = ref(600), born = ref(0)
let timer = 0, ctrl = null, ro = null
const phone = () => innerWidth < 1024

const center = computed(() => {
  const r = state.parcel?.ring || []
  return r.length ? { lat: r.reduce((s, p) => s + p[0], 0) / r.length, lon: r.reduce((s, p) => s + p[1], 0) / r.length } : null
})
const nPast = computed(() => data.value?.months.length ?? 0)
const fut = computed(() => data.value?.future?.soil_water ?? null)
const nFut = computed(() => fut.value?.periods.length ?? 0)
const nAll = computed(() => nPast.value + nFut.value)
const isFuture = computed(() => at.value >= nPast.value)
const k = computed(() => at.value - nPast.value)                 // month of the projection (0 = the first)
const label = computed(() => isFuture.value ? fut.value.periods[k.value] : data.value.months[at.value])
const year = computed(() => +label.value.slice(0, 4))
const month = computed(() => +label.value.slice(5, 7))
const ninoYears = computed(() => data.value?.el_nino_years ?? [])

async function load() {
  if (!center.value || !ML_API) return
  ctrl?.abort(); ctrl = new AbortController()
  error.value = null; data.value = null
  try {
    data.value = await getTimeline(center.value, ctrl.signal)
    at.value = fut.value ? nPast.value + Math.min(state.ahead.month, nFut.value - 1) : nPast.value - 1   // open on 2026
    born.value++
    say(() => t('This is your field\'s log. Each month since 1998 is on the line, and the big El Niño years are marked. At the end, the "?" is the coming year: drag the bar to see what my model expects, and watch the soil of the block fill or dry.'), 'happy', [], { level: 'note' })
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message }
}

// ---- the deep layer this month, in words (thresholds: 0.01 = the app's "about usual", 0.04 ≈ 3 times the model error)
const deep = computed(() => data.value?.layers.find(l => l.key === 'sm_root_m3m3'))
const valueAt = i => i < nPast.value ? deep.value.observed[i] : fut.value.median[i - nPast.value]
const usualAt = i => i < nPast.value ? deep.value.usual_by_month[+data.value.months[i].slice(5, 7) - 1] : fut.value.usual[i - nPast.value]
function wordOf(v, u) {
  if (v == null || u == null) return null
  const d = v - u
  return Math.abs(d) < 0.01 ? 'same' : d > 0.04 ? 'muchWetter' : d > 0 ? 'wetter' : d < -0.04 ? 'muchDrier' : 'drier'
}
const SENT = {
  muchWetter: 'Much wetter than usual for this month', wetter: 'A little wetter than usual for this month', same: 'About usual for this month',
  drier: 'A little drier than usual for this month', muchDrier: 'Much drier than usual for this month',
}
const SHORT = { muchWetter: 'much wetter', wetter: 'wetter', same: 'usual', drier: 'drier', muchDrier: 'much drier' }
const ICON = { muchWetter: 'soil_wet', wetter: 'soil_wet', same: 'soil_moist', drier: 'soil_dry', muchDrier: 'soil_dry' }
const word = computed(() => data.value && wordOf(valueAt(at.value), usualAt(at.value)))

// Each layer this month: how full it is for this place (5-95 % of its own record) for the block, and its word.
const layers = computed(() => {
  if (!data.value) return []
  return data.value.layers.map((l, n) => {
    let v = null, u = l.usual_by_month[month.value - 1]
    if (!isFuture.value) v = l.observed[at.value]
    else if (l.key === 'sm_root_m3m3') { v = fut.value.median[k.value]; u = fut.value.usual[k.value] }
    const fill = v == null || l.p05 == null ? null : Math.max(0, Math.min(1, (v - l.p05) / Math.max(1e-6, l.p95 - l.p05)))
    return { ...l, n, v, fill, w: wordOf(v, u) }
  })
})
watch(layers, ls => emit('layers', ls.map(l => l.fill)), { immediate: true })
const NAME = ['Surface', 'Middle', 'Deep']

// ---- the log screen. The past 1998-2025 takes 64 % of the width and the coming year the rest, so 2026 reads clearly.
const H = computed(() => phone() ? 96 : 124)
const TOP = computed(() => phone() ? 0 : 48)                     // band of the log entries above the line
const geo = computed(() => {
  if (!data.value) return null
  const Wd = width.value, split = Wd * (fut.value ? 0.64 : 1), pad = 6
  const x = i => i < nPast.value ? pad + i / (nPast.value - 1) * (split - 24 - pad) : split + 18 + (i - nPast.value + 0.5) / nFut.value * (Wd - split - 24)
  const vals = [...deep.value.observed, ...(fut.value ? [...fut.value.low_90, ...fut.value.high_90] : [])].filter(v => v != null)
  const lo = Math.min(...vals), hi = Math.max(...vals), y0 = TOP.value + 10, y1 = H.value - 16
  const y = v => y1 - (v - lo) / Math.max(1e-6, hi - lo) * (y1 - y0)
  const line = idx => idx.map(i => [i, valueAt(i)]).filter(([, v]) => v != null).map(([i, v], n) => `${n ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')
  const past = line([...Array(nPast.value).keys()])
  const area = `${past}L${x(nPast.value - 1).toFixed(1)},${y1}L${x(0).toFixed(1)},${y1}Z`
  const fi = [...Array(nFut.value).keys()].map(j => nPast.value + j)
  const future = fut.value ? line([nPast.value - 1, ...fi]) : ''
  const band = fut.value ? [...fi.map(i => `${x(i).toFixed(1)},${y(fut.value.high_90[i - nPast.value]).toFixed(1)}`),
    ...fi.slice().reverse().map(i => `${x(i).toFixed(1)},${y(fut.value.low_90[i - nPast.value]).toFixed(1)}`)].join(' ') : ''
  const every = phone() ? 10 : 5, first = phone() ? 2000 : 1998
  const years = data.value.months.map((m, i) => ({ m, i })).filter(d => d.m.endsWith('-01') && +d.m.slice(0, 4) >= first && (+d.m.slice(0, 4) - first) % every === 0)
  return { Wd, split, x, y, y1, past, area, future, band, years, useful: fut.value ? x(nPast.value + fut.value.useful_lead - 1) + 6 : 0 }
})

// Log entries: each run of El Niño years (at its wettest month), the driest year if it stands apart, and the coming
// year as "?". Joined in time order by arrows, like rumours leading to the unknown.
const NODE_W = 66
const entries = computed(() => {
  if (!geo.value) return []
  const m = data.value.months, out = [], runs = []
  for (const yr of [...ninoYears.value].sort()) {
    const last = runs[runs.length - 1]
    if (last && yr === last[last.length - 1] + 1) last.push(yr); else runs.push([yr])
  }
  for (const r of runs) {
    const idx = m.map((s, i) => [s, i]).filter(([s]) => r.includes(+s.slice(0, 4))).map(([, i]) => i)
    if (!idx.length) continue
    const peak = idx.reduce((a, b) => (valueAt(b) ?? -1) > (valueAt(a) ?? -1) ? b : a)
    out.push({ id: 'n' + r[0], i: peak, kind: 'nino', head: r.length > 1 ? `${r[0]}–${String(r[r.length - 1]).slice(2)}` : `${r[0]}`, icon: 'rain', sub: 'El Niño' })
  }
  const byYear = {}
  m.forEach((s, i) => { const v = valueAt(i); if (v != null) (byYear[s.slice(0, 4)] ??= []).push([i, v]) })
  const dry = Object.entries(byYear).filter(([, a]) => a.length === 12)
    .map(([yr, a]) => [yr, a.reduce((s, [, v]) => s + v, 0) / 12, a.reduce((p, q) => q[1] < p[1] ? q : p)[0]])
    .reduce((p, q) => q[1] < p[1] ? q : p, ['', Infinity, 0])
  if (dry[0] && out.every(e => Math.abs(geo.value.x(e.i) - geo.value.x(dry[2])) > NODE_W + 12)) out.push({ id: 'dry', i: dry[2], kind: 'dry', head: dry[0], icon: 'soil_dry', sub: 'Driest' })
  if (fut.value) out.push({ id: 'next', i: nPast.value + Math.floor(nFut.value / 2), kind: 'next', head: fut.value.periods[0].slice(0, 4), icon: null, sub: 'Coming' })
  return out.sort((a, b) => a.i - b.i).map((e, n) => ({ ...e, n, cx: e.kind === 'next' ? geo.value.split + (geo.value.Wd - geo.value.split) / 2 : geo.value.x(e.i) }))
})
const activeEntry = computed(() => {
  if (!data.value) return null
  if (isFuture.value) return 'next'
  const e = entries.value.find(e => e.kind === 'nino' && ninoYears.value.includes(year.value) && Math.abs(e.i - at.value) < 24)
  return e?.id ?? (entries.value.find(e => e.kind === 'dry' && data.value.months[e.i].startsWith(String(year.value)))?.id ?? null)
})
const arrows = computed(() => entries.value.slice(1).map((e, n) => {
  const a = entries.value[n], x1 = a.cx + NODE_W / 2 + 2, x2 = e.cx - NODE_W / 2 - 4, yy = TOP.value / 2 + 6
  return x2 > x1 + 10 ? { id: a.id + e.id, d: `M${x1.toFixed(1)},${yy}L${x2.toFixed(1)},${yy}`, head: `M${(x2 - 6).toFixed(1)},${yy - 5}L${x2.toFixed(1)},${yy}L${(x2 - 6).toFixed(1)},${yy + 5}`, n } : null
}).filter(Boolean))
const cursorX = computed(() => geo.value ? geo.value.x(at.value) : 0)
const cursorY = computed(() => { const v = geo.value && valueAt(at.value); return v == null ? null : geo.value.y(v) })

// ---- controls
// Drag on the screen (or use the arrow keys when it has focus) to move through the months.
let dragging = false
function pickAt(e) {
  const r = plot.value.getBoundingClientRect(), px = e.clientX - r.left, g = geo.value
  let best = 0, bd = Infinity
  for (let i = 0; i < nAll.value; i++) { const d = Math.abs(g.x(i) - px); if (d < bd) { bd = d; best = i } }
  stop(); at.value = best
}
function down(e) { if (e.target.closest('button')) return; dragging = true; plot.value.setPointerCapture(e.pointerId); pickAt(e) }
const move = e => { if (dragging) pickAt(e) }
const up = () => { dragging = false }
function key(e) {
  const d = { ArrowLeft: -1, ArrowRight: 1, PageDown: -12, PageUp: 12 }[e.key] ?? (e.key === 'Home' ? -at.value : e.key === 'End' ? nAll.value - 1 - at.value : 0)
  if (!d) return
  e.preventDefault(); e.stopPropagation()                         // the topic arrows must not move too
  stop(); at.value = Math.max(0, Math.min(nAll.value - 1, at.value + d))
}
const jump = e => { stop(); at.value = e.kind === 'next' ? nPast.value + Math.min(state.ahead.month, nFut.value - 1) : e.i }
function play() {
  if (playing.value) return stop()
  if (at.value >= nAll.value - 1) at.value = 0
  playing.value = true
  timer = setInterval(() => { if (at.value >= nAll.value - 1) stop(); else at.value += at.value < nPast.value - 1 ? 2 : 1 }, 90)
}
function stop() { playing.value = false; clearInterval(timer) }
const toComing = () => { stop(); at.value = nPast.value + Math.min(state.ahead.month, Math.max(0, nFut.value - 1)) }
// The coming months and the map's month are the same thing: keep them together.
watch(at, i => { if (data.value && i >= nPast.value && state.ahead.month !== i - nPast.value) state.ahead.month = i - nPast.value })
watch(() => state.ahead.month, m => { if (data.value && isFuture.value && k.value !== m && m < nFut.value) at.value = nPast.value + m })

const fmt = v => v == null ? '–' : v.toFixed(3)
const errorText = computed(() => !error.value ? '' : /outside_grid|not in the Lambayeque/.test(error.value)
  ? t('Your field is outside the area my models cover (Lambayeque and its edges, in 2 km squares), so there is no log for it.')
  : t('I could not read your field\'s log. Is the model service running?'))

watch(center, load)
onMounted(() => {
  load()
  ro = new ResizeObserver(() => { emit('size', root.value.offsetHeight); if (plot.value) width.value = plot.value.clientWidth })
  ro.observe(root.value)
})
watch(plot, el => { if (el) { width.value = el.clientWidth; ro?.observe(el) } })
onBeforeUnmount(() => { stop(); ctrl?.abort(); ro?.disconnect() })
</script>

<template>
  <div ref="root" class="hud absolute z-[13] flex flex-col gap-1.5 bg-panel/90 px-2.5 py-2" :style="{ left: box.left + 'px', width: box.right - box.left + 'px', bottom: box.bottom + 'px' }">
    <p v-if="error" class="text-sm">{{ errorText }}</p>
    <p v-else-if="!data" class="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted"><span class="block size-2 animate-ping bg-teal" aria-hidden="true" />{{ t('Reading your field\'s past…') }}</p>
    <template v-else>
      <!-- Header: the log's name, where it reads, and the controls -->
      <div class="flex items-center gap-2 whitespace-nowrap">
        <span class="font-mono text-[11px] uppercase tracking-[0.12em] text-teal">{{ t('Field log') }}</span>
        <span class="truncate font-mono text-[11px] text-muted max-lg:hidden">· {{ data.location.nearest ? t('nearest 2 km square, {d} km away', { d: data.location.distance_km }) : t('the 2 km square at your field') }}</span>
        <span class="ml-auto min-w-0" />
        <button v-if="fut" type="button" class="btn !min-h-7 !px-2 font-mono text-[11px]" :aria-pressed="isFuture" @click="toComing">{{ t('{y} →', { y: fut.periods[0].slice(0, 4) }) }}</button>
        <button type="button" class="btn !min-h-7 !w-8 !px-0" :aria-label="playing ? t('Pause') : t('Play from 1998')" :title="playing ? t('Pause') : t('Play from 1998')" @click="play">
          <svg viewBox="0 0 12 12" class="size-3" aria-hidden="true"><path v-if="!playing" d="M2 1 L11 6 L2 11 Z" fill="var(--ink)" /><g v-else fill="var(--ink)"><rect x="2" y="1" width="3" height="10" /><rect x="7" y="1" width="3" height="10" /></g></svg>
        </button>
      </div>

      <!-- The log screen -->
      <div ref="plot" :key="born" class="relative cursor-ew-resize touch-none select-none border border-line bg-bg/70 focus-visible:outline-2 focus-visible:outline-teal" :style="{ height: H + 'px' }"
           role="slider" tabindex="0" :aria-label="t('Month on the time bar')" :aria-valuemin="0" :aria-valuemax="nAll - 1" :aria-valuenow="at" :aria-valuetext="`${t(MONTHS[month - 1])} ${year}`"
           @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up" @keydown="key">
        <svg v-if="geo" class="absolute inset-0 size-full overflow-visible" aria-hidden="true">
          <defs><pattern id="log-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0V24M0 24H24" fill="none" stroke="var(--line)" /></pattern></defs>
          <rect width="100%" height="100%" fill="url(#log-grid)" class="log-fade" />
          <!-- a scan sweeps the screen once while the log draws -->
          <rect :x="0" y="0" width="2" :height="H" fill="var(--teal)" class="log-scan" :style="{ '--w': geo.Wd + 'px' }" />
          <!-- the coming year's side of the screen -->
          <rect v-if="fut" :x="geo.split" y="0" :width="geo.Wd - geo.split" :height="H" fill="var(--teal)" fill-opacity=".06" class="log-fade" style="--d: 1.5s" />
          <line v-if="fut" :x1="geo.split" :x2="geo.split" y1="0" :y2="H" stroke="var(--teal)" stroke-dasharray="3 3" class="log-fade" style="--d: 1.4s" />
          <!-- El Niño years -->
          <template v-for="yr in ninoYears" :key="yr">
            <rect v-if="data.months.includes(`${yr}-01`)" :x="geo.x(data.months.indexOf(`${yr}-01`))" :y="TOP" :width="geo.x(data.months.indexOf(`${yr}-01`) + 11) - geo.x(data.months.indexOf(`${yr}-01`))" :height="H - TOP - 14" fill="var(--line)" class="log-fade" style="--d: .2s" />
          </template>
          <!-- the past: area and line, drawn from 1998 -->
          <path :d="geo.area" fill="var(--teal)" fill-opacity=".1" class="log-fade" style="--d: 1.2s" />
          <path :d="geo.past" fill="none" stroke="var(--teal)" stroke-width="1.5" pathLength="1" class="log-draw" />
          <!-- the coming year: band, then the dashed middle; the dotted line marks how far the projection is useful -->
          <polygon v-if="geo.band" :points="geo.band" fill="var(--teal)" fill-opacity=".18" class="log-fade" style="--d: 1.7s" />
          <path v-if="geo.future" :d="geo.future" fill="none" stroke="var(--teal)" stroke-width="1.5" stroke-dasharray="5 4" class="log-fade" style="--d: 1.9s" />
          <line v-if="fut && fut.useful_lead < nFut" :x1="geo.useful" :x2="geo.useful" :y1="TOP + 4" :y2="geo.y1" stroke="var(--muted)" stroke-dasharray="1 3" class="log-fade" style="--d: 2s" />
          <!-- log entries: ticks down to the line and arrows between them -->
          <template v-if="TOP">
            <line v-for="e in entries" :key="'t' + e.id" :x1="e.cx" :x2="e.kind === 'next' ? e.cx : geo.x(e.i)" :y1="TOP - 2" :y2="valueAt(e.i) != null ? geo.y(valueAt(e.i)) : TOP + 10"
                  stroke="var(--teal)" stroke-opacity=".5" stroke-dasharray="2 2" class="log-fade" :style="{ '--d': 0.6 + e.n * 0.25 + 's' }" />
            <g v-for="a in arrows" :key="a.id">
              <path :d="a.d" stroke="var(--ink)" stroke-opacity=".75" stroke-width="1.5" pathLength="1" class="log-draw" :style="{ '--d': 0.85 + a.n * 0.25 + 's', '--t': '.45s' }" />
              <path :d="a.head" fill="none" stroke="var(--ink)" stroke-opacity=".75" stroke-width="1.5" class="log-fade" :style="{ '--d': 1.25 + a.n * 0.25 + 's' }" />
            </g>
          </template>
          <!-- the chosen month: the one campfire mark of the screen -->
          <g class="log-cursor" :style="{ transform: `translateX(${cursorX}px)` }">
            <line x1="0" x2="0" :y1="TOP" :y2="H - 14" stroke="var(--fire)" stroke-width="2" />
            <rect v-if="cursorY != null" x="-4" :y="cursorY - 4" width="8" height="8" fill="var(--fire)" :transform="`rotate(45 0 ${cursorY})`" />
          </g>
        </svg>
        <!-- entries as HTML cards (pixel icons, crisp text) -->
        <template v-if="TOP">
          <button v-for="e in entries" :key="e.id" type="button" class="log-node absolute top-0 flex flex-col items-stretch border bg-bg text-center"
                  :class="[e.kind === 'next' ? 'border-dashed' : '', activeEntry === e.id ? 'border-fire' : 'border-teal']"
                  :style="{ left: e.cx - NODE_W / 2 + 'px', width: NODE_W + 'px', '--d': 0.6 + e.n * 0.25 + 's' }" :title="t(e.sub)" @click.stop="jump(e)">
            <span class="block truncate px-1 font-mono text-[10px] font-semibold uppercase leading-4 text-bg" :class="activeEntry === e.id ? 'bg-fire' : 'bg-teal'">{{ e.head }}</span>
            <span class="flex h-[30px] items-center justify-center gap-1">
              <PixelIcon v-if="e.icon" :name="e.icon" :size="1" />
              <span v-if="e.kind === 'next'" class="font-display text-xl font-semibold leading-none" :class="activeEntry === e.id ? 'text-fire' : 'text-teal'">?</span>
              <span class="font-mono text-[9px] uppercase text-muted">{{ t(e.sub) }}</span>
            </span>
            <span v-if="activeEntry === e.id" class="log-ping pointer-events-none absolute inset-0 border border-fire" aria-hidden="true" />
          </button>
        </template>
        <!-- year marks (past) and month initials (coming year) -->
        <div class="pointer-events-none absolute inset-x-0 bottom-0 h-3 font-mono text-[10px] leading-3 text-muted" aria-hidden="true">
          <span v-for="d in geo?.years" :key="d.m" class="absolute -translate-x-1/2" :style="{ left: geo.x(d.i) + 'px' }">{{ d.m.slice(0, 4) }}</span>
          <template v-if="fut && phone()"><span class="absolute -translate-x-1/2 text-teal" :style="{ left: geo.split + (geo.Wd - geo.split) / 2 + 'px' }">{{ fut.periods[0].slice(0, 4) }}</span></template>
          <template v-else><span v-for="(p, j) in fut?.periods" :key="p" class="absolute -translate-x-1/2" :class="nPast + j === at ? 'text-fire' : ''" :style="{ left: geo.x(nPast + j) + 'px' }">{{ M1[+p.slice(5, 7) - 1] }}</span></template>
        </div>
      </div>

      <!-- What this month means, in words -->
      <div :key="'w' + born" class="log-rise flex flex-col gap-1">
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
          <span class="font-display text-lg font-semibold leading-tight" :class="isFuture ? 'text-ink' : 'text-fire'">{{ t(MONTHS[month - 1]) }} {{ year }}</span>
          <span v-if="isFuture" class="font-mono text-[11px] uppercase tracking-wider text-teal">{{ t('if {y} is a normal year', { y: year }) }}</span>
          <span v-else-if="ninoYears.includes(year)" class="flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-ink"><PixelIcon name="rain" :size="1" />{{ t('coastal El Niño year') }}</span>
          <span v-else class="font-mono text-[11px] uppercase tracking-wider text-muted">{{ t('measured') }}</span>
        </div>
        <p class="flex items-center gap-2 text-[15px] leading-snug">
          <PixelIcon :name="ICON[word] || 'soil_moist'" :size="2" />
          <span>
            <span class="text-muted">{{ t('Deep soil of your field:') }}</span> {{ word ? t(SENT[word]) : t('no value this month') }}<span v-if="state.mode === 'pro' && valueAt(at) != null" class="font-mono text-sm text-muted"> · {{ fmt(valueAt(at)) }} m³/m³</span>
            <span v-if="isFuture && k + 1 > fut.useful_lead" class="block text-sm text-muted">{{ t('This far ahead my answer is close to a guess: in tests it was no better than a typical year.') }}</span>
          </span>
        </p>
        <!-- The three layers of the block, top to bottom -->
        <div class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs max-lg:hidden">
          <span v-for="l in layers" :key="l.key" class="flex items-center gap-1.5" :class="{ 'opacity-45': l.v == null }">
            <span class="inline-block size-3 border border-line" :style="{ background: l.v == null ? 'transparent' : PAL.deep, opacity: l.v == null ? 1 : 0.25 + 0.75 * (l.fill ?? 0) }" />
            <span class="text-muted">{{ t(NAME[l.n]) }} · {{ l.top_cm }}–{{ l.bottom_cm }} cm:</span>
            <span v-if="l.v == null">{{ t('not projected') }}</span>
            <span v-else-if="state.mode === 'pro'" class="font-mono">{{ fmt(l.v) }}</span>
            <span v-else>{{ t(SHORT[l.w] || 'usual') }}</span>
          </span>
        </div>
      </div>
      <details class="text-[11px] text-muted max-lg:hidden">
        <summary class="cursor-pointer">{{ t('Where these numbers come from') }}</summary>
        {{ t('Line: deep soil water (28–100 cm) from ERA5-Land, read on the 2 km square in the middle of your field; it does not see irrigation. Grey blocks: El Niño years. After the dashed line: my projection for the coming year, with the range where 9 in 10 tries landed.') }}
        {{ t('Not a forecast: my model ran this month with the weather of each past year.') }} {{ t('Drag the screen, or use the arrow keys, to move through the months.') }}
      </details>
    </template>
  </div>
</template>
