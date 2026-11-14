// "Ask something else": Sprout's open questions.
// With VITE_ASK_URL set (a small server that holds the AI key, never the browser), the question goes there as
// POST { question, lang, context } and the reply is { answer }. Without it, Sprout answers from a few local topics
// and says honestly that the AI service is not connected.
import { GLOSSARY } from '../content.js'
import { lang } from '../i18n.js'

const ENDPOINT = import.meta.env.VITE_ASK_URL || ''
export const askConnected = !!ENDPOINT

const TOPICS = [
  [/ndvi|green|verd|q.umir/i, GLOSSARY[0][1]],
  [/evapo|transpir/i, GLOSSARY[1][1]],
  [/moist|humed|huqu|smap/i, GLOSSARY[2][1]],
  [/soil test|an[aá]lisis|laborator/i, GLOSSARY[3][1]],
  [/ni[ñn]o/i, 'El Niño warms the sea off this coast and brings heavy rain to the desert. Here I use the coastal index (Niño 1+2): 1983, 1998, 2016, 2017 and 2023 were the wet years.'],
  [/pixel|p[ií]xel|cell|celda|cuadr|square|resol/i, 'Satellites see in squares. NASA POWER (climate) is about 55 km wide, IMERG rain is 11 km and MODIS greenness is 250 m. The bigger the square, the more it describes your region instead of your field.'],
  [/rotat|rotaci|cowpea|caup[ií]|legum|frijol|muyu/i, 'A rotation changes the crop on the same land. After rice, a short bean like cowpea covers the soil and leaves nitrogen for the next crop.'],
  [/salt|salin|salitr|kachi/i, 'No NASA satellite measures salt in the soil directly. A soil test (electrical conductivity) is the sure way. Salt collects in low, flat land with poor drainage.'],
  [/who are|qui[eé]n eres|sprout|pitaq/i, "I'm Sprout! A small helper who turns NASA satellite data into plain words. I'm not an agronomist, so the final word is always yours."],
]

// Returns Sprout's lines: [[text, mood], ...]. Server answers are wrapped in a function so they are shown as they come.
export async function ask(question, context = {}) {
  if (ENDPOINT) {
    try {
      const r = await fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, lang: lang.value, context }) })
      const answer = r.ok && (await r.json()).answer
      if (answer) return [[() => String(answer), 'happy']]
    } catch { /* fall through to the local topics */ }
  }
  const hit = TOPICS.find(([re]) => re.test(question))
  if (hit) return [[hit[1], 'thinking']]
  return [
    [ENDPOINT ? "I'm sorry... I couldn't reach my bigger brain just now." : "I'm sorry... my bigger brain (an AI service) isn't connected in this version, so I can't answer that one yet.", 'sad'],
    ['But I can explain these: greenness (NDVI), soil moisture, El Niño, satellite squares, rotations and salty soil.', 'shy'],
  ]
}
