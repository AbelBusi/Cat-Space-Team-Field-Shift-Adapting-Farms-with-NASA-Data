<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { state, mapUi } from '../store.js'
import { say } from '../guide.js'
import { t } from '../i18n.js'
import { PAL } from '../lib/palette.js'
import { formatArea } from '../lib/geo.js'
import { loadTerrain } from '../lib/terrain3d.js'

// The outlined field in 3D, like a diorama floating in the night: its square of land with the real relief and the
// satellite photo, the field marked three ways (darker surroundings, an orange edge on the ground, a glowing fence)
// and a beacon with its name. The camera starts straight above, like the 2D map, then tilts down while the land rises,
// so it is clear it is the same place. Drag to turn, wheel or pinch to zoom. three.js loads only when this opens.
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
const host = ref(null), pin = ref(null), needle = ref(null)
const phase = ref('loading')   // loading | ready | error
const info = ref(null)
const spinning = ref(!reduce)
const top = ref(150)

let THREE, renderer, scene, camera, controls, raf = 0, observer, data
let terrain, skirt, fence, rim, beacon, intro = 0
const UNITS = 1000            // the square of land is 1000 units wide, whatever its size in meters
const FENCE = 14              // fence height in units

// Heights in scene units, raised by `rise` (0 → flat like the map, 1 → full relief).
const lift = (h, rise) => (h - data.min) * data.exaggeration * (UNITS / data.size) * rise
const xz = (u, v) => [(u - 0.5) * UNITS, (v - 0.5) * UNITS]

function placeHud() {
  const hud = document.querySelector('[data-hud-top]')
  top.value = (hud?.getBoundingClientRect().bottom ?? 140) + 10
}

function buildTerrain() {
  const { N, heights } = data
  const pos = new Float32Array(N * N * 3), uv = new Float32Array(N * N * 2), index = []
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
    const k = i * N + j, [x, z] = xz(j / (N - 1), i / (N - 1))
    pos.set([x, 0, z], k * 3)
    uv.set([j / (N - 1), 1 - i / (N - 1)], k * 2)
  }
  for (let i = 0; i < N - 1; i++) for (let j = 0; j < N - 1; j++) { const a = i * N + j; index.push(a, a + N, a + 1, a + 1, a + N, a + N + 1) }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  geo.setIndex(index)
  const tex = new THREE.CanvasTexture(data.photo)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()
  terrain = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: tex }))
  scene.add(terrain)

  // The sides of the diorama: earth-colored walls from the edge of the land down to a flat base.
  const edge = []
  for (let j = 0; j < N; j++) edge.push(j)
  for (let i = 1; i < N; i++) edge.push(i * N + N - 1)
  for (let j = N - 2; j >= 0; j--) edge.push((N - 1) * N + j)
  for (let i = N - 2; i > 0; i--) edge.push(i * N)
  edge.push(0)
  const sp = new Float32Array(edge.length * 6), si = []
  edge.forEach((k, n) => { if (n) si.push(2 * n - 2, 2 * n - 1, 2 * n, 2 * n, 2 * n - 1, 2 * n + 1) })
  const sg = new THREE.BufferGeometry()
  sg.setAttribute('position', new THREE.BufferAttribute(sp, 3))
  sg.setIndex(si)
  sg.userData.edge = edge
  skirt = new THREE.Mesh(sg, new THREE.MeshLambertMaterial({ color: PAL.soil, side: THREE.DoubleSide }))
  scene.add(skirt)

  // The field: a see-through campfire fence along its edge, a line on top, and a beacon at its center.
  const ring = [...data.fieldUV, data.fieldUV[0]], pts = []
  for (let k = 0; k < ring.length - 1; k++) for (let s = 0; s < 10; s++) {
    const [u0, v0] = ring[k], [u1, v1] = ring[k + 1]
    pts.push([u0 + (u1 - u0) * s / 10, v0 + (v1 - v0) * s / 10])
  }
  pts.push(ring[0])
  const fp = new Float32Array(pts.length * 6), fi = []
  pts.forEach((_, n) => { if (n) fi.push(2 * n - 2, 2 * n - 1, 2 * n, 2 * n, 2 * n - 1, 2 * n + 1) })
  const fg = new THREE.BufferGeometry()
  fg.setAttribute('position', new THREE.BufferAttribute(fp, 3))
  fg.setIndex(fi)
  fg.userData.pts = pts
  fence = new THREE.Mesh(fg, new THREE.MeshBasicMaterial({ color: PAL.fire, transparent: true, opacity: 0.32, side: THREE.DoubleSide, depthWrite: false }))
  scene.add(fence)
  const rg = new THREE.BufferGeometry()
  rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts.length * 3), 3))
  rim = new THREE.Line(rg, new THREE.LineBasicMaterial({ color: PAL.fire }))
  scene.add(rim)
  const [cx, cz] = xz(...data.field.center)
  beacon = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1, 2.4), new THREE.MeshBasicMaterial({ color: PAL.fire }))
  beacon.position.set(cx, 0, cz)
  scene.add(beacon)
}

