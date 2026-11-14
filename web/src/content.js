// All the words on the page live here, so the team can edit text without touching components.
import * as d3 from 'd3'
import { reactive } from 'vue'
import { PAL, RAMP } from './lib/palette.js'

const ramp = (stops, domain) => d3.scaleLinear().domain(stops.map((_, i) => domain[0] + i * (domain[1] - domain[0]) / (stops.length - 1))).range(stops).clamp(true)

export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
export const M1 = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

export const ICON = {
  rain: '<path d="M7 15a4 4 0 1 1 .9-7.9A5 5 0 0 1 17.5 9 3.5 3.5 0 0 1 17 16H7"/><path d="M8 19l-1 2M12 19l-1 2M16 19l-1 2"/>',
  soil: '<path d="M12 3s-6 6.5-6 11a6 6 0 0 0 12 0c0-4.5-6-11-6-11z"/><path d="M3 21h18"/>',
  heat: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/>',
  veg: '<path d="M12 21v-9"/><path d="M12 12C12 7 8 4 4 4c0 5 3 8 8 8z"/><path d="M12 14c0-4 3-7 8-7 0 4-3 7-8 7z"/>',
  water: '<path d="M3 7h18M3 12h18M3 17h18" opacity=".35"/><path d="M12 4v14"/><path d="M8 14l4 4 4-4"/>',
  coin: '<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.5-1-1.6-1.5-3-1.5-1.7 0-3 .8-3 2s1.3 1.7 3 2 3 .8 3 2-1.3 2-3 2c-1.4 0-2.5-.5-3-1.5"/><path d="M12 6v2M12 16v2"/>',
  bug: '<rect x="8" y="7" width="8" height="12" rx="4"/><path d="M12 7V5M9 4l1.5 1.5M15 4l-1.5 1.5M8 11H4M8 15H4M16 11h4M16 15h4"/>',
  storm: '<path d="M7 14a4 4 0 1 1 .9-7.9A5 5 0 0 1 17.5 8 3.5 3.5 0 0 1 17 15"/><path d="M12 13l-2 4h4l-2 4"/>',
  play: '<path d="M7 4l13 8-13 8z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/>',
  sound: '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
  mute: '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M17 9l5 6M22 9l-5 6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
}

// say(v) returns [plain-language reading, Sprout's mood]
// Reactive so a layer's source can change by place (e.g. IMERG instead of POWER inside Lambayeque).
export const LAYERS = reactive({
  rain: {
    name: 'Rain', unit: 'mm', ds: 'NASA POWER', px: 55, icon: 'rain', domain: [0, 200],
    scale: () => ramp(RAMP.amount, [0, 200]),
    say: v => v < 5 ? ['It barely rains. Your crop depends completely on irrigation.', 'neutral']
      : v < 40 ? ['A little rain. It helps, but it is not enough for the crop.', 'thinking']
      : v < 100 ? ['Moderate rain. Watch out for waterlogged fields.', 'worried']
      : ['Heavy rain! Fields can flood and water can wash the soil away.', 'surprised'],
  },
  soil: {
    name: 'Soil wetness', unit: '%', ds: 'NASA POWER (GWETTOP)', px: 55, icon: 'soil', domain: [0, 100],
    scale: () => ramp(RAMP.amount, [0, 100]),
    say: v => v < 20 ? ['The topsoil is dry. With nothing growing on it, wind can blow it away.', 'worried']
      : v < 40 ? ['Low wetness. Plants start to suffer without irrigation.', 'thinking']
      : v < 70 ? ['Good wetness for most crops.', 'happy']
      : ['Very wet soil. Watch out for waterlogging.', 'surprised'],
  },
  heat: {
    name: 'Daytime heat', unit: '°C', ds: 'NASA POWER (typical afternoon high)', px: 55, icon: 'heat', domain: [0, 40],
    scale: () => ramp(RAMP.temp, [0, 40]),
    say: v => v >= 31 ? ['Strong heat. At midday plants get stressed and drink more water.', 'worried']
      : v >= 27 ? ['Hot days. Good for growing, as long as there is water.', 'happy']
      : v >= 20 ? ['Mild temperature, comfortable for many crops.', 'happy']
      : v >= 8 ? ['Cool weather. Crops grow more slowly.', 'thinking']
      : ['Cold! Frost can hurt crops this month.', 'worried'],
  },
  veg: {
    name: 'Plant greenness', unit: 'NDVI', ds: 'MODIS MOD13Q1 (2024)', px: 0.25, icon: 'veg', domain: [0, 0.85],
    scale: () => ramp(RAMP.veg, [0, 0.85]),
    say: v => v < 0.2 ? ['It looks almost bare: open soil or desert.', 'sad']
      : v < 0.4 ? ['A little vegetation: scrub, or a crop that just started.', 'thinking']
      : v < 0.6 ? ['Medium vegetation.', 'neutral']
      : ['Very green! A dense, healthy crop.', 'happy'],
  },
  water: {
    name: 'Underground water', unit: 'cm/yr', ds: 'GRACE-FO (coming)', px: 300, icon: 'water', domain: [-2, 2], pending: true,
    scale: () => ramp([PAL.ember, '#2A3A66', PAL.teal], [-2, 2]),
    say: v => v <= -1 ? ['Underground water keeps dropping, year after year. It needs care.', 'sad']
      : v < -0.3 ? ['Underground water is slowly going down.', 'worried']
      : ['Underground water is holding steady.', 'happy'],
  },
})
export const LAYER_KEYS = ['heat', 'rain', 'soil', 'veg', 'water']

