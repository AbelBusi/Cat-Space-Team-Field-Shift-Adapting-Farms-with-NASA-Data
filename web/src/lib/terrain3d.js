// Data for the 3D view of an outlined field: the heights and the satellite photo of the field (with a thin margin).
// Heights: Terrain Tiles on AWS Open Data (Terrarium PNG, NASA SRTM 30 m in Peru). Photo: Esri World Imagery, with
// Sentinel-2 cloudless as the fallback. All three answer browser requests (CORS), so no backend is needed.
import { insideRing } from './geo.js'

const TILE = 256
const lon2x = (lon, z) => (lon + 180) / 360 * TILE * 2 ** z
const lat2y = (lat, z) => { const s = Math.sin(lat * Math.PI / 180); return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * TILE * 2 ** z }
const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

const ELEVATION = (z, x, y) => `https://elevation-tiles-prod.s3.amazonaws.com/terrarium/${z}/${x}/${y}.png`
const ESRI = (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
const SENTINEL = (z, x, y) => `https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/${z}/${y}/${x}.jpg`   // up to zoom 14

// Tiles are read as raw bytes: no color management. Terrarium stores height in the color itself (red × 256 m),
// so a browser "correcting" one red step would add a false 256 m spike.
async function loadTile(url) {
  const r = await fetch(url, { mode: 'cors' })
  if (!r.ok) throw new Error(`tile ${r.status}: ${url}`)
  return createImageBitmap(await r.blob(), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' })
}

// Paints the tiles that cover a box (pixels at zoom z) on one canvas cropped to the box. Fails only if no tile loads.
// The box is snapped to whole pixels, so no tile is resampled.
async function mosaic(tileUrl, z, box) {
  const [x0, y0, x1, y1] = [Math.floor(box[0]), Math.floor(box[1]), Math.ceil(box[2]), Math.ceil(box[3])]
  const cv = document.createElement('canvas')
  cv.width = x1 - x0
  cv.height = y1 - y0
  const ctx = cv.getContext('2d', { willReadFrequently: true }), jobs = []
  ctx.imageSmoothingEnabled = false
  for (let ty = Math.floor(y0 / TILE); ty <= Math.floor((y1 - 1) / TILE); ty++)
    for (let tx = Math.floor(x0 / TILE); tx <= Math.floor((x1 - 1) / TILE); tx++)
      jobs.push(loadTile(tileUrl(z, tx, ty)).then(img => ctx.drawImage(img, tx * TILE - x0, ty * TILE - y0)))
  const done = await Promise.allSettled(jobs)
  if (!done.some(r => r.status === 'fulfilled')) throw new Error('no tiles')
  return cv
}

// Heights from the Terrarium pixels, cleaned twice: pixels with no data take the median, and a 3 × 3 median filter
// removes single-pixel spikes the source can still have (SRTM is 30 m: nothing real is smaller than that).
function decodeHeights(canvas) {
  const { width: W, height: H } = canvas, px = canvas.getContext('2d').getImageData(0, 0, W, H).data
  const raw = new Float32Array(W * H)
  for (let k = 0; k < W * H; k++) raw[k] = px[k * 4 + 3] === 255 ? px[k * 4] * 256 + px[k * 4 + 1] + px[k * 4 + 2] / 256 - 32768 : NaN
  const valid = h => h > -500 && h < 7000
  const sorted = raw.filter(valid).sort(), median = sorted.length ? sorted[sorted.length >> 1] : 0
  const out = new Float32Array(W * H), win = []
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    win.length = 0
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const h = raw[clamp(y + dy, 0, H - 1) * W + clamp(x + dx, 0, W - 1)]
      if (valid(h)) win.push(h)
    }
    out[y * W + x] = win.length ? win.sort((a, b) => a - b)[win.length >> 1] : median
  }
  return { W, H, h: out }
}

// The field's square: its bounding box plus a thin margin, at least 150 m wide.
export function framing(ring) {
  const lats = ring.map(p => p[0]), lons = ring.map(p => p[1])
  const lat = (Math.min(...lats) + Math.max(...lats)) / 2, lon = (Math.min(...lons) + Math.max(...lons)) / 2
  const mLat = 111320, mLon = 111320 * Math.cos(lat * Math.PI / 180)
  const span = Math.max((Math.max(...lats) - Math.min(...lats)) * mLat, (Math.max(...lons) - Math.min(...lons)) * mLon)
  const size = Math.max(150, span * 1.08), half = size / 2
  return { lat, lon, size, north: lat + half / mLat, south: lat - half / mLat, west: lon - half / mLon, east: lon + half / mLon }
}

