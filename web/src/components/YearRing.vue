<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'
import { CROP, MONTHS, M1 } from '../content.js'
import { useTween } from '../lib/tween.js'

const props = defineProps({ cal: String, score: Number, risks: Array, month: Number, showRisks: Boolean })
const arc = d3.arc().innerRadius(62).outerRadius(88).padAngle(0.025).cornerRadius(3)
const segs = computed(() => props.cal.split('').map((k, i) => ({
  k, d: arc({ startAngle: i / 12 * Math.PI * 2, endAngle: (i + 1) / 12 * Math.PI * 2 }),
  a: (i + 0.5) / 12 * Math.PI * 2,
})))
const RISK = [['heat', '#D9480F'], ['rain', '#1D5FA8'], ['dry', '#A9772E'], ['frost', '#7FC8F8']]
const dots = computed(() => props.risks.flatMap((rk, i) => {
  const a = (i + 0.5) / 12 * Math.PI * 2
  return RISK.filter(([k]) => rk[k]).map(([k, color], j) => ({ key: `${i}${k}`, i, color, x: Math.sin(a) * (97 + j * 8), y: -Math.cos(a) * (97 + j * 8) }))
}))
const shownScore = useTween(() => props.score, 800)
const labelFill = k => /[AL]/.test(k) ? '#FFFFFF' : k === 'B' ? 'var(--fallow-ink)' : '#14201A'
</script>

<template>
  <svg class="ring" viewBox="0 0 220 220" role="img" :aria-label="`Year calendar, fit ${score} out of 100`">
    <g transform="translate(110,110)">
      <path v-for="(s, i) in segs" :key="i" :d="s.d" class="ring-seg" :style="{ fill: CROP[s.k].color, '--i': i }"><title>{{ MONTHS[i] }}: {{ CROP[s.k].name }}</title></path>
      <text v-for="(s, i) in segs" :key="'t' + i" :x="(Math.sin(s.a) * 75).toFixed(1)" :y="(-Math.cos(s.a) * 75 + 4).toFixed(1)"
            text-anchor="middle" class="ring-m" :style="{ fill: labelFill(s.k) }" aria-hidden="true">{{ M1[i] }}</text>
      <g class="risk-dots" :class="{ on: showRisks }">
        <circle v-for="d in dots" :key="d.key" :cx="d.x.toFixed(1)" :cy="d.y.toFixed(1)" r="3.2" :fill="d.color" :style="{ '--i': d.i }" />
      </g>
      <line x1="0" y1="-46" x2="0" y2="-58" class="ring-mark" :style="{ transform: `rotate(${(month + 0.5) * 30}deg)` }" />
      <text text-anchor="middle" y="6" class="ring-score">{{ Math.round(shownScore) }}</text>
      <text text-anchor="middle" y="26" class="ring-of">OUT OF 100</text>
    </g>
  </svg>
</template>
