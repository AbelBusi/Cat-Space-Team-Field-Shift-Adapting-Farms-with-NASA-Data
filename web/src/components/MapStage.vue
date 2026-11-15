<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import * as d3 from 'd3'
import { LAYERS } from '../content.js'
import { state, db, valueAt, selectPoint, local, cell, mapUi, mapApi } from '../store.js'
import { PAL, RAMP } from '../lib/palette.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'
import { gridCells, gibsDataLayers } from '../lib/nasa.js'
import { polygonAreaM2, ringPerimeterM, vertexCenter } from '../lib/geo.js'
import { inRings, boundsOf, locate } from '../lib/admin.js'
import PLACES from '../data/lambayeque_places.json'

// The satellite map, cut to the outline of the territory (a district, or the department in free mode): outside it
// the night sky shows through. Everything else on screen floats above this map.
// tint: the climate square colors the territory with the chosen signal. squares: draw the outline of every satellite's
// square (only the topic that explains them, so the first view stays clean).
const props = defineProps({ tint: Boolean, squares: Boolean })

const mapEl = ref(null)
let map, edgeLayer, cellLayer, pointLayer, parcelLayer, coverLayer, dataLayer
const rects = {}
const L_ = computed(() => LAYERS[state.layer])
const latlngs = rings => rings.map(r => r.map(([lon, lat]) => [lat, lon]))

// ---- The territory: clip, outline and camera -------------------------------------------------------------------
// The clip is a CSS path on Leaflet's map pane, in the pane's own pixels, so it follows every pan for free.
// It is rebuilt when the zoom changes. An animated zoom moves the tiles with a CSS transition; the clip follows them
// frame by frame: `tracker` is an empty element that runs the same transition (like Leaflet's image overlays), and
// its live transform is applied to the outline, so no piece of land outside the territory ever flashes.
const outline = () => state.area.rings.map(r => r.map(([lon, lat]) => map.latLngToLayerPoint(L.latLng(lat, lon))))
function setClip(rings) {
  map.getPane('mapPane').style.clipPath = `path('${rings.map(r => 'M' + r.map(p => `${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join('L') + 'Z').join('')}')`
}
let tracker, following = 0
function clip() {
  cancelAnimationFrame(following)
  following = 0
  if (tracker) tracker.style.transform = ''
  setClip(outline())
}
function followZoom(e) {
  const from = outline()
  const k = map.getZoomScale(e.zoom, map.getZoom())
  const a = map._latLngToNewLayerPoint(map.layerPointToLatLng([0, 0]), e.zoom, e.center)   // where layer point 0,0 lands
  L.DomUtil.setTransform(tracker, a, k)
  cancelAnimationFrame(following)
  const step = () => {
    const m = new DOMMatrix(getComputedStyle(tracker).transform)
    setClip(from.map(r => r.map(p => m.transformPoint(new DOMPoint(p.x, p.y)))))
    following = requestAnimationFrame(step)
  }
  following = requestAnimationFrame(step)
}
// Room for the cards (left and right) and for Sprout (bottom), so the territory sits in the free middle of the screen.
function padding() {
  const edge = (sel, side, fallback) => document.querySelector(sel)?.getBoundingClientRect()[side] ?? fallback
  const top = edge('[data-hud-top]', 'bottom', 150) + 14
  if (innerWidth < 1024) return { paddingTopLeft: [12, top], paddingBottomRight: [12, innerHeight * 0.44 + 12] }
  return { paddingTopLeft: [edge('.col-left', 'right', 380) + 16, top], paddingBottomRight: [innerWidth - edge('.col-right', 'left', innerWidth - 380) + 16, 150] }
}
function showArea() {
  const b = L.latLngBounds(boundsOf(state.area.rings))
  edgeLayer.clearLayers()
  L.polygon(latlngs(state.area.rings), { color: PAL.teal, weight: 4, fill: false, interactive: false, className: 'territory-edge' }).addTo(edgeLayer)
  map.setMinZoom(1).setMaxBounds(null)
  map.fitBounds(b, { ...padding(), animate: false })
  map.setMinZoom(map.getZoom() - 0.5).setMaxBounds(b.pad(1.6))
  clip()
}

