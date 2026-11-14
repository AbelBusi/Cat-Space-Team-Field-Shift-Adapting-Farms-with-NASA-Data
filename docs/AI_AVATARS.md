# Idea for later: regional guide avatars with AI

Status: **idea, not built.** Today Sprout speaks from a fixed script (`SCRIPTS` in `web/src/content.js`) plus a few reactions.
This note keeps the team's plan so it can be built after the core is done.

## The idea

Instead of one generic chatbot, a few **guides from different farming cultures**, each a local animal with its own look,
light local slang and an understanding of that region's crops and climate. The farmer picks one, or it is suggested by the
chosen place. They explain the same NASA data in their own way, and can answer short questions about it.

- **Sprout stays the main guide** (the alien cat that came down from orbit). The others are "friends" Sprout introduces.
- **Voice = animal sounds + text**, like Sprout's meows. No text-to-speech.
- **Slang in small doses.** A word or two per answer, never a caricature. Respectful, warm, a bit of humour.

Example cast (to be reviewed by people from each region):

| Region | Guide | Flavor |
|---|---|---|
| Peru (coast and Andes) | A guinea pig (cuy) or an alpaca | "¡Habla, causa!" once in a while; knows rice, maize, El Niño costero, *heladas* in the highlands |
| Mexico | An axolotl | Milpa (maize, beans, squash), monsoon rains |
| USA, Corn Belt | A prairie dog | Corn and soybean rotations, frost dates, drought |
| India, Punjab | A peacock | Rice-wheat rotation, monsoon, falling groundwater |
| Kenya | A dik-dik | Two rainy seasons, maize and beans, drought years |
| Brazil | A capybara | Soy and second-crop maize, dry season |
| Egypt, Nile Delta | An ibis | Irrigation, salinity, cotton and wheat |

## How it would work (cheap and safe)

```
browser ──► small Python endpoint (FastAPI) ──► LLM API
              │  holds the API key (never in the browser)
              │  adds: the persona "skill" + the NASA numbers for the chosen place
              └  topic filter: only farming, climate, water, soil and this app
```

- **Persona "skill" = a well-written system prompt per guide**, stored as a text file
  (`personas/peru_cuy.md` …): who they are, tone, 10–20 local words they may use, crops and risks of the region,
  and hard rules (do not invent data, say when the satellite cannot see something, recommend a local agronomist).
- **Grounding:** the endpoint passes the real values the page already has (POWER climate, NDVI, hard years, chosen rotation)
  so the guide explains *those* numbers instead of making things up.
- **Topic filter:** a short classifier prompt (or keyword check) before answering. Off-topic questions get a friendly refusal
  in character ("I only know about fields and skies, causa!").
- **Short answers:** 1–3 sentences, plain words, one tangible comparison.

## Model options to evaluate

| Option | Why | Watch out |
|---|---|---|
| Ollama running a small open model locally (Llama, Qwen, Mistral families) | Free, works offline at the event | Needs a laptop with enough RAM; slower |
| A hosted open-model API with a free tier | Fast, cheap | Free-tier limits; check terms and data use |
| A small commercial model (e.g. Claude Haiku) | Best quality per cost for short answers | Paid; key must stay server-side |

Pick one by testing the same 10 farmer questions in Spanish and English with each option.

## Before building

- Space Apps rules: credit the model and any persona or slang sources; no personal data.
- Ask someone from each region to review their guide's words and tone.
- Keep the scripted Sprout as the fallback when the AI is off or slow.
