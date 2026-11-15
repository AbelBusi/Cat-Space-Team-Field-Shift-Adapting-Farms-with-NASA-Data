// Sprout's dialogue. Sprout never hides data: every screen shows its content at once, and Sprout only talks about it.
// With the guide ON, Sprout explains each screen the first time you open it. With the guide OFF, Sprout waits in a
// corner, raises a small flag when there is something worth saying, and answers when you tap.
import { reactive, computed } from 'vue'
import { SCRIPTS } from './content.js'
import { ask } from './lib/ask.js'
import { tour, startTour, goStep, endTour } from './lib/tour.js'

const saved = (() => { try { return localStorage.getItem('fs-guide') } catch { return null } })()
export const guide = reactive({
  on: saved !== 'off',
  lines: [], i: 0,      // what Sprout is saying: [[English text or function, mood], ...]
  choices: null,        // answers the user can pick after the last line: [{ label, run }]
  open: false,          // the dialogue panel is on screen
  unread: false,        // guide off: Sprout has something to say
  asking: false,        // the question box is open
  screen: null,         // id of the screen on show (a key of SCRIPTS)
  seen: {},             // screens already explained
  muted: false, talking: false,
})
let pending = null

export const line = computed(() => guide.lines[guide.i] || null)
export const hasNext = computed(() => guide.i < guide.lines.length - 1)

function show(lines, choices = null) {
  pending = null
  Object.assign(guide, { lines, i: 0, choices, open: true, unread: false, asking: false })
}

// level 'info': a passing remark, dropped while the guide is off or a script is unfinished.
// level 'note': worth knowing; with the guide off it raises Sprout's flag. level 'force': always shown (errors, answers).
export function tell(lines, { choices = null, level = 'info' } = {}) {
  if (level === 'force' || guide.on) {
    if (level === 'info' && guide.open && (hasNext.value || guide.choices || guide.asking)) return
    return show(lines, choices)
  }
  if (level === 'note') { pending = { lines, choices }; guide.unread = true }
}
export const say = (text, mood = 'neutral', more = [], opts) => tell([[text, mood], ...more], opts)

export function next() { if (hasNext.value) guide.i++ }
export function close() { guide.open = false; guide.asking = false; endTour() }

// A screen came into view: explain it once if the guide is on.
export function enter(id) {
  guide.screen = id
  if (!guide.on || guide.seen[id] || !SCRIPTS[id]) return
  guide.seen[id] = true
  show(SCRIPTS[id])
}
export function explain() {
  if (SCRIPTS[guide.screen]) show(SCRIPTS[guide.screen])
  else show([["There's nothing tricky on this screen. You're doing great!", 'happy']])
}

export function setGuide(on) {
  guide.on = on
  try { localStorage.setItem('fs-guide', on ? 'on' : 'off') } catch {}
  if (on) {
    guide.seen[guide.screen] = true
    show([["Yay! I'll explain each screen as we go. I'll do my very best!", 'happy'], ...(SCRIPTS[guide.screen] || [])])
  } else {
    show([["Oh... okay! That's totally fine. I'll wait quietly right here. Tap me whenever you need me, I'd be so happy to help.", 'shy']])
  }
}

// The tutorial: the screen dims, one part at a time stays lit, and Sprout explains it (lib/tour.js, Tour.vue).
export function tutorial() {
  if (!startTour()) return show([["There's nothing to point at on this screen yet.", 'shy']])
  tourStep()
}
function tourStep() {
  const [, text, mood] = tour.steps[tour.i], last = tour.i === tour.steps.length - 1
  show([[text, mood]], [
    { label: last ? 'Finish the tutorial' : 'Next', run: () => { if (last) close(); else { goStep(tour.i + 1); tourStep() } } },
    ...(tour.i ? [{ label: 'Back', run: () => { goStep(tour.i - 1); tourStep() } }] : []),
    ...(last ? [] : [{ label: 'End the tutorial', run: close }]),
  ])
}

function menu(first) {
  show([[first, 'happy']], [
    { label: 'Explain this screen', run: explain },
    { label: 'Show me how this screen works', run: tutorial },
    guide.on ? { label: "Stop explaining, I'll call you", run: () => setGuide(false) } : { label: 'Guide me from now on', run: () => setGuide(true) },
    { label: 'I want to ask something else', run: openAsk },
    { label: 'Never mind', run: close },
  ])
}
// The user tapped Sprout.
export function summon() {
  if (pending) return show(pending.lines, pending.choices)
  menu("Here I am! What do you need?")
}
export function openAsk() {
  show([[chat.length ? 'Sure! What else would you like to know?' : 'Of course! What would you like to know?', 'happy']])
  guide.asking = true
}
// The conversation with Sprout's AI: the last turns go with each question, so it can continue naturally.
const chat = []
export async function submitQuestion(question, context) {
  show([['Hmm, let me think...', 'thinking']])
  const lines = await ask(question, context, chat.slice(-8))
  const text = lines.map(([l]) => typeof l === 'function' ? l() : l).join(' ')
  chat.push({ role: 'user', content: question }, { role: 'assistant', content: text })
  show(lines)
  guide.asking = true            // the question box stays open: just keep writing
}
