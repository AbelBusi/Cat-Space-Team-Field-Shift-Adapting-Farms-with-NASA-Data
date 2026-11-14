<script setup>
import { ref, computed } from 'vue'
import * as d3 from 'd3'
import Reveal from './Reveal.vue'
import Instrument from './Instrument.vue'
import PixelIcon from './PixelIcon.vue'
import { state, db, history, placeLabel } from '../store.js'
import { useScript } from '../guide.js'
import { t } from '../i18n.js'
import { PAL, RAMP } from '../lib/palette.js'

const el = ref(null)
useScript('years', el)
const H = history
// Warming stripes: one stripe per year, colored by how far its afternoons were from this place's average.
const stripeColor = d3.scaleLinear().domain([-0.9, 0, 0.45, 0.9]).range(RAMP.anomaly).interpolate(d3.interpolateLab).clamp(true)   // Lab keeps the middle tones clean
const W = 660, BH = 120
const bars = computed(() => {
  if (!H.value) return []
  const n = H.value.years.length, max = H.value.wettest.rain || 1, bw = W / n
  return H.value.years.map((d, i) => {
    const h = Math.max(1, d.rain / max * BH), hi = d === H.value.wettest, lo = d === H.value.driest
    return { ...d, x: i * bw + 1, w: bw - 2, h, fill: hi ? PAL.fire : lo ? PAL.sand : PAL.teal, op: hi || lo ? 1 : 0.35, hi, lo, cx: i * bw + bw / 2 }
  })
})
const times = computed(() => H.value ? Math.max(1, Math.round(H.value.wettest.rain / Math.max(1, H.value.meanRain))) : 1)
</script>

<template>
  <section ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">2</span>
        <h2>{{ t('Your place, year by year') }}</h2>
        <p>{{ t('44 years of NASA POWER data at {place} (1981–2024): which years were hard, and how the climate is shifting.', { place: state.point ? placeLabel(state.point) : t('this spot') }) }}</p>
      </div>
      <p v-if="!H" class="muted">{{ t(db.error ? 'No NASA POWER data for this spot.' : 'Reading 44 years of NASA data…') }}</p>
      <template v-else>
        <Reveal :at="0">
          <div class="card years-card">
            <div class="stripes" role="img" :aria-label="t('Warming stripes 1981 to 2024. Recent afternoons are {n} degrees warmer than in 1981 to 2000.', { n: H.warming })">
              <i v-for="(d, i) in H.years" :key="d.y" :style="{ background: stripeColor(d.heat - H.heatMean), '--i': i }" :title="`${d.y}: ${d.heat.toFixed(1)} °C`" />
            </div>
            <div class="axis"><span>{{ H.years[0].y }}</span><span>{{ t('Each stripe is one year · turquoise = cooler afternoons · campfire = hotter') }}</span><span>{{ H.years[H.years.length - 1].y }}</span></div>
          </div>
        </Reveal>
        <Reveal :at="1">
          <div class="facts">
            <div class="card fact">
              <Instrument kind="rain" :value="H.wettest.rain" :domain="[0, H.wettest.rain]" :size="2" />
              <div><span class="k">{{ t('Wettest year') }}</span><b>{{ H.wettest.y }}</b>
                <span v-if="state.mode === 'farmer'">{{ t('About {n}× the rain of a normal year', { n: times }) }}</span>
                <span v-else>{{ t('{n} mm · average {avg} mm', { n: H.wettest.rain, avg: H.meanRain }) }}</span></div>
            </div>
            <div class="card fact">
              <PixelIcon name="soil_dry" :size="3" />
              <div><span class="k">{{ t('Driest year') }}</span><b>{{ H.driest.y }}</b>
                <span v-if="state.mode === 'farmer'">{{ t('The ground was at its thirstiest') }}</span>
                <span v-else>{{ t('{n} mm of rain', { n: H.driest.rain }) }}</span></div>
            </div>
            <div class="card fact">
              <PixelIcon :name="H.warming > 0.1 ? 'up' : H.warming < -0.1 ? 'down' : 'flat'" :color="H.warming > 0.1 ? PAL.ember : PAL.teal" :size="3" />
              <div><span class="k">{{ t('Afternoons now vs 1981–2000') }}</span><b>{{ H.warming > 0 ? '+' : '' }}{{ H.warming }} °C</b>
                <span v-if="state.mode === 'farmer'">{{ t(H.warming > 0.3 ? 'Noticeably hotter than in your parents\' time' : H.warming > 0.1 ? 'A little hotter than before' : H.warming < -0.3 ? 'Noticeably cooler than before' : H.warming < -0.1 ? 'A little cooler than before' : 'About the same as before') }}</span>
                <span v-else>{{ t('Rain {n} % over the same periods', { n: (H.rainChange > 0 ? '+' : '') + H.rainChange }) }}</span></div>
            </div>
          </div>
          <div v-if="state.mode === 'pro'" class="card years-card">
            <svg :viewBox="`0 0 ${W} ${BH + 34}`" class="rain-bars" role="img" :aria-label="t('Annual rain per year. Wettest {w}, driest {d}.', { w: H.wettest.y, d: H.driest.y })">
              <line x1="0" :x2="W" :y1="BH + 14" :y2="BH + 14" :stroke="PAL.line" />
              <rect v-for="(b, i) in bars" :key="b.y" class="bar" :x="b.x" :y="BH + 14 - b.h" :width="b.w" :height="b.h" :fill="b.fill" :fill-opacity="b.op" :style="{ '--i': i }" />
              <template v-for="b in bars" :key="'l' + b.y"><text v-if="b.hi || b.lo" :x="b.cx" :y="b.hi ? 10 : BH + 8 - b.h" text-anchor="middle" class="bar-label" :fill="b.hi ? PAL.fire : PAL.sand">{{ b.y }} · {{ b.rain }} mm</text></template>
              <text x="0" :y="BH + 30" class="bar-axis">{{ H.years[0].y }}</text><text :x="W" :y="BH + 30" text-anchor="end" class="bar-axis">{{ H.years[H.years.length - 1].y }}</text>
            </svg>
            <div class="axis"><span>{{ t('Annual rain, NASA POWER (~55 km cell)') }}</span></div>
          </div>
        </Reveal>
      </template>
    </div>
  </section>
</template>