// Everything the scene needs: heights (meters) to sample anywhere in the square, the photo, the field's outline in
// u, v (0..1 across the square, v going south) and the field's own numbers.
export async function loadTerrain(ring) {
  const f = framing(ring), mpp0 = 156543.03 * Math.cos(f.lat * Math.PI / 180)
  const box = z => [lon2x(f.west, z), lat2y(f.north, z), lon2x(f.east, z), lat2y(f.south, z)]
  // Zoom 17 at most, as on the 2D map: Esri has no imagery beyond it in much of rural Lambayeque (it sends a placeholder).
  let zPhoto = clamp(Math.round(Math.log2(mpp0 * 1536 / f.size)), 10, 17)
  while (box(zPhoto)[2] - box(zPhoto)[0] > 2048) zPhoto--
  const zElev = clamp(zPhoto - 2, 8, 15)

  const [elevCanvas, photo] = await Promise.all([
    mosaic(ELEVATION, zElev, box(zElev)),
    mosaic(ESRI, zPhoto, box(zPhoto)).catch(() => mosaic(SENTINEL, Math.min(zPhoto, 14), box(Math.min(zPhoto, 14)))),
  ])
  const dem = decodeHeights(elevCanvas)
  // Both canvases start at a whole pixel just before the square: map u, v of the square into each of them.
  const [ex0, ey0, ex1, ey1] = box(zElev), ox = ex0 - Math.floor(ex0), oy = ey0 - Math.floor(ey0)
  const at = (x, y) => dem.h[clamp(y, 0, dem.H - 1) * dem.W + clamp(x, 0, dem.W - 1)]
  const sample = (u, v) => {   // bilinear, between pixel centers
    const x = ox + u * (ex1 - ex0) - 0.5, y = oy + v * (ey1 - ey0) - 0.5, x0 = Math.floor(x), y0 = Math.floor(y), dx = x - x0, dy = y - y0
    return at(x0, y0) * (1 - dx) * (1 - dy) + at(x0 + 1, y0) * dx * (1 - dy) + at(x0, y0 + 1) * (1 - dx) * dy + at(x0 + 1, y0 + 1) * dx * dy
  }
  const zp = box(zPhoto)[2] - box(zPhoto)[0] > photo.width + 2 ? Math.min(zPhoto, 14) : zPhoto   // the fallback photo is coarser
  const [px0, py0, px1, py1] = box(zp)
  const photoUV = { u0: (px0 - Math.floor(px0)) / photo.width, v0: (py0 - Math.floor(py0)) / photo.height, su: (px1 - px0) / photo.width, sv: (py1 - py0) / photo.height }

  const [bx0, by0, bx1, by1] = box(0)
  const toUV = ([lat, lon]) => [(lon2x(lon, 0) - bx0) / (bx1 - bx0), (lat2y(lat, 0) - by0) / (by1 - by0)]
  const toLatLon = (u, v) => [f.north - v * (f.north - f.south), f.west + u * (f.east - f.west)]
  const fieldUV = ring.map(toUV)

  // The field's numbers, from a 60 × 60 net of points inside it.
  const n = 60, step = f.size / n, hs = [], slopes = [], fall = [0, 0]
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
    const u = j / n, v = i / n
    if (!insideRing(toLatLon(u, v), ring)) continue
    const d = 1 / n
    hs.push(sample(u, v))
    const gx = (sample(u + d, v) - sample(u - d, v)) / (2 * step), gy = (sample(u, v + d) - sample(u, v - d)) / (2 * step)
    slopes.push(Math.atan(Math.hypot(gx, gy)) * 180 / Math.PI)
    fall[0] -= gx; fall[1] -= gy   // downhill, in u, v
  }
  if (!hs.length) { hs.push(sample(0.5, 0.5)); slopes.push(0) }
  const lo = Math.min(...hs), hi = Math.max(...hs), relief = hi - lo
  // A flat field would look like a sheet of paper, so small relief is raised (the factor is shown on screen).
  const exaggeration = relief > 0.5 ? clamp(Math.round(f.size * 0.05 / relief * 2) / 2, 1, 5) : 5

  return {
    size: f.size, sample, photo, photoUV, fieldUV, min: lo, relief, exaggeration,
    field: {
      min: Math.round(lo), max: Math.round(hi), slope: +(slopes.reduce((a, b) => a + b, 0) / slopes.length).toFixed(1),
      downhill: Math.hypot(...fall) > 1e-9 ? fall.map(c => c / Math.hypot(...fall)) : [1, 0],   // unit direction the land falls to
    },
  }
}