// Puts every height in place for a given rise (the land grows during the intro).
function setRise(rise) {
  const { N, heights } = data
  const p = terrain.geometry.attributes.position
  for (let k = 0; k < N * N; k++) p.setY(k, lift(heights[k], rise))
  p.needsUpdate = true
  terrain.geometry.computeVertexNormals()
  const base = -UNITS * 0.05, sp = skirt.geometry.attributes.position
  skirt.geometry.userData.edge.forEach((k, n) => {
    const x = p.getX(k), y = p.getY(k), z = p.getZ(k)
    sp.setXYZ(2 * n, x, y, z)
    sp.setXYZ(2 * n + 1, x, base, z)
  })
  sp.needsUpdate = true
  skirt.geometry.computeVertexNormals()
  const fp = fence.geometry.attributes.position, rp = rim.geometry.attributes.position
  fence.geometry.userData.pts.forEach(([u, v], n) => {
    const [x, z] = xz(u, v), y = lift(data.sampleUV(u, v), rise) + 0.6
    fp.setXYZ(2 * n, x, y, z)
    fp.setXYZ(2 * n + 1, x, y + FENCE * rise, z)
    rp.setXYZ(n, x, y + FENCE * rise, z)
  })
  fp.needsUpdate = rp.needsUpdate = true
  const [u, v] = data.field.center, ground = lift(data.sampleUV(u, v), rise)
  beacon.scale.y = Math.max(0.01, FENCE * 3.2 * rise)
  beacon.position.y = ground + beacon.scale.y / 2
}

// Camera on a sphere around the center: polar 0 = straight above (north up, like the map).
function aim(polar, azimuth, dist) {
  const t0 = controls.target
  camera.position.set(t0.x + dist * Math.sin(polar) * Math.sin(azimuth), t0.y + dist * Math.cos(polar), t0.z + dist * Math.sin(polar) * Math.cos(azimuth))
  camera.lookAt(t0)
}
const fitDistance = () => (UNITS / 2) / Math.tan(camera.fov * Math.PI / 360) * Math.max(0.92, 1.05 / camera.aspect)
const INTRO_MS = 1600
function start() {
  intro = performance.now()
  controls.enabled = false
  controls.autoRotate = false
}
function resetView() { start() }

function frame(now) {
  raf = requestAnimationFrame(frame)
  if (document.hidden) return
  const k = intro ? Math.min(1, (now - intro) / INTRO_MS) : 1
  if (intro) {
    const e = 1 - (1 - k) ** 3
    setRise(reduce ? 1 : e)
    aim(0.001 + (reduce ? 1 : e) * 0.92, (reduce ? 1 : e) * 0.5, fitDistance() * (1.05 - 0.12 * e))   // azimuth 0 = from the south, north up
    if (k >= 1) { intro = 0; controls.enabled = true; controls.autoRotate = spinning.value; controls.update() }
  } else controls.update()
  renderer.render(scene, camera)

  // The beacon's label and the compass follow the camera.
  const w = host.value.clientWidth, h = host.value.clientHeight
  const tip = beacon.position.clone().setY(beacon.position.y + beacon.scale.y / 2).project(camera)
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
    scene.add(new THREE.AmbientLight(PAL.ink, 1.1))
    const sun = new THREE.DirectionalLight(PAL.ink, 1.3)   // from the north-west, as on relief maps, so slopes read the right way
    sun.position.set(-600, 900, -600)
    scene.add(sun)
    controls = new orbit.OrbitControls(camera, renderer.domElement)
    Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, autoRotateSpeed: 0.6, minPolarAngle: 0.15, maxPolarAngle: 1.3, enablePan: false })
    controls.addEventListener('start', () => { spinning.value = false; controls.autoRotate = false })
    buildTerrain()
    const resize = () => {
      const w = host.value.clientWidth, h = host.value.clientHeight
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      controls.minDistance = fitDistance() * 0.3
      controls.maxDistance = fitDistance() * 1.6
    }
    observer = new ResizeObserver(resize)
    observer.observe(host.value)
    controls.target.set(0, lift(data.min + data.relief * 0.35, 1), 0)   // look a little above the lowest ground
    resize()
    setRise(0)
    phase.value = 'ready'
    start()
    raf = requestAnimationFrame(frame)
    say(() => t('Here is your field in 3D! The orange fence is its edge. I raised the relief ×{n} so small slopes show; the real heights are in the card.', { n: data.exaggeration }), 'surprised', [], { level: 'note' })
  } catch (e) {
    console.warn('3D view failed:', e)
    phase.value = 'error'
  }
}
function toggleSpin() {
  spinning.value = !spinning.value
  if (controls) controls.autoRotate = spinning.value
}

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
