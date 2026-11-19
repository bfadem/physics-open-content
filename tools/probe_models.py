#!/usr/bin/env python3
"""Probe which Gemini models this key can actually call.

Visibility in the models list is not entitlement. This sends a minimal
generateContent request to each text-capable model and records the outcome.
HTTP 200 means callable, regardless of what came back.

Writes docs/model-probe.md and prints the same table.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("GEMINI_API_KEY is not set")

BASE = "https://generativelanguage.googleapis.com/v1beta"
HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

# Families that are not text-to-text; probing them tells us nothing useful.
SKIP = re.compile(
    r"(-tts|tts-|image|lyria|transcribe|nano-banana|robotics|computer-use)"
)

PROMPT = "Reply with the single word: ok"
PER_CALL_TIMEOUT = 40
PAUSE_BETWEEN_CALLS = 1.0


def get_models():
    req = urllib.request.Request(f"{BASE}/models?pageSize=200", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return [
        m["name"].removeprefix("models/")
        for m in data.get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]


def probe(model):
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 64},
    }
    req = urllib.request.Request(
        f"{BASE}/models/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=PER_CALL_TIMEOUT) as resp:
            data = json.load(resp)
        elapsed = time.monotonic() - start
        cands = data.get("candidates", [{}])
        reason = cands[0].get("finishReason", "?") if cands else "no-candidates"
        total = data.get("usageMetadata", {}).get("totalTokenCount", "?")
        return ("OK", f"{reason}, {total} tok", f"{elapsed:.1f}s")
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        try:
            msg = json.loads(e.read())["error"]["message"]
        except Exception:
            msg = "(unparsed error body)"
        msg = msg.split(". ")[0][:90]
        return (f"HTTP {e.code}", msg, f"{elapsed:.1f}s")
    except Exception as e:
        elapsed = time.monotonic() - start
        return ("ERROR", type(e).__name__, f"{elapsed:.1f}s")


models = get_models()
probed = [m for m in models if not SKIP.search(m)]
skipped = [m for m in models if SKIP.search(m)]

print(f"{len(models)} text-capable models listed; "
      f"probing {len(probed)}, skipping {len(skipped)} non-text.\n")

rows = []
for i, model in enumerate(sorted(probed), 1):
    status, detail, elapsed = probe(model)
    print(f"[{i:2d}/{len(probed)}] {model:42s} {status:10s} {elapsed:>6s}  {detail}")
    rows.append((model, status, elapsed, detail))
    time.sleep(PAUSE_BETWEEN_CALLS)

ok = [r for r in rows if r[1] == "OK"]
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

os.makedirs("docs", exist_ok=True)
with open("docs/model-probe.md", "w") as f:
    f.write("# Gemini model entitlement probe\n\n")
    f.write(f"Generated {stamp} from an unbilled API key.\n\n")
    f.write(f"**{len(ok)} of {len(probed)} probed models are callable.** ")
    f.write("HTTP 200 means callable; it says nothing about output quality.\n\n")
    f.write("| Model | Status | Latency | Detail |\n")
    f.write("|---|---|---|---|\n")
    for model, status, elapsed, detail in rows:
        f.write(f"| `{model}` | {status} | {elapsed} | {detail} |\n")
    f.write(f"\nSkipped as non-text: {', '.join(f'`{m}`' for m in sorted(skipped))}\n")

print(f"\n{len(ok)} of {len(probed)} callable. Wrote docs/model-probe.md")
