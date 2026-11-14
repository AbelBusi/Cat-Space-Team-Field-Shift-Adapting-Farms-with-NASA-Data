#!/usr/bin/env bash
# Installs everything the project needs: the web app (Vue) and the Python data pipeline.
#   ./setup.sh          # both
#   ./setup.sh web      # only Vue
#   ./setup.sh python   # only Python
set -euo pipefail
cd "$(dirname "$0")"
what="${1:-all}"

if [[ "$what" == all || "$what" == web ]]; then
  command -v npm >/dev/null || { echo "npm not found. Install Node.js 20+ first: https://nodejs.org"; exit 1; }
  echo "==> Installing web app (Vue) dependencies"
  (cd web && npm install)
fi

if [[ "$what" == all || "$what" == python ]]; then
  command -v python3 >/dev/null || { echo "python3 not found. Install Python 3.11+ first."; exit 1; }
  echo "==> Creating Python environment in pipeline/.venv"
  python3 -m venv pipeline/.venv
  pipeline/.venv/bin/python -m pip install --upgrade pip
  pipeline/.venv/bin/python -m pip install -r pipeline/requirements.txt
  pipeline/.venv/bin/python -c "import earthaccess, xarray, h5netcdf, pandas, numpy, sklearn; print('Python libraries OK')"
fi

echo
echo "Done. Start the app with:  cd web && npm run dev   (http://localhost:5173)"
