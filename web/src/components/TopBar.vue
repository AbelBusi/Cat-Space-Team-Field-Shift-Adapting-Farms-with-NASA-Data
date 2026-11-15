<script setup>
import { ref } from 'vue'
import { state, enterFree } from '../store.js'
import { guide, setGuide, say } from '../guide.js'
import { t, lang, setLang, LANGS } from '../i18n.js'
import { ICON } from '../content.js'

const root = document.documentElement
const dark = ref(root.dataset.theme !== 'light')   // night is the default look
const menu = ref(false)

function toggleTheme() {
  dark.value = !dark.value
  root.dataset.theme = dark.value ? 'dark' : 'light'
  try { localStorage.setItem('fs-theme', root.dataset.theme) } catch {}
}
function setMode(m) {
  state.mode = m
  try { localStorage.setItem('fs-mode', m) } catch {}
  say(() => t(m === 'farmer' ? 'Farmer mode: I\'ll show you tools you know, like a thermometer and a rain gauge, and tell you what they mean.'
    : 'Pro mode: numbers, units and charts. Same NASA data, more detail.'), m === 'farmer' ? 'happy' : 'thinking')
}
// Back to the place picker: the whole department, or one province.
function pick(province = null) { state.province = province; state.stage = 'where' }
const print = () => window.print()
</script>

<template>
  <header class="fixed inset-x-0 top-0 z-40 border-b border-line bg-bg/90 print:hidden">
    <div class="flex h-12 items-center gap-2 px-3">
      <button type="button" class="flex shrink-0 items-center gap-2 whitespace-nowrap font-display text-[17px] font-semibold text-ink" :title="t('Back to the start')" :aria-label="t('Back to the start')" @click="state.stage = 'intro'">
        <span class="inline-block size-3 bg-teal" aria-hidden="true" /><span :class="{ 'max-sm:hidden': state.stage !== 'intro' }">Field Shift</span>
      </button>

      <nav v-if="state.stage !== 'intro'" class="flex min-w-0 items-center gap-1 font-mono text-xs uppercase tracking-wider text-muted" :aria-label="t('Where you are')">
        <span aria-hidden="true">/</span>
        <button type="button" class="truncate hover:text-teal" @click="pick()">Lambayeque</button>
        <template v-if="state.stage === 'explore' && state.area?.kind === 'district'">
          <span aria-hidden="true">/</span>
          <button type="button" class="truncate hover:text-teal max-sm:hidden" @click="pick(state.area.province)">{{ state.area.province }}</button>
          <span aria-hidden="true" class="max-sm:hidden">/</span>
          <span class="truncate text-ink">{{ state.area.name }}</span>
        </template>
        <template v-else-if="state.stage === 'explore'">
          <span aria-hidden="true">/</span><span class="truncate text-ink">{{ t('free mode') }}</span>
        </template>
        <template v-else-if="state.province">
          <span aria-hidden="true">/</span><span class="truncate text-ink">{{ state.province }}</span>
        </template>
      </nav>

      <div class="ml-auto flex items-center gap-2">
        <div class="seg" role="group" :aria-label="t('Language')">
          <button v-for="[code, label, name] in LANGS" :key="code" type="button" :aria-pressed="lang === code" :title="name" @click="setLang(code)">{{ label }}</button>
        </div>
        <button type="button" class="btn md:hidden" :aria-expanded="menu" :aria-label="t('Settings')" @click="menu = !menu">≡</button>
        <div class="items-center gap-2 md:flex" :class="menu ? 'absolute right-2 top-12 z-50 flex flex-col items-stretch border border-line bg-panel p-2' : 'hidden'">
          <div v-if="state.stage === 'explore'" class="seg" role="group" :aria-label="t('View mode')">
            <button type="button" :aria-pressed="state.mode === 'farmer'" @click="setMode('farmer')">{{ t('Farmer') }}</button>
            <button type="button" :aria-pressed="state.mode === 'pro'" @click="setMode('pro')">{{ t('Pro') }}</button>
          </div>
          <button v-if="state.stage === 'explore' && state.area?.kind === 'district'" type="button" class="btn" :title="t('Open the whole department and tap anywhere')" @click="enterFree()">{{ t('Free mode') }}</button>
          <button type="button" class="btn" :aria-pressed="guide.on" :title="t('Sprout explains each screen by itself')" @click="setGuide(!guide.on)">Sprout: {{ t(guide.on ? 'on' : 'off') }}</button>
          <button v-if="state.stage === 'explore'" type="button" class="btn" :title="t('Print the report or save it as a PDF')" @click="print">PDF</button>
          <button type="button" class="btn !px-2" :aria-label="t(dark ? 'Switch to light mode' : 'Switch to dark mode')" @click="toggleTheme">
            <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="dark ? ICON.sun : ICON.moon" />
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
