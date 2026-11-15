<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { state, mapApi, mapUi } from '../store.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'
import { PAL } from '../lib/palette.js'
import { loadTerrain } from '../lib/terrain3d.js'
import { distanceM, formatArea, formatLength } from '../lib/geo.js'
import FieldTimeline from './FieldTimeline.vue'

// The outlined field rises out of the map as a floating block of land, in the free space between the cards.
// On the map the field stays lit and everything around it gets darker; a soft beam of light joins the field to the
// block above it, like a projection, but the block itself is full quality: the satellite photo over the real relief,
// soil layers on the sides, the orange outline on top. Two measurements are drawn in 3D and turn with it: a height
// line on the uphill side and the slope angle on the downhill side. Drag to turn, wheel or pinch to zoom.
// three.js loads only when this opens.
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const host = ref(null), heightTag = ref(null), slopeTag = ref(null), areaTag = ref(null), needle = ref(null)
// The field's sides with their real length: how its area is measured. Only for outlines with few corners.
const sideTags = ref([])
const sides3d = computed(() => {
  const r = state.parcel?.ring || []
  return r.length > 10 ? [] : r.map((p, k) => ({ k, len: formatLength(distanceM(p, r[(k + 1) % r.length])) }))
})
const phase = ref('loading')   // loading | ready | error
const info = ref(null)
const box = ref({ left: 0, top: 0, right: 0, bottom: 0 })
const beam = ref(null)

let THREE, renderer, scene, camera, controls, raf = 0, observer, data
let piece, surface, sides, rim, notes, intro = 0, bottomRing = [], turn = null
// 4D: the months as strata of time under the block (walls) and the ones to come above it (rings); a glass cube = now
let baseTargetY = 0
let series = null, cursor = 0, cursorSmooth = 0, strata = null, rings = null, glass = null, clipLow = null, clipHigh = null, topY = 0
const T4 = 3.4, GAP4 = 12                 // thickness of one month and the gap between the block and the stacks, in units
const marks = ref([]), markTags = ref([])
let soilCanvas = null, soilTex = null, fills = []   // per layer: 0-1 water, null = no value (hatched), missing = plain earth
const UNITS = 1000            // the field's square is 1000 units wide, whatever its size in meters
const BASE = 70               // depth of the soil block below the surface, in units
const INTRO_MS = 1600

const lift = (h, rise = 1) => (h - data.min) * data.exaggeration * (UNITS / data.size) * rise
const xz = (u, v) => [(u - 0.5) * UNITS, (v - 0.5) * UNITS]

// The time bar under the block (FieldTimeline) takes the bottom of the free space; it reports its real height.
const tlHeight = ref(innerWidth < 1024 ? 190 : 300)
// Only in "What's ahead": there it leads from the past to the projection and moves the map's month with it. In "Today" the
// month and the kind of year are chosen in the topic's own card, so a second time control would only confuse.
const showLog = computed(() => state.track === 'ahead')
const view4d = computed(() => mapUi.view4d && showLog.value)
// The free space between the cards (wide screens) or above the bottom sheet (phones). The block floats in its upper
// part; the field sits on the map in its lower part; the time bar sits under both.
function freeBox() {
  const b = freeSpace()
  return { ...b, bottom: b.bottom - (showLog.value ? tlHeight.value + 8 : 0), floor: b.bottom }
}
function freeSpace() {
  const hud = document.querySelector('[data-hud-top]')?.getBoundingClientRect().bottom ?? 140
  // Phones: the free band between the top strip of cards and the bottom one (SlideFrame)
  if (innerWidth < 1024) {
    const edge = (sel, side, fb) => document.querySelector(sel)?.getBoundingClientRect()[side] ?? fb
    const top = Math.max(hud, edge('.col-left', 'bottom', hud)) + 16, bottom = Math.min(innerHeight - 10, edge('.col-right', 'top', innerHeight * 0.7)) - 16
    // the block keeps ≥ 200 px; the log stays above Sprout's tab
    return { left: 8, right: innerWidth - 8, top, bottom: Math.min(innerHeight - 76, Math.max(bottom, top + 200 + (showLog.value ? tlHeight.value + 8 : 0))) }
  }
  const col = Math.min(380, Math.max(280, innerWidth * 0.27))
  return { left: 56 + col + 20, right: innerWidth - 56 - col - 20, top: hud + 8, bottom: innerHeight - 110 }
}
// Share of the free space for the floating block; the field sits on the map below it, after a small gap.
const blockShare = () => innerWidth < 1024 ? 0.56 : 0.62
const hostStyle = computed(() => {
  const b = box.value
  return { left: b.left + 'px', top: b.top + 'px', width: b.right - b.left + 'px', height: (b.bottom - b.top) * (view4d.value ? 1 : blockShare()) + 'px' }
})
const tlBox = computed(() => ({ left: box.value.left, right: box.value.right, bottom: innerHeight - (box.value.floor ?? innerHeight) }))
function onTlSize(h) { if (Math.abs(h - tlHeight.value) > 2) { tlHeight.value = h; placeBox() } }
function placeBox() {
  const b = freeBox()
  box.value = { ...b, split: b.top + (b.bottom - b.top) * blockShare() + (innerWidth < 1024 ? 28 : 0) }
  mapApi.frameField?.(box.value)
}

