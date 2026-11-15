<script setup>
import { computed, watch, onMounted, onBeforeUnmount } from 'vue'
import MapStage from './MapStage.vue'
import MapTools from './MapTools.vue'
import PixelIcon from './PixelIcon.vue'
import Field3D from './Field3D.vue'
import SlideSignals from '../slides/SlideSignals.vue'
import SlideGround from '../slides/SlideGround.vue'
import SlideYears from '../slides/SlideYears.vue'
import SlidePrio from '../slides/SlidePrio.vue'
import SlideRots from '../slides/SlideRots.vue'
import SlideDetail from '../slides/SlideDetail.vue'
import SlideReport from '../slides/SlideReport.vue'
import SlideOutlook from '../slides/SlideOutlook.vue'
import SlideWhatIf from '../slides/SlideWhatIf.vue'
import SlideGreenAhead from '../slides/SlideGreenAhead.vue'
import SlideSpots from '../slides/SlideSpots.vue'
import SlideTrust from '../slides/SlideTrust.vue'
import { state, mapUi } from '../store.js'
import { slidesOf } from '../content.js'
import { enter } from '../guide.js'

// The map with one topic over it at a time. Arrows (on screen or on the keyboard) move between topics.
// Two tracks share the map: "today" (what the satellites see) and "ahead" (projections and what-if of the ML models).
const VIEWS = { signals: SlideSignals, ground: SlideGround, years: SlideYears, prio: SlidePrio, rots: SlideRots, detail: SlideDetail, report: SlideReport,
  outlook: SlideOutlook, whatif: SlideWhatIf, green: SlideGreenAhead, spots: SlideSpots, trust: SlideTrust }
const SLIDES = computed(() => slidesOf(state.track))
const slide = computed(() => SLIDES.value[Math.min(state.slide, SLIDES.value.length - 1)])
const last = computed(() => SLIDES.value.length - 1)
const ahead = computed(() => state.track === 'ahead')
const go = d => { state.slide = Math.max(0, Math.min(last.value, state.slide + d)) }
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
      <nav data-tour="topics" class="hud pointer-events-auto flex items-center gap-3 bg-panel/90 px-3 py-1" :aria-label="t('Topics')">
        <button type="button" class="btn !min-h-8 !px-2 lg:hidden" :disabled="state.slide === 0" :aria-label="t('Previous topic')" @click="go(-1)">‹</button>
        <div class="text-center">
          <Transition name="flip" mode="out-in"><h2 :key="slide.id" class="text-base md:text-lg">{{ t(slide.title) }}</h2></Transition>
          <!-- The path of topics: one pixel icon each, joined by a line. Done in teal, here in campfire, ahead dimmed. -->
          <ol class="mt-1 flex items-center justify-center">
            <li v-for="(s, i) in SLIDES" :key="s.id" class="flex items-center">
              <span v-if="i" class="h-px w-2 sm:w-3" :class="i <= state.slide ? 'bg-teal' : 'bg-line'" aria-hidden="true" />
              <button type="button" class="flex size-7 items-center justify-center border transition-[border-color,background-color,opacity] duration-300"
                      :class="i === state.slide ? 'border-fire bg-fire/15' : i < state.slide ? 'border-teal bg-teal/10' : 'border-line opacity-45 hover:opacity-100'"
                      :aria-label="t(s.title)" :aria-current="i === state.slide ? 'step' : null" :title="t(s.title)" @click="state.slide = i">
                <PixelIcon :name="s.icon" :size="1" />
              </button>
            </li>
          </ol>
          <div v-if="state.slide < last" class="mt-0.5 truncate font-mono text-[10px] uppercase tracking-wider text-muted">{{ t('Next: {topic}', { topic: t(SLIDES[state.slide + 1].title) }) }}</div>
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
