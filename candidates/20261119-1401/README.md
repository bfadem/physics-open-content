# Batch 20261119-1401

- Requested 5, attempted 5, **accepted 3**, rejected 2, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `groq:openai/gpt-oss-120b` | author, solver | 5 | 9604 | ready |
| `gemini:gemini-4-hydrogen` | author | 0 | 0 | ready |
| `gemini:gemini-3-flash-preview` | author, solver | 2 | 14629 | exhausted (gemini:gemini-3-flash-preview: daily quota reached [GenerateRequestsPerDayPerPro) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 0 | 0 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `groq:qwen/qwen3.8-27b` | solver | 3 | 556 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- agreement: 1
- dedupe: 1

## Accepted (awaiting human review)

- `gen-20261119-1401-001` [plug-and-chug] magnetic force on a moving charge: `q*v*B*sin(theta)` (groq:openai/gpt-oss-120b / gemini:gemini-3-flash-preview)
- `gen-20261119-1401-002` [multi-step] Faraday's law and motional emf for a sliding rectangular loop: `B*h*v` (groq:openai/gpt-oss-120b / gemini:gemini-3-flash-preview)
- `gen-20261119-1401-003` [interesting] period of a conical pendulum: `2*pi*sqrt(L*cos(theta)/g)` (groq:openai/gpt-oss-120b / groq:qwen/qwen3.8-27b)

## Rejected

- `gen-20261119-1401-004` [dedupe] Conical pendulum period — ValueError: duplicate of gen-20261119-1401-003
- `gen-20261119-1401-005` [agreement] Maximum speed of a mass‑spring oscillator — ValueError: author and blind solver disagree: differ at a test point: 0.359883+0j vs 0.67388+0j