// The side of the block: the three ERA5-Land soil layers, top to bottom 0-7, 7-28 and 28-100 cm (the thin top ones a
// little thicker than to scale, so they can be seen), drawn as earth with pebbles. The time bar fills each layer with
// that month's water: the wetter the layer is for this place, the more water-blue it gets; hatched = no value.
const BANDS = [[0, 0.1, PAL.soil], [0.1, 0.3, '#8A6E44'], [0.3, 1, '#6E5634']]
function paintSoil() {
  const ctx = soilCanvas.getContext('2d'), w = soilCanvas.width, h = soilCanvas.height
  BANDS.forEach(([a, b, c], k) => {
    const y0 = a * h, bh = (b - a) * h
    ctx.fillStyle = c; ctx.fillRect(0, y0, w, bh)
    const f = fills[k]
    if (f === null) {
      ctx.strokeStyle = 'rgba(11,16,38,.35)'; ctx.lineWidth = 2
      ctx.save(); ctx.beginPath(); ctx.rect(0, y0, w, bh); ctx.clip()
      for (let x = -h; x < w; x += 10) { ctx.beginPath(); ctx.moveTo(x, y0 + bh); ctx.lineTo(x + bh, y0); ctx.stroke() }
      ctx.restore()
    } else if (f != null) {
      ctx.globalAlpha = 0.1 + 0.75 * f; ctx.fillStyle = PAL.deep; ctx.fillRect(0, y0, w, bh); ctx.globalAlpha = 1
    }
    if (k) { ctx.fillStyle = 'rgba(242,232,213,.35)'; ctx.fillRect(0, y0, w, 1) }
  })
  let seed = 7
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  for (let k = 0; k < 900; k++) {
    ctx.fillStyle = rnd() < 0.5 ? 'rgba(11,16,38,.22)' : 'rgba(242,232,213,.16)'
    const s = 1 + Math.floor(rnd() * 3)
    ctx.fillRect(Math.floor(rnd() * w), Math.floor(rnd() * h), s, s)
  }
  if (soilTex) soilTex.needsUpdate = true
}
function soilTexture() {
  soilCanvas = document.createElement('canvas')
  soilCanvas.width = 256
  soilCanvas.height = 128
  paintSoil()
  soilTex = new THREE.CanvasTexture(soilCanvas)
  soilTex.colorSpace = THREE.SRGBColorSpace
  soilTex.wrapS = THREE.RepeatWrapping
  return soilTex
}
function onLayers(f) {
  fills = f
  if (soilCanvas) paintSoil()
}

