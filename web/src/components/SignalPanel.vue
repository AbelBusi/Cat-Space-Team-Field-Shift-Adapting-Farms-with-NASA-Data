<script setup>
import { computed, ref } from 'vue'
import * as d3 from 'd3'
import Reveal from './Reveal.vue'
import Sparkline from './Sparkline.vue'
import Instrument from './Instrument.vue'
import PixelGlobe from './PixelGlobe.vue'
import { LAYERS, LAYER_KEYS, MONTHS, ICON, reading, levelWord } from '../content.js'
import { state, db, series, valueAt, climate, placeLabel, cell } from '../store.js'
import PixelIcon from './PixelIcon.vue'
import { say } from '../guide.js'
import { useTween } from '../lib/tween.js'
import { melody } from '../lib/sound.js'
import { formatArea, formatShortDate } from '../lib/geo.js'

const L = computed(() => LAYERS[state.layer])
const current = computed(() => reading(state.layer, valueAt(state.layer)))
const shown = useTween(() => LAYER_KEYS.map(k => valueAt(k)))

function fmt(k, v) {
  if (LAYERS[k].pending) return 'Coming soon'
  if (v == null) return k === 'veg' && db.ndviError ? 'Not available' : '…'
  if (k === 'veg') return v.toFixed(2)
  return (k === 'heat' || k === 'water' ? (k === 'water' && v > 0 ? '+' : '') + v.toFixed(1) : Math.round(v)) + ' ' + LAYERS[k].unit
}
function note(k) {
  if (k === 'veg') return db.ndviLoading ? 'MODIS is slow, about a minute…' : db.ndviError ? 'MODIS service did not answer' : 'in ' + MONTHS[state.month] + ' 2024'
  if (LAYERS[k].pending) return 'needs Earthdata login'
  if (k === 'water') return 'trend 2002–2026, regional'
  return 'in ' + MONTHS[state.month] + (state.scen === 'nino' ? ', El Niño years' : ', typical year')
}
function pick(k) {
  state.layer = k
  const [text, mood] = reading(k, valueAt(k))
  say(`${LAYERS[k].name}: ${text}`, mood)
}

// How big one pixel of the current source is compared with the field (the outlined one, or a typical 3 ha).
const fieldHa = computed(() => state.parcel ? state.parcel.areaM2 / 10_000 : 3)
const fieldLabel = computed(() => state.parcel ? `your ${formatArea(state.parcel.areaM2)} field` : 'a 3 ha field')
const lens = computed(() => {
  const FIELD_HA = fieldHa.value
  const pxHa = L.value.px * L.value.px * 100
  if (pxHa < FIELD_HA) return { side: Math.max(3, 72 * Math.sqrt(pxHa / FIELD_HA)), fine: true, n: Math.max(1, Math.round(FIELD_HA / pxHa)), m: Math.round(L.value.px * 1000) }
  return { side: Math.max(2, 72 * Math.sqrt(FIELD_HA / pxHa)), fine: false, n: d3.format(',')(Math.max(1, Math.round(pxHa / FIELD_HA))), km: L.value.px }
})

const listening = ref(false)
function listen() {
  const vals = series(state.layer)
  if (listening.value || !vals) return
  const [lo, hi] = L.value.domain
  melody(vals.map(v => v == null ? 0 : Math.min(1, Math.max(0, (v - lo) / (hi - lo)))))
  say('Listen! High notes mean more, low notes mean less. One note per month.', 'happy')
  listening.value = true
  const start = state.month
  let i = 0
  const t = setInterval(() => {
    state.month = i
    if (++i >= 12) { clearInterval(t); listening.value = false; state.month = start }
  }, 320)
}
</script>

