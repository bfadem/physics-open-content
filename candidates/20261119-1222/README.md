# Batch 20261119-1222

- Requested 5, attempted 5, **accepted 3**, rejected 2, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `groq:openai/gpt-oss-120b` | author, solver | 5 | 10241 | ready |
| `gemini:gemini-4-hydrogen` | author | 0 | 0 | ready |
| `gemini:gemini-3-flash-preview` | author, solver | 1 | 2295 | exhausted (gemini:gemini-3-flash-preview: daily quota reached [GenerateRequestsPerDayPerPro) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 4 | 879 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- agreement: 1
- verify: 1

## Accepted (awaiting human review)

- `gen-20261119-1222-003` [interesting] Escape speed from a spherical planet: `sqrt(2*G*M/R)` (groq:openai/gpt-oss-120b / gemini:gemini-3.5-flash-lite)
- `gen-20261119-1222-004` [plug-and-chug] Conservation of momentum in a perfectly inelastic collision: `(m1*u1 + m2*u2)/(m1 + m2)` (groq:openai/gpt-oss-120b / gemini:gemini-3.5-flash-lite)
- `gen-20261119-1222-005` [multi-step] First law for a two‑step process of an ideal gas: `n*C_v*(T_f - T_i) + n*R_gas*T_f*log(V_f/V_i)` (groq:openai/gpt-oss-120b / gemini:gemini-3.5-flash-lite)

## Rejected

- `gen-20261119-1222-001` [verify] Conical pendulum angular speed — ValueError: limit L->infinity: unknown identifiers: ['infinity']
- `gen-20261119-1222-002` [agreement] spring potential energy problem — ValueError: author and blind solver disagree: differ at a test point: 0.489851+0j vs 1.60677+0j
