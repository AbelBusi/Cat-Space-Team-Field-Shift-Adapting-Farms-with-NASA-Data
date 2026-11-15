<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { state, mapUi } from '../store.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'
import { PAL } from '../lib/palette.js'
import { formatArea } from '../lib/geo.js'
import { loadTerrain } from '../lib/terrain3d.js'

// The outlined field in 3D, cut out like a block of land floating in the night: its surface is the satellite photo
// over the real relief, and its sides show the soil. Only the field, nothing around it. The camera starts straight
// above with north up, like the 2D map, then tilts down while the land rises, so it reads as the same place.
// Drag to turn, wheel or pinch to zoom. three.js loads only when this opens.
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const host = ref(null), pin = ref(null), needle = ref(null)
const phase = ref('loading')   // loading | ready | error
const info = ref(null)
const spinning = ref(!reduce)
const top = ref(150)

let THREE, renderer, scene, camera, controls, raf = 0, observer, data
let surface, sides, rim, intro = 0
const UNITS = 1000            // the field's square is 1000 units wide, whatever its size in meters
const BASE = 70               // depth of the soil block below the lowest point, in units

// Heights in scene units, raised by `rise` (0 → flat like the map, 1 → full relief).
const lift = (h, rise) => (h - data.min) * data.exaggeration * (UNITS / data.size) * rise
const xz = (u, v) => [(u - 0.5) * UNITS, (v - 0.5) * UNITS]
const uvOf = (x, z) => [x / UNITS + 0.5, z / UNITS + 0.5]

function placeHud() {
  const hud = document.querySelector('[data-hud-top]')
  top.value = (hud?.getBoundingClientRect().bottom ?? 140) + 10
}

// The side of the block: soil layers drawn in the palette (dark topsoil, sandy layers, pebbles), repeated along the edge.
function soilTexture() {
  const cv = document.createElement('canvas')
  cv.width = 256
  cv.height = 128
  const ctx = cv.getContext('2d')
  const layers = [[0, 0.14, PAL.soil], [0.14, 0.45, '#8A6E44'], [0.45, 0.72, PAL.sand], [0.72, 1, '#6E5634']]
  for (const [a, b, c] of layers) { ctx.fillStyle = c; ctx.fillRect(0, a * 128, 256, (b - a) * 128) }
  let seed = 7
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  for (let k = 0; k < 900; k++) {
    ctx.fillStyle = rnd() < 0.5 ? 'rgba(11,16,38,.22)' : 'rgba(242,232,213,.16)'
    const s = 1 + Math.floor(rnd() * 3)
    ctx.fillRect(Math.floor(rnd() * 256), Math.floor(rnd() * 128), s, s)
  }
  const tex = new THREE.CanvasTexture(cv)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.wrapS = THREE.RepeatWrapping
  return tex
}

async function buildField() {
  const { TessellateModifier } = await import('three/examples/jsm/modifiers/TessellateModifier.js')
  // The surface: the field's outline, cut into small triangles so it can follow the relief.
  const outline = data.fieldUV.map(([u, v]) => xz(u, v))
  const shape = new THREE.Shape(outline.map(([x, z]) => new THREE.Vector2(x, z)))
  let geo = new THREE.ShapeGeometry(shape)
  geo = new TessellateModifier(UNITS / 70, 18).modify(geo)
  geo.deleteAttribute('normal')
  const pos = geo.attributes.position, uv = new Float32Array(pos.count * 2), ground = new Float32Array(pos.count)
  const p = data.photoUV
  for (let k = 0; k < pos.count; k++) {
    const x = pos.getX(k), z = pos.getY(k), [u, v] = uvOf(x, z)
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
  scene.add(surface)

  // The sides: from the surface edge straight down to a flat bottom, with the soil texture.
  const edge = [], ring = [...data.fieldUV, data.fieldUV[0]]
  for (let k = 0; k < ring.length - 1; k++) {
    const [u0, v0] = ring[k], [u1, v1] = ring[k + 1], steps = Math.max(2, Math.ceil(Math.hypot(u1 - u0, v1 - v0) * 70))
    for (let s = 0; s < steps; s++) edge.push([u0 + (u1 - u0) * s / steps, v0 + (v1 - v0) * s / steps])
  }
  edge.push(ring[0])
  const sp = new Float32Array(edge.length * 6), suv = new Float32Array(edge.length * 4), si = []
  let along = 0
  edge.forEach(([u, v], n) => {
    if (n) {
      along += Math.hypot(u - edge[n - 1][0], v - edge[n - 1][1]) * 4
      si.push(2 * n - 2, 2 * n - 1, 2 * n, 2 * n, 2 * n - 1, 2 * n + 1)
    }
    suv.set([along, 1, along, 0], n * 4)
  })
  const sg = new THREE.BufferGeometry()
  sg.setAttribute('position', new THREE.BufferAttribute(sp, 3))
  sg.setAttribute('uv', new THREE.BufferAttribute(suv, 2))
  sg.setIndex(si)
  sg.userData.edge = edge.map(([u, v]) => [u, v, data.sample(u, v)])
  sides = new THREE.Mesh(sg, new THREE.MeshLambertMaterial({ map: soilTexture(), side: THREE.DoubleSide }))
  scene.add(sides)

  // A thin campfire line on the top edge: the same outline the farmer drew on the 2D map.
  const rg = new THREE.BufferGeometry()
  rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(edge.length * 3), 3))
  rim = new THREE.Line(rg, new THREE.LineBasicMaterial({ color: PAL.fire }))
  scene.add(rim)
}

