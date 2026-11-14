// The DESIGN.md palette for code that cannot read CSS variables (Leaflet, D3, canvas). Keep in sync with style.css.
export const PAL = {
  bg: '#0B1026', panel: '#121A3A', line: '#1E2A52', muted: '#8C9BC4', ink: '#F2E8D5', teal: '#4FC1B6', fire: '#F2A541',
  sand: '#D8C08E', soil: '#A88B5A', sage: '#9CC5A1', deep: '#2E6E86', ember: '#E0703A', ghost: '#A99BE8',
}
export const RAMP = {
  amount: [PAL.line, PAL.deep, PAL.teal, '#BFEDE6'],          // rain, soil moisture
  veg: [PAL.sand, PAL.sage, PAL.teal, PAL.deep],              // NDVI
  temp: [PAL.deep, PAL.sand, PAL.fire, PAL.ember],            // absolute temperature
  anomaly: [PAL.teal, '#2A3A66', PAL.fire, PAL.ember],        // cooler/wetter ← normal → hotter/drier
}
