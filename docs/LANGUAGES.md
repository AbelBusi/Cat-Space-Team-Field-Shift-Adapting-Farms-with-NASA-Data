# Languages: English, Spanish and Quechua

The top bar has an `EN | ES | QU` switch. The choice is saved in the browser and sets `<html lang>`.
**English is the default**, because Space Apps asks for the project in English.

## How it works

- All translations live in `web/src/i18n.js`. **The English text is the key**: `t('Rain')` returns `'Lluvia'` in Spanish.
- Missing Quechua falls back to Spanish, then to English, so the page never shows an empty label.
- In templates `t()` is global (`{{ t('Save water') }}`). In script code: `import { t } from '../i18n.js'`.
- Text with numbers or names uses placeholders: `t('Tap at least 3 corners (you have {n}).', { n: 2 })`.
- Sprout's lines are stored in English (or as a function for lines with names and numbers) and are translated when shown,
  so the line on screen changes language at once.

## Adding or changing text

1. Write the English text in the component or in `content.js` and wrap it with `t()`.
2. Add the same English string as a key in `ES` **and** in `QU` (both required: every key exists in all three languages).
3. Keep the English key **exactly** identical, including punctuation; otherwise the translation is not found.

## Quechua status: beta

- **Everything is translated** (391 keys, same as Spanish): menus, buttons, readings, Sprout's whole script and reactions,
  rotations, satellite evidence, glossary, footer credits and screen-reader labels. Nothing falls back to Spanish.
- Loanwords only where Quechua has no everyday word: Spanish (*prueba*, *facil*, *seguro*, *crédito*,
  *molino*, *fertilizante*, *nitrógeno*, *sorgo*, *hectárea*, *agronomo*) and English/technical names (*píxel*, *demo*,
  *NDVI*, satellite and dataset names). Numbers and units stay as they are.
- It is **Southern Quechua** written with AI help. It must be reviewed by native speakers. The Quechua spoken in Lambayeque's
  highlands (Inkawasi-Kañaris) is a different variety: ideally a speaker from Inkawasi or Kañaris reviews and adapts it.
- Spanish month names are used in Quechua mode, as is common in everyday speech.
