<script setup>
import { ref } from 'vue'
import Reveal from './Reveal.vue'
import { GLOSSARY } from '../content.js'
import { useScript } from '../guide.js'

const el = ref(null)
useScript('gloss', el)
</script>

<template>
  <section id="how" ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">5</span>
        <h2>Satellite words, made simple</h2>
      </div>
      <Reveal :at="0">
        <div class="gloss">
          <details v-for="([term, text], i) in GLOSSARY" :key="term" class="card" :open="i === 0"><summary>{{ term }}</summary><p>{{ text }}</p></details>
        </div>
      </Reveal>
    </div>
  </section>
</template>
