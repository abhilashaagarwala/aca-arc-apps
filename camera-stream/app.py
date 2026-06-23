import os
import time

import cv2
from flask import Flask, Response

app = Flask(__name__)

DEVICE = os.environ.get("CAMERA_DEVICE", "/dev/video0")
PORT = int(os.environ.get("PORT", "8080"))

_camera = None


def get_camera():
    global _camera
    if _camera is None or not _camera.isOpened():
        _camera = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)
    return _camera


def frames():
    cam = get_camera()
    while True:
        ok, frame = cam.read()
        if not ok:
            time.sleep(0.1)
            cam = get_camera()
            continue
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + buf.tobytes()
            + b"\r\n"
        )


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Camera Stream</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0;
           margin:0; display:flex; flex-direction:column; align-items:center;
           justify-content:center; min-height:100vh; }
    h1 { margin:1rem; font-size:1.25rem; }
    img { max-width:90vw; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.5); }
  </style>
</head>
<body>
  <h1>Live Camera Stream (/dev/video0)</h1>
  <img src="/stream" alt="camera stream">
</body>
</html>"""


@app.route("/")
def index():
    return PAGE


@app.route("/stream")
def stream():
    return Response(
        frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/snapshot")
def snapshot():
    """Capture and return a single JPEG frame."""
    cam = get_camera()
    ok, frame = cam.read()
    if not ok:
        return Response("could not read frame", status=503, mimetype="text/plain")
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return Response("could not encode frame", status=500, mimetype="text/plain")
    return Response(buf.tobytes(), mimetype="image/jpeg")


@app.route("/health")
def health():
    cam = get_camera()
    if cam.isOpened():
        return Response("ok", mimetype="text/plain")
    return Response("camera not open", status=503, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
