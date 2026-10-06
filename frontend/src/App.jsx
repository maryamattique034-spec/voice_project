import { useRef, useState } from "react";

const TTS_API = "http://localhost:8000";
const STT_API = "http://localhost:8001";

const VOICES = [
    ["af_heart", "Heart (US, female)"],
    ["af_bella", "Bella (US, female)"],
    ["am_michael", "Michael (US, male)"],
    ["bf_emma", "Emma (UK, female)"],
    ["bm_george", "George (UK, male)"],
];

export default function App() {
    const [text, setText] = useState("");
    const [voice, setVoice] = useState("af_heart");
    const [status, setStatus] = useState("Ready");
    const [recording, setRecording] = useState(false);
    const [busy, setBusy] = useState(false);
    const [audioUrl, setAudioUrl] = useState(null);
    const recorder = useRef(null);
    const chunks = useRef([]);

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            chunks.current = [];
            const mr = new MediaRecorder(stream);
            mr.ondataavailable = (e) => chunks.current.push(e.data);
            mr.onstop = () => {
                stream.getTracks().forEach((t) => t.stop());
                transcribe(new Blob(chunks.current, { type: mr.mimeType }));
            };
            mr.start();
            recorder.current = mr;
            setRecording(true);
            setStatus("Listening... press Stop when you are done");
        } catch {
            setStatus("Microphone blocked. Allow mic access and try again.");
        }
    }

    function stopRecording() {
        recorder.current?.stop();
        setRecording(false);
    }

    async function transcribe(blob) {
        setBusy(true);
        setStatus("Transcribing...");
        try {
            const form = new FormData();
            form.append("file", blob, "recording.webm");
            const res = await fetch(`${STT_API}/stt`, { method: "POST", body: form });
            if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
            const data = await res.json();
            setText((t) => (t ? t + " " : "") + data.text);
            setStatus("Done. Edit the text or press Speak.");
        } catch (e) {
            setStatus("Transcription failed: " + e.message + ". Is the backend running?");
        }
        setBusy(false);
    }

    async function speak() {
        if (!text.trim()) return setStatus("Type or record something first.");
        setBusy(true);
        setStatus("Generating speech...");
        try {
            const res = await fetch(`${TTS_API}/tts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, voice }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
            const url = URL.createObjectURL(await res.blob());
            setAudioUrl(url);
            new Audio(url).play();
            setStatus("Done.");
        } catch (e) {
            setStatus("Speech failed: " + e.message + ". Is the backend running?");
        }
        setBusy(false);
    }

    return (
        <main className="wrap">
            <style>{css}</style>
            <h1>Say it, read it, hear it</h1>
            <p className="sub">
                Whisper turns your voice into text. Kokoro reads any text aloud.
            </p>

            <section>
                <h2>Voice to text</h2>
                <button
                    className={recording ? "stop" : "go"}
                    disabled={busy}
                    onClick={recording ? stopRecording : startRecording}
                >
                    {recording ? "Stop recording" : "Record"}
                </button>
            </section>

            <section>
                <h2>Text</h2>
                <textarea
                    rows={6}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Your transcript appears here. You can also type."
                />
            </section>

            <section>
                <h2>Text to voice</h2>
                <div className="row">
                    <select value={voice} onChange={(e) => setVoice(e.target.value)}>
                        {VOICES.map(([id, label]) => (
                            <option key={id} value={id}>
                                {label}
                            </option>
                        ))}
                    </select>
                    <button className="go" disabled={busy || recording} onClick={speak}>
                        Speak
                    </button>
                    {audioUrl && (
                        <a href={audioUrl} download="speech.wav">
                            Download audio
                        </a>
                    )}
                </div>
            </section>

            <p className="status" role="status">
                {status}
            </p>
        </main>
    );
}

const css = `
:root{--bg:#f3f6f4;--ink:#16221d;--mute:#5b6b63;--line:#c9d4ce;--accent:#0f6b4f;--rec:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#121a16;--ink:#e6efe9;--mute:#98a89f;--line:#2b3a33;--accent:#4cc79b;--rec:#ff8a80}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,serif}
.wrap{max-width:640px;margin:0 auto;padding:40px 20px}
h1{font:700 2rem/1.15 system-ui,sans-serif;margin:0 0 8px}
h2{font:600 1rem system-ui,sans-serif;margin:0 0 8px}
.sub{color:var(--mute);margin:0 0 28px}
section{border-top:1px solid var(--line);padding:20px 0}
textarea,select{width:100%;font:inherit;color:inherit;background:transparent;border:1px solid var(--line);border-radius:8px;padding:10px}
select{width:auto}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{font:600 1rem system-ui,sans-serif;border:0;border-radius:8px;padding:10px 20px;cursor:pointer;color:var(--bg)}
button.go{background:var(--accent)}
button.stop{background:var(--rec)}
button:disabled{opacity:.5;cursor:wait}
button:focus-visible,select:focus-visible,textarea:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
a{color:var(--accent)}
.status{color:var(--mute);font-size:.9rem;min-height:1.5em}
`;