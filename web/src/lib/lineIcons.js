// Field Shift's own line icons (24 × 24, drawn by hand as SVG paths; no icon library, so they do not look generic).
// Each icon is inner SVG markup. Strokes take the text colour unless a class names a palette colour (c-teal, c-fire…).
// Motion lives on <g> wrappers (i-sway, i-fall, i-spin…; keyframes in style.css): every icon draws itself on when it
// appears and then keeps one small movement of its own. Pixel art stays only in Sprout (web/src/cat/).
const RAW = {
  // ---- weather and water
  sun: `<g class="i-spin"><path class="c-fire" d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/></g><circle class="c-fire" cx="12" cy="12" r="4"/>`,
  drop: `<g class="i-bob"><path class="c-teal" d="M12 3.2c-2.6 3.4-5.5 7-5.5 10.6a5.5 5.5 0 0 0 11 0c0-3.6-2.9-7.2-5.5-10.6z"/><path class="c-teal" d="M9.2 14.2a2.9 2.9 0 0 0 2.2 2.6"/></g>`,
  rain: `<path d="M7 13.5a4 4 0 0 1 .6-7.9 5 5 0 0 1 9.4 1.2 3.4 3.4 0 0 1 .2 6.7z"/><g class="i-fall"><path class="c-teal" d="M8.5 16.5l-1 3"/></g><g class="i-fall" style="--d:.35s"><path class="c-teal" d="M12.5 16.5l-1 3"/></g><g class="i-fall" style="--d:.7s"><path class="c-teal" d="M16.5 16.5l-1 3"/></g>`,
  frost: `<g class="i-spin-slow"><path class="c-ghost" d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9"/><path class="c-ghost" d="M12 6l-2-2M12 6l2-2M12 18l-2 2M12 18l2 2"/></g>`,
  // ---- trend arrows (the colour prop says what it means for the crop)
  up: `<g class="i-nudge-up"><path d="M12 20V5M6 11l6-6 6 6"/></g>`,
  down: `<g class="i-nudge-down"><path d="M12 4v15M6 13l6 6 6-6"/></g>`,
  flat: `<g class="i-nudge-right"><path d="M4 12h15M13 6l6 6-6 6"/></g>`,
  // ---- the plant and the furrow
  plant_ok: `<path class="c-sand" d="M3 20.5h18"/><g class="i-sway"><path class="c-sage" d="M12 20.5V9"/><path class="c-sage" d="M12 13c-4.5 0-6-2.6-6-5.5 4 0 6 2 6 5.5z"/><path class="c-teal" d="M12 10.5c4.5 0 6.5-2.6 6.5-6C14.500 4.500 12 7 12 10.500z"/></g>`,
  plant_thirsty: `<path class="c-sand" d="M3 20.5h18"/><g class="i-droop"><path class="c-sand" d="M12 20.5v-7c0-2 .8-3.400 2.400-4.200"/><path class="c-sand" d="M12 15.500c-3.600.6-5.400-.6-6.300-3 3-.9 5.300 0 6.300 3z"/><path class="c-sand" d="M14.400 9.300c2.900.9 4.600 0 5.800-2.300-2.700-1.400-4.800-.6-5.800 2.300z"/></g><g class="i-pulse"><path class="c-teal" d="M18.500 14.500c-.8 1-1.200 1.700-1.200 2.300a1.200 1.200 0 0 0 2.400 0c0-.6-.4-1.300-1.200-2.300z"/></g>`,
  plant_dead: `<path class="c-ember" d="M3 20.5h18"/><path class="c-ember" d="M12 20.5v-6l-3.500-4M12 14.500l4-3.500M8.500 10.500l-2-.5M16 11l1-2.500"/><path class="c-ember" d="M7.500 20.500l1.200 2M15 20.500l-1 2"/>`,
  seed: `<path class="c-sand" d="M3 20h18"/><ellipse class="c-sand" cx="12" cy="17" rx="3.200" ry="2.300"/><g class="i-grow"><path class="c-sage" d="M12 14.700V9.500"/><path class="c-sage" d="M12 11c-2.600 0-3.600-1.500-3.600-3.300 2.400 0 3.600 1.200 3.600 3.300z"/><path class="c-teal" d="M12 9.500c2.400 0 3.400-1.400 3.400-3.200-2.300 0-3.400 1.200-3.400 3.200z"/></g>`,
  harvest: `<g class="i-sway"><path class="c-fire" d="M12 21V8"/><path class="c-fire" d="M12 8c.9-1.600.9-3.300 0-5-.9 1.700-.9 3.400 0 5zM12 11.500c-2.600-.2-3.600-1.800-3.600-3.600 2.200.2 3.600 1.400 3.600 3.600zM12 11.500c2.600-.2 3.600-1.800 3.600-3.600-2.200.2-3.600 1.400-3.600 3.600zM12 15.500c-2.600-.2-3.600-1.800-3.600-3.600 2.200.2 3.600 1.400 3.600 3.600zM12 15.500c2.600-.2 3.600-1.800 3.600-3.600-2.200.2-3.600 1.400-3.600 3.600z"/></g>`,
  bare: `<path class="c-sand" d="M3 15h18"/><path class="c-sand" d="M7 15l1.500 3-1 2.500M13 15l-1 2.500 1.500 3M18 15l.8 2.200"/><g class="i-pulse"><path class="c-muted" stroke-width="2" d="M5 11.500h.01M10 10h.01M16 11h.01M19.500 9.500h.01"/></g>`,
  soil_dry: `<path class="c-sand" d="M3.500 9.500h17V20h-17z"/><path class="c-ember" d="M8 9.500l1.500 3.500-1.500 3 1 4M14.500 9.500l-1 3 2 2.500-.8 5"/><g class="i-pulse"><path class="c-muted" stroke-width="2" d="M5.500 6h.01M12 5h.01M18.500 6h.01"/></g>`,
  soil_moist: `<path class="c-sand" d="M3.500 9.500h17V20h-17z"/><g class="i-pulse"><path class="c-teal" stroke-width="2.400" d="M8 13.500h.01M12 15.500h.01M16 13h.01M9.500 17.500h.01M15 17.500h.01"/></g><g class="i-sway"><path class="c-sage" d="M12 9.500V6M12 7.500c-1.600 0-2.300-.9-2.300-2M12 6.500c1.600 0 2.300-.9 2.300-2"/></g>`,
  soil_wet: `<path class="c-sand" d="M3.500 11h17v9h-17z"/><g class="i-wave"><path class="c-teal" d="M-8 8.500c1.700-1.600 3.300-1.600 5 0s3.300 1.600 5 0 3.300-1.600 5 0 3.300 1.600 5 0 3.300-1.600 5 0 3.300 1.600 5 0 3.300-1.600 5 0 3.300 1.600 5 0"/></g><path class="c-teal" stroke-width="2.400" d="M7 14.500h.01M12 16h.01M17 14.500h.01M9.500 18h.01M14.500 18h.01"/>`,
  // ---- crops of the example rotations
  rice: `<path class="c-teal" d="M3 20h18"/><g class="i-sway"><path class="c-sage" d="M12 20V8M12 20c-1-4-3-7-6-8.500M12 20c1-4 3-7 6-8.500"/><path class="c-sand" d="M12 8c-.8-1.200-.8-2.600 0-4 .8 1.400.8 2.800 0 4zM6 11.500c-1.300-.5-2-1.600-2-3 1.400.3 2.200 1.300 2 3zM18 11.500c1.300-.5 2-1.600 2-3-1.400.3-2.200 1.300-2 3z"/></g>`,
  maize: `<g class="i-sway"><path class="c-fire" d="M12 3.500c2.400 2 3.500 4.800 3.500 8s-1.100 5.500-3.500 7.500c-2.400-2-3.500-4.300-3.500-7.500s1.100-6 3.500-8z"/><path class="c-fire" d="M10 8h4M9.200 11.500h5.600M9.500 15h5"/><path class="c-sage" d="M8.500 13c-2.500 1-4 3.500-4 7 3.500 0 6-1 7.500-3M15.500 13c2.500 1 4 3.500 4 7-3.500 0-6-1-7.500-3"/></g>`,
  cowpea: `<g class="i-sway"><path class="c-sage" d="M4 9c3 8 11 11 16 6-2-1-3.500-2.500-4.500-4.500C13 6 7.500 5.500 4 9zM4 9L2.500 6.500"/><circle class="c-sand" cx="8.500" cy="10" r="1.300"/><circle class="c-sand" cx="12.300" cy="12.200" r="1.300"/><circle class="c-sand" cx="16" cy="14.600" r="1.200"/></g>`,
  sorghum: `<g class="i-sway"><path class="c-sage" d="M12 21V11M12 15c-3-.5-4.500-2-5-4M12 17c3-.5 4.500-2 5-4"/><path class="c-ember" d="M12 11c-2.200 0-3.500-1.800-3.500-4s1.300-4 3.500-4 3.500 1.800 3.500 4-1.300 4-3.500 4z"/><path class="c-ember" stroke-width="2" d="M10.500 6h.01M13.500 6h.01M12 8.200h.01M12 4.800h.01"/></g>`,
  green_manure: `<path class="c-sand" d="M3 20.500h18"/><g class="i-sway"><path class="c-sage" d="M12 20.500V13"/><circle class="c-teal" cx="12" cy="8" r="2.800"/><circle class="c-sage" cx="8" cy="12" r="2.800"/><circle class="c-sage" cx="16" cy="12" r="2.800"/></g>`,
  // ---- topics and controls
  satellite: `<path d="M10 8l6 6-2.500 2.500-6-6z"/><path class="c-teal" d="M3 6.500L6.500 3l3 3L6 9.500zM14.500 18l3.500-3.500 3 3-3.500 3.500z"/><g class="i-pulse"><path class="c-fire" d="M16 5.500a4.500 4.500 0 0 1 2.500 2.500M17.500 2.500a8 8 0 0 1 4 4"/></g>`,
  calendar: `<path d="M4.500 6h15v14h-15zM4.500 10h15M8.500 3.500v4M15.500 3.500v4"/><path class="c-teal" stroke-width="2.200" d="M8.500 13.500h.01M12 13.500h.01M15.500 13.500h.01M8.500 16.800h.01M12 16.800h.01"/><g class="i-blink"><path class="c-fire" stroke-width="2.600" d="M15.500 16.800h.01"/></g>`,
  heart: `<g class="i-beat"><path class="c-fire" d="M12 20S4 15 4 9.500A4.300 4.300 0 0 1 12 7.300 4.300 4.300 0 0 1 20 9.500C20 15 12 20 12 20z"/></g>`,
  compare: `<path d="M12 4.500V20M8 20h8"/><g class="i-tilt"><path d="M4.500 7.500h15"/><path class="c-teal" d="M4.500 7.500l-2.500 6a2.700 2.700 0 0 0 5 0z"/><path class="c-fire" d="M19.500 7.500l-2.500 6a2.700 2.700 0 0 0 5 0z"/></g>`,
  report: `<path d="M6 3.500h8.500l4 4V20.500H6zM14.500 3.500v4h4"/><g class="i-pulse"><path class="c-teal" d="M9 11.500h6.500M9 14.500h6.500M9 17.500h4"/></g>`,
  speaker: `<path d="M4 9.500h3.500L12 5.500v13l-4.500-4H4z"/><g class="i-pulse"><path class="c-teal" d="M15 9a4.500 4.500 0 0 1 0 6M17.500 6.500a8 8 0 0 1 0 11"/></g>`,
  speaker_off: `<path d="M4 9.500h3.500L12 5.500v13l-4.500-4H4z"/><path class="c-ember" d="M15.500 9.500l5 5M20.500 9.500l-5 5"/>`,
  close: `<path d="M6 6l12 12M18 6L6 18"/>`,
  mic: `<path d="M9 5.500a3 3 0 0 1 6 0v6a3 3 0 0 1-6 0z"/><path d="M5.500 11a6.500 6.500 0 0 0 13 0M12 17.500V21M8.500 21h7"/><g class="i-pulse"><path class="c-teal" d="M2.500 9v3M21.500 9v3"/></g>`,
  ai: `<g class="i-twinkle"><path class="c-teal" d="M11 4l1.600 4.900 4.900 1.600-4.900 1.600L11 17l-1.600-4.900-4.900-1.600 4.900-1.600z"/></g><g class="i-twinkle" style="--d:.8s"><path class="c-fire" d="M18 14.500l.8 2.200 2.200.8-2.200.8-.8 2.200-.8-2.200-2.200-.8 2.200-.8z"/></g>`,
  // ---- the mark of Field Shift: a sprout over two furrows (two frames for the animated logo)
  logo_a: `<path class="c-sand" d="M3 20.500h18M5.500 17.500h13"/><path class="c-teal" d="M12 17.500V10M12 12.500c-3.200 0-4.500-2-4.500-4.200 3 0 4.500 1.600 4.500 4.200zM12 10.500c3.200 0 4.500-2 4.500-4.200-3 0-4.500 1.600-4.500 4.200z"/>`,
  logo_b: `<path class="c-sand" d="M3 20.500h18M5.500 17.500h13"/><path class="c-teal" d="M12 17.500V9M12 11.500c-3.400-.6-4.800-2.800-4.500-5 3 .4 4.600 2.200 4.500 5zM12 9.500c3.400-.6 4.800-2.800 4.500-5-3 .4-4.600 2.200-4.500 5z"/>`,
}

// pathLength="1" on every shape lets one CSS rule draw any icon on, whatever its real length.
export const LINE_ICONS = Object.fromEntries(Object.entries(RAW).map(([k, v]) => [k, v.replace(/<(path|circle|ellipse|rect|line|polyline)\b/g, '<$1 pathLength="1"')]))
