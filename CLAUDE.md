# physics-open-content

A free-tier AI pipeline for generating open physics content — problem
libraries, figure code, format conversion — with deterministic verification.

## Hard rules — never violate

1. No Canvas data, no student work, no student names, IDs or scores ever
   enter this repo or any call made from it.
2. The Canvas token (`.canvas_env.sh`) is never present here in any form.
3. The provider free tiers used here are DATA-SHARING tiers: everything sent
   is trainable by the provider. Account separation from anything touching
   student data is structural, not a matter of care.
4. The Framework Grading Model and the Workshop-style activity structure stay
   OUT of this environment. Physics notation conventions are fine to use.
5. This repo is PUBLIC. Never commit credentials. Keys live only in GitHub
   repo secrets.

## How compute works

All model calls run in GitHub Actions on standard runners, which are free and
unlimited on public repositories. Nothing calls a model from the laptop.

- Key: repo secret `GEMINI_API_KEY`, sent as the `x-goog-api-key` header,
  never as a URL query parameter (it would appear in logged request lines).
- Workflows may commit back to `main` (`probe-models.yml` writes its report),
  so run `git pull --rebase` before committing locally.

## Layout

- `tools/list_models.py`, `tools/probe_models.py` — Gemini model listing / entitlement probe
- `tools/list_provider_models.py` — list OpenAI-compatible provider models (no quota used)
- `tools/check_quota.py` — remaining free quota -> `docs/quota.md` (Groq from
  rate-limit headers, one request per model; Gemini counted from today's batches)
- `tools/engines.py` + `tools/engines.json` — router: ordered engines per role
  (author, solver), falls over on daily quota / missing model / busy
- `tools/generate.py` — topic mode, or curriculum-gated request mode (`REQUEST=`)
- `tools/verify.py` — checks 1-5 always; 6-8 (curriculum, lexical, pedagogy)
  with `--request`, otherwise reported PARTIAL
- `tools/curriculum.py`, `tools/validate_curriculum.py`, `tools/check_rules.py`,
  `tools/prompt.py`, `tools/render.py` — curriculum layer (see
  `SPEC-curriculum-gating.md`)
- `curriculum/` — concept registry, calculus flags, representations, sequences
- `requests/` — committed request files; `requests/fixtures/` for CI
- `problems/*.json` — hand-checked records, self-tests, guards
- `candidates/<batch>/` — generated output awaiting human review; never
  auto-promoted to `problems/`
- `tests/` — unittest suite, golden prompt, curriculum fixture runner
- Workflows: `verify.yml` (CI), `generate.yml`, `probe-models.yml`,
  `list-provider-models.yml`, `check-quota.yml`, `smoke-test.yml`

## Providers

Gemini (`GEMINI_API_KEY`) and Groq (`GROQ_API_KEY`). One account per
provider, personal identity, never institutional. Limits are honored, never
evaded. Free Gemini models allow roughly 20 requests/day each; Groq about
1,000/day per model. Groq is behind Cloudflare: send a User-Agent. Mistral's
free plan no longer includes API keys (Nov 2026); GitHub Models is retired.

## Model entitlement (probed 2026-11-19, unbilled key)

- **Callable free:** `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`,
  `gemini-flash-lite-latest`, `gemini-3-flash-preview` (reasons before
  answering), `gemini-4-hydrogen` (most capable reachable free),
  `gemma-4-31b-it` (slow).
- **Billing required** (instant HTTP 429): `gemini-pro-latest`,
  `deep-research-*`, `gemini-omni-*`, `gemini-4-argon|carbon|neon`.
- **Retired** (404, closed to new users): all `gemini-2.5-*`.
- **Undetermined** (503 or timeout — retry, these are likely free):
  `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.7-flash`,
  `gemini-3.8-flash`, `gemini-flash-latest`, `gemma-4-26b-a4b-it`.
- Prefer explicit model names over `-latest` aliases, which can resolve to
  reasoning models and blow past timeouts.

## Verification principle

Generate symbolically, instantiate numerically. The model emits a symbolic
answer; SymPy does every arithmetic step, so model arithmetic errors are
structurally impossible. Model output is character- and identifier-whitelisted
before it reaches the parser.

Five checks: parse, non-triviality, dimensions, limiting cases, numeric.

Records flagged `"known_bad": true` are harness self-tests and MUST fail. A
verifier that has never rejected anything is not known to work. Equally, watch
for the opposite failure — rejecting correct physics — since nobody inspects
what gets discarded.

## Problem record schema

```json
{
  "id": "mech-001",
  "topic": "short description",
  "tier": "plug-and-chug | multi-step | interesting",
  "statement": "the problem as a student would read it",
  "symbols": {"v": {"desc": "launch speed", "unit": "m/s"}},
  "answer_expression": "SymPy-parseable, in declared symbols only",
  "answer_unit": "m",
  "given": {"v": "25"},
  "expected_value": 55.18,
  "limits": [{"symbol": "theta", "to": "0", "expect": "0"}]
}
```

## Current state

Working: verification harness (checks 1-8), multi-engine routing with
fallback, topic-mode and curriculum-gated generation with a blind-solver
cross-check, LaTeX/Canvas rendering. Spec milestones M0-M5 done.

Not done: M6 (populate `work-first` and the other sequence stubs); the
rotation/oscillation tail of `impulse-first` is provisional (`rotational-ke`
unplaced) — do not generate past `extended-work-energy` until it is fixed.
Checks 6 and 8 rely on the model's self-reported `requires` and
`trivial_if_available`; only the lexical check is independent of it.

Every false rejection found so far became a guard record or a regression
test. Keep doing that: when a correct problem is rejected, fix the harness
and add a guard.
