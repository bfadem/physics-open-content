# Free quota remaining

Generated 2026-11-20 02:41 UTC by `tools/check_quota.py` (run the `check-quota` workflow to refresh).

## groq

Read from response headers after one minimal call per model (the check itself uses one request each).

| model | status | requests/day | left today | resets in | tokens/min | tokens left this min |
|---|---|---|---|---|---|---|
| `openai/gpt-oss-120b` | ok | 1000 | 999 | 1m26.4s | 8000 | 7909 |
| `qwen/qwen3.8-27b` | ok | 1000 | 999 | 1m26.4s | 8000 | 7968 |
| `openai/gpt-oss-20b` | ok | 1000 | 999 | 1m26.4s | 8000 | 7909 |

## gemini

The API reports no remaining quota, so this counts calls from 10 batch(es) since midnight Pacific (2026-11-19 08:00 UTC); next reset 2026-11-20 08:00 UTC. Daily limits differ by model (the larger models have run out near 20; the lite models have exceeded 40) and are shown in Google AI Studio. Calls from other workflows are not counted, so these are lower bounds.

| model | calls today (batches) | status |
|---|---|---|
| `gemini-4-hydrogen` | 3 | exhausted today |
| `gemini-3-flash-preview` | 19 | exhausted today |
| `gemini-3.5-flash-lite` | 41 | not exhausted in any batch today |
| `gemma-4-31b-it` | 0 | not exhausted in any batch today |
| `gemini-3.1-flash-lite` | 20 | not exhausted in any batch today |