// Plain-language reading for any layer and value, including "still loading" and "not connected yet".
export function reading(k, v) {
  if (LAYERS[k].pending) return ['Underground water needs a free NASA Earthdata login, so it arrives during the hackathon. I can\'t see it yet.', 'shy']
  if (v == null) return ['I\'m still listening to the satellites for this one...', 'thinking']
  return LAYERS[k].say(v)
}

// Farmer mode: a word instead of a number (DESIGN.md §9).
export function levelWord(k, v) {
  if (LAYERS[k].pending) return 'Coming soon'
  if (v == null) return 'Listening…'
  if (k === 'heat') return v < 8 ? 'Frosty' : v < 20 ? 'Cool' : v < 27 ? 'Mild' : v < 31 ? 'Hot' : 'Very hot'
  if (k === 'rain') return v < 5 ? 'Dry month' : v < 40 ? 'A little rain' : v < 100 ? 'Rainy' : 'Very rainy'
  if (k === 'soil') return v < 20 ? 'Dry soil' : v < 40 ? 'Slightly moist' : v < 70 ? 'Moist' : 'Wet'
  if (k === 'veg') return v < 0.2 ? 'Bare' : v < 0.4 ? 'Sparse' : v < 0.6 ? 'Green' : 'Lush'
  if (k === 'water') return v <= -1 ? 'Dropping fast' : v < -0.3 ? 'Slowly dropping' : v > 0.3 ? 'Slowly rising' : 'Steady'
  return ''
}
export const fitWord = score => score >= 70 ? 'Good fit' : score >= 45 ? 'Could work' : 'Poor fit'

// Example places across continents, so anyone can try the tool in one tap.
export const PLACES = [   // phase 1: Lambayeque only
  { name: 'Chiclayo', lat: -6.77, lon: -79.84 },
  { name: 'Lambayeque', lat: -6.70, lon: -79.91 },
  { name: 'Ferreñafe', lat: -6.64, lon: -79.79 },
  { name: 'Mórrope', lat: -6.54, lon: -80.01 },
  { name: 'Motupe', lat: -6.15, lon: -79.71 },
  { name: 'Olmos', lat: -5.98, lon: -79.75 },
]

