#!/usr/bin/env python3
"""Deterministic verification of generated physics problems.

Runs five checks against each problem record. Model output is never trusted:
expressions are whitelisted before parsing, and all arithmetic is done by
SymPy rather than by the model.

Records flagged "known_bad": true are harness self-tests and MUST fail.
If such a record also lists "expect_fail": [check names], exactly those
checks must fail and every other check must pass -- otherwise a self-test
could "succeed" by failing for the wrong reason.
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

        failed = sorted(name for name, ok, _ in results if not ok)
        expect_fail = rec.get("expect_fail")
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
    print("All good.")


if __name__ == "__main__":
    main()
