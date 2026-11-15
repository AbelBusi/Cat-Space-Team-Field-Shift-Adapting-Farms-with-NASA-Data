<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { tour, endTour } from '../lib/tour.js'
import { state } from '../store.js'

// The tutorial spotlight: four veils around the lit part (clicks inside it still work), a HUD frame on it.
// The veil follows the target every frame, so it stays right while panels animate or the page resizes.
const box = ref(null)
let raf = 0
function follow() {
  const el = tour.target && document.querySelector(`[data-tour="${tour.target}"]`)
  if (el) {
    const r = el.getBoundingClientRect(), p = 6
    box.value = { x: Math.max(0, r.left - p), y: Math.max(0, r.top - p), w: r.width + 2 * p, h: r.height + 2 * p }
  }
  raf = requestAnimationFrame(follow)
}
watch(() => state.stage, () => { if (tour.active) endTour() })   // a new screen has other parts: the tour ends
watch(() => tour.active, on => { cancelAnimationFrame(raf); if (on) follow(); else box.value = null }, { immediate: true })
onBeforeUnmount(() => cancelAnimationFrame(raf))
const onKey = e => { if (tour.active && e.key === 'Escape') endTour() }
addEventListener('keydown', onKey)
onBeforeUnmount(() => removeEventListener('keydown', onKey))
</script>

<template>
  <!-- The veil sits under Sprout's panel (z-50) and over the top bar (z-40); the frame sits over everything. -->
  <div v-if="tour.active && box" class="tour pointer-events-none fixed inset-0 z-[45] print:hidden" aria-hidden="true">
    <div class="veil pointer-events-auto" :style="{ left: 0, top: 0, width: '100%', height: box.y + 'px' }" />
    <div class="veil pointer-events-auto" :style="{ left: 0, top: box.y + box.h + 'px', width: '100%', bottom: 0 }" />
    <div class="veil pointer-events-auto" :style="{ left: 0, top: box.y + 'px', width: box.x + 'px', height: box.h + 'px' }" />
    <div class="veil pointer-events-auto" :style="{ left: box.x + box.w + 'px', top: box.y + 'px', right: 0, height: box.h + 'px' }" />
  </div>
  <div v-if="tour.active && box" class="pointer-events-none fixed inset-0 z-[60] print:hidden" aria-hidden="true">
    <div class="hud spot" :style="{ left: box.x + 'px', top: box.y + 'px', width: box.w + 'px', height: box.h + 'px' }" />
  </div>
</template>

<style scoped>
.veil { position: absolute; background: color-mix(in srgb, var(--bg) 82%, transparent); transition: all .35s ease; }
.spot { position: absolute; border-color: var(--teal); transition: all .35s ease; animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { border-color: var(--fire); } }
</style>
