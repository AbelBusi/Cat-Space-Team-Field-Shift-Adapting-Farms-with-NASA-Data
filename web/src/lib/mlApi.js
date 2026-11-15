// The Field Shift ML API (ml-api/, FastAPI): the only place that knows its URL. The tested XGBoost models run there;
// the web never computes or stores predictions itself. URL from VITE_ML_API_URL (.env.development, .env.example).
export const ML_API = (import.meta.env.VITE_ML_API_URL || '').replace(/\/$/, '')

async function call(path, { method = 'GET', body, signal } = {}) {
  if (!ML_API) throw new Error('VITE_ML_API_URL is not set')
  let r
  try {
    r = await fetch(`${ML_API}${path}`, { method, signal, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body && JSON.stringify(body) })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('the model service is not reachable')
  }
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    const d = data?.detail
    throw new Error(Array.isArray(d) ? d.map(x => x.message || x).join('; ') : d || `HTTP ${r.status}`)
  }
  return data
}

/** @returns {Promise<object>} every Lambayeque cell: 12 months of soil water, 4 quarters of NDVI, per scenario */
export const getProjections = signal => call('/projections', { signal })
export const getHealth = signal => call('/health', { signal })

/**
 * A what-if for one cell, compared with a normal year.
 * @param {{ location: { lat: number, lon: number } | { cell_id: string }, start?: string, horizon?: number,
 *   scenario?: { rain_factor?: number, t2m_delta?: number, rh_delta?: number, months?: number[], dry_months?: number[], analog?: 'all' | 'el_nino' | number[] } }} body
 */
export const simulateClimate = (body, signal) => call('/simulations/climate', { method: 'POST', body, signal })
