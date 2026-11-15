# Instructions for AI coding agents (Claude, Gemini, Copilot, Cursor…)

Project: **Field Shift**, NASA Space Apps Challenge 2026. A web tool that turns NASA Earth data into plain language so
farmers anywhere can compare crop rotations. Team from Chiclayo, Peru. Read this file before writing any code.

## Rules that are not negotiable

1. **Design:** follow [`DESIGN.md`](DESIGN.md) exactly. Only its colors (as CSS variables), square corners, its fonts and
   the pixel icons. Do not invent colors, rounded cards, pills, gradients, shadows or giant headings.
2. **Language:** everything users see (UI text, Sprout's lines), commit messages and repo docs are in **English** (Space Apps rule).
   UI text is written in English and wrapped with `t()`; add its Spanish (and if possible Quechua) translation in
   `web/src/i18n.js` (see `docs/LANGUAGES.md`).
3. **Data honesty:** never invent numbers and present them as real. Hypothetical values must be labeled. State the pixel size
   of each dataset (a 55 km climate cell is not "your field"). Cite every source in `docs/DATA_SOURCES.md`.
4. **Keep it small:** reuse what exists (`web/src/lib/`, `content.js`, `store.js`), no new dependencies for a few lines of code,
   no backend unless a feature truly needs one.
4b. **Styling:** Tailwind classes in the templates for layout, spacing, type and responsive rules; `web/src/style.css` only for
   what Tailwind cannot do (tokens, pixel art, Leaflet overrides, keyframes, print). Tailwind only knows the DESIGN.md colors.
5. **Commits:** follow [`COMMITS.md`](COMMITS.md) (Conventional Commits 1.0.0, in English), e.g. `feat(map): add SMAP layer`.
6. **Current phase: Lambayeque first.** Make everything work well for Lambayeque, Peru (bbox W −80.7, S −7.2, E −78.8, N −5.4).
   All of Peru only if time allows; the rest of the world keeps working with live APIs but is not polished.
7. **APIs first, datasets as backup.** Use live keyless APIs (NASA POWER, GIBS, ORNL MODIS) when they exist. Downloaded files in
   `data/` are the backup (the Lambayeque grid file) or the only source when NASA offers no keyless API (IMERG, GRACE, NASADEM, SMAP).
8. **Licenses:** only NASA / partner-agency data, or third-party material that is free and openly licensed. Ask before adding any.

## Map of the repo

| Path | What |
|---|---|
| `web/` | Vue 3 + Vite app. `npm run dev` inside it |
| `web/src/content.js` | All UI text, Sprout's script (`SCRIPTS`), layers, crops, rotations |
| `web/src/store.js` · `web/src/guide.js` | App state, stages and live data · Sprout's dialogue, answers and guide on/off |
| `web/src/components/` · `web/src/slides/` | Stages (`IntroStage`, `RegionPicker`, `ExploreStage`, `MapStage`), HUD pieces · one file per topic |
| `web/src/lib/admin.js` · `web/src/data/` | Lambayeque provinces, districts and place names (OpenStreetMap, built by `pipeline/build_*.py`) |
| `web/src/lib/ask.js` | Sprout's open questions: an optional AI endpoint (`VITE_ASK_URL`) or a few local answers |
| `web/src/lib/nasa.js` | Live NASA requests (POWER, MODIS via ORNL, GIBS) and grid cells |
| `web/src/lib/pixelIcons.js` · `web/src/cat/sprites.js` | Pixel icons · Sprout's sprites |
| `pipeline/` | Python data scripts (venv in `pipeline/.venv`) |
| `data/` | Downloaded data. Read `data/README.md` and `data/STRUCTURE.md` before touching any NASA file |
| `setup.sh` | Installs Vue and Python dependencies |

## Before you finish

- `cd web && npx vite build` must pass.
- Check the page in a browser at desktop and phone width (there is only the night look, no light mode).
- The commit message follows `COMMITS.md` (Conventional Commits, English).
