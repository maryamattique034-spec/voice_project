#!/bin/bash
# Starts Whisper (8001), Kokoro (8000) and the React app from ONE terminal.
# Press Ctrl+C once to stop everything.
cd "$(dirname "$0")"
source .venv/bin/activate

trap 'kill 0' EXIT

(cd backend && uvicorn stt_server:app --port 8001) &
(cd backend && uvicorn main:app --port 8000) &
(cd frontend && npm run dev) &

wait