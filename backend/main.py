# Kokoro (text-to-speech) server. Whisper lives in stt_server.py (separate process).
import io
import threading
import time
import traceback
import warnings
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

warnings.filterwarnings("ignore", category=UserWarning)

tts_pipeline = None
state = {"tts": "loading"}


def load_kokoro():
    global tts_pipeline
    try:
        t = time.time()
        print("Loading Kokoro...", flush=True)
        from kokoro import KPipeline

        tts_pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        list(tts_pipeline("Hello.", voice="af_heart"))  # warm-up
        state["tts"] = "ready"
        print(f"Kokoro ready in {time.time() - t:.1f}s", flush=True)
    except Exception as e:
        state["tts"] = f"error: {e}"
        traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=load_kokoro, daemon=True).start()
    yield


app = FastAPI(title="Kokoro TTS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

VOICE_MAPPING = {
    "Heart (US, female)": "af_heart",
    "Bella (US, female)": "af_bella",
    "Michael (US, male)": "am_michael",
    "Emma (UK, female)": "bf_emma",
    "George (UK, male)": "bm_george",
}


class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"


@app.get("/status")
def status():
    return state


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    if tts_pipeline is None:
        raise HTTPException(status_code=503, detail=f"Kokoro not ready: {state['tts']}")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    voice_id = VOICE_MAPPING.get(req.voice, req.voice)
    try:
        chunks = []
        for _, _, audio in tts_pipeline(req.text, voice=voice_id, speed=1.0):
            if audio is not None:
                chunks.append(audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio))
        if not chunks:
            raise ValueError("No audio generated")
        buf = io.BytesIO()
        sf.write(buf, np.concatenate(chunks), 24000, format="WAV")
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")