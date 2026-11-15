<script setup>
import { reactive, ref, computed, watch, onBeforeUnmount } from 'vue'
import HudCard from './HudCard.vue'
import FanChart from './FanChart.vue'
import PixelIcon from './PixelIcon.vue'
import { state } from '../store.js'
import { simulateClimate, ML_API } from '../lib/mlApi.js'
import { M1, MONTHS } from '../content.js'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// The simulator's buttons: the farmer changes the coming months' weather, the ML API runs the tested XGBoost model
// on this 2 km cell and compares it with a normal year. Inputs (yours) and results (the model's) are shown apart.
const H = 6                                  // the useful lead of the projections (docs/ML_PROJECTIONS.md)
const START = '2025-12'
const ui = reactive({ dry: [], t2m: 0, rain: 1, analog: 'all' })
const busy = ref(false), error = ref(null), res = ref(null)
let ctrl = null, lastKey = ''
const leadMonth = k => MONTHS[(11 + k) % 12]          // lead 1 = January when the start is December
const body = computed(() => ({
  location: { lat: state.point?.lat, lon: state.point?.lon }, start: START, horizon: H,
  scenario: { dry_months: [...ui.dry].sort(), t2m_delta: ui.t2m, rain_factor: ui.rain, analog: ui.analog },
}))
const changed = computed(() => ui.dry.length || ui.t2m || ui.rain !== 1 || ui.analog !== 'all')
async function run() {
  const key = JSON.stringify(body.value)
  if (!state.point || busy.value || key === lastKey) return          // no duplicate requests
  ctrl?.abort(); ctrl = new AbortController()
  busy.value = true; error.value = null
  try { res.value = await simulateClimate(body.value, ctrl.signal); lastKey = key }
  catch (e) { if (e.name !== 'AbortError') { error.value = e.message; res.value = null } }
  finally { busy.value = false }
}
const toggleDry = k => { ui.dry = ui.dry.includes(k) ? ui.dry.filter(x => x !== k) : [...ui.dry, k] }
watch(() => state.point, () => { res.value = null; lastKey = '' })
onBeforeUnmount(() => ctrl?.abort())

const biggest = computed(() => res.value && res.value.comparison.reduce((b, c) => Math.abs(c.absolute_difference) > Math.abs(b.absolute_difference) ? c : b))
const verdict = computed(() => {
  const b = biggest.value
  if (!b) return null
  if (b.within_model_error) return { icon: 'flat', color: PAL.ink, word: 'No clear change: smaller than the model\'s own error' }
  return b.absolute_difference < 0 ? { icon: 'down', color: PAL.ember, word: 'Drier than in a normal year' } : { icon: 'up', color: PAL.teal, word: 'Wetter than in a normal year' }
})
const at = ref(0)
</script>

<template>
  <HudCard v-if="ML_API" :title="t('Simulator · your own what-if')">
    <p class="text-xs text-muted">{{ t('Your changes to the next 6 months of weather. The model then runs on this 2 km cell.') }}</p>
    <div class="flex flex-col gap-1">
      <span class="font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('Months without rain') }}</span>
      <div class="grid grid-cols-6 gap-0.5">
        <button v-for="k in H" :key="k" type="button" class="btn !min-h-8 !px-0 font-mono text-xs" :aria-pressed="ui.dry.includes(k)" :title="t(leadMonth(k))" @click="toggleDry(k)">{{ M1[(11 + k) % 12] }}</button>
      </div>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <span class="font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('Afternoons') }}</span>
      <div class="seg" role="group" :aria-label="t('Temperature change')">
        <button v-for="d in [-1, 0, 1, 2]" :key="d" type="button" :aria-pressed="ui.t2m === d" @click="ui.t2m = d">{{ d > 0 ? '+' : '' }}{{ d }} °C</button>
      </div>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <span class="font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('Weather years') }}</span>
      <div class="seg" role="group" :aria-label="t('Weather years')">
        <button type="button" :aria-pressed="ui.analog === 'all'" @click="ui.analog = 'all'">{{ t('All') }}</button>
        <button type="button" :aria-pressed="ui.analog === 'el_nino'" @click="ui.analog = 'el_nino'">El Niño</button>
      </div>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <span class="font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('Rain') }}</span>
      <div class="seg" role="group" :aria-label="t('Rain change')">
        <button v-for="f in [0.5, 1, 1.5]" :key="f" type="button" :aria-pressed="ui.rain === f" @click="ui.rain = f">× {{ f }}</button>
      </div>
      <span v-if="ui.rain !== 1 && res?.reliability?.simulation_model === 'v1'" class="text-[11px] text-muted">{{ t('the model barely reacts to rain alone') }}</span>
    </div>
    <button type="button" class="btn" :disabled="!state.point || busy || !changed" @click="run">
      <PixelIcon name="satellite" :size="1" />{{ busy ? t('The model is running…') : t('Run the model') }}
    </button>
    <p v-if="error" class="text-xs text-ember">{{ t('The simulator could not answer: {e}', { e: error }) }}</p>

    <template v-if="res">
      <div class="border-t border-line pt-2">
        <div class="label">{{ t('Model result (XGBoost)') }}</div>
        <div v-if="state.mode === 'farmer'" class="mt-1 flex items-center gap-3">
          <PixelIcon :name="verdict.icon" :color="verdict.color" :size="3" />
          <p>{{ t(verdict.word) }}<span class="text-muted"> · {{ t('biggest in {m}', { m: t(MONTHS[+biggest.period.slice(5, 7) - 1]) }) }}</span></p>
        </div>
        <FanChart v-else :series="[{ median: res.baseline.median, color: PAL.muted, label: 'normal' }, { median: res.scenario.median, low: res.scenario.low_90, high: res.scenario.high_90, color: PAL.teal, label: 'yours' }]"
                  :at="at" :useful="res.reliability.useful_lead_months" :labels="res.periods.map(p => M1[+p.slice(5, 7) - 1])" :digits="2" @pick="i => (at = i)" />
        <p class="text-xs">{{ res.interpretation.summary }}</p>
        <details class="text-xs text-muted">
          <summary class="cursor-pointer">{{ t('Limits of this answer ({n})', { n: res.interpretation.limitations.length }) }}</summary>
          <ul class="mt-1 list-disc pl-4"><li v-for="l in res.interpretation.limitations" :key="l">{{ l }}</li></ul>
          <p class="mt-1">{{ t('Changed by you:') }} {{ res.modified_inputs.join(' · ') }}</p>
        </details>
      </div>
    </template>
  </HudCard>
</template>
