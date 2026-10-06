import io
import os
import warnings

# Suppress internal PyTorch deprecation and module warnings from third-party libraries
warnings.filterwarnings("ignore", category=UserWarning, message=".*dropout option adds dropout after all but last recurrent layer.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*torch.nn.utils.weight_norm is deprecated.*")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import tempfile

import numpy as np
import soundfile as sf

# import whisper
from faster_whisper import WhisperModel
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from kokoro import KPipeline
from pydantic import BaseModel

app = FastAPI(title="Whisper + Kokoro API")

# Allow the React dev server (Vite runs on port 5173) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models load once at startup. Change "base" to "tiny" (faster) or "small" (more accurate).
print("Loading Whisper...")
# stt_model = whisper.load_model("base")
stt_model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Loading Kokoro...")
tts_pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")  # "a" = American English, "b" = British English
print("Models ready.")


class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"

@app.get("/")
def read_root():
    return {"status": "Server is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/stt")
def speech_to_text(file: UploadFile = File(...)):
    """Receive an audio file, return the transcript."""
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        # Whisper uses ffmpeg to decode the file, so ffmpeg must be installed.
        # result = stt_model.transcribe(path, language="en", fp16=False)
        # return {"text": result["text"].strip()}
        segments, info = stt_model.transcribe(path, language="en")
        text = "".join([segment.text for segment in segments]).strip()
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.remove(path)


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    """Receive text, return a WAV audio file."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    try:
        chunks = []
        for _, _, audio in tts_pipeline(req.text, voice=req.voice):
            chunks.append(audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio))
        if not chunks:
            raise HTTPException(status_code=500, detail="No audio generated")
        buf = io.BytesIO()
        sf.write(buf, np.concatenate(chunks), 24000, format="WAV")
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)