async function buildBlock() {
  const { TessellateModifier } = await import('three/examples/jsm/modifiers/TessellateModifier.js')
  piece = new THREE.Group()
  scene.add(piece)

  // Surface: the field's outline cut into small triangles, so it can follow the relief.
  const shape = new THREE.Shape(data.fieldUV.map(([u, v]) => new THREE.Vector2(...xz(u, v))))
  const geo = new TessellateModifier(UNITS / 70, 18).modify(new THREE.ShapeGeometry(shape))
  geo.deleteAttribute('normal')
  const pos = geo.attributes.position, uv = new Float32Array(pos.count * 2), ground = new Float32Array(pos.count), p = data.photoUV
  for (let k = 0; k < pos.count; k++) {
    const x = pos.getX(k), z = pos.getY(k), u = x / UNITS + 0.5, v = z / UNITS + 0.5
    pos.setXYZ(k, x, 0, z)
    ground[k] = data.sample(u, v)
    uv.set([p.u0 + u * p.su, 1 - (p.v0 + v * p.sv)], k * 2)
  }
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  geo.userData.ground = ground
  const photo = new THREE.CanvasTexture(data.photo)
  photo.colorSpace = THREE.SRGBColorSpace
  photo.anisotropy = renderer.capabilities.getMaxAnisotropy()
  surface = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: photo, side: THREE.DoubleSide }))
  piece.add(surface)

  // Sides: from the surface edge straight down to a flat bottom, with the soil texture.
  const edge = [], ring = [...data.fieldUV, data.fieldUV[0]]
  for (let k = 0; k < ring.length - 1; k++) {
    const [u0, v0] = ring[k], [u1, v1] = ring[k + 1], steps = Math.max(2, Math.ceil(Math.hypot(u1 - u0, v1 - v0) * 70))
    for (let s = 0; s < steps; s++) edge.push([u0 + (u1 - u0) * s / steps, v0 + (v1 - v0) * s / steps])
  }
  edge.push(ring[0])
  const sp = new Float32Array(edge.length * 6), suv = new Float32Array(edge.length * 4), si = []
  let along = 0
  edge.forEach(([u, v], n) => {
    if (n) { along += Math.hypot(u - edge[n - 1][0], v - edge[n - 1][1]) * 4; si.push(2 * n - 2, 2 * n - 1, 2 * n, 2 * n, 2 * n - 1, 2 * n + 1) }
    suv.set([along, 1, along, 0], n * 4)
  })
  const sg = new THREE.BufferGeometry()
  sg.setAttribute('position', new THREE.BufferAttribute(sp, 3))
  sg.setAttribute('uv', new THREE.BufferAttribute(suv, 2))
  sg.setIndex(si)
  sg.userData.edge = edge.map(([u, v]) => [u, v, data.sample(u, v)])
  sides = new THREE.Mesh(sg, new THREE.MeshLambertMaterial({ map: soilTexture(), side: THREE.DoubleSide }))
  piece.add(sides)

  // The orange outline on the top edge: the same line the farmer drew on the 2D map.
  const rg = new THREE.BufferGeometry()
  rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(edge.length * 3), 3))
  rim = new THREE.Line(rg, new THREE.LineBasicMaterial({ color: PAL.fire }))
  piece.add(rim)
}

// Puts every height in place for a given rise (the block grows out of the flat map during the intro).
function setRise(rise) {
  const pos = surface.geometry.attributes.position, ground = surface.geometry.userData.ground
  for (let k = 0; k < pos.count; k++) pos.setY(k, lift(ground[k], rise))
  pos.needsUpdate = true
  surface.geometry.computeVertexNormals()
  const sp = sides.geometry.attributes.position, rp = rim.geometry.attributes.position
  bottomRing = []
  sides.geometry.userData.edge.forEach(([u, v, h], n) => {
    const [x, z] = xz(u, v), y = lift(h, rise)
    sp.setXYZ(2 * n, x, y, z)
    sp.setXYZ(2 * n + 1, x, -BASE * rise, z)
    rp.setXYZ(n, x, y + 0.8, z)
    if (n % 4 === 0) bottomRing.push(new THREE.Vector3(x, -BASE * rise, z))
  })
  sp.needsUpdate = rp.needsUpdate = true
  sides.geometry.computeVertexNormals()
}

