#!/usr/bin/env python3
"""Curriculum registry loader and state expander.

No model calls, no network. A State is the explicit set of concepts,
calculus capabilities and representations a student has at a cursor in a
sequence. Only explicit sets derived from a State ever reach a provider
(spec R3); sequence_name and cursor are local bookkeeping.
"""
import json
import os
from dataclasses import dataclass

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                    "curriculum")


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def load_concepts():
    return _load("concepts.json")


def load_calculus():
    return _load("calculus.json")


def load_representations():
    return _load("representations.json")


def load_sequence(name):
    path = os.path.join(ROOT, "sequences", f"{name}.json")
    if not os.path.exists(path):
        raise ValueError(f"unknown sequence {name!r}")
    return _load("sequences", f"{name}.json")


@dataclass(frozen=True)
class State:
    covered: frozenset          # concept IDs at or before cursor
    forbidden: frozenset        # concept IDs after cursor, in this sequence
    calculus: frozenset         # resolved capability flags
    representations: frozenset  # available representations
    cursor: str
    sequence_name: str          # local only; never serialized into a prompt
    order: tuple = ()           # covered IDs in sequence order (for prompts)
    forbidden_order: tuple = ()


def resolve_calculus(calculus, cal=None):
    """A preset name or a literal flag list -> frozenset of flags."""
    cal = cal or load_calculus()
    if isinstance(calculus, str):
        if calculus not in cal["presets"]:
            raise ValueError(f"unknown calculus preset {calculus!r}")
        flags = cal["presets"][calculus]
    elif isinstance(calculus, (list, tuple)):
        flags = list(calculus)
    else:
        raise ValueError(f"calculus must be a preset name or flag list, got {calculus!r}")
    unknown = set(flags) - set(cal["flags"])
    if unknown:
        raise ValueError(f"unknown calculus flags {sorted(unknown)}")
    return frozenset(flags)


def expand(sequence, cursor, calculus):
    """sequence: name or loaded dict; cursor: last covered concept (inclusive)."""
    seq = load_sequence(sequence) if isinstance(sequence, str) else sequence
    order = seq["order"]
    if cursor not in order:
        raise ValueError(f"cursor {cursor!r} is not in sequence {seq['name']!r}")
    i = order.index(cursor)
    covered, tail = order[: i + 1], order[i + 1:]
    reps = frozenset(r for r, at in seq.get("representations_at", {}).items()
                     if at in covered)
    return State(covered=frozenset(covered), forbidden=frozenset(tail),
                 calculus=resolve_calculus(calculus), representations=reps,
                 cursor=cursor, sequence_name=seq["name"],
                 order=tuple(covered), forbidden_order=tuple(tail))


def load_request(path):
    """Load and validate a request file; return (request, State)."""
    with open(path, encoding="utf-8") as f:
        req = json.load(f)
    for k in ("sequence", "cursor", "calculus", "target_concepts"):
        if k not in req:
            raise ValueError(f"request missing {k!r}")
    state = expand(req["sequence"], req["cursor"], req["calculus"])
    bad = set(req["target_concepts"]) - state.covered
    if bad:
        raise ValueError(f"target_concepts not covered at this cursor: {sorted(bad)}")
    tiers = req.get("tiers")
    if tiers is not None and "count" in req and sum(tiers.values()) != req["count"]:
        raise ValueError(f"tiers sum to {sum(tiers.values())}, count is {req['count']}")
    return req, state


# -- label <-> ID mapping: the model only ever sees labels (R3) -------------

def concept_label_map(concepts=None):
    concepts = concepts or load_concepts()
    return {_norm(v["label"]): k for k, v in concepts.items()}


def calculus_label_map(cal=None):
    cal = cal or load_calculus()
    return {_norm(v): k for k, v in cal["flags"].items()}


def representation_label_map(reps=None):
    reps = reps or load_representations()
    return {_norm(v["label"]): k for k, v in reps.items()}


def _norm(s):
    return " ".join(str(s).lower().replace("’", "'").split())


def labels_to_ids(labels, label_map, kind):
    """Map model-reported labels back to IDs; unknown labels raise."""
    if isinstance(labels, str):
        labels = [labels]
    out, unknown = [], []
    for lab in labels or []:
        key = _norm(lab)
        if key in label_map:
            out.append(label_map[key])
        elif key in label_map.values():      # tolerate an ID echoed back
            out.append(key)
        else:
            unknown.append(lab)
    if unknown:
        raise ValueError(f"unknown {kind} label(s): {unknown}")
    return out
