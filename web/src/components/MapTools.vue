<script setup>
import { state, mapUi, mapApi } from '../store.js'
import { t } from '../i18n.js'
import { formatArea } from '../lib/geo.js'

// The few actions of the map, as one row of HUD buttons: zoom, whole view, find me, outline my field.
</script>

<template>
  <div class="pointer-events-auto flex flex-wrap items-center justify-center gap-1">
    <template v-if="mapUi.drawing">
      <span class="border border-fire bg-panel/90 px-2 py-1.5 font-mono text-xs">{{ mapUi.corners < 3 ? t('Tap at least 3 corners (you have {n}).', { n: mapUi.corners }) : t('{n} corners. Press Finish when done.', { n: mapUi.corners }) }}</span>
      <button type="button" class="btn" :disabled="!mapUi.corners" @click="mapApi.undoCorner()">{{ t('Undo') }}</button>
      <button type="button" class="btn btn-fire" :disabled="mapUi.corners < 3" @click="mapApi.finishOutline()">{{ t('Finish') }}</button>
      <button type="button" class="btn" @click="mapApi.clearOutline()">{{ t('Cancel') }}</button>
    </template>
    <template v-else>
      <button type="button" class="btn !w-9 !px-0 text-base" :aria-label="t('Zoom out')" :title="t('Zoom out')" @click="mapApi.zoomOut()">−</button>
      <button type="button" class="btn !w-9 !px-0 text-base" :aria-label="t('Zoom in')" :title="t('Zoom in')" @click="mapApi.zoomIn()">+</button>
      <button type="button" class="btn !w-9 !px-0" :aria-label="t('Show the whole territory again')" :title="t('Show the whole territory again')" @click="mapApi.refit()">
        <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg>
      </button>
      <button type="button" class="btn" :aria-pressed="mapUi.labels" :title="t('Show or hide town names')" @click="mapUi.labels = !mapUi.labels">{{ t('Names') }}</button>
      <button type="button" class="btn" @click="mapApi.locateMe()">{{ t('My location') }}</button>
      <button v-if="!state.parcel" type="button" class="btn" :title="t('Outline your land to get its size and read NASA data at its center.')" @click="mapApi.startOutline()">{{ t('Outline my field') }}</button>
      <template v-else>
        <span class="border border-fire bg-panel/90 px-2 py-1.5 font-mono text-xs">{{ t('Your field:') }} {{ formatArea(state.parcel.areaM2) }}</span>
        <button type="button" class="btn" @click="mapApi.editOutline()">{{ t('Edit outline') }}</button>
        <button type="button" class="btn" @click="mapApi.clearOutline()">{{ t('Delete') }}</button>
      </template>
    </template>
  </div>
</template>