// The two measurements, drawn in teal so they read as notes, not as land.
function buildNotes() {
  notes = new THREE.Group()
  const ink = new THREE.LineBasicMaterial({ color: PAL.teal })
  const dash = new THREE.LineDashedMaterial({ color: PAL.teal, dashSize: 8, gapSize: 6 })
  const line = (pts, mat = ink) => { const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat); l.computeLineDistances(); notes.add(l) }
  const edge = sides.geometry.userData.edge, [du, dv] = data.field.downhill
  const [cu, cv] = data.fieldUV.reduce((a, [u, v]) => [a[0] + u / data.fieldUV.length, a[1] + v / data.fieldUV.length], [0, 0])
  const along = ([u, v]) => (u - cu) * du + (v - cv) * dv
  const dir = new THREE.Vector3(du, 0, dv)
  const side = new THREE.Vector3(-dv, 0, du)

  // Height: a dimension line on the uphill side, from the bottom of the block to its surface.
  const up = edge.reduce((a, b) => along(b) < along(a) ? b : a)
  const [ux, uz] = xz(up[0], up[1]), top = lift(up[2]), out = dir.clone().multiplyScalar(-46)
  const a = new THREE.Vector3(ux, -BASE, uz).add(out), b = new THREE.Vector3(ux, top, uz).add(out)
  line([a, b])
  for (const p of [a, b]) line([p.clone().addScaledVector(side, -12), p.clone().addScaledVector(side, 12)])
  notes.userData.height = a.clone().lerp(b, 0.5).add(dir.clone().multiplyScalar(-14))

  // Slope: on the downhill side, the level line (dashed) and the line of the land, with the angle between them.
  const low = edge.reduce((a, b) => along(b) > along(a) ? b : a)
  const [lx, lz] = xz(low[0], low[1]), o = new THREE.Vector3(lx, lift(low[2]) + 1, lz)
  const seen = Math.atan(Math.tan(data.field.slope * Math.PI / 180) * data.exaggeration)   // as drawn, with the raised relief
  const len = 150, down = new THREE.Vector3(0, -1, 0)
  line([o, o.clone().addScaledVector(dir, len)], dash)
  line([o, o.clone().addScaledVector(dir, len * Math.cos(seen)).addScaledVector(down, len * Math.sin(seen))])
  const arc = []
  for (let k = 0; k <= 16; k++) { const th = seen * k / 16; arc.push(o.clone().addScaledVector(dir, 90 * Math.cos(th)).addScaledVector(down, 90 * Math.sin(th))) }
  line(arc)
  notes.userData.slope = o.clone().addScaledVector(dir, len + 18)
  const [ax, az] = xz(cu, cv)
  notes.userData.area = new THREE.Vector3(ax, lift(data.min + data.relief) + 30, az)
  const onTop = (u, v) => { const [x, z] = xz(u, v); return new THREE.Vector3(x, lift(data.sample(u, v)), z) }
  notes.userData.sides = data.fieldUV.map(([u0, v0], k) => {
    const [u1, v1] = data.fieldUV[(k + 1) % data.fieldUV.length], um = (u0 + u1) / 2, vm = (v0 + v1) / 2
    const outward = new THREE.Vector3(um - cu, 0, vm - cv).normalize().multiplyScalar(28)
    return { mid: onTop(um, vm).add(new THREE.Vector3(0, 4, 0)).add(outward), a: onTop(u0, v0), b: onTop(u1, v1) }
  })
  piece.add(notes)
}

