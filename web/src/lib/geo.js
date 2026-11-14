import { lang } from '../i18n.js'
// Geometry helpers for the parcel tool and the search box (ported from the team's React map, geo.ts).
const EARTH_RADIUS_M = 6_371_008.8
const toRad = deg => deg * Math.PI / 180

// "-6.77, -79.84" or "-6.77 -79.84" (latitude first, like Google Maps).
const COORD_PATTERN = /^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$/

// Returns [lat, lon] or null. If the first number cannot be a latitude, it assumes "lon, lat".
export function parseCoordinates(input) {
  const m = COORD_PATTERN.exec(input)
  if (!m) return null
  let lat = Number(m[1]), lon = Number(m[2])
  if (Math.abs(lat) > 90 && Math.abs(lon) <= 90) [lat, lon] = [lon, lat]
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null
  return [lat, lon]
}

// Area of a polygon on the sphere, in m². ring = [[lat, lon], ...]
export function polygonAreaM2(ring) {
  if (ring.length < 3) return 0
  let sum = 0
  for (let i = 0; i < ring.length; i++) {
    const [lat1, lon1] = ring[i], [lat2, lon2] = ring[(i + 1) % ring.length]
    sum += toRad(lon2 - lon1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)))
  }
  return Math.abs(sum * EARTH_RADIUS_M ** 2 / 2)
}

function distanceM([lat1, lon1], [lat2, lon2]) {
  const a = Math.sin(toRad(lat2 - lat1) / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(toRad(lon2 - lon1) / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a))
}

export const ringPerimeterM = ring => ring.reduce((t, p, i) => t + distanceM(p, ring[(i + 1) % ring.length]), 0)

// Average of the corners: good enough as the parcel's reference point.
export const vertexCenter = ring => [ring.reduce((s, p) => s + p[0], 0) / ring.length, ring.reduce((s, p) => s + p[1], 0) / ring.length]

export function formatArea(m2) {
  const ha = m2 / 10_000
  if (ha < 0.1) return `${Math.round(m2).toLocaleString('en-US')} m²`
  return `${ha.toLocaleString('en-US', { maximumFractionDigits: ha < 10 ? 2 : 1 })} ha`
}

export const formatLength = m => m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toLocaleString('en-US', { maximumFractionDigits: 2 })} km`

// "2026-10-24" -> "Oct 24"
export const formatShortDate = iso => new Date(`${iso}T00:00:00Z`).toLocaleDateString(lang.value === 'en' ? 'en-US' : 'es-PE', { day: 'numeric', month: 'short', timeZone: 'UTC' })
