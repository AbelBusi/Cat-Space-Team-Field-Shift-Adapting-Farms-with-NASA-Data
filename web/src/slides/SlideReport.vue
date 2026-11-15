<script setup>
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import PixelIcon from '../components/PixelIcon.vue'
import PixelGlobe from '../components/PixelGlobe.vue'
import CropSequence from '../components/CropSequence.vue'
import { GLOSSARY, SLIDES, fitWord } from '../content.js'
import { PAL } from '../lib/palette.js'
import { state, climate, placeLabel, chosen, confidence } from '../store.js'
import { t } from '../i18n.js'

// The end of the visit: a short summary, and the full report to print or save as a PDF.
const print = () => window.print()
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard :title="t('In short')">
        <div class="flex items-center gap-3">
          <PixelGlobe :lat="state.point?.lat" :lon="state.point?.lon" :size="56" />
          <div class="min-w-0">
            <div class="truncate font-display text-xl font-semibold">{{ state.point ? placeLabel(state.point) : '' }}</div>
            <div class="flex items-center gap-1.5 font-mono text-xs text-teal"><PixelIcon :name="climate?.dry === 'dry' ? 'soil_dry' : 'soil_moist'" :size="1" />{{ climate?.label() }}</div>
          </div>
        </div>
        <div class="border-t border-line pt-2">
          <div class="flex items-center justify-between gap-2">
            <span class="label">{{ t('Chosen strategy') }}</span>
            <span class="flex items-center gap-1 font-mono text-xs"><PixelIcon :name="chosen.score >= 70 ? 'plant_ok' : chosen.score >= 45 ? 'plant_thirsty' : 'plant_dead'" :size="1" />{{ state.mode === 'pro' ? t('{n} out of 100', { n: chosen.score }) : t(fitWord(chosen.score)) }}</span>
          </div>
          <b class="mb-1 block text-fire">{{ t(chosen.r.name) }}</b>
          <CropSequence :cal="chosen.r.cal" />
        </div>
        <p class="flex items-start gap-2"><PixelIcon name="up" :color="PAL.teal" :size="1" class="mt-1" /><span><b class="text-teal">{{ t('You gain:') }}</b> {{ t(chosen.r.gain) }}</span></p>
        <p class="flex items-start gap-2"><PixelIcon name="down" :color="PAL.ember" :size="1" class="mt-1" /><span><b class="text-fire">{{ t('You risk:') }}</b> {{ t(chosen.r.lose) }}</span></p>
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted">{{ t('Confidence') }}</span>
          <div class="meter flex-1" role="img" :aria-label="t('Confidence {n} out of 100', { n: confidence.score })"><i v-for="i in 10" :key="i" :class="{ on: i <= Math.round(confidence.score / 10) }" :style="{ '--i': i }" /></div>
          <b class="text-xs">{{ t(confidence.level) }}</b>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <button type="button" class="btn" @click="state.slide = SLIDES.findIndex(s => s.id === 'rots')"><PixelIcon name="seed" :size="1" />{{ t('Change strategy') }}</button>
          <button type="button" class="btn" @click="state.slide = SLIDES.findIndex(s => s.id === 'detail')"><PixelIcon name="compare" :size="1" />{{ t('Raise the confidence') }}</button>
        </div>
      </HudCard>
      <HudCard :title="t('Your report')">
        <p>{{ t('Everything you saw, on paper: the readings for the 12 months, the hard years, the four rotations and where each number comes from.') }}</p>
        <button type="button" class="btn btn-fire self-start !min-h-11 !px-5" @click="print"><PixelIcon name="report" :size="1" />{{ t('Print or save as PDF') }}</button>
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