// ---- 4D. One thin plate per month with the field's own outline. Past months are solid strata under the block (older
// = deeper, like layers of ground); months after the chosen one float above it as rings. Colour = how full the deep
// soil was for this place; wetter months are also wider, so El Niño years stick out. Two clipping planes at the block
// hide whatever is on the wrong side, so moving the cursor just slides both stacks through the glass cube.
function build4D() {
  for (const o of [strata, rings, glass]) if (o) { piece.remove(o); o.traverse(c => { c.geometry?.dispose(); c.material?.dispose() }) }
  strata = rings = glass = null
  marks.value = series?.marks ?? []
  if (!series || !sides || !piece) return
  const edge = sides.geometry.userData.edge, step = Math.max(1, Math.ceil(edge.length / 72))
  const ring = edge.filter((_, k) => k % step === 0).map(([u, v]) => xz(u, v))
  const E = ring.length, n = series.fill.length
  const cx = ring.reduce((a, p) => a + p[0], 0) / E, cz = ring.reduce((a, p) => a + p[1], 0) / E
  const wp = new Float32Array(n * E * 6), wc = new Float32Array(n * E * 6), wi = []
  const lp = new Float32Array(n * E * 6), lc = new Float32Array(n * E * 6)
  const dry = new THREE.Color(PAL.soil), wet = new THREE.Color(PAL.deep), bright = new THREE.Color(PAL.teal), none = new THREE.Color(PAL.line), ink = new THREE.Color(PAL.ink), sand = new THREE.Color(PAL.sand)
  const col = new THREE.Color(), lin = new THREE.Color()
  for (let i = 0; i < n; i++) {
    const f = series.fill[i], sc = 1 + 0.16 * (f ?? 0), y0 = i * T4, y1 = y0 + T4 * 0.82
    if (f == null) col.copy(none); else { col.copy(dry).lerp(wet, f); if (f > 0.8) col.lerp(bright, (f - 0.8) * 2.5) }
    if (series.kind[i] === 'trend') lin.copy(ink).multiplyScalar(0.6)
    else { lin.copy(sand).lerp(bright, f ?? 0); if (series.kind[i] === 'future') lin.multiplyScalar(0.55) }
    for (let k = 0; k < E; k++) {
      const x = cx + (ring[k][0] - cx) * sc, z = cz + (ring[k][1] - cz) * sc, o = (i * E + k) * 6
      wp.set([x, y1, z, x, y0, z], o); wc.set([col.r, col.g, col.b, col.r * 0.6, col.g * 0.6, col.b * 0.6], o)
      const a = (i * E + k) * 2, b = (i * E + (k + 1) % E) * 2
      wi.push(a, a + 1, b, b, a + 1, b + 1)
      const q = ring[(k + 1) % E], x2 = cx + (q[0] - cx) * sc, z2 = cz + (q[1] - cz) * sc
      lp.set([x, y0, z, x2, y0, z2], o); lc.set([lin.r, lin.g, lin.b, lin.r, lin.g, lin.b], o)
    }
  }
  clipLow = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0); clipHigh = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  const wg = new THREE.BufferGeometry()
  wg.setAttribute('position', new THREE.BufferAttribute(wp, 3)); wg.setAttribute('color', new THREE.BufferAttribute(wc, 3)); wg.setIndex(wi)
  wg.computeVertexNormals()
  strata = new THREE.Mesh(wg, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, clippingPlanes: [clipLow] }))   // flat colour: the water must read
  const lg = new THREE.BufferGeometry()
  lg.setAttribute('position', new THREE.BufferAttribute(lp, 3)); lg.setAttribute('color', new THREE.BufferAttribute(lc, 3))
  rings = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.85, clippingPlanes: [clipHigh] }))
  // the glass cube around the block: "now"
  topY = lift(data.min + data.relief)
  const h = topY + BASE + 16, box = new THREE.BoxGeometry(UNITS * 1.04, h, UNITS * 1.04)
  glass = new THREE.Group()
  glass.add(new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineBasicMaterial({ color: PAL.teal, transparent: true, opacity: 0.6 })))
  glass.add(new THREE.Mesh(box, new THREE.MeshBasicMaterial({ color: PAL.teal, transparent: true, opacity: 0.045, depthWrite: false, side: THREE.DoubleSide })))
  glass.position.y = (topY - BASE) / 2
  piece.add(strata, rings, glass)
  cursorSmooth = cursor
  show4D()
}
function show4D() {
  const on = view4d.value && !intro
  for (const o of [strata, rings, glass]) if (o) o.visible = on
}
function onSeries(d) { series = d; if (piece && sides) build4D() }
function onCursor(i) { cursor = i }
// Where the stacks sit for the (smoothed) chosen month: the last past plate touches the block's bottom gap, the first
// later ring starts above its top; the planes keep each stack on its own side.
function place4D() {
  if (!strata) {          // no time data (the "Today" track): the camera goes back to the block
    if (controls && !intro && Math.abs(controls.target.y - baseTargetY) > 0.5) { const dy = (baseTargetY - controls.target.y) * 0.2; controls.target.y += dy; camera.position.y += dy }
    return
  }
  cursorSmooth += (cursor - cursorSmooth) * 0.16
  // the camera looks at the middle of the whole column, so on screen the column stays and the glass cube travels along it
  if (controls && !intro) {
    const want = baseTargetY + (view4d.value ? (series.fill.length - 2 * cursorSmooth) * T4 / 2 : 0), dy = (want - controls.target.y) * (turn ? 1 : 0.2)
    controls.target.y += dy; camera.position.y += dy
  }
  strata.position.y = -BASE - GAP4 - ((cursorSmooth - 1) * T4 + T4 * 0.82)
  rings.position.y = topY + GAP4 - (cursorSmooth + 1) * T4
  const py = piece.position.y
  clipLow.constant = py - BASE - GAP4 + 0.5          // keeps y below the block
  clipHigh.constant = -(py + topY + GAP4 - 0.5)      // keeps y above the block
}

function aim(polar, azimuth, dist) {
  const t0 = controls.target
  camera.position.set(t0.x + dist * Math.sin(polar) * Math.sin(azimuth), t0.y + dist * Math.cos(polar), t0.z + dist * Math.sin(polar) * Math.cos(azimuth))
  camera.lookAt(t0)
}
// Phones are portrait: a looser width margin lets the block fill more of its space (the labels still fit).
// In 4D the whole column of time must fit: the block plus one plate per month under and over it.
const column4D = () => (series?.fill.length ?? 0) * T4 + BASE + topY + 2 * GAP4
const fitDistance = () => {
  const k = 1 / Math.tan(camera.fov * Math.PI / 360), wide = (UNITS * 0.46) * k * Math.max(1, (innerWidth < 1024 ? 1.2 : 1.5) / camera.aspect)
  return view4d.value && series ? Math.max(column4D() * 0.56 * k, wide * 1.25) : wide
}

