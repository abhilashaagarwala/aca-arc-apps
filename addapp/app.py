import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# Internal URL of the TinyLlama OpenAI-compatible service (set via env in the container app).
FACT_SERVICE_URL = os.environ.get("FACT_SERVICE_URL", "http://tinyllama-fact")
FACT_TIMEOUT = float(os.environ.get("FACT_TIMEOUT", "60"))

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
            box-shadow:0 10px 30px rgba(0,0,0,.4); width:min(460px,90vw); }}
    h1 {{ margin:0 0 1.5rem; font-size:1.5rem; }}
    label {{ display:block; margin:.75rem 0 .25rem; font-size:.9rem; color:#94a3b8; }}
    input {{ width:100%; padding:.6rem .75rem; border-radius:8px; border:1px solid #334155;
            background:#0f172a; color:#e2e8f0; font-size:1rem; box-sizing:border-box; }}
    button {{ margin-top:1.5rem; width:100%; padding:.7rem; border:0; border-radius:8px;
             background:#3b82f6; color:#fff; font-size:1rem; cursor:pointer; }}
    button:hover {{ background:#2563eb; }}
    .result {{ margin-top:1.5rem; padding:1rem; border-radius:8px; background:#064e3b;
              color:#6ee7b7; font-size:1.25rem; text-align:center; font-weight:600; }}
    .fact-label {{ margin-top:1.5rem; font-size:.8rem; color:#94a3b8;
                  text-transform:uppercase; letter-spacing:.05em; }}
    textarea {{ width:100%; margin-top:.4rem; padding:.75rem; border-radius:8px;
               border:1px solid #334155; background:#0f172a; color:#e2e8f0;
               font-size:.95rem; box-sizing:border-box; resize:vertical; min-height:90px;
               line-height:1.4; }}
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
      <button type="submit">Add &amp; get a fun fact</button>
    </form>
    {result}
    {fact}
  </div>
</body>
</html>"""


def get_fun_fact(number):
    """Ask the TinyLlama service for a one-sentence fun fact about the number."""
    prompt = (
        f"Tell me a single short, fun fact about the number {number}. "
        f"Respond with one sentence only."
    )
    try:
        resp = requests.post(
            f"{FACT_SERVICE_URL}/v1/chat/completions",
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
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        return f"(Could not reach the fact service: {exc})"


def render(a="", b="", result="", fact=""):
    result_block = f'<div class="result">{result}</div>' if result else ""
    fact_block = ""
    if fact:
        fact_block = (
            '<div class="fact-label">Fun fact about the sum</div>'
            f'<textarea readonly>{fact}</textarea>'
        )
    return PAGE.format(a=a, b=b, result=result_block, fact=fact_block)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        a = request.form.get("a", "")
        b = request.form.get("b", "")
        try:
            total = float(a) + float(b)
            if total.is_integer():
                total = int(total)
            fact = get_fun_fact(total)
            return render(a, b, f"{a} + {b} = {total}", fact)
        except ValueError:
            return render(a, b, "Please enter valid numbers.")
    return render()


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
