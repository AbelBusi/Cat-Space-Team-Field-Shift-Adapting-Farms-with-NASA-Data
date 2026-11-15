<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import HudCard from './HudCard.vue'
import { state, enterDistrict, enterFree, LAMBAYEQUE } from '../store.js'
import { enter, say } from '../guide.js'
import { t } from '../i18n.js'
import { useTween } from '../lib/tween.js'
import { DEPARTMENT, PROVINCES, ADMIN_SOURCE, locate, boundsOf } from '../lib/admin.js'
import { searchPlaces } from '../lib/nasa.js'
import PLACES from '../data/lambayeque_places.json'

// "Where do you farm?": the department with its provinces, then the districts of the province you tap.
// One drawing for everything: the camera (the SVG viewBox) glides from the department to a province to a district.
const [[S, W], [N, E]] = boundsOf(DEPARTMENT.rings)
const K = Math.cos((S + N) / 2 * Math.PI / 180), SCALE = 600
const px = ([lon, lat]) => [(lon - W) * K * SCALE, (N - lat) * SCALE]
const pathOf = rings => rings.map(r => 'M' + r.map(p => px(p).map(v => v.toFixed(1)).join(',')).join('L') + 'Z').join('')
const boxOf = (rings, pad) => {
  const [[s, w], [n, e]] = boundsOf(rings), [x0, y0] = px([w, n]), [x1, y1] = px([e, s]), m = Math.max(x1 - x0, y1 - y0) * pad
  return [x0 - m, y0 - m, x1 - x0 + 2 * m, y1 - y0 + 2 * m]
}
// Area-weighted center of a ring, where its name goes.
function centroid(pts) {
  let a = 0, x = 0, y = 0
  pts.forEach(([x1, y1], i) => { const [x2, y2] = pts[(i + 1) % pts.length], f = x1 * y2 - x2 * y1; a += f; x += (x1 + x2) * f; y += (y1 + y2) * f })
  return [x / (3 * a), y / (3 * a)]
}
const COLORS = ['var(--teal)', 'var(--sand)', 'var(--ghost)']   // DESIGN.md category order, without the campfire
const provinces = PROVINCES.map((p, i) => ({
  ...p, color: COLORS[i % COLORS.length], d: pathOf(p.rings), box: boxOf(p.rings, 0.08),
  label: centroid(p.rings[0].map(px)),
  districts: p.districts.map(d => ({ ...d, d: pathOf(d.rings), box: boxOf(d.rings, 0.35), at: px(d.center) })),
}))
const HOME = boxOf(DEPARTMENT.rings, 0.05)

const focus = computed(() => provinces.find(p => p.name === state.province) || null)
const zoomed = ref(null)   // district being entered: the camera dives into it before the map opens
const hover = ref(null)
const view = useTween(() => zoomed.value?.box || focus.value?.box || HOME, 700)

// Labels keep the same size on screen whatever the zoom, and hide where the shape is too small for the name.
const svg = ref(null), width = ref(600)
const measure = () => { if (svg.value) width.value = svg.value.clientWidth }
const unit = computed(() => view.value[2] / Math.max(1, Math.min(width.value, svg.value?.clientHeight * view.value[2] / view.value[3] || width.value)))
const fits = d => (d.box[2] / 1.7) / unit.value > d.name.length * 8.5
onMounted(() => { measure(); addEventListener('resize', measure); enter(state.province ? 'province' : 'where') })
onBeforeUnmount(() => removeEventListener('resize', measure))
watch(() => state.province, p => enter(p ? 'province' : 'where'))

function open(p, d) {
  if (zoomed.value) return
  zoomed.value = d
  setTimeout(() => enterDistrict(p, d), matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 620)
}

