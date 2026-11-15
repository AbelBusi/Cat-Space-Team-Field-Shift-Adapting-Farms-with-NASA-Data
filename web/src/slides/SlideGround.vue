<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelGlobe from '../components/PixelGlobe.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { LAYERS } from '../content.js'
import { state, db, climate, placeLabel, cell, mapApi } from '../store.js'
import { t } from '../i18n.js'
import { gridCells } from '../lib/nasa.js'

// What each satellite measures and how often, with a pixel icon of what it sees.
const SOURCE = {
  power: { icon: 'sun', text: 'Climate from satellites and models, every month since 1981: heat, rain and soil wetness.' },
  imerg: { icon: 'rain', text: 'Rain seen from space by the GPM satellites, every 30 minutes. Here: the 2001–2024 average.' },
  smap: { icon: 'drop', text: 'Water in the top 5 cm of soil, measured with microwaves every 2–3 days, even through clouds.' },
  modis: { icon: 'plant_ok', text: 'How green the plants are, every 16 days: sharp enough to see large fields.' },
  hls: { icon: 'satellite', text: 'Landsat and Sentinel-2 together, every 2–3 days: sharp enough to see inside a small field.' },
}
const used = id => id === 'power' || id === 'modis' || (id === 'imerg' && !!cell.value)
import { formatArea, formatShortDate } from '../lib/geo.js'

// Where you are, the ground under it, the last 30 days, and how sharp each satellite sees compared with your field.
const L = computed(() => LAYERS[state.layer])
const cells = computed(() => state.point ? gridCells(state.point.lat, state.point.lon) : [])
const fieldHa = computed(() => state.parcel ? state.parcel.areaM2 / 10_000 : 3)
const fieldLabel = computed(() => state.parcel ? t('your {area} field', { area: formatArea(state.parcel.areaM2) }) : t('a 3 ha field'))
const lens = computed(() => {
  const pxHa = L.value.px * L.value.px * 100
  if (pxHa < fieldHa.value) return { side: Math.max(3, 56 * Math.sqrt(pxHa / fieldHa.value)), fine: true, n: Math.max(1, Math.round(fieldHa.value / pxHa)), m: Math.round(L.value.px * 1000) }
  return { side: Math.max(2, 56 * Math.sqrt(fieldHa.value / pxHa)), fine: false, n: d3.format(',')(Math.max(1, Math.round(pxHa / fieldHa.value))), km: L.value.px }
})
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard :title="t('Your place')">
        <div class="flex items-center gap-3">
          <PixelGlobe :lat="state.point?.lat" :lon="state.point?.lon" :size="72" />
          <div class="min-w-0">
            <Transition name="flip" mode="out-in"><div :key="state.point ? placeLabel(state.point) : ''" class="truncate font-display text-xl font-semibold">{{ state.point ? placeLabel(state.point) : t('Pick a place') }}</div></Transition>
            <div class="font-mono text-xs text-teal">{{ climate?.label() || t(db.error ? 'No data' : 'Reading the climate…') }}</div>
            <div v-if="state.point" class="font-mono text-xs text-muted">{{ state.point.lat }}, {{ state.point.lon }}</div>
          </div>
        </div>
      </HudCard>
      <HudCard v-if="cell && cell.land > 0" :title="cell.n > 1 ? t('Ground · NASADEM 30 m, average of {n} squares', { n: cell.n }) : t('Ground · NASADEM 30 m, cell mean')">
        <div class="flex items-center gap-3">
          <PixelIcon :name="cell.slope < 2 ? 'soil_moist' : cell.slope < 6 ? 'soil_dry' : 'up'" :size="3" />
          <div>
            <div class="font-display text-lg font-semibold">{{ state.mode === 'pro' ? t('{m} m above sea · slope {deg}°', { m: cell.elev, deg: cell.slope }) : t(cell.slope < 2 ? 'Flat ground' : cell.slope < 6 ? 'Gentle slope' : 'Steep ground') }}</div>
            <div class="text-muted">{{ t(cell.slope < 2 ? 'Low erosion risk.' : cell.slope < 6 ? 'Bare soil can wash away in heavy rain.' : 'High erosion risk when the soil is bare: keep it covered.') }}</div>
          </div>
        </div>
      </HudCard>
      <HudCard :title="t('Last 30 days')">
        <p v-if="db.recent">
          <span class="font-mono text-xs text-muted">{{ formatShortDate(db.recent.from) }} – {{ formatShortDate(db.recent.to) }}</span><br>
          {{ t('{mm} mm of rain on {days} days, {c} °C on average.', { mm: db.recent.rainMm.toFixed(1), days: db.recent.rainyDays, c: db.recent.tempC.toFixed(1) }) }}
        </p>
        <p v-else class="text-muted">{{ t(db.recentError ? 'No data' : 'Reading the last 30 days…') }}</p>
      </HudCard>
    </template>

    <template #right>
      <HudCard :title="t('How sharp does it see?')">
        <div class="flex items-center gap-3">
          <div class="flex size-14 shrink-0 items-center justify-center border border-line" aria-hidden="true"><span class="block bg-teal transition-all duration-500" :style="{ width: Math.min(56, lens.side) + 'px', height: Math.min(56, lens.side) + 'px' }" /></div>
          <p v-if="lens.fine">{{ t('For {layer} one pixel is about {m} m wide. About {n} pixels fit in {field}, so it sees inside the field.', { layer: t(L.name).toLowerCase(), m: lens.m, n: lens.n, field: fieldLabel }) }}</p>
          <p v-else>{{ t('For {layer} one pixel is about {km} km wide. {field} fits {n} times in it: it describes the region, not the exact field.', { layer: t(L.name).toLowerCase(), km: lens.km, n: lens.n, field: fieldLabel[0].toUpperCase() + fieldLabel.slice(1) }) }}</p>
        </div>
      </HudCard>
      <HudCard :title="t('The square of each satellite')">
        <p class="text-xs text-muted">{{ t('Each satellite sees the ground in squares of its own size. Tap one to see its square on the map.') }}</p>
        <button v-for="c in cells" :key="c.id" type="button" class="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-2.5 border-l-2 py-1 pl-2 text-left transition-colors hover:bg-teal/10"
                :style="{ borderColor: c.color }" :title="t('Zoom to this square')" @click="mapApi.zoomTo(c)">
          <span class="row-span-2 flex size-9 items-center justify-center border border-line bg-bg/60"><PixelIcon :name="SOURCE[c.id].icon" :size="2" /></span>
          <span class="flex flex-wrap items-baseline gap-x-2">
            <b>{{ c.name }}</b><span class="font-mono text-xs text-muted">{{ c.size }}</span>
            <span class="font-mono text-[10px] uppercase tracking-wider" :class="used(c.id) ? 'text-teal' : 'text-muted'">{{ t(used(c.id) ? 'in use' : 'planned') }}</span>
          </span>
          <span class="text-xs text-muted">{{ t(SOURCE[c.id].text) }}</span>
        </button>
      </HudCard>
    </template>
  </SlideFrame>
</template>
