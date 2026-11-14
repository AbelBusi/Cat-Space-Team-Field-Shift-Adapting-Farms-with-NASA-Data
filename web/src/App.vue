<script setup>
// Footer credits: HTML strings we write ourselves, translated in i18n.js.
const FOOT = ["<b>Live data:</b> heat, rain and soil wetness from <a href=\"https://power.larc.nasa.gov\">NASA POWER</a> (monthly, 2001–2024); plant greenness from MODIS MOD13Q1 via the <a href=\"https://modis.ornl.gov\">ORNL DAAC</a> (2024). Map imagery: NASA GIBS, Blue Marble.", "<b>Still hypothetical:</b> the rotation scores (1–5 per topic) and the confidence meter. Coming during the hackathon: GPM IMERG, SMAP, HLS, GRACE-FO, SoilGrids and FAO-56 crop water use.", "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program. Made for NASA Space Apps Chiclayo 2026."]
import { ref, onMounted, onBeforeUnmount } from 'vue'
import HeroSection from './components/HeroSection.vue'
import MapSection from './components/MapSection.vue'
import YearsSection from './components/YearsSection.vue'
import Priorities from './components/Priorities.vue'
import Rotations from './components/Rotations.vue'
import Glossary from './components/Glossary.vue'
import CatDialogue from './cat/CatDialogue.vue'
import { ICON, PLACES } from './content.js'
import { selectPoint, state } from './store.js'
import { say, showEverything } from './guide.js'
import { t, lang, setLang, LANGS } from './i18n.js'
import { PLACES as DEMO_PLACES } from './demoPlaces.js'

onMounted(() => selectPoint(PLACES[0].lat, PLACES[0].lon, PLACES[0].name))

// The page sky warms up like a sunrise as you scroll down (drives --scroll, 0 at the top → 1 at the bottom).
let ticking = false
function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    const max = document.documentElement.scrollHeight - innerHeight
    document.documentElement.style.setProperty('--scroll', max > 0 ? (scrollY / max).toFixed(3) : '0')
    ticking = false
  })
}
onMounted(() => { addEventListener('scroll', onScroll, { passive: true }); onScroll() })
onBeforeUnmount(() => removeEventListener('scroll', onScroll))

const root = document.documentElement
const dark = ref(root.dataset.theme !== 'light')   // night is the default look
function setMode(m) {
  state.mode = m
  try { localStorage.setItem('fs-mode', m) } catch {}
  say(() => t(m === 'farmer' ? 'Farmer mode: I\'ll show you tools you know, like a thermometer and a rain gauge, and tell you what they mean.'
    : 'Pro mode: numbers, units and charts. Same NASA data, more detail.'), m === 'farmer' ? 'happy' : 'thinking')
}
// Demo data: instant saved NASA snapshots for a few places, and every section shown at once.
function toggleDemo() {
  state.demo = !state.demo
  if (state.demo) {
    showEverything()
    const p = DEMO_PLACES[0]
    selectPoint(p.lat, p.lon, p.name)
  } else if (state.point) {
    selectPoint(state.point.lat, state.point.lon, state.point.name)
  }
}
function toggleTheme() {
  dark.value = !dark.value
  root.dataset.theme = dark.value ? 'dark' : 'light'
  try { localStorage.setItem('fs-theme', root.dataset.theme) } catch {}
}
</script>

<template>
  <div class="atmos" aria-hidden="true"><i class="glow-teal" /><i class="glow-teal2" /><i class="glow-fire" /><i class="glow-ghost" /><i class="stars" /></div>
  <div class="topbar">
    <div class="wrap">
      <div class="brand"><span class="brand-dot" aria-hidden="true" /><span>Field Shift<span class="wide-only"> · {{ t('Listen to your field') }}</span></span></div>
      <div class="top-right">
        <div class="seg mode-seg" role="group" :aria-label="t('Language')">
          <button v-for="[code, label, name] in LANGS" :key="code" type="button" :aria-pressed="lang === code" :title="name" @click="setLang(code)">{{ label }}</button>
        </div>
        <div class="seg mode-seg" role="group" :aria-label="t('View mode')">
          <button type="button" :aria-pressed="state.mode === 'farmer'" @click="setMode('farmer')">{{ t('Farmer') }}</button>
          <button type="button" :aria-pressed="state.mode === 'pro'" @click="setMode('pro')">{{ t('Pro') }}</button>
        </div>
        <span class="badge wide-only">{{ t(state.demo ? 'Demo · saved NASA data' : 'Prototype · live NASA data') }}</span>
        <button type="button" class="demo-btn" :aria-pressed="state.demo" :title="t('Load saved NASA data for Chiclayo, Iowa and Punjab instantly and show every section')" @click="toggleDemo">{{ t(state.demo ? '[ demo on ]' : '[ demo data ]') }}</button>
        <button type="button" class="theme-btn" :aria-label="t(dark ? 'Switch to light mode' : 'Switch to dark mode')" @click="toggleTheme">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="dark ? ICON.sun : ICON.moon" />
          <span class="wide-only" aria-hidden="true">{{ t(dark ? 'Light mode' : 'Dark mode') }}</span>
        </button>
      </div>
    </div>
  </div>

  <HeroSection />
  <main>
    <MapSection />
    <YearsSection />
    <Priorities />
    <Rotations />
    <Glossary />
  </main>
  <footer>
    <div class="wrap">
      <div v-html="t(FOOT[0])" />
      <div v-html="t(FOOT[1])" />
      <div v-html="t(FOOT[2])" />
    </div>
  </footer>
  <CatDialogue />
</template>
