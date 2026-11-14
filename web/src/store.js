// Page state and the live NASA data for the chosen point.
import { reactive, computed, shallowRef, watch } from 'vue'
import { CRIT, ROTS, LAYERS } from './content.js'
import { fetchPower, fetchNdvi, fetchRecentClimate, NINO_COASTAL } from './lib/nasa.js'
import { say } from './guide.js'
import { t } from './i18n.js'

export const state = reactive({
  layer: 'heat', month: 2, scen: 'normal',
  mode: (() => { try { return localStorage.getItem('fs-mode') || 'farmer' } catch { return 'farmer' } })(),   // farmer | pro
  point: null,      // { lat, lon, name }
  parcel: null,     // { ring: [[lat, lon], ...], areaM2, perimeterM } when the farmer outlines a field
  prio: { water: 3, income: 2, soil: 2, pests: 1, climate: 2 },
  rot: null, checks: { soil: false, water: false, tried: false },
})
export const db = reactive({ power: null, ndvi: null, recent: null, loading: false, ndviLoading: false, error: null, ndviError: null, recentError: null })

// Lambayeque grid: the downloaded NASA files (IMERG 0.1° rain, NASADEM terrain, GRACE water) pre-computed by
// pipeline/build_lambayeque.py. NASA has no keyless API for these, so this file is their source inside the bbox.
export const LAMBAYEQUE = { west: -80.7, south: -7.2, east: -78.8, north: -5.4 }
export const inLambayeque = (lat, lon) => lat >= LAMBAYEQUE.south && lat <= LAMBAYEQUE.north && lon >= LAMBAYEQUE.west && lon <= LAMBAYEQUE.east
export const local = shallowRef(null)   // big read-only arrays: no deep reactivity
let localLoad = null
function loadLocal() {
  localLoad ||= fetch(`${import.meta.env.BASE_URL}data/lambayeque.json`)
    .then(r => r.ok ? r.json() : Promise.reject(new Error(`lambayeque.json ${r.status}`)))
    .then(d => (local.value = d))
    .catch(e => { localLoad = null; console.warn('Lambayeque grid not available:', e) })
  return localLoad
}

// The grid cell under the chosen point (0.1°, ~11 km), or null outside Lambayeque.
export const cell = computed(() => {
  const g = local.value, p = state.point
  if (!g || !p || !inLambayeque(p.lat, p.lon)) return null
  const { lat, lon } = g.meta.grid
  const near = (arr, v) => arr.reduce((best, x, k) => Math.abs(x - v) < Math.abs(arr[best] - v) ? k : best, 0)
  const i = near(lat, p.lat), j = near(lon, p.lon), c = i * lon.length + j
  return {
    lat: lat[i], lon: lon[j], rain: { normal: g.rain.typical[c], nino: g.rain.nino[c] }, annual: g.rain.annual[c],
    elev: g.terrain.elev_m[c], slope: g.terrain.slope_deg[c], land: g.terrain.land_share[c], water: g.water,
  }
})
// Inside Lambayeque, rain comes from IMERG (11 km) instead of POWER (55 km), and underground water from GRACE.
watch(cell, c => {
  Object.assign(LAYERS.rain, c ? { ds: 'GPM IMERG V07 (0.1°, 2001–2024)', px: 11 } : { ds: 'NASA POWER', px: 55 })
  Object.assign(LAYERS.water, c ? { ds: 'GRACE-FO mascon (regional, 2002–2026)', pending: false } : { ds: 'GRACE-FO (coming)', pending: true })
})

export const placeLabel = p => p.name || `${Math.abs(p.lat).toFixed(2)}° ${p.lat < 0 ? 'S' : 'N'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon < 0 ? 'W' : 'E'}`

