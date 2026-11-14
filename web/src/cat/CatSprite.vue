<script>
import { PALETTE, BASE, ANTENNAE, EXPRESSIONS } from './sprites.js'

// Rows of characters → one <rect> per horizontal run of the same color.
function runs(rows) {
  const out = []
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length;) {
      let w = 1
      while (row[x + w] === row[x]) w++
      if (row[x] !== '.') out.push({ x, y, w, fill: PALETTE[row[x]] })
      x += w
    }
  })
  return out
}
const cache = new Map()
const layer = rows => cache.get(rows) || cache.set(rows, runs(rows)).get(rows)
const BASE_RUNS = runs(BASE)
</script>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  mood: { type: String, default: 'neutral' },
  talking: Boolean,
  size: { type: Number, default: 96 },
})
const expr = computed(() => EXPRESSIONS[props.mood] || EXPRESSIONS.neutral)
const mouthOpen = ref(false)
const blinking = ref(false)

const face = computed(() => {
  const e = expr.value
  if (blinking.value && e.blink) return layer(e.blink)
  return layer(props.talking && mouthOpen.value ? e.talk : e.face)
})
const ant = computed(() => layer(ANTENNAE[expr.value.ant]))

let talkTimer, blinkTimer
watch(() => props.talking, on => {
  clearInterval(talkTimer)
  mouthOpen.value = false
  if (on) talkTimer = setInterval(() => (mouthOpen.value = !mouthOpen.value), 120)
}, { immediate: true })

function scheduleBlink() {
  blinkTimer = setTimeout(() => {
    blinking.value = true
    setTimeout(() => { blinking.value = false; scheduleBlink() }, 130)
  }, 2400 + Math.random() * 2800)
}
onMounted(scheduleBlink)
onBeforeUnmount(() => { clearInterval(talkTimer); clearTimeout(blinkTimer) })
</script>

<template>
  <svg class="cat" :class="{ talking }" :width="size" :height="size" viewBox="0 -1 32 33"
       shape-rendering="crispEdges" role="img" :aria-label="`Sprout the alien cat, looking ${mood}`">
    <g class="cat-ant"><rect v-for="r in ant" :key="`${r.x},${r.y}`" :x="r.x" :y="r.y" :width="r.w" height="1" :fill="r.fill" /></g>
    <g class="cat-body" :key="mood">
      <rect v-for="r in BASE_RUNS" :key="`b${r.x},${r.y}`" :x="r.x" :y="r.y" :width="r.w" height="1" :fill="r.fill" />
      <rect v-for="r in face" :key="`f${r.x},${r.y},${r.fill}`" :x="r.x" :y="r.y" :width="r.w" height="1" :fill="r.fill" />
    </g>
  </svg>
</template>
