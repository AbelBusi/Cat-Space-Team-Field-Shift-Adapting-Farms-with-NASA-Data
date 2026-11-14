<script setup>
import { computed } from 'vue'
import FieldRow from './FieldRow.vue'
import { LAYERS, LAYER_KEYS, MONTHS, CRIT, LEVELS, fitWord } from '../content.js'
import { state, db, series, climate, placeLabel, cell, history as H, ranking, risks, chosen, confidence, formatValue } from '../store.js'
import { t } from '../i18n.js'
import { NINO_COASTAL } from '../lib/nasa.js'
import { formatArea, formatShortDate } from '../lib/geo.js'
import { ADMIN_SOURCE } from '../lib/admin.js'

// The printed report: everything the visit showed, in plain tables. Hidden on screen, the only thing on paper.
const today = new Date().toISOString().slice(0, 10)
const keys = computed(() => LAYER_KEYS.filter(k => k !== 'water'))
</script>

<template>
  <article v-if="state.stage === 'explore' && state.point" class="report hidden bg-bg font-sans text-[11pt] leading-snug text-ink print:block">
    <header class="mb-4 border-b-2 border-ink pb-2">
      <div class="font-mono text-[9pt] uppercase tracking-widest text-teal">Field Shift · NASA Space Apps 2026</div>
      <h1 class="text-[20pt]">{{ t('Field report') }}: {{ placeLabel(state.point) }}</h1>
      <p class="text-muted">
        <template v-if="state.area?.province">{{ state.area.name }}, {{ state.area.province }}, </template>Lambayeque, Peru · {{ state.point.lat }}, {{ state.point.lon }}
        <template v-if="state.parcel"> · {{ t('Your field:') }} {{ formatArea(state.parcel.areaM2) }}</template> · {{ today }}
      </p>
    </header>

    <section class="mb-4">
      <h2 class="mb-1 text-[13pt]">1. {{ t('What the satellites see') }}</h2>
      <p>{{ climate?.label() }}<template v-if="db.recent"> · {{ t('Last 30 days') }} ({{ formatShortDate(db.recent.from) }} – {{ formatShortDate(db.recent.to) }}): {{ t('{mm} mm of rain on {days} days, {c} °C on average.', { mm: db.recent.rainMm.toFixed(1), days: db.recent.rainyDays, c: db.recent.tempC.toFixed(1) }) }}</template></p>
      <table class="mt-2 w-full border-collapse text-[9pt]">
        <thead><tr class="border-b border-ink text-left"><th class="py-1 pr-2">{{ t('Typical year') }}</th><th v-for="m in MONTHS" :key="m" class="px-1 text-right font-mono">{{ t(m).slice(0, 3) }}</th></tr></thead>
        <tbody>
          <tr v-for="k in keys" :key="k" class="border-b border-line"><td class="py-1 pr-2">{{ t(LAYERS[k].name) }} <span class="text-muted">({{ LAYERS[k].unit }})</span></td>
            <td v-for="(v, i) in series(k, 'normal') || MONTHS.map(() => null)" :key="i" class="px-1 text-right font-mono">{{ v == null ? '–' : k === 'veg' ? v.toFixed(2) : k === 'heat' ? v.toFixed(1) : Math.round(v) }}</td></tr>
          <tr class="border-b border-line"><td class="py-1 pr-2">{{ t('Rain') }}, {{ t('El Niño years') }} <span class="text-muted">(mm)</span></td>
            <td v-for="(v, i) in series('rain', 'nino') || MONTHS.map(() => null)" :key="i" class="px-1 text-right font-mono">{{ v == null ? '–' : Math.round(v) }}</td></tr>
        </tbody>
      </table>
      <p v-if="cell" class="mt-2">{{ t('Ground · NASADEM 30 m, cell mean') }}: {{ t('{m} m above sea · slope {deg}°', { m: cell.elev, deg: cell.slope }) }}.
        {{ t('Underground water') }}: {{ formatValue('water', cell.water.trend_cm_per_year) }} ({{ t('trend 2002–2026, regional') }}).</p>
    </section>

    <section v-if="H" class="mb-4">
      <h2 class="mb-1 text-[13pt]">2. {{ t('Your place, year by year') }} (1981–2024)</h2>
      <ul class="list-disc pl-5">
        <li>{{ t('Wettest year') }}: <b>{{ H.wettest.y }}</b>, {{ t('{n} mm · average {avg} mm', { n: H.wettest.rain, avg: H.meanRain }) }}</li>
        <li>{{ t('Driest year') }}: <b>{{ H.driest.y }}</b>, {{ t('{n} mm of rain', { n: H.driest.rain }) }}</li>
        <li>{{ t('Afternoons now vs 1981–2000') }}: <b>{{ H.warming > 0 ? '+' : '' }}{{ H.warming }} °C</b>; {{ t('Rain {n} % over the same periods', { n: (H.rainChange > 0 ? '+' : '') + H.rainChange }) }}</li>
        <li>{{ t('El Niño years') }} (NOAA Niño 1+2): {{ NINO_COASTAL.join(', ') }}</li>
      </ul>
    </section>

    <section class="mb-4">
      <h2 class="mb-1 text-[13pt]">3. {{ t('What matters most to you?') }}</h2>
      <p><span v-for="(c, i) in CRIT" :key="c.k">{{ i ? ' · ' : '' }}{{ t(c.label) }}: <b>{{ t(LEVELS[state.prio[c.k]]) }}</b></span></p>
    </section>

    <section class="mb-4">
      <h2 class="mb-1 text-[13pt]">4. {{ t('How your year could look') }} <span class="font-mono text-[9pt] font-normal uppercase text-muted">({{ t('hypothetical scores') }})</span></h2>
      <div v-for="(x, i) in ranking" :key="x.r.id" class="mb-3 break-inside-avoid border border-line p-2">
        <div class="flex items-baseline justify-between"><b>{{ i + 1 }}. {{ t(x.r.name) }}</b><span class="font-mono text-[9pt]">{{ t(fitWord(x.score)) }} · {{ t('{n} out of 100', { n: x.score }) }}</span></div>
        <FieldRow class="my-1 max-w-[120mm]" :cal="x.r.cal" :score="x.score" :risks="risks" :month="-1" :floods="!!x.r.floods" />
        <p>{{ t('You gain:') }} {{ t(x.r.gain) }}. {{ t('You risk:') }} {{ t(x.r.lose) }}.</p>
        <p v-for="f in x.flags" :key="f" class="text-[9pt] text-muted">{{ f }}</p>
      </div>
    </section>

    <section class="mb-4">
      <h2 class="mb-1 text-[13pt]">5. {{ t('Chosen strategy') }}: {{ t(chosen.r.name) }}</h2>
      <p>{{ t(chosen.r.why) }}</p>
      <div class="mt-1 grid grid-cols-2 gap-4">
        <div><b>{{ t('What you gain') }}</b><ul class="list-disc pl-5"><li v-for="b in chosen.r.ben" :key="b">{{ t(b) }}</li></ul></div>
        <div><b>{{ t('What you risk') }}</b><ul class="list-disc pl-5"><li v-for="b in chosen.r.risks" :key="b">{{ t(b) }}</li></ul></div>
      </div>
      <p class="mt-1"><b>{{ t('What the satellites say') }}:</b> <span v-for="e in chosen.r.evid" :key="e[0]">{{ t(e[0]) }}: {{ t(e[1]) }} </span></p>
      <p class="mt-1"><b>{{ t('Confidence') }}: {{ t(confidence.level) }}</b> ({{ t('hypothetical') }}, {{ t('{n} out of 100', { n: confidence.score }) }})</p>
      <ul class="list-disc pl-5 text-[9pt] text-muted"><li v-for="x in confidence.reasons" :key="x">{{ x }}</li></ul>
    </section>

    <footer class="border-t border-ink pt-2 text-[8.5pt] text-muted">
      <p><b>{{ t('Where each number comes from') }}:</b> NASA POWER ({{ t('heat, soil wetness, yearly history; squares of about 55 km') }}) · GPM IMERG V07 ({{ t('rain; 11 km') }}) · MODIS MOD13Q1 via ORNL DAAC ({{ t('greenness; 250 m') }}) · GRACE-FO · NASADEM · NOAA Niño 1+2. {{ ADMIN_SOURCE }}.</p>
      <p>{{ t('The rotation scores and the confidence level are hypothetical expert rules, not measurements.') }} {{ t('This tool shows patterns and possibilities. The final word belongs to your experience and to an agronomist who knows your area.') }}</p>
      <p>These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program.</p>
    </footer>
  </article>
</template>
