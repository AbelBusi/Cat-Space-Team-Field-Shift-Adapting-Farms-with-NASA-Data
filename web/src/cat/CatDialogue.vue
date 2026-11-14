<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import CatSprite from './CatSprite.vue'
import { guide, line, hasNext, canAdvance, next, showEverything } from '../guide.js'
import { blip, meow, meowLength, unlock } from '../lib/sound.js'
import { t, lang } from '../i18n.js'

// A line is an English key, or a function for lines with names and numbers, so it re-translates when the language changes.
const resolve = x => typeof x === 'function' ? x() : t(x)

const PITCH = { happy: 1.15, surprised: 1.3, sad: 0.8, worried: 0.92, shy: 1.06, thinking: 0.96, neutral: 1 }
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const typed = ref('')
let timer, lastMood = null

// Typewriter: letters appear one by one, with short pauses after punctuation.
watch([line, lang], ([l]) => {
  clearTimeout(timer)
  guide.talking = false
  if (!l) return
  const [en, mood] = l
  const text = resolve(en)
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

const shown = computed(() => line.value ? resolve(line.value[0]) : '')
const done = computed(() => !!line.value && typed.value.length >= shown.value.length)

function advance() {
  unlock()
  if (!done.value) { clearTimeout(timer); typed.value = shown.value; guide.talking = false; return }
  next()
}
function toggleSound() { unlock(); guide.muted = !guide.muted }
</script>

<template>
  <Transition name="dlg">
    <aside v-if="guide.open && line" class="dlg hud" :aria-label="t('Sprout, your guide')">
      <div class="dlg-head">
        <span class="dlg-tag"><span class="dlg-name">Sprout</span> · {{ t('translator') }}</span>
        <span class="dlg-ctrl">
          <button v-if="!guide.showAll" type="button" class="dlg-btn" @click="showEverything">{{ t('[ show all ]') }}</button>
          <button type="button" class="dlg-btn" :aria-pressed="!guide.muted" :aria-label="guide.muted ? 'Turn voice sound on' : 'Turn voice sound off'" @click="toggleSound">{{ t(guide.muted ? '[ sound off ]' : '[ sound on ]') }}</button>
          <button type="button" class="dlg-btn" :aria-label="t('Minimize Sprout')" @click="guide.open = false">[ _ ]</button>
        </span>
      </div>
      <div class="dlg-body" @click="advance">
        <div class="dlg-face"><CatSprite :mood="line[1]" :talking="guide.talking" :size="64" /></div>
        <p class="dlg-text" aria-hidden="true">{{ typed }}<span v-if="!done" class="dlg-cursor">▌</span></p>
        <p class="sr-only" aria-live="polite">{{ shown }}</p>
        <button v-if="!done || canAdvance" type="button" class="dlg-next" @click.stop="advance">{{ t(done ? '[ next ]' : '[ skip ]') }}</button>
      </div>
    </aside>
  </Transition>
  <button v-if="!guide.open" type="button" class="dlg-reopen hud" :aria-label="t('Show Sprout, your guide')" @click="guide.open = true">
    <CatSprite :mood="line?.[1] || 'happy'" :size="44" /><span>Sprout</span>
  </button>
</template>