const toScreen = (v, rect) => { const p = v.clone().project(camera); return { x: rect.left + (p.x + 1) / 2 * rect.width, y: rect.top + (1 - p.y) / 2 * rect.height, z: p.z } }
function place(el, v, rect, anchor) {
  if (!el) return
  const s = toScreen(v, rect)
  el.style.transform = `translate(${(s.x - rect.left).toFixed(1)}px, ${(s.y - rect.top).toFixed(1)}px) ${anchor}`
  el.style.opacity = s.z < 1 ? 1 : 0
}

function frame(now) {
  raf = requestAnimationFrame(frame)
  if (document.hidden) return
  if (intro) {
    const k = Math.min(1, (now - intro) / INTRO_MS), e = reduce ? 1 : 1 - (1 - k) ** 3
    setRise(e)
    aim(0.001 + e * 0.98, e * 0.55, fitDistance() * (1.1 - 0.1 * e))   // azimuth 0 = from the south: north up, like the map
    if (k >= 1) {
      intro = 0
      buildNotes()
      build4D()
      if (view4d.value) enter4D()
      controls.enabled = true
      controls.autoRotate = !reduce
      controls.update()
    }
  } else if (turn) {
    // The compass was tapped: swing round until north points up again (seen from the south).
    const k = Math.min(1, (now - turn.t0) / (turn.from4 ? 1100 : 700)), e = 1 - (1 - k) ** 3
    const f4 = turn.from4
    aim(f4 ? f4.polar + (turn.polar - f4.polar) * e : turn.polar, turn.from + (turn.to - turn.from) * e, f4 ? f4.dist + (turn.dist - f4.dist) * e : turn.dist)
    if (k >= 1) { turn = null; controls.update() }
  } else {
    controls.update()
    if (!reduce) piece.position.y = Math.sin(now / 1700) * 7   // it floats
  }
  place4D()
  renderer.render(scene, camera)

  const rect = host.value.getBoundingClientRect()
  // year marks beside the stacks: under the block for months already past the cursor, above it for the ones to come
  marks.value.forEach((m, k) => {
    const el = markTags.value[k]
    if (!el) return
    const d = m.i - cursorSmooth, on = strata?.visible && Math.abs(d) >= 1.5
    if (!on) { el.style.opacity = 0; return }
    const y = (d < 0 ? strata.position.y : rings.position.y) + m.i * T4 + piece.position.y
    const s = toScreen(new THREE.Vector3(-UNITS * 0.6, y, UNITS * 0.6), rect)
    el.style.transform = `translate(${(s.x - rect.left).toFixed(1)}px, ${(s.y - rect.top).toFixed(1)}px) translate(-100%, -50%)`
    el.style.opacity = s.z < 1 && s.y > rect.top + 4 && s.y < rect.bottom - 4 ? 1 : 0
  })
  if (notes) {
    place(heightTag.value, notes.userData.height.clone().add(piece.position), rect, 'translate(-100%, -50%)')
    place(slopeTag.value, notes.userData.slope.clone().add(piece.position), rect, 'translate(0, -50%)')
    place(areaTag.value, notes.userData.area.clone().add(piece.position), rect, 'translate(-50%, -100%)')
    // A side's length shows only when that side is long enough on screen to carry it.
    notes.userData.sides.forEach((s, k) => {
      const el = sideTags.value[k]
      if (!el) return
      const a = toScreen(s.a, rect), b = toScreen(s.b, rect)
      place(el, s.mid.clone().add(piece.position), rect, 'translate(-50%, -50%)')
      if (Math.hypot(a.x - b.x, a.y - b.y) < 90) el.style.opacity = 0
    })
  }
  const c = controls.target.clone().project(camera), n = controls.target.clone().add(new THREE.Vector3(0, 0, -100)).project(camera)
  if (needle.value) needle.value.style.transform = `rotate(${Math.atan2((n.x - c.x) * rect.width, (n.y - c.y) * rect.height)}rad)`

  // The beam: from the field's top edge on the map up to the bottom of the floating block.
  const field = view4d.value ? null : mapApi.fieldOnScreen?.()
  if (!field) beam.value = null
  if (field && bottomRing.length) {
    const pts = bottomRing.map(v => toScreen(v.clone().add(piece.position), rect))
    const l = Math.min(...pts.map(p => p.x)), r = Math.max(...pts.map(p => p.x)), y = Math.max(...pts.map(p => p.y))
    beam.value = field.top > y + 4 ? { pts: `${l},${y} ${r},${y} ${field.right},${field.top} ${field.left},${field.top}`, l, r, y, field } : null
  }
}

