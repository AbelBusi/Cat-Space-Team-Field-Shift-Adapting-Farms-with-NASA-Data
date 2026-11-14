# Field Shift design system

**Agreed by the whole team on Nov 13, 2026. Do not add colors, shapes or fonts outside this file.**
If something seems to need a new color, it does not: use a ramp step, a pattern, an icon or a text label instead.
The tokens below live as CSS variables at the top of `web/src/style.css`, and as `PAL` / `RAMP` in `web/src/lib/palette.js` for
Leaflet, D3 and canvas code. Always use those, never a raw hex.

Mood: **Outer Wilds at night**. A calm, cozy space-camp feeling: deep night sky, a turquoise glow, a warm campfire.
Data must still read clearly, so data colors are *derived* from the same two accents.

## 1. Palette

### Interface (5 neutrals + 2 accents)

| Token | Hex | Use | Never |
|---|---|---|---|
| `--bg` | `#0B1026` | Page background, the "space" | — |
| `--panel` | `#121A3A` | Panels, cards, the map frame, Sprout's screen | — |
| `--line` | `#1E2A52` | 1 px borders, chart grid lines, dividers | Text |
| `--muted` | `#8C9BC4` | Secondary text, axis labels, captions | Long paragraphs |
| `--ink` | `#F2E8D5` | Main text, icons by default | — |
| `--teal` | `#4FC1B6` | **The accent.** Links, active state, selected items, focus ring, "normal" data | Warnings |
| `--fire` | `#F2A541` | **The campfire.** At most ONE highlighted thing per screen: the main button, the key number, the highlighted bar | Decoration, backgrounds |

Light mode ("daytime camp") keeps the same roles: `--bg #F4EEDF`, `--panel #FFFDF7`, `--line #DCD3BF`, `--muted #5B6585`,
`--ink #141B38`, `--teal #23877E`, `--fire #B86A0B` (darker so they pass contrast on cream).

### Data (derived, only inside charts, maps and legends)

| Token | Hex | Use |
|---|---|---|
| `--sand` | `#D8C08E` | Dry, bare soil, low risk |
| `--soil` | `#A88B5A` | Soil in icons, the ground line of charts |
| `--sage` | `#9CC5A1` | Middle of the vegetation ramp |
| `--deep` | `#2E6E86` | Dark end of the water ramp, plant outlines |
| `--ember` | `#E0703A` | High risk, extreme heat. The only "alarm" color |
| `--ghost` | `#A99BE8` | Frost, and the 4th category when 4 are needed |

**Ramps** (always these stops, in this order):

| Meaning | Stops |
|---|---|
| Amount (rain, soil moisture) | `--line` → `--deep` → `--teal` → `#BFEDE6` |
| Vegetation (NDVI) | `--sand` → `--sage` → `--teal` → `--deep` |
| Temperature (absolute) | `--deep` → `--sand` → `--fire` → `--ember` |
| Anomaly (diverging) | `--teal` (cooler / wetter) → `#2A3A66` (normal) → `--fire` → `--ember` (hotter / drier) |
| Risk (3 levels, not a traffic light) | `--sand` low · `--fire` medium · `--ember` high |
| Categories (max 4, this order) | `--teal`, `--fire`, `--sand`, `--ghost` |

No red, yellow or green "traffic lights". No rainbow ramps (jet, viridis, turbo). No colors from chart-library defaults.

## 2. Shape

- **Square corners everywhere** (`border-radius: 0`). No pills, no bubbly cards, no rounded buttons, also in Leaflet controls.
- Borders are **1 px `--line`**. A featured panel may add **HUD corner brackets** (the `.hud` class), like a ship screen.
- No shadows, no blur, no glassmorphism, no gradients **on components**. Gradients live only in the **atmosphere**: the landing sky
  and the fixed page background (soft teal, campfire and lavender lights, faint stars; the campfire glow grows as you scroll).
  Cards may be slightly see-through (88 % panel) so that light shows behind them, but never blurred.
- Buttons are text in **mono caps inside brackets or a 1 px frame**: `[ NEXT ]`, `EXPLORE`. The single main action uses `--fire`.

## 3. Type

