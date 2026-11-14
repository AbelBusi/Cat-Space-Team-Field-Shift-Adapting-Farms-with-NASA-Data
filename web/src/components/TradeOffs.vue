<script setup>
import PixelIcon from './PixelIcon.vue'
import { CRIT } from '../content.js'
import { PAL } from '../lib/palette.js'
import { state } from '../store.js'

// Today's rotation vs the chosen one, topic by topic: five squares each, and an arrow that says better or worse.
defineProps({ base: Object, pick: Object })
const arrow = (a, b) => b > a ? ['up', PAL.teal, 'better'] : b < a ? ['down', PAL.ember, 'worse'] : ['flat', PAL.muted, 'same']
</script>

<template>
  <div class="trade-rows">
    <div v-for="c in CRIT" :key="c.k" class="tr-row">
      <span class="tr-label">{{ t(c.label) }}</span>
      <template v-if="state.mode === 'pro'">
        <span class="tr-pips" :aria-label="`Today ${base[c.k]} of 5`"><i v-for="n in 5" :key="n" :class="{ on: n <= base[c.k] }" /></span>
        <span class="tr-pips pick" :aria-label="`Chosen ${pick[c.k]} of 5`"><i v-for="n in 5" :key="n" :class="{ on: n <= pick[c.k] }" /></span>
      </template>
      <span v-else class="tr-word" :style="{ color: arrow(base[c.k], pick[c.k])[1] }">{{ t({ better: 'Better', worse: 'Worse', same: 'Same' }[arrow(base[c.k], pick[c.k])[2]]) }}</span>
      <PixelIcon :name="arrow(base[c.k], pick[c.k])[0]" :color="arrow(base[c.k], pick[c.k])[1]" :size="1" :label="arrow(base[c.k], pick[c.k])[2]" />
    </div>
  </div>
</template>
