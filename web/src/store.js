// Page state and the live NASA data for the chosen point.
import { reactive, computed, shallowRef, watch } from 'vue'
import { CRIT, ROTS, LAYERS, MONTHS } from './content.js'
import { fetchPower, fetchNdvi, fetchRecentClimate, NINO_COASTAL } from './lib/nasa.js'
import { say, tell } from './guide.js'
import { DEPARTMENT, locate } from './lib/admin.js'
import { gridCells } from './lib/nasa.js'
import { samplePoints } from './lib/geo.js'
import { t } from './i18n.js'

export const state = reactive({
  stage: 'intro',   // intro (Sprout says hello) → where (pick province and district) → explore (map and slides)
  area: null,       // the territory on the map: { kind: 'district' | 'department', name, province, rings }
  slide: 0,         // index in SLIDES
  province: null,   // province open in the place picker
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

// An outlined field can be bigger than one grid square. Points spread over it say which squares it touches
// and how much of the field falls in each (its share). `power` counts the NASA POWER squares (0.5° × 0.625°).
export const cover = computed(() => {
  const ring = state.parcel?.ring
  if (!ring) return null
  const pts = samplePoints(ring)
  return { pts, power: new Set(pts.map(([la, lo]) => `${Math.round(la / 0.5)},${Math.round((lo + 180) / 0.625)}`)).size }
})

// The Lambayeque grid square under the chosen point (0.1°, ~11 km), or null outside Lambayeque. With an outlined
// field it is the average of every square the field touches, weighted by the share of the field in each one.
export const cell = computed(() => {
  const g = local.value, p = state.point
  if (!g || !p || !inLambayeque(p.lat, p.lon)) return null
  const { lat, lon } = g.meta.grid
  const near = (arr, v) => arr.reduce((best, x, k) => Math.abs(x - v) < Math.abs(arr[best] - v) ? k : best, 0)
  const weight = new Map()   // grid index → number of field points in it
  for (const [la, lo] of cover.value?.pts.length ? cover.value.pts : [[p.lat, p.lon]]) {
    const c = near(lat, la) * lon.length + near(lon, lo)
    weight.set(c, (weight.get(c) || 0) + 1)
  }
  const ids = [...weight.keys()], total = [...weight.values()].reduce((a, b) => a + b, 0)
  const avg = (get, digits = 0) => {
    let sum = 0, n = 0
    for (const c of ids) { const v = get(c); if (v != null) { sum += v * weight.get(c); n += weight.get(c) } }
    return n ? +(sum / n).toFixed(digits) : null
  }
  const months = arr => Array.from({ length: 12 }, (_, m) => avg(c => arr[c]?.[m]))
  const typicalYear = ids.map(c => g.rain.typical[c]).filter(Boolean).map(r => r.reduce((x, y) => x + (y ?? 0), 0))   // mm a year per square
  return {
    n: ids.length, squares: ids.map(c => [lat[Math.floor(c / lon.length)], lon[c % lon.length], weight.get(c) / total]),
    rain: { normal: months(g.rain.typical), nino: months(g.rain.nino) }, annual: g.rain.annual_years.map((_, y) => avg(c => g.rain.annual[c]?.[y])),
    range: [Math.round(Math.min(...typicalYear)), Math.round(Math.max(...typicalYear))],
    elev: avg(c => g.terrain.elev_m[c]), slope: avg(c => g.terrain.slope_deg[c], 1), land: avg(c => g.terrain.land_share[c], 2), water: g.water,
  }
})

// What Sprout adds when the outlined field is bigger than the data squares.
function coverLines() {
  const c = cell.value, out = []
  if (c?.n > 1) out.push([() => t('Your field is big: it covers {n} rain squares of 11 km. I averaged them by how much of your field falls in each one. Between them, yearly rain goes from {min} to {max} mm.', { n: c.n, min: c.range[0], max: c.range[1] }), 'thinking'])
  if (cover.value?.power > 1) out.push([() => t('It also crosses {n} NASA POWER climate squares (about 55 km). Heat and soil wetness come from the square at its center, so read them as a regional value.', { n: cover.value.power }), 'worried'])
  if (state.parcel?.areaM2 > 250_000) out.push([() => t('Greenness is still read at one 250 m pixel in the middle of your field, not across the whole field.'), 'neutral'])
  return out
}
// Inside Lambayeque, rain comes from IMERG (11 km) instead of POWER (55 km), and underground water from GRACE.
watch(cell, c => {
  Object.assign(LAYERS.rain, c ? { ds: 'GPM IMERG V07 (0.1°, 2001–2024)', px: 11 } : { ds: 'NASA POWER', px: 55 })
  Object.assign(LAYERS.water, c ? { ds: 'GRACE-FO mascon (regional, 2002–2026)', pending: false } : { ds: 'GRACE-FO (coming)', pending: true })
})

export const placeLabel = p => (p.name && t(p.name)) || `${Math.abs(p.lat).toFixed(2)}° ${p.lat < 0 ? 'S' : 'N'}, ${Math.abs(p.lon).toFixed(2)}° ${p.lon < 0 ? 'W' : 'E'}`

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
    if (inside) await loadLocal()
    if (id !== request) return
    const [text, mood] = LAYERS[state.layer].say(valueAt(state.layer)), notes = coverLines()
    tell([[() => t('{place}. {layer}: {text}', { place: placeLabel(state.point), layer: t(LAYERS[state.layer].name), text: t(text) }), mood], ...notes], { level: notes.length ? 'note' : 'info' })
  } catch (e) {
    if (id !== request) return
    db.error = e.message
    say(() => t("Oh no... I couldn't reach NASA POWER ({error}). Check the internet connection and tap the map again.", { error: e.message }), 'sad', [], { level: 'force' })
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

// The rotation on show (the user's pick, or the best fit) and today's rotation to compare with.
export const chosen = computed(() => ranking.value.find(x => x.r.id === state.rot) || ranking.value[0])
export const baseline = computed(() => ranking.value.find(x => x.r.id === 'current'))

// Hypothetical confidence: what the data can see here, plus what the farmer already knows.
export const confidence = computed(() => {
  const nino = state.scen === 'nino', r = chosen.value.r
  const score = Math.max(10, Math.min(95, 45 + (db.ndvi ? 10 : 0) + (state.checks.soil ? 15 : 0) + (state.checks.water ? 12 : 0) + (state.checks.tried ? 10 : 0) - (nino ? 10 : 0) + (r.id === 'current' ? 8 : 0)))
  const size = state.point ? gridCells(state.point.lat, state.point.lon)[0].size : t('about 55 km')
  return {
    score, level: score < 45 ? 'Low' : score < 70 ? 'Medium' : 'High',
    reasons: [
      t('Climate comes in NASA POWER cells of {size}: it describes the region, not your plot.', { size }),
      t(db.ndvi ? 'Greenness comes from 250 m MODIS pixels: much closer to your field.' : 'Greenness is not loaded for this spot yet.'),
      t(state.checks.soil ? 'With your soil test, the suggestion is more precise.' : 'Your plot\'s soil test is missing.'),
      t(state.checks.water ? 'You know how much water you get, so fewer surprises.' : 'We don\'t know how much water you get per season.'),
      ...(!state.checks.tried && r.id !== 'current' ? [t('You have never grown this here: try it on a small plot first.')] : []),
      ...(nino ? [t('An El Niño year is harder to predict.')] : []),
    ],
  }
})

// A reading as text: the number with its unit (Pro), and the small note under it.
export function formatValue(k, v) {
  if (LAYERS[k].pending) return t('Coming soon')
  if (v == null) return k === 'veg' && db.ndviError ? t('Not available') : '…'
  if (k === 'veg') return v.toFixed(2)
  return (k === 'heat' || k === 'water' ? (k === 'water' && v > 0 ? '+' : '') + v.toFixed(1) : Math.round(v)) + ' ' + LAYERS[k].unit
}
export function readingNote(k) {
  if (k === 'veg') return t(db.ndviLoading ? 'MODIS is slow, about a minute…' : db.ndviError ? 'MODIS service did not answer' : 'in {month} 2024', { month: t(MONTHS[state.month]) })
  if (LAYERS[k].pending) return t('needs Earthdata login')
  if (k === 'water') return t('trend 2002–2026, regional')
  return t(state.scen === 'nino' ? 'in {month}, El Niño years' : 'in {month}, typical year', { month: t(MONTHS[state.month]) })
}

// Map tools shared between the map and the HUD buttons. The map fills `mapApi` with its actions when it mounts.
export const mapUi = reactive({ drawing: false, corners: 0, data: null, intensity: 0.7 })
export const mapApi = {}

// Entering the map: one district (only its territory shows) or free mode (the whole department).
function open(area, lat, lon, name) {
  Object.assign(state, { area, parcel: null, slide: 0, stage: 'explore' })
  selectPoint(lat, lon, name)
}
export function enterDistrict(province, district, at = null) {
  const [lon, lat] = district.center
  open({ kind: 'district', name: district.name, province: province.name, rings: district.rings }, at?.lat ?? lat, at?.lon ?? lon, district.name)
}
export function enterFree(at = null) {
  const lat = at?.lat ?? state.point?.lat ?? -6.77, lon = at?.lon ?? state.point?.lon ?? -79.84
  open({ kind: 'department', name: DEPARTMENT.name, province: null, rings: DEPARTMENT.rings }, lat, lon, locate(lat, lon)?.district.name ?? null)
}
