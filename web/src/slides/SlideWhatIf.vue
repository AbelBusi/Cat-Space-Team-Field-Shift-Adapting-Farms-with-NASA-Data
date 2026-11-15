<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FanChart from '../components/FanChart.vue'
import PixelIcon from '../components/PixelIcon.vue'
import AheadMapCard from '../components/AheadMapCard.vue'
import SimTuner from '../components/SimTuner.vue'
import { state } from '../store.js'
import { proj, projError, spot, periodImage, shortLabel, useAheadMap, SCENARIOS } from '../lib/projections.js'
import { M1, MONTHS } from '../content.js'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// The simulator: one "what if" at a time against a normal year. The map shows the change in the chosen month
// (campfire = drier, turquoise = wetter); the card shows both years at the spot.
useAheadMap(() => periodImage('soil_water', state.ahead.scen, state.ahead.month, true))
const scen = computed(() => SCENARIOS.find(x => x.id === state.ahead.scen))
const base = computed(() => proj.value && spot('soil_water', 'base'))
const alt = computed(() => proj.value && spot('soil_water', state.ahead.scen))
const periods = computed(() => proj.value?.meta.periods.soil_water ?? [])
const useful = computed(() => proj.value?.meta.useful_lead.soil_water_months ?? 0)
const k = computed(() => state.ahead.month)
const diff = computed(() => base.value && alt.value ? alt.value.median.map((v, i) => v == null || base.value.median[i] == null ? null : v - base.value.median[i]) : null)
const biggest = computed(() => diff.value ? diff.value.reduce((b, v, i) => Math.abs(v ?? 0) > Math.abs(diff.value[b] ?? 0) ? i : b, 0) : 0)
const dir = v => v == null ? 'flat' : v > 0.005 ? 'up' : v < -0.005 ? 'down' : 'flat'
const WORD = { up: 'Wetter than in a normal year', down: 'Drier than in a normal year', flat: 'About the same as a normal year' }
const month = i => t(MONTHS[+periods.value[i].slice(5, 7) - 1])
const members = computed(() => proj.value?.soil_water[state.ahead.scen]?.members)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The projections file is not available ({e}).', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <HudCard v-else-if="!base"><p class="text-muted">{{ t('There is no projection for this spot. Tap a colored square inside Lambayeque.') }}</p></HudCard>
      <template v-else>
        <HudCard :title="t('{what}: deep soil water at your spot', { what: t(scen.label) })">
          <template v-if="state.ahead.scen === 'base'">
            <p>{{ t('Pick a "what if" on the right to compare it with this normal year.') }}</p>
          </template>
          <template v-else-if="state.mode === 'farmer'">
            <div class="flex items-center gap-3">
              <PixelIcon :name="dir(diff[k])" :color="dir(diff[k]) === 'down' ? PAL.ember : dir(diff[k]) === 'up' ? PAL.teal : PAL.ink" :size="3" />
              <div>
                <div class="text-base"><span class="text-fire">{{ month(k) }}:</span> {{ t(WORD[dir(diff[k])]) }}</div>
                <div class="text-xs text-muted">{{ t('Biggest change: {m}', { m: month(biggest) }) }}</div>
              </div>
            </div>
          </template>
          <template v-if="state.ahead.scen !== 'base' || state.mode === 'pro'">
            <FanChart :series="[{ median: base.median, color: PAL.muted, label: 'normal' }, { median: alt.median, low: alt.low, high: alt.high, color: PAL.teal, label: state.ahead.scen }]"
                      :at="k" :useful="useful" :labels="periods.map(p => shortLabel('soil_water', p, M1))" :digits="2" @pick="i => (state.ahead.month = i)" />
            <p class="text-xs text-muted">{{ t('Gray: a normal year. Turquoise: {what}.', { what: t(scen.label).toLowerCase() }) }}
              <span v-if="state.mode === 'pro' && diff[k] != null" class="font-mono text-ink"> Δ {{ month(k) }}: {{ (diff[k] > 0 ? '+' : '') + diff[k].toFixed(3) }} m³/m³</span></p>
          </template>
        </HudCard>
        <HudCard :title="t('Read it with care')">
          <p class="text-xs">{{ t('This is how Sprout\'s model answers a made-up situation. It is not a forecast, and it does not prove that rain alone would cause it.') }}</p>
          <p v-if="state.ahead.scen === 'el_nino'" class="text-xs text-muted">{{ t('Only {n} past years had a coastal El Niño in the rainy season, so this answer is less sure.', { n: members }) }}</p>
        </HudCard>
      </template>
    </template>

    <template #right>
      <HudCard :title="t('What if…')">
        <div class="flex flex-col gap-1">
          <button v-for="x in SCENARIOS" :key="x.id" type="button" class="btn !justify-start !px-2 text-left" :aria-pressed="state.ahead.scen === x.id" :title="t(x.hint)" @click="state.ahead.scen = x.id">
            <PixelIcon :name="x.icon" :size="1" /><span>{{ t(x.label) }}</span>
          </button>
        </div>
        <p class="text-xs text-muted">{{ t(scen.hint) }}</p>
      </HudCard>
      <AheadMapCard v-model="state.ahead.month" v="soil_water" :diff="state.ahead.scen !== 'base'" :title="t('Month on the map')" />
      <SimTuner />
    </template>
  </SlideFrame>
</template>
