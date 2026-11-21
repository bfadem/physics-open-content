# Specification: Curriculum-Gated Problem Generation

Status: M0-M5 implemented and green in CI; M6 outstanding (§9)
Extends: `CLAUDE.md` (hard rules, verification principle, problem record schema)
Audience: Claude Code working in this repo

---

## 1. Purpose

The generator must produce problems that a student **can actually solve at a
specific point in a specific course**. Topic tags cannot express this. "A
conservation of momentum problem" covers both a stick-together collision
(solvable with one equation) and a 1-D elastic collision (needs a second
relation from kinetic energy). If the course has not reached kinetic energy,
the second is unsolvable and must not be generated.

This specification adds a **curriculum state** layer: an explicit set of
concepts and inference tools the student currently has, against which every
generated problem is checked.

Two independent gates, both of which move during a term:

1. **Concept gate** — a cursor into an ordered sequence of physics concepts.
2. **Calculus gate** — a set of mathematical capability flags.

Admissibility is the conjunction of both.

---

## 2. Hard rules specific to this layer

These extend, and do not replace, the five hard rules in `CLAUDE.md`.

**R1. Sequence files contain concept IDs and ordering only.** No unit numbers,
section numbers, chapter numbers, activity numbers, unit titles, publisher
names, textbook titles, course codes, or institution names. Not in file
contents, not in filenames, not in comments, not in commit messages.

**R2. No provenance in this repo.** Where a sequence ordering came from is not
recorded here in any form. A sequence is named for its own structural logic
(§5.2), never for its source.

**R3. Nothing but explicit sets reaches a provider.** The prompt carries a
literal list of covered concept IDs and a literal list of forbidden concept
IDs. It never carries a sequence name, a cursor name, or any text describing a
course. Sequence names exist for local readability and must be stripped during
prompt construction.

**R4. This extends rule 4 of `CLAUDE.md`, which keeps Workshop-style activity
structure out of this environment.** A bare ordering of standard physics
concepts is permitted under R1 and R2. The pedagogical apparatus — activity
sequencing, predict/observe/reconcile structure, the Framework Grading Model —
remains excluded.

A `tools/check_rules.py` script enforces R1 mechanically: it scans
`curriculum/` for a denylist of patterns (`\d+\.\d+`, `[Uu]nit \d`,
`[Cc]hapter \d`, `[Mm]odule \d`, `[Aa]ctivity`, any all-caps acronym of four or more letters
(`\b[A-Z]{4,}\b`, with JSON and ASCII exempt), `PHY-?\d`) and fails
CI on a match. Add it to `verify.yml`.

---

## 3. Data model

All curriculum files are JSON, matching the repo's existing use of JSON for
`problems/`. Two-space indent. Keys in the order given below.

### 3.1 `curriculum/concepts.json`

The concept registry. Flat object keyed by concept ID.

```json
{
  "momentum-conservation-1d": {
    "label": "conservation of linear momentum in one dimension",
    "requires": ["momentum-definition", "newton-3rd"],
    "lexical_markers": [
      "conservation of momentum",
      "momentum is conserved",
      "total momentum"
    ]
  }
}
```

- `id` (the key) — kebab-case, stable, never renamed once referenced by a
  committed problem record.
- `label` — lowercase prose, used in prompt text. This is what the model sees;
  it must be ordinary physics vocabulary.
- `requires` — concept IDs this one depends on. These edges form the DAG.
  A sequence is valid only if it is a topological sort of this DAG (§4.2).
- `lexical_markers` — surface strings that betray this concept in a problem
  statement. Used by the lexical check (§6.3) to reject a stem that leaks an
  uncovered concept. Include symbol spellings where they are distinctive
  (`"KE"`, `"1/2 m v^2"`). Omit markers so generic they would false-positive
  (`"energy"` alone is too broad; `"kinetic energy"` is right).

`lexical_markers` must be complete for every concept in the energy and
momentum threads before the gate is trusted. For kinematics and forces, which
are covered early in every sequence, markers matter less and may be filled in
later.

### 3.2 `curriculum/calculus.json`

