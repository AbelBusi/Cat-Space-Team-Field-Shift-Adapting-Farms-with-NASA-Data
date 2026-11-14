<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import * as d3 from 'd3'
import Reveal from './Reveal.vue'
import SignalPanel from './SignalPanel.vue'
import { LAYERS, MONTHS, M1, ICON, PLACES } from '../content.js'
import { state, db, valueAt, selectPoint } from '../store.js'
import { useScript, say } from '../guide.js'
import { gridCells, gibsDataLayers, searchPlaces } from '../lib/nasa.js'
import { parseCoordinates, polygonAreaM2, ringPerimeterM, vertexCenter, formatArea, formatLength, formatShortDate } from '../lib/geo.js'

const el = ref(null)
useScript('map', el)

const gibs = (layer, matrix, ext) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/default/${matrix}/{z}/{y}/{x}.${ext}`
const mapEl = ref(null)
let map, cellLayer, powerRect, parcelLayer, dataLayer
const rects = {}

const L_ = computed(() => LAYERS[state.layer])
const legendStops = computed(() => { const sc = L_.value.scale(), [a, b] = L_.value.domain; return d3.range(0, 1.0001, 0.125).map(p => sc(a + p * (b - a))).join(',') })
const cells = computed(() => state.point ? gridCells(state.point.lat, state.point.lon) : [])

// Nested squares appear one after another, from the biggest cell to the smallest.
function drawCells() {
  if (!map || !state.point) return
  cellLayer.clearLayers()
  cells.value.forEach((c, i) => {
    const r = L.rectangle(c.bounds, { color: c.color, weight: c.id === 'power' ? 3 : 2, fillOpacity: c.id === 'power' ? 0.5 : 0, fillColor: c.color, className: 'grid-cell', interactive: false })
    r.addTo(cellLayer)
    r.getElement()?.style.setProperty('animation-delay', `${400 + i * 180}ms`)
    rects[c.id] = r
  })
  powerRect = rects.power
  L.circleMarker([state.point.lat, state.point.lon], { radius: 6, color: '#0A0B0D', weight: 2, fillColor: '#FFFFFF', fillOpacity: 1, className: 'pt' }).addTo(cellLayer)
  paintCell()
  // With an outlined field, keep the view on the field; otherwise show the whole climate cell.
  if (state.parcel) map.flyToBounds(L.latLngBounds(state.parcel.ring).pad(0.6), { duration: 1, maxZoom: 17 })
  else map.flyToBounds(L.latLngBounds(cells.value[0].bounds).pad(0.8), { duration: 1.2 })
}
// The POWER square takes the color of the chosen signal and month.
function paintCell() {
  const v = valueAt(state.layer)
  powerRect?.setStyle({ fillColor: v == null ? '#888' : L_.value.scale()(v), fillOpacity: v == null ? 0.15 : 0.45 })
}
function zoomTo(c) { map?.flyToBounds(L.latLngBounds(c.bounds).pad(1.5), { duration: 1, maxZoom: 18 }) }

onMounted(() => {
  // Whole zoom levels only: fractional zoom leaves thin seams between tiles.
  map = L.map(mapEl.value, { worldCopyJump: true, minZoom: 2, maxZoom: 18, zoomSnap: 1 }).setView([0, -40], 2)
  // Satellite base in two layers: Sentinel-2 cloudless (global, ~10 m, up to zoom 14), then Esri World Imagery
  // (≈1 m in many places) from zoom 12 to 17. Both have their own licenses: see docs/DATA_SOURCES.md.
  L.tileLayer('https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg', {
    maxNativeZoom: 14, maxZoom: 18,
    attribution: '<a href="https://s2maps.eu">Sentinel-2 cloudless</a> by EOX (contains modified Copernicus Sentinel data 2024)',
  }).addTo(map)
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    minZoom: 12, maxNativeZoom: 17, maxZoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
  }).addTo(map)
  L.tileLayer(gibs('Reference_Labels_15m', 'GoogleMapsCompatible_Level13', 'png'), { maxNativeZoom: 13, maxZoom: 18, attribution: 'Labels: NASA GIBS' }).addTo(map)
  map.createPane('data').style.zIndex = 350   // NASA data images sit under the grid cells and the field outline
  L.control.scale({ imperial: false }).addTo(map)
  cellLayer = L.layerGroup().addTo(map)
  parcelLayer = L.layerGroup().addTo(map)
  map.on('click', e => drawing.value ? addCorner(e.latlng) : pickPoint(e.latlng.lat, e.latlng.lng))
  drawCells()
})
onBeforeUnmount(() => { clearInterval(playTimer); map?.remove() })
watch(() => state.point, drawCells)
watch(() => [state.layer, state.month, state.scen, db.power, db.ndvi], paintCell)

// Any new place forgets the outlined field.
function pickPoint(lat, lon, name) {
  state.parcel = null
  corners.value = []
  drawParcel()
  selectPoint(lat, lon, name)
}

// Search: a place name (OpenStreetMap Nominatim) or coordinates.
const query = ref('')
const results = ref([])
const searchState = ref('idle')   // idle | loading | empty | error
async function search() {
  const q = query.value.trim()
  if (!q) return
  const c = parseCoordinates(q)
  if (c) { results.value = []; searchState.value = 'idle'; return pickPoint(c[0], c[1]) }
  searchState.value = 'loading'
  try {
    const b = map.getBounds()
    results.value = await searchPlaces(q, map.getZoom() >= 5 ? [b.getWest(), b.getNorth(), b.getEast(), b.getSouth()].join(',') : null)
    searchState.value = results.value.length ? 'idle' : 'empty'
  } catch {
    results.value = []
    searchState.value = 'error'
  }
}
function choose(place) {
  query.value = place.title
  results.value = []
  pickPoint(place.lat, place.lon, place.title)
}

function myLocation() {
  if (!navigator.geolocation) return say('This browser can\'t share its location. You can tap the map instead.', 'sad')
  navigator.geolocation.getCurrentPosition(
    p => pickPoint(p.coords.latitude, p.coords.longitude, 'Your location'),
    e => say(e.code === 1
      ? 'I don\'t have permission to see your location. You can allow it in the browser settings, or just tap the map.'
      : 'I couldn\'t find your location. Try again, ideally outdoors, or tap the map.', 'shy'),
    { enableHighAccuracy: true },
  )
}

// Outline my field: each tap adds a corner. The finished outline gives area, perimeter and a center point.
const drawing = ref(false)
const corners = ref([])
const C = '#FDE047'
function drawParcel() {
  if (!parcelLayer) return
  parcelLayer.clearLayers()
  const pts = corners.value
  if (pts.length >= 3) L.polygon(pts, { color: C, weight: 3, fillColor: C, fillOpacity: 0.18, interactive: false }).addTo(parcelLayer)
  else if (pts.length === 2) L.polyline(pts, { color: C, weight: 3, interactive: false }).addTo(parcelLayer)
  if (drawing.value) pts.forEach(p => L.circleMarker(p, { radius: 6, color: '#A16207', weight: 2.5, fillColor: '#FFFFFF', fillOpacity: 1, interactive: false }).addTo(parcelLayer))
}
function setDrawing(on) {
  drawing.value = on
  map.getContainer().style.cursor = on ? 'crosshair' : ''
  on ? map.doubleClickZoom.disable() : map.doubleClickZoom.enable()   // a double tap must not zoom mid-outline
  drawParcel()
}
function startOutline() {
  corners.value = []
  state.parcel = null
  setDrawing(true)
  if (state.point && map.getZoom() < 15) map.flyTo([state.point.lat, state.point.lon], 16, { duration: 1 })
  say('Tap each corner of your field on the map. When you have at least three, press Finish.', 'happy')
}
function addCorner(ll) { corners.value = [...corners.value, [ll.lat, ll.lng]]; drawParcel() }
function undoCorner() { corners.value = corners.value.slice(0, -1); drawParcel() }
function editOutline() { state.parcel = null; setDrawing(true) }
function clearOutline() { corners.value = []; state.parcel = null; setDrawing(false) }
function finishOutline() {
  if (corners.value.length < 3) return
  const ring = corners.value
  state.parcel = { ring, areaM2: polygonAreaM2(ring), perimeterM: ringPerimeterM(ring) }
  setDrawing(false)
  const [lat, lon] = vertexCenter(ring)
  selectPoint(lat, lon, 'Your field')
}

// One NASA image layer at a time: two color scales on top of each other are hard to read.
const dataLayers = gibsDataLayers()
const activeData = ref(null)
const intensity = ref(0.7)
watch(activeData, id => {
  dataLayer?.remove()
  dataLayer = null
  const d = dataLayers.find(x => x.id === id)
  if (d) dataLayer = L.tileLayer(d.tiles, { pane: 'data', maxNativeZoom: d.maxNativeZoom, maxZoom: 18, opacity: intensity.value, attribution: 'Data: NASA GIBS' }).addTo(map)
})
watch(intensity, v => dataLayer?.setOpacity(v))
const activeInfo = computed(() => dataLayers.find(x => x.id === activeData.value))

function setScen(s) {
  state.scen = s
  say(s === 'nino' ? 'El Niño years! Now every month is the average of the El Niño years only. Watch how the colors change.' : 'Back to the typical year: the average of 2001 to 2024.', s === 'nino' ? 'surprised' : 'neutral')
}

const playing = ref(false)
let playTimer
function togglePlay() {
  playing.value = !playing.value
  clearInterval(playTimer)
  if (!playing.value) return
  if (L_.value.pending) state.layer = 'heat'
  playTimer = setInterval(() => { state.month = (state.month + 1) % 12 }, 900)
}
</script>

<template>
  <section ref="el" class="step">
    <div class="wrap">
      <div class="step-head">
        <span class="step-num">1</span>
        <h2>Find your field, anywhere on Earth</h2>
        <p>Search a place, tap the map or try an example. You can also outline your own field. We fetch real NASA data for that spot and show the grid cells each satellite uses.</p>
      </div>
      <div class="map-grid">
        <Reveal :at="0">
          <div class="card map-card">
            <div class="map-toolbar">
              <div class="places" role="group" aria-label="Example places">
                <button v-for="p in PLACES" :key="p.name" type="button" class="place-chip" :aria-pressed="state.point?.name === p.name" @click="pickPoint(p.lat, p.lon, p.name)">{{ p.name }}</button>
              </div>
              <form class="coords" role="search" @submit.prevent="search">
                <label for="place-q" class="sr-only">Search a place or coordinates</label>
                <input id="place-q" v-model="query" placeholder="Town, district or lat, lon" autocomplete="off" enterkeyhint="search" @keydown.esc="results = []">
                <button type="submit" class="mini-btn" :disabled="!query.trim() || searchState === 'loading'">{{ searchState === 'loading' ? 'Searching…' : 'Search' }}</button>
                <button type="button" class="mini-btn" @click="myLocation">My location</button>
              </form>
              <p v-if="searchState === 'empty'" class="coords-err">No place found. Try another name, or coordinates like -6.77, -79.84</p>
              <p v-if="searchState === 'error'" class="coords-err" role="alert">Search is not available right now. Check the connection and try again.</p>
              <ul v-if="results.length" class="results">
                <li v-for="r in results" :key="r.id"><button type="button" @click="choose(r)"><b>{{ r.title }}</b><span>{{ r.detail }}</span></button></li>
              </ul>
            </div>
            <div class="map-stage" :class="{ loading: db.loading }">
              <div ref="mapEl" class="leaflet-host" role="application" aria-label="World map. Click to choose a place." />
              <div v-if="drawing" class="map-status">Tap each corner of your field</div>
              <div v-else-if="db.loading" class="map-status">Listening to NASA POWER…</div>
            </div>
            <div class="map-tools">
              <section class="tool" aria-label="My field">
                <template v-if="drawing">
                  <p class="small">{{ corners.length < 3 ? `Tap at least 3 corners (you have ${corners.length}).` : `${corners.length} corners. Press Finish when done.` }}</p>
                  <div class="tool-row">
                    <button type="button" class="mini-btn" :disabled="!corners.length" @click="undoCorner">Undo</button>
                    <button type="button" class="mini-btn solid" :disabled="corners.length < 3" @click="finishOutline">Finish</button>
                    <button type="button" class="link-btn" @click="clearOutline">Cancel</button>
                  </div>
                </template>
                <template v-else-if="state.parcel">
                  <p class="small"><b>Your field:</b> {{ formatArea(state.parcel.areaM2) }} · perimeter {{ formatLength(state.parcel.perimeterM) }}</p>
                  <div class="tool-row">
                    <button type="button" class="mini-btn" @click="editOutline">Edit outline</button>
                    <button type="button" class="link-btn" @click="clearOutline">Delete</button>
                  </div>
                </template>
                <template v-else>
                  <p class="small muted">Outline your land to get its size and read NASA data at its center.</p>
                  <button type="button" class="mini-btn solid" @click="startOutline">Outline my field</button>
                </template>
              </section>
              <section class="tool" aria-label="NASA image layers">
                <div class="seg small-seg" role="group" aria-label="Paint NASA images on the map">
                  <button type="button" :aria-pressed="!activeData" @click="activeData = null">Satellite only</button>
                  <button v-for="d in dataLayers" :key="d.id" type="button" :aria-pressed="activeData === d.id" @click="activeData = d.id">{{ d.label }}</button>
                </div>
                <template v-if="activeInfo">
                  <p class="small muted">{{ activeInfo.hint }} {{ activeInfo.resolution }} · NASA, {{ formatShortDate(activeInfo.date) }}</p>
                  <label class="intensity small">Intensity <input v-model.number="intensity" type="range" min="0.3" max="1" step="0.05"></label>
                </template>
              </section>
            </div>
            <Reveal :at="1">
              <ul class="cells">
                <li v-for="c in cells" :key="c.id">
                  <button type="button" class="cell-btn" @click="zoomTo(c)">
                    <i :style="{ borderColor: c.color }" /><b>{{ c.name }}</b><span>{{ c.size }}</span><span class="muted">{{ c.what }}</span>
                  </button>
                </li>
              </ul>
            </Reveal>
            <Reveal :at="2">
              <div class="legend">
                <div class="seg" role="group" aria-label="Kind of year">
                  <button type="button" :aria-pressed="state.scen === 'normal'" @click="setScen('normal')">Typical year</button>
                  <button type="button" :aria-pressed="state.scen === 'nino'" @click="setScen('nino')">El Niño years</button>
                </div>
                <span>Less</span>
                <span class="bar" :style="{ background: `linear-gradient(90deg, ${legendStops})` }" />
                <span>More</span>
                <span class="src">Source: {{ L_.ds }}</span>
              </div>
              <div class="timeline">
                <button type="button" class="play" :aria-label="playing ? 'Pause' : 'Play the 12 months'" @click="togglePlay">
                  <svg viewBox="0 0 24 24" aria-hidden="true" v-html="playing ? ICON.pause : ICON.play" />
                </button>
                <div class="months">
                  <input type="range" min="0" max="11" step="1" :value="state.month" aria-label="Month"
                         @input="state.month = +$event.target.value; playing && togglePlay()">
                  <div class="month-ticks" aria-hidden="true"><span v-for="(m, i) in M1" :key="i">{{ m }}</span></div>
                </div>
                <Transition name="flip" mode="out-in">
                  <div :key="state.month" class="month-name">{{ MONTHS[state.month] }}</div>
                </Transition>
              </div>
            </Reveal>
          </div>
        </Reveal>
        <Reveal :at="3"><SignalPanel /></Reveal>
      </div>
    </div>
  </section>
</template>
