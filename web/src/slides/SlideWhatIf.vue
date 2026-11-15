<script setup>
import { computed, watch } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FanChart from '../components/FanChart.vue'
import PixelIcon from '../components/PixelIcon.vue'
import AheadMapCard from '../components/AheadMapCard.vue'
import SimTuner from '../components/SimTuner.vue'
import { state } from '../store.js'
import { proj, projError, spot, periodImage, shortLabel, useAheadMap, versusUsual, SCENARIOS } from '../lib/projections.js'
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
// Farmer words. A change smaller than the model's own error (validation RMSE 0.0125 m³/m³) is "about the same".
const ERR = 0.0125, BIG = 0.04
const dir = v => v == null || Math.abs(v) < ERR ? 'flat' : v > 0 ? 'up' : 'down'
const size = v => v == null || Math.abs(v) < ERR ? 'same' : Math.abs(v) >= BIG ? 'much' : 'little'
const WORD = { 'up.much': 'Much wetter than in a normal year', 'up.little': 'A little wetter than in a normal year',
  'down.much': 'Much drier than in a normal year', 'down.little': 'A little drier than in a normal year',
  'flat.same': 'About the same as a normal year' }
const word = v => WORD[`${dir(v)}.${size(v)}`]
const arrowColor = v => dir(v) === 'down' ? PAL.ember : dir(v) === 'up' ? PAL.teal : PAL.muted
// The ground of each month, compared with what is usual at this spot in that month.
const SOIL = { wetter: 'soil_wet', usual: 'soil_moist', drier: 'soil_dry' }
const ground = (series, i) => SOIL[versusUsual('soil_water', series?.median[i], base.value?.usual[i])] || 'soil_moist'
const SHORT = { el_nino: 'With El Niño', drought_feb_mar: 'Without rain' }
// A new "what if" opens on the month where it changes the most.
watch(() => [state.ahead.scen, biggest.value], () => { if (state.ahead.scen !== 'base') state.ahead.month = biggest.value })
const month = i => t(MONTHS[+periods.value[i].slice(5, 7) - 1])
const members = computed(() => proj.value?.soil_water[state.ahead.scen]?.members)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The model service is not available ({e}). Start ml-api and reload.', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <HudCard v-else-if="!base"><p class="text-muted">{{ t('There is no projection for this spot. Tap a colored square inside Lambayeque.') }}</p></HudCard>
      <template v-else>
        <HudCard :title="t('{what}: deep soil water at your spot', { what: t(scen.label) })">
          <template v-if="state.ahead.scen === 'base'">
            <p>{{ t('Pick a "what if" on the right to compare it with this normal year.') }}</p>
          </template>
          <template v-else-if="state.mode === 'farmer'">
            <div class="flex items-center gap-3">
              <PixelIcon :name="dir(diff[k])" :color="arrowColor(diff[k])" :size="3" />
              <div>
                <div class="text-base"><span class="text-fire">{{ month(k) }}:</span> {{ t(word(diff[k])) }}</div>
                <button v-if="biggest !== k" type="button" class="text-xs text-muted underline" @click="state.ahead.month = biggest">{{ t('Biggest change: {m}', { m: month(biggest) }) }}</button>
              </div>
            </div>
            <!-- Two furrows of 12 months: the ground in a normal year, the ground in the "what if", and the change. -->
            <div class="grid grid-cols-[5.5rem_repeat(12,minmax(0,1fr))] items-center gap-y-1 text-[11px]">
              <span class="text-muted">{{ t('Normal year') }}</span>
              <span v-for="(p, i) in periods" :key="'b' + p" class="flex justify-center" :class="{ 'opacity-40': i + 1 > useful }"><PixelIcon :name="ground(base, i)" :size="1" /></span>
              <span class="text-ink">{{ t(SHORT[state.ahead.scen]) }}</span>
              <span v-for="(p, i) in periods" :key="'a' + p" class="flex justify-center" :class="{ 'opacity-40': i + 1 > useful }"><PixelIcon :name="ground(alt, i)" :size="1" /></span>
              <span class="text-muted">{{ t('Change') }}</span>
              <span v-for="(p, i) in periods" :key="'d' + p" class="flex justify-center" :class="{ 'opacity-40': i + 1 > useful }">
                <PixelIcon v-if="dir(diff[i]) !== 'flat'" :name="dir(diff[i])" :color="arrowColor(diff[i])" :size="1" /><span v-else class="text-muted">·</span>
              </span>
              <span />
              <button v-for="(p, i) in periods" :key="'m' + p" type="button" class="border font-mono text-[10px]" :class="i === k ? 'border-fire text-fire' : 'border-transparent text-muted'" @click="state.ahead.month = i">{{ M1[i] }}</button>
            </div>
            <p class="text-xs text-muted">{{ t('Ground: dry, usual or wet for this spot and month. Arrow: wetter or drier than a normal year; a dot means about the same. Faded months are too far ahead to trust.') }}</p>
          </template>
          <template v-else>
            <FanChart :series="[{ median: base.median, color: PAL.muted, label: 'normal' }, { median: alt.median, low: alt.low, high: alt.high, color: PAL.teal, label: state.ahead.scen }]"
                      :at="k" :useful="useful" :labels="periods.map(p => shortLabel('soil_water', p, M1))" :digits="2" @pick="i => (state.ahead.month = i)" />
            <p class="text-xs text-muted">{{ t('Gray: a normal year. Turquoise: {what}.', { what: t(scen.label).toLowerCase() }) }}
              <span v-if="diff[k] != null" class="font-mono text-ink"> Δ {{ month(k) }}: {{ (diff[k] > 0 ? '+' : '') + diff[k].toFixed(3) }} m³/m³</span></p>
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