async function build() {
  phase.value = 'loading'
  try {
    const [three, orbit, terrainData] = await Promise.all([import('three'), import('three/examples/jsm/controls/OrbitControls.js'), loadTerrain(state.parcel.ring)])
    THREE = three
    data = terrainData
    info.value = { ...data.field, ex: data.exaggeration }
    await nextTick()
    if (!host.value) return
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    renderer.localClippingEnabled = true
    host.value.prepend(renderer.domElement)
    renderer.domElement.className = 'block size-full cursor-grab active:cursor-grabbing'
    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(35, 1, 1, 20000)
    scene.add(new THREE.AmbientLight(PAL.ink, 1.2))
    const sun = new THREE.DirectionalLight(PAL.ink, 1.4)   // from the north-west, as on relief maps, so slopes read the right way
    sun.position.set(-600, 900, -400)
    scene.add(sun)
    controls = new orbit.OrbitControls(camera, renderer.domElement)
    Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, autoRotateSpeed: 0.5, minPolarAngle: 0.15, maxPolarAngle: 1.35, enablePan: false })
    controls.addEventListener('start', () => { controls.autoRotate = false })
    await buildBlock()
    baseTargetY = lift(data.min + data.relief / 2) - BASE / 2
    controls.target.set(0, baseTargetY, 0)   // the middle of the block
    const resize = () => {
      const w = host.value.clientWidth, h = host.value.clientHeight
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      controls.minDistance = fitDistance() * (view4d.value ? 0.2 : 0.35)
      controls.maxDistance = fitDistance() * 1.8
    }
    observer = new ResizeObserver(resize)
    observer.observe(host.value)
    resize()
    setRise(0)
    phase.value = 'ready'
    intro = performance.now()
    controls.enabled = false
    raf = requestAnimationFrame(frame)
    say(() => t('Here is your field in 3D, cut out like a block of land. I raised the relief ×{n} so small slopes show; the real heights are in the card.', { n: data.exaggeration }), 'surprised', [], { level: 'note' })
  } catch (e) {
    console.warn('3D view failed:', e)
    phase.value = 'error'
  }
}

function northUp() {
  if (!controls || intro) return
  controls.autoRotate = false
  const o = camera.position.clone().sub(controls.target), dist = o.length()
  let from = Math.atan2(o.x, o.z)
  from -= Math.round(from / (2 * Math.PI)) * 2 * Math.PI   // the short way round
  turn = { t0: performance.now(), from, to: 0, polar: Math.acos(o.y / dist), dist }
}
// Entering 4D pulls the camera back and lower, so the strata under the block and the rings above it are in view.
function enter4D() {
  if (!controls || intro) return
  show4D()
  controls.autoRotate = !reduce
  const o = camera.position.clone().sub(controls.target)
  controls.minDistance = fitDistance() * (view4d.value ? 0.2 : 0.35)
  controls.maxDistance = fitDistance() * 1.8
  turn = { t0: performance.now(), from: Math.atan2(o.x, o.z), to: view4d.value ? 0.6 : 0.55, polar: view4d.value ? 1.2 : 0.98, dist: fitDistance(), from4: { polar: Math.acos(o.y / o.length()), dist: o.length() } }
}
watch(view4d, async () => { await nextTick(); placeBox(); const w = host.value?.clientWidth; if (w && renderer) { renderer.setSize(w, host.value.clientHeight, false); camera.aspect = w / host.value.clientHeight; camera.updateProjectionMatrix() } enter4D() })
const onResize = () => placeBox()
watch(showLog, on => { if (!on) { onLayers([]); onSeries(null) } placeBox() })
onMounted(() => { placeBox(); addEventListener('resize', onResize); build() })
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  removeEventListener('resize', onResize)
  observer?.disconnect()
  controls?.dispose()
  scene?.traverse(o => { o.geometry?.dispose(); o.material?.map?.dispose(); o.material?.dispose() })
  renderer?.dispose()
})
</script>

