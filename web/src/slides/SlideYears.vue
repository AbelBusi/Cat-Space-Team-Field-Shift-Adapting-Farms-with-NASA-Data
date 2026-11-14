<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import Instrument from '../components/Instrument.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { state, db, history as H } from '../store.js'
import { t } from '../i18n.js'
import { PAL, RAMP } from '../lib/palette.js'

// 44 years at this spot: warming stripes on one side, the three facts worth remembering on the other.
// Stripes: one per year, colored by how far its afternoons were from this place's average. Lab keeps the middle tones clean.
const stripeColor = d3.scaleLinear().domain([-0.9, 0, 0.45, 0.9]).range(RAMP.anomaly).interpolate(d3.interpolateLab).clamp(true)
const W = 330, BH = 84
const bars = computed(() => {
  if (!H.value) return []
  const n = H.value.years.length, max = H.value.wettest.rain || 1, bw = W / n
  return H.value.years.map((d, i) => {
    const h = Math.max(1, d.rain / max * BH), hi = d === H.value.wettest, lo = d === H.value.driest
    return { ...d, x: i * bw + 0.5, w: bw - 1, h, fill: hi ? PAL.fire : lo ? PAL.sand : PAL.teal, op: hi || lo ? 1 : 0.35, hi, lo, cx: Math.min(W - 40, Math.max(40, i * bw + bw / 2)) }
  })
})
const times = computed(() => H.value ? Math.max(1, Math.round(H.value.wettest.rain / Math.max(1, H.value.meanRain))) : 1)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="!H"><p class="text-muted">{{ t(db.error ? 'No NASA POWER data for this spot.' : 'Reading 44 years of NASA data…') }}</p></HudCard>
      <template v-else>
        <HudCard :title="t('Afternoon heat, 1981 to 2024')">
          <div class="stripes" role="img" :aria-label="t('Warming stripes 1981 to 2024. Recent afternoons are {n} degrees warmer than in 1981 to 2000.', { n: H.warming })">
            <i v-for="(d, i) in H.years" :key="d.y" :style="{ background: stripeColor(d.heat - H.heatMean), '--i': i }" :title="`${d.y}: ${d.heat.toFixed(1)} °C`" />
          </div>
          <div class="flex justify-between font-mono text-[10px] text-muted"><span>{{ H.years[0].y }}</span><span>{{ H.years[H.years.length - 1].y }}</span></div>
          <p class="text-xs text-muted">{{ t('Each stripe is one year · turquoise = cooler afternoons · campfire = hotter') }}</p>
        </HudCard>
        <HudCard v-if="state.mode === 'pro'" :title="t('Annual rain, NASA POWER (~55 km cell)')">
          <svg :viewBox="`0 0 ${W} ${BH + 34}`" class="w-full" role="img" :aria-label="t('Annual rain per year. Wettest {w}, driest {d}.', { w: H.wettest.y, d: H.driest.y })">
            <line x1="0" :x2="W" :y1="BH + 14" :y2="BH + 14" :stroke="PAL.line" />
            <rect v-for="(b, i) in bars" :key="b.y" class="bar" :x="b.x" :y="BH + 14 - b.h" :width="b.w" :height="b.h" :fill="b.fill" :fill-opacity="b.op" :style="{ '--i': i }" />
            <template v-for="b in bars" :key="'l' + b.y"><text v-if="b.hi || b.lo" :x="b.cx" :y="b.hi ? 10 : BH + 8 - b.h" text-anchor="middle" class="bar-label" :fill="b.hi ? PAL.fire : PAL.sand">{{ b.y }} · {{ b.rain }} mm</text></template>
            <text x="0" :y="BH + 30" class="bar-axis">{{ H.years[0].y }}</text><text :x="W" :y="BH + 30" text-anchor="end" class="bar-axis">{{ H.years[H.years.length - 1].y }}</text>
          </svg>
        </HudCard>
      </template>
    </template>

    <template v-if="H" #right>
      <HudCard :title="t('Wettest year')">
        <div class="flex items-center gap-3">
          <Instrument kind="rain" :value="H.wettest.rain" :domain="[0, H.wettest.rain]" :size="2" />
          <div><div class="font-display text-2xl font-semibold text-fire">{{ H.wettest.y }}</div>
            <div class="text-muted">{{ state.mode === 'farmer' ? t('About {n}× the rain of a normal year', { n: times }) : t('{n} mm · average {avg} mm', { n: H.wettest.rain, avg: H.meanRain }) }}</div></div>
        </div>
      </HudCard>
      <HudCard :title="t('Driest year')">
        <div class="flex items-center gap-3">
          <PixelIcon name="soil_dry" :size="3" />
          <div><div class="font-display text-2xl font-semibold">{{ H.driest.y }}</div>
            <div class="text-muted">{{ state.mode === 'farmer' ? t('The ground was at its thirstiest') : t('{n} mm of rain', { n: H.driest.rain }) }}</div></div>
        </div>
      </HudCard>
      <HudCard :title="t('Afternoons now vs 1981–2000')">
        <div class="flex items-center gap-3">
          <PixelIcon :name="H.warming > 0.1 ? 'up' : H.warming < -0.1 ? 'down' : 'flat'" :color="H.warming > 0.1 ? PAL.ember : PAL.teal" :size="3" />
          <div><div class="font-display text-2xl font-semibold">{{ H.warming > 0 ? '+' : '' }}{{ H.warming }} °C</div>
            <div class="text-muted">{{ state.mode === 'farmer'
              ? t(H.warming > 0.3 ? 'Noticeably hotter than in your parents\' time' : H.warming > 0.1 ? 'A little hotter than before' : H.warming < -0.3 ? 'Noticeably cooler than before' : H.warming < -0.1 ? 'A little cooler than before' : 'About the same as before')
              : t('Rain {n} % over the same periods', { n: (H.rainChange > 0 ? '+' : '') + H.rainChange }) }}</div></div>
        </div>
      </HudCard>
    </template>
  </SlideFrame>
</template>
