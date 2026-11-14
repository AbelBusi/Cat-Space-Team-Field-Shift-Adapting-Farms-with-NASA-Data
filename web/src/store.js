// Page state and the live NASA data for the chosen point.
import { reactive, computed } from 'vue'
import { CRIT, ROTS, LAYERS } from './content.js'
import { fetchPower, fetchNdvi, fetchRecentClimate } from './lib/nasa.js'
import { say } from './guide.js'
import { PLACES as DEMO_PLACES } from './demoPlaces.js'

export const state = reactive({
  layer: 'heat', month: 2, scen: 'normal',
  mode: (() => { try { return localStorage.getItem('fs-mode') || 'farmer' } catch { return 'farmer' } })(),   // farmer | pro
  demo: false,      // true = use the saved NASA snapshots in public/demo instead of live requests
  point: null,      // { lat, lon, name }
  parcel: null,     // { ring: [[lat, lon], ...], areaM2, perimeterM } when the farmer outlines a field
  prio: { water: 3, income: 2, soil: 2, pests: 1, climate: 2 },
  rot: null, checks: { soil: false, water: false, tried: false },
})
export const db = reactive({ power: null, ndvi: null, recent: null, loading: false, ndviLoading: false, error: null, ndviError: null, recentError: null })

export const placeLabel = p => p.name || `${Math.abs(p.lat).toFixed(2)}° ${p.lat < 0 ? 'S' : 'N'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon < 0 ? 'W' : 'E'}`

// 12 monthly values for a layer, or null while it loads (or if it is not connected yet).
export function series(layer, scen = state.scen) {
  if (layer === 'veg') return db.ndvi
  if (LAYERS[layer].pending) return null
  return db.power?.[scen][layer] ?? null
}
export const valueAt = layer => series(layer)?.[state.month] ?? null

let request = 0
export async function selectPoint(lat, lon, name = null) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90) return
  lon = ((lon + 540) % 360) - 180   // wrap clicks on a repeated world map back to -180..180
  const id = ++request
  state.point = { lat: +lat.toFixed(4), lon: +lon.toFixed(4), name }
  Object.assign(db, { power: null, ndvi: null, recent: null, loading: true, ndviLoading: true, error: null, ndviError: null, recentError: null })
  say(`Listening to the satellites over ${placeLabel(state.point)}...`, 'thinking')

  // Demo data: a saved snapshot of the same NASA requests, loaded instantly (see scripts/make-demo.mjs).
  const demo = state.demo && DEMO_PLACES.find(p => Math.abs(p.lat - lat) < 0.05 && Math.abs(p.lon - lon) < 0.05)
  if (demo) {
    try {
      const r = await fetch(`${import.meta.env.BASE_URL}demo/${demo.id}.json`)
      if (!r.ok) throw new Error(`demo file ${r.status}`)
      const d = await r.json()
      if (id !== request) return
      Object.assign(db, { power: d.power, ndvi: d.ndvi, recent: d.recent, loading: false, ndviLoading: false })
      const [text, mood] = LAYERS[state.layer].say(valueAt(state.layer))
      say(`${placeLabel(state.point)} (saved NASA data). ${LAYERS[state.layer].name}: ${text}`, mood)
      return
    } catch (e) {
      console.warn('Demo data failed, using live NASA data:', e)
    }
  }

  fetchRecentClimate(state.point.lat, state.point.lon)
    .then(v => { if (id === request) db.recent = v })
    .catch(e => { if (id === request) db.recentError = e.message })
  fetchNdvi(state.point.lat, state.point.lon)
    .then(v => { if (id === request) db.ndvi = v })
    .catch(e => { if (id === request) db.ndviError = e.message })
    .finally(() => { if (id === request) db.ndviLoading = false })
  try {
    const power = await fetchPower(state.point.lat, state.point.lon)
    if (id !== request) return
    db.power = power
    const [text, mood] = LAYERS[state.layer].say(valueAt(state.layer))
    say(`${placeLabel(state.point)}. ${LAYERS[state.layer].name}: ${text}`, mood)
  } catch (e) {
    if (id !== request) return
    db.error = e.message
    say(`Oh no... I couldn't reach NASA POWER (${e.message}). Check the internet connection and tap the map again.`, 'sad')
  } finally {
    if (id === request) db.loading = false
  }
}

// Simple climate reading of the cell, used for warnings and confidence.
export const climate = computed(() => {
  const p = db.power?.normal
  if (!p) return null
  const rain = Math.round(p.rain.reduce((a, b) => a + (b ?? 0), 0))
  const ninoRain = Math.round(db.power.nino.rain.reduce((a, b) => a + (b ?? 0), 0))
  const tmax = p.heat.reduce((a, b) => a + (b ?? 0), 0) / 12
  const dry = rain < 250 ? 'dry' : rain < 600 ? 'semi-dry' : 'wet'
  return { rain, ninoRain, cool: tmax < 18, dry, label: `${tmax < 18 ? 'Cool' : 'Warm'}, ${dry} climate · ${rain} mm of rain a year` }
})

export const ranking = computed(() => {
  const c = climate.value, nino = state.scen === 'nino'
  const total = CRIT.reduce((s, k) => s + state.prio[k.k], 0)
  return ROTS.map(r => {
    const sc = { ...r.s, ...(nino && { climate: r.nino }) }
    let score = CRIT.reduce((s, k) => s + (total ? state.prio[k.k] : 1) * sc[k.k], 0) / (5 * (total || CRIT.length)) * 100
    const flags = []
    if (c?.dry === 'dry' && sc.water <= 2) { score *= 0.8; flags.push(`Dry climate here (${c.rain} mm a year): a thirsty crop needs reliable irrigation.`) }
    if (c && nino && r.floods && c.ninoRain > c.rain * 1.25) flags.push(`In El Niño years rain here goes up ${Math.round((c.ninoRain / c.rain - 1) * 100)}%: maize may flood.`)
    if (c?.cool) flags.push('Cool climate: these warm-season example crops may not fit. Local rotations will differ.')
    return { r, sc, score: Math.round(Math.min(100, score)), flags }
  }).sort((a, b) => b.score - a.score)
})

// Year by year at this spot: wettest and driest years, and how much warmer the last 20 years are than the 1980s-90s.
export const history = computed(() => {
  const ys = db.power?.years
  if (!ys?.length) return null
  const mean = a => a.reduce((s, x) => s + x, 0) / a.length
  const old = ys.filter(x => x.y <= 2000), recent = ys.filter(x => x.y >= 2005)
  const byRain = [...ys].sort((a, b) => b.rain - a.rain)
  return {
    years: ys, wettest: byRain[0], driest: byRain[byRain.length - 1], meanRain: Math.round(mean(ys.map(x => x.rain))),
    warming: +(mean(recent.map(x => x.heat)) - mean(old.map(x => x.heat))).toFixed(1),
    rainChange: Math.round((mean(recent.map(x => x.rain)) / mean(old.map(x => x.rain)) - 1) * 100),
    heatMean: mean(ys.map(x => x.heat)),
  }
})

export const risks = computed(() => {
  const T = series('heat'), R = series('rain'), S = series('soil'), C = db.power?.[state.scen].coldest
  if (!T || !R || !S || !C) return []
  return T.map((_, i) => ({ heat: T[i] >= 30, rain: R[i] >= 60, dry: S[i] < 20, frost: C[i] != null && C[i] < 0 }))
})
