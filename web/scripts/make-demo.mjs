// Saves a snapshot of the live NASA data for a few example places into public/demo/, using the app's own code.
// The "Demo data" button loads these files instantly (no waiting for MODIS, works offline at the event).
//   node scripts/make-demo.mjs
import { writeFileSync, readFileSync, existsSync } from 'node:fs'
import { fetchPower, fetchNdvi, fetchRecentClimate, NINO_COASTAL } from '../src/lib/nasa.js'
import { PLACES } from '../src/demoPlaces.js'

for (const p of PLACES) {
  const t0 = Date.now()
  const file = new URL(`../public/demo/${p.id}.json`, import.meta.url)
  const old = existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : {}
  // ORNL's MODIS service is often down (503/504): keep the NDVI already saved instead of failing.
  const ndviOrOld = fetchNdvi(p.lat, p.lon).catch(e => { console.warn(`  ${p.id}: NDVI kept from the old snapshot (${e.message})`); return old.ndvi ?? null })
  const [power, ndvi, recent] = await Promise.all([fetchPower(p.lat, p.lon, p.lat > -7.2 && p.lat < -5.4 && p.lon > -80.7 && p.lon < -78.8 ? NINO_COASTAL : undefined), ndviOrOld, fetchRecentClimate(p.lat, p.lon)])
  writeFileSync(file, JSON.stringify({ saved: new Date().toISOString().slice(0, 10), place: p, power, ndvi, recent }))
  console.log(`ok ${p.id} in ${Math.round((Date.now() - t0) / 1000)} s`)
}
