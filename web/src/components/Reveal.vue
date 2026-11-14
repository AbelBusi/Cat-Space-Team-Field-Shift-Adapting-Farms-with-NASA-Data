<script setup>
import { inject } from 'vue'

// Shows its content once Sprout's script for this section reaches line `at`.
defineProps({ at: { type: Number, default: 0 } })
const step = inject('step')
const now = inject('now')
</script>

<template>
  <div class="reveal" :class="{ on: step >= at, now: now === at }"><slot /></div>
</template>
