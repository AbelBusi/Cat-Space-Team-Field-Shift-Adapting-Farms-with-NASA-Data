import { PAL } from './palette.js'

// Live NASA data for any point on Earth. Neither service needs a login, and both accept calls from the browser.

// El Niño events by NOAA's Oceanic Niño Index (central Pacific), as the January of each event, within 2001–2024.
export const NINO_YEARS = [2003, 2005, 2007, 2010, 2015, 2016, 2019, 2024]
// Coastal El Niño for the Peruvian coast: Jan-Apr NOAA Niño 1+2 anomaly >= 0.8 °C, 1981-2024.
// These are the years that flood Lambayeque; the ONI list above misses them.
export const NINO_COASTAL = [1983, 1998, 2016, 2017, 2023]
const YEARS = Array.from({ length: 24 }, (_, i) => 2001 + i)        // the "typical year"
const ALL_YEARS = Array.from({ length: 44 }, (_, i) => 1981 + i)    // 1981-2024, for the year-by-year story
const MM = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0'))
const daysIn = (y, m) => new Date(y, m, 0).getDate()

// NASA POWER monthly values 2001–2024 → 12-month averages for all years and for El Niño years.
// Careful: monthly T2M_MAX / T2M_MIN are the single hottest / coldest hour of the month, so the typical
// afternoon high is estimated as mean temperature + half the average daily range.
const powerCache = new Map()   // one answer per POWER cell and session: averaging a district asks for several cells
export async function fetchPower(lat, lon, ninoYears = NINO_YEARS) {
  const url = `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,T2M_RANGE,T2M_MIN,PRECTOTCORR,GWETTOP&community=AG&latitude=${lat}&longitude=${lon}&start=1981&end=2024&format=JSON`
  if (!powerCache.has(url)) powerCache.set(url, fetch(url).then(async r => {
    if (!r.ok) throw new Error(`NASA POWER answered ${r.status}`)
    return (await r.json()).properties.parameter
  }).catch(e => { powerCache.delete(url); throw e }))
  const p = await powerCache.get(url)
  const get = (param, key) => { const v = p[param][key]; return v === -999 || v == null ? null : v }   // -999 = no data   // -999 = no data
  const avg = (years, f) => MM.map((mm, i) => {
    const vals = years.map(y => f(`${y}${mm}`, y, i + 1)).filter(v => v != null && !Number.isNaN(v))
    return vals.length ? +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : null
  })
  const pick = years => ({
    heat: avg(years, k => get('T2M', k) == null || get('T2M_RANGE', k) == null ? null : get('T2M', k) + get('T2M_RANGE', k) / 2),
    rain: avg(years, (k, y, m) => get('PRECTOTCORR', k) == null ? null : get('PRECTOTCORR', k) * daysIn(y, m)),   // mm/day → mm/month
    soil: avg(years, k => get('GWETTOP', k) == null ? null : get('GWETTOP', k) * 100),                             // 0–1 wetness → %
    coldest: avg(years, k => get('T2M_MIN', k)),                                                                   // for frost risk
  })
  // One value per year: total rain (mm) and the mean afternoon high (°C). Years with missing months are skipped.
  const years = ALL_YEARS.map(y => {
    const n = (param, mm) => get(param, `${y}${mm}`) ?? NaN
    const r = MM.map((mm, i) => n('PRECTOTCORR', mm) * daysIn(y, i + 1))
    const h = MM.map(mm => n('T2M', mm) + n('T2M_RANGE', mm) / 2)
    return r.some(Number.isNaN) || h.some(Number.isNaN) ? null : { y, rain: Math.round(r.reduce((a, b) => a + b, 0)), heat: +(h.reduce((a, b) => a + b, 0) / 12).toFixed(2) }
  }).filter(Boolean)
  return { normal: pick(YEARS), nino: pick(ninoYears), years }
}