// 12 monthly values for a layer, or null while it loads (or if it is not connected yet).
export function series(layer, scen = state.scen) {
  if (layer === 'veg') return db.ndvi
  if (layer === 'rain' && cell.value) return cell.value.rain[scen]
  if (layer === 'water') return cell.value ? Array(12).fill(cell.value.water.trend_cm_per_year) : null
  if (LAYERS[layer].pending) return null
  return db.power?.[scen][layer] ?? null
}
export const valueAt = layer => series(layer)?.[state.month] ?? null

let request = 0
export async function selectPoint(lat, lon, name = null) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90) return
  lon = ((lon + 540) % 360) - 180   // wrap clicks on a repeated world map back to -180..180
  const id = ++request
  const inside = inLambayeque(lat, lon)
  if (inside) loadLocal()
  state.point = { lat: +lat.toFixed(4), lon: +lon.toFixed(4), name }
  Object.assign(db, { power: null, ndvi: null, recent: null, loading: true, ndviLoading: true, error: null, ndviError: null, recentError: null })
  say(() => t('Listening to the satellites over {place}...', { place: placeLabel(state.point) }), 'thinking')

  fetchRecentClimate(state.point.lat, state.point.lon)
    .then(v => { if (id === request) db.recent = v })
    .catch(e => { if (id === request) db.recentError = e.message })
  fetchNdvi(state.point.lat, state.point.lon)
    .then(v => { if (id === request) db.ndvi = v })
    .catch(e => { if (id === request) db.ndviError = e.message })
    .finally(() => { if (id === request) db.ndviLoading = false })
  try {
    const power = await fetchPower(state.point.lat, state.point.lon, inside ? NINO_COASTAL : undefined)   // coastal El Niño on the Peruvian coast
    if (id !== request) return
    db.power = power
    const [text, mood] = LAYERS[state.layer].say(valueAt(state.layer))
    say(() => t('{place}. {layer}: {text}', { place: placeLabel(state.point), layer: t(LAYERS[state.layer].name), text: t(text) }), mood)
  } catch (e) {
    if (id !== request) return
    db.error = e.message
    say(() => t("Oh no... I couldn't reach NASA POWER ({error}). Check the internet connection and tap the map again.", { error: e.message }), 'sad')
  } finally {
    if (id === request) db.loading = false
  }
}

// Simple climate reading of the cell, used for warnings and confidence.
export const climate = computed(() => {
  const p = db.power?.normal
  if (!p) return null
  const sum = a => Math.round((a || []).reduce((s, b) => s + (b ?? 0), 0))
  const rain = sum(series('rain', 'normal')), ninoRain = sum(series('rain', 'nino'))   // IMERG inside Lambayeque, else POWER
  const tmax = p.heat.reduce((a, b) => a + (b ?? 0), 0) / 12
  const dry = rain < 250 ? 'dry' : rain < 600 ? 'semi-dry' : 'wet'
  return { rain, ninoRain, cool: tmax < 18, dry, label: () => t(`${tmax < 18 ? 'Cool' : 'Warm'}, ${dry} climate`) + ' · ' + t('{n} mm of rain a year', { n: rain }) }
})

export const ranking = computed(() => {
  const c = climate.value, nino = state.scen === 'nino'
  const total = CRIT.reduce((s, k) => s + state.prio[k.k], 0)
  return ROTS.map(r => {
    const sc = { ...r.s, ...(nino && { climate: r.nino }) }
    let score = CRIT.reduce((s, k) => s + (total ? state.prio[k.k] : 1) * sc[k.k], 0) / (5 * (total || CRIT.length)) * 100
    const flags = []
    if (c?.dry === 'dry' && sc.water <= 2) { score *= 0.8; flags.push(t('Dry climate here ({n} mm a year): a thirsty crop needs reliable irrigation.', { n: c.rain })) }
    if (c && nino && r.floods && c.ninoRain > c.rain * 1.25) flags.push(t('In El Niño years rain here goes up {n}%: maize may flood.', { n: Math.round((c.ninoRain / c.rain - 1) * 100) }))
    if (c?.cool) flags.push(t('Cool climate: these warm-season example crops may not fit. Local rotations will differ.'))
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
