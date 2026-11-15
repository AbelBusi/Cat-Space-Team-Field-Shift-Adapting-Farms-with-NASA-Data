// Data for the 3D view of an outlined field: a square of land around it, its heights and its satellite photo.
// Heights: Terrain Tiles on AWS Open Data (Terrarium PNG, NASA SRTM 30 m in Peru). Photo: Esri World Imagery, with
// Sentinel-2 cloudless as the fallback. All three answer browser requests (CORS), so no backend is needed.
import { PAL } from './palette.js'
import { insideRing } from './geo.js'

const TILE = 256
const lon2x = (lon, z) => (lon + 180) / 360 * TILE * 2 ** z
const lat2y = (lat, z) => { const s = Math.sin(lat * Math.PI / 180); return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * TILE * 2 ** z }
const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

const ELEVATION = (z, x, y) => `https://elevation-tiles-prod.s3.amazonaws.com/terrarium/${z}/${x}/${y}.png`
const ESRI = (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
const SENTINEL = (z, x, y) => `https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/${z}/${y}/${x}.jpg`   // up to zoom 14

const loadImage = url => new Promise((ok, fail) => {
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => ok(img)
  img.onerror = () => fail(new Error(`tile not available: ${url}`))
  img.src = url
})

// Paints the tiles that cover a box (pixels at zoom z) on one canvas cropped to the box. Fails only if no tile loads.
// The box is snapped to whole pixels: a tile drawn at half a pixel leaves a see-through edge, and a see-through
// elevation pixel would read as −32 km.
async function mosaic(tileUrl, z, box) {
  const [x0, y0, x1, y1] = [Math.floor(box[0]), Math.floor(box[1]), Math.ceil(box[2]), Math.ceil(box[3])]
  const cv = document.createElement('canvas')
  cv.width = Math.round(x1 - x0)
  cv.height = Math.round(y1 - y0)
  const ctx = cv.getContext('2d', { willReadFrequently: true }), jobs = []
  for (let ty = Math.floor(y0 / TILE); ty <= Math.floor((y1 - 1) / TILE); ty++)
    for (let tx = Math.floor(x0 / TILE); tx <= Math.floor((x1 - 1) / TILE); tx++)
      jobs.push(loadImage(tileUrl(z, tx, ty)).then(img => ctx.drawImage(img, tx * TILE - x0, ty * TILE - y0)))
  const done = await Promise.allSettled(jobs)
  if (!done.some(r => r.status === 'fulfilled')) throw new Error('no tiles')
  return cv
}

// The square of land shown: about three times the field, never smaller than 700 m or larger than 15 km.
export function framing(ring) {
  const lats = ring.map(p => p[0]), lons = ring.map(p => p[1])
  const lat = (Math.min(...lats) + Math.max(...lats)) / 2, lon = (Math.min(...lons) + Math.max(...lons)) / 2
  const mLat = 111320, mLon = 111320 * Math.cos(lat * Math.PI / 180)
  const span = Math.max((Math.max(...lats) - Math.min(...lats)) * mLat, (Math.max(...lons) - Math.min(...lons)) * mLon)
  const size = clamp(span * 3.2, 700, 15000), half = size / 2
  return { lat, lon, size, north: lat + half / mLat, south: lat - half / mLat, west: lon - half / mLon, east: lon + half / mLon }
}

// Everything the scene needs: a height grid (meters), the photo with the field marked on it, and the field's numbers.
export async function loadTerrain(ring, N = 128) {
  const f = framing(ring), mpp0 = 156543.03 * Math.cos(f.lat * Math.PI / 180)
  let zPhoto = clamp(Math.round(Math.log2(mpp0 * 1280 / f.size)), 10, 17)
  const box = z => [lon2x(f.west, z), lat2y(f.north, z), lon2x(f.east, z), lat2y(f.south, z)]
  while (box(zPhoto)[2] - box(zPhoto)[0] > 2048) zPhoto--
  const zElev = clamp(zPhoto - 2, 8, 15)

  const [elevCanvas, photo] = await Promise.all([
    mosaic(ELEVATION, zElev, box(zElev)),
    mosaic(ESRI, zPhoto, box(zPhoto)).catch(() => mosaic(SENTINEL, Math.min(zPhoto, 14), box(Math.min(zPhoto, 14)))),
  ])

  // Terrarium: height = R × 256 + G + B / 256 − 32768 (meters).
  // Pixels from a tile that did not load are empty: they take the median height instead of a false −32 km.
  const { width: W, height: H } = elevCanvas, px = elevCanvas.getContext('2d').getImageData(0, 0, W, H).data
  const raw = new Float32Array(W * H)
  for (let k = 0; k < W * H; k++) raw[k] = px[k * 4 + 3] === 255 ? px[k * 4] * 256 + px[k * 4 + 1] + px[k * 4 + 2] / 256 - 32768 : NaN
  const good = raw.filter(h => h > -500 && h < 7000).sort()
  const median = good.length ? good[good.length >> 1] : 0
  for (let k = 0; k < raw.length; k++) if (!(raw[k] > -500 && raw[k] < 7000)) raw[k] = median
  const at = (x, y) => raw[clamp(y, 0, H - 1) * W + clamp(x, 0, W - 1)]
  const sample = (u, v) => {   // bilinear
    const x = u * (W - 1), y = v * (H - 1), x0 = Math.floor(x), y0 = Math.floor(y), dx = x - x0, dy = y - y0
    return at(x0, y0) * (1 - dx) * (1 - dy) + at(x0 + 1, y0) * dx * (1 - dy) + at(x0, y0 + 1) * (1 - dx) * dy + at(x0 + 1, y0 + 1) * dx * dy
  }
  const heights = new Float32Array(N * N)
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) heights[i * N + j] = sample(j / (N - 1), i / (N - 1))

  // u, v (0..1 across the square, v going south) of a [lat, lon]; and back.
  const [bx0, by0, bx1, by1] = box(0)
  const toUV = ([lat, lon]) => [(lon2x(lon, 0) - bx0) / (bx1 - bx0), (lat2y(lat, 0) - by0) / (by1 - by0)]
  const toLatLon = (u, v) => [f.north - v * (f.north - f.south), f.west + u * (f.east - f.west)]
  const fieldUV = ring.map(toUV)

  // The field on the photo: everything around it a little darker, and its edge in campfire orange.
  const ctx = photo.getContext('2d')
  ctx.save()
  ctx.beginPath()
  ctx.rect(0, 0, photo.width, photo.height)
  fieldUV.forEach(([u, v], k) => ctx[k ? 'lineTo' : 'moveTo'](u * photo.width, v * photo.height))
  ctx.closePath()
  ctx.fillStyle = 'rgba(11,16,38,.38)'
  ctx.fill('evenodd')
  ctx.beginPath()
  fieldUV.forEach(([u, v], k) => ctx[k ? 'lineTo' : 'moveTo'](u * photo.width, v * photo.height))
  ctx.closePath()
  ctx.lineWidth = Math.max(3, photo.width / 400)
  ctx.strokeStyle = PAL.fire
  ctx.stroke()
  ctx.restore()

  // The field's own numbers, from the grid points that fall inside it (the whole field if it is smaller than a cell).
  const step = f.size / (N - 1), inside = []
  for (let i = 1; i < N - 1; i++) for (let j = 1; j < N - 1; j++) if (insideRing(toLatLon(j / (N - 1), i / (N - 1)), ring)) inside.push([i, j])
  if (!inside.length) { const [u, v] = toUV([f.lat, f.lon]); inside.push([Math.round(v * (N - 1)), Math.round(u * (N - 1))]) }
  const hs = inside.map(([i, j]) => heights[i * N + j])
  const slopes = inside.map(([i, j]) => {
    const gx = (heights[i * N + j + 1] - heights[i * N + j - 1]) / (2 * step), gy = (heights[(i + 1) * N + j] - heights[(i - 1) * N + j]) / (2 * step)
    return Math.atan(Math.hypot(gx, gy)) * 180 / Math.PI
  })
  let lo = Infinity, hi = -Infinity
  for (const h of heights) { lo = Math.min(lo, h); hi = Math.max(hi, h) }
  // Flat coastal land would look like a sheet of paper, so small relief is raised (and the factor is shown on screen).
  const relief = hi - lo, exaggeration = relief > 0 ? clamp(Math.round(f.size * 0.06 / relief * 2) / 2, 1, 8) : 8

  return {
    N, size: f.size, heights, min: lo, relief, photo, fieldUV, exaggeration,
    sampleUV: (u, v) => heights[Math.round(clamp(v, 0, 1) * (N - 1)) * N + Math.round(clamp(u, 0, 1) * (N - 1))],
    field: {
      min: Math.round(Math.min(...hs)), max: Math.round(Math.max(...hs)),
      slope: +(slopes.reduce((a, b) => a + b, 0) / slopes.length).toFixed(1),
      center: fieldUV.reduce((a, [u, v]) => [a[0] + u / fieldUV.length, a[1] + v / fieldUV.length], [0, 0]),
    },
  }
}
