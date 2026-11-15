<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { state } from '../store.js'
import { proj, projError, gridImage, useAheadMap } from '../lib/projections.js'
import { getTimeline } from '../lib/mlApi.js'
import { PAL, RAMP } from '../lib/palette.js'
import { t } from '../i18n.js'

// Towards 2030 (docs/ML_TRENDS.md): how this place changed from 1998 to 2025, and that trend drawn on to 2030 with the
// range of past years around it. The models' projections are useful for months, not years, so 2027-2030 is the
// observed trend, labelled by check T (it did not beat "nothing changes" on 2018-2025). The map shows where the change
// is clear. One idea per card; the dashed part is always called a direction.
const VARS = [
  { id: 'temperature', name: 'Temperature', icon: 'sun', up: 'Getting warmer', down: 'Getting cooler', good: -1, digits: 2 },
  { id: 'rain', name: 'Rain', icon: 'rain', up: 'More rain than before', down: 'Less rain than before', good: 0, digits: 0 },
  { id: 'soil_water', name: 'Deep soil water', icon: 'soil_moist', up: 'Deep soil getting wetter', down: 'Deep soil getting drier', good: 1, digits: 3 },
  { id: 'ndvi', name: 'Greenness', icon: 'plant_ok', up: 'Greener than before', down: 'Less green than before', good: 1, digits: 3 },
]
const mapVar = ref('temperature')

// The map: each square coloured by its trend per decade where it is clear, the "normal" tone where it is not.
useAheadMap(d => {
  const tr = d.trends?.[mapVar.value]
  if (!tr) return null
  const sign = mapVar.value === 'temperature' ? -1 : 1                     // hotter reads like drier: campfire side
  const clearVals = tr.per_decade.filter((v, i) => v != null && tr.clear[i]).map(v => Math.abs(v))
  const m = Math.max(1e-9, d3.quantile(clearVals.sort(d3.ascending), 0.95) || 1)
  const [wet, normal, dry, drier] = RAMP.anomaly
  const color = d3.scaleLinear().domain([-m, -m / 3, 0, m / 3, m]).range([drier, dry, normal, normal, wet]).interpolate(d3.interpolateLab).clamp(true)
  return gridImage(i => tr.per_decade[i] == null ? null : tr.clear[i] ? sign * tr.per_decade[i] : 0, color)
})
const share = computed(() => {
  const tr = proj.value?.trends?.[mapVar.value]
  if (!tr) return null
  const n = tr.clear.filter(c => c != null).length, up = tr.per_decade.filter((v, i) => tr.clear[i] && v > 0).length, down = tr.per_decade.filter((v, i) => tr.clear[i] && v < 0).length
  return { up: Math.round(100 * up / n), down: Math.round(100 * down / n) }
})

// The chosen spot's own trends (the 2 km square, or the nearest one).
const tl = ref(null), err = ref(null)
let ctrl = null
async function load() {
  if (!state.point) return
  ctrl?.abort(); ctrl = new AbortController(); err.value = null
  try { tl.value = await getTimeline(state.point, ctrl.signal) } catch (e) { if (e.name !== 'AbortError') { err.value = e.message; tl.value = null } }
}
watch(() => state.point, load, { immediate: true })
onBeforeUnmount(() => ctrl?.abort())

