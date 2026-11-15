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
const soilIcon = computed(() => props.value == null ? 'soil_moist' : props.value < 20 ? 'soil_dry' : props.value < 60 ? 'soil_moist' : 'soil_wet')
const plantIcon = computed(() => props.value == null ? 'seed' : props.value < 0.2 ? 'bare' : props.value < 0.4 ? 'plant_thirsty' : 'plant_ok')
</script>

<template>
  <!-- Thermometer: the column rises and takes the colour of the heat -->
  <svg v-if="kind === 'heat'" class="instrument ln-icon" viewBox="0 0 20 48" :width="10 * size" :height="24 * size" aria-hidden="true">
    <path d="M7 5a3 3 0 0 1 6 0v24.300a6.200 6.200 0 1 1-6 0z" />
    <path stroke="var(--muted)" d="M15.500 9h2.500M15.500 15h2.500M15.500 21h2.500M15.500 27h2.500" />
    <line x1="10" y1="34" x2="10" :y2="31 - frac * 24" :stroke="tempColor(frac)" stroke-width="3" />
    <circle cx="10" cy="35" r="3.400" :fill="tempColor(frac)" :stroke="tempColor(frac)" />
  </svg>
  <!-- Rain gauge: the water level, with a small wave on top -->
  <svg v-else-if="kind === 'rain'" class="instrument ln-icon" viewBox="0 0 20 48" :width="10 * size" :height="24 * size" aria-hidden="true">
    <rect x="5.800" :y="41 - frac * 34" width="8.400" :height="frac * 34" fill="var(--teal)" fill-opacity=".55" stroke="none" />
    <defs><clipPath id="gauge-glass"><rect x="5.800" y="4" width="8.400" height="38" /></clipPath></defs>
    <g v-if="frac > 0.03" clip-path="url(#gauge-glass)"><g class="i-wave"><path class="c-teal" :d="`M-4 ${41 - frac * 34}c1.700-1.600 3.300-1.600 5 0s3.300 1.600 5 0 3.300-1.600 5 0 3.300 1.600 5 0 3.300-1.600 5 0 3.300 1.600 5 0`" /></g></g>
    <path d="M2.500 4h15M5 4v36a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V4" />
    <path stroke="var(--muted)" d="M5 12h3M5 20h3M5 28h3M5 36h3" />
  </svg>
  <PixelIcon v-else-if="kind === 'soil'" :name="soilIcon" :size="size" />
  <PixelIcon v-else-if="kind === 'veg'" :name="plantIcon" :size="size" />
  <PixelIcon v-else-if="kind === 'water'" :name="value > 0.3 ? 'up' : value < -0.3 ? 'down' : 'flat'" :color="value < -0.3 ? PAL.ember : PAL.teal" :size="size" />
  <PixelIcon v-else name="flat" :size="size" />
</template>
