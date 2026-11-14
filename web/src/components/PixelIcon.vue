<script>
import { PIXEL_ICONS, ICON_PALETTE } from '../lib/pixelIcons.js'

// Rows of characters → one <rect> per horizontal run of the same color (same idea as Sprout's sprites).
const cache = new Map()
function runs(name) {
  if (cache.has(name)) return cache.get(name)
  const out = []
  PIXEL_ICONS[name].forEach((row, y) => {
    for (let x = 0; x < row.length;) {
      let w = 1
      while (row[x + w] === row[x]) w++
      if (row[x] !== '.') out.push({ x, y, w, c: row[x] })
      x += w
    }
  })
  cache.set(name, out)
  return out
}
</script>

<script setup>
import { computed } from 'vue'

// size: pixels per icon pixel (whole numbers keep it crisp). color: replaces the cream 'c' pixels (arrows).
const props = defineProps({ name: { type: String, required: true }, size: { type: Number, default: 2 }, color: String, label: String })
const rects = computed(() => runs(props.name))
const fill = c => c === 'c' && props.color ? props.color : ICON_PALETTE[c]
</script>

<template>
  <svg class="px-icon" viewBox="0 0 16 16" :width="16 * size" :height="16 * size" shape-rendering="crispEdges"
       :role="label ? 'img' : null" :aria-label="label" :aria-hidden="label ? null : 'true'">
    <rect v-for="r in rects" :key="`${r.x},${r.y}`" :x="r.x" :y="r.y" :width="r.w" height="1" :fill="fill(r.c)" />
  </svg>
</template>
