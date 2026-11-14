<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import CatSprite from './CatSprite.vue'
import { guide, line, hasNext, canAdvance, next, showEverything } from '../guide.js'
import { blip, meow, meowLength, unlock } from '../lib/sound.js'
import { ICON } from '../content.js'

const PITCH = { happy: 1.15, surprised: 1.3, sad: 0.8, worried: 0.92, shy: 1.06, thinking: 0.96, neutral: 1 }
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const typed = ref('')
let timer, lastMood = null

// Typewriter: letters appear one by one, with short pauses after punctuation.
watch(line, l => {
  clearTimeout(timer)
  guide.talking = false
  if (!l) return
  const [text, mood] = l
  // A meow when the mood changes, then the text starts once the meow ends.
  const meows = mood !== lastMood && !guide.muted
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
    timer = setTimeout(tick, /[.!?]/.test(ch) ? 260 : /[,:]/.test(ch) ? 130 : 24)
  }
  timer = setTimeout(tick, meows ? meowLength(mood) * 1000 : 0)
}, { immediate: true })
onBeforeUnmount(() => clearTimeout(timer))

const done = computed(() => !!line.value && typed.value.length >= line.value[0].length)

function advance() {
  unlock()
  if (!done.value) { clearTimeout(timer); typed.value = line.value[0]; guide.talking = false; return }
  next()
}
function toggleSound() { unlock(); guide.muted = !guide.muted }
</script>

<template>
  <Transition name="dlg">
    <aside v-if="guide.open && line" class="dlg" aria-label="Sprout, your guide">
      <div class="dlg-box" @click="advance">
        <div class="dlg-face"><CatSprite :mood="line[1]" :talking="guide.talking" :size="84" /></div>
        <div class="dlg-body">
          <div class="dlg-name">Sprout</div>
          <p class="dlg-text" aria-hidden="true">{{ typed }}<span v-if="done && canAdvance" class="dlg-caret">▼</span></p>
          <p class="sr-only" aria-live="polite">{{ line[0] }}</p>
        </div>
      </div>
      <div class="dlg-actions">
        <button v-if="!done || canAdvance" type="button" class="dlg-btn main" @click="advance">{{ done ? 'Next ›' : 'Skip ›' }}</button>
        <button v-if="!guide.showAll" type="button" class="dlg-btn" @click="showEverything">Show everything</button>
        <button type="button" class="dlg-btn" :aria-pressed="!guide.muted" :aria-label="guide.muted ? 'Turn voice sound on' : 'Turn voice sound off'" @click="toggleSound">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="guide.muted ? ICON.mute : ICON.sound" />
        </button>
        <button type="button" class="dlg-btn" @click="guide.open = false">Hide</button>
      </div>
    </aside>
  </Transition>
  <button v-if="!guide.open" type="button" class="dlg-reopen" aria-label="Show Sprout, your guide" @click="guide.open = true">
    <CatSprite :mood="line?.[1] || 'happy'" :size="56" />
  </button>
</template>