```json
{
  "flags": {
    "trig-decomposition": "resolve a vector into components using sine and cosine",
    "graphical-slope":    "read a rate of change as the slope of a graph",
    "graphical-area":     "read an accumulated quantity as the area under a graph",
    "derivative-analytic": "differentiate a function symbolically",
    "integral-analytic":   "integrate a function symbolically"
  },
  "presets": {
    "algebra-trig":        ["trig-decomposition"],
    "graphical":           ["trig-decomposition", "graphical-slope", "graphical-area"],
    "calc-coreq-early":    ["trig-decomposition", "graphical-slope", "graphical-area"],
    "calc-coreq-mid":      ["trig-decomposition", "graphical-slope", "graphical-area", "derivative-analytic"],
    "calc-coreq-late":     ["trig-decomposition", "graphical-slope", "graphical-area", "derivative-analytic", "integral-analytic"],
    "full-calculus":       ["trig-decomposition", "graphical-slope", "graphical-area", "derivative-analytic", "integral-analytic"]
  }
}
```

**Flags, not an ordinal ladder.** Courses do not nest. A lab-centered course
reaches `graphical-area` early and `integral-analytic` late or never; an
algebra-based course has `graphical-slope` and no derivatives at all. An
ordinal level would force false nesting and silently misgate.

`graphical-area` matters disproportionately: it makes variable-force work
available with no calculus, so work-done-stretching-a-spring problems are
legal well before symbolic integration arrives.

Presets are a local convenience. The expander resolves them to a flag set;
only the flag set is used downstream.

### 3.3 `curriculum/representations.json`

Representations are gated like concepts — a problem that asks for an energy
bar chart is inadmissible until that representation has been introduced,
independent of which concepts are covered.

```json
{
  "free-body-diagram": {"label": "free-body diagram"},
  "motion-diagram":    {"label": "motion diagram"},
  "graph-vt":          {"label": "velocity-versus-time graph"},
  "energy-bar-chart":  {"label": "energy bar chart"},
  "momentum-vector-diagram": {"label": "momentum vector diagram"}
}
```

Most sequences will cover few of these. The registry exists so the field is
not silently ignored.

### 3.4 `curriculum/sequences/<name>.json`

```json
{
  "name": "impulse-first",
  "description": "Momentum and collisions are developed from Newton's laws before any energy concept; elastic collisions are deferred until kinetic and potential energy exist.",
  "order": ["measurement-uncertainty", "position-velocity-graphical", "..."],
  "representations_at": {
    "free-body-diagram": "newton-2nd",
    "momentum-vector-diagram": "momentum-conservation-2d"
  },
  "calculus_hint": {
    "work-variable-force": {"any_of": ["graphical-area", "integral-analytic"]}
  }
}
```

- `order` — the full ordered concept list. Every ID must exist in
  `concepts.json`.
- `representations_at` — maps a representation to the concept at which it
  becomes available. Expanded alongside the concept cursor.
- `calculus_hint` — advisory, for authoring and for prompt text. The binding
  requirement lives on the problem record (§6.2).

### 3.5 Request files: `requests/<YYYY-MM-DD>_<sequence>_<cursor>.json`

Filename example: `requests/2026-11-19_impulse-first_impulse-momentum-theorem.json`

```json
{
  "sequence": "impulse-first",
  "cursor": "impulse-momentum-theorem",
  "calculus": "graphical",
  "target_concepts": ["impulse-momentum-theorem"],
  "tiers": {"plug-and-chug": 6, "multi-step": 3, "interesting": 1},
  "count": 10,
  "model": "gemini-4-hydrogen"
}
```

`cursor` names the **last covered** concept, inclusive. `calculus` accepts
either a preset name or a literal flag array. `target_concepts` is what the
problems should exercise; it must be a subset of the covered set, and the
expander rejects the request otherwise.

Request files are committed — they are the reproducible record of what was
asked for. They contain a sequence name, which is permitted in the repo under
R1 (the name is structural) but is stripped before any prompt is built (R3).

---

## 4. The curriculum module

### 4.1 `tools/curriculum.py`

Loader and expander. No model calls, no network, fully unit-testable.

```
load_concepts()                  -> dict
load_calculus()                  -> dict
load_representations()           -> dict
load_sequence(name)              -> dict
expand(sequence, cursor, calculus) -> State
```

`State` is a frozen dataclass:

```python
@dataclass(frozen=True)
class State:
    covered: frozenset[str]          # concept IDs at or before cursor
    forbidden: frozenset[str]        # concept IDs after cursor, in this sequence
    calculus: frozenset[str]         # resolved capability flags
    representations: frozenset[str]  # available representations
    cursor: str
    sequence_name: str               # local only; never serialized into a prompt
```

`forbidden` is the tail of the sequence, computed explicitly rather than left
implicit as "everything not covered." A free-tier model will reach for the
standard treatment unless given a literal denylist, and the lexical check
(§6.3) needs the list to scan against.

