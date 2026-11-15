<script setup>
import { computed } from 'vue'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { state } from '../store.js'
import { proj, projError, gridImage, colorScale, useAheadMap, cellAt, SCENARIOS } from '../lib/projections.js'
import { inRings } from '../lib/admin.js'
import PLACES from '../data/lambayeque_places.json'
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
// The open district first: its place in the province, and its own wettest and driest corners, named by their towns.
const dryValue = i => {
  const d = proj.value, arr = d.soil_water[state.ahead.scen].median
  const v = DRY.map(k => arr[i * 12 + k]).filter(x => x != null)
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length / d.meta.scale : null
}
const mine = computed(() => {
  if (!proj.value || state.area?.kind !== 'district') return null
  const k = rows.value.findIndex(r => r.district === state.area.name)
  if (k < 0) return null
  const vals = rows.value.map(r => r.dry_season_soil_water).sort((a, b) => a - b), mid = vals[Math.floor(vals.length / 2)]
  const v = rows.value[k].dry_season_soil_water, d = (v - mid) / sc.value
  return { rank: k + 1, of: rows.value.length, value: v / sc.value, word: d > 0.01 ? 'wetter' : d < -0.01 ? 'drier' : 'middle' }
})
const corners = computed(() => {
  if (!mine.value) return null
  const seen = new Set(), out = []
  for (const [name, lat, lon] of PLACES) {
    if (!inRings(lat, lon, state.area.rings)) continue
    const i = cellAt(lat, lon)
    if (i < 0 || seen.has(i)) continue
    const v = dryValue(i)
    if (v == null) continue
    seen.add(i); out.push({ name, v })
  }
  out.sort((a, b) => b.v - a.v)
  return out.length >= 2 ? { wet: out.slice(0, 3), dry: out.slice(-2).reverse().filter(x => !out.slice(0, 3).includes(x)) } : null
})
const MINE_WORD = { wetter: 'Keeps more water than most districts of {p}', drier: 'Keeps less water than most districts of {p}', middle: 'Keeps about as much water as the middle of {p}' }
const scenLabel = computed(() => t(SCENARIOS.find(x => x.id === state.ahead.scen).label))
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard v-if="projError"><p class="text-muted">{{ t('The model service is not available ({e}). Start ml-api and reload.', { e: projError }) }}</p></HudCard>
      <HudCard v-else-if="!proj"><p class="text-muted">{{ t('Loading the projections…') }}</p></HudCard>
      <template v-else>
        <HudCard data-focus="my-district" v-if="mine" :title="t('{d} in the dry months, Jul–Nov 2026', { d: state.area.name })">
          <div class="flex items-center gap-3">
            <PixelIcon :name="mine.word === 'wetter' ? 'soil_wet' : mine.word === 'drier' ? 'soil_dry' : 'soil_moist'" :size="3" />
            <div>
              <div class="text-base"><span class="text-fire">{{ t('Place {r} of {n}', { r: mine.rank, n: mine.of }) }}</span> {{ t('in {p}', { p: state.area.province }) }}</div>
              <div class="text-xs text-muted">{{ t(MINE_WORD[mine.word], { p: state.area.province }) }}<span v-if="state.mode === 'pro'" class="font-mono"> · {{ mine.value.toFixed(3) }} m³/m³</span></div>
            </div>
          </div>
          <div v-if="corners" class="grid grid-cols-2 gap-2 border-t border-line pt-2 text-xs">
            <div>
              <div class="label !text-[10px]">{{ t('More water near') }}</div>
              <ul><li v-for="c in corners.wet" :key="c.name" class="flex items-center gap-1"><PixelIcon name="drop" :size="1" />{{ c.name }}</li></ul>
            </div>
            <div v-if="corners.dry.length">
              <div class="label !text-[10px]">{{ t('Less water near') }}</div>
              <ul><li v-for="c in corners.dry" :key="c.name" class="flex items-center gap-1"><PixelIcon name="soil_dry" :size="1" />{{ c.name }}</li></ul>
            </div>
          </div>
        </HudCard>
        <HudCard data-focus="water-ranking" :title="t('Most water in the deep soil, Jul–Nov 2026')">
          <p class="text-xs text-muted">{{ inView ? t('Districts of {p} · {s}', { p: state.area.province, s: scenLabel }) : t('All districts of Lambayeque · {s}', { s: scenLabel }) }}</p>
          <ol class="flex flex-col gap-1 text-xs">
            <template v-for="(r, i) in rows" :key="r.district">
              <li v-if="i < 8 || r.district === state.area?.name" class="grid grid-cols-[7.5rem_minmax(0,1fr)_auto] items-center gap-2">
                <span class="truncate" :class="r.district === state.area?.name ? 'text-fire' : ''">{{ i + 1 }}. {{ r.district }}</span>
                <i class="block h-2.5" :class="r.district === state.area?.name || (!mine && i === 0) ? 'bg-fire' : 'bg-teal/35'" :style="{ width: share(r.dry_season_soil_water) * 100 + '%' }" />
                <span v-if="state.mode === 'pro'" class="font-mono text-muted">{{ (r.dry_season_soil_water / sc).toFixed(3) }}</span>
              </li>
              <li v-if="i === 8 && mine && mine.rank > 9" class="text-muted">…</li>
            </template>
          </ol>
          <p v-if="rows.length > 8" class="text-xs text-muted">{{ t('The map shows every 2 km cell of the district.') }}</p>
        </HudCard>
      </template>
    </template>

    <template #right>
      <HudCard v-if="proj && greenest.length" :title="t('Greenest in the second half of 2026')">
        <ol class="flex flex-col gap-1 text-xs">
          <li v-for="(r, i) in greenest" :key="r.district" class="flex items-center gap-2">
            <PixelIcon :name="r.q3q4_ndvi / sc >= 0.4 ? 'plant_ok' : r.q3q4_ndvi / sc >= 0.2 ? 'plant_thirsty' : 'bare'" :size="1" />
            <span class="flex-1 truncate" :class="r.district === state.area?.name ? 'text-fire' : ''">{{ i + 1 }}. {{ r.district }}</span>
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
