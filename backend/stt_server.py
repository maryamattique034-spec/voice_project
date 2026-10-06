# Whisper (speech-to-text) in its OWN process, so it never clashes with torch/Kokoro on macOS.
import os
import tempfile
import traceback

from faster_whisper import WhisperModel
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

print("Loading Whisper (faster-whisper, tiny)...", flush=True)
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Whisper ready.", flush=True)

app = FastAPI(title="Whisper STT")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
def status():
    return {"stt": "ready"}


@app.post("/stt")
def speech_to_text(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        segments, _ = model.transcribe(path, language="en")
        return {"text": "".join(s.text for s in segments).strip()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(path):
            os.remove(path)