// ---- The chosen point and the squares each satellite uses ------------------------------------------------------
function drawPoint() {
  if (!map || !state.point) return
  pointLayer.clearLayers()
  cellLayer.clearLayers()
  const at = [state.point.lat, state.point.lon]
  L.circleMarker(at, { radius: 11, color: PAL.fire, weight: 2, fill: false, interactive: false, className: 'grid-cell' }).addTo(pointLayer)
  L.circleMarker(at, { radius: 5, color: PAL.bg, weight: 2, fillColor: PAL.ink, fillOpacity: 1, interactive: false }).addTo(pointLayer)
  for (const k in rects) delete rects[k]
  if (props.tint || props.squares) gridCells(...at).filter(c => props.squares || c.id === 'power').forEach((c, i) => {
    const r = L.rectangle(c.bounds, { color: c.color, weight: !props.squares ? 0 : c.id === 'power' ? 3 : 2, fillOpacity: 0, fillColor: c.color, className: 'grid-cell', interactive: false }).addTo(cellLayer)
    r.getElement()?.style.setProperty('animation-delay', `${200 + i * 160}ms`)
    rects[c.id] = r
  })
  paint()
  drawCover()
}
// The big climate square takes the color of the chosen signal and month.
function paint() {
  const v = valueAt(state.layer)
  rects.power?.setStyle({ fillColor: v == null ? PAL.muted : L_.value.scale()(v), fillOpacity: !props.tint || mapUi.data ? 0 : v == null ? 0.1 : 0.24 })
}
// A big field is read as the average of every IMERG rain square it touches, with its share written in each one.
function drawCover() {
  if (!coverLayer) return
  coverLayer.clearLayers()
  const sq = cell.value?.squares, many = props.squares && sq?.length > 1
  rects.imerg?.setStyle({ opacity: many ? 0 : 1 })
  if (!many) return
  sq.forEach(([la, lo, share]) => {
    L.rectangle([[la - 0.05, lo - 0.05], [la + 0.05, lo + 0.05]], { color: PAL.teal, weight: 2, fillColor: PAL.teal, fillOpacity: 0.06 + 0.3 * share, interactive: false }).addTo(coverLayer)
    L.marker([la, lo], { interactive: false, keyboard: false, icon: L.divIcon({ className: 'share-label', html: `${Math.max(1, Math.round(share * 100))} %`, iconSize: [52, 20] }) }).addTo(coverLayer)
  })
}

// Any new place forgets the outlined field. In a district every point is that district; in free mode we look it up.
function pickPoint(lat, lon) {
  state.parcel = null
  corners = []
  drawParcel()
  selectPoint(lat, lon, state.area.kind === 'district' ? state.area.name : locate(lat, lon)?.district.name ?? null)
}
function onClick(e) {
  if (mapUi.drawing) return addCorner(e.latlng)
  const { lat, lng } = e.latlng
  if (inRings(lat, lng, state.area.rings)) return pickPoint(lat, lng)
  say(() => t('That spot is outside {place}. Tap inside the bright territory, or open free mode to explore all of Lambayeque.', { place: state.area.name }), 'shy', [], { level: 'note' })
}

// ---- Town and village names, like a road map, over the photo ------------------------------------------------------
// From OpenStreetMap (pipeline/build_places.py). The names of a territory are created once and ride along with the map
// (Leaflet moves them during zoom), so they never blink. After each zoom or pan we only decide which ones are visible:
// bigger places first, names already on screen keep their spot, and a name that would cover another one stays hidden.
const MIN_ZOOM = [0, 7, 11, 8.5, 10.5]   // city, town, suburb, village, hamlet
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
let labelLayer, labels = []
function findPlaces() {
  labelLayer.clearLayers()
  labels = PLACES.filter(([, lat, lon]) => inRings(lat, lon, state.area.rings)).map(([name, lat, lon, rank]) => {
    const w = name.length * (rank < 2 ? 8.5 : 7) + 10, h = rank < 2 ? 20 : 16
    const marker = L.marker([lat, lon], { pane: 'labels', interactive: false, keyboard: false,
      icon: L.divIcon({ className: `place-label rank-${rank} off`, html: esc(name), iconSize: [w, h] }) }).addTo(labelLayer)
    return { marker, rank, w, h, on: false }
  })
}
function drawLabels() {
  const z = map.getZoom(), size = map.getSize(), taken = []
  const order = [...labels].sort((a, b) => a.rank - b.rank || b.on - a.on)
  for (const l of order) {
    let show = z >= MIN_ZOOM[l.rank]
    if (show) {
      const p = map.latLngToContainerPoint(l.marker.getLatLng())
      const box = [p.x - l.w / 2, p.y - l.h / 2, p.x + l.w / 2, p.y + l.h / 2]
      show = box[2] > 0 && box[0] < size.x && box[3] > 0 && box[1] < size.y && !taken.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])
      if (show) taken.push(box)
    }
    if (show !== l.on) { l.on = show; l.marker.getElement()?.classList.toggle('off', !show) }
  }
}

