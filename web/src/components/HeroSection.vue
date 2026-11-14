<script setup>
import { ref } from 'vue'
import OrbitSky from './OrbitSky.vue'
import Reveal from './Reveal.vue'
import CatSprite from '../cat/CatSprite.vue'
import { LAYERS, LAYER_KEYS, ICON } from '../content.js'
import { guide, line, useScript } from '../guide.js'
import { state } from '../store.js'
import { meow, unlock } from '../lib/sound.js'

const el = ref(null)
useScript('hero', el)

function pet() {
  unlock()
  if (!guide.muted) meow(line.value?.[1] || 'happy')
}

function pick(k) {
  state.layer = k
  document.querySelector('.map-stage')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
</script>

<template>
  <header ref="el" class="hero">
    <OrbitSky />
    <div class="wrap">
      <div>
        <div class="eyebrow">NASA Space Apps 2026 · Field Shift challenge</div>
        <h1>Your field is already talking. Let's learn to listen.</h1>
        <p class="lead">From space, NASA satellites measure heat, rain, soil wetness and plant greenness for every field on Earth. We bring those signals together to help you think about what to plant next year.</p>
      </div>
      <div class="hero-side">
        <button type="button" class="hero-cat" aria-label="Pet Sprout" @click="pet"><CatSprite :mood="line?.[1] || 'happy'" :talking="guide.talking" :size="168" /></button>
        <Reveal :at="1">
          <div class="hint">Five signals the satellites send. Tap one to see it on the map:</div>
          <div class="signals">
            <button v-for="k in LAYER_KEYS" :key="k" type="button" class="signal-chip" :aria-pressed="state.layer === k" @click="pick(k)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[LAYERS[k].icon]" />
              {{ LAYERS[k].name }}<small v-if="LAYERS[k].pending"> (soon)</small>
            </button>
          </div>
        </Reveal>
      </div>
    </div>
  </header>
</template>
