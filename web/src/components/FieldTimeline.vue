<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import PixelIcon from './PixelIcon.vue'
import { state } from '../store.js'
import { getTimeline, ML_API } from '../lib/mlApi.js'
import { versusUsual } from '../lib/projections.js'
import { MONTHS } from '../content.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'

// The outlined field through time: every month since 1998 of the 2 km square at the field's centre, then the
// projection. Dragging the bar (or playing it) fills the soil layers of the 3D block with that month's water.
// Observed (ERA5-Land), the model's months and the projection are drawn apart and named; nothing is filled in.
const props = defineProps({ box: { type: Object, required: true } })
const emit = defineEmits(['layers', 'size'])
const root = ref(null)
let ro = null
const data = ref(null), error = ref(null), at = ref(0), playing = ref(false)
let timer = 0, ctrl = null

const center = computed(() => {
  const r = state.parcel?.ring || []
  return r.length ? { lat: r.reduce((s, p) => s + p[0], 0) / r.length, lon: r.reduce((s, p) => s + p[1], 0) / r.length } : null
})
const nPast = computed(() => data.value?.months.length ?? 0)
const fut = computed(() => data.value?.future?.soil_water ?? null)
const nAll = computed(() => nPast.value + (fut.value?.periods.length ?? 0))
const label = computed(() => at.value < nPast.value ? data.value.months[at.value] : fut.value.periods[at.value - nPast.value])
const isFuture = computed(() => at.value >= nPast.value)
const year = computed(() => +label.value.slice(0, 4))
const month = computed(() => +label.value.slice(5, 7))
const elNino = computed(() => data.value?.el_nino_years.includes(year.value))

async function load() {
  if (!center.value || !ML_API) return
  ctrl?.abort(); ctrl = new AbortController()
  error.value = null; data.value = null
  try {
    data.value = await getTimeline(center.value, ctrl.signal)
    at.value = nPast.value - 1                                    // open on the last observed month
    say(() => t('Under the block there is a time bar. Drag it, or press play, to see how much water each soil layer of your field held, month by month since 1998.'), 'happy', [], { level: 'note' })
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message }
}

// Each layer this month: its value, how full it is for this place (5-95 % of its own record) and the word against
// the usual value of that calendar month. In the projection only the deep layer is known.
const layers = computed(() => {
  if (!data.value) return []
  return data.value.layers.map((l, k) => {
    let v = null, usual = l.usual_by_month[month.value - 1]
    if (!isFuture.value) v = l.observed[at.value]
    else if (l.key === 'sm_root_m3m3') { v = fut.value.median[at.value - nPast.value]; usual = fut.value.usual[at.value - nPast.value] }
    const fill = v == null || l.p05 == null ? null : Math.max(0, Math.min(1, (v - l.p05) / Math.max(1e-6, l.p95 - l.p05)))
    return { ...l, k, v, usual, fill, word: versusUsual('soil_water', v, usual) }
  })
})
watch(layers, ls => emit('layers', ls.map(l => l.fill)), { immediate: true })

const ICON = { wetter: 'soil_wet', usual: 'soil_moist', drier: 'soil_dry' }
const WORD = { wetter: 'Wetter than usual', usual: 'About usual', drier: 'Drier than usual' }
const NAME = ['Surface', 'Middle', 'Deep']

// The strip: the deep layer observed (teal), the projection after the last data (dashed, with its band), El Niño
// years as faint blocks, and the chosen month in campfire.
const W = 600, H = 46, P = 3
const chart = computed(() => {
  if (!data.value) return null
  const deep = data.value.layers.find(l => l.key === 'sm_root_m3m3')
  const f = fut.value, all = [...deep.observed, ...(f ? [...f.low_90, ...f.high_90] : [])].filter(v => v != null)
  const lo = Math.min(...all), hi = Math.max(...all), n = nAll.value
  const x = i => P + i / Math.max(1, n - 1) * (W - 2 * P), y = v => H - P - (v - lo) / Math.max(1e-6, hi - lo) * (H - 2 * P)
  const path = (vals, off = 0) => vals.map((v, i) => v == null ? null : `${x(i + off).toFixed(1)},${y(v).toFixed(1)}`)
    .reduce((s, p, i, a) => p ? s + (a[i - 1] ? 'L' : 'M') + p : s, '')
  const nino = data.value.el_nino_years.map(yr => {
    const i = data.value.months.indexOf(`${yr}-01`)
    return i < 0 ? null : { yr, x: x(i), w: x(i + 11) - x(i) }
  }).filter(Boolean)
  const band = f ? [...f.high_90.map((v, i) => `${x(nPast.value + i).toFixed(1)},${y(v).toFixed(1)}`), ...f.low_90.map((v, i) => `${x(nPast.value + i).toFixed(1)},${y(v).toFixed(1)}`).reverse()].join(' ') : ''
  const ticks = data.value.months.map((m, i) => ({ m, i })).filter(d => d.m.endsWith('-01') && (+d.m.slice(0, 4) - 1998) % 5 === 0).map(d => ({ yr: d.m.slice(0, 4), at: x(d.i) / W }))
  return { past: path(deep.observed), future: f ? path([deep.observed[nPast.value - 1], ...f.median], nPast.value - 1) : '', band, nino, ticks,
           today: x(nPast.value - 1), cursor: x(at.value) }
})

