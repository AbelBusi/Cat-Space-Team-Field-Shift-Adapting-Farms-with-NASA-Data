#!/usr/bin/env bash
# Downloads Sprout's two voices (Piper, from https://huggingface.co/rhasspy/piper-voices, MIT-licensed code, voices with
# their own model cards) into voice_assistant/models/ (~63 MB each, ignored by git):
#   es_MX-claude-high  (Spanish, soft voice)   en_US-amy-medium  (English, soft voice)
# Then set TTS_ENGINE=piper in ml-api/.env (the default). Run from anywhere: bash ml-api/voice_assistant/download_voices.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p models
for p in es/es_MX/claude/high/es_MX-claude-high en/en_US/amy/medium/en_US-amy-medium; do
  f=$(basename "$p")
  for ext in onnx onnx.json; do
    [[ -s "models/$f.$ext" ]] && { echo "ok  models/$f.$ext"; continue; }
    echo "get models/$f.$ext"
    curl -fL --progress-bar -o "models/$f.$ext" "https://huggingface.co/rhasspy/piper-voices/resolve/main/$p.$ext"
  done
done
echo "Done. Restart the API; check GET /api/v1/assistant/status (tts.voices.*.found = true)."
