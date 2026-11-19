#!/usr/bin/env python3
"""Validate the curriculum registry (spec section 4.2). Run in CI.

Fails on:
  1. a sequence referencing a concept ID absent from concepts.json
  2. a cycle in the concepts' requires edges
  3. a sequence that is not a topological sort of the requires DAG
  4. a representations_at value not in that sequence's order
  5. a calculus_hint key not in the order, or a flag absent from calculus.json
  6. an R1 denylist match anywhere under curriculum/ (via check_rules)
Also: requires edges naming unknown concepts, duplicate labels (labels are
how model output is mapped back to IDs, so they must be unique), and
sequence-name / filename mismatch.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_rules  # noqa: E402
import curriculum as cur  # noqa: E402


def find_cycle(concepts):
    WHITE, GREY, BLACK = 0, 1, 2
    color = {c: WHITE for c in concepts}
    stack = []

    def visit(c):
        color[c] = GREY
        stack.append(c)
        for r in concepts[c]["requires"]:
            if r not in concepts:
                continue
            if color[r] == GREY:
                return stack[stack.index(r):] + [r]
            if color[r] == WHITE:
                found = visit(r)
                if found:
                    return found
        stack.pop()
        color[c] = BLACK
        return None

    for c in concepts:
        if color[c] == WHITE:
            found = visit(c)
            if found:
                return found
    return None


def validate(root=None):
    errors = []
    concepts = cur.load_concepts()
    cal = cur.load_calculus()
    reps = cur.load_representations()

    for cid, meta in concepts.items():
        for r in meta["requires"]:
            if r not in concepts:
                errors.append(f"concept {cid}: requires unknown concept {r!r}")
    # Labels (and their tolerated variants) map model output back to IDs,
    # so no variant may belong to two concepts / flags / representations.
    for kind, pairs in (
            ("concept", [(k, v["label"]) for k, v in concepts.items()]),
            ("calculus flag", list(cal["flags"].items())),
            ("representation", [(k, v["label"]) for k, v in reps.items()])):
        for alias, a, b in cur.alias_clashes(pairs):
            errors.append(f"{kind} label variant {alias!r} is shared by {a} and {b}")

    cycle = find_cycle(concepts)                                       # 2
    if cycle:
        errors.append("requires cycle: " + " -> ".join(cycle))

    seq_dir = os.path.join(cur.ROOT, "sequences")
    for fname in sorted(os.listdir(seq_dir)):
        if not fname.endswith(".json"):
            continue
        name = fname[:-5]
        seq = cur.load_sequence(name)
        tag = f"sequence {name}"
        if seq.get("name") != name:
            errors.append(f"{tag}: name field {seq.get('name')!r} != filename")
        order = seq.get("order", [])
        pos = {c: i for i, c in enumerate(order)}
        if len(pos) != len(order):
            errors.append(f"{tag}: duplicate concept in order")
        for c in order:                                                # 1
            if c not in concepts:
                errors.append(f"{tag}: unknown concept {c!r}")
        for c in order:                                                # 3
            for r in concepts.get(c, {}).get("requires", []):
                if r not in pos:
                    errors.append(f"{tag}: {c} requires {r}, which is absent")
                elif pos[r] > pos[c]:
                    errors.append(f"{tag}: {c} appears before its prerequisite {r}")
        for rep, at in seq.get("representations_at", {}).items():      # 4
            if rep not in reps:
                errors.append(f"{tag}: unknown representation {rep!r}")
            if at not in pos:
                errors.append(f"{tag}: representation {rep} at {at!r}, not in order")
        for c, hint in seq.get("calculus_hint", {}).items():           # 5
            if c not in pos:
                errors.append(f"{tag}: calculus_hint key {c!r} not in order")
            for key in ("any_of", "all_of"):
                for flag in hint.get(key, []):
                    if flag not in cal["flags"]:
                        errors.append(f"{tag}: calculus_hint flag {flag!r} unknown")

    for preset, flags in cal["presets"].items():
        for flag in flags:
            if flag not in cal["flags"]:
                errors.append(f"calculus preset {preset}: unknown flag {flag!r}")

    errors += [f"R1: {p}" for p in check_rules.scan_tree(root or cur.ROOT)]  # 6
    return errors


def main():
    errors = validate()
    for e in errors:
        print(e)
    if errors:
        sys.exit(f"curriculum invalid: {len(errors)} problem(s)")
    print("validate_curriculum: OK")


if __name__ == "__main__":
    main()
