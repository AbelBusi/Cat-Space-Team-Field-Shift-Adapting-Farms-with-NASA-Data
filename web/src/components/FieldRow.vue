<script setup>
import { computed } from 'vue'
import PixelIcon from './PixelIcon.vue'
import { CROP, MONTHS, M1, fitWord } from '../content.js'
import { state as app } from '../store.js'
import { useTween } from '../lib/tween.js'

// A year as a row of 12 plants, January to December: what a farmer would see walking along the furrow.
const props = defineProps({ cal: String, score: Number, risks: Array, month: Number, floods: Boolean })
// Dry soil is not marked on top: it already shows as a thirsty plant.
const RISK_ICON = { heat: 'sun', rain: 'rain', frost: 'frost' }
const cols = computed(() => props.cal.split('').map((k, i, all) => {
  const r = props.risks[i] || {}
  const marks = Object.keys(RISK_ICON).filter(x => r[x]).map(x => RISK_ICON[x]).slice(0, 2)
  let icon = 'bare'
  if (k !== 'B') {
    const first = all[i - 1] !== k, last = all[i + 1] !== k
    const stressed = r.heat || r.dry || r.frost || (r.rain && props.floods)
    icon = first ? 'seed' : last ? 'harvest' : stressed ? 'plant_thirsty' : 'plant_ok'
  }
  return { k, i, icon, marks, crop: CROP[k] }
}))
const shown = useTween(() => props.score, 800)
const state = computed(() => props.score >= 70 ? 'plant_ok' : props.score >= 45 ? 'plant_thirsty' : 'plant_dead')
const summary = computed(() => `Fit ${props.score} out of 100. ` + cols.value.map(c => `${MONTHS[c.i]}: ${c.crop.name}`).join(', '))
</script>

<template>
  <div class="field-row" role="img" :aria-label="summary">
    <div class="fr-score"><PixelIcon :name="state" :size="2" /><template v-if="app.mode === 'pro'"><b>{{ Math.round(shown) }}</b><span>/100 fit</span></template><b v-else class="fit-word">{{ fitWord(score) }}</b></div>
    <div class="fr-grid">
      <div v-for="c in cols" :key="c.i" class="fr-col" :class="{ now: c.i === month }" :style="{ '--i': c.i }">
        <span class="fr-marks"><PixelIcon v-for="m in c.marks" :key="m" :name="m" :size="1" /></span>
        <PixelIcon :name="c.icon" :size="2" />
        <span class="fr-band" :style="{ background: c.crop.color }" />
        <span class="fr-m">{{ M1[c.i] }}</span>
      </div>
    </div>
  </div>
</template>
