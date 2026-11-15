// Sprout's tutorial: one thing at a time. The screen dims, only the part Sprout talks about stays lit (Tour.vue), and
// Sprout explains it in its panel with Next / Back / End. Steps whose target is not on screen (e.g. buttons hidden in
// the phone menu) are skipped. Targets are elements with data-tour="…".
import { reactive } from 'vue'
import { state } from '../store.js'

export const TOURS = {
  intro: [
    ['lang', 'Here you choose the language: English, Spanish or Quechua. You can change it any time.', 'happy'],
    ['guide', 'This button turns my explanations on or off. When I am off, I wait quietly and raise a little flag if something is important.', 'shy'],
    ['ask', 'Tap this bubble to ask me anything in your own words. After each answer we can keep talking.', 'happy'],
    ['sound', 'This is my voice. Tap it if you prefer silence.', 'neutral'],
    ['close', 'The X sends me to my corner. Tap me there to call me back.', 'shy'],
    ['explore', 'This is the main door: pick your district and see what NASA satellites see over your land today.', 'happy'],
    ['ahead', 'This door looks ahead: the coming months and "what if" cases like El Niño, from the models our team trained.', 'thinking'],
    ['links', 'For the curious: the project\'s code and the scientific paper about our models.', 'neutral'],
    ['sprout', 'And this is me! Tap me whenever you need help. You\'re ready!', 'happy'],
  ],
  where: [
    ['picker-map', 'This is Lambayeque. Tap your province, and then your district.', 'happy'],
    ['province-list', 'If the map is hard to tap, use this list instead.', 'neutral'],
    ['search', 'You can also write the name of your town or neighborhood.', 'thinking'],
    ['locate', 'Or let me find you with your phone\'s location.', 'happy'],
    ['free-picker', 'Free mode opens the whole department, to tap anywhere.', 'neutral'],
    ['lang', 'The language is always up here.', 'shy'],
  ],
  explore: [
    ['topics', 'Each icon is a topic. The big arrows on the sides, or your keyboard arrows, take you to the next one.', 'happy'],
    ['cards', 'The cards explain the topic. Tap the map to read another spot.', 'thinking'],
    ['maptools', 'Zoom, go back to the whole view, find your location, or outline your field with these buttons.', 'neutral'],
    ['track', 'Today shows what the satellites see now. Ahead shows what our models expect for the coming months.', 'thinking'],
    ['mode', 'Farmer mode speaks with tools and words; Pro mode shows numbers and charts.', 'happy'],
    ['where', 'Tap here to change province or district.', 'neutral'],
    ['free', 'Free mode opens the whole department.', 'neutral'],
    ['pdf', 'Print your report or save it as a PDF to share with your agronomist.', 'happy'],
    ['ask', 'And remember: you can ask me anything from this bubble.', 'shy'],
  ],
}

export const tour = reactive({ active: false, steps: [], i: 0, target: null })

const visible = sel => {
  const el = document.querySelector(`[data-tour="${sel}"]`)
  if (!el) return false
  const r = el.getBoundingClientRect()
  return r.width > 0 && r.height > 0
}
export function stageTour() { return TOURS[state.stage] || TOURS.explore }
export function startTour(steps = stageTour()) {
  const ok = steps.filter(([sel]) => visible(sel))
  if (!ok.length) return false
  Object.assign(tour, { active: true, steps: ok, i: 0, target: ok[0][0] })
  return true
}
export function goStep(i) {
  if (i < 0 || i >= tour.steps.length) return endTour()
  Object.assign(tour, { i, target: tour.steps[i][0] })
}
export function endTour() { Object.assign(tour, { active: false, steps: [], i: 0, target: null }) }
