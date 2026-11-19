#!/usr/bin/env python3
"""Smoke test: confirm the Gemini API key works and report usable models.

Reads GEMINI_API_KEY from the environment. Sends the key as a header rather
than a URL query parameter so it can never appear in a logged request line.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("GEMINI_API_KEY is not set")

URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"

req = urllib.request.Request(URL, headers={"x-goog-api-key": API_KEY})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "replace")
    sys.exit(f"HTTP {e.code} from the models endpoint:\n{body}")

models = data.get("models", [])
usable = [
    m for m in models
    if "generateContent" in m.get("supportedGenerationMethods", [])
]

print(f"Key accepted. {len(models)} models visible; "
      f"{len(usable)} support generateContent.\n")

for m in sorted(usable, key=lambda m: m["name"]):
    name = m["name"].removeprefix("models/")
    print(f"  {name:45s} "
          f"in={m.get('inputTokenLimit', '?'):>9} "
          f"out={m.get('outputTokenLimit', '?'):>7}")
