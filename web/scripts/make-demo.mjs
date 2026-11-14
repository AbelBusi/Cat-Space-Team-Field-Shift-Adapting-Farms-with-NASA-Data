// Saves a snapshot of the live NASA data for a few example places into public/demo/, using the app's own code.
// The "Demo data" button loads these files instantly (no waiting for MODIS, works offline at the event).
//   node scripts/make-demo.mjs
import { writeFileSync } from 'node:fs'
import { fetchPower, fetchNdvi, fetchRecentClimate } from '../src/lib/nasa.js'
import { PLACES } from '../src/demoPlaces.js'

for (const p of PLACES) {
  const t0 = Date.now()
  const [power, ndvi, recent] = await Promise.all([fetchPower(p.lat, p.lon), fetchNdvi(p.lat, p.lon), fetchRecentClimate(p.lat, p.lon)])
  writeFileSync(new URL(`../public/demo/${p.id}.json`, import.meta.url), JSON.stringify({ saved: new Date().toISOString().slice(0, 10), place: p, power, ndvi, recent }))
  console.log(`ok ${p.id} in ${Math.round((Date.now() - t0) / 1000)} s`)
}
