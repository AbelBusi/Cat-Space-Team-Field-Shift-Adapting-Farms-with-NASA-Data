// Development aid only (removed from the production build): browsers that are not painting, such as a hidden test
// pane or some headless runs, never call requestAnimationFrame, which freezes Vue transitions and Leaflet tiles.
// Opening the dev server with ?timerFrames swaps it for a timer so the app can still be driven and checked.
if (import.meta.env.DEV && location.search.includes('timerFrames')) {
  window.requestAnimationFrame = cb => setTimeout(() => cb(performance.now()), 16)
  window.cancelAnimationFrame = id => clearTimeout(id)
}
