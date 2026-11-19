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

- `tools/list_models.py` — enumerate models the key can see
- `tools/gen_once.py` — one generateContent call; `MODEL` env var selects it
- `tools/probe_models.py` — probe real entitlement; writes `docs/model-probe.md`
- `tools/verify.py` — deterministic verification harness
- `problems/*.json` — problem records
- `.github/workflows/` — `smoke-test.yml`, `probe-models.yml`, `verify.yml`

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

Working: smoke test, entitlement probe, verification harness.
Not yet built: the problem generator, multi-provider routing with fallback.

Open bugs in `tools/verify.py`, dimensions check — both cause the harness to
reject CORRECT physics:

1. Substituting units collapses sums. `m1` and `m2` both become `kilogram`,
   so `(m2 - m1)` evaluates to zero and the expression reads as dimensionless.
   Substitute distinct dummy coefficients times each unit instead.
2. Dimensional dependencies are compared by printed form. `Dimension(time)`
   and `Dimension(time, T)` are equal but print differently. Compare by
   dimension name.

Target: `verify.yml` green, with `mech-001` and `mech-002` passing all five
checks and `harness-selftest-001` failing on `numeric` alone.
