#!/usr/bin/env python3
"""Deterministic verification of generated physics problems.

Runs five checks against each problem record. Model output is never trusted:
expressions are whitelisted before parsing, and all arithmetic is done by
SymPy rather than by the model.

Checks 1-5 (parse, non-trivial, dimensions, limits, numeric) need only the
record. Checks 6-8 (curriculum, lexical, pedagogy) need a curriculum State,
supplied with --request; without it they are skipped and the run is reported
as PARTIAL, never as a pass.

Records flagged "known_bad": true are harness self-tests and MUST fail.
If such a record also lists "expect_fail": [check names], exactly those
checks must fail and every other check must pass -- otherwise a self-test
could "succeed" by failing for the wrong reason.
"""
import argparse
import glob
import json
import os
import random
import re
import sys

import sympy
from sympy import Symbol, simplify
from sympy.parsing.sympy_parser import (
    convert_xor, parse_expr, standard_transformations,
)
from sympy.physics import units as u
from sympy.physics.units import Dimension
from sympy.physics.units.systems.si import SI, dimsys_SI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import curriculum as cur  # noqa: E402

CURRICULUM_CHECKS = ("curriculum", "lexical", "pedagogy")

# '^' means XOR in Python; convert_xor makes it exponentiation, which is how
# both unit strings and model-emitted expressions tend to write it.
TRANSFORMS = standard_transformations + (convert_xor,)

ALLOWED_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sqrt", "exp", "log", "Abs", "pi", "E", "oo",
}
SAFE_CHARS = re.compile(r"[A-Za-z0-9_+\-*/^(). ,]+")
IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")

UNIT_NS = {
    "m": u.meter, "s": u.second, "kg": u.kilogram, "N": u.newton,
    "J": u.joule, "W": u.watt, "Pa": u.pascal, "C": u.coulomb,
    "V": u.volt, "A": u.ampere, "K": u.kelvin, "Hz": u.hertz,
    "mol": u.mole, "ohm": u.ohm,
    "F": u.farad, "H": u.henry, "T": u.tesla, "Wb": u.weber,
    # Angles are dimensionless in SI; treating them so keeps trig functions
    # from tripping the dimensional checker.
    "rad": sympy.S.One, "1": sympy.S.One,
}


def safe_parse(text, symbols):
    """Parse model-supplied text only after whitelisting it."""
    text = str(text)
    if not SAFE_CHARS.fullmatch(text):
        raise ValueError("expression contains disallowed characters")
    unknown = set(IDENT.findall(text)) - set(symbols) - ALLOWED_NAMES
    if unknown:
        raise ValueError(f"unknown identifiers: {sorted(unknown)}")
    local = {s: Symbol(s, positive=True) for s in symbols}
    for name in ALLOWED_NAMES:
        if hasattr(sympy, name):
            local[name] = getattr(sympy, name)
    return parse_expr(text, local_dict=local,
                      transformations=TRANSFORMS, evaluate=True)


NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def parse_value(text):
    """A given value: a plain/scientific-notation number, or a constant
    expression such as pi/6. Scientific notation must be handled here: the
    identifier whitelist would otherwise read '8.99e9' as containing 'e9'.
    """
    text = str(text).strip()
    if NUMBER.fullmatch(text):
        return sympy.Float(text, 15)
    return safe_parse(text, [])


def near_given_points(record, n=5, spread=0.1):
    """Points close to the record's given values. These sit inside the
    physical domain the problem implies (d < L, 0 < theta < pi/2, ...), which
    random points do not."""
    rng = random.Random(record.get("id", ""))
    base = {k: float(parse_value(v)) for k, v in record.get("given", {}).items()}
    return [{Symbol(k, positive=True): v * rng.uniform(1 - spread, 1 + spread)
             for k, v in base.items()} for _ in range(n)]


def agree_near_given(a, b, record):
    """Numeric equality near the given values. Used when simplify() cannot
    prove a - b == 0 because equality only holds on the physical domain
    (e.g. Abs(sin(theta)) vs sin(theta), sqrt(x**2) vs x)."""
    for pt in near_given_points(record):
        va, vb = complex(a.subs(pt).evalf()), complex(b.subs(pt).evalf())
        if abs(va - vb) > 1e-9 * max(abs(va), abs(vb), 1e-30):
            return False
    return True