// ---- Outline my field: each tap adds a corner --------------------------------------------------------------------
let corners = []
function drawParcel() {
  if (!parcelLayer) return
  parcelLayer.clearLayers()
  mapUi.corners = corners.length
  const C = PAL.fire   // the outlined field is the one thing to look at
  if (corners.length >= 3) L.polygon(corners, { color: C, weight: 3, fillColor: C, fillOpacity: 0.18, interactive: false }).addTo(parcelLayer)
  else if (corners.length === 2) L.polyline(corners, { color: C, weight: 3, interactive: false }).addTo(parcelLayer)
  if (mapUi.drawing) corners.forEach(p => L.circleMarker(p, { radius: 5, color: PAL.bg, weight: 2, fillColor: C, fillOpacity: 1, interactive: false }).addTo(parcelLayer))
}
function setDrawing(on) {
  mapUi.drawing = on
  map.getContainer().style.cursor = on ? 'crosshair' : ''
  on ? map.doubleClickZoom.disable() : map.doubleClickZoom.enable()   // a double tap must not zoom mid-outline
  drawParcel()
}
function addCorner(ll) { corners = [...corners, [ll.lat, ll.lng]]; drawParcel() }
Object.assign(mapApi, {
  zoomIn: () => map.zoomIn(), zoomOut: () => map.zoomOut(), refit: () => showArea(),
  zoomTo: c => map.flyToBounds(L.latLngBounds(c.bounds).pad(0.4), { duration: 0.8, maxZoom: 17 }),
  startOutline() {
    corners = []
    state.parcel = null
    setDrawing(true)
    if (state.point && map.getZoom() < 14) map.flyTo([state.point.lat, state.point.lon], 15, { duration: 0.9 })
    say('Tap each corner of your field on the map. When you have at least three, press Finish.', 'happy')
  },
  undoCorner() { corners = corners.slice(0, -1); drawParcel() },
  editOutline() { state.parcel = null; setDrawing(true) },
  clearOutline() { corners = []; state.parcel = null; setDrawing(false) },
  finishOutline() {
    if (corners.length < 3) return
    state.parcel = { ring: corners, areaM2: polygonAreaM2(corners), perimeterM: ringPerimeterM(corners) }
    setDrawing(false)
    const [lat, lon] = vertexCenter(corners)
    selectPoint(lat, lon, 'Your field')
    map.flyToBounds(L.latLngBounds(corners).pad(0.8), { duration: 0.9, maxZoom: 17 })
    mapUi.view3d = true   // a new field opens straight in 3D
  },
  locateMe() {
    if (!navigator.geolocation) return say('This browser can\'t share its location. You can tap the map instead.', 'sad', [], { level: 'force' })
    navigator.geolocation.getCurrentPosition(p => {
      const lat = p.coords.latitude, lon = p.coords.longitude
      if (!inRings(lat, lon, state.area.rings)) return say(() => t('You are outside {place} right now, so I kept the point where it was.', { place: state.area.name }), 'worried', [], { level: 'force' })
      pickPoint(lat, lon)
      map.flyTo([lat, lon], Math.max(map.getZoom(), 15), { duration: 0.9 })
    }, e => say(e.code === 1 ? 'I don\'t have permission to see your location. You can allow it in the browser settings, or just tap the map.'
      : 'I couldn\'t find your location. Try again, ideally outdoors, or tap the map.', 'shy', [], { level: 'force' }), { enableHighAccuracy: true, timeout: 15000 })
  },
})

