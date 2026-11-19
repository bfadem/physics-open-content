# Batch 20261119-1508

- Request: `requests/2026-11-19_impulse-first_impulse-momentum-theorem.json` (copied to `request.json`)
- State: 16 concepts covered through `impulse-momentum-theorem`, 29 forbidden; calculus ['graphical-area', 'graphical-slope', 'trig-decomposition']; representations ['free-body-diagram']
- Targets: the impulse-momentum theorem: impulse equals change in momentum
- Checks: 1-8 (curriculum, lexical, pedagogy included)
- Requested 10, attempted 10, **accepted 8**, rejected 2, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `gemini:gemini-4-hydrogen` | author | 2 | 27945 | exhausted (gemini:gemini-4-hydrogen: daily quota reached [GenerateRequestsPerDayPerProjectP) |
| `groq:openai/gpt-oss-120b` | author, solver | 6 | 6519 | ready |
| `gemini:gemini-3-flash-preview` | author, solver | 4 | 3048 | exhausted (gemini:gemini-3-flash-preview: daily quota reached [GenerateRequestsPerDayPerPro) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 0 | 0 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `groq:qwen/qwen3.8-27b` | solver | 1 | 222 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- agreement: 2

## Accepted (awaiting human review)

- `gen-20261119-1508-001` [plug-and-chug] final speed from impulse starting from rest: `J_0/m` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1508-002` [plug-and-chug] average force during a rebound impact: `m*(v_i + v_f)/dt` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1508-003` [plug-and-chug] time interval for a given momentum change: `(p_f - p_i)/F` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1508-004` [plug-and-chug] mass from impulse and change in speed: `J_0/(v_f - v_i)` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261119-1508-005` [plug-and-chug] magnitude of impulse for a right-angle turn: `m*sqrt(v_i^2 + v_f^2)` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1508-006` [plug-and-chug] initial speed before a braking impulse: `v_f + F_avg*dt/m` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1508-009` [multi-step] two-dimensional impulse and projectile launch from a table: `sqrt(2*h/g)*sqrt(v_0^2 + 2*v_0*F_a*t_c*cos(theta)/m + F_a^2*t_c^2/m^2)` (gemini:gemini-4-hydrogen / groq:openai/gpt-oss-120b)
- `gen-20261119-1508-010` [interesting] minimum stopping time with force limit: `m*(v_i - v_f)/F_max` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)

## Rejected

- `gen-20261119-1508-007` [agreement] vertical bounce and average normal force — ValueError: unknown identifiers: ['h1', 'h2']
- `gen-20261119-1508-008` [agreement] time-varying force pulse followed by kinetic friction — ValueError: unknown identifiers: ['t1', 't2']