<template>
  <aside class="card panel" aria-live="polite">
    <div class="place-row">
    <PixelGlobe :lat="state.point?.lat" :lon="state.point?.lon" :size="96" />
    <div class="place">
      <span class="tag">{{ climate?.label || (db.error ? 'No data' : 'Reading the climate…') }}</span>
      <Transition name="flip" mode="out-in"><h3 :key="state.point ? placeLabel(state.point) : ''">{{ state.point ? placeLabel(state.point) : 'Pick a place' }}</h3></Transition>
      <span v-if="state.point" class="muted small">{{ state.point.lat }}, {{ state.point.lon }} · {{ state.scen === 'nino' ? 'El Niño years' : 'typical year (2001–2024)' }}</span>
    </div>
    </div>
    <p v-if="db.recent" class="recent small">
      <b>Last 30 days</b> ({{ formatShortDate(db.recent.from) }} – {{ formatShortDate(db.recent.to) }}):
      {{ db.recent.rainMm.toFixed(1) }} mm of rain on {{ db.recent.rainyDays }} days, {{ db.recent.tempC.toFixed(1) }} °C on average.
    </p>
    <p v-else-if="!db.recentError && db.loading" class="recent small muted">Reading the last 30 days…</p>
    <p v-if="db.error" class="say err" role="alert">Could not load NASA POWER: {{ db.error }}</p>
    <div v-else class="say">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" v-html="ICON[L.icon]" />
      <span><strong>{{ L.name }}:</strong> {{ current[0] }}</span>
    </div>
    <div class="readout">
      <button v-for="(k, i) in LAYER_KEYS" :key="k" type="button" class="sig-row" :class="{ pending: LAYERS[k].pending }" :aria-pressed="k === state.layer" @click="pick(k)">
        <span class="sig-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[LAYERS[k].icon]" /></span>
        <span class="sig-txt">
          <span class="k">{{ LAYERS[k].name }}</span>
          <span class="v" :class="{ wait: valueAt(k) == null }">{{ state.mode === 'farmer' ? levelWord(k, valueAt(k)) : fmt(k, shown[i]) }}</span>
          <span class="s">{{ note(k) }}</span>
        </span>
        <span v-if="state.mode === 'farmer'" class="inst-cell"><Instrument v-if="!LAYERS[k].pending" :kind="k" :value="valueAt(k)" :domain="LAYERS[k].domain" :size="2" /></span>
        <Sparkline v-else-if="series(k)" :values="series(k)" :domain="LAYERS[k].domain" :at="state.month" />
        <span v-else class="spark-wait" aria-hidden="true" />
      </button>
    </div>
    <div v-if="cell && cell.land > 0" class="ground">
      <PixelIcon :name="cell.slope < 2 ? 'soil_moist' : cell.slope < 6 ? 'soil_dry' : 'up'" :size="2" />
      <div>
        <span class="k">Ground · NASADEM 30 m, cell mean</span>
        <b v-if="state.mode === 'pro'">{{ cell.elev }} m above sea · slope {{ cell.slope }}°</b>
        <b v-else>{{ cell.slope < 2 ? 'Flat ground' : cell.slope < 6 ? 'Gentle slope' : 'Steep ground' }}</b>
        <span>{{ cell.slope < 2 ? 'Low erosion risk.' : cell.slope < 6 ? 'Bare soil can wash away in heavy rain.' : 'High erosion risk when the soil is bare: keep it covered.' }}</span>
      </div>
    </div>
    <Reveal :at="4">
      <div class="lens">
        <div class="lens-viz" aria-hidden="true"><span :style="{ width: Math.min(72, lens.side) + 'px', height: Math.min(72, lens.side) + 'px' }" /></div>
        <p v-if="lens.fine">For <b>{{ L.name.toLowerCase() }}</b> one pixel is about {{ lens.m }} m wide. About <b>{{ lens.n }} pixels</b> fit in {{ fieldLabel }}, so it sees inside the field.</p>
        <p v-else>For <b>{{ L.name.toLowerCase() }}</b> one pixel is about {{ lens.km }} km wide. {{ fieldLabel[0].toUpperCase() + fieldLabel.slice(1) }} fits <b>{{ lens.n }} times</b> in it: it describes the region, not the exact field.</p>
      </div>
    </Reveal>
    <button type="button" class="listen" :aria-pressed="listening" :disabled="!series(state.layer)" @click="listen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON.sound" />
      {{ listening ? 'Listening…' : `Listen to ${L.name.toLowerCase()} over the year` }}
    </button>
  </aside>
</template>
