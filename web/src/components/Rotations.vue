<script setup>
import { ref, computed } from 'vue'
import Reveal from './Reveal.vue'
import FieldRow from './FieldRow.vue'
import PixelIcon from './PixelIcon.vue'
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
        <span class="step-num">4</span>
        <h2>How your year could look</h2>
        <p>Each row is one year, January to December, like walking along a furrow. The color strip under each plant is the crop. Icons above mark risky months at your spot, from real NASA POWER data, and the framed column is the month you picked. These four are example rotations from the Peruvian coast; the crop library can grow for other regions.</p>
      </div>
      <Reveal :at="0">
        <TransitionGroup tag="div" name="rot" class="rot-grid">
          <button v-for="x in ranking" :key="x.r.id" type="button" class="rot" :aria-pressed="selected === x.r.id" @click="choose(x.r)">
            <span class="pills">
              <span v-if="x === ranking[0]" class="pill best">Best fit for you</span>
              <span v-if="x.r.id === 'current'" class="pill now">What you do today</span>
            </span>
            <FieldRow :cal="x.r.cal" :score="x.score" :risks="step >= 1 ? risks : []" :month="state.month" :floods="!!x.r.floods" />
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
          <span><PixelIcon name="seed" :size="1" />Sowing</span>
          <span><PixelIcon name="plant_ok" :size="1" />Growing well</span>
          <span><PixelIcon name="plant_thirsty" :size="1" />Stressed</span>
          <span><PixelIcon name="harvest" :size="1" />Harvest</span>
          <span><PixelIcon name="sun" :size="1" />Strong heat</span>
          <span><PixelIcon name="rain" :size="1" />Heavy rain</span>
          <span><PixelIcon name="bare" :size="1" />Bare soil</span>
          <span><PixelIcon name="frost" :size="1" />Frost</span>
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
