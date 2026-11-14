<script setup>
import { ref, computed } from 'vue'
import Reveal from './Reveal.vue'
import FieldRow from './FieldRow.vue'
import PixelIcon from './PixelIcon.vue'
import RotationDetail from './RotationDetail.vue'
import { CROP, ICON } from '../content.js'
import { state, ranking, risks } from '../store.js'
import { useScript, say } from '../guide.js'
import { t } from '../i18n.js'

const el = ref(null)
const step = useScript('rots', el)
const selected = computed(() => state.rot || ranking.value[0].r.id)
const bare = cal => cal.split('').filter(k => k === 'B').length

function choose(r) {
  state.rot = r.id
  say(() => t('{name}: you gain {gain}, but you risk {lose}.', { name: t(r.name), gain: t(r.gain).toLowerCase(), lose: t(r.lose).toLowerCase() }), 'thinking')
}
</script>

<template>
  <section ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">4</span>
        <h2>{{ t('How your year could look') }}</h2>
        <p>{{ t('Each row is one year, January to December, like walking along a furrow. The color strip under each plant is the crop. Icons above mark risky months at your spot, from real NASA POWER data, and the framed column is the month you picked. These four are example rotations from the Peruvian coast; the crop library can grow for other regions.') }}</p>
      </div>
      <Reveal :at="0">
        <TransitionGroup tag="div" name="rot" class="rot-grid">
          <button v-for="x in ranking" :key="x.r.id" type="button" class="rot" :aria-pressed="selected === x.r.id" @click="choose(x.r)">
            <span class="pills">
              <span v-if="x === ranking[0]" class="pill best">{{ t('Best fit for you') }}</span>
              <span v-if="x.r.id === 'current'" class="pill now">{{ t('What you do today') }}</span>
            </span>
            <FieldRow :cal="x.r.cal" :score="x.score" :risks="step >= 1 ? risks : []" :month="state.month" :floods="!!x.r.floods" />
            <span class="ptitle">{{ t(x.r.name) }}</span>
            <span class="trade">
              <span><b class="gain-ink">{{ t('You gain:') }}</b> {{ t(x.r.gain) }}</span>
              <span><b class="warn-ink">{{ t('You risk:') }}</b> {{ t(x.r.lose) }}</span>
              <span class="muted">{{ t('Months of bare soil:') }} <b class="ink">{{ bare(x.r.cal) }}</b></span>
            </span>
            <span v-for="f in x.flags" :key="f" class="flag">{{ f }}</span>
          </button>
        </TransitionGroup>
      </Reveal>
      <Reveal :at="1">
        <div class="crop-legend">
          <span v-for="(c, k) in CROP" :key="k"><i :style="{ background: c.color }" />{{ t(c.name) }}</span>
          <span><PixelIcon name="seed" :size="1" />{{ t('Sowing') }}</span>
          <span><PixelIcon name="plant_ok" :size="1" />{{ t('Growing well') }}</span>
          <span><PixelIcon name="plant_thirsty" :size="1" />{{ t('Stressed') }}</span>
          <span><PixelIcon name="harvest" :size="1" />{{ t('Harvest') }}</span>
          <span><PixelIcon name="sun" :size="1" />{{ t('Strong heat') }}</span>
          <span><PixelIcon name="rain" :size="1" />{{ t('Heavy rain') }}</span>
          <span><PixelIcon name="bare" :size="1" />{{ t('Bare soil') }}</span>
          <span><PixelIcon name="frost" :size="1" />{{ t('Frost') }}</span>
        </div>
      </Reveal>
      <Reveal :at="2"><RotationDetail :id="selected" /></Reveal>
      <Reveal :at="4">
        <div class="remind">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ICON.info" />
          <span>{{ t('This tool shows patterns and possibilities. The final word belongs to your experience and to an agronomist who knows your area.') }}</span>
        </div>
      </Reveal>
    </div>
  </section>
</template>