### 4.2 Validation — `tools/validate_curriculum.py`

Run in CI. Fails on any of:

1. A sequence references a concept ID absent from `concepts.json`.
2. `concepts.json` `requires` edges contain a cycle.
3. A sequence is **not a topological sort** of the DAG — i.e. some concept
   appears before one of its own prerequisites. This catches ordering mistakes
   automatically and is the main reason to maintain the DAG at all.
4. A `representations_at` value is not a concept in that sequence's `order`.
5. A `calculus_hint` key is not in that sequence's `order`, or a flag named is
   absent from `calculus.json`.
6. R1 denylist match anywhere under `curriculum/` (delegates to
   `tools/check_rules.py`).

---

## 5. Sequences

### 5.1 `impulse-first` — populate this one first

Verified at concept granularity. Momentum and collisions complete before any
energy concept appears; the solvable elastic collision is deferred until after
kinetic energy, gravitational potential energy, and mechanical energy
conservation.

```
measurement-uncertainty
position-velocity-graphical
constant-acceleration
newton-1st
newton-2nd
free-fall
projectile-motion
universal-gravitation
normal-force
tension
friction-static-kinetic
inclined-plane
uniform-circular-dynamics
momentum-definition
impulse
impulse-momentum-theorem
newton-3rd
momentum-conservation-1d
inelastic-collision-1d
center-of-mass
momentum-conservation-2d
inelastic-collision-2d
work-constant-force
work-dot-product
power
spring-force-hookes-law
work-variable-force
kinetic-energy
work-energy-theorem
conservative-vs-nonconservative
gravitational-pe
mechanical-energy-conservation
elastic-pe
elastic-collision-1d
thermal-energy-loss
extended-work-energy
angular-kinematics
torque
rotational-inertia
newton-2nd-rotational
cross-product
angular-momentum
angular-momentum-conservation
simple-harmonic-motion
pendulum
```

Four properties of this ordering that a model will get wrong unless the
forbidden list is explicit:

- `newton-3rd` arrives **inside the momentum thread**, after `impulse`. Any
  problem needing the third law is inadmissible through the whole force
  section preceding it.
- `impulse` and `impulse-momentum-theorem` precede
  `momentum-conservation-1d`. There is a real window where impulse problems
  are legal and conservation problems are not.
- `work-constant-force`, `work-dot-product`, `power`, and
  `work-variable-force` all precede `kinetic-energy`. A large pool of
  work-only problems — including the spring integral — is available before the
  work-energy theorem exists.
- `extended-work-energy` and `thermal-energy-loss` are last. Friction-as-lost-
  energy problems are gated later than almost everything else.

**Open item.** The rotation and oscillation tail (`angular-kinematics` through
`pendulum`) is provisional. `rotational-ke` is not yet placed and probably
belongs between `rotational-inertia` and `cross-product`. Verify before
generating against any cursor past `extended-work-energy`.

### 5.2 Other sequences — stubs with `order: []`

Create the files so the registry shape is fixed; populate later.

| File | Structural logic |
|---|---|
| `work-first.json` | work → kinetic energy → work-energy theorem → potential energy → mechanical energy → then momentum and collisions. The mainstream textbook order. |
| `energy-principle-first.json` | energy introduced as a fundamental conservation principle early, before detailed force analysis. |
| `conservation-unified.json` | momentum and energy taught together as one conservation-laws unit; elastic collisions available almost immediately. |
| `transfer-model.json` | energy as transfer between storage modes; work is transfer, friction produces internal energy. Leans on `energy-bar-chart`, so `representations_at` matters here. |

Names describe the ordering's own defining choice. Add a numeric suffix
(`work-first-2`) only to disambiguate two sequences sharing a structure.

---

## 6. Problem records and verification

### 6.1 Schema extension

The existing record schema in `CLAUDE.md` gains one object. All other fields
are unchanged.

```json
{
  "id": "mom-impulse-001",
  "topic": "impulse delivered to a struck ball",
  "tier": "plug-and-chug",
  "statement": "...",
  "symbols": {"m": {"desc": "ball mass", "unit": "kg"}},
  "answer_expression": "m*(v_f - v_i)",
  "answer_unit": "kg*m/s",
  "given": {"m": "0.145", "v_f": "38", "v_i": "-40"},
  "expected_value": 11.31,
  "limits": [{"symbol": "v_f", "to": "v_i", "expect": "0"}],

  "curriculum": {
    "sequence": "impulse-first",
    "cursor": "impulse-momentum-theorem",
    "requires": ["momentum-definition", "impulse", "impulse-momentum-theorem"],
    "intended_path": "impulse-momentum-theorem",
    "trivial_if_available": [],
    "representations": [],
    "calculus_all_of": ["trig-decomposition"],
    "calculus_any_of": []
  }
}
```