// Quick search: districts, provinces and our 650 towns answer at once from local data; streets, neighborhoods and
// other places come from OpenStreetMap (Nominatim), only inside Lambayeque, after a short pause in typing.
const query = ref(''), found = ref([]), searching = ref(false), searchError = ref(false)
const fold = s => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
const where = (lat, lon) => { const hit = locate(lat, lon); return hit ? `${hit.district.name}, ${hit.province.name}` : '' }
function localMatches(q) {
  const f = fold(q), score = name => fold(name).startsWith(f) ? 0 : fold(name).includes(f) ? 1 : -1
  const out = []
  for (const p of PROVINCES) if (score(p.name) >= 0) out.push({ kind: 'Province', title: p.name, detail: 'Lambayeque', province: p, s: score(p.name) })
  for (const p of PROVINCES) for (const d of p.districts) if (score(d.name) >= 0) out.push({ kind: 'District', title: d.name, detail: p.name, province: p, district: d, s: score(d.name) })
  for (const [name, lat, lon, rank] of PLACES) if (score(name) >= 0) out.push({ kind: rank === 2 ? 'Neighborhood' : 'Town', title: name, detail: where(lat, lon), lat, lon, s: score(name) + rank / 10 })
  return out.sort((a, b) => a.s - b.s).slice(0, 6)
}
const KIND = { highway: 'Street', place: 'Town', boundary: 'Area', landuse: 'Neighborhood', amenity: 'Place', building: 'Place', natural: 'Place', waterway: 'River' }
let pause, asked = 0
function onType() {
  clearTimeout(pause)
  searchError.value = false
  const q = query.value.trim()
  if (q.length < 2) { found.value = []; return }
  found.value = localMatches(q)
  if (q.length < 3) return
  pause = setTimeout(async () => {
    const id = ++asked
    searching.value = true
    try {
      const { west, north, east, south } = LAMBAYEQUE
      const remote = (await searchPlaces(q, [west, north, east, south].join(','), true))
        .filter(r => locate(r.lat, r.lon))
        .map(r => ({ kind: r.category === 'place' && /suburb|neighbourhood|quarter/.test(r.type) ? 'Neighborhood' : KIND[r.category] || 'Place', title: r.title, detail: where(r.lat, r.lon), lat: r.lat, lon: r.lon, bounds: r.bounds }))
      if (id !== asked) return
      const seen = new Set(found.value.map(r => fold(r.title)))
      found.value = [...found.value, ...remote.filter(r => !seen.has(fold(r.title)))].slice(0, 9)
    } catch { if (id === asked) searchError.value = true }
    finally { if (id === asked) searching.value = false }
  }, 550)   // Nominatim asks for few requests: wait until typing stops
}
function go(r) {
  if (!r) return
  query.value = ''
  found.value = []
  if (r.kind === 'Province') return (state.province = r.province.name)
  if (r.kind === 'District') return enterDistrict(r.province, r.district)
  const hit = locate(r.lat, r.lon)
  if (!hit) return
  state.flyTo = { lat: r.lat, lon: r.lon, bounds: r.kind === 'Street' || r.kind === 'Neighborhood' ? r.bounds : null }
  enterDistrict(hit.province, hit.district, { lat: r.lat, lon: r.lon })
}

const finding = ref(false)
function findMe() {
  if (!navigator.geolocation) return say('This browser can\'t share its location. You can tap the map instead.', 'sad', [], { level: 'force' })
  finding.value = true
  navigator.geolocation.getCurrentPosition(pos => {
    finding.value = false
    const lat = pos.coords.latitude, lon = pos.coords.longitude, hit = locate(lat, lon)
    if (!hit) return say('You seem to be outside Lambayeque right now. Tap your province on the map, or try free mode.', 'worried', [], { level: 'force' })
    say(() => t('Found you! You are in {district}, {province}.', { district: hit.district.name, province: hit.province.name }), 'happy', [], { level: 'note' })
    enterDistrict(hit.province, hit.district, { lat, lon })
  }, e => {
    finding.value = false
    say(e.code === 1 ? 'I don\'t have permission to see your location. You can allow it in the browser settings, or just tap the map.'
      : 'I couldn\'t find your location. Try again, ideally outdoors, or tap the map.', 'shy', [], { level: 'force' })
  }, { enableHighAccuracy: true, timeout: 15000 })
}
</script>