// MODIS NDVI (MOD13Q1, 250 m) for 2024 through ORNL DAAC → 12 monthly means.
// The service allows 10 images per request and is slow (~40 s), so results are cached in the browser.
const ORNL_CHUNKS = [['A2024001', 'A2024145'], ['A2024161', 'A2024305'], ['A2024321', 'A2024353']]
export async function fetchNdvi(lat, lon) {
  const key = `ndvi:${lat.toFixed(3)},${lon.toFixed(3)}`
  try { const hit = localStorage.getItem(key); if (hit) return JSON.parse(hit) } catch {}
  const parts = await Promise.all(ORNL_CHUNKS.map(async ([a, b]) => {
    const r = await fetch(`https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset?latitude=${lat}&longitude=${lon}&band=250m_16_days_NDVI&startDate=${a}&endDate=${b}&kmAboveBelow=0&kmLeftRight=0`)
    if (!r.ok) throw new Error(`MODIS service answered ${r.status}`)
    return (await r.json()).subset
  }))
  const byMonth = Array.from({ length: 12 }, () => [])
  for (const s of parts.flat()) {
    const v = s.data[0]
    if (v > -2000) byMonth[+s.calendar_date.slice(5, 7) - 1].push(v * 0.0001)  // -3000 = no data
  }
  const out = byMonth.map(vs => vs.length ? +(vs.reduce((a, b) => a + b, 0) / vs.length).toFixed(2) : null)
  try { localStorage.setItem(key, JSON.stringify(out)) } catch {}
  return out
}

// The grid cell each dataset uses around a point, from coarse to fine.
// POWER and IMERG follow their real lat/lon grids; the others use other projections, so their squares are approximate.
const KM_PER_DEG = 111.32
export function gridCells(lat, lon) {
  const kmLon = KM_PER_DEG * Math.cos(lat * Math.PI / 180)
  const around = (km, la = lat, lo = lon) => [[la - km / 2 / KM_PER_DEG, lo - km / 2 / kmLon], [la + km / 2 / KM_PER_DEG, lo + km / 2 / kmLon]]
  const pLat = Math.round(lat / 0.5) * 0.5, pLon = Math.round((lon + 180) / 0.625) * 0.625 - 180
  const iLat = Math.floor(lat * 10) / 10, iLon = Math.floor(lon * 10) / 10
  return [
    { id: 'power', name: 'NASA POWER', what: 'climate: heat, rain, soil wetness', color: PAL.ink,
      bounds: [[pLat - 0.25, pLon - 0.3125], [pLat + 0.25, pLon + 0.3125]], size: `${Math.round(0.5 * KM_PER_DEG)} × ${Math.round(0.625 * kmLon)} km` },
    { id: 'imerg', name: 'GPM IMERG', what: 'rain from space (used in Lambayeque)', color: PAL.teal,
      bounds: [[iLat, iLon], [iLat + 0.1, iLon + 0.1]], size: `${Math.round(0.1 * KM_PER_DEG)} × ${Math.round(0.1 * kmLon)} km` },
    { id: 'smap', name: 'SMAP', what: 'soil moisture (planned)', color: PAL.ghost, bounds: around(9), size: '≈ 9 × 9 km' },
    { id: 'modis', name: 'MODIS', what: 'plant greenness (NDVI)', color: PAL.sage, bounds: around(0.25), size: '≈ 250 × 250 m' },
    { id: 'hls', name: 'Landsat / Sentinel-2 (HLS)', what: 'field-level greenness (planned)', color: PAL.sand, bounds: around(0.03), size: '≈ 30 × 30 m' },
  ]
}

const DAY_MS = 86_400_000
const isoDate = ms => new Date(ms).toISOString().slice(0, 10)

// Rain and temperature of the last 30 days with data (POWER publishes 2–5 days late).
export async function fetchRecentClimate(lat, lon) {
  const end = Date.now() - 5 * DAY_MS, start = end - 29 * DAY_MS
  const q = new URLSearchParams({ parameters: 'PRECTOTCORR,T2M', community: 'AG', latitude: lat.toFixed(4), longitude: lon.toFixed(4),
    start: isoDate(start).replace(/-/g, ''), end: isoDate(end).replace(/-/g, ''), format: 'JSON' })
  const r = await fetch(`https://power.larc.nasa.gov/api/temporal/daily/point?${q}`)
  if (!r.ok) throw new Error(`NASA POWER answered ${r.status}`)
  const p = (await r.json()).properties?.parameter
  const valid = s => Object.values(s || {}).filter(v => typeof v === 'number' && v > -900)
  const rain = valid(p?.PRECTOTCORR), temp = valid(p?.T2M)
  if (!rain.length || !temp.length) throw new Error('NASA POWER has no recent data here')
  return { from: isoDate(start), to: isoDate(end), rainMm: rain.reduce((a, b) => a + b, 0), rainyDays: rain.filter(v => v >= 1).length,
    tempC: temp.reduce((a, b) => a + b, 0) / temp.length }
}