| Role | Font | Size |
|---|---|---|
| Headings | Bricolage Grotesque, weight 600 | h1 max **40 px** desktop / 30 px mobile; h2 24–28 px. No giant hero letters |
| Body | Atkinson Hyperlegible | 16 px, line-height 1.5 |
| HUD labels, numbers, buttons, Sprout's text | IBM Plex Mono | 12–15 px; labels in caps with 0.08em spacing |
| Sprout's name tag only | Pixelify Sans | 13 px |

## 4. Icons

Use only the pixel icons in `web/src/lib/pixelIcons.js` through `<PixelIcon name="…" />` (16 × 16, scaled by whole numbers).
They speak the farmer's language: a plant that is fine, thirsty or dead says more than a red dot.

| Icon | Means |
|---|---|
| `plant_ok` | Healthy crop, good conditions |
| `plant_thirsty` | Water stress, risk of loss |
| `plant_dead` | Crop loss, high risk |
| `seed` · `harvest` · `bare` | Sowing month · harvest month · bare soil |
| `sun` · `drop` · `rain` · `frost` | Heat · irrigation water · heavy rain · frost |
| `up` · `down` · `flat` | Trend. Color = what it means for the crop: `--ember` worse, `--teal` better, `--ink` neutral |

Line icons (stroke SVG) are allowed only for UI controls (play, sound, close), drawn in `--ink` or `--muted`.

## 5. Charts

- **One story per chart.** The bar, point or month that matters is `--fire` with its label; everything else is `--teal` at 35 % opacity.
- Grid lines `--line`, axis labels `--muted` in mono. No pie, donut, 3D or gauge charts. No legends when a direct label fits.
- Prefer farm metaphors: a year is a **row of 12 plants** (sown, growing, harvested, bare); risk is a plant's state; trend is an arrow.
- Every number on screen is rounded and has its unit.

## 6. Map

- The base map is always **real satellite imagery, untouched**. Farmers must see their field as it is.
- NASA data are **optional overlays** on top, with the ramps above, a legend and an opacity control.
- The frame around the map uses the interface neutrals, so the map looks like a ship's window.

## 7. Sprout's panel (Outer Wilds translator style)

- A bar at the bottom of the screen: `--panel` background, 1 px `--teal` frame with HUD brackets, label `SPROUT · TRANSLATOR` in mono caps.
- Text in IBM Plex Mono, `--ink`, typed letter by letter. Buttons `[ NEXT ]`, `[ SHOW ALL ]`, `[ ♪ ]`, `[ _ ]` (minimize).
- Minimized: a small square tab with Sprout's face in a corner. On phones the panel spans the full width.

## 8. Motion

Things appear when Sprout explains them (fade + 12 px rise, 0.5 s). Charts draw in. Numbers count. Nothing loops except the sky,
the satellite and Sprout's idle bob. Everything turns off with `prefers-reduced-motion`.

## 9. Two modes: Farmer and Pro

A switch in the top bar (`state.mode`, saved in the browser). Same NASA data, two ways to read it.

| | Farmer mode (default) | Pro mode |
|---|---|---|
| Readings | A **tool the farmer knows**, drawn in pixels: thermometer (heat), rain gauge (rain), a handful of soil — cracked, moist or puddled (soil wetness), a plant — bare, thirsty or healthy (greenness) — plus a **word** ("Hot", "A little rain") | The number with its unit and a sparkline |
| Rotation fit | A plant (healthy / thirsty / dead) and a word: Good fit · Could work · Poor fit | The score out of 100 |
| Comparison | An arrow and Better / Worse / Same | Five squares per topic and the arrow |
| Year by year | Warming stripes and three tangible facts ("About 4× the rain of a normal year") | The same plus the annual rain bars with the extreme years labeled |

Rules: Farmer mode never shows a percentage or a decimal; thresholds live in `levelWord()` (`web/src/content.js`), so the
science is the same in both modes. Sprout explains in words what the icons show.

## 10. Original charts we use

| Chart | Where | Why it is ours |
|---|---|---|
| Row of 12 plants | Rotations | A year read like a furrow: seed, growing, stressed, harvest, bare soil |
| Warming stripes | Year by year | One stripe per year from 1981, turquoise cooler → campfire hotter |
| One-story bars | Year by year (Pro) | Only the wettest year in `--fire` and the driest in `--sand` are lit |
| Pixel instruments | Signal panel (Farmer) | Thermometer and rain gauge fill up with the real value |
| Pixel globe | Signal panel | A small Earth (land from NASA GRACE's land mask) turns to the chosen place and marks it with a campfire pixel |