// Puts every height in place for a given rise (the block grows from the flat map during the intro).
function setRise(rise) {
  const pos = surface.geometry.attributes.position, ground = surface.geometry.userData.ground
  for (let k = 0; k < pos.count; k++) pos.setY(k, lift(ground[k], rise))
  pos.needsUpdate = true
  surface.geometry.computeVertexNormals()
  const bottom = -BASE * rise, sp = sides.geometry.attributes.position, rp = rim.geometry.attributes.position
  sides.geometry.userData.edge.forEach(([u, v, h], n) => {
    const [x, z] = xz(u, v), y = lift(h, rise)
    sp.setXYZ(2 * n, x, y, z)
    sp.setXYZ(2 * n + 1, x, bottom, z)
    rp.setXYZ(n, x, y + 0.8, z)
  })
  sp.needsUpdate = rp.needsUpdate = true
  sides.geometry.computeVertexNormals()
}

// Camera on a sphere around the center: polar 0 = straight above (north up, like the map).
function aim(polar, azimuth, dist) {
  const t0 = controls.target
  camera.position.set(t0.x + dist * Math.sin(polar) * Math.sin(azimuth), t0.y + dist * Math.cos(polar), t0.z + dist * Math.sin(polar) * Math.cos(azimuth))
  camera.lookAt(t0)
}
const fitDistance = () => (UNITS / 2) / Math.tan(camera.fov * Math.PI / 360) * Math.max(1.0, 1.1 / camera.aspect)
const INTRO_MS = 1600
function start() {
  intro = performance.now()
  controls.enabled = false
  controls.autoRotate = false
}

function frame(now) {
  raf = requestAnimationFrame(frame)
  if (document.hidden) return
  if (intro) {
    const k = Math.min(1, (now - intro) / INTRO_MS), e = reduce ? 1 : 1 - (1 - k) ** 3
    setRise(e)
    aim(0.001 + e * 0.95, e * 0.55, fitDistance() * (1.05 - 0.1 * e))   // azimuth 0 = seen from the south, north up
    if (k >= 1) { intro = 0; controls.enabled = true; controls.autoRotate = spinning.value; controls.update() }
  } else controls.update()
  renderer.render(scene, camera)

  // The label floats over the middle of the field, and the compass follows the camera.
  const w = host.value.clientWidth, h = host.value.clientHeight
  const tip = new THREE.Vector3(0, lift(data.min + data.relief, 1) + 45, 0).project(camera)
  if (pin.value) {
    pin.value.style.transform = `translate(${((tip.x + 1) / 2 * w).toFixed(1)}px, ${((1 - tip.y) / 2 * h).toFixed(1)}px) translate(-50%, -100%)`
    pin.value.style.opacity = tip.z < 1 ? 1 : 0
  }
  const c = controls.target.clone().project(camera), n = controls.target.clone().add(new THREE.Vector3(0, 0, -100)).project(camera)
  if (needle.value) needle.value.style.transform = `rotate(${Math.atan2((n.x - c.x) * w, (n.y - c.y) * h)}rad)`
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
    host.value.prepend(renderer.domElement)
    renderer.domElement.className = 'block size-full cursor-grab active:cursor-grabbing'
    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(35, 1, 1, 20000)
    scene.add(new THREE.AmbientLight(PAL.ink, 1.2))
    const sun = new THREE.DirectionalLight(PAL.ink, 1.4)   // from the north-west, as on relief maps, so slopes read the right way
    sun.position.set(-600, 900, -400)
    scene.add(sun)
    controls = new orbit.OrbitControls(camera, renderer.domElement)
    Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, autoRotateSpeed: 0.6, minPolarAngle: 0.15, maxPolarAngle: 1.35, enablePan: false })
    controls.addEventListener('start', () => { spinning.value = false; controls.autoRotate = false })
    await buildField()
    controls.target.set(0, lift(data.min + data.relief / 2, 1) - BASE / 2, 0)   // the middle of the block
    const resize = () => {
      const w = host.value.clientWidth, h = host.value.clientHeight
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      controls.minDistance = fitDistance() * 0.35
      controls.maxDistance = fitDistance() * 1.8
    }
    observer = new ResizeObserver(resize)
    observer.observe(host.value)
    resize()
    setRise(0)
    phase.value = 'ready'
    start()
    raf = requestAnimationFrame(frame)
    say(() => t('Here is your field in 3D, cut out like a block of land. I raised the relief ×{n} so small slopes show; the real heights are in the card.', { n: data.exaggeration }), 'surprised', [], { level: 'note' })
  } catch (e) {
    console.warn('3D view failed:', e)
    phase.value = 'error'
  }
}
function toggleSpin() {
  spinning.value = !spinning.value
  if (controls) controls.autoRotate = spinning.value
}
const resetView = () => controls && start()

