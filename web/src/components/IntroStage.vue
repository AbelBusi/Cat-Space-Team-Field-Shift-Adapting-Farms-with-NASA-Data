<script>
// The arrival plays once per page load: coming back to this screen later shows Sprout already here.
let arrived = false
</script>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import CatSprite from '../cat/CatSprite.vue'
import { PALETTE, UFO, UFO_SIZE } from '../cat/sprites.js'
import { state } from '../store.js'
import { guide, line, tell, openAsk } from '../guide.js'
import { SCRIPTS } from '../content.js'
import { meow, unlock } from '../lib/sound.js'

// Sprout arrives: its saucer glides in over the hills, a beam of light opens, Sprout floats down to the campfire,
// lands with a little bounce and waves; the saucer leaves and only then Sprout starts to talk.
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const phase = ref(arrived || reduce ? 'here' : 'fly')   // fly → beam → land → here
const waving = ref(false), cheer = ref(false)
const mood = computed(() => cheer.value || phase.value !== 'here' ? 'excited' : line.value?.[1] || 'happy')
const timers = []
const after = (ms, fn) => timers.push(setTimeout(fn, ms))

// Sprout says hello and asks how much help you want. Whatever the answer, the next screen is the place picker.
// `answered`: the user picked an answer in the dialogue (not just the big button), so Sprout replies to it.
function begin(on, answered = true) {
  guide.on = on
  try { localStorage.setItem('fs-guide', on ? 'on' : 'off') } catch {}
  if (on || !answered) guide.open = false
  else tell([["Oh... okay! That's totally fine. I'll wait quietly right here. Tap me whenever you need me, I'd be so happy to help.", 'shy']], { level: 'force' })
  state.province = null
  state.stage = 'where'
}
function greet() {
  guide.screen = 'intro'
  tell(SCRIPTS.intro, { level: 'force', choices: [
    { label: 'Yes, please guide me', run: () => begin(true) },
    { label: "No thanks, I'll explore on my own", run: () => begin(false) },
    { label: 'I want to ask something else', run: openAsk },
  ] })
}
function wave(ms = 1600) {
  waving.value = true
  after(ms, () => (waving.value = false))
}
onMounted(() => {
  if (phase.value === 'here') { arrived = true; return greet() }
  after(1500, () => (phase.value = 'beam'))       // the saucer stops above the campfire and opens its beam
  after(2950, () => { phase.value = 'land'; if (!guide.muted) meow('excited') })
  after(3400, () => { phase.value = 'here'; arrived = true; wave(); greet() })
})
onBeforeUnmount(() => timers.forEach(clearTimeout))
function pet() {
  unlock()
  if (!guide.muted) meow(line.value?.[1] || 'happy')
  cheer.value = true
  wave(1100)
  after(1100, () => (cheer.value = false))
  if (!guide.open && phase.value === 'here') greet()
}
</script>

<template>
  <section class="absolute inset-0 z-10 flex flex-col items-center px-4 pt-[clamp(72px,13vh,140px)] text-center">
    <div class="label">NASA Space Apps 2026 · Field Shift</div>
    <h1 class="mt-3 text-[30px] text-sky-ink md:text-[40px]">{{ t('Your field is already talking.') }}<br>{{ t("Let's learn to listen.") }}</h1>
    <p class="mt-3 max-w-[620px] text-sky-muted [@media(max-height:720px)]:hidden">{{ t('NASA satellites measure heat, rain, soil wetness and plant greenness for every field on Earth. Sprout translates them so you can choose what to plant next.') }}</p>
    <button type="button" class="btn btn-fire mt-5 !min-h-11 !px-6" @click="begin(guide.on, false)">{{ t('Explore your field') }}</button>

    <!-- The landing spot, next to the campfire. Everything in the arrival is placed from here. -->
    <div class="arrival absolute bottom-[calc(13%-6px)] left-[calc(50%-150px)] w-[150px] max-sm:left-[calc(50%-120px)] max-sm:w-[120px]" :data-phase="phase" aria-hidden="false">
      <svg v-if="phase !== 'here'" class="ufo absolute bottom-[300px] left-1/2 w-[150px]" :viewBox="`0 0 ${UFO_SIZE[0]} ${UFO_SIZE[1]}`" shape-rendering="crispEdges" aria-hidden="true">
        <rect v-for="[x, y, w, c] in UFO" :key="`${x},${y}`" :x="x" :y="y" :width="w" height="1" :fill="PALETTE[c]" />
      </svg>
      <div v-if="phase === 'beam' || phase === 'land'" class="beam absolute bottom-0 left-1/2 h-[300px] w-[150px]" aria-hidden="true" />
      <button type="button" class="sprout relative block w-full transition-transform active:scale-95" :aria-label="t('Pet Sprout')" @click="pet">
        <CatSprite :mood="mood" :pose="waving ? 'wave' : 'sit'" :talking="guide.talking && phase === 'here'" :size="150" full class="mx-auto max-sm:!w-[120px]" />
      </button>
    </div>
  </section>
</template>
