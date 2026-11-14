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
const shown = useTween(() => value.value)
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
      <HudCard :title="t('Satellite signals')">
        <div class="grid grid-cols-5 gap-1" role="group" :aria-label="t('Satellite signals')">
          <button v-for="k in LAYER_KEYS" :key="k" type="button" class="btn !h-11 !px-0" :aria-pressed="k === state.layer" :aria-label="t(LAYERS[k].name)" :title="t(LAYERS[k].name)" @click="state.layer = k">
            <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[LAYERS[k].icon]" />
          </button>
        </div>
        <div class="flex min-h-[104px] items-center gap-4" aria-live="polite">
          <div class="flex w-16 shrink-0 justify-center">
            <Instrument v-if="!L.pending" :key="state.layer" :kind="state.layer" :value="value" :domain="L.domain" :size="4" />
          </div>
          <div class="min-w-0">
            <div class="font-mono text-xs text-muted">{{ t(L.name) }}</div>
            <Transition name="flip" mode="out-in">
              <div :key="state.layer + state.mode" class="font-display text-[26px] font-semibold leading-tight" :class="{ 'text-muted': value == null }">
                {{ state.mode === 'farmer' ? t(levelWord(state.layer, value)) : formatValue(state.layer, shown) }}
              </div>
            </Transition>
            <div class="text-xs text-muted">{{ readingNote(state.layer) }}</div>
            <Sparkline v-if="state.mode === 'pro' && series(state.layer)" class="mt-1" :values="series(state.layer)" :domain="L.domain" :at="state.month" />
          </div>
        </div>
        <p v-if="db.error" class="border border-ember p-2 text-ember" role="alert">{{ t('No NASA POWER data for this spot.') }}</p>
        <p v-else>{{ t(current[0]) }}</p>
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
