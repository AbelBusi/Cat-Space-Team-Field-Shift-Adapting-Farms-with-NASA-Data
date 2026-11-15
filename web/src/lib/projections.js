// "What's ahead": projections of the tested XGBoost models, computed by the ML API (ml-api/, GET /projections) with the
// same code as ml/notebooks/06_projections.ipynb. Values are integers × meta.scale. One 2 km cell per value.
import { shallowRef, computed, watchEffect, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { RAMP } from './palette.js'
import { state, mapUi } from '../store.js'
import { getProjections } from './mlApi.js'

export const proj = shallowRef(null)      // the whole file (big arrays: no deep reactivity)
export const projError = shallowRef(null)
export const aheadMap = shallowRef(null)  // { url, bounds } the map shows over the photo, set by the open topic
let loading = null
let index = null                            // "x,y" → cell position

export function loadProjections() {
  if (loading) return loading
  projError.value = null
  loading = getProjections()
    .then(d => {
      index = new Map(d.cells.x.map((x, i) => [`${x},${d.cells.y[i]}`, i]))
      proj.value = d
    })
    .catch(e => { loading = null; projError.value = e.message })
  return loading
}

export const VARS = { soil_water: { unit: 'm³/m³', digits: 3 }, ndvi: { unit: 'NDVI', digits: 2 } }
export const nPeriods = v => proj.value?.meta.periods[v].length ?? 0
const step = () => proj.value.meta.grid_step_deg

// The cell under a point, or -1 (outside the grid, or a coastal cell without data).
export function cellAt(lat, lon) {
  if (!proj.value || lat == null) return -1
  return index.get(`${Math.floor(lon / step())},${Math.floor(lat / step())}`) ?? -1
}
// The cell under a point or, if it has none (a point just past the edge of the grid, or a coastal cell), the nearest cell
// with a projection up to 1.5 squares (~3 km) away. The time bar does the same on the API side and says so.
export function nearestCell(lat, lon, max = 1.5) {
  const own = cellAt(lat, lon)
  if (own >= 0 || !proj.value || lat == null) return own
  const fx = lon / step(), fy = lat / step(), x0 = Math.floor(fx), y0 = Math.floor(fy)
  let best = -1, bd = Infinity
  for (let dx = -2; dx <= 2; dx++) for (let dy = -2; dy <= 2; dy++) {
    const i = index.get(`${x0 + dx},${y0 + dy}`)
    if (i == null) continue
    const d = Math.hypot(x0 + dx + 0.5 - fx, y0 + dy + 0.5 - fy)
    if (d < bd) { bd = d; best = i }
  }
  return bd <= max ? best : -1
}
export const spotCell = computed(() => state.point ? nearestCell(state.point.lat, state.point.lon) : -1)

// Values of one cell (or null where there are none), in real units.
export function cellSeries(v, scen, field, i) {
  const d = proj.value, n = nPeriods(v), arr = d?.[v]?.[scen]?.[field] ?? (field === 'usual' ? d?.[v]?.usual : null)
  if (!arr || i < 0) return null
  return Array.from({ length: n }, (_, k) => arr[i * n + k] == null ? null : arr[i * n + k] / d.meta.scale)
}
export function spot(v, scen) {
  const i = spotCell.value
  if (i < 0 || !proj.value?.[v]?.[scen]) return null
  const median = cellSeries(v, scen, 'median', i)
  if (!median || median.every(x => x == null)) return null
  return { median, low: cellSeries(v, scen, 'low', i), high: cellSeries(v, scen, 'high', i), usual: cellSeries(v, 'base', 'usual', i) }
}

// Compared with the usual value of that cell and month: the farmer's word.
export function versusUsual(v, value, usual) {
  if (value == null || usual == null) return null
  const tol = v === 'ndvi' ? 0.03 : 0.01
  return value > usual + tol ? 'wetter' : value < usual - tol ? 'drier' : 'usual'
}

// Colors for the map. `diff`: change against the normal scenario (teal = wetter or greener, campfire = drier).
export function colorScale(v, diff = false) {
  if (diff) {
    const m = v === 'ndvi' ? 0.06 : 0.04
    const [wet, normal, dry, drier] = RAMP.anomaly
    return d3.scaleLinear().domain([-m, -m / 2, -m / 8, m / 8, m]).range([drier, dry, normal, normal, wet]).interpolate(d3.interpolateLab).clamp(true)
  }
  const [a, b] = proj.value.meta.domain[v].map(x => x / proj.value.meta.scale)
  const stops = v === 'ndvi' ? RAMP.veg : RAMP.amount
  return d3.scaleLinear().domain(stops.map((_, k) => a + k * (b - a) / (stops.length - 1))).range(stops).clamp(true)
}

// One canvas pixel per 2 km cell, shown as ONE image over the map (fast at any zoom).
// value(i) → number or null for cell i.
export function gridImage(value, color) {
  const d = proj.value, { x, y } = d.cells
  const x0 = Math.min(...x), x1 = Math.max(...x), y0 = Math.min(...y), y1 = Math.max(...y)
  const cv = document.createElement('canvas')
  cv.width = x1 - x0 + 1; cv.height = y1 - y0 + 1
  const ctx = cv.getContext('2d')
  for (let i = 0; i < x.length; i++) {
    const v = value(i)
    if (v == null) continue
    ctx.fillStyle = color(v)
    ctx.fillRect(x[i] - x0, y1 - y[i], 1, 1)            // canvas row 0 = north
  }
  const s = step()
  return { url: cv.toDataURL(), bounds: [[y0 * s, x0 * s], [(y1 + 1) * s, (x1 + 1) * s]] }
}

// The map layer for a variable, scenario and period; against the normal scenario when `diff`.
export function periodImage(v, scen, k, diff = false) {
  const d = proj.value, n = nPeriods(v), arr = d[v][scen].median, base = d[v].base.median, sc = d.meta.scale
  const color = colorScale(v, diff && scen !== 'base')
  return gridImage(i => {
    const a = arr[i * n + k]
    if (a == null) return null
    if (!(diff && scen !== 'base')) return a / sc
    const b = base[i * n + k]
    return b == null ? null : (a - b) / sc
  }, color)
}

export const periodLabel = (v, p, months, t) => v === 'ndvi'
  ? t('Quarter {q}, {y}', { q: p.slice(-1), y: p.slice(0, 4) })
  : `${t(months[+p.slice(5, 7) - 1])} ${p.slice(0, 4)}`

// The scenarios on offer, in order, with their pixel icon. "Half / double the rain" are served only when the API runs the
// v3 soil water model, which passed the rain check (docs/ML_V3_ERA5_RAIN.md); with v1 they would show noise as an answer.
// Lists show only the scenarios the API sent: offered(p).
export const SCENARIOS = [
  { id: 'base', label: 'A normal year', icon: 'sun', hint: 'The weather of each of 28 past years (1998–2025), one by one.' },
  { id: 'el_nino', label: 'An El Niño year', icon: 'rain', hint: 'Only the years with a coastal El Niño in the rainy season: 1998, 2016, 2017, 2023, 2024.' },
  { id: 'drought_feb_mar', label: 'Two months without rain', icon: 'soil_dry', hint: 'No rain in February and March 2026, the heart of the rainy season.' },
  { id: 'rain_half', label: 'Half the rain', icon: 'plant_thirsty', hint: 'Each past year with half its rain, every month.' },
  { id: 'rain_double', label: 'Double the rain', icon: 'drop', hint: 'Each past year with twice its rain, every month.' },
]
export const offered = p => SCENARIOS.filter(x => p?.soil_water?.[x.id])

// For a topic of the "ahead" track: load the file, switch off other map images, and keep the map image in sync.
export function useAheadMap(build) {
  loadProjections()
  mapUi.data = null
  const stop = watchEffect(() => { aheadMap.value = proj.value ? build(proj.value) : null })
  onBeforeUnmount(() => { stop(); aheadMap.value = null })
}

// Months of the projection as initials (or Q1..Q4), for chart axes.
export const shortLabel = (v, p, initials) => v === 'ndvi' ? 'Q' + p.slice(-1) : initials[+p.slice(5, 7) - 1]
