<script setup>
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import FieldRow from '../components/FieldRow.vue'
import CropSequence from '../components/CropSequence.vue'
import { CRIT, LEVELS, ICON } from '../content.js'
import { state, ranking, risks } from '../store.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'

// What matters to this farmer (left) and, live, the rotation that fits it best (right).
function bump(k) {
  const before = ranking.value[0].r
  state.prio[k] = (state.prio[k] + 1) % 4
  const after = ranking.value[0].r
  if (after !== before) say(() => t('With what matters to you now, "{name}" fits best. Look, it moved to the front!', { name: t(after.name) }), 'surprised')
}
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard :title="t('Tap to raise or lower')">
        <div class="swipe flex flex-col gap-2">
        <button v-for="c in CRIT" :key="c.k" type="button" class="flex items-center gap-3 border border-line p-2 text-left transition-colors hover:border-teal"
                :class="{ 'border-teal bg-teal/10': state.prio[c.k] === 3 }"
                :aria-label="t('{name}: importance {level}. Tap to change.', { name: t(c.label), level: t(LEVELS[state.prio[c.k]]) })" @click="bump(c.k)">
          <svg class="size-6 shrink-0 text-teal" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[c.icon]" />
          <span class="min-w-0 flex-1"><b class="block">{{ t(c.label) }}</b><span class="block truncate text-xs text-muted">{{ t(c.hint) }}</span></span>
          <span class="flex shrink-0 flex-col items-end gap-1">
            <span class="flex gap-1"><i v-for="i in 3" :key="i" class="size-2.5 border border-teal transition-colors" :class="{ 'bg-teal': i <= state.prio[c.k] }" /></span>
            <span class="font-mono text-[10px] uppercase text-muted">{{ t(LEVELS[state.prio[c.k]]) }}</span>
          </span>
        </button>
        </div>
      </HudCard>
    </template>
    <template #right>
      <HudCard :title="t('Best fit for you')">
        <Transition name="flip" mode="out-in"><div :key="ranking[0].r.id" class="font-display text-xl font-semibold text-fire">{{ t(ranking[0].r.name) }}</div></Transition>
        <CropSequence :key="'c' + ranking[0].r.id" :cal="ranking[0].r.cal" />
        <FieldRow :key="ranking[0].r.id" :cal="ranking[0].r.cal" :score="ranking[0].score" :risks="risks" :month="state.month" :floods="!!ranking[0].r.floods" />
        <p><b class="text-teal">{{ t('You gain:') }}</b> {{ t(ranking[0].r.gain) }}</p>
        <p><b class="text-fire">{{ t('You risk:') }}</b> {{ t(ranking[0].r.lose) }}</p>
      </HudCard>
    </template>
  </SlideFrame>
</template>
