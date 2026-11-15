<script setup>
import { computed, watch, onMounted, onBeforeUnmount } from 'vue'
import MapStage from './MapStage.vue'
import MapTools from './MapTools.vue'
import Field3D from './Field3D.vue'
import SlideSignals from '../slides/SlideSignals.vue'
import SlideGround from '../slides/SlideGround.vue'
import SlideYears from '../slides/SlideYears.vue'
import SlidePrio from '../slides/SlidePrio.vue'
import SlideRots from '../slides/SlideRots.vue'
import SlideDetail from '../slides/SlideDetail.vue'
import SlideReport from '../slides/SlideReport.vue'
import { state, mapUi } from '../store.js'
import { SLIDES } from '../content.js'
import { enter } from '../guide.js'

// The map with one topic over it at a time. Arrows (on screen or on the keyboard) move between topics.
const VIEWS = { signals: SlideSignals, ground: SlideGround, years: SlideYears, prio: SlidePrio, rots: SlideRots, detail: SlideDetail, report: SlideReport }
const slide = computed(() => SLIDES[state.slide])
const last = SLIDES.length - 1
const go = d => { state.slide = Math.max(0, Math.min(last, state.slide + d)) }
// The outlined field can float in 3D in the free space between the cards; the cards stay.
const view3d = computed(() => mapUi.view3d && !!state.parcel)
function onKey(e) {
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return
  if (e.key === 'ArrowRight') go(1)
  if (e.key === 'ArrowLeft') go(-1)
}
onMounted(() => addEventListener('keydown', onKey))
onBeforeUnmount(() => removeEventListener('keydown', onKey))
watch(() => state.slide, () => enter(slide.value.id), { immediate: true })
</script>

<template>
  <section class="absolute inset-0">
    <MapStage :tint="slide.id === 'signals'" :squares="slide.id === 'ground'" />
    <Transition name="stage"><Field3D v-if="view3d" :key="state.parcel.areaM2" /></Transition>

    <div data-hud-top class="pointer-events-none absolute inset-x-0 top-14 z-20 mx-auto flex flex-col items-center gap-1.5 px-2 lg:max-w-[calc(100vw-2*(clamp(280px,27vw,380px)+64px))]">
      <nav class="hud pointer-events-auto flex items-center gap-3 bg-panel/90 px-3 py-1" :aria-label="t('Topics')">
        <button type="button" class="btn !min-h-8 !px-2 lg:hidden" :disabled="state.slide === 0" :aria-label="t('Previous topic')" @click="go(-1)">‹</button>
        <div class="text-center">
          <Transition name="flip" mode="out-in"><h2 :key="slide.id" class="text-base md:text-lg">{{ t(slide.title) }}</h2></Transition>
          <div class="mt-1 flex items-center justify-center gap-1.5">
            <button v-for="(s, i) in SLIDES" :key="s.id" type="button" class="size-2.5 border transition-colors" :class="i === state.slide ? 'border-fire bg-fire' : i < state.slide ? 'border-teal bg-teal' : 'border-muted'"
                    :aria-label="t(s.title)" :aria-current="i === state.slide ? 'step' : null" :title="t(s.title)" @click="state.slide = i" />
          </div>
        </div>
        <button type="button" class="btn !min-h-8 !px-2 lg:hidden" :disabled="state.slide === last" :aria-label="t('Next topic')" @click="go(1)">›</button>
      </nav>
      <MapTools />
    </div>

    <button type="button" class="btn absolute left-2 top-1/2 z-20 hidden !h-24 !w-11 -translate-y-1/2 !px-0 text-2xl lg:flex" :disabled="state.slide === 0" :aria-label="t('Previous topic')" @click="go(-1)">‹</button>
    <button type="button" class="btn absolute right-2 top-1/2 z-20 hidden !h-24 !w-11 -translate-y-1/2 !px-0 text-2xl lg:flex" :class="{ 'btn-fire': state.slide < last }" :disabled="state.slide === last" :aria-label="t('Next topic')" @click="go(1)">›</button>

    <Transition name="slide" mode="out-in"><component :is="VIEWS[slide.id]" :key="slide.id" /></Transition>
  </section>
</template>