const W = 260, H = 46
function chart(tr) {
  const ext = tr.extension, ys = tr.yearly.map((v, k) => [tr.years[k], v]).filter(([, v]) => v != null)
  const all = [...ys.map(d => d[1]), ...(ext ? [...ext.low, ...ext.high] : [])]
  const x = d3.scaleLinear().domain([1998, 2030]).range([3, W - 3]), y = d3.scaleLinear().domain(d3.extent(all)).nice().range([H - 4, 4])
  return {
    past: d3.line()(ys.map(([a, b]) => [x(a), y(b)])), dots: ys.map(([a, b]) => ({ x: x(a), y: y(b) })),
    trend: tr.line ? [x(tr.line.from[0]), y(tr.line.from[1]), x(tr.line.to[0]), y(tr.line.to[1])] : null,
    band: ext ? [...ext.years.map((a, k) => `${x(a)},${y(ext.high[k])}`), ...ext.years.map((a, k) => `${x(a)},${y(ext.low[k])}`).reverse()].join(' ') : '',
    mid: ext ? d3.line()([[x(2025), y(tr.line.to[1])], ...ext.years.map((a, k) => [x(a), y(ext.centre[k])])]) : '', now: x(2025.5),
  }
}
const rows = computed(() => !tl.value ? [] : VARS.map(v => {
  const tr = tl.value.trends[v.id]
  if (!tr || tr.per_decade == null) return { ...v, tr: null }
  const dir = tr.direction, good = dir === 'none' || v.good === 0 ? PAL.ink : (dir === 'up') === (v.good > 0) ? PAL.teal : PAL.ember
  return { ...v, tr, dir, color: good, word: dir === 'up' ? v.up : dir === 'down' ? v.down : 'No clear change since 1998', g: chart(tr) }
}))
const UNIT = { temperature: '°C', rain: 'mm', soil_water: 'm³/m³', ndvi: '' }
const fmt = (v, d) => (v > 0 ? '+' : '') + v.toFixed(d)
const helps = computed(() => tl.value && Object.values(tl.value.trends).some(tr => tr.check?.trend_helps))
const ninoEvery = computed(() => tl.value ? Math.round(1 / tl.value.el_nino_share_1998_2025) : 6)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="!state.point"><p class="text-muted">{{ t('Tap a square inside Lambayeque to see how that place has changed since 1998.') }}</p></HudCard>
      <HudCard v-else-if="err"><p>{{ /outside_grid/.test(err) ? t('This spot is outside the area my models cover (Lambayeque and its edges).') : t('I could not read this place\'s past. Is the model service running?') }}</p></HudCard>
      <HudCard v-else-if="!tl"><p class="text-muted">{{ t('Reading 28 years of this place…') }}</p></HudCard>
      <HudCard v-else :title="t('Your place since 1998, and towards 2030')">
        <ul class="flex flex-col gap-2.5">
          <li v-for="r in rows" :key="r.id" class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2">
              <PixelIcon :name="r.icon" :size="2" />
              <span class="font-mono text-[11px] uppercase tracking-wider text-muted">{{ t(r.name) }}</span>
              <span class="ml-auto flex items-center gap-1 text-sm">
                <PixelIcon :name="r.dir === 'up' ? 'up' : r.dir === 'down' ? 'down' : 'flat'" :color="r.color" :size="1" />{{ r.tr ? t(r.word) : t('not enough data') }}
              </span>
            </div>
            <svg v-if="r.tr" :viewBox="`0 0 ${W} ${H}`" class="h-11 w-full" role="img" :aria-label="t('{name} every year since 1998, and the trend drawn on to 2030', { name: t(r.name) })">
              <rect :x="r.g.now" y="0" :width="W - r.g.now" :height="H" fill="var(--teal)" fill-opacity=".06" />
              <polygon v-if="r.g.band" :points="r.g.band" fill="var(--teal)" fill-opacity=".16" />
              <path :d="r.g.past" fill="none" stroke="var(--teal)" stroke-opacity=".45" stroke-width="1" />
              <circle v-for="(d, k) in r.g.dots" :key="k" :cx="d.x" :cy="d.y" r="1.6" fill="var(--teal)" />
              <line v-if="r.g.trend" :x1="r.g.trend[0]" :y1="r.g.trend[1]" :x2="r.g.trend[2]" :y2="r.g.trend[3]" :stroke="r.color" stroke-width="2" />
              <path v-if="r.g.mid" :d="r.g.mid" fill="none" :stroke="r.color" stroke-width="2" stroke-dasharray="4 3" />
            </svg>
            <p v-if="r.tr && state.mode === 'pro'" class="font-mono text-[11px] text-muted">
              {{ fmt(r.tr.per_decade, r.digits) }} {{ UNIT[r.id] }} {{ t('per decade') }} [{{ fmt(r.tr.per_decade_low, r.digits) }}, {{ fmt(r.tr.per_decade_high, r.digits) }}] · {{ r.tr.clear ? t('clear') : t('not clear') }}
            </p>
          </li>
        </ul>
        <p class="text-xs text-muted">{{ t('Dots: each year since 1998. Solid line: the trend. Dashed and band: that trend drawn on to 2030, with the range of past years around it.') }}</p>
      </HudCard>
    </template>

    <template #right>
      <HudCard :title="t('Where it is changing')">
        <div class="seg" role="group" :aria-label="t('Where it is changing')">
          <button v-for="v in VARS" :key="v.id" type="button" :aria-pressed="mapVar === v.id" :title="t(v.name)" @click="mapVar = v.id"><PixelIcon :name="v.icon" :size="1" /></button>
        </div>
        <p class="text-sm">{{ t(VARS.find(v => v.id === mapVar).name) }}</p>
        <p v-if="share" class="text-xs">{{ t('Clear change in {a} % of Lambayeque going up and {b} % going down, 1998–2025. Faint squares: no clear change.', { a: share.up, b: share.down }) }}</p>
        <p v-else-if="projError" class="text-xs text-muted">{{ t('The model service is not available ({e}). Start ml-api and reload.', { e: projError }) }}</p>
      </HudCard>
      <HudCard :title="t('Can a trend tell 2030?')">
        <p class="text-xs">{{ helps ? t('In tests on 2018–2025, extending the trend was closer to reality than assuming no change.') : t('I tested it: a trend drawn on 1998–2017 did not predict 2018–2025 better than "nothing changes". So the dashed part is a direction, not a number.') }}</p>
        <p class="flex items-center gap-2 text-xs"><PixelIcon name="rain" :size="1" />{{ t('About one year in {n} had a coastal El Niño since 1998: the range to 2030 includes years like them.', { n: ninoEvery }) }}</p>
      </HudCard>
    </template>
  </SlideFrame>
</template>
