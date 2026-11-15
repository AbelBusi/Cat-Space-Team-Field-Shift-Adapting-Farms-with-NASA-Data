<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import CatSprite from './CatSprite.vue'
import { guide, line, hasNext, next, close, summon, submitQuestion } from '../guide.js'
import { state, valueAt, placeLabel, chosen } from '../store.js'
import { LAYER_KEYS } from '../content.js'
import { blip, meow, meowLength, unlock } from '../lib/sound.js'
import { t, lang } from '../i18n.js'

// Sprout's translator panel: typed lines, answers to pick, and a box for open questions.
// A line is an English key, or a function for lines with names and numbers, so it re-translates when the language changes.
const resolve = x => typeof x === 'function' ? x() : t(x)
const PITCH = { happy: 1.15, surprised: 1.3, sad: 0.8, worried: 0.92, shy: 1.06, thinking: 0.96, neutral: 1 }
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const typed = ref('')
let timer, restTimer, lastMood = null

// Typewriter: letters appear one by one, with short pauses after punctuation.
watch([line, lang, () => guide.open], ([l, , open]) => {
  clearTimeout(timer)
  guide.talking = false
  if (!l || !open) return
  const [en, mood] = l
  const text = resolve(en)
  const meows = mood !== lastMood && !guide.muted   // a meow when the mood changes, then the text starts
  lastMood = mood
  if (meows) meow(mood)
  if (reduce) { typed.value = text; return }
  let i = 0
  typed.value = ''
  guide.talking = true
  const tick = () => {
    typed.value = text.slice(0, ++i)
    const ch = text[i - 1]
    if (!guide.muted && i % 2 && /\w/.test(ch)) blip(PITCH[mood])
    if (i >= text.length) { guide.talking = false; return }
    timer = setTimeout(tick, /[.!?]/.test(ch) ? 220 : /[,:]/.test(ch) ? 110 : 20)
  }
  timer = setTimeout(tick, meows ? meowLength(mood) * 1000 : 0)
}, { immediate: true })

const shown = computed(() => line.value ? resolve(line.value[0]) : '')
const done = computed(() => !!line.value && typed.value.length >= shown.value.length)
const atEnd = computed(() => done.value && !hasNext.value)
function advance() {
  unlock()
  if (!done.value) { clearTimeout(timer); typed.value = shown.value; guide.talking = false; return }
  next()
}
function pick(c) { unlock(); c.run() }

// With the guide off, Sprout steps back by itself once it has said what it had to say.
watch(() => [atEnd.value, guide.on, guide.choices, guide.asking, guide.open], () => {
  clearTimeout(restTimer)
  if (guide.open && atEnd.value && !guide.on && !guide.choices && !guide.asking) restTimer = setTimeout(close, 7000)
})

const question = ref(''), box = ref(null)
watch(() => guide.asking, on => on && nextTick(() => box.value?.focus()))
function send() {
  const q = question.value.trim()
  if (!q) return
  question.value = ''
  submitQuestion(q, {
    stage: state.stage, mode: state.mode, district: state.area?.name, place: state.point && placeLabel(state.point), month: state.month + 1, scenario: state.scen,
    readings: Object.fromEntries(LAYER_KEYS.map(k => [k, valueAt(k)])), rotation: state.stage === 'explore' ? chosen.value.r.name : null,
  })
}

