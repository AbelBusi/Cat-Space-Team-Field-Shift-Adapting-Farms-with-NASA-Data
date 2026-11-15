<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { state } from '../store.js'
import { proj, projError, useAheadMap } from '../lib/projections.js'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// How well the projections did on past years (hindcasts 2018-2022, the years used to decide): for each distance
// ahead, how much better than "a typical year" (or "same as last month"). One story: the last useful month in campfire.
useAheadMap(() => null)
const m = computed(() => proj.value?.meta)
const W = 330, H = 120, B = 18
function bars(v) {
  const rows = m.value?.skill_by_lead[v] ?? [], useful = m.value?.useful_lead[v === 'ndvi' ? 'ndvi_quarters' : 'soil_water_months'] ?? 0
  const max = Math.max(0.05, ...rows.map(r => r.high ?? r.skill)), min = Math.min(0, ...rows.map(r => r.low ?? r.skill))
  const y = s => B + (max - s) / (max - min) * (H - 2 * B), bw = W / Math.max(1, rows.length)
  return { useful, zero: y(0), rows: rows.map((r, i) => ({ ...r, x: i * bw + 2, w: bw - 4, y0: Math.min(y(0), y(r.skill)), h: Math.max(1, Math.abs(y(r.skill) - y(0))),
    lo: r.low == null ? null : y(r.low), hi: r.high == null ? null : y(r.high), cx: i * bw + bw / 2, last: r.lead === useful, ok: r.lead <= useful })) }
}
const sm = computed(() => bars('soil_water'))
const nd = computed(() => bars('ndvi'))
const pct = v => Math.round(v * 100)
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The projections file is not available ({e}).', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <template v-else>
        <HudCard :title="t('Deep soil water: better than a typical year?')">
          <div class="flex items-center gap-3">
            <PixelIcon name="calendar" :size="3" />
            <p class="text-base">{{ t('Useful for the next {n} months. After that, it is close to a typical year.', { n: sm.useful }) }}</p>
          </div>
          <svg v-if="state.mode === 'pro'" :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img" :aria-label="t('Skill by month ahead')">
            <line x1="0" :x2="W" :y1="sm.zero" :y2="sm.zero" :stroke="PAL.line" />
            <g v-for="r in sm.rows" :key="r.lead">
              <rect :x="r.x" :y="r.y0" :width="r.w" :height="r.h" :fill="r.last ? PAL.fire : PAL.teal" :fill-opacity="r.last ? 1 : r.ok ? 0.55 : 0.2" />
              <line v-if="r.lo != null" :x1="r.cx" :x2="r.cx" :y1="r.lo" :y2="r.hi" :stroke="PAL.muted" />
              <text :x="r.cx" :y="H - 3" text-anchor="middle" class="bar-axis">{{ r.lead }}</text>
            </g>
          </svg>
          <p v-if="state.mode === 'pro'" class="text-xs text-muted">{{ t('Bars: skill by months ahead (1 = perfect, 0 = no better than the simple rule), tested on 2018–2022 with 95 % intervals.') }}</p>
        </HudCard>
        <HudCard :title="t('Greenness')">
          <p>{{ nd.useful ? t('Useful for the next {n} quarters, but only a little better than the usual value.', { n: nd.useful }) : t('Not clearly better than the usual value: read greenness ahead as a rough idea.') }}</p>
          <p v-if="state.mode === 'pro'" class="font-mono text-xs text-muted">{{ nd.rows.map(r => `Q+${r.lead}: ${r.skill.toFixed(2)}`).join(' · ') }}</p>
        </HudCard>
      </template>
    </template>

    <template v-if="proj" #right>
      <HudCard :title="t('The 90 % range, checked')">
        <p class="text-xs">{{ t('In 2023–2025, a period with a coastal El Niño, the real soil water fell inside the range {a} % of the time (greenness: {b} %). It should be 90 %: in extreme years the ranges are too narrow.', { a: pct(m.coverage_2023_2025.sm), b: pct(m.coverage_2023_2025.ndvi) }) }}</p>
      </HudCard>
      <HudCard :title="t('What Sprout cannot tell you')">
        <ul class="flex flex-col gap-1.5 text-xs">
          <li class="flex gap-2"><PixelIcon name="harvest" :size="1" />{{ t('Your harvest or your profit: there is no harvest data yet.') }}</li>
          <li class="flex gap-2"><PixelIcon name="rain" :size="1" />{{ t('Next year\'s rain: it is not forecast, only the range of past years.') }}</li>
          <li class="flex gap-2"><PixelIcon name="drop" :size="1" />{{ t('Irrigation: the data do not include it.') }}</li>
          <li class="flex gap-2"><PixelIcon name="satellite" :size="1" />{{ t('Your exact field: each value is a 2 km cell.') }}</li>
          <li class="flex gap-2"><PixelIcon name="flat" :size="1" />{{ t('"More rain" or "less rain" alone: my model leans on last month\'s soil water and barely reacts to rain by itself, so I only offer the El Niño and dry-months cases.') }}</li>
        </ul>
      </HudCard>
    </template>
  </SlideFrame>
</template>
