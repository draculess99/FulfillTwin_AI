#!/usr/bin/env bash
set -euo pipefail

export API_PORT="${API_PORT:-5000}"
export FULFILLTWIN_API_URL="${FULFILLTWIN_API_URL:-http://127.0.0.1:${API_PORT}}"

gunicorn --workers 1 --threads 4 --timeout 180 --bind "0.0.0.0:${API_PORT}" "fulfilltwin.backend.app:create_app()" &
API_PID=$!
trap 'kill ${API_PID} 2>/dev/null || true' EXIT

streamlit run streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --server.headless true
