<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FanChart from '../components/FanChart.vue'
import PixelIcon from '../components/PixelIcon.vue'
import AheadMapCard from '../components/AheadMapCard.vue'
import { state } from '../store.js'
import { proj, projError, spot, periodImage, versusUsual, shortLabel, useAheadMap } from '../lib/projections.js'
import { M1, MONTHS } from '../content.js'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// The coming 12 months of deep soil water (28-100 cm) at the chosen spot, in a normal year: the middle of 28 tries
// (the weather of each past year), the band where most landed, and the usual value. The map shows one month.
useAheadMap(() => periodImage('soil_water', 'base', state.ahead.month))
const s = computed(() => proj.value && spot('soil_water', 'base'))
const periods = computed(() => proj.value?.meta.periods.soil_water ?? [])
const useful = computed(() => proj.value?.meta.useful_lead.soil_water_months ?? 0)
const k = computed(() => state.ahead.month)
const word = i => versusUsual('soil_water', s.value?.median[i], s.value?.usual[i])
const ICON = { wetter: 'soil_wet', usual: 'soil_moist', drier: 'soil_dry' }
const WORD = { wetter: 'Wetter than usual', usual: 'About usual', drier: 'Drier than usual' }
const fmt = v => v == null ? '–' : v.toFixed(3)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The model service is not available ({e}). Start ml-api and reload.', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <HudCard v-else-if="!s"><p class="text-muted">{{ t('There is no projection for this spot. Tap a colored square inside Lambayeque.') }}</p></HudCard>
      <template v-else>
        <HudCard :title="t('Deep soil water at your spot, 2026')">
          <template v-if="state.mode === 'farmer'">
            <!-- Two rows of 6 months: January-June (the months the projection is good for) and July-December (faded). -->
            <div v-for="half in [0, 6]" :key="half" class="grid grid-cols-6 gap-1">
              <button v-for="i in [0, 1, 2, 3, 4, 5].map(j => j + half)" :key="periods[i]" type="button" class="flex flex-col items-center gap-1 border py-1.5"
                      :class="[i === k ? 'border-fire' : 'border-transparent', i + 1 > useful ? 'opacity-45' : '']" :title="t(WORD[word(i)] || '')" @click="state.ahead.month = i">
                <PixelIcon :name="ICON[word(i)] || 'soil_moist'" :size="2" />
                <span class="font-mono text-xs" :class="i === k ? 'text-fire' : 'text-muted'">{{ M1[i] }}</span>
              </button>
            </div>
            <p class="text-lg">
              <span class="text-fire">{{ t(MONTHS[+periods[k].slice(5, 7) - 1]) }}:</span> {{ t(WORD[word(k)]) }}
              <span v-if="k + 1 > useful" class="text-muted"> · {{ t('this far ahead it is a guess close to a typical year') }}</span>
            </p>
          </template>
          <template v-else>
            <FanChart :series="[{ median: s.median, low: s.low, high: s.high, color: PAL.teal, label: 'normal' }]" :usual="s.usual" :at="k" :useful="useful"
                      :labels="periods.map(p => shortLabel('soil_water', p, M1))" :digits="2" @pick="i => (state.ahead.month = i)" />
            <p class="font-mono text-xs">
              <span class="text-fire">{{ fmt(s.median[k]) }} m³/m³</span>
              <span class="text-muted"> · {{ t('90 % range') }} {{ fmt(s.low[k]) }}–{{ fmt(s.high[k]) }} · {{ t('usual') }} {{ fmt(s.usual[k]) }}</span>
            </p>
            <p class="text-xs text-muted">{{ t('Line: middle of 28 tries. Band: 90 % range. Dashed: average 1998–2025.') }}</p>
          </template>
        </HudCard>
      </template>
    </template>

    <template #right>
      <AheadMapCard v-model="state.ahead.month" v="soil_water" :title="t('Month on the map')" />
      <HudCard :title="t('How this is made')">
        <p class="text-xs">{{ t('From the soil water observed in December 2025, Sprout\'s model ran each month of 2026 with the weather of each past year (1998–2025), one at a time. Nobody knows 2026\'s rain yet, so this shows what usually happens next, not a forecast.') }}</p>
        <p class="text-xs text-muted">{{ t('In tests on past years, this beat "a typical year" for the first {n} months.', { n: useful }) }}</p>
      </HudCard>
    </template>
  </SlideFrame>
</template>
