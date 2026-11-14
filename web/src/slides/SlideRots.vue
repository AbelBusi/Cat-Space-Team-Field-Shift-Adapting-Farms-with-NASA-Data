<script setup>
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FieldRow from '../components/FieldRow.vue'
import PixelIcon from '../components/PixelIcon.vue'
import { CROP } from '../content.js'
import { state, ranking, risks, chosen } from '../store.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'

// The four example rotations, best fit first: two on each side of the map. Each one is a year as a row of 12 plants.
function choose(r) {
  state.rot = r.id
  say(() => t('{name}: you gain {gain}, but you risk {lose}.', { name: t(r.name), gain: t(r.gain).toLowerCase(), lose: t(r.lose).toLowerCase() }), 'thinking')
}
const LEGEND = [['seed', 'Sowing'], ['plant_ok', 'Growing well'], ['plant_thirsty', 'Stressed'], ['harvest', 'Harvest'], ['bare', 'Bare soil'], ['sun', 'Strong heat'], ['rain', 'Heavy rain'], ['frost', 'Frost']]
</script>

<template>
  <SlideFrame>
    <template v-for="side in ['left', 'right']" :key="side" #[side]>
      <button v-for="(x, i) in ranking.slice(side === 'left' ? 0 : 2, side === 'left' ? 2 : 4)" :key="x.r.id" type="button"
              class="hud pointer-events-auto flex flex-col gap-1.5 bg-panel/90 p-3 text-left text-sm transition-colors" :class="chosen.r.id === x.r.id ? '!border-fire' : 'hover:border-teal'"
              :aria-pressed="chosen.r.id === x.r.id" @click="choose(x.r)">
        <span class="flex flex-wrap items-center gap-2">
          <span class="label !text-muted">{{ (side === 'left' ? 1 : 3) + i }}</span>
          <b class="min-w-0 flex-1 text-[15px]">{{ t(x.r.name) }}</b>
          <span v-if="x === ranking[0]" class="label bg-teal px-1.5 !text-on-accent">{{ t('Best fit for you') }}</span>
          <span v-if="x.r.id === 'current'" class="label border border-line px-1.5 !text-muted">{{ t('What you do today') }}</span>
        </span>
        <FieldRow :cal="x.r.cal" :score="x.score" :risks="risks" :month="state.month" :floods="!!x.r.floods" />
        <span><b class="text-teal">{{ t('You gain:') }}</b> {{ t(x.r.gain) }}</span>
        <span><b class="text-fire">{{ t('You risk:') }}</b> {{ t(x.r.lose) }}</span>
      </button>
      <HudCard v-if="side === 'right'">
        <details>
          <summary class="label cursor-pointer">{{ t('What the drawings mean') }}</summary>
          <div class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs">
            <span v-for="(c, k) in CROP" :key="k" class="flex items-center gap-1"><i class="inline-block h-1.5 w-4" :style="{ background: c.color }" />{{ t(c.name) }}</span>
            <span v-for="[icon, text] in LEGEND" :key="icon" class="flex items-center gap-1"><PixelIcon :name="icon" :size="1" />{{ t(text) }}</span>
          </div>
        </details>
      </HudCard>
    </template>
  </SlideFrame>
</template>
