<script setup>
import { computed, ref, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import Sparkline from '../components/Sparkline.vue'
import Instrument from '../components/Instrument.vue'
import { LAYERS, LAYER_KEYS, MONTHS, ICON, reading, levelWord } from '../content.js'
import { state, db, series, valueAt, formatValue, readingNote, local, mapUi } from '../store.js'
import { gibsDataLayers } from '../lib/nasa.js'
import { formatShortDate } from '../lib/geo.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'
import { useTween } from '../lib/tween.js'
import { melody } from '../lib/sound.js'

// One signal at a time: what it reads this month (left), and the month and kind of year you are looking at (right).
const L = computed(() => LAYERS[state.layer])
const value = computed(() => valueAt(state.layer))
const current = computed(() => reading(state.layer, value.value))
const shownAll = useTween(() => LAYER_KEYS.map(k => valueAt(k)))
const legendStops = computed(() => { const sc = L.value.scale(), [a, b] = L.value.domain; return d3.range(0, 1.0001, 0.125).map(p => sc(a + p * (b - a))).join(',') })

// One NASA image at a time on top of the photo: two color scales over each other are hard to read.
const GRID = { id: 'grid', label: 'Rain grid 0.1° (IMERG)', resolution: 'each square ≈ 11 km, 2001–2024 average',
  hint: 'Typical rain for the chosen month in every IMERG cell of Lambayeque. Follows the month and the El Niño switch.' }
const gibsLayers = gibsDataLayers()
const images = computed(() => local.value ? [...gibsLayers, GRID] : gibsLayers)
const image = computed(() => images.value.find(x => x.id === mapUi.data))

function setScen(s) {
  state.scen = s
  const coast = !!local.value && LAYERS.rain.px === 11
  say(s === 'nino'
    ? (coast ? 'Coastal El Niño years! On this coast I use the Niño 1+2 index: 1983, 1998, 2016, 2017 and 2023, the years that flooded Lambayeque.'
      : 'El Niño years! Now every month is the average of the El Niño years only. Watch how the colors change.')
    : 'Back to the typical year: the average of 2001 to 2024.', s === 'nino' ? 'surprised' : 'neutral')
}

const playing = ref(false)
let playTimer
function togglePlay() {
  playing.value = !playing.value
  clearInterval(playTimer)
  if (playing.value) playTimer = setInterval(() => { state.month = (state.month + 1) % 12 }, 900)
}
const listening = ref(false)
let listenTimer
function listen() {
  const vals = series(state.layer)
  if (listening.value || !vals) return
  const [lo, hi] = L.value.domain
  melody(vals.map(v => v == null ? 0 : Math.min(1, Math.max(0, (v - lo) / (hi - lo)))))
  say('Listen! High notes mean more, low notes mean less. One note per month.', 'happy')
  listening.value = true
  const start = state.month
  let i = 0
  listenTimer = setInterval(() => {
    state.month = i
    if (++i >= 12) { clearInterval(listenTimer); listening.value = false; state.month = start }
  }, 320)
}
onBeforeUnmount(() => { clearInterval(playTimer); clearInterval(listenTimer) })
</script>

<template>
  <SlideFrame>
    <template #left>
      <!-- All five signals at once, one row each: the tool a farmer knows, its word or number, and how it moves in the
           year (Pro). Tapping a row paints that signal on the map. -->
      <HudCard :title="t('Satellite signals')">
        <div class="flex flex-col gap-1" role="radiogroup" :aria-label="t('Satellite signals')">
          <button v-for="(k, i) in LAYER_KEYS" :key="k" type="button" role="radio" :aria-checked="k === state.layer"
                  class="grid grid-cols-[2.5rem_minmax(0,1fr)_auto] items-center gap-3 border px-2 py-1.5 text-left transition-colors"
                  :class="k === state.layer ? 'border-teal bg-teal/10' : 'border-line hover:border-muted'" @click="state.layer = k">
            <span class="flex h-12 items-center justify-center">
              <Instrument v-if="!LAYERS[k].pending" :kind="k" :value="valueAt(k)" :domain="LAYERS[k].domain" :size="2" />
              <svg v-else class="size-5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[LAYERS[k].icon]" />
            </span>
            <span class="min-w-0">
              <span class="block font-mono text-[11px] uppercase tracking-wider" :class="k === state.layer ? 'text-teal' : 'text-muted'">{{ t(LAYERS[k].name) }}</span>
              <span class="block font-display text-lg font-semibold leading-tight" :class="{ 'text-muted': valueAt(k) == null }">
                {{ state.mode === 'farmer' ? t(levelWord(k, valueAt(k))) : formatValue(k, shownAll[i]) }}
              </span>
              <span class="block truncate text-[11px] text-muted">{{ readingNote(k) }}</span>
            </span>
            <Sparkline v-if="state.mode === 'pro' && series(k)" :values="series(k)" :domain="LAYERS[k].domain" :at="state.month" />
          </button>
        </div>
        <p v-if="db.error" class="border border-ember p-2 text-ember" role="alert">{{ t('No NASA POWER data for this spot.') }}</p>
        <p v-else class="border-l-2 border-teal pl-2" aria-live="polite"><b>{{ t(L.name) }}:</b> {{ t(current[0]) }}</p>
      </HudCard>
    </template>

    <template #right>
      <HudCard :title="t('Month and kind of year')">
        <div class="flex items-center gap-3">
          <button type="button" class="btn !size-10 shrink-0 !px-0" :aria-label="t(playing ? 'Pause' : 'Play the 12 months')" @click="togglePlay">
            <svg class="size-4" viewBox="0 0 24 24" aria-hidden="true" v-html="playing ? ICON.pause : ICON.play" />
          </button>
          <Transition name="flip" mode="out-in"><div :key="state.month" class="font-display text-xl font-semibold">{{ t(MONTHS[state.month]) }}</div></Transition>
        </div>
        <div>
          <input class="w-full" type="range" min="0" max="11" step="1" :value="state.month" :aria-label="t('Month')" @input="state.month = +$event.target.value; playing && togglePlay()">
          <div class="grid grid-cols-12 text-center font-mono text-[10px] text-muted" aria-hidden="true"><span v-for="(m, i) in MONTHS" :key="i" :class="{ 'text-teal': i === state.month }">{{ t(m)[0] }}</span></div>
        </div>
        <div class="seg self-start" role="group" :aria-label="t('Kind of year')">
          <button type="button" :aria-pressed="state.scen === 'normal'" @click="setScen('normal')">{{ t('Typical year') }}</button>
          <button type="button" :aria-pressed="state.scen === 'nino'" @click="setScen('nino')">{{ t('El Niño years') }}</button>
        </div>
      </HudCard>
      <HudCard :title="t('Color on the map')">
        <label class="flex items-center gap-2 font-mono text-xs text-muted">{{ t('Paint') }}
          <select class="min-w-0 flex-1 border border-line bg-bg px-2 py-1.5 text-ink" :value="mapUi.data || ''" @change="mapUi.data = $event.target.value || null">
            <option value="">{{ t('The signal on the left') }}</option>
            <option v-for="d in images" :key="d.id" :value="d.id">{{ t(d.label) }}</option>
          </select>
        </label>
        <template v-if="image">
          <p class="text-xs text-muted">{{ t(image.hint) }} {{ image.resolution }}<template v-if="image.date"> · NASA, {{ formatShortDate(image.date) }}</template></p>
          <label class="flex items-center gap-2 font-mono text-xs text-muted">{{ t('Intensity') }} <input v-model.number="mapUi.intensity" class="min-w-0 flex-1" type="range" min="0.3" max="1" step="0.05"></label>
        </template>
        <template v-else>
          <div class="flex items-center gap-2 font-mono text-xs text-muted">
            <span>{{ t('Less') }}</span><span class="h-2.5 flex-1" :style="{ background: `linear-gradient(90deg, ${legendStops})` }" /><span>{{ t('More') }}</span>
          </div>
          <p class="text-xs text-muted">{{ t('Source:') }} {{ t(L.ds) }} · {{ t('one square ≈ {km} km', { km: L.px }) }}</p>
        </template>
        <button type="button" class="btn self-start" :aria-pressed="listening" :disabled="!series(state.layer)" @click="listen">
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON.sound" />
          {{ t(listening ? 'Listening…' : 'Listen to the year') }}
        </button>
      </HudCard>
    </template>
  </SlideFrame>
</template>
