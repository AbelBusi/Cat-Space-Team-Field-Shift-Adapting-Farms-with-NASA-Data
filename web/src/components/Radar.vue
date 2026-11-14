<script setup>
import { computed } from 'vue'
import { CRIT } from '../content.js'
import { useTween } from '../lib/tween.js'

const props = defineProps({ base: Object, pick: Object })
const C = 150, R = 100, n = CRIT.length
const pt = (i, v) => { const a = -Math.PI / 2 + i / n * Math.PI * 2; return [C + Math.cos(a) * R * v / 5, C + Math.sin(a) * R * v / 5] }
const poly = sc => CRIT.map((c, i) => pt(i, sc[c.k]).join(',')).join(' ')
const grid = [1, 2, 3, 4, 5].map(lv => CRIT.map((c, i) => pt(i, lv).join(',')).join(' '))
const axes = CRIT.map((c, i) => ({ end: pt(i, 5), label: pt(i, 6.4), text: c.label }))
const pickTween = useTween(() => props.pick)
const pickPoly = computed(() => poly(pickTween.value))
</script>

<template>
  <svg class="radar" viewBox="-30 0 360 300" role="img" aria-label="Five criteria compared with your current rotation">
    <polygon v-for="(g, i) in grid" :key="i" :points="g" class="radar-grid" />
    <g v-for="a in axes" :key="a.text">
      <line :x1="C" :y1="C" :x2="a.end[0]" :y2="a.end[1]" class="radar-grid" />
      <text :x="a.label[0]" :y="a.label[1] + 4" text-anchor="middle" class="radar-label">{{ a.text }}</text>
    </g>
    <polygon :points="poly(base)" class="radar-base" />
    <polygon :points="pickPoly" class="radar-pick" />
  </svg>
</template>
