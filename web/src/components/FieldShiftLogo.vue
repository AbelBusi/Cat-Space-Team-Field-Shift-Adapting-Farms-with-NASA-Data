<script setup>
import PixelIcon from './PixelIcon.vue'
// The Field Shift mark: a sprout over furrows, swaying in two frames (stops with prefers-reduced-motion).
defineProps({ size: { type: Number, default: 1.5 } })
</script>

<template>
  <span class="fs-logo relative inline-block shrink-0" :style="{ width: 16 * size + 'px', height: 16 * size + 'px' }" aria-hidden="true">
    <PixelIcon name="logo_a" :size="size" class="absolute inset-0" />
    <PixelIcon name="logo_b" :size="size" class="frame-b absolute inset-0" />
  </span>
</template>

<style scoped>
.frame-b { animation: sway 1.6s steps(1) infinite; }
.fs-logo .px-icon:first-child { animation: sway 1.6s steps(1) infinite reverse; }
@keyframes sway { 0% { opacity: 0; } 50% { opacity: 1; } }
</style>
