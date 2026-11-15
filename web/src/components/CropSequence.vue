<script setup>
import { computed } from 'vue'
import PixelIcon from './PixelIcon.vue'
import { stretches, MONTHS } from '../content.js'
import { t } from '../i18n.js'

// A rotation as its crops in order, each with its pixel icon and its months: "rice Jan–Jun → bare soil Jul–Dec".
// compact: icons only (for tight rows), with the names in the tooltip.
const props = defineProps({ cal: String, compact: Boolean })
const parts = computed(() => stretches(props.cal))
const m = i => t(MONTHS[i]).slice(0, 3)
const months = p => p.from === p.to ? m(p.from) : `${m(p.from)}–${m(p.to)}`
</script>

<template>
  <ol class="flex flex-wrap items-center" :class="compact ? 'gap-0.5' : 'gap-x-1 gap-y-1.5'" :aria-label="parts.map(p => t(p.crop.name)).join(', ')">
    <li v-for="(p, i) in parts" :key="i" class="flex items-center gap-1" :title="`${t(p.crop.name)} · ${t(MONTHS[p.from]).slice(0, 3)}–${t(MONTHS[p.to]).slice(0, 3)}`">
      <span v-if="i" class="font-mono text-xs text-muted" aria-hidden="true">›</span>
      <span class="flex items-center gap-1.5" :class="compact ? '' : 'border border-line bg-bg/50 py-0.5 pl-0.5 pr-2'">
        <span class="flex items-center justify-center" :class="{ 'opacity-50': p.key === 'B' }" :style="compact ? null : { borderBottom: `3px solid ${p.crop.color}` }"><PixelIcon :name="p.crop.icon" :size="compact ? 1 : 2" /></span>
        <span v-if="!compact" class="leading-tight">
          <span class="block text-xs font-semibold">{{ t(p.crop.name) }}</span>
          <span class="block font-mono text-[10px] text-muted">{{ months(p) }}</span>
        </span>
      </span>
    </li>
  </ol>
</template>