<template>
  <section class="absolute inset-0 z-10 flex flex-col items-center gap-3 px-3 pb-40 pt-16 lg:flex-row lg:justify-center lg:gap-8 lg:px-16">
    <div class="relative min-h-0 w-full flex-1 lg:h-full lg:max-w-[720px]">
      <svg ref="svg" class="region size-full" :viewBox="view.map(v => v.toFixed(1)).join(' ')" preserveAspectRatio="xMidYMid meet" role="group" :aria-label="t('Map of Lambayeque')">
        <g v-for="(p, pi) in provinces" :key="p.name" :style="{ opacity: focus && focus !== p ? 0.12 : 1, transition: 'opacity .5s', pointerEvents: focus && focus !== p ? 'none' : 'auto' }">
          <path v-for="(d, di) in p.districts" :key="d.name" class="unit" :d="d.d" :fill="p.color" :stroke="focus === p ? 'var(--sky-bg)' : p.color"
                :stroke-width="focus === p ? 1.2 : 0.4" :style="{ '--i': pi * 6 + di }"
                :fill-opacity="zoomed === d ? 0.85 : hover === (focus === p ? d.name : p.name) ? 0.62 : focus === p ? (di % 2 ? 0.3 : 0.22) : 0.3"
                :opacity="zoomed && zoomed !== d ? 0.15 : 1"
                role="button" tabindex="-1" :aria-label="focus === p ? d.name : p.name"
                @mouseenter="hover = focus === p ? d.name : p.name" @mouseleave="hover = null"
                @click="focus === p ? open(p, d) : (state.province = p.name)" />
          <path :d="p.d" fill="none" :stroke="p.color" :stroke-width="focus === p ? 2.5 : 1.5" style="pointer-events: none" />
        </g>
        <template v-if="!focus">
          <text v-for="p in provinces" :key="p.name" :x="p.label[0]" :y="p.label[1]" :font-size="15 * unit" font-weight="500">{{ p.name }}</text>
        </template>
        <template v-else-if="!zoomed">
          <template v-for="d in focus.districts" :key="d.name">
            <text v-if="fits(d) || hover === d.name" :x="d.at[0]" :y="d.at[1]" :font-size="11.5 * unit">{{ d.name }}</text>
          </template>
        </template>
      </svg>
    </div>

    <HudCard class="w-full shrink-0 lg:w-[340px]" :title="t(focus ? 'Which district?' : 'Where do you farm?')">
      <p class="text-muted">{{ t(focus ? 'Tap your district on the map or in this list.' : 'Tap your province on the map or in this list.') }}</p>
      <div class="grid max-h-[26dvh] grid-cols-2 gap-1 overflow-y-auto lg:max-h-[38dvh]">
        <template v-if="focus">
          <button v-for="d in focus.districts" :key="d.name" type="button" class="btn !justify-start !normal-case !tracking-normal" :aria-pressed="hover === d.name"
                  @mouseenter="hover = d.name" @mouseleave="hover = null" @focus="hover = d.name" @click="open(focus, d)">{{ d.name }}</button>
        </template>
        <template v-else>
          <button v-for="p in provinces" :key="p.name" type="button" class="btn col-span-2 !justify-start !normal-case !tracking-normal" :aria-pressed="hover === p.name"
                  @mouseenter="hover = p.name" @mouseleave="hover = null" @focus="hover = p.name" @click="state.province = p.name">
            <i class="inline-block size-3" :style="{ background: p.color }" />{{ p.name }} <span class="ml-auto text-muted">{{ t('{n} districts', { n: p.districts.length }) }}</span>
          </button>
        </template>
      </div>
      <form class="relative flex flex-col gap-1 border-t border-line pt-2" role="search" @submit.prevent="go(found[0])">
        <label for="place-search" class="label">{{ t('Find a place') }}</label>
        <div class="flex items-center border border-line bg-bg/70 focus-within:border-teal">
          <svg class="ml-2 size-4 shrink-0 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
          <input id="place-search" v-model="query" type="search" autocomplete="off" enterkeyhint="go" class="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-muted"
                 :placeholder="t('Town, neighborhood, street…')" @input="onType" @keydown.esc="query = ''; found = []">
          <span v-if="searching" class="mr-2 block size-2 animate-ping bg-teal" aria-hidden="true" />
        </div>
        <ul v-if="found.length" class="max-h-[30dvh] overflow-y-auto border border-line bg-panel" role="listbox" :aria-label="t('Search results')">
          <li v-for="(r, i) in found" :key="r.kind + r.title + i">
            <button type="button" role="option" class="flex w-full items-baseline gap-2 px-2 py-1.5 text-left hover:bg-teal/10 focus:bg-teal/10" @click="go(r)">
              <span class="w-[5.5rem] shrink-0 font-mono text-[10px] uppercase tracking-wider text-teal">{{ t(r.kind) }}</span>
              <span class="min-w-0"><b class="block truncate text-sm">{{ r.title }}</b><span v-if="r.detail" class="block truncate text-xs text-muted">{{ r.detail }}</span></span>
            </button>
          </li>
        </ul>
        <p v-else-if="query.trim().length >= 3 && !searching" class="text-xs text-muted">{{ t(searchError ? 'Search is not available right now. Check the connection and try again.' : 'No place found in Lambayeque.') }}</p>
      </form>
      <div class="flex flex-wrap gap-2 border-t border-line pt-2">
        <button v-if="focus" type="button" class="btn" @click="state.province = null">‹ Lambayeque</button>
        <button type="button" class="btn btn-fire" :disabled="finding" @click="findMe">{{ t(finding ? 'Searching…' : 'Use my location') }}</button>
        <button type="button" class="btn" :title="t('Open the whole department and tap anywhere')" @click="enterFree()">{{ t('Free mode') }}</button>
      </div>
      <p class="font-mono text-[10px] text-muted">{{ ADMIN_SOURCE }}</p>
    </HudCard>
  </section>
</template>
