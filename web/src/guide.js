// Sprout's dialogue: which lines are playing and how much of each section is revealed.
import { reactive, computed, provide, onMounted, onBeforeUnmount } from 'vue'
import { SCRIPTS } from './content.js'

export const guide = reactive({
  section: null, lines: [], i: 0,
  steps: {},        // section -> highest revealed line (Infinity = everything)
  seen: {},         // sections whose script already played
  queue: [],        // sections waiting for the current script to end
  showAll: false, muted: false, open: true, talking: false,
})
const visible = reactive(new Set())  // sections currently on screen

export const line = computed(() => guide.lines[guide.i] || null)
export const hasNext = computed(() => guide.i < guide.lines.length - 1)
export const canAdvance = computed(() => hasNext.value || guide.queue.some(s => visible.has(s)))

function finishSection() { if (guide.section) guide.steps[guide.section] = Infinity }

function start(section) {
  finishSection()
  guide.seen[section] = true
  guide.queue = guide.queue.filter(s => s !== section)
  Object.assign(guide, { section, lines: SCRIPTS[section], i: 0 })
  guide.steps[section] = 0
}

// Sections take turns: a new one waits while the current script is unfinished and still on screen.
function request(section) {
  if (guide.seen[section] || guide.showAll) return
  if (guide.section && hasNext.value && visible.has(guide.section)) {
    if (!guide.queue.includes(section)) guide.queue.push(section)
  } else start(section)
}

function startQueued() {
  const q = guide.queue.find(s => visible.has(s) && !guide.seen[s])
  guide.queue = guide.queue.filter(s => visible.has(s) && s !== q)
  if (q) start(q)
}

export function next() {
  if (hasNext.value) {
    guide.i++
    if (guide.section) guide.steps[guide.section] = guide.i
  } else {
    finishSection()
    startQueued()
  }
}

// A one-line reaction to something the user did. It never cuts a script in the middle.
export function say(text, mood = 'neutral', more = []) {
  if (guide.section && hasNext.value) return
  finishSection()
  guide.section = null
  startQueued()
  if (guide.section) return
  Object.assign(guide, { section: null, lines: [[text, mood], ...more], i: 0 })
}

export function showEverything() {
  finishSection()
  guide.showAll = true
  guide.queue = []
  Object.assign(guide, { section: null, lines: [['Okay! Everything is out now. Explore at your own pace, and tap things if you want me to explain them.', 'happy']], i: 0 })
}

// Call from a section component: plays its script when it scrolls into view and
// provides `step` to the <Reveal> blocks inside it.
export function useScript(section, el) {
  const step = computed(() => guide.showAll ? Infinity : (guide.steps[section] ?? -1))
  const now = computed(() => guide.section === section ? guide.i : -1)
  provide('step', step)
  provide('now', now)
  let io
  onMounted(() => {
    io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { visible.add(section); request(section); return }
      visible.delete(section)
      if (guide.section === section && hasNext.value) startQueued()
    }, { rootMargin: '0px 0px -40% 0px' })
    io.observe(el.value)
  })
  onBeforeUnmount(() => io?.disconnect())
  return step
}
