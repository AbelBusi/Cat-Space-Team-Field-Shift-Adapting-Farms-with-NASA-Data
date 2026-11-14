<script setup>
// One insight on the map: a small HUD panel with a mono label. Keep one idea per card.
defineProps({ title: String })
</script>

<template>
  <section class="hud pointer-events-auto flex flex-col gap-2 bg-panel/90 p-3 text-sm">
    <h3 v-if="title" class="label">{{ title }}</h3>
    <slot />
  </section>
</template>