export const CROP = {
  A: { name: 'Rice', color: PAL.teal },
  M: { name: 'Yellow maize', color: PAL.fire },
  S: { name: 'Sorghum', color: PAL.sand },
  L: { name: 'Cowpea', color: PAL.ghost },
  V: { name: 'Green manure', color: PAL.sage },
  B: { name: 'Bare soil', color: 'var(--fallow)' },
}
export const CRIT = [
  { k: 'water', label: 'Save water', icon: 'soil', hint: 'Use less irrigation water' },
  { k: 'income', label: 'Earn more', icon: 'coin', hint: 'More income per hectare' },
  { k: 'soil', label: 'Care for my soil', icon: 'veg', hint: 'More organic matter and nitrogen' },
  { k: 'pests', label: 'Fewer pests', icon: 'bug', hint: 'Break the pest cycle' },
  { k: 'climate', label: 'Withstand El Niño', icon: 'storm', hint: 'Handle extreme rain or heat' },
]
export const LEVELS = ['None', 'Some', 'Quite a bit', 'A lot']

// Scores 1–5 are hypothetical expert rules; replace them with values the team can justify.
export const ROTS = [
  { id: 'current', name: 'Rice, then fallow', cal: 'AAAAAABBBBBB', s: { water: 1, income: 3, soil: 1, pests: 1, climate: 2 }, nino: 3,
    gain: 'You know it and it already has a buyer', lose: 'Six months of bare soil',
    why: 'It is what many valleys grow today. We use it as the starting point to compare.',
    evid: [['Greenness (Landsat)', 'from July to December the field is almost bare.'], ['Heat (POWER)', 'January to March goes above 30 °C, right while the rice grows.'], ['Moisture (SMAP)', 'the soil dries out in the second half of the year.']],
    ben: ['Crop, mill and credit you already know.', 'Rice handles excess water well.'],
    risks: ['Six months of bare soil: wind carries the fertile topsoil away.', 'Always the same crop, so pest cycles never break.'] },
  { id: 'cowpea', name: 'Rice, then cowpea', cal: 'AAAAALLLLBBB', s: { water: 2, income: 4, soil: 3, pests: 3, climate: 3 }, nino: 3,
    gain: 'An extra harvest and soil with more nitrogen', lose: 'Needs water in the second season',
    why: 'Uses the empty months after rice for a short-cycle bean that feeds the soil.',
    evid: [['Greenness (Landsat)', 'shows the free gap from June to September.'], ['Heat (POWER)', 'June to September cools to about 25 °C, comfortable for cowpea.'], ['Moisture (SMAP)', 'cowpea covers the soil right when it dries the most.']],
    ben: ['Extra income in the same year.', 'Leaves nitrogen for the next rice, so less fertilizer.', 'Four more months of covered soil.'],
    risks: ['If second-season water is cut, the cowpea may fail.', 'Check for pests that both crops share.'] },
  { id: 'maize', name: 'Maize, cowpea and green manure', cal: 'MMMMMLLLLVVV', s: { water: 4, income: 3, soil: 5, pests: 4, climate: 3 }, nino: 1, floods: true,
    gain: 'Much less water and soil covered all year', lose: 'Very fragile if El Niño arrives',
    why: 'Swaps rice for a cereal that needs far less water, and keeps the soil covered all twelve months.',
    evid: [['Heat (ECOSTRESS)', 'a well-watered maize field runs cooler than a paddy in dry months (to confirm with real data).'], ['Greenness (Landsat)', 'the goal is a field that stays green all year.'], ['Rain (GPM)', 'in El Niño years, February and March bring rain that knocks maize down.']],
    ben: ['Big water savings compared with rice.', 'Green manure adds organic matter, so water soaks in better.', 'Breaks the pest cycle of rice.'],
    risks: ['Very vulnerable to flooding in an El Niño year.', 'A different market: buyer and price change.'] },
  { id: 'sorghum', name: 'Sorghum, then cowpea', cal: 'SSSSSLLLLBBB', s: { water: 5, income: 2, soil: 3, pests: 4, climate: 4 }, nino: 3,
    gain: 'Needs the least water', lose: 'Less income in normal years',
    why: 'The toughest option against drought and heat, meant for years when the reservoir runs low.',
    evid: [['Heat (POWER)', 'the hottest months fall in its growing stage, and sorghum tolerates them.'], ['Underground water (GRACE-FO)', 'if groundwater keeps dropping, a less thirsty crop is safer.'], ['Moisture (SMAP)', 'it handles dry soil better than rice.']],
    ben: ['The lowest water demand of the four.', 'Works as grain or as forage: two markets.', 'Tolerates some salinity.'],
    risks: ['Less income per hectare than rice in normal years.', 'Three months of bare soil at the end of the year.'] },
]

