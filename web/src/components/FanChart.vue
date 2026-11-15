<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'
import { PAL } from '../lib/palette.js'
import { t } from '../i18n.js'

// A projection over time: the middle line, the band where most tries landed, the usual value (dashed) and the point
// where the projection stops beating "a typical year" (useful lead). One story: the chosen period is the campfire dot.
const props = defineProps({
  series: Array,        // [{ median: [], low?: [], high?: [], color, label }]
  usual: Array,         // usual value per period, or null
  at: Number,           // highlighted period
  useful: Number,       // periods with real skill; after them the chart is dimmed
  labels: Array,        // one short label per period
  digits: { type: Number, default: 2 },
  unit: String,
})
const emit = defineEmits(['pick'])
const W = 330, H = 150, M = { l: 34, r: 8, t: 10, b: 20 }
const n = computed(() => props.labels.length)
const x = computed(() => d3.scaleLinear().domain([0, n.value - 1]).range([M.l, W - M.r]))
const y = computed(() => {
  const vals = props.series.flatMap(s => [...s.median, ...(s.low || []), ...(s.high || [])]).concat(props.usual || []).filter(v => v != null)
  const [a, b] = d3.extent(vals), pad = (b - a) * 0.12 || 0.01
  return d3.scaleLinear().domain([a - pad, b + pad]).nice(4).range([H - M.b, M.t])
})
const ok = v => v != null
const line = arr => d3.line().defined(ok).x((_, i) => x.value(i)).y(v => y.value(v)).curve(d3.curveMonotoneX)(arr)
const band = s => s.low && s.high ? d3.area().defined((_, i) => ok(s.low[i]) && ok(s.high[i])).x((_, i) => x.value(i))
  .y0((_, i) => y.value(s.low[i])).y1((_, i) => y.value(s.high[i])).curve(d3.curveMonotoneX)(s.median) : null
const ticks = computed(() => y.value.ticks(4))
const cut = computed(() => props.useful != null && props.useful < n.value ? (x.value(props.useful - 1) + x.value(props.useful)) / 2 : null)
const hit = computed(() => Array.from({ length: n.value }, (_, i) => ({ i, x0: i ? (x.value(i - 1) + x.value(i)) / 2 : M.l - 6, x1: i < n.value - 1 ? (x.value(i) + x.value(i + 1)) / 2 : W })))
const main = computed(() => props.series[props.series.length - 1])
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img" :aria-label="t('Projection chart')">
    <g v-for="v in ticks" :key="v">
      <line :x1="M.l" :x2="W - M.r" :y1="y(v)" :y2="y(v)" :stroke="PAL.line" />
      <text :x="M.l - 4" :y="y(v) + 3" text-anchor="end" class="bar-axis">{{ v.toFixed(digits) }}</text>
    </g>
    <rect v-if="cut" :x="cut" :y="M.t" :width="W - M.r - cut" :height="H - M.b - M.t" :fill="PAL.bg" fill-opacity="0.45" />
    <line v-if="cut" :x1="cut" :x2="cut" :y1="M.t" :y2="H - M.b" :stroke="PAL.muted" stroke-dasharray="2 3" />
    <text v-if="cut" :x="Math.min(cut + 4, W - 70)" :y="M.t + 9" class="bar-axis">{{ t('typical year →') }}</text>
    <path v-if="usual" :d="line(usual)" fill="none" :stroke="PAL.muted" stroke-dasharray="4 3" />
    <template v-for="s in series" :key="s.label">
      <path v-if="band(s)" :d="band(s)" :fill="s.color" fill-opacity="0.16" />
      <path :d="line(s.median)" fill="none" :stroke="s.color" stroke-width="2" />
    </template>
    <circle v-if="ok(main.median[at])" :cx="x(at)" :cy="y(main.median[at])" r="4.5" :fill="PAL.fire" :stroke="PAL.bg" stroke-width="1.5" />
    <text v-for="(l, i) in labels" :key="i" :x="x(i)" :y="H - 6" text-anchor="middle" class="bar-axis" :fill="i === at ? PAL.fire : null">{{ l }}</text>
    <rect v-for="h in hit" :key="'h' + h.i" :x="h.x0" :y="0" :width="h.x1 - h.x0" :height="H" fill="transparent" class="cursor-pointer" @click="emit('pick', h.i)" />
  </svg>
</template>
