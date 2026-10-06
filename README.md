# Voice App: Whisper (STT) + Kokoro (TTS)

A small web app that turns speech into text and text into speech, running entirely on your own machine.

- **Speech-to-Text:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper `tiny` model, English)
- **Text-to-Speech:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) with 5 English voices
- **Backend:** FastAPI (Python), as two small services
- **Frontend:** React (Vite)

## How it works

```
React app (5173)
   ├── record mic audio ──► STT service (8001) ──► Whisper ──► transcript
   └── send text ─────────► TTS service (8000) ──► Kokoro  ──► WAV audio
```

Whisper and Kokoro run as **two separate processes**. On macOS, loading both in one process can hang because their libraries each bundle an OpenMP runtime and clash. Separate processes avoid this completely.

## Project structure

```
voice_project/
├── .venv/                  Python virtual environment
├── run_all.sh              starts everything with one command
├── backend/
│   ├── main.py             Kokoro TTS service  (port 8000)
│   ├── stt_server.py       Whisper STT service (port 8001)
│   └── requirements.txt
└── frontend/
    ├── package.json
    └── src/
        ├── main.jsx
        └── App.jsx         the UI
```

## Requirements

- Python 3.10 to 3.12 (3.13 can cause install problems)
- Node.js 18+ and npm
- `espeak-ng` (used by Kokoro)
- Internet on the first run (models download once, about 330 MB for Kokoro and 75 MB for Whisper, then they are cached and work offline)

```bash
# macOS
brew install node espeak-ng

# Ubuntu / Debian
sudo apt-get install espeak-ng
```

## Setup (one time)

From the project root:

```bash
# 1. Python environment and backend dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Frontend dependencies
cd frontend
npm install
cd ..
```

## Run

**Option A: one command**

```bash
bash run_all.sh
```

Press `Ctrl+C` once to stop everything.

**Option B: three terminals**

```bash
# Terminal 1: Kokoro (TTS)
source .venv/bin/activate
cd backend && uvicorn main:app --port 8000

# Terminal 2: Whisper (STT)
source .venv/bin/activate
cd backend && uvicorn stt_server:app --port 8001

# Terminal 3: React app
cd frontend && npm run dev
```

Do not use `--reload` for the backend, because it restarts the process and reloads the models on every file change.

Open **http://localhost:5173**.

On the first run Kokoro downloads its model, so wait until `http://127.0.0.1:8000/status` shows `{"tts":"ready"}` before pressing Speak.

## Using the app

1. **Record:** click Record, speak in English, click Stop. The transcript appears in the text box.
2. **Edit:** the text box is editable. You can also just type.
3. **Speak:** choose a voice and click Speak. Kokoro reads the text aloud. Use "Download audio" to save the WAV file.

## API

| Service | Method | Path | Description |
|---|---|---|---|
| TTS (8000) | GET | `/status` | `{"tts": "loading" / "ready" / "error: ..."}` |
| TTS (8000) | POST | `/tts` | JSON `{"text": "...", "voice": "af_heart"}`, returns `audio/wav` |
| STT (8001) | GET | `/status` | `{"stt": "ready"}` |
| STT (8001) | POST | `/stt` | multipart form field `file` (audio), returns `{"text": "..."}` |

Interactive docs: `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8001/docs`.

## Configuration

| What | Where | How |
|---|---|---|
| Whisper model size | `backend/stt_server.py` | change `"tiny"` to `"base"` or `"small"` (more accurate, slower) |
| Voices | `frontend/src/App.jsx` (`VOICES`) and `backend/main.py` (`VOICE_MAPPING`) | Kokoro voice ids, such as `af_heart`, `am_michael`, `bf_emma` |
| Backend URLs | `frontend/src/App.jsx` (`TTS_API`, `STT_API`) | defaults to localhost ports 8000 and 8001 |
| Allowed origins (CORS) | `allow_origin_regex` in both backend files | defaults to `localhost` and `127.0.0.1` on any port |

## Troubleshooting

**`Kokoro not ready` (HTTP 503) when clicking Speak**
The model is still loading. Check `http://127.0.0.1:8000/status`. If it shows an error, the message tells you what failed. If it stays on `loading` for many minutes, check that the download finished: `du -sh ~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M` should be around 312M.

**Kokoro hangs while loading**
Kokoro needs the spaCy English model. Install it with `python -m spacy download en_core_web_sm`. Also confirm `espeak-ng --version` works.

**`OMP: Error #15: libiomp5.dylib already initialized` or the server hangs on macOS**
This happens when Whisper and Kokoro are loaded in the same process. Run them separately as described above (`stt_server.py` and `main.py`).

**`Failed to fetch` in the UI**
The backend is not running, or the page is not on `localhost` / `127.0.0.1`. Start the services and check the `/status` URLs.

**Microphone not working**
Browsers only allow microphone access on `https://` or `localhost`. Allow the permission when the browser asks.

**Blank or oddly styled page**
Make sure `src/main.jsx` does not import Vite's default `index.css`, since its styles conflict with the app's own CSS.

**Port already in use**
Stop the old process, or find it with `lsof -i :8000` and stop it with `kill <PID>`.

## Deployment notes

For development the app calls `http://localhost:8000` and `http://localhost:8001` directly. Before deploying:

1. Build the frontend with `npm run build` and host the static files.
2. Run each backend service as a managed process or container, ideally with a reverse proxy (Nginx or Caddy) in front.
3. Serve everything over **HTTPS**, because browsers block the microphone on plain HTTP.
4. Replace the hardcoded URLs with environment variables (for example `import.meta.env.VITE_TTS_API`) and add your domain to the CORS settings.
5. Cache the downloaded models (a Docker volume or baked into the image) so they are not downloaded on every restart.

The models run on CPU. Whisper `tiny` plus Kokoro work on a small server (about 2 to 4 CPU cores and 4 GB RAM). Use a GPU for many users or lower latency.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper) and [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) by hexgrad
- [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), [Vite](https://vite.dev/)