export const GLOSSARY = [
  ['Greenness (NDVI)', 'How green and alive the field looks from above. Near 0 is bare ground. Near 0.8 is a dense, healthy crop.'],
  ['Evapotranspiration', 'The water that leaves the field: what evaporates from the soil plus what plants "sweat" through their leaves. It is exactly what irrigation has to replace.'],
  ['Soil moisture', 'How much water the top few centimeters of soil hold. The SMAP satellite measures it with microwaves, even through clouds.'],
  ['Satellite or soil test?', 'A satellite sees the whole valley every few days, but it averages big areas. A soil test is exact, but only at one spot. Together they correct each other.'],
]

// Sprout's lines per section. Line i reveals every <Reveal :at="i"> in that section.
export const SCRIPTS = {
  hero: [
    ['Oh! Hello there! I\'m Sprout. I came down from orbit to help you read what the satellites see.', 'happy'],
    ['From up there, NASA satellites measure signals about any field on Earth. They\'re these little buttons.', 'neutral'],
    ['I know it sounds like a lot... but don\'t worry! We\'ll go one step at a time, together. Scroll down whenever you\'re ready.', 'shy'],
  ],
  map: [
    ['This is the whole Earth! Search a town, tap the map, or try an example place. You can even outline your own field with the yellow tool.', 'happy'],
    ['NASA data comes in squares called grid cells, and every satellite uses a different size. Here they are, nested around your point. Tap one to zoom in.', 'thinking'],
    ['Press play to watch a whole year go by. The big square takes the color of the signal you picked.', 'happy'],
    ['Over here I translate the numbers into plain words. They are real NASA numbers for that spot, averaged over 2001 to 2024!', 'surprised'],
    ['One honest thing, though: the climate cell is about 50 km wide. It describes your region, not your exact field. Greenness comes at 250 meters, much closer.', 'worried'],
  ],
  years: [
    ['Now let\'s travel back in time. Each stripe is one year at your spot, from 1981 to 2024. Turquoise years had cooler afternoons, campfire years hotter ones.', 'thinking'],
    ['And these are the hard years: the wettest and the driest. They can come back, so it\'s good to plan for them.', 'worried'],
  ],
  prio: [
    ['Every farm is different, so I\'d love to know what matters to you.', 'neutral'],
    ['Tap a card to make it more important. The rotations below will reorder themselves. It\'s your call!', 'happy'],
  ],
  rots: [
    ['Each row is one year, like walking along a furrow from January to December. A seed is sowing, a golden plant is harvest, empty soil is bare land.', 'thinking'],
    ['See the little icons above some months? Those are risky months at your spot: heat, heavy rain, dry soil or frost. A plant growing then looks thirsty.', 'worried'],
    ['Pick any rotation and I\'ll compare it with what you grow today, point by point.', 'neutral'],
    ['I\'m not always sure, and that\'s okay. If you tell me what you know about your field, I get more confident.', 'shy'],
    ['And remember: I\'m only a helper. You and your local agronomist always have the final word.', 'happy'],
  ],
  gloss: [
    ['Satellite words can sound scary. Here they are in plain words. You\'ve got this!', 'happy'],
  ],
}
