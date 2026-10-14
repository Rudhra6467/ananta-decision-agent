"""Telugu voice on the Mac (Oct 11, plan Batch 3): Meta's MMS Telugu model, free, no account. Runs as com.ananta.telugu on port 8210.
POST /speak {"sentences": [Telugu script], "speed": 1.0} -> one MP3 with sentence start times (same shape as the main voice server)."""
from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel

MODEL = "facebook/mms-tts-tel"
_lock = threading.Lock()
model = VitsModel.from_pretrained(MODEL)
tok = AutoTokenizer.from_pretrained(MODEL)
RATE = model.config.sampling_rate


def speak(sentences: list[str], speed: float = 1.0) -> dict:
    t0 = time.time()
    parts, offsets, total = [], [], 0.0
    with _lock:
        model.speaking_rate = max(0.7, min(1.4, float(speed or 1.0)))
        for s in sentences:
            with torch.no_grad():
                a = model(**tok(s, return_tensors="pt")).waveform.squeeze().numpy()
            offsets.append(round(total, 3))
            a = np.concatenate([a, np.zeros(int(0.25 * RATE), dtype=a.dtype)])
            parts.append(a)
            total += len(a) / RATE
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(parts) if parts else np.zeros(1), RATE, format="WAV", subtype="PCM_16")
    wav, mime = buf.getvalue(), "audio/wav"
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    try:
        out = subprocess.run([ff, "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k",
                              "-f", "mp3", "pipe:1"], input=wav, capture_output=True, timeout=20).stdout
        if len(out) > 200:
            wav, mime = out, "audio/mpeg"
    except Exception:  # noqa: BLE001
        pass
    return {"audio_b64": base64.b64encode(wav).decode(), "mime": mime, "offsets": offsets, "duration": round(total, 3),
            "voice": "mms-tel", "ms": int(1000 * (time.time() - t0))}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D401
        pass

    def _send(self, code: int, body: dict) -> None:
        b = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"ok": True, "model": MODEL})

    def do_POST(self):
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._send(200, speak([str(x) for x in d.get("sentences") or []][:40], d.get("speed", 1.0)))
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error": str(exc)[:200]})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8210), H).serve_forever()