// Keys: Enter or Space for the next line, 1–9 to pick an answer, Escape to send Sprout back to the corner.
function onKey(e) {
  if (!guide.open || /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(e.target.tagName)) return
  if (e.key === 'Escape') return close()
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); return advance() }
  const c = atEnd.value && guide.choices?.[+e.key - 1]
  if (c) pick(c)
}
onMounted(() => addEventListener('keydown', onKey))
onBeforeUnmount(() => { clearTimeout(timer); clearTimeout(restTimer); removeEventListener('keydown', onKey) })
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 z-50 flex justify-center px-2 print:hidden"
       :class="state.stage === 'intro' ? 'bottom-[calc(13%+190px)]' : state.stage === 'explore' ? 'bottom-3 max-lg:bottom-[calc(44dvh+8px)]' : 'bottom-3'">
    <Transition name="dock" mode="out-in">
      <aside v-if="guide.open && line" key="panel" class="hud pointer-events-auto w-[min(620px,100%)] !border-teal/50 bg-panel font-mono text-ink" :aria-label="t('Sprout, your guide')">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-1 text-xs uppercase tracking-wider text-teal">
          <span><span class="font-pixel text-[13px]">Sprout</span> · {{ t('translator') }}</span>
          <span class="flex gap-1 text-muted [&_button]:uppercase">
            <button type="button" class="px-1.5 py-1 hover:text-ink" :aria-pressed="!guide.muted" :aria-label="t(guide.muted ? 'Turn voice sound on' : 'Turn voice sound off')" @click="unlock(); guide.muted = !guide.muted">{{ t(guide.muted ? '[ sound off ]' : '[ sound on ]') }}</button>
            <button type="button" class="px-1.5 py-1 hover:text-ink" :aria-label="t('Minimize Sprout')" @click="close">[ _ ]</button>
          </span>
        </div>
        <div class="grid cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-3 py-2.5" @click="advance">
          <div v-if="state.stage !== 'intro'" class="flex size-[60px] items-center justify-center border border-line bg-bg"><CatSprite :mood="line[1]" :talking="guide.talking" :size="52" /></div>
          <span v-else />
          <p class="min-h-[3.1em] text-[14.5px] leading-normal" aria-hidden="true">{{ typed }}<span v-if="!done" class="animate-[caret_.8s_steps(2)_infinite] text-teal">▌</span></p>
          <p class="sr-only" aria-live="polite">{{ shown }}</p>
          <button v-if="!atEnd" type="button" class="btn self-end !min-h-8" :class="state.stage === 'intro' ? 'btn-fire' : '!border-teal !text-teal'" @click.stop="advance">{{ t(done ? '[ next ]' : '[ skip ]') }}</button>
        </div>
        <div v-if="atEnd && guide.choices && !guide.asking" class="flex flex-col gap-1 border-t border-line p-2 sm:flex-row sm:flex-wrap" role="group" :aria-label="t('Your answer')">
          <button v-for="(c, i) in guide.choices" :key="c.label" type="button" class="btn !justify-start !py-1.5 text-left !normal-case !tracking-normal sm:flex-1" :class="{ 'btn-fire': i === 0 && state.stage === 'intro', '!border-teal': i === 0 && state.stage !== 'intro' }" @click="pick(c)">
            <span aria-hidden="true">▸</span>{{ t(c.label) }}
          </button>
        </div>
        <form v-if="guide.asking" class="flex gap-1 border-t border-line p-2" @submit.prevent="send">
          <label for="sprout-q" class="sr-only">{{ t('Your question for Sprout') }}</label>
          <input id="sprout-q" ref="box" v-model="question" class="min-w-0 flex-1 border border-line bg-bg px-2 py-1.5 font-sans text-sm text-ink" :placeholder="t('Write your question…')" autocomplete="off" maxlength="300">
          <button type="submit" class="btn btn-fire" :disabled="!question.trim()">{{ t('Ask') }}</button>
        </form>
      </aside>
      <button v-else-if="state.stage !== 'intro'" key="tab" type="button" class="hud pointer-events-auto relative flex items-center gap-2 bg-panel py-1 pl-1 pr-3 font-pixel text-[13px] uppercase text-teal transition-transform hover:-translate-y-0.5"
              :aria-label="t(guide.unread ? 'Sprout has something to tell you' : 'Show Sprout, your guide')" @click="unlock(); summon()">
        <CatSprite :mood="guide.unread ? 'surprised' : guide.on ? 'happy' : 'shy'" :size="40" /><span>Sprout</span>
        <span v-if="guide.unread" class="absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center bg-fire font-mono text-[11px] font-bold text-on-accent">!
          <span class="absolute inset-0 animate-[ping_1.4s_ease-out_3] bg-fire" aria-hidden="true" /></span>
      </button>
    </Transition>
  </div>
</template>
