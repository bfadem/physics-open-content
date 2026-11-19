# Batch 20261119-1802

- Request: `requests/2026-11-19_impulse-first_kinetic-energy.json` (copied to `request.json`)
- State: 28 concepts covered through `kinetic-energy`, 17 forbidden; calculus ['graphical-area', 'graphical-slope', 'trig-decomposition']; representations ['free-body-diagram', 'momentum-vector-diagram']
- Targets: work done by a constant force, work as the dot product of force and displacement, power as the rate of doing work, work done by a variable force, kinetic energy
- Checks: 1-8 (curriculum, lexical, pedagogy included)
- Requested 15, attempted 15, **accepted 5**, rejected 10, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `gemini:gemini-4-hydrogen` | author | 0 | 0 | exhausted (gemini:gemini-4-hydrogen: daily quota reached [GenerateRequestsPerDayPerProjectP) |
| `groq:openai/gpt-oss-120b` | author, solver | 6 | 26292 | ready |
| `gemini:gemini-3-flash-preview` | author, solver | 2 | 4228 | exhausted (gemini:gemini-3-flash-preview: daily quota reached [GenerateRequestsPerDayPerPro) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 0 | 0 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `groq:qwen/qwen3.8-27b` | solver | 6 | 1014 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- agreement: 1
- curriculum-map: 7
- dedupe: 1
- verify: 1

## Accepted (awaiting human review)

- `gen-20261119-1802-001` [plug-and-chug] Work done by a constant horizontal force: `F_const*d` (groq:openai/gpt-oss-120b / gemini:gemini-3-flash-preview)
- `gen-20261119-1802-003` [plug-and-chug] Power from constant force and constant speed: `F*v` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)
- `gen-20261119-1802-004` [plug-and-chug] Work done by a linearly increasing force: `0.5*k*x_max**2` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)
- `gen-20261119-1802-005` [plug-and-chug] Kinetic energy of a moving mass: `0.5*m*v**2` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)
- `gen-20261119-1802-014` [interesting] Kinetic energy from constant angled pull: `F*cos(theta)*d` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)

## Rejected

- `gen-20261119-1802-002` [verify] Work as dot product with an angle — ValueError: limit theta->1.5707963268: got -5.10341196725696e-12*F*d, expected 0
- `gen-20261119-1802-006` [curriculum-map] Constant force work and power — unknown concept label(s): ['resolve a vector into components using sine and cosine']
- `gen-20261119-1802-007` [curriculum-map] Variable force work and kinetic‑energy ratio — problem has no curriculum block
- `gen-20261119-1802-008` [curriculum-map] Work by a constant force at an angle — unknown concept label(s): ['resolve a vector into components using sine and cosine']
- `gen-20261119-1802-009` [dedupe] Power from a constant force moving at constant speed — ValueError: duplicate of gen-20261119-1802-003
- `gen-20261119-1802-010` [curriculum-map] Work done by a linearly increasing force — problem has no curriculum block
- `gen-20261119-1802-011` [curriculum-map] Average power from a constant horizontal force — problem has no curriculum block
- `gen-20261119-1802-012` [agreement] Block pulled by a constant horizontal force — ValueError: author and blind solver disagree: differ at a test point: 1.18338+0j vs 1.16254+0j
- `gen-20261119-1802-013` [curriculum-map] Cart pulled by a linearly increasing force — problem has no curriculum block
- `gen-20261119-1802-015` [curriculum-map] Work done by a linearly increasing spring force — problem has no curriculum block