function pick(e) {
  const r = e.currentTarget.getBoundingClientRect()
  at.value = Math.round(Math.max(0, Math.min(1, ((e.clientX - r.left) / r.width * W - P) / (W - 2 * P))) * (nAll.value - 1))
}
function play() {
  if (playing.value) return stop()
  if (at.value >= nAll.value - 1) at.value = 0
  playing.value = true
  timer = setInterval(() => { if (at.value >= nAll.value - 1) stop(); else at.value++ }, 140)
}
function stop() { playing.value = false; clearInterval(timer) }
const fmt = v => v == null ? '–' : v.toFixed(3)

watch(center, load)
onMounted(() => { load(); ro = new ResizeObserver(() => emit('size', root.value.offsetHeight)); ro.observe(root.value) })
onBeforeUnmount(() => { stop(); ctrl?.abort(); ro?.disconnect() })
</script>

<template>
  <div ref="root" class="hud absolute z-[13] flex flex-col gap-1 bg-panel/90 px-2 py-1.5" :style="{ left: box.left + 'px', width: box.right - box.left + 'px', bottom: box.bottom + 'px' }">
    <p v-if="error" class="text-xs text-muted">{{ t('The time bar could not load ({e}).', { e: error }) }}</p>
    <p v-else-if="!data" class="font-mono text-xs uppercase tracking-wider text-muted">{{ t('Reading your field\'s past…') }}</p>
    <template v-else>
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
        <button type="button" class="btn !min-h-8 !w-9 !px-0" :aria-label="playing ? t('Pause') : t('Play from 1998')" :title="playing ? t('Pause') : t('Play from 1998')" @click="play">
          <svg viewBox="0 0 12 12" class="size-3" aria-hidden="true"><path v-if="!playing" d="M2 1 L11 6 L2 11 Z" fill="var(--ink)" /><g v-else fill="var(--ink)"><rect x="2" y="1" width="3" height="10" /><rect x="7" y="1" width="3" height="10" /></g></svg>
        </button>
        <span class="font-display text-base font-semibold" :class="isFuture ? 'text-muted' : 'text-fire'">{{ t(MONTHS[month - 1]) }} {{ year }}</span>
        <span v-if="isFuture" class="font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('projection, not a measurement') }}</span>
        <span v-else-if="elNino" class="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-ink"><PixelIcon name="rain" :size="1" />{{ t('coastal El Niño year') }}</span>
        <!-- The three layers, top to bottom, as on the side of the block -->
        <div class="ml-auto flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
          <span v-for="l in layers" :key="l.key" class="flex items-center gap-1" :class="{ 'opacity-40': l.v == null }"
                :title="t('{name} soil, {a}–{b} cm', { name: t(NAME[l.k]), a: l.top_cm, b: l.bottom_cm })">
            <PixelIcon :name="ICON[l.word] || 'soil_moist'" :size="1" />
            <span class="font-mono text-[10px] text-muted">{{ l.top_cm }}–{{ l.bottom_cm }} cm</span>
            <span v-if="l.v == null" class="max-lg:hidden">{{ t('not projected') }}</span>
            <span v-else-if="state.mode === 'pro'" class="font-mono">{{ fmt(l.v) }}</span>
            <span v-else class="max-lg:hidden">{{ t(WORD[l.word]) }}</span>
          </span>
        </div>
      </div>
      <svg :viewBox="`0 0 ${W} ${H}`" class="h-11 w-full cursor-pointer" preserveAspectRatio="none" role="img"
           :aria-label="t('Deep soil water at your field every month since 1998, then the projection')" @click="pick">
        <rect v-for="b in chart.nino" :key="b.yr" :x="b.x" y="0" :width="b.w" :height="H" fill="var(--line)" />
        <line :x1="chart.today" :x2="chart.today" y1="0" :y2="H" stroke="var(--muted)" stroke-dasharray="2 2" />
        <polygon v-if="chart.band" :points="chart.band" fill="var(--teal)" fill-opacity=".15" />
        <path :d="chart.past" fill="none" stroke="var(--teal)" stroke-width="1.2" vector-effect="non-scaling-stroke" />
        <path v-if="chart.future" :d="chart.future" fill="none" stroke="var(--teal)" stroke-width="1.2" stroke-dasharray="4 3" vector-effect="non-scaling-stroke" />
        <line :x1="chart.cursor" :x2="chart.cursor" y1="0" :y2="H" stroke="var(--fire)" stroke-width="2" vector-effect="non-scaling-stroke" />
      </svg>
      <div class="relative h-3 font-mono text-[10px] text-muted" aria-hidden="true">
        <span v-for="k in chart.ticks" :key="k.yr" class="absolute top-0 -translate-x-1/2" :style="{ left: k.at * 100 + '%' }">{{ k.yr }}</span>
      </div>
      <input v-model.number="at" type="range" min="0" :max="nAll - 1" step="1" class="w-full accent-fire" :aria-label="t('Month on the time bar')" :aria-valuetext="`${t(MONTHS[month - 1])} ${year}`" @input="stop">
      <p class="text-[10px] text-muted max-lg:hidden">
        {{ t('Line: deep soil (28–100 cm) at the 2 km square in the middle of your field, ERA5-Land. Grey blocks: El Niño years. Dashed: projection.') }}
        <span v-if="state.mode === 'pro' && !isFuture && data.model.predicted[at] != null"> · {{ t('model this month {v}', { v: fmt(data.model.predicted[at]) }) }}</span>
      </p>
    </template>
  </div>
</template>