// ---- One NASA image layer at a time, on top of the satellite photo ------------------------------------------------
const gibsLayers = gibsDataLayers()
// The 420 rain cells are painted on a 21 × 20 canvas and shown as ONE image: fast, whatever the zoom.
function gridImage() {
  const g = local.value, { lat, lon } = g.meta.grid, cv = document.createElement('canvas')
  cv.width = lon.length; cv.height = lat.length
  const ctx = cv.getContext('2d'), color = d3.scaleLinear().domain([0, 20, 60, 150]).range(RAMP.amount).clamp(true)
  const rows = g.rain[state.scen === 'nino' ? 'nino' : 'typical']
  for (let i = 0; i < lat.length; i++) for (let j = 0; j < lon.length; j++) {
    ctx.fillStyle = color(rows[i * lon.length + j][state.month] ?? 0)
    ctx.fillRect(j, lat.length - 1 - i, 1, 1)                       // canvas row 0 = north
  }
  const h = 0.05
  return { url: cv.toDataURL(), bounds: [[lat[0] - h, lon[0] - h], [lat[lat.length - 1] + h, lon[lon.length - 1] + h]] }
}
function showData() {
  dataLayer?.remove()
  dataLayer = null
  if (mapUi.data === 'grid' && local.value) {
    const { url, bounds } = gridImage()
    dataLayer = L.imageOverlay(url, bounds, { pane: 'data', opacity: mapUi.intensity, className: 'grid-image', attribution: 'Data: GPM IMERG (downloaded)' }).addTo(map)
    return
  }
  const d = gibsLayers.find(x => x.id === mapUi.data)
  if (d) dataLayer = L.tileLayer(d.tiles, { pane: 'data', maxNativeZoom: d.maxNativeZoom, maxZoom: 18, opacity: mapUi.intensity, attribution: 'Data: NASA GIBS' }).addTo(map)
}

const onResize = () => { map.invalidateSize(); clip() }
onMounted(() => {
  // Half zoom steps let the territory fill the free space; the tile style below hides the hairline seams they cause.
  map = L.map(mapEl.value, { zoomControl: false, maxZoom: 18, zoomSnap: 0.5, zoomDelta: 0.5, maxBoundsViscosity: 0.7 }).setView([-6.5, -79.9], 9)
  // Satellite base in two layers: Sentinel-2 cloudless (~10 m, up to zoom 14), then Esri World Imagery (≈1 m in many
  // places) from zoom 12 to 17. Both have their own licenses: see docs/DATA_SOURCES.md.
  L.tileLayer('https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg', {
    maxNativeZoom: 14, maxZoom: 18,
    attribution: '<a href="https://s2maps.eu">Sentinel-2 cloudless</a> by EOX (contains modified Copernicus Sentinel data 2024)',
  }).addTo(map)
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    minZoom: 12, maxNativeZoom: 17, maxZoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
  }).addTo(map)
  map.createPane('data').style.zIndex = 350   // NASA data images sit under the squares and the field outline
  map.createPane('labels').style.zIndex = 450  // names above the squares, under the point and the field corners
  map.attributionControl.setPosition('bottomleft')
  map.attributionControl.addAttribution('Boundaries © OpenStreetMap contributors')
  L.control.scale({ imperial: false, position: 'bottomright' }).addTo(map)
  edgeLayer = L.layerGroup().addTo(map)
  cellLayer = L.layerGroup().addTo(map)
  coverLayer = L.layerGroup().addTo(map)
  parcelLayer = L.layerGroup().addTo(map)
  pointLayer = L.layerGroup().addTo(map)
  labelLayer = L.layerGroup().addTo(map)
  map.on('zoomend moveend', drawLabels)
  map.on('click', onClick)
  tracker = L.DomUtil.create('div', 'leaflet-zoom-animated', map.getPane('mapPane'))
  tracker.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0'
  map.on('zoomanim', followZoom)
  map.on('zoom move viewreset zoomend moveend', clip)
  addEventListener('resize', onResize)
  showArea()
  findPlaces()
  drawLabels()
  drawPoint()
  showData()
})
onBeforeUnmount(() => { cancelAnimationFrame(following); removeEventListener('resize', onResize); mapUi.drawing = false; map?.remove() })

watch(() => state.area, () => { mapApi.clearOutline(); showArea(); findPlaces(); drawLabels() })
watch(() => [state.point, props.squares, props.tint], drawPoint)
watch(() => cell.value?.squares, drawCover)
watch(() => [state.layer, state.month, state.scen, db.power, db.ndvi], paint)
watch(() => mapUi.data, () => { showData(); paint() })
watch(() => [state.month, state.scen], () => { if (mapUi.data === 'grid') showData() })
watch(() => mapUi.intensity, v => dataLayer?.setOpacity(v))
</script>

<template>
  <!-- Leaflet owns the classes of its own element, so the changing class lives on a wrapper. -->
  <div class="absolute inset-0 z-0 isolate" :class="{ 'map-loading': db.loading }">
    <div ref="mapEl" class="size-full" role="application" :aria-label="t('Satellite map of {place}. Tap inside it to choose a spot.', { place: state.area?.name })" />
  </div>
</template>
