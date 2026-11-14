// Lambayeque's department, provinces and districts (built by pipeline/build_districts.py from OpenStreetMap).
// Rings are [lon, lat] pairs.
import ADMIN from '../data/lambayeque_admin.json'

export const DEPARTMENT = ADMIN.department
export const PROVINCES = ADMIN.provinces
export const ADMIN_SOURCE = ADMIN.source

function inRing(lon, lat, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j]
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) inside = !inside
  }
  return inside
}
export const inRings = (lat, lon, rings) => rings.some(r => inRing(lon, lat, r))

// Which province and district a point falls in, or null outside Lambayeque.
export function locate(lat, lon) {
  for (const province of PROVINCES) for (const district of province.districts) if (inRings(lat, lon, district.rings)) return { province, district }
  return null
}

// [[south, west], [north, east]] of a set of rings.
export function boundsOf(rings) {
  const pts = rings.flat(), lons = pts.map(p => p[0]), lats = pts.map(p => p[1])
  return [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]]
}
