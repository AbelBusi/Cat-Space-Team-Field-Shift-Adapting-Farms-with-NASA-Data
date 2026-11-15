<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { state } from '../store.js'
import { proj, projError, gridImage, colorScale, useAheadMap, SCENARIOS } from '../lib/projections.js'
import { t } from '../i18n.js'

// Where the deep soil should keep the most water in the dry months (Jul–Nov 2026), district by district, in the chosen
// "what if". One story: the first district is the campfire bar, the rest turquoise. Water is not the harvest.
const DRY = [6, 7, 8, 9, 10]   // Jul..Nov in the 12 projected months
useAheadMap(d => {
  const arr = d.soil_water[state.ahead.scen].median, n = 12, sc = d.meta.scale
  return gridImage(i => {
    const v = DRY.map(k => arr[i * n + k]).filter(x => x != null)
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length / sc : null
  }, colorScale('soil_water'))
})
// Districts in view: the province of the open district, or the whole department in free mode.
const inView = computed(() => {
  if (!proj.value) return []
  if (state.area?.kind !== 'district') return null
  const d = proj.value, prov = d.provinces.indexOf(state.area.province)
  return new Set(d.cells.district.filter((x, i) => x >= 0 && d.cells.province[i] === prov).map(x => d.districts[x]))
})
const rows = computed(() => {
  if (!proj.value) return []
  const all = proj.value.district_summary.filter(r => r.scenario === state.ahead.scen && r.cells >= 3 && (!inView.value || inView.value.has(r.district)))
  return all.sort((a, b) => b.dry_season_soil_water - a.dry_season_soil_water)
})
const top = computed(() => rows.value[0]?.dry_season_soil_water || 1)
const low = computed(() => Math.min(...rows.value.map(r => r.dry_season_soil_water)))
const greenest = computed(() => [...rows.value].filter(r => r.q3q4_ndvi != null).sort((a, b) => b.q3q4_ndvi - a.q3q4_ndvi).slice(0, 5))
const share = v => 0.15 + 0.85 * (v - low.value) / Math.max(1, top.value - low.value)
const sc = computed(() => proj.value?.meta.scale ?? 1000)
const scenLabel = computed(() => t(SCENARIOS.find(x => x.id === state.ahead.scen).label))
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The projections file is not available ({e}).', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <HudCard v-else :title="t('Most water in the deep soil, Jul–Nov 2026')">
        <p class="text-xs text-muted">{{ inView ? t('Districts of {p} · {s}', { p: state.area.province, s: scenLabel }) : t('All districts of Lambayeque · {s}', { s: scenLabel }) }}</p>
        <ol class="flex flex-col gap-1 text-xs">
          <li v-for="(r, i) in rows.slice(0, 8)" :key="r.district" class="grid grid-cols-[7.5rem_minmax(0,1fr)_auto] items-center gap-2">
            <span class="truncate" :class="r.district === state.area?.name ? 'text-fire' : ''">{{ i + 1 }}. {{ r.district }}</span>
            <i class="block h-2.5" :class="i === 0 ? 'bg-fire' : 'bg-teal/35'" :style="{ width: share(r.dry_season_soil_water) * 100 + '%' }" />
            <span v-if="state.mode === 'pro'" class="font-mono text-muted">{{ (r.dry_season_soil_water / sc).toFixed(3) }}</span>
          </li>
        </ol>
        <p v-if="rows.length > 8" class="text-xs text-muted">{{ t('…and {n} more districts. The map shows every 2 km cell.', { n: rows.length - 8 }) }}</p>
      </HudCard>
    </template>

    <template #right>
      <HudCard v-if="proj && greenest.length" :title="t('Greenest in the second half of 2026')">
        <ol class="flex flex-col gap-1 text-xs">
          <li v-for="(r, i) in greenest" :key="r.district" class="flex items-center gap-2">
            <PixelIcon :name="r.q3q4_ndvi / sc >= 0.4 ? 'plant_ok' : r.q3q4_ndvi / sc >= 0.2 ? 'plant_thirsty' : 'bare'" :size="1" />
            <span class="flex-1 truncate">{{ i + 1 }}. {{ r.district }}</span>
            <span v-if="state.mode === 'pro'" class="font-mono text-muted">NDVI {{ (r.q3q4_ndvi / sc).toFixed(2) }}</span>
          </li>
        </ol>
      </HudCard>
      <HudCard :title="t('Water is not the harvest')">
        <p class="text-xs">{{ t('These are the places where the model expects the deep soil to stay wettest. A good harvest also depends on the crop, irrigation, soil care and the market. We have no harvest data yet, so Sprout does not rank crops or profits.') }}</p>
        <p class="text-xs text-muted">{{ t('Change the "what if" in the previous topic to see how the ranking moves.') }}</p>
      </HudCard>
    </template>
  </SlideFrame>
</template>
