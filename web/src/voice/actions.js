// What Sprout's voice can do in the web: the API answers with actions, and this runs them with the same functions the
// buttons use (so the map, the topic and the cards move as if the user had tapped them).
import { state, enterDistrict, enterFree, selectPoint } from '../store.js'
import { PROVINCES, locate } from '../lib/admin.js'
import { slidesOf } from '../content.js'

const fold = s => String(s ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()

function goToPlace(a) {
  if (a.kind === 'province') {
    const p = PROVINCES.find(x => fold(x.name) === fold(a.name))
    if (p) Object.assign(state, { stage: 'where', province: p.name })
    return
  }
  if (a.kind === 'district') {
    for (const p of PROVINCES) {
      const d = p.districts.find(x => fold(x.name) === fold(a.name))
      if (d) return enterDistrict(p, d)
    }
    return
  }
  if (Number.isFinite(a.lat) && Number.isFinite(a.lon)) {        // a town: its district, centred on it
    const hit = locate(a.lat, a.lon)
    return hit ? enterDistrict(hit.province, hit.district, { lat: a.lat, lon: a.lon }) : enterFree({ lat: a.lat, lon: a.lon })
  }
}

function openTopic(topic, track) {
  if (state.stage !== 'explore') enterFree()               // topics live on the map screen
  const list = slidesOf(track)
  const i = list.findIndex(s => s.id === topic)
  if (i >= 0) Object.assign(state, { track, slide: i })
}

const ANALYSIS_TOPIC = { 'water-retention': 'spots', districts: 'spots', vegetation: 'green', 'drought-risk': 'spots', anomalies: 'spots', hotspots: 'spots' }

export function runActions(actions = []) {
  // a place first, then the screen, so "take me to Olmos and show me 2030" ends on the right topic in the right place
  const order = { go_to_place: 0, select_cell: 1, compare_cells: 1, open_topic: 2, run_simulation: 2, show_analysis: 2, show_alerts: 2 }
  for (const a of [...actions].sort((x, y) => (order[x.type] ?? 3) - (order[y.type] ?? 3))) {
    try {
      if (a.type === 'go_to_place') goToPlace(a)
      else if (a.type === 'open_topic') openTopic(a.topic, a.track)
      else if (a.type === 'select_cell' && Number.isFinite(a.lat)) { if (state.stage !== 'explore') enterFree({ lat: a.lat, lon: a.lon }); else selectPoint(a.lat, a.lon) }
      else if (a.type === 'run_simulation') openTopic('whatif', 'ahead')
      else if (a.type === 'show_analysis') openTopic(ANALYSIS_TOPIC[a.kind] || 'spots', 'ahead')
      else if (a.type === 'show_alerts') openTopic('outlook', 'ahead')
    } catch (e) { console.warn('voice action failed', a, e) }
  }
}