onMounted(() => { placeHud(); addEventListener('resize', placeHud); build() })
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  removeEventListener('resize', placeHud)
  observer?.disconnect()
  controls?.dispose()
  scene?.traverse(o => { o.geometry?.dispose(); o.material?.map?.dispose(); o.material?.dispose() })
  renderer?.dispose()
})
</script>

<template>
  <!-- The 2D map stays behind, dimmed, so the place keeps its context. -->
  <div class="pointer-events-none absolute inset-0 z-[5] bg-bg/60" aria-hidden="true" />
  <section class="hud absolute inset-x-2 bottom-24 z-[12] flex flex-col bg-bg/85 sm:inset-x-6 lg:inset-x-14"
           :style="{ top: top + 'px' }" :aria-label="t('3D view of your field')">
    <header class="flex items-center gap-2 border-b border-line px-3 py-1.5">
      <h3 class="label min-w-0 flex-1 truncate">{{ t('3D view · your field') }}</h3>
      <button type="button" class="btn !min-h-7 !px-2" :aria-pressed="spinning" :disabled="phase !== 'ready'" @click="toggleSpin">⟳ {{ t('Turn') }}</button>
      <button type="button" class="btn !min-h-7 !px-2" :disabled="phase !== 'ready'" @click="resetView">{{ t('Reset view') }}</button>
      <button type="button" class="btn !min-h-7 !px-2" :aria-label="t('Back to 2D')" @click="mapUi.view3d = false">2D ✕</button>
    </header>

    <div ref="host" class="relative min-h-0 flex-1 overflow-hidden" role="img"
         :aria-label="info ? t('3D view of your field. Height {min} to {max} m, mean slope {deg}°.', { min: info.min, max: info.max, deg: info.slope }) : t('3D view of your field')">
      <div v-if="phase === 'ready'" ref="pin" class="pointer-events-none absolute left-0 top-0 whitespace-nowrap border border-fire bg-bg/90 px-2 py-0.5 font-mono text-xs text-ink transition-opacity">
        {{ t('Your field') }} · {{ formatArea(state.parcel.areaM2) }}
      </div>
      <div v-if="phase === 'ready'" class="pointer-events-none absolute right-3 top-3 flex size-11 items-center justify-center border border-line bg-bg/80" :title="t('North')">
        <span ref="needle" class="flex flex-col items-center font-mono text-[10px] leading-none text-fire"><b>N</b><i class="block h-4 w-0.5 bg-fire" /></span>
      </div>
      <div v-if="phase === 'loading'" class="absolute inset-0 flex flex-col items-center justify-center gap-2 font-mono text-xs uppercase tracking-wider text-muted">
        <span class="block size-3 animate-ping bg-teal" aria-hidden="true" />{{ t('Building the 3D view…') }}
      </div>
      <div v-else-if="phase === 'error'" class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4 text-center">
        <p>{{ t('I couldn\'t build the 3D view. Check the connection and try again.') }}</p>
        <button type="button" class="btn" @click="build">{{ t('Try again') }}</button>
      </div>
    </div>

    <footer v-if="info" class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-3 py-1.5 font-mono text-xs text-muted">
      <span v-if="state.mode === 'pro'" class="text-ink">{{ t('Height {min}–{max} m', { min: info.min, max: info.max }) }} · {{ t('mean slope {deg}°', { deg: info.slope }) }}</span>
      <span v-else class="text-ink">{{ t(info.slope < 2 ? 'Flat ground' : info.slope < 6 ? 'Gentle slope' : 'Steep ground') }}</span>
      <span>{{ t('Relief ×{n}', { n: info.ex }) }}</span>
      <span class="max-sm:hidden">{{ t('Drag to turn · wheel or pinch to zoom') }}</span>
      <span class="ml-auto">{{ t('Elevation: NASA SRTM 30 m (Terrain Tiles)') }}</span>
    </footer>
  </section>
</template>