def parse_unit(text):
    text = str(text)
    if not SAFE_CHARS.fullmatch(text):
        raise ValueError(f"bad unit string: {text!r}")
    unknown = set(IDENT.findall(text)) - set(UNIT_NS)
    if unknown:
        raise ValueError(f"unknown units: {sorted(unknown)}")
    return parse_expr(text, local_dict=dict(UNIT_NS),
                      transformations=TRANSFORMS)


def _deps(dim):
    """Base-SI dependencies of a Dimension, keyed by dimension NAME.

    Keys must be names, not printed Dimension objects: Dimension(time) and
    Dimension(time, T) are the same dimension but print differently.
    """
    deps = dimsys_SI.get_dimensional_dependencies(dim)
    return {str(getattr(k, "name", k)): v
            for k, v in dict(deps).items() if v != 0}


def base_dims(expr):
    """Base SI dimensions of an expression whose symbols carry units.

    Walks the tree rather than asking SymPy for one dimensional expression,
    so that every term of a sum is checked (not just the first) and that
    function arguments (sin, exp, log, ...) are required to be dimensionless.
    """
    expr = sympy.sympify(expr)
    if isinstance(expr, u.Quantity):
        return _deps(SI.get_quantity_dimension(expr))
    if isinstance(expr, Dimension):
        return _deps(expr)
    if expr.is_Number or expr.is_NumberSymbol or expr.is_Symbol:
        return {}
    if expr.is_Mul:
        total = {}
        for arg in expr.args:
            for k, v in base_dims(arg).items():
                total[k] = total.get(k, 0) + v
        return {k: v for k, v in total.items() if v != 0}
    if expr.is_Pow:
        base, exp_ = expr.args
        bd, ed = base_dims(base), base_dims(exp_)
        if ed:
            raise ValueError(f"exponent {exp_} is not dimensionless: {ed}")
        if not bd:
            return {}
        if not exp_.is_Number:
            raise ValueError(f"dimensional base {base} raised to symbolic power")
        return {k: v * exp_ for k, v in bd.items()}
    if expr.is_Add:
        terms = [base_dims(a) for a in expr.args]
        for t in terms[1:]:
            if t != terms[0]:
                raise ValueError(f"adding unlike dimensions: {terms[0] or 'dimensionless'}"
                                 f" + {t or 'dimensionless'}")
        return terms[0]
    if isinstance(expr, sympy.Abs):
        return base_dims(expr.args[0])
    if isinstance(expr, sympy.Function):
        for arg in expr.args:
            ad = base_dims(arg)
            if ad:
                raise ValueError(f"{expr.func.__name__} of dimensional argument: {ad}")
        return {}
    raise ValueError(f"cannot determine dimensions of {expr!r}")


def marker_regex(marker):
    """Case-insensitive match on word boundaries. Boundaries are defined
    by alphanumerics, so markers that start or end with punctuation
    (e.g. "K.E.", "1/2 m v^2") still work, and "inelastic collision" does
    not contain a match for "elastic collision"."""
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(marker)
                      + r"(?![A-Za-z0-9_])", re.IGNORECASE)


