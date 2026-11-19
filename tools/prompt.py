#!/usr/bin/env python3
"""Build the author prompt for curriculum-gated generation (spec section 7).

Pure function, no network; golden-file tested. Per rule R3 the prompt carries
only explicit sets, as ordinary physics vocabulary (labels): never a sequence
name, cursor name, concept/flag/representation ID, the words "sequence" or
"curriculum", or text describing a course, institution or textbook.

The model reports the record's curriculum fields (requires, intended_path,
...) under the neutral key "solution_profile", using the labels it was shown;
map_curriculum_fields converts them to IDs locally.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import curriculum as cur  # noqa: E402
import verify  # noqa: E402

UNIT_VOCAB = ", ".join(sorted(k for k in verify.UNIT_NS if k != "1"))
RESERVED = set(verify.ALLOWED_NAMES) | {
    "lambda", "I", "S", "N", "O", "Q", "beta", "gamma", "zeta", "Ei",
}

TIER_GUIDE = {
    "plug-and-chug": "one idea applied directly; a single relation gives the answer",
    "multi-step": "two or more ideas chained; an intermediate quantity must be found first",
    "interesting": "a situation that rewards insight, such as an unexpected limiting "
                   "behaviour or a non-obvious choice of method; not a routine exercise "
                   "with a story attached",
}

RECORD_RULES = f"""Rules for every problem:
- Identifiers: ASCII letters, digits, underscore; start with a letter. Do not
  use these names: {", ".join(sorted(RESERVED))}. Use g for gravitational
  acceleration and declare it as a symbol. Physical constants must also be
  declared as symbols with units and given values.
- Declare only the symbols the answer is expressed in. Do not declare the
  unknown being solved for.
- Units must be products/quotients/powers of: {UNIT_VOCAB}. Use ^ for powers,
  e.g. "m/s^2". Angles: "rad". Dimensionless: "1".
- Allowed functions: sin cos tan asin acos atan sqrt exp log Abs, constant pi.
  Write infinity as oo.
- Every symbol must be positive. Ask for a magnitude, not a signed quantity.
- "given" assigns a realistic value to every declared symbol so the answer is
  a real positive number. Angles in radians. Never compute the numeric answer.
- Give 1 or 2 limiting cases a physicist would use to sanity-check the answer.
- The statement is symbolic (no numbers), names every symbol by its exact
  identifier, and asks for exactly one quantity."""


def _bullets(items):
    return "\n".join(f"- {x}" for x in items) if items else "- (none)"


def build_prompt(state, target_concepts, tier, count, concepts=None,
                 calculus=None, representations=None):
    concepts = concepts or cur.load_concepts()
    calculus = calculus or cur.load_calculus()
    representations = representations or cur.load_representations()
    if tier not in TIER_GUIDE:
        raise ValueError(f"unknown tier {tier!r}")
    bad = set(target_concepts) - state.covered
    if bad:
        raise ValueError(f"target concepts not covered: {sorted(bad)}")

    label = lambda cid: concepts[cid]["label"]  # noqa: E731
    covered = [label(c) for c in state.order]
    forbidden = [label(c) for c in state.forbidden_order]
    flags = [calculus["flags"][f] for f in sorted(state.calculus)]
    reps = [representations[r]["label"] for r in sorted(state.representations)]
    targets = [label(c) for c in target_concepts]

    return f"""You write physics problems for students who know exactly the
physics listed below and nothing more.

The student knows (the complete set of physics tools available):
{_bullets(covered)}

Not yet available (must not appear in any problem statement or symbol
description, and must not be needed to solve any problem):
{_bullets(forbidden)}

Mathematics available (the complete set of mathematical operations; anything
else, such as calculus not listed here, is unavailable):
{_bullets(flags)}

Diagrams and graphs the student can draw or read:
{_bullets(reps)}

Task: write {count} different {tier} problem(s) that exercise:
{_bullets(targets)}
A {tier} problem: {TIER_GUIDE[tier]}.
Do not write a problem that a listed tool solves more simply than the
intended one; such problems waste the practice and will be discarded.

{RECORD_RULES}

Reply with JSON only, an object with one key "problems" holding a list of
{count} objects, each with exactly these keys:
{{
  "topic": "short description",
  "statement": "the problem as a student reads it",
  "symbols": {{"<identifier>": {{"desc": "...", "unit": "..."}}}},
  "answer_expression": "SymPy-parseable, using only the declared identifiers",
  "answer_unit": "...",
  "given": {{"<identifier>": "<positive number>"}},
  "limits": [{{"symbol": "<identifier>", "to": "<value or identifier>", "expect": "<expression>"}}],
  "solution_profile": {{
    "requires": ["<every physics idea needed to solve it, copied exactly from what the student knows>"],
    "intended_path": "<the one idea it is meant to exercise, copied exactly>",
    "trivial_if_available": ["<any listed idea that would give a simpler route; normally empty>"],
    "representations": ["<diagrams or graphs the student must draw or read, copied exactly; may be empty>"],
    "calculus_all_of": ["<every mathematical operation needed, copied exactly>"],
    "calculus_any_of": ["<operations of which any one suffices, copied exactly; may be empty>"]
  }}
}}
"requires" describes the solution, not the wording: list every idea the
solution uses, even ones the statement never names.
"""


def map_curriculum_fields(meta, state, concepts=None, calculus=None,
                          representations=None):
    """Convert a model-reported curriculum block (labels) to IDs, and stamp
    the local sequence/cursor. Unknown labels raise ValueError."""
    if not isinstance(meta, dict):
        raise ValueError("problem has no curriculum block")
    cl = cur.concept_label_map(concepts)
    fl = cur.calculus_label_map(calculus)
    rl = cur.representation_label_map(representations)
    # Models sometimes list a mathematics or diagram label under "requires".
    # Those labels are unambiguous (validate_curriculum forbids shared
    # variants), so route them to the field they belong to, never drop them.
    requires, calc_extra, rep_extra = [], [], []
    req = meta.get("requires")
    for lab in ([req] if isinstance(req, str) else req or []):
        key = cur._norm(lab)
        if key not in cl and key in fl:
            calc_extra.append(lab)
        elif key not in cl and key in rl:
            rep_extra.append(lab)
        else:
            requires.append(lab)

    def ids(field, lmap, kind, extra=()):
        v = meta.get(field)
        v = [v] if isinstance(v, str) else list(v or [])
        return list(dict.fromkeys(cur.labels_to_ids(v + list(extra), lmap, kind)))

    ip = cur.labels_to_ids(meta.get("intended_path") or [], cl, "concept")
    return {
        "sequence": state.sequence_name,
        "cursor": state.cursor,
        "requires": cur.labels_to_ids(requires, cl, "concept"),
        "intended_path": ip[0] if ip else None,
        "trivial_if_available": ids("trivial_if_available", cl, "concept"),
        "representations": ids("representations", rl, "representation", rep_extra),
        "calculus_all_of": ids("calculus_all_of", fl, "calculus", calc_extra),
        "calculus_any_of": ids("calculus_any_of", fl, "calculus"),
    }