// NASA GIBS image layers to paint on the map (no key). Dates are the newest images that surely exist.
// MODIS NDVI comes in 8-day composites starting on day 1, 9, 17... of each year; we take the last closed one.
export function gibsDataLayers(now = Date.now()) {
  const t = new Date(now - 16 * DAY_MS), y0 = Date.UTC(t.getUTCFullYear(), 0, 1)
  const ndviDate = isoDate(y0 + Math.floor((t - y0) / DAY_MS / 8) * 8 * DAY_MS)
  const heatDate = isoDate(now - 3 * DAY_MS)
  const gibs = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'
  return [
    { id: 'ndvi', label: 'Vegetation health', date: ndviDate, maxNativeZoom: 9, resolution: 'each square ≈ 6 ha',
      hint: 'Greener = denser, more active plants. No color = no data (clouds or water).',
      tiles: `${gibs}/MODIS_Terra_NDVI_8Day/default/${ndviDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png` },
    { id: 'lst', label: 'Ground heat', date: heatDate, maxNativeZoom: 7, resolution: 'each square ≈ 100 ha',
      hint: 'Daytime temperature of the ground surface. Helps spot hotter, drier areas. No color = clouds.',
      tiles: `${gibs}/MODIS_Terra_Land_Surface_Temp_Day/default/${heatDate}/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png` },
    { id: 'imerg', label: 'Rain (IMERG)', date: isoDate(now - 2 * DAY_MS), maxNativeZoom: 6, resolution: 'each square ≈ 11 km',
      hint: 'Rain falling that day, from the GPM satellites. No color = no rain.',
      tiles: `${gibs}/IMERG_Precipitation_Rate/default/${isoDate(now - 2 * DAY_MS)}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png` },
    { id: 'smap', label: 'Soil moisture (SMAP)', date: isoDate(now - 3 * DAY_MS), maxNativeZoom: 6, resolution: 'each square ≈ 9 km',
      hint: 'Water in the top 5 cm of soil. SMAP passes every 2–3 days, so some stripes have no data.',
      tiles: `${gibs}/SMAP_L3_Passive_Enhanced_Day_Soil_Moisture/default/${isoDate(now - 3 * DAY_MS)}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png` },
  ]
}

// Place search with OpenStreetMap Nominatim. Its usage policy asks for caching and few requests.
const searchCache = new Map()
// viewbox: 'west,north,east,south'. bounded: only results inside it (the Lambayeque search uses both).
export async function searchPlaces(q, viewbox, bounded = false) {
  const key = `${q.toLowerCase()}|${viewbox}|${bounded}`
  if (searchCache.has(key)) return searchCache.get(key)
  const params = new URLSearchParams({ q, format: 'jsonv2', limit: bounded ? '8' : '5', 'accept-language': 'es' })
  if (viewbox) params.set('viewbox', viewbox)   // prefer what the user is looking at, without excluding the rest
  if (bounded) params.set('bounded', '1')
  const r = await fetch(`https://nominatim.openstreetmap.org/search?${params}`)
  if (!r.ok) throw new Error(`Place search answered ${r.status}`)
  const places = (await r.json()).map(it => {
    const [title, ...rest] = it.display_name.split(', ')
    const bb = it.boundingbox?.map(Number)   // [south, north, west, east]
    return { id: it.place_id, title, detail: rest.join(', '), lat: +it.lat, lon: +it.lon, bounds: bb?.length === 4 ? [[bb[0], bb[2]], [bb[1], bb[3]]] : null, category: it.category, type: it.type }
  })
  searchCache.set(key, places)
  return places
}
