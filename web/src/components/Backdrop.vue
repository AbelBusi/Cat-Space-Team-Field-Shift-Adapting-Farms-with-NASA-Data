<script setup>
import OrbitSky from './OrbitSky.vue'

// The night sky and the hills behind every screen. Once the visit starts the hills sink, so the sky is free
// for the territory, like a camera tilting up from the campfire.
defineProps({ low: Boolean })
</script>

<template>
  <div class="fixed inset-0 z-0 overflow-hidden bg-sky-bg print:hidden" aria-hidden="true">
    <OrbitSky class="absolute inset-0 h-full w-full" />
    <div class="absolute inset-x-0 bottom-0 h-[46%] transition-transform duration-[1200ms] ease-soft" :class="low ? 'translate-y-[64%]' : ''">
      <!-- Landscape silhouettes: Andes far away, coastal hills, algarrobo trees and the campfire. -->
      <svg class="land absolute inset-0 h-full w-full" viewBox="0 0 1440 360" preserveAspectRatio="xMidYMax slice">
        <path class="far" d="M0 210 L120 150 L210 185 L330 110 L430 170 L560 95 L660 160 L780 120 L900 175 L1010 105 L1130 165 L1250 120 L1350 160 L1440 140 L1440 360 L0 360Z" />
        <path class="mid" d="M0 270 C160 230 300 255 450 238 C600 222 700 262 860 246 C1010 232 1150 258 1300 240 C1370 232 1410 236 1440 238 L1440 360 L0 360Z" />
        <g class="near">
          <path d="M0 312 C240 296 480 306 720 300 C960 294 1200 304 1440 296 L1440 360 L0 360Z" />
          <path d="M120 302 L122 262 L104 250 L124 254 L126 232 L98 222 L130 226 L140 206 L150 228 L180 214 L154 236 L176 246 L150 250 L148 300Z" />
          <path d="M1240 300 L1244 252 L1216 238 L1246 242 L1250 212 L1226 196 L1256 204 L1268 182 L1278 206 L1310 196 L1284 218 L1306 232 L1276 238 L1272 298Z" />
          <path d="M1330 298 L1332 270 L1316 262 L1334 264 L1338 246 L1352 262 L1368 258 L1350 272 L1350 298Z" />
        </g>
      </svg>
      <div class="campfire absolute bottom-[28%] left-[calc(50%+4px)] h-[26px] w-[22px]"><i /><i /><i /></div>
    </div>
  </div>
</template>
