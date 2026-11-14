<script setup>
import { ref } from 'vue'
import OrbitSky from './OrbitSky.vue'
import Reveal from './Reveal.vue'
import PixelIcon from './PixelIcon.vue'
import CatSprite from '../cat/CatSprite.vue'
import { LAYERS, LAYER_KEYS } from '../content.js'
import { guide, line, useScript } from '../guide.js'
import { state } from '../store.js'
import { meow, unlock } from '../lib/sound.js'

const el = ref(null)
useScript('hero', el)
const SIGNAL_ICON = { heat: 'sun', rain: 'rain', soil: 'drop', veg: 'plant_ok', water: 'down' }

function pet() {
  unlock()
  if (!guide.muted) meow(line.value?.[1] || 'happy')
}
const go = sel => document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
function pick(k) { state.layer = k; go('.map-stage') }
</script>

<template>
  <header ref="el" class="hero">
    <OrbitSky />
    <!-- Landscape silhouettes: Andes far away, coastal hills, algarrobo trees and the campfire. -->
    <svg class="land" viewBox="0 0 1440 360" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <path class="far" d="M0 210 L120 150 L210 185 L330 110 L430 170 L560 95 L660 160 L780 120 L900 175 L1010 105 L1130 165 L1250 120 L1350 160 L1440 140 L1440 360 L0 360Z" />
      <path class="mid" d="M0 270 C160 230 300 255 450 238 C600 222 700 262 860 246 C1010 232 1150 258 1300 240 C1370 232 1410 236 1440 238 L1440 360 L0 360Z" />
      <g class="near">
        <path d="M0 312 C240 296 480 306 720 300 C960 294 1200 304 1440 296 L1440 360 L0 360Z" />
        <path d="M120 302 L122 262 L104 250 L124 254 L126 232 L98 222 L130 226 L140 206 L150 228 L180 214 L154 236 L176 246 L150 250 L148 300Z" />
        <path d="M1240 300 L1244 252 L1216 238 L1246 242 L1250 212 L1226 196 L1256 204 L1268 182 L1278 206 L1310 196 L1284 218 L1306 232 L1276 238 L1272 298Z" />
        <path d="M1330 298 L1332 270 L1316 262 L1334 264 L1338 246 L1352 262 L1368 258 L1350 272 L1350 298Z" />
      </g>
    </svg>
    <div class="campfire" aria-hidden="true"><i /><i /><i /></div>
    <button type="button" class="hero-cat" aria-label="Pet Sprout" @click="pet">
      <CatSprite :mood="line?.[1] || 'happy'" :talking="guide.talking" :size="96" />
    </button>

    <div class="hero-copy wrap">
      <div class="eyebrow">NASA Space Apps 2026 · Field Shift</div>
      <h1>Your field is already talking.<br>Let's learn to listen.</h1>
      <p class="lead">NASA satellites measure heat, rain, soil wetness and plant greenness for every field on Earth. Sprout translates them so you can choose what to plant next.</p>
      <div class="hero-actions">
        <button type="button" class="btn-fire" @click="go('.map-stage')">Explore your field</button>
        <button type="button" class="btn-line" @click="go('#how')">How it works</button>
      </div>
      <Reveal :at="1">
        <div class="signals" role="group" aria-label="Satellite signals">
          <button v-for="k in LAYER_KEYS" :key="k" type="button" class="signal-chip" :aria-pressed="state.layer === k" @click="pick(k)">
            <PixelIcon :name="SIGNAL_ICON[k]" :size="1" />{{ LAYERS[k].name }}<small v-if="LAYERS[k].pending"> (soon)</small>
          </button>
        </div>
      </Reveal>
    </div>
  </header>
</template>
