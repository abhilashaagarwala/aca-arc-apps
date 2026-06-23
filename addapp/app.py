import os
import time
import base64
import concurrent.futures
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# CPU fact service (ACA container app) and GPU fact service (plain k8s on the RTX 5060).
CPU_SERVICE_URL = os.environ.get("CPU_SERVICE_URL", os.environ.get("FACT_SERVICE_URL", "http://tinyllama-fact"))
GPU_SERVICE_URL = os.environ.get("GPU_SERVICE_URL", "http://tinyllama-gpu.gpu-workloads.svc.cluster.local")
# Camera snapshot service (plain k8s, camera namespace).
CAMERA_SERVICE_URL = os.environ.get("CAMERA_SERVICE_URL", "http://camera-stream.camera.svc.cluster.local")
FACT_TIMEOUT = float(os.environ.get("FACT_TIMEOUT", "90"))
CAMERA_TIMEOUT = float(os.environ.get("CAMERA_TIMEOUT", "15"))

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Add Two Numbers</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
           background:#0f172a; color:#e2e8f0; display:flex; min-height:100vh;
           align-items:center; justify-content:center; margin:0; }}
    .card {{ background:#1e293b; padding:2.5rem; border-radius:16px;
            box-shadow:0 10px 30px rgba(0,0,0,.4); width:min(520px,92vw); }}
    h1 {{ margin:0 0 1.5rem; font-size:1.5rem; }}
    label {{ display:block; margin:.75rem 0 .25rem; font-size:.9rem; color:#94a3b8; }}
    input {{ width:100%; padding:.6rem .75rem; border-radius:8px; border:1px solid #334155;
            background:#0f172a; color:#e2e8f0; font-size:1rem; box-sizing:border-box; }}
    button {{ margin-top:1.5rem; width:100%; padding:.7rem; border:0; border-radius:8px;
             background:#3b82f6; color:#fff; font-size:1rem; cursor:pointer; }}
    button:hover {{ background:#2563eb; }}
    .result {{ margin-top:1.5rem; padding:1rem; border-radius:8px; background:#064e3b;
              color:#6ee7b7; font-size:1.25rem; text-align:center; font-weight:600; }}
    .fact-label {{ margin-top:1.5rem; font-size:.8rem; color:#94a3b8; display:flex;
                  justify-content:space-between; text-transform:uppercase; letter-spacing:.05em; }}
    .fact-label .timing {{ color:#64748b; text-transform:none; letter-spacing:0; }}
    .cpu .fact-label {{ color:#fbbf24; }}
    .gpu .fact-label {{ color:#34d399; }}
    textarea {{ width:100%; margin-top:.4rem; padding:.75rem; border-radius:8px;
               border:1px solid #334155; background:#0f172a; color:#e2e8f0;
               font-size:.95rem; box-sizing:border-box; resize:vertical; min-height:80px;
               line-height:1.4; }}
    .cpu textarea {{ border-color:#78350f; }}
    .gpu textarea {{ border-color:#065f46; }}
    img.snapshot {{ width:100%; margin-top:.4rem; border-radius:8px; border:1px solid #334155; display:block; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Add Two Numbers</h1>
    <form method="post" action="/">
      <label for="a">First number</label>
      <input id="a" name="a" type="number" step="any" value="{a}" required>
      <label for="b">Second number</label>
      <input id="b" name="b" type="number" step="any" value="{b}" required>
      <button type="submit">Add &amp; get fun facts (CPU vs GPU)</button>
    </form>
    {result}
    {facts}
  </div>
</body>
</html>"""


def get_fun_fact(service_url, number):
    """Ask a TinyLlama service for a one-sentence fun fact. Returns (text, elapsed_seconds)."""
    prompt = (
        f"Tell me a single short, fun fact about the number {number}. "
        f"Respond with one sentence only."
    )
    start = time.time()
    try:
        resp = requests.post(
            f"{service_url}/v1/chat/completions",
            json={
                "model": "tinyllama",
                "messages": [
                    {"role": "system", "content": "You are a concise assistant that shares fun facts about numbers."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 80,
                "temperature": 0.7,
            },
            timeout=FACT_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text, time.time() - start
    except Exception as exc:  # noqa: BLE001
        return f"(Unavailable: {exc})", time.time() - start


def get_camera_snapshot():
    """Fetch a single JPEG frame from the camera service. Returns a data URI or None."""
    try:
        resp = requests.get(f"{CAMERA_SERVICE_URL}/snapshot", timeout=CAMERA_TIMEOUT)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:  # noqa: BLE001
        return None


def camera_block(data_uri):
    if data_uri:
        return (
            '<div class="fact-label"><span>Camera snapshot</span></div>'
            f'<img class="snapshot" src="{data_uri}" alt="camera snapshot">'
        )
    return (
        '<div class="fact-label"><span>Camera snapshot</span></div>'
        '<textarea readonly>(Camera unavailable)</textarea>'
    )


def fact_block(css_class, title, text, secs):
    timing = f"{secs:.1f}s" if secs else ""
    return (
        f'<div class="{css_class}">'
        f'<div class="fact-label"><span>{title}</span><span class="timing">{timing}</span></div>'
        f'<textarea readonly>{text}</textarea>'
        f'</div>'
    )


def render(a="", b="", result="", facts=""):
    result_block = f'<div class="result">{result}</div>' if result else ""
    return PAGE.format(a=a, b=b, result=result_block, facts=facts)


def get_all(number):
    """Query CPU fact, GPU fact, and camera snapshot in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_cpu = pool.submit(get_fun_fact, CPU_SERVICE_URL, number)
        f_gpu = pool.submit(get_fun_fact, GPU_SERVICE_URL, number)
        f_cam = pool.submit(get_camera_snapshot)
        return f_cpu.result(), f_gpu.result(), f_cam.result()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        a = request.form.get("a", "")
        b = request.form.get("b", "")
        try:
            total = float(a) + float(b)
            if total.is_integer():
                total = int(total)
            (cpu_text, cpu_secs), (gpu_text, gpu_secs), snapshot = get_all(total)
            facts = (
                fact_block("cpu", "CPU fact (ACA / TinyLlama)", cpu_text, cpu_secs)
                + fact_block("gpu", "GPU fact (RTX 5060 / TinyLlama)", gpu_text, gpu_secs)
                + camera_block(snapshot)
            )
            return render(a, b, f"{a} + {b} = {total}", facts)
        except ValueError:
            return render(a, b, "Please enter valid numbers.")
    return render()


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
