<script setup>
import SlideFrame from '../components/SlideFrame.vue'
import HudCard from '../components/HudCard.vue'
import TradeOffs from '../components/TradeOffs.vue'
import { state, chosen, baseline, confidence } from '../store.js'
import { fitWord } from '../content.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'

// The chosen rotation against what the farmer does today, and how sure we can be.
const CHECKS = [['soil', 'I have a recent soil test'], ['water', 'I know how much water I get per season'], ['tried', 'I have grown these crops before']]
function toggle(k, on) {
  state.checks[k] = on
  if (on) say(() => t("Thank you! That makes me more confident. Now I'm at {level} confidence.", { level: t(confidence.value.level).toLowerCase() }), 'happy')
}
</script>

<template>
  <SlideFrame>
    <template #left>
      <HudCard :title="t('Chosen strategy') + ' · ' + (state.mode === 'pro' ? t('{n} out of 100', { n: chosen.score }) : t(fitWord(chosen.score)))">
        <Transition name="flip" mode="out-in"><div :key="chosen.r.id" class="font-display text-xl font-semibold">{{ t(chosen.r.name) }}</div></Transition>
        <p class="text-muted">{{ t(chosen.r.why) }}</p>
        <div><b class="text-teal">{{ t('What you gain') }}</b><ul class="list-disc pl-5"><li v-for="b in chosen.r.ben" :key="b">{{ t(b) }}</li></ul></div>
        <div><b class="text-fire">{{ t('What you risk') }}</b><ul class="list-disc pl-5"><li v-for="b in chosen.r.risks" :key="b">{{ t(b) }}</li></ul></div>
        <p v-for="f in chosen.flags" :key="f" class="border-l-2 border-ember pl-2 text-xs">{{ f }}</p>
      </HudCard>
      <HudCard>
        <details>
          <summary class="label cursor-pointer">{{ t('What the satellites say') }}</summary>
          <ul class="mt-2 flex flex-col gap-1"><li v-for="e in chosen.r.evid" :key="e[0]"><b>{{ t(e[0]) }}:</b> {{ t(e[1]) }}</li></ul>
        </details>
      </HudCard>
    </template>

    <template #right>
      <HudCard :title="t('Compared with what you do today')">
        <div v-if="state.mode === 'pro'" class="tr-head"><span /><span>{{ t('Today') }}</span><span>{{ t(chosen.r.name) }}</span><span /></div>
        <TradeOffs :base="baseline.sc" :pick="chosen.sc" />
        <p class="text-xs text-muted">{{ t(state.mode === 'pro' ? 'More filled squares = better on that topic (0 to 5). The arrow says if the change helps or hurts.' : 'Compared with what you grow today, topic by topic.') }}</p>
      </HudCard>
      <HudCard :title="t('How sure are we?')">
        <div class="flex items-baseline justify-between"><span class="text-muted">{{ t('Confidence') }} <span class="font-mono text-[10px] uppercase">({{ t('hypothetical') }})</span></span><b class="font-display text-lg">{{ t(confidence.level) }}</b></div>
        <div class="meter" role="img" :aria-label="t('Confidence {n} out of 100', { n: confidence.score })"><i v-for="i in 10" :key="i" :class="{ on: i <= Math.round(confidence.score / 10) }" :style="{ '--i': i }" /></div>
        <p class="text-xs"><b>{{ t('What you know about your field raises the confidence.') }}</b> {{ t('Check what you already have:') }}</p>
        <label v-for="[k, text] in CHECKS" :key="k" class="flex cursor-pointer items-center gap-2">
          <input type="checkbox" :checked="state.checks[k]" @change="toggle(k, $event.target.checked)">{{ t(text) }}
        </label>
        <details>
          <summary class="label cursor-pointer">{{ t('Why this level') }}</summary>
          <ul class="mt-1 list-disc pl-5 text-xs text-muted"><li v-for="x in confidence.reasons" :key="x">{{ x }}</li></ul>
        </details>
      </HudCard>
    </template>
  </SlideFrame>
</template>