### 6.2 Field semantics

- `requires` — every concept needed to **solve** the problem. The distinction
  that matters: a problem can be *stated* entirely in covered vocabulary and
  still require an uncovered method. `requires` describes the solution, not
  the wording.
- `intended_path` — the concept the problem is meant to exercise. Must be in
  `requires` and in `covered`.
- `trivial_if_available` — concepts that, **if covered**, give a shortcut that
  defeats the problem's purpose. A block on a straight frictionless incline
  asked as an energy problem lists `["newton-2nd", "constant-acceleration"]`,
  because with those available the force method is cleaner and the energy
  practice is wasted. A curved track lists nothing, because no covered
  alternative solves it. This is how the spec captures that an ordering
  changes which problems are *pedagogically meaningful*, not merely which are
  legal.
- `calculus_all_of` — every flag required.
- `calculus_any_of` — at least one required. Non-empty where a problem admits
  two routes: variable-force work needs
  `{"any_of": ["graphical-area", "integral-analytic"]}`.
- `representations` — representations the problem asks the student to produce
  or read.

### 6.3 New verification checks

`tools/verify.py` currently runs five checks: parse, non-triviality,
dimensions, limiting cases, numeric. Add three, named for their failure
reason so `expect_fail` can target them:

**6. `curriculum`** — structural admissibility. Fails if any of:
- `requires` ⊄ `State.covered`
- `requires` ∩ `State.forbidden` ≠ ∅
- `intended_path` ∉ `requires`, or ∉ `State.covered`
- `representations` ⊄ `State.representations`
- `calculus_all_of` ⊄ `State.calculus`
- `calculus_any_of` non-empty and disjoint from `State.calculus`

**7. `lexical`** — vocabulary leak. For every concept in `State.forbidden`,
scan `statement` and every `symbols[*].desc` for that concept's
`lexical_markers`, case-insensitive, on word boundaries. Any hit fails.
This is the check that stops an uncovered concept appearing in the problem's
wording even when the declared `requires` looks clean — the common failure
mode when a weak model drifts toward the standard treatment.

**8. `pedagogy`** — shortcut detection. Fails if any concept in
`trivial_if_available` is in `State.covered`. Keep this a hard failure rather
than a warning; a warning in a batch pipeline that nobody reads is not a
check.

Checks 6–8 require a `State`, so `verify.py` gains a `--request` argument
naming the request file whose state the records were generated against. When
`--request` is omitted, checks 6–8 are skipped and the run is reported as
`partial`, never as `pass`.

### 6.4 Harness self-tests — mandatory

The repo's existing principle holds: a verifier that has never rejected
anything is not known to work, and a verifier that rejects correct physics is
worse. Both directions need fixtures.

Add to `problems/curriculum-selftests.json`, all with `"known_bad": true`:

| id | must fail on | construction |
|---|---|---|
| `ct-selftest-001` | `curriculum` | 1-D elastic collision declaring `requires: [..., "elastic-collision-1d"]` against a cursor of `impulse-momentum-theorem` |
| `ct-selftest-002` | `lexical` | momentum-only problem whose statement says "find the kinetic energy lost", with `requires` listing only covered concepts — the declared set is clean, the wording leaks |
| `ct-selftest-003` | `pedagogy` | straight frictionless incline asked as an energy problem, `trivial_if_available: ["newton-2nd", "constant-acceleration"]`, against a cursor past `mechanical-energy-conservation` |
| `ct-selftest-004` | `curriculum` | variable-force spring-work problem with `calculus_any_of: ["graphical-area", "integral-analytic"]` against the `algebra-trig` preset |

Add to `problems/false-rejection-guards.json`, which must **pass** all eight
checks:

| id | guards against |
|---|---|
| `ct-guard-001` | a legal impulse problem at cursor `impulse-momentum-theorem` — rejecting this means the gate is too tight |
| `ct-guard-002` | a legal variable-force spring-work problem under the `graphical` preset — confirms `calculus_any_of` is a disjunction, not a conjunction |
| `ct-guard-003` | a stick-together collision at cursor `momentum-conservation-1d` whose statement uses the word "energy" in ordinary prose but no `kinetic-energy` marker — confirms the lexical scan is not over-broad |