<template>
  <FieldTimeline v-if="showLog" :box="tlBox" :compact="view4d" @layers="onLayers" @size="onTlSize" @series="onSeries" @cursor="onCursor" />
  <svg class="pointer-events-none fixed inset-0 z-[11] size-full" aria-hidden="true">
    <template v-if="beam">
      <polygon :points="beam.pts" fill="var(--teal)" fill-opacity=".07" />
      <line :x1="beam.l" :y1="beam.y" :x2="beam.field.left" :y2="beam.field.top" stroke="var(--teal)" stroke-opacity=".35" />
      <line :x1="beam.r" :y1="beam.y" :x2="beam.field.right" :y2="beam.field.top" stroke="var(--teal)" stroke-opacity=".35" />
    </template>
  </svg>

  <div ref="host" class="absolute z-[12]" :style="hostStyle" role="img"
       :aria-label="info ? t('3D view of your field. Height {min} to {max} m, mean slope {deg}°.', { min: info.min, max: info.max, deg: info.slope }) : t('3D view of your field')">
    <template v-if="phase === 'ready' && info">
      <span v-show="!view4d" ref="heightTag" class="pointer-events-none absolute left-0 top-0 whitespace-nowrap border-l-2 border-teal bg-bg/80 px-1.5 py-0.5 text-right font-mono text-xs leading-tight text-ink">
        {{ state.mode === 'pro' ? t('Height {min}–{max} m', { min: info.min, max: info.max }) : t('About {m} m above the sea', { m: Math.round((info.min + info.max) / 2) }) }}
        <span v-if="info.ex > 1" class="block text-[10px] text-muted">{{ t('Relief ×{n}', { n: info.ex }) }}</span>
      </span>
      <span ref="areaTag" class="pointer-events-none absolute left-0 top-0 whitespace-nowrap border border-fire bg-bg/85 px-2 py-0.5 text-center font-mono text-xs leading-tight text-ink">
        {{ t('Area {a}', { a: formatArea(state.parcel.areaM2) }) }}
        <span v-if="state.mode === 'pro'" class="block text-[10px] text-muted">{{ t('perimeter {p}', { p: formatLength(state.parcel.perimeterM) }) }}</span>
      </span>
      <span v-for="s in sides3d" v-show="!view4d" :key="s.k" :ref="el => (sideTags[s.k] = el)" class="pointer-events-none absolute left-0 top-0 whitespace-nowrap bg-bg/70 px-1 font-mono text-[10px] text-sky-ink opacity-0">{{ s.len }}</span>
      <span v-show="!view4d" ref="slopeTag" class="pointer-events-none absolute left-0 top-0 whitespace-nowrap border-l-2 border-teal bg-bg/80 px-1.5 py-0.5 font-mono text-xs leading-tight text-ink">
        {{ state.mode === 'pro' ? t('Mean slope {deg}°', { deg: info.slope }) : t(info.slope < 2 ? 'Flat ground' : info.slope < 6 ? 'Gentle slope' : 'Steep ground') }}
      </span>
      <span v-for="(m, k) in marks" :key="m.i + m.text" :ref="el => (markTags[k] = el)"
            class="pointer-events-none absolute left-0 top-0 whitespace-nowrap border-r-2 bg-bg/75 px-1.5 py-0.5 font-mono text-[11px] leading-tight opacity-0"
            :class="m.nino ? 'border-fire text-ink' : m.next ? 'border-teal text-teal' : 'border-line text-muted'">{{ m.text }}</span>
      <button type="button" class="hud absolute right-1 top-1 size-[68px] bg-bg/85 p-1" :title="t('Compass · tap to put north up')" :aria-label="t('Compass · tap to put north up')" @click="northUp">
        <svg ref="needle" viewBox="-34 -34 68 68" class="size-full" aria-hidden="true">
          <circle r="26" fill="none" stroke="var(--muted)" stroke-opacity=".5" />
          <g stroke="var(--muted)"><line y1="-26" y2="-22" /><line y1="22" y2="26" /><line x1="-26" x2="-22" /><line x1="22" x2="26" /></g>
          <path d="M0 -20 L5 0 L0 3 L-5 0 Z" fill="var(--fire)" />
          <path d="M0 20 L5 0 L0 -3 L-5 0 Z" fill="var(--muted)" />
          <g font-family="IBM Plex Mono, monospace" font-size="9.5" text-anchor="middle" dominant-baseline="central">
            <text y="-30" fill="var(--fire)" font-weight="700">N</text><text y="30" fill="var(--muted)">S</text>
            <text x="30" fill="var(--muted)">E</text><text x="-30" fill="var(--muted)">{{ t('W') }}</text>
          </g>
        </svg>
      </button>
    </template>
    <div v-if="phase === 'loading'" class="absolute inset-0 flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-wider text-sky-muted">
      <span class="block size-2.5 animate-ping bg-teal" aria-hidden="true" />{{ t('Building the 3D view…') }}
    </div>
    <div v-else-if="phase === 'error'" class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
      <p class="bg-bg/80 px-2 py-1">{{ t('I couldn\'t build the 3D view. Check the connection and try again.') }}</p>
      <button type="button" class="btn" @click="build">{{ t('Try again') }}</button>
    </div>
  </div>
</template>
