<script setup>
import PixelIcon from '../components/PixelIcon.vue'
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import CatSprite from './CatSprite.vue'
import { guide, line, hasNext, next, close, summon, submitQuestion, openAsk, say, tell } from '../guide.js'
import { state, valueAt, placeLabel, chosen } from '../store.js'
import { LAYER_KEYS } from '../content.js'
import { blip, meow, meowLength, unlock } from '../lib/sound.js'
import { t, lang } from '../i18n.js'
import VoiceButton from '../voice/VoiceButton.vue'
import { runActions } from '../voice/actions.js'
import { askByText, toVoiceContext } from '../voice/voiceApi.js'
import { voiceLine } from '../voice/speech.js'

// Sprout's translator panel: typed lines, answers to pick, and a box for open questions.
// A line is an English key, or a function for lines with names and numbers, so it re-translates when the language changes.
const resolve = x => typeof x === 'function' ? x() : t(x)
const PITCH = { happy: 1.15, surprised: 1.3, sad: 0.8, worried: 0.92, shy: 1.06, thinking: 0.96, neutral: 1 }
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const typed = ref('')
let timer, restTimer, lastMood = null

// Typewriter: letters appear one by one, with short pauses after punctuation.
// Sprout's voice: every line it types is also spoken (Piper on the ML API, or the browser), unless the sound is off.
let voice = null
const stopVoice = () => { voice?.stop(); voice = null; guide.voicing = false }
watch(() => guide.muted, m => m && stopVoice())
watch([line, lang, () => guide.open], ([l, , open]) => {
  clearTimeout(timer)
  guide.talking = false
  stopVoice()
  if (!l || !open) return
  const [en, mood, lineLang] = l
  const text = resolve(en)
  if (!guide.muted && text) {
    guide.voicing = true             // set now, so the typing blips stay quiet while the voice is fetched
    voice = voiceLine(text, { lang: lineLang || (lang.value === 'en' ? 'en' : 'es'), onEnd: () => { guide.voicing = false } })
  }
  const meows = mood !== lastMood && !guide.muted && !guide.voicing   // a meow when the mood changes, then the text starts
  lastMood = mood
  if (meows) meow(mood)
  if (reduce) { typed.value = text; return }
  let i = 0
  typed.value = ''
  guide.talking = true
  const tick = () => {
    typed.value = text.slice(0, ++i)
    const ch = text[i - 1]
    if (!guide.muted && !guide.voicing && i % 2 && /\w/.test(ch)) blip(PITCH[mood])
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

// Voice: what the user sees goes with the question; the answer is typed in the panel, spoken, and its actions run
// (the map flies to a place, a topic opens). The last turns go back as history so a conversation can continue.
const voiceContext = () => ({
  lat: state.point?.lat, lon: state.point?.lon, district: state.area?.name, province: state.area?.province ?? state.province,
  month: state.month + 1, topic: guide.screen, track: state.track, stage: state.stage,
  view: { signal: state.layer, month: state.month + 1, year_kind: state.scen === 'nino' ? 'el_nino' : 'typical', scenario: state.ahead.scen, mode: state.mode, priorities: { ...state.prio } },
  readings: Object.fromEntries(LAYER_KEYS.map(k => [k, valueAt(k)])),
})
const voiceTurns = []
const voiceHistory = () => voiceTurns
const onListening = () => { unlock(); say(() => t('I\'m listening… tap the microphone again when you finish.'), 'happy', [], { level: 'force' }) }
const onThinking = () => say(() => t('Let me think…'), 'thinking', [], { level: 'force' })
function onReply(r) {
  if (r.transcript) voiceTurns.push({ role: 'user', content: r.transcript })
  voiceTurns.push({ role: 'assistant', content: r.text })
  voiceTurns.splice(0, Math.max(0, voiceTurns.length - 10))
  // next steps the assistant offers become Sprout's answer buttons: tapping one asks it, as if the user had said it
  const offered = (r.actions || []).find(a => a.type === 'choices')?.items ?? []
  const choices = offered.length ? offered.map(label => ({ label, run: () => askText(label) })) : null
  // if the answer moves the user (a place, a topic), the new screen's own lines wait, so this answer stays on screen
  if ((r.actions || []).some(a => a.type !== 'choices')) guide.holdUntil = Date.now() + 3000
  tell([[() => r.text, r.mood || 'neutral', r.lang]], { level: 'force', choices })   // the line watcher speaks it in that language
  runActions(r.actions)
}
const onVoiceError = m => { guide.voicing = false; say(() => m, 'worried', [], { level: 'force' }) }

const question = ref(''), box = ref(null)
watch(() => guide.asking, on => on && nextTick(() => box.value?.focus()))

// Typed questions go to the same assistant as the voice (it can move the map and open topics); if it does not answer,
// the plain chat (/ask) takes over.
async function send() {
  const q = question.value.trim()
  if (!q) return
  question.value = ''
  return askText(q)
}
async function askText(q) {
  onThinking()
  try {
    const r = await askByText(q, { context: toVoiceContext(voiceContext()), history: voiceTurns, lang: lang.value === 'en' ? 'en' : 'es' })
    onReply({ ...r, transcript: q })
    return
  } catch (e) { console.warn('assistant chat failed, using /ask:', e.message) }
  submitQuestion(q, {
    stage: state.stage, mode: state.mode, district: state.area?.name, place: state.point && placeLabel(state.point), month: state.month + 1, scenario: state.scen,
    readings: Object.fromEntries(LAYER_KEYS.map(k => [k, valueAt(k)])), rotation: state.stage === 'explore' ? chosen.value.r.name : null,
    lat: state.point?.lat, lon: state.point?.lon, track: state.track, topic: guide.screen,
    ...(state.track === 'ahead' && { ahead_scenario: state.ahead.scen, ahead_month_index: state.ahead.month }),
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
       :class="state.stage === 'intro' ? 'bottom-[calc(13%+190px)]' : state.stage === 'explore' ? 'bottom-3 max-lg:bottom-2' : 'bottom-3'">
    <Transition name="dock" mode="out-in">
      <aside v-if="guide.open && line" key="panel" class="hud pointer-events-auto w-[min(620px,100%)] !border-teal/50 bg-panel font-mono text-ink" :aria-label="t('Sprout, your guide')">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-1 text-xs uppercase tracking-wider text-teal">
          <span><span class="font-pixel text-[13px]">Sprout</span> · {{ t('translator') }}</span>
          <span class="flex gap-1 text-muted [&_button]:uppercase">
            <button type="button" class="px-1.5 py-1 hover:text-ink" data-tour="ask" :class="{ 'text-teal': guide.asking }" :aria-pressed="guide.asking" :aria-label="t('Ask Sprout anything')" :title="t('Ask Sprout anything')" @click="openAsk"><PixelIcon name="ai" color="currentColor" :size="1.25" /></button>
            <VoiceButton :context="voiceContext" :history="voiceHistory" :speak="false" :muted="true" data-tour="voice"
                         @listening="onListening" @thinking="onThinking" @reply="onReply" @error="onVoiceError" />
            <button type="button" class="px-1.5 py-1 hover:text-ink" data-tour="sound" :aria-pressed="!guide.muted" :aria-label="t(guide.muted ? 'Turn voice sound on' : 'Turn voice sound off')" :title="t(guide.muted ? 'Turn voice sound on' : 'Turn voice sound off')" @click="unlock(); guide.muted = !guide.muted"><PixelIcon :name="guide.muted ? 'speaker_off' : 'speaker'" color="currentColor" :size="1.25" /></button>
            <button type="button" class="px-1.5 py-1 hover:text-ink" data-tour="close" :aria-label="t('Close Sprout')" :title="t('Close Sprout')" @click="close"><PixelIcon name="close" color="currentColor" :size="1.25" /></button>
          </span>
        </div>
        <div class="grid cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-3 py-2.5 max-sm:gap-2 max-sm:py-1.5" @click="advance">
          <div v-if="state.stage !== 'intro'" class="-mb-2.5 -mt-4 self-end max-sm:-mb-1.5 max-sm:-mt-2 max-sm:w-11"><CatSprite :mood="line[1]" :talking="guide.talking || guide.voicing" :size="88" bust class="max-sm:!h-auto max-sm:!w-11" /></div>
          <span v-else />
          <p class="min-h-[3.1em] text-[14.5px] leading-normal max-sm:min-h-0 max-sm:text-[13px] max-sm:leading-snug" aria-hidden="true">{{ typed }}<span v-if="!done" class="animate-[caret_.8s_steps(2)_infinite] text-teal">▌</span></p>
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