def curriculum_checks(record, state, concepts=None):
    """Checks 6-8. Returns [(name, ok, detail)] for curriculum, lexical,
    pedagogy."""
    concepts = concepts or cur.load_concepts()
    meta = record.get("curriculum")
    if not isinstance(meta, dict):
        msg = "record has no curriculum block"
        return [(n, False, msg) for n in CURRICULUM_CHECKS]
    out = []

    # 6. curriculum -- structural admissibility
    why = []
    if meta.get("sequence") not in (None, state.sequence_name) or \
            meta.get("cursor") not in (None, state.cursor):
        why.append(f"record was generated for {meta.get('sequence')}@"
                   f"{meta.get('cursor')}, not the requested state")
    requires = set(meta.get("requires") or [])
    unknown = requires - set(concepts)
    if unknown:
        why.append(f"unknown concepts {sorted(unknown)}")
    if requires & state.forbidden:
        why.append(f"requires not-yet-covered {sorted(requires & state.forbidden)}")
    elif requires - state.covered - unknown:
        why.append(f"requires concepts outside this sequence "
                   f"{sorted(requires - state.covered - unknown)}")
    ip = meta.get("intended_path")
    if ip not in requires:
        why.append(f"intended_path {ip!r} not in requires")
    elif ip not in state.covered:
        why.append(f"intended_path {ip!r} not covered")
    reps = set(meta.get("representations") or [])
    if reps - state.representations:
        why.append(f"representations not yet available "
                   f"{sorted(reps - state.representations)}")
    all_of = set(meta.get("calculus_all_of") or [])
    if all_of - state.calculus:
        why.append(f"needs calculus {sorted(all_of - state.calculus)}")
    any_of = set(meta.get("calculus_any_of") or [])
    if any_of and not (any_of & state.calculus):
        why.append(f"needs one of calculus {sorted(any_of)}")
    out.append(("curriculum", not why,
                "; ".join(why) if why else
                f"{len(requires)} required concepts all covered"))

    # 7. lexical -- forbidden vocabulary in the wording
    texts = [("statement", record.get("statement", ""))] + [
        (f"symbols.{k}.desc", (v or {}).get("desc", ""))
        for k, v in (record.get("symbols") or {}).items()]
    hits = []
    for cid in sorted(state.forbidden):
        for marker in concepts.get(cid, {}).get("lexical_markers", []):
            rx = marker_regex(marker)
            for where, text in texts:
                if rx.search(str(text)):
                    hits.append(f"{marker!r} ({cid}) in {where}")
    out.append(("lexical", not hits,
                "; ".join(hits[:5]) if hits else
                f"no markers of {len(state.forbidden)} forbidden concepts"))

    # 8. pedagogy -- a covered shortcut defeats the problem's purpose
    trivial = set(meta.get("trivial_if_available") or []) & state.covered
    out.append(("pedagogy", not trivial,
                f"shortcut already available: {sorted(trivial)}" if trivial
                else "no covered shortcut"))
    return out


