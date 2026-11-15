<script setup>
import { computed } from 'vue'
import * as d3 from 'd3'
import HudCard from './HudCard.vue'
import { proj, colorScale, nPeriods, periodLabel } from '../lib/projections.js'
import { MONTHS } from '../content.js'
import { t } from '../i18n.js'

// The period shown on the map (‹ month ›) and its color legend. `diff`: colors are the change against a normal year.
const props = defineProps({ v: String, diff: Boolean, title: String })
const k = defineModel({ type: Number, default: 0 })
const n = computed(() => nPeriods(props.v))
const label = computed(() => proj.value ? periodLabel(props.v, proj.value.meta.periods[props.v][k.value], MONTHS, t) : '…')
const useful = computed(() => proj.value?.meta.useful_lead[props.v === 'ndvi' ? 'ndvi_quarters' : 'soil_water_months'] ?? 0)
const stops = computed(() => {
  if (!proj.value) return ''
  const sc = colorScale(props.v, props.diff), [a, b] = sc.domain().length > 4 ? [sc.domain()[0], sc.domain().at(-1)] : [sc.domain()[0], sc.domain().at(-1)]
  return d3.range(0, 1.0001, 0.125).map(p => sc(a + p * (b - a))).join(',')
})
const ends = computed(() => {
  if (!proj.value) return ['', '']
  if (props.diff) return [t(props.v === 'ndvi' ? 'Less green' : 'Drier'), t(props.v === 'ndvi' ? 'Greener' : 'Wetter')]
  const [a, b] = proj.value.meta.domain[props.v].map(x => x / proj.value.meta.scale)
  return props.v === 'ndvi' ? [`${t('Bare')} ${a.toFixed(2)}`, `${b.toFixed(2)} ${t('Green')}`] : [`${t('Dry')} ${a.toFixed(2)}`, `${b.toFixed(2)} ${t('Wet')}`]
})
</script>

<template>
  <HudCard :title="title || t('On the map')">
    <div class="flex items-center gap-2">
      <button type="button" class="btn !w-9 !px-0" :disabled="k === 0" :aria-label="t('Previous')" @click="k--">‹</button>
      <div class="min-w-0 flex-1 text-center">
        <div class="font-mono text-sm uppercase tracking-wider text-ink">{{ label }}</div>
        <div class="font-mono text-[10px] uppercase tracking-wider" :class="k + 1 <= useful ? 'text-teal' : 'text-muted'">
          {{ k + 1 <= useful ? t('projection') : t('closer to a typical year') }}
        </div>
      </div>
      <button type="button" class="btn !w-9 !px-0" :disabled="k >= n - 1" :aria-label="t('Next')" @click="k++">›</button>
    </div>
    <div class="h-2.5 w-full" :style="{ background: `linear-gradient(90deg, ${stops})` }" aria-hidden="true" />
    <div class="flex justify-between font-mono text-[10px] text-muted"><span>{{ ends[0] }}</span><span>{{ ends[1] }}</span></div>
    <p class="text-xs text-muted">{{ t('Each colored square is one 2 km cell. Tap one to read it.') }}</p>
  </HudCard>
</template>
