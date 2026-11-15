<script setup>
// Fine-tune a what-if with the live ML service (ml-api/). Shown only when VITE_ML_API_URL is set; filled in the backend step.
const api = import.meta.env.VITE_ML_API_URL
</script>

<template>
  <div v-if="api" />
</template>
