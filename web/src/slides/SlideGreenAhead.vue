<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FanChart from '../components/FanChart.vue'
import PixelIcon from '../components/PixelIcon.vue'
import AheadMapCard from '../components/AheadMapCard.vue'
import { state } from '../store.js'
import { proj, projError, spot, periodImage, shortLabel, useAheadMap, SCENARIOS } from '../lib/projections.js'
import { M1 } from '../content.js'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// Plant greenness (NDVI) for the four quarters of 2026, in the chosen "what if". A quarter = 3 months.
useAheadMap(() => periodImage('ndvi', state.ahead.scen, state.ahead.quarter, state.ahead.scen !== 'base'))
const s = computed(() => proj.value && spot('ndvi', state.ahead.scen))
const periods = computed(() => proj.value?.meta.periods.ndvi ?? [])
const useful = computed(() => proj.value?.meta.useful_lead.ndvi_quarters ?? 0)
const k = computed(() => state.ahead.quarter)
// The same thresholds as the greenness reading of "today" (content.js LAYERS.veg).
const plant = v => v == null ? 'bare' : v < 0.2 ? 'bare' : v < 0.4 ? 'plant_thirsty' : 'plant_ok'
const WORD = { bare: 'Almost bare', plant_thirsty: 'A little green', plant_ok: 'Green' }
const QMONTHS = ['Jan–Mar', 'Apr–Jun', 'Jul–Sep', 'Oct–Dec']
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The projections file is not available ({e}).', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <HudCard v-else-if="!s"><p class="text-muted">{{ t('There is no projection for this spot. Tap a colored square inside Lambayeque.') }}</p></HudCard>
      <HudCard v-else :title="t('Greenness at your spot, 2026')">
        <template v-if="state.mode === 'farmer'">
          <div class="grid grid-cols-4 gap-1">
            <button v-for="(p, i) in periods" :key="p" type="button" class="flex flex-col items-center gap-1 border py-2" :class="i === k ? 'border-fire' : 'border-transparent'" @click="state.ahead.quarter = i">
              <PixelIcon :name="plant(s.median[i])" :size="3" />
              <span class="font-mono text-[10px] uppercase text-muted">{{ t(QMONTHS[i]) }}</span>
              <span class="text-xs">{{ t(WORD[plant(s.median[i])]) }}</span>
            </button>
          </div>
        </template>
        <template v-else>
          <FanChart :series="[{ median: s.median, low: s.low, high: s.high, color: PAL.sage, label: state.ahead.scen }]" :usual="s.usual" :at="k" :useful="useful"
                    :labels="periods.map(p => shortLabel('ndvi', p, M1))" :digits="2" @pick="i => (state.ahead.quarter = i)" />
          <p class="font-mono text-xs"><span class="text-fire">NDVI {{ s.median[k]?.toFixed(2) }}</span>
            <span v-if="s.low" class="text-muted"> · {{ t('90 % range') }} {{ s.low[k]?.toFixed(2) }}–{{ s.high[k]?.toFixed(2) }}</span>
            <span class="text-muted"> · {{ t('usual') }} {{ s.usual[k]?.toFixed(2) }}</span></p>
        </template>
        <p class="text-xs text-muted">{{ t('Greenness is harder to project than soil water: the model gets it only a little better than the usual value. Irrigation is not in the data.') }}</p>
      </HudCard>
    </template>

    <template #right>
      <HudCard :title="t('What if…')">
        <div class="seg flex-wrap" role="group" :aria-label="t('What if…')">
          <button v-for="x in SCENARIOS" :key="x.id" type="button" :aria-pressed="state.ahead.scen === x.id" :title="t(x.hint)" @click="state.ahead.scen = x.id">
            <PixelIcon :name="x.icon" :size="1" />
          </button>
        </div>
        <p class="text-xs">{{ t(SCENARIOS.find(x => x.id === state.ahead.scen).label) }}</p>
      </HudCard>
      <AheadMapCard v-model="state.ahead.quarter" v="ndvi" :diff="state.ahead.scen !== 'base'" :title="t('Quarter on the map')" />
    </template>
  </SlideFrame>
</template>