def check(record, state=None):
    """Run every check. Returns a list of (name, ok, detail).
    Checks 6-8 run only when a curriculum State is supplied."""
    out = []
    syms = record.get("symbols", {})
    names = list(syms)

    # 1. parse
    try:
        expr = safe_parse(record["answer_expression"], names)
        out.append(("parse", True, str(expr)))
    except Exception as e:
        return [("parse", False, str(e))]

    # 2. non-triviality
    used = {s.name for s in expr.free_symbols}
    if not used:
        out.append(("non-trivial", False, "answer is a bare constant"))
    else:
        unused = set(names) - used
        out.append((
            "non-trivial", True,
            f"uses {sorted(used)}" + (f"; ignores {sorted(unused)}" if unused else ""),
        ))

    # 3. dimensions
    try:
        # Each symbol becomes (distinct positive dummy) * (its unit). Bare
        # units would collapse sums: m1 and m2 both -> kilogram, so
        # (m2 - m1) -> 0 and the whole answer would read as dimensionless.
        subs = {Symbol(n, positive=True):
                sympy.Dummy(n, positive=True) * parse_unit(meta.get("unit", "1"))
                for n, meta in syms.items()}
        got = base_dims(expr.subs(subs))
        want = base_dims(parse_unit(record["answer_unit"]))
        ok = got == want
        detail = (f"expected {record['answer_unit']} = {want or 'dimensionless'}"
                  if ok else f"got {got or 'dimensionless'}, "
                             f"expected {want or 'dimensionless'} "
                             f"({record['answer_unit']})")
        out.append(("dimensions", ok, detail))
    except Exception as e:
        out.append(("dimensions", False, str(e)))

    # 4. limits
    for lim in record.get("limits", []):
        label = f"limit {lim['symbol']}->{lim['to']}"
        try:
            # Models write infinity in several ways; SymPy spells it oo.
            to = re.sub(r"\b(infinity|Infinity|inf|Inf)\b", "oo", str(lim["to"]))
            got = sympy.limit(expr,
                              safe_parse(lim["symbol"], names),
                              safe_parse(to, names))
            want = safe_parse(lim["expect"], names)
            ok = simplify(got - want) == 0
            how = "symbolically"
            if not ok and record.get("given"):
                ok = agree_near_given(got, want, record)
                how = "numerically, near the given values"
            out.append((label, ok, f"got {got}, expected {want}"
                                   + (f" (equal {how})" if ok else "")))
        except Exception as e:
            out.append((label, False, str(e)))

    # 5. numeric
    try:
        subs = {Symbol(k, positive=True): parse_value(v)
                for k, v in record["given"].items()}
        got = float(expr.subs(subs).evalf())
        want = float(record["expected_value"])
        tol = max(abs(want) * 1e-3, 1e-9)
        ok = abs(got - want) <= tol
        out.append(("numeric", ok, f"got {got:.6g}, expected {want:.6g}"))
    except Exception as e:
        out.append(("numeric", False, str(e)))

    if state is not None:
        out += curriculum_checks(record, state)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="record files (default problems/*.json)")
    ap.add_argument("--request", help="request file whose State checks 6-8 use")
    ap.add_argument("--ids", help="comma-separated record ids to check (default all)")
    args = ap.parse_args()

    files = args.files or sorted(glob.glob("problems/*.json"))
    if not files:
        sys.exit("No problem files found under problems/")
    state = None
    if args.request:
        _req, state = cur.load_request(args.request)
        print(f"State from {args.request}: {len(state.covered)} covered, "
              f"{len(state.forbidden)} forbidden, calculus {sorted(state.calculus)}")

    records = []
    for path in files:
        with open(path) as f:
            data = json.load(f)
        records.extend(data if isinstance(data, list) else [data])
    if args.ids:
        wanted = set(args.ids.split(","))
        records = [r for r in records if r.get("id") in wanted]
        missing = wanted - {r.get("id") for r in records}
        if missing:
            sys.exit(f"--ids not found: {sorted(missing)}")

    harness_ok = True
    real_failures = 0
    not_exercised = []

    for rec in records:
        results = check(rec, state)
        passed = all(ok for _, ok, _ in results)
        known_bad = rec.get("known_bad", False)
        expect_fail = rec.get("expect_fail")

        # A self-test aimed at checks 6-8 cannot be exercised without a State.
        if state is None and known_bad and expect_fail and \
                set(expect_fail) <= set(CURRICULUM_CHECKS):
            not_exercised.append(rec.get("id"))
            print(f"\n{rec.get('id', '?')} — {rec.get('topic', '?')} "
                  f"-> NOT EXERCISED (targets {expect_fail}; needs --request)")
            continue

        verdict = "PASS" if passed else "FAIL"
        if state is None and passed:
            verdict = "PASS (checks 1-5 only)"
        tag = "  [known_bad]" if known_bad else ""
        print(f"\n{rec.get('id', '?')} — {rec.get('topic', '?')} "
              f"[{rec.get('tier', '?')}] -> {verdict}{tag}")
        for name, ok, detail in results:
            print(f"   {'ok  ' if ok else 'FAIL'}  {name:22s} {detail}")

        failed = sorted(name for name, ok, _ in results if not ok)
        if known_bad and passed:
            print("   !! harness did not catch a known-bad record")
            harness_ok = False
        elif known_bad and expect_fail is not None \
                and failed != sorted(expect_fail):
            print(f"   !! known-bad record failed {failed}, "
                  f"expected exactly {sorted(expect_fail)}")
            harness_ok = False
        elif not known_bad and not passed:
            real_failures += 1

    total = len(records)
    bad = sum(1 for r in records if r.get("known_bad"))
    print(f"\n{total} records ({bad} known-bad). "
          f"{real_failures} genuine failures.")

    if not harness_ok:
        sys.exit("Harness self-test failed: a known-bad record passed "
                 "or failed for the wrong reason.")
    if real_failures:
        sys.exit(f"{real_failures} record(s) failed verification.")
    if state is None:
        print("PARTIAL: checks 1-5 only. Curriculum checks 6-8 were skipped "
              f"(no --request); {len(not_exercised)} curriculum self-test(s) "
              "not exercised. This is not a curriculum pass.")
    else:
        print("All good: checks 1-8.")


if __name__ == "__main__":
    main()
