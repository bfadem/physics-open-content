#!/usr/bin/env python3
"""Report how much free quota is left today. Run in GitHub Actions only.

OpenAI-compatible providers (Groq): one minimal call per model named in
tools/engines.json, reading the x-ratelimit-* response headers. Each check
costs one request of that model's daily allowance and a handful of tokens.

Gemini: the API exposes no remaining-quota figure, and a test call would
spend a scarce daily request to learn very little. Instead, calls are
totalled from today's batch READMEs (candidates/*/README.md, batch ids are
UTC). Gemini daily quotas reset at midnight Pacific time. Calls made by
other workflows (probe-models, smoke-test) are not counted.

Writes docs/quota.md and prints the same.
"""
import datetime
import glob
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engines import CONFIG, _post  # noqa: E402

PACIFIC = ZoneInfo("America/Los_Angeles")
HEADERS = [("limit-requests", "requests/day"), ("remaining-requests", "left today"),
           ("reset-requests", "resets in"), ("limit-tokens", "tokens/min"),
           ("remaining-tokens", "tokens left this min")]

with open(CONFIG) as f:
    cfg = json.load(f)
engines = list(dict.fromkeys(cfg.get("author", []) + cfg.get("solver", [])))
now = datetime.datetime.now(datetime.timezone.utc)
lines = ["# Free quota remaining", "",
         f"Generated {now:%Y-%m-%d %H:%M} UTC by `tools/check_quota.py` "
         "(run the `check-quota` workflow to refresh).", ""]


def header(h, name):
    return (h or {}).get(f"x-ratelimit-{name}", "") if h else ""


# -- OpenAI-compatible providers: read rate-limit headers -------------------
for pname, spec in cfg["providers"].items():
    if spec["kind"] != "openai":
        continue
    models = [e.split(":", 1)[1] for e in engines if e.startswith(pname + ":")]
    key = os.environ.get(spec["key_env"])
    if not models:
        continue
    if not key:
        continue                      # provider not set up; nothing to report
    lines += [f"## {pname}", "",
              "Read from response headers after one minimal call per model "
              "(the check itself uses one request each).", "",
              "| model | status | " + " | ".join(t for _, t in HEADERS) + " |",
              "|---|---|" + "---|" * len(HEADERS)]
    for model in models:
        status, body, h = _post(
            f"{spec['base']}/chat/completions",
            {"model": model, "max_completion_tokens": 16,
             "messages": [{"role": "user", "content": "Reply with OK."}]},
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=60)
        st = "ok" if status == 200 else f"HTTP {status}"
        if status == 429:
            st = "rate-limited (429)"
        vals = [header(h, n) or "—" for n, _ in HEADERS]
        lines.append(f"| `{model}` | {st} | " + " | ".join(vals) + " |")
    lines.append("")

# -- Gemini: count today's calls from batch READMEs ---------------------------
gem = [e for e in engines if e.startswith("gemini:")]
if gem:
    midnight_pt = datetime.datetime.now(PACIFIC).replace(
        hour=0, minute=0, second=0, microsecond=0)
    since = midnight_pt.astimezone(datetime.timezone.utc)
    used = {e: 0 for e in gem}
    exhausted = set()
    batches = 0
    for readme in sorted(glob.glob("candidates/*/README.md")):
        bid = os.path.basename(os.path.dirname(readme))
        try:
            t = datetime.datetime.strptime(bid, "%Y%m%d-%H%M").replace(
                tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if t < since:
            continue
        batches += 1
        with open(readme, encoding="utf-8") as f:
            for m in re.finditer(r"^\| `(gemini:[^`]+)` \| [^|]* \| (\d+) \| [^|]* \| ([^|]*)\|",
                                 f.read(), re.M):
                label, calls, state = m.group(1), int(m.group(2)), m.group(3)
                used[label] = used.get(label, 0) + calls
                if "exhausted" in state:
                    exhausted.add(label)
    reset = (midnight_pt + datetime.timedelta(days=1)).astimezone(datetime.timezone.utc)
    lines += ["## gemini", "",
              f"The API reports no remaining quota, so this counts calls from "
              f"{batches} batch(es) since midnight Pacific ({since:%Y-%m-%d %H:%M} UTC); "
              f"next reset {reset:%Y-%m-%d %H:%M} UTC. Daily limits differ by model "
              "(the larger models have run out near 20; the lite models have "
              "exceeded 40) and are shown in Google AI Studio. Calls from other "
              "workflows are not counted, so these are lower bounds.", "",
              "| model | calls today (batches) | status |", "|---|---|---|"]
    for label in gem:
        status = ("exhausted today" if label in exhausted
                  else "not exhausted in any batch today")
        lines.append(f"| `{label.split(':', 1)[1]}` | {used[label]} | {status} |")
    lines.append("")

os.makedirs("docs", exist_ok=True)
with open("docs/quota.md", "w") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