`ct-guard-003` is the important one. An over-broad marker list will quietly
discard most of the usable output, and nobody inspects what gets discarded.

---

## 7. Prompt construction

New module `tools/prompt.py`. Pure function, golden-file tested, no network.

```
build_prompt(state: State, target_concepts, tier, count) -> str
```

The prompt must contain:

1. The covered concepts as `label` strings, in sequence order, introduced as
   the complete set of tools the student has.
2. The forbidden concepts as `label` strings, named explicitly as unavailable,
   with the instruction that they must not appear in the problem statement or
   be needed for its solution.
3. The calculus flags as `label` strings, as the complete set of mathematical
   operations available.
4. The target concepts, the tier, and the count.
5. The output contract: a JSON array of records matching §6.1, symbolic
   `answer_expression` in declared symbols only.

The prompt must **not** contain: the sequence name, the cursor name, any
concept IDs, the words "sequence" or "curriculum", or any text describing a
course, institution, or textbook. Assert this in the golden-file test with the
same denylist `tools/check_rules.py` uses.

Generate symbolically, instantiate numerically, per the repo's existing
verification principle. The model never does arithmetic.

---

## 8. Output rendering

New module `tools/render.py`, run over accepted records only.

- `--format latex` → `out/latex/<sequence>_<cursor>.tex`. Standalone
  compilable document, `amsmath`, problems as an `enumerate`, answers in a
  separate section. Vectors as `\vec{v}`.
- `--format canvas` → `out/canvas/<sequence>_<cursor>.html`. Canvas-ready
  MathJax: inline math in `\( \)`, display math in `\[ \]`, no `<html>` or
  `<body>` wrapper, no external CSS, so it pastes directly into a Canvas
  rich-content editor.

Both formats for every batch; the two are routinely wanted together.

---

## 9. Build order

Each milestone ends green in CI before the next begins.

**M0 — fix the harness.** The two dimensions bugs in `tools/verify.py` noted
in `CLAUDE.md`: distinct dummy coefficients per unit rather than bare unit
substitution, and dimension comparison by name rather than printed form.
Target: `verify.yml` green with `mech-001` and `mech-002` passing all five
checks and `harness-selftest-001` failing on `numeric` alone. Curriculum work
on a harness that rejects correct physics is wasted effort — do not start M1
before this is green.

**M1 — curriculum registry.** `curriculum/concepts.json` with the full
`impulse-first` concept set, complete `lexical_markers` for every momentum and
energy concept; `calculus.json`; `representations.json`;
`sequences/impulse-first.json` plus four empty stubs.
`tools/curriculum.py` loader. `tools/check_rules.py`.

**M2 — validation and expansion.** `tools/validate_curriculum.py` with all six
checks of §4.2, the topological-sort check included.
`expand()` returning `State`. Unit tests on cursor edges: first concept, last
concept, a cursor name absent from the sequence, a preset name versus a
literal flag array.

**M3 — schema and checks.** Extend the problem record. Add checks 6–8 to
`tools/verify.py` with the `--request` argument and the `partial` status.
Add `problems/curriculum-selftests.json` and extend
`problems/false-rejection-guards.json` per §6.4. All self-tests failing on
exactly their named check; all guards passing.

**M4 — generation.** `tools/prompt.py` with golden-file tests including the
denylist assertion. Wire into `tools/generate.py`, reading a request file and
writing to `candidates/<timestamp>/` in the existing accepted/rejected shape.
Extend the batch `README.md` to record the request file and resolved state.

**M5 — rendering.** `tools/render.py`, both formats.

**M6 — remaining sequences.** Populate `work-first` first; it is the
mainstream order and the most useful comparison case for checking that the
gate actually changes output.

---

## 10. Open items

1. `rotational-ke` is registered and placed in `impulse-first` after
   `newton-2nd-rotational`; the fence on generating past
   `extended-work-energy` is lifted. `rolling-without-slipping` is still
   unregistered, so rolling-energy problems remain out of reach.
2. `angular-momentum` requires only `momentum-definition` and
   `rotational-inertia`, not `cross-product`. `impulse-first` happens to
   order them safely, but nothing enforces it, so a new sequence could
   expose the particle form L = r x p before the cross product exists.
   Settle this before populating further sequences.
3. `lexical_markers` completeness outside the momentum and energy threads.
4. Multi-provider routing with fallback is still unbuilt per `CLAUDE.md`;
   this layer is provider-agnostic and does not depend on it.
5. Whether `pedagogy` should ever be advisory rather than fatal. Current
   decision: always fatal.
