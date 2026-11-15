<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
// Layout of a topic. Wide screens: cards on the left and right edges of the map (they slide in from their side).
// Phones and tablets: the left cards become a strip at the top and the right cards a strip at the bottom, each a row
// you swipe with a finger (one card at a time, with small squares that say where you are); the map stays in the middle.
const left = ref(null), right = ref(null), top = ref(150), dots = reactive({ left: 0, right: 0 })
const pages = reactive({ left: { n: 0, i: 0 }, right: { n: 0, i: 0 } })
function measure() {
  top.value = Math.round((document.querySelector('[data-hud-top]')?.getBoundingClientRect().bottom ?? 140) + 6)
  if (left.value) dots.left = Math.round(left.value.getBoundingClientRect().bottom + 4)
  if (right.value) dots.right = Math.round(innerHeight - right.value.getBoundingClientRect().top + 4)
  for (const [k, el] of [['left', left.value], ['right', right.value]]) {
    if (!el) continue
    pages[k].n = el.children.length
    const w = el.firstElementChild?.getBoundingClientRect().width || 1
    pages[k].i = Math.min(pages[k].n - 1, Math.round(el.scrollLeft / (w + 8)))
  }
}
let obs
onMounted(() => {
  nextTick(measure)
  addEventListener('resize', measure)
  obs = new MutationObserver(measure)
  sizes = new ResizeObserver(measure)        // cards grow when their data arrive: the dots follow
  for (const el of [left.value, right.value]) if (el) { obs.observe(el, { childList: true }); sizes.observe(el) }
})
let sizes
onBeforeUnmount(() => { removeEventListener('resize', measure); obs?.disconnect(); sizes?.disconnect() })
const go = (k, i) => { const el = k === 'left' ? left.value : right.value; el?.children[i]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' }) }
// Every card has the same height on phones (both strips match), long lists inside swipe sideways (.swipe).
const strip = 'max-lg:pointer-events-auto max-lg:absolute max-lg:inset-x-0 max-lg:h-[26dvh] max-lg:min-h-[170px] max-lg:flex-row max-lg:gap-2 max-lg:overflow-x-auto max-lg:overflow-y-hidden max-lg:snap-x max-lg:snap-mandatory max-lg:scroll-px-3 max-lg:px-3 strip ' +
  'max-lg:[&>*]:h-full max-lg:[&>*]:w-[86vw] max-lg:[&>*]:max-w-[440px] max-lg:[&>*]:shrink-0 max-lg:[&>*]:snap-start max-lg:[&>*]:overflow-y-auto max-lg:[&>*]:overflow-x-hidden'
const desk = 'lg:absolute lg:top-36 lg:max-h-[calc(100dvh-9rem-9.5rem)] lg:w-[clamp(280px,27vw,380px)] lg:overflow-y-auto lg:overflow-x-hidden lg:p-0.5'
</script>

<template>
  <div class="pointer-events-none absolute inset-0 z-10" :style="{ '--strip-top': top + 'px' }">
    <div ref="left" data-tour="cards" class="col-left flex flex-col gap-3 max-lg:top-[var(--strip-top)] max-lg:items-start lg:left-14" :class="[strip, desk]" @scroll.passive="measure">
      <slot name="left" />
    </div>
    <div v-if="pages.left.n > 1" class="dots pointer-events-auto absolute inset-x-0 flex justify-center gap-1.5 lg:hidden" :style="{ top: dots.left + 'px' }">
      <button v-for="i in pages.left.n" :key="i" type="button" class="size-2" :class="i - 1 === pages.left.i ? 'bg-teal' : 'bg-line'" :aria-label="t('Card {n}', { n: i })" @click="go('left', i - 1)" />
    </div>
    <div ref="right" class="col-right flex flex-col gap-3 max-lg:bottom-2 max-lg:items-end lg:right-14" :class="[strip, desk]" @scroll.passive="measure">
      <slot name="right" />
    </div>
    <div v-if="pages.right.n > 1" class="dots pointer-events-auto absolute inset-x-0 flex justify-center gap-1.5 lg:hidden" :style="{ bottom: dots.right + 'px' }">
      <button v-for="i in pages.right.n" :key="i" type="button" class="size-2" :class="i - 1 === pages.right.i ? 'bg-teal' : 'bg-line'" :aria-label="t('Card {n}', { n: i })" @click="go('right', i - 1)" />
    </div>
  </div>
</template>
