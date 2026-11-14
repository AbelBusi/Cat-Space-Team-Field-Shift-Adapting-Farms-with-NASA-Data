<script setup>
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import { GLOSSARY, fitWord } from '../content.js'
import { state, climate, placeLabel, chosen, confidence } from '../store.js'
import { t } from '../i18n.js'

// The end of the visit: a short summary, and the full report to print or save as a PDF.
const print = () => window.print()
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard :title="t('In short')">
        <div class="font-display text-xl font-semibold">{{ state.point ? placeLabel(state.point) : '' }}</div>
        <p class="font-mono text-xs text-teal">{{ climate?.label() }}</p>
        <p>{{ t('Chosen strategy') }}: <b class="text-fire">{{ t(chosen.r.name) }}</b> · {{ state.mode === 'pro' ? t('{n} out of 100', { n: chosen.score }) : t(fitWord(chosen.score)) }}</p>
        <p><b class="text-teal">{{ t('You gain:') }}</b> {{ t(chosen.r.gain) }}<br><b class="text-fire">{{ t('You risk:') }}</b> {{ t(chosen.r.lose) }}</p>
        <p class="text-muted">{{ t('Confidence') }}: {{ t(confidence.level) }}</p>
      </HudCard>
      <HudCard :title="t('Your report')">
        <p>{{ t('Everything you saw, on paper: the readings for the 12 months, the hard years, the four rotations and where each number comes from.') }}</p>
        <button type="button" class="btn btn-fire self-start !min-h-11 !px-5" @click="print">{{ t('Print or save as PDF') }}</button>
        <p class="text-xs text-muted">{{ t('This tool shows patterns and possibilities. The final word belongs to your experience and to an agronomist who knows your area.') }}</p>
      </HudCard>
    </template>
    <template #right>
      <HudCard :title="t('Satellite words, made simple')">
        <details v-for="[term, text] in GLOSSARY" :key="term" class="border-b border-line pb-1 last:border-0">
          <summary class="cursor-pointer font-semibold">{{ t(term) }}</summary><p class="mt-1 text-muted">{{ t(text) }}</p>
        </details>
      </HudCard>
    </template>
  </SlideFrame>
</template>
