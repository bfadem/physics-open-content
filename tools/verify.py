#!/usr/bin/env python3
"""Deterministic verification of generated physics problems.

Runs five checks against each problem record. Model output is never trusted:
expressions are whitelisted before parsing, and all arithmetic is done by
SymPy rather than by the model.

Records flagged "known_bad": true are harness self-tests and MUST fail.
"""
import glob
import json
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


def parse_unit(text):
    text = str(text)
    if not SAFE_CHARS.fullmatch(text):
        raise ValueError(f"bad unit string: {text!r}")
    unknown = set(IDENT.findall(text)) - set(UNIT_NS)
    if unknown:
        raise ValueError(f"unknown units: {sorted(unknown)}")
    return parse_expr(text, local_dict=dict(UNIT_NS),
                      transformations=TRANSFORMS)


def base_dims(expr_with_units):
    """Reduce to base SI dimensional dependencies.

    Comparing dimensional expressions directly fails for derived units:
    newtons stay symbolic as 'force' instead of expanding to kg*m/s^2.
    """
    dim = Dimension(SI.get_dimensional_expr(expr_with_units))
    deps = dimsys_SI.get_dimensional_dependencies(dim)
    return {str(k): v for k, v in dict(deps).items() if v != 0}


def check(record):
    """Run every check. Returns a list of (name, ok, detail)."""
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
        subs = {Symbol(n, positive=True): parse_unit(meta.get("unit", "1"))
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
            got = sympy.limit(expr,
                              safe_parse(lim["symbol"], names),
                              safe_parse(lim["to"], names))
            want = safe_parse(lim["expect"], names)
            ok = simplify(got - want) == 0
            out.append((label, ok, f"got {got}, expected {want}"))
        except Exception as e:
            out.append((label, False, str(e)))

    # 5. numeric
    try:
        subs = {Symbol(k, positive=True): safe_parse(v, [])
                for k, v in record["given"].items()}
        got = float(expr.subs(subs).evalf())
        want = float(record["expected_value"])
        tol = max(abs(want) * 1e-3, 1e-9)
        ok = abs(got - want) <= tol
        out.append(("numeric", ok, f"got {got:.6g}, expected {want:.6g}"))
    except Exception as e:
        out.append(("numeric", False, str(e)))

    return out


def main():
    files = sorted(glob.glob("problems/*.json"))
    if not files:
        sys.exit("No problem files found under problems/")

    records = []
    for path in files:
        with open(path) as f:
            data = json.load(f)
        records.extend(data if isinstance(data, list) else [data])

    harness_ok = True
    real_failures = 0

    for rec in records:
        results = check(rec)
        passed = all(ok for _, ok, _ in results)
        known_bad = rec.get("known_bad", False)

        verdict = "PASS" if passed else "FAIL"
        tag = "  [known_bad]" if known_bad else ""
        print(f"\n{rec.get('id', '?')} — {rec.get('topic', '?')} "
              f"[{rec.get('tier', '?')}] -> {verdict}{tag}")
        for name, ok, detail in results:
            print(f"   {'ok  ' if ok else 'FAIL'}  {name:22s} {detail}")

        if known_bad and passed:
            print("   !! harness did not catch a known-bad record")
            harness_ok = False
        elif not known_bad and not passed:
            real_failures += 1

    total = len(records)
    bad = sum(1 for r in records if r.get("known_bad"))
    print(f"\n{total} records ({bad} known-bad). "
          f"{real_failures} genuine failures.")

    if not harness_ok:
        sys.exit("Harness self-test failed: a known-bad record passed.")
    if real_failures:
        sys.exit(f"{real_failures} record(s) failed verification.")
    print("All good.")


if __name__ == "__main__":
    main()
