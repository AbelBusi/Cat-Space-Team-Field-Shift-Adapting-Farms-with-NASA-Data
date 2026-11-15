<script setup>
import { computed } from 'vue'
import { LINE_ICONS } from '../lib/lineIcons.js'

// One icon of Field Shift's own animated line set (lib/lineIcons.js). The component keeps its old name because every
// screen uses it; since the redesign the only pixel art left is Sprout.
// size: 1 = 18 px, 2 = 36 px, 3 = 54 px. color: replaces the stroke (trend arrows say good or bad with it).
const props = defineProps({ name: { type: String, required: true }, size: { type: Number, default: 2 }, color: String, label: String })
const inner = computed(() => LINE_ICONS[props.name] ?? LINE_ICONS.flat)
</script>

<template>
  <svg class="ln-icon px-icon" viewBox="0 0 24 24" :width="18 * size" :height="18 * size" :style="color ? { color } : null"
       :role="label ? 'img' : null" :aria-label="label" :aria-hidden="label ? null : 'true'" v-html="inner" />
</template>
