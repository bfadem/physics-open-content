# Batch 20261119-1810

- Request: `requests/2026-11-19_impulse-first_kinetic-energy.json` (copied to `request.json`)
- State: 28 concepts covered through `kinetic-energy`, 17 forbidden; calculus ['graphical-area', 'graphical-slope', 'trig-decomposition']; representations ['free-body-diagram', 'momentum-vector-diagram']
- Targets: work done by a constant force, work as the dot product of force and displacement, power as the rate of doing work, work done by a variable force, kinetic energy
- Checks: 1-8 (curriculum, lexical, pedagogy included)
- Requested 15, attempted 15, **accepted 12**, rejected 3, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `gemini:gemini-4-hydrogen` | author | 1 | 12469 | exhausted (gemini:gemini-4-hydrogen: daily quota reached [GenerateRequestsPerDayPerProjectP) |
| `groq:openai/gpt-oss-120b` | author, solver | 4 | 1437 | disabled (groq:openai/gpt-oss-120b: HTTP 400: {"error":{"message":"Failed to generate JSON) |
| `gemini:gemini-3-flash-preview` | author, solver | 3 | 5835 | exhausted (gemini:gemini-3-flash-preview: daily quota reached [GenerateRequestsPerDayPerPro) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 2 | 6125 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `groq:qwen/qwen3.8-27b` | solver | 6 | 1207 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- agreement: 1
- curriculum-map: 2

## Accepted (awaiting human review)

- `gen-20261119-1810-001` [plug-and-chug] work done by a constant force: `F_p * d` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1810-002` [plug-and-chug] work as the dot product of force and displacement: `F_t * d * cos(theta)` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1810-003` [plug-and-chug] work as the dot product of force and displacement: `F_x * d_x + F_y * d_y` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1810-004` [plug-and-chug] power as the rate of doing work: `W_m / t_m` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1810-005` [plug-and-chug] power as the rate of doing work: `W_req / P_eng` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1810-006` [plug-and-chug] work done by a variable force: `(F_1 + F_2) * d / 2` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1810-007` [plug-and-chug] kinetic energy: `m * v^2 / 2` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1810-008` [multi-step] work done by a constant force: `F * d * cos(theta) - f * d` (gemini:gemini-3.5-flash-lite / groq:qwen/qwen3.8-27b)
- `gen-20261119-1810-009` [multi-step] work as the dot product of force and displacement: `Fx * dx + Fy * dy` (gemini:gemini-3.5-flash-lite / groq:qwen/qwen3.8-27b)
- `gen-20261119-1810-010` [multi-step] power as the rate of doing work: `F * v` (gemini:gemini-3.5-flash-lite / groq:qwen/qwen3.8-27b)
- `gen-20261119-1810-012` [multi-step] kinetic energy: `F * d` (gemini:gemini-3.5-flash-lite / groq:qwen/qwen3.8-27b)
- `gen-20261119-1810-013` [multi-step] work done by a constant force and kinetic energy: `(F - f) * d` (gemini:gemini-3.5-flash-lite / groq:qwen/qwen3.8-27b)

## Rejected

- `gen-20261119-1810-011` [curriculum-map] work done by a variable force — unknown concept label(s): ['work done by a variable function']
- `gen-20261119-1810-014` [agreement] Power delivered by a constant force on a cart accelerating from rest — ValueError: author and blind solver disagree: differ at a test point: 0.629818+0j vs 1.25964+0j
- `gen-20261119-1810-015` [curriculum-map] Work done by a variable spring force over a displacement — unknown representation label(s): ['read an accumulated quantity as the area under a graph']
