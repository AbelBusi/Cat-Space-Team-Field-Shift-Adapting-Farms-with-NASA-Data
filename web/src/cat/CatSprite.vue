<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { PALETTE, SIZE, BODY, ANTENNAE, FACES } from './sprites.js'

// Sprout, drawn from pixel runs (see sprites.js). It blinks, its tail sways, its mouth moves while it talks, and the
// whole cat squashes a little when its mood changes.
// full: the whole sitting cat; otherwise a bust (head and chest) for small spots. pose: 'sit' or 'wave' (a paw up).
const props = defineProps({
  mood: { type: String, default: 'neutral' },
  talking: Boolean,
  size: { type: Number, default: 96 },
  full: Boolean,
  pose: { type: String, default: 'sit' },
})
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const f = computed(() => FACES[props.mood] || FACES.neutral)
const mouthOpen = ref(false), blinking = ref(false), wag = ref(false)

const body = computed(() => BODY[`${props.pose === 'wave' ? 'wave' : 'sit'}_${wag.value ? 'wag' : 'up'}`])
const face = computed(() => blinking.value ? f.value.blink : props.talking && mouthOpen.value ? f.value.talk : f.value.face)
const ant = computed(() => ANTENNAE[f.value.ant])
const box = computed(() => props.full ? `0 0 ${SIZE[0]} ${SIZE[1]}` : '3 -1 38 38')

let talkTimer, blinkTimer, wagTimer
watch(() => props.talking, on => {
  clearInterval(talkTimer)
  mouthOpen.value = false
  if (on) talkTimer = setInterval(() => (mouthOpen.value = !mouthOpen.value), 130)
}, { immediate: true })
function scheduleBlink() {
  blinkTimer = setTimeout(() => {
    blinking.value = true
    setTimeout(() => { blinking.value = false; scheduleBlink() }, 140)
  }, 2200 + Math.random() * 2800)
}
onMounted(() => {
  scheduleBlink()
  if (props.full && !reduce) wagTimer = setInterval(() => (wag.value = !wag.value), 700)
})
onBeforeUnmount(() => { clearInterval(talkTimer); clearTimeout(blinkTimer); clearInterval(wagTimer) })
</script>

<template>
  <svg class="cat" :class="{ talking }" :width="size" :height="full ? size * SIZE[1] / SIZE[0] : size" :viewBox="box"
       shape-rendering="crispEdges" role="img" :aria-label="t('Sprout the alien cat, looking ' + mood)">
    <g class="cat-body" :key="mood">
      <rect v-for="[x, y, w, c] in body" :key="`b${x},${y}`" :x="x" :y="y" :width="w" height="1" :fill="PALETTE[c]" />
      <rect v-for="[x, y, w, c] in face" :key="`f${x},${y},${c}`" :x="x" :y="y" :width="w" height="1" :fill="PALETTE[c]" />
    </g>
    <g class="cat-ant"><rect v-for="[x, y, w, c] in ant" :key="`a${x},${y}`" :x="x" :y="y" :width="w" height="1" :fill="PALETTE[c]" /></g>
  </svg>
</template>
