<script setup>
import { ref, onMounted } from 'vue'
import HeroSection from './components/HeroSection.vue'
import MapSection from './components/MapSection.vue'
import Priorities from './components/Priorities.vue'
import Rotations from './components/Rotations.vue'
import Glossary from './components/Glossary.vue'
import CatDialogue from './cat/CatDialogue.vue'
import { ICON, PLACES } from './content.js'
import { selectPoint } from './store.js'

onMounted(() => selectPoint(PLACES[0].lat, PLACES[0].lon, PLACES[0].name))

const root = document.documentElement
const dark = ref(root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches)
function toggleTheme() {
  dark.value = !dark.value
  root.dataset.theme = dark.value ? 'dark' : 'light'
  try { localStorage.setItem('fs-theme', root.dataset.theme) } catch {}
}
</script>

<template>
  <div class="topbar">
    <div class="wrap">
      <div class="brand"><span class="brand-dot" aria-hidden="true" /><span>Field Shift<span class="wide-only"> · Listen to your field</span></span></div>
      <div class="top-right">
        <span class="badge"><span class="wide-only">Prototype · </span>live NASA data</span>
        <button type="button" class="theme-btn" :aria-label="dark ? 'Switch to light mode' : 'Switch to dark mode'" @click="toggleTheme">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="dark ? ICON.sun : ICON.moon" />
          <span class="wide-only" aria-hidden="true">{{ dark ? 'Light mode' : 'Dark mode' }}</span>
        </button>
      </div>
    </div>
  </div>

  <HeroSection />
  <main>
    <MapSection />
    <Priorities />
    <Rotations />
    <Glossary />
  </main>
  <footer>
    <div class="wrap">
      <div><b>Live data:</b> heat, rain and soil wetness from <a href="https://power.larc.nasa.gov">NASA POWER</a> (monthly, 2001–2024); plant greenness from MODIS MOD13Q1 via the <a href="https://modis.ornl.gov">ORNL DAAC</a> (2024). Map imagery: NASA GIBS, Blue Marble.</div>
      <div><b>Still hypothetical:</b> the rotation scores (1–5 per topic) and the confidence meter. Coming during the hackathon: GPM IMERG, SMAP, HLS, GRACE-FO, SoilGrids and FAO-56 crop water use.</div>
      <div>These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program. Made for NASA Space Apps Chiclayo 2026.</div>
    </div>
  </footer>
  <CatDialogue />
</template>
