<script setup>
import { ref, computed } from 'vue'
import Reveal from './Reveal.vue'
import YearRing from './YearRing.vue'
import RotationDetail from './RotationDetail.vue'
import { CROP, ICON } from '../content.js'
import { state, ranking, risks } from '../store.js'
import { useScript, say } from '../guide.js'

const el = ref(null)
const step = useScript('rots', el)
const selected = computed(() => state.rot || ranking.value[0].r.id)
const bare = cal => cal.split('').filter(k => k === 'B').length

function choose(r) {
  state.rot = r.id
  say(`${r.name}: you gain ${r.gain.toLowerCase()}, but you risk ${r.lose.toLowerCase()}.`, 'thinking')
}
</script>

<template>
  <section ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">3</span>
        <h2>How your year could look</h2>
        <p>Each ring is one year, January at the top and moving clockwise. Colors are crops and beige is bare soil. Dots outside are risky months at your spot, from real NASA POWER data, and the dark mark is the month you picked. These four are example rotations from the Peruvian coast; the crop library can grow for other regions.</p>
      </div>
      <Reveal :at="0">
        <TransitionGroup tag="div" name="rot" class="rot-grid">
          <button v-for="x in ranking" :key="x.r.id" type="button" class="rot" :aria-pressed="selected === x.r.id" @click="choose(x.r)">
            <span class="pills">
              <span v-if="x === ranking[0]" class="pill best">Best fit for you</span>
              <span v-if="x.r.id === 'current'" class="pill now">What you do today</span>
            </span>
            <YearRing :cal="x.r.cal" :score="x.score" :risks="risks" :month="state.month" :show-risks="step >= 1" />
            <span class="ptitle">{{ x.r.name }}</span>
            <span class="trade">
              <span><b class="gain-ink">You gain:</b> {{ x.r.gain }}</span>
              <span><b class="warn-ink">You risk:</b> {{ x.r.lose }}</span>
              <span class="muted">Months of bare soil: <b class="ink">{{ bare(x.r.cal) }}</b></span>
            </span>
            <span v-for="f in x.flags" :key="f" class="flag">{{ f }}</span>
          </button>
        </TransitionGroup>
      </Reveal>
      <Reveal :at="1">
        <div class="crop-legend">
          <span v-for="(c, k) in CROP" :key="k"><i :style="{ background: c.color }" />{{ c.name }}</span>
          <span><i class="dot" style="background:#D9480F" />Strong heat</span>
          <span><i class="dot" style="background:#1D5FA8" />Heavy rain</span>
          <span><i class="dot" style="background:#A9772E" />Dry soil</span>
          <span><i class="dot" style="background:#7FC8F8" />Frost risk</span>
        </div>
      </Reveal>
      <Reveal :at="2"><RotationDetail :id="selected" /></Reveal>
      <Reveal :at="4">
        <div class="remind">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON.info" />
          <span>This tool shows patterns and possibilities. The final word belongs to your experience and to an agronomist who knows your area.</span>
        </div>
      </Reveal>
    </div>
  </section>
</template>
