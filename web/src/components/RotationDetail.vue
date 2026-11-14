<script setup>
import { computed } from 'vue'
import Reveal from './Reveal.vue'
import TradeOffs from './TradeOffs.vue'
import { state, db, ranking } from '../store.js'
import { fitWord } from '../content.js'
import { t } from '../i18n.js'
import { gridCells } from '../lib/nasa.js'
import { say } from '../guide.js'

const props = defineProps({ id: String })
const cur = computed(() => ranking.value.find(x => x.r.id === props.id))
const base = computed(() => ranking.value.find(x => x.r.id === 'current'))

// Hypothetical confidence: what the data can see here, plus what the farmer already knows.
const conf = computed(() => {
  const nino = state.scen === 'nino', r = cur.value.r
  let c = 45 + (db.ndvi ? 10 : 0)
  c += (state.checks.soil ? 15 : 0) + (state.checks.water ? 12 : 0) + (state.checks.tried ? 10 : 0) - (nino ? 10 : 0) + (r.id === 'current' ? 8 : 0)
  return Math.max(10, Math.min(95, c))
})
const powerSize = computed(() => state.point ? gridCells(state.point.lat, state.point.lon)[0].size : 'about 55 km')
const level = computed(() => conf.value < 45 ? 'Low' : conf.value < 70 ? 'Medium' : 'High')
const reasons = computed(() => [
  t('Climate comes in NASA POWER cells of {size}: it describes the region, not your plot.', { size: powerSize.value }),
  t(db.ndvi ? 'Greenness comes from 250 m MODIS pixels: much closer to your field.' : 'Greenness is not loaded for this spot yet.'),
  t(state.checks.soil ? 'With your soil test, the suggestion is more precise.' : 'Your plot\'s soil test is missing.'),
  t(state.checks.water ? 'You know how much water you get, so fewer surprises.' : 'We don\'t know how much water you get per season.'),
  ...(!state.checks.tried && cur.value.r.id !== 'current' ? [t('You have never grown this here: try it on a small plot first.')] : []),
  ...(state.scen === 'nino' ? [t('An El Niño year is harder to predict.')] : []),
])
const CHECKS = [['soil', 'I have a recent soil test'], ['water', 'I know how much water I get per season'], ['tried', 'I have grown these crops before']]
function toggle(k, on) {
  state.checks[k] = on
  if (on) say(() => t("Thank you! That makes me more confident. Now I'm at {level} confidence.", { level: t(level.value).toLowerCase() }), 'happy')
}
</script>

<template>
  <div class="detail">
    <div class="card">
      <span class="tag">{{ t('Chosen strategy') }} · {{ state.mode === 'pro' ? t('{n} out of 100', { n: cur.score }) : t(fitWord(cur.score)) }}</span>
      <Transition name="flip" mode="out-in"><h3 :key="cur.r.id" class="detail-title">{{ t(cur.r.name) }}</h3></Transition>
      <p class="why">{{ t(cur.r.why) }}</p>
      <div class="gl">
        <div class="gain"><h4>{{ t('What you gain') }}</h4><ul><li v-for="b in cur.r.ben" :key="b">{{ t(b) }}</li></ul></div>
        <div class="risk"><h4>{{ t('What you risk') }}</h4><ul><li v-for="b in cur.r.risks" :key="b">{{ t(b) }}</li></ul></div>
      </div>
      <h4 class="evid-title">{{ t('What the satellites say') }}</h4>
      <ul class="evid"><li v-for="e in cur.r.evid" :key="e[0]"><b>{{ t(e[0]) }}:</b> {{ t(e[1]) }}</li></ul>
    </div>
    <div class="card">
      <h3>{{ t('Compared with what you do today') }}</h3>
      <div v-if="state.mode === 'pro'" class="tr-head"><span /><span>{{ t('Today') }}</span><span>{{ t(cur.r.name) }}</span><span /></div>
      <TradeOffs :base="base.sc" :pick="cur.sc" />
      <p class="muted small">{{ t(state.mode === 'pro' ? 'More filled squares = better on that topic (0 to 5). The arrow says if the change helps or hurts.' : 'Compared with what you grow today, topic by topic.') }}</p>
    </div>
    <Reveal :at="3">
      <div class="card">
        <h3>{{ t('How sure are we?') }}</h3>
        <div class="conf-head"><span class="muted">{{ t('Confidence') }}</span><b>{{ t(level) }}</b></div>
        <div class="meter" role="img" :aria-label="`Confidence ${conf} out of 100`"><i v-for="i in 10" :key="i" :class="{ on: i <= Math.round(conf / 10) }" :style="{ '--i': i }" /></div>
        <TransitionGroup tag="ul" name="list" class="reasons"><li v-for="x in reasons" :key="x">{{ x }}</li></TransitionGroup>
        <p class="small"><b>{{ t('What you know about your field raises the confidence.') }}</b> {{ t('Check what you already have:') }}</p>
        <div class="checks">
          <label v-for="[k, text] in CHECKS" :key="k" class="check">
            <input type="checkbox" :checked="state.checks[k]" @change="toggle(k, $event.target.checked)">{{ t(text) }}
          </label>
        </div>
      </div>
    </Reveal>
  </div>
</template>
