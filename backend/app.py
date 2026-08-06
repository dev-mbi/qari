"""Flask + SocketIO server for the Quran recitation feedback system."""

import base64
import json

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

from . import config
from .engine import get_engine

app = Flask(__name__, static_folder=str(config.FRONTEND_DIR), static_url_path="/static")
app.config["SECRET_KEY"] = "qari"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


@app.get("/")
def index():
    return send_from_directory(config.FRONTEND_DIR, "index.html")


@app.get("/api/page/<int:page_no>")
def api_page(page_no: int):
    try:
        return jsonify(get_engine().page_info(page_no))
    except KeyError:
        return jsonify({"error": "page not found"}), 404


@app.get("/api/meta")
def api_meta():
    eng = get_engine()
    return jsonify(eng.meta)


@app.post("/transcribe")
def transcribe():
    """Testing endpoint: JSON body {"audio": "<base64 wav>", "sample_rate": 16000}."""
    body = request_json()
    b64 = body.get("audio", "")
    sr = body.get("sample_rate", config.SAMPLE_RATE)
    fmt = body.get("format", "i16")
    try:
        raw = base64.b64decode(b64)
        text = get_engine().process_audio(raw, sr, fmt=fmt)
        return jsonify(text)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on("connect")
def on_connect():
    try:
        info = get_engine().set_page(1)
        emit("page", info)
    except Exception as e:
        emit("error", {"message": str(e)})


@socketio.on("select_page")
def on_select_page(data):
    page_no = int((data or {}).get("page", 1))
    try:
        info = get_engine().set_page(page_no)
        emit("page", info)
    except KeyError:
        emit("error", {"message": f"page {page_no} not found"})


@socketio.on("audio_chunk")
def on_audio_chunk(data):
    try:
        pcm = base64.b64decode(data.get("pcm", ""))
        sr = int(data.get("sample_rate", config.SAMPLE_RATE))
        fmt = data.get("format", "i16")
        result = get_engine().process_audio(pcm, sr, fmt=fmt)
        emit("feedback", result)
    except Exception as e:
        emit("error", {"message": str(e)})


def request_json():
    try:
        return request.get_json(force=True, silent=True) or {}
    except Exception:
        return {}


def main():
    import threading

    def warmup():
        try:
            from . import asr
            asr.get_model()
            print("[qari] ASR model loaded (warmup done)")
        except Exception as e:
            print(f"[qari] warmup failed: {e}")

    threading.Thread(target=warmup, daemon=True).start()

    cert = config.BASE_DIR / "certs" / "cert.pem"
    key = config.BASE_DIR / "certs" / "key.pem"
    if cert.exists() and key.exists():
        # HTTPS fallback on 5001 for browsers that force https://localhost:5000
        def run_https():
            try:
                socketio.run(app, host="0.0.0.0", port=5001,
                             ssl_context=(str(cert), str(key)),
                             debug=False, allow_unsafe_werkzeug=True)
            except Exception as e:
                print(f"[qari] https on 5001 failed: {e}")
        threading.Thread(target=run_https, daemon=True).start()
        print("[qari] HTTPS fallback on https://localhost:5001")

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
