<script setup>
import { computed } from 'vue'
import PixelIcon from './PixelIcon.vue'
import { PAL, RAMP } from '../lib/palette.js'
import { useTween } from '../lib/tween.js'
import * as d3 from 'd3'

// Farmer-mode readings as tools a farmer knows: a thermometer, a rain gauge, a handful of soil, a plant.
// No numbers here: the level is drawn, and Sprout says it in words.
const props = defineProps({ kind: String, value: Number, domain: Array, size: { type: Number, default: 3 } })
const t = useTween(() => props.value ?? props.domain[0], 700)
const frac = computed(() => Math.max(0, Math.min(1, (t.value - props.domain[0]) / (props.domain[1] - props.domain[0]))))
const tempColor = d3.scaleLinear().domain([0, 1 / 3, 2 / 3, 1]).range(RAMP.temp)
// 10 x 24 pixel tubes; the column height is a whole number of pixels so it stays crisp.
const rows = computed(() => Math.round(frac.value * (props.kind === 'heat' ? 15 : 16)))
const soilIcon = computed(() => props.value == null ? 'soil_moist' : props.value < 20 ? 'soil_dry' : props.value < 60 ? 'soil_moist' : 'soil_wet')
const plantIcon = computed(() => props.value == null ? 'seed' : props.value < 0.2 ? 'bare' : props.value < 0.4 ? 'plant_thirsty' : 'plant_ok')
</script>

<template>
  <svg v-if="kind === 'heat'" class="instrument" viewBox="0 0 10 24" :width="10 * size" :height="24 * size" shape-rendering="crispEdges" aria-hidden="true">
    <rect x="3" y="0" width="4" height="19" :fill="PAL.line" /><rect x="4" y="1" width="2" height="17" :fill="PAL.bg" />
    <rect x="4" :y="18 - rows" width="2" :height="rows" :fill="tempColor(frac)" />
    <rect x="2" y="18" width="6" height="5" :fill="tempColor(frac)" /><rect x="3" y="23" width="4" height="1" :fill="tempColor(frac)" />
    <rect v-for="k in 3" :key="k" x="8" :y="3 + k * 4" width="2" height="1" :fill="PAL.muted" />
  </svg>
  <svg v-else-if="kind === 'rain'" class="instrument" viewBox="0 0 10 24" :width="10 * size" :height="24 * size" shape-rendering="crispEdges" aria-hidden="true">
    <rect x="0" y="0" width="10" height="2" :fill="PAL.muted" /><rect x="1" y="2" width="1" height="20" :fill="PAL.line" /><rect x="8" y="2" width="1" height="20" :fill="PAL.line" />
    <rect x="1" y="22" width="8" height="2" :fill="PAL.line" />
    <rect x="2" :y="22 - rows" width="6" :height="rows" :fill="PAL.teal" opacity=".85" /><rect v-if="rows" x="2" :y="22 - rows" width="6" height="1" fill="#BFEDE6" />
    <rect v-for="k in 4" :key="k" x="1" :y="2 + k * 4" width="3" height="1" :fill="PAL.muted" />
  </svg>
  <PixelIcon v-else-if="kind === 'soil'" :name="soilIcon" :size="size" />
  <PixelIcon v-else-if="kind === 'veg'" :name="plantIcon" :size="size" />
  <PixelIcon v-else-if="kind === 'water'" :name="value > 0.3 ? 'up' : value < -0.3 ? 'down' : 'flat'" :color="value < -0.3 ? PAL.ember : PAL.teal" :size="size" />
  <PixelIcon v-else name="flat" :size="size" />
</template>
