#!/usr/bin/env python3
"""List the models each configured OpenAI-compatible provider offers.

Listing costs no generation quota. Providers come from tools/engines.json and
are included only when their key secret is present. Writes
docs/provider-models.md and prints the same.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engines import CONFIG, _get  # noqa: E402

with open(CONFIG) as f:
    cfg = json.load(f)

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines = ["# Provider model listings", "",
         f"Generated {now} by `tools/list_provider_models.py`. "
         "A listing shows what a key can see, not what it can call free; "
         "the router disables any engine that refuses a call.", ""]
configured = set(cfg.get("author", []) + cfg.get("solver", []))

for name, spec in cfg["providers"].items():
    if spec["kind"] != "openai":
        continue
    key = os.environ.get(spec["key_env"])
    if not key:
        lines += [f"## {name}", "", f"_No `{spec['key_env']}` secret; skipped._", ""]
        continue
    try:
        data = _get(f"{spec['base']}/models", {"Authorization": f"Bearer {key}"})
    except Exception as e:
        lines += [f"## {name}", "", f"Listing failed: {e}", ""]
        continue
    models = sorted(data.get("data", []), key=lambda m: m.get("id", ""))
    lines += [f"## {name} ({len(models)} models)", "",
              "| id | owned by | context | active | in engines.json |",
              "|---|---|---|---|---|"]
    for m in models:
        mid = m.get("id", "")
        lines.append(f"| `{mid}` | {m.get('owned_by', '')} | "
                     f"{m.get('context_window', '')} | {m.get('active', '')} | "
                     f"{'yes' if f'{name}:{mid}' in configured else ''} |")
    lines.append("")

os.makedirs("docs", exist_ok=True)
with open("docs/provider-models.md", "w") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
