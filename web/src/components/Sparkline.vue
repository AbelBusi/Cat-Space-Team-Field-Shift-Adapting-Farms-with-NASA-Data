<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'

const props = defineProps({ values: Array, domain: Array, at: Number })
const W = 96, H = 34
const x = d3.scaleLinear().domain([0, 11]).range([3, W - 3])
const y = computed(() => d3.scaleLinear().domain(props.domain).range([H - 4, 4]).clamp(true))
const ok = d => d != null   // months with no data leave a gap
const line = computed(() => d3.line().defined(ok).x((d, i) => x(i)).y(d => y.value(d)).curve(d3.curveMonotoneX)(props.values))
const area = computed(() => d3.area().defined(ok).x((d, i) => x(i)).y0(H - 2).y1(d => y.value(d)).curve(d3.curveMonotoneX)(props.values))
</script>

<template>
  <svg class="spark" :viewBox="`0 0 ${W} ${H}`" aria-hidden="true">
    <path :d="area" class="spark-area" />
    <path :key="values.join()" :d="line" class="spark-line" pathLength="1" />
    <circle v-if="ok(values[at])" r="3.5" class="spark-dot" :style="{ transform: `translate(${x(at)}px, ${y(values[at])}px)` }" />
  </svg>
</template>
