<script setup>
import { ref } from 'vue'
import Reveal from './Reveal.vue'
import { CRIT, LEVELS, ICON } from '../content.js'
import { state, ranking } from '../store.js'
import { useScript, say } from '../guide.js'
import { t } from '../i18n.js'

const el = ref(null)
useScript('prio', el)

function bump(k) {
  const before = ranking.value[0].r
  state.prio[k] = (state.prio[k] + 1) % 4
  const after = ranking.value[0].r
  if (after !== before) say(() => t('With what matters to you now, "{name}" fits best. Look, it moved to the front!', { name: t(after.name) }), 'surprised')
}
</script>

<template>
  <section ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">3</span>
        <h2>{{ t('What matters most to you?') }}</h2>
        <p>{{ t('Tap each card to raise its importance, from none to a lot. The rotations below reorder instantly.') }}</p>
      </div>
      <Reveal :at="1">
        <div class="prio-grid">
          <button v-for="c in CRIT" :key="c.k" type="button" class="prio" :data-level="state.prio[c.k]"
                  :aria-label="t('{name}: importance {level}. Tap to change.', { name: t(c.label), level: t(LEVELS[state.prio[c.k]]) })" @click="bump(c.k)">
            <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON[c.icon]" /></span>
            <span class="ptitle">{{ t(c.label) }}</span>
            <span class="muted small">{{ t(c.hint) }}</span>
            <span class="lvl"><span class="dots"><i v-for="i in 3" :key="i" :class="{ on: i <= state.prio[c.k] }" /></span>{{ t(LEVELS[state.prio[c.k]]) }}</span>
          </button>
        </div>
      </Reveal>
    </div>
  </section>
</template>
