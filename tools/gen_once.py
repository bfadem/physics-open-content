#!/usr/bin/env python3
"""One generateContent call: confirm the free tier actually generates text."""
import json
import os
import sys
import urllib.error
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("GEMINI_API_KEY is not set")

MODEL = os.environ.get("MODEL", "gemini-flash-latest")

PROMPT = (
    "Give the range of a projectile launched from level ground with speed v "
    "at angle theta, ignoring air resistance. Reply with JSON only, in "
    'exactly this form: {"expression": "<SymPy-parseable expression in '
    'v, theta, g>"}'
)

url = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)
payload = {
    "contents": [{"parts": [{"text": PROMPT}]}],
    "generationConfig": {
        "temperature": 0,
        "responseMimeType": "application/json",
    },
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "replace")
    sys.exit(f"HTTP {e.code} calling {MODEL}:\n{body}")

candidates = data.get("candidates", [])
if not candidates:
    sys.exit(f"No candidates returned. Full response:\n"
             f"{json.dumps(data, indent=2)}")

parts = candidates[0].get("content", {}).get("parts")
if not parts:
    sys.exit(f"Candidate returned no parts (finishReason="
             f"{candidates[0].get('finishReason')}). Full response:\n"
             f"{json.dumps(data, indent=2)}")

text = parts[0].get("text", "")
usage = data.get("usageMetadata", {})

print(f"model:  {MODEL}")
print(f"output: {text.strip()}")
print(f"tokens: prompt={usage.get('promptTokenCount')} "
      f"output={usage.get('candidatesTokenCount')} "
      f"total={usage.get('totalTokenCount')}")
