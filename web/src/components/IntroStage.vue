<script setup>
import { onMounted } from 'vue'
import CatSprite from '../cat/CatSprite.vue'
import { state } from '../store.js'
import { guide, line, tell, openAsk } from '../guide.js'
import { SCRIPTS } from '../content.js'
import { meow, unlock } from '../lib/sound.js'

// Sprout says hello and asks how much help you want. Whatever the answer, the next screen is the place picker.
function begin(on) {
  guide.on = on
  try { localStorage.setItem('fs-guide', on ? 'on' : 'off') } catch {}
  if (on) guide.open = false
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
onMounted(greet)
function pet() {
  unlock()
  if (!guide.muted) meow(line.value?.[1] || 'happy')
  if (!guide.open) greet()
}
</script>

<template>
  <section class="absolute inset-0 z-10 flex flex-col items-center px-4 pt-[clamp(72px,13vh,140px)] text-center">
    <div class="label">NASA Space Apps 2026 · Field Shift</div>
    <h1 class="mt-3 text-[30px] text-sky-ink md:text-[40px]">{{ t('Your field is already talking.') }}<br>{{ t("Let's learn to listen.") }}</h1>
    <p class="mt-3 max-w-[620px] text-sky-muted [@media(max-height:720px)]:hidden">{{ t('NASA satellites measure heat, rain, soil wetness and plant greenness for every field on Earth. Sprout translates them so you can choose what to plant next.') }}</p>
    <button type="button" class="btn btn-fire mt-5 !min-h-11 !px-6" @click="begin(guide.on)">{{ t('Explore your field') }}</button>

    <button type="button" class="absolute bottom-[calc(13%-8px)] left-[calc(50%-150px)] transition-transform active:scale-95 max-sm:left-[calc(50%-120px)]" :aria-label="t('Pet Sprout')" @click="pet">
      <CatSprite :mood="line?.[1] || 'happy'" :talking="guide.talking" :size="128" />
    </button>
  </section>
</template>
