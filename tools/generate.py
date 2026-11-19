#!/usr/bin/env python3
"""Generate a batch of candidate problem records from one provider (Gemini).

Pipeline per candidate:
  1. AUTHOR model writes a record: statement, symbols, symbolic answer,
     given values, limiting cases. It never supplies a number.
  2. SOLVER model (a different model, to decorrelate errors) sees only the
     statement and symbol list and derives the answer blind.
  3. SymPy checks the two answers agree at random points, computes
     expected_value from the author's expression, and the record then runs
     through every check in verify.py.

Accepted records go to candidates/<batch>/accepted.json for human review --
they are NOT promoted into problems/ automatically. Rejected records go to
candidates/<batch>/rejected.json with reasons, because nobody inspects what a
pipeline silently discards. A report is written to candidates/<batch>/README.md.

Model calls go through engines.Router, which falls over across the free
engines in tools/engines.json as each one's quota runs out. The solver is
never the same engine as the author of that record. The batch stops cleanly,
keeping what it produced, only when every engine for a role is exhausted.

Env: provider keys (GEMINI_API_KEY, GROQ_API_KEY, ...), COUNT, BATCH, and
optional AUTHOR_MODEL / SOLVER_MODEL ("provider:model", or a bare Gemini
model) to put first in that role's chain.
"""
import datetime
import json
import os
import random
import re
import sys
import time

import sympy
from sympy import Symbol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402
from engines import QuotaExhausted, Router, Unavailable  # noqa: E402

PAUSE = 4.0            # seconds between calls; stay well under per-minute caps

TOPICS = [
    "projectile motion", "kinematics with constant acceleration",
    "inclined plane with friction", "Atwood machine or pulley system",
    "uniform circular motion", "banked curve", "conical pendulum",
    "work-energy theorem", "spring potential energy",
    "conservation of momentum in a collision", "ballistic pendulum",
    "rotational kinematics", "rolling without slipping",
    "torque and static equilibrium", "moment of inertia",
    "angular momentum conservation", "simple harmonic motion",
    "physical pendulum", "orbital motion and gravitation", "escape speed",
    "fluid statics and buoyancy", "Bernoulli's equation",
    "ideal gas law", "first law of thermodynamics for an ideal gas",
    "Coulomb's law", "electric field of a charge distribution",
    "capacitors and stored energy", "DC circuits with resistors",
    "RC circuit charging or discharging", "magnetic force on a moving charge",
    "Faraday's law and motional emf", "standing waves on a string",
    "Doppler effect", "thin lens or mirror equation", "Snell's law",
]
TIERS = ["plug-and-chug", "multi-step", "interesting"]

UNIT_VOCAB = ", ".join(sorted(k for k in verify.UNIT_NS if k != "1"))
RESERVED = set(verify.ALLOWED_NAMES) | {
    "lambda", "I", "S", "N", "O", "Q", "beta", "gamma", "zeta", "Ei",
}

AUTHOR_PROMPT = """You write physics problems for an introductory
university course. Write ONE {tier} problem on: {topic}.

Reply with JSON only, exactly these keys:
{{
  "topic": "short description",
  "statement": "the problem as a student reads it, symbolic (no numbers); name every symbol by its exact identifier",
  "symbols": {{"<identifier>": {{"desc": "...", "unit": "..."}}}},
  "answer_expression": "SymPy-parseable, using only the declared identifiers",
  "answer_unit": "...",
  "given": {{"<identifier>": "<positive number, realistic>"}},
  "limits": [{{"symbol": "<identifier>", "to": "<value or identifier>", "expect": "<expression>"}}]
}}

Rules:
- Identifiers: ASCII letters, digits, underscore; start with a letter. Do not
  use these names: {reserved}. Use g for gravitational acceleration and
  declare it as a symbol. Physical constants (e.g. k_e, G_N, mu0) must also
  be declared as symbols with units and given values.
- Units must be products/quotients/powers of: {units}. Use ^ for powers,
  e.g. "m/s^2", "N*m^2/C^2". Angles: "rad". Dimensionless: "1".
- Allowed functions: sin cos tan asin acos atan sqrt exp log Abs, constant pi.
- Every symbol must be positive. Ask for a magnitude, not a signed quantity.
- "given" must assign a value to every symbol, such that the answer is a
  real positive number. Angles in radians.
- Give 1 or 2 limiting cases a physicist would use to sanity-check the
  answer (e.g. a mass going to 0, an angle going to 0).
- The answer must be the single quantity the statement asks for.
"""

SOLVER_PROMPT = """Solve this physics problem symbolically.

{statement}

Symbols (all positive):
{symbols}

Reply with JSON only: {{"answer_expression": "<SymPy-parseable expression
using only the identifiers above>"}}
Allowed functions: sin cos tan asin acos atan sqrt exp log Abs, constant pi.
Give the magnitude of the requested quantity.
"""


def precheck(rec):
    """Structural checks that verify.py assumes have already passed."""
    syms = rec.get("symbols")
    if not isinstance(syms, dict) or not syms:
        return "no symbols declared"
    for name in syms:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            return f"bad identifier {name!r}"
        if name in RESERVED:
            return f"reserved identifier {name!r}"
    given = rec.get("given") or {}
    # Models often declare the unknown itself (e.g. v, T) as a symbol. A
    # symbol with no given value that the answer does not use is that
    # unknown: drop it rather than reject correct physics.
    used = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*",
                          str(rec.get("answer_expression", ""))))
    for name in [n for n in syms if n not in given and n not in used]:
        del syms[name]
    missing = set(syms) - set(given)
    if missing:
        return f"no given value for {sorted(missing)}"
    for k in ("statement", "answer_expression", "answer_unit"):
        if not isinstance(rec.get(k), str) or not rec[k].strip():
            return f"missing {k}"
    rec["given"] = {k: str(v) for k, v in given.items()}
    return None


def instantiate(rec):
    """SymPy, not the model, computes the numeric answer."""
    names = list(rec["symbols"])
    expr = verify.safe_parse(rec["answer_expression"], names)
    subs = {Symbol(k, positive=True): verify.parse_value(v)
            for k, v in rec["given"].items()}
    val = complex(expr.subs(subs).evalf())
    if abs(val.imag) > 1e-9 * max(1, abs(val.real)) or not val.real > 0:
        raise ValueError(f"given values make the answer non-positive/complex: {val}")
    return float(f"{val.real:.6g}")


def equivalent(a_text, b_text, names, trials=8):
    """Numerical equivalence at random positive points (robust where
    simplify() is not, e.g. trig identities)."""
    a = verify.safe_parse(a_text, names)
    b = verify.safe_parse(b_text, names)
    rng = random.Random(0)
    checked = 0
    for _ in range(trials * 3):
        pt = {Symbol(n, positive=True): sympy.Float(rng.uniform(0.2, 1.4))
              for n in names}
        try:
            va, vb = complex(a.subs(pt).evalf()), complex(b.subs(pt).evalf())
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if any(v != v or abs(v) == float("inf") for v in (va, vb)):
            continue
        if abs(va - vb) > 1e-6 * max(abs(va), abs(vb), 1e-12):
            return False, f"differ at a test point: {va:.6g} vs {vb:.6g}"
        checked += 1
        if checked >= trials:
            break
    if checked < 3:
        return False, "could not evaluate at enough test points"
    return True, f"agree at {checked} random points"


def main():
    count = int(os.environ.get("COUNT", "30"))
    router = Router(overrides={"author": os.environ.get("AUTHOR_MODEL"),
                               "solver": os.environ.get("SOLVER_MODEL")})
    for role, chain in router.describe().items():
        print(f"{role} chain: {chain or 'NONE'}")
    if not router.chains["author"] or not router.chains["solver"]:
        sys.exit("No usable engine for some role: check provider secrets")
    batch = os.environ.get("BATCH") or datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%d-%H%M")
    outdir = os.path.join("candidates", batch)
    os.makedirs(outdir, exist_ok=True)

    rng = random.Random(batch)
    jobs = [(rng.choice(TOPICS), TIERS[i % 3]) for i in range(count)]
    accepted, rejected, unavailable = [], [], []
    stop_reason = None

    for i, (topic, tier) in enumerate(jobs, 1):
        rid = f"gen-{batch}-{i:03d}"
        print(f"\n[{i}/{count}] {tier}: {topic}")
        rec = {"id": rid, "tier": tier}
        stage = "author"
        try:
            out, author = router.call("author", AUTHOR_PROMPT.format(
                tier=tier, topic=topic, reserved=", ".join(sorted(RESERVED)),
                units=UNIT_VOCAB))
            rec["provenance"] = {"author": author}
            rec.update({k: out.get(k) for k in (
                "topic", "statement", "symbols", "answer_expression",
                "answer_unit", "given", "limits")})
            rec["limits"] = rec.get("limits") or []
            rec["tier"] = tier

            stage = "precheck"
            problem = precheck(rec)
            if problem:
                raise ValueError(problem)

            stage = "instantiate"
            rec["expected_value"] = instantiate(rec)

            stage = "blind-solve"
            time.sleep(PAUSE)
            sym_list = "\n".join(f"- {n}: {m.get('desc', '')} [{m.get('unit', '')}]"
                                 for n, m in rec["symbols"].items())
            sol, solver = router.call("solver", SOLVER_PROMPT.format(
                statement=rec["statement"], symbols=sym_list), avoid={author})
            rec["provenance"]["solver"] = solver
            rec["solver_expression"] = str(sol.get("answer_expression", ""))

            stage = "agreement"
            ok, detail = equivalent(rec["answer_expression"],
                                    rec["solver_expression"], list(rec["symbols"]))
            if not ok:
                raise ValueError(f"author and blind solver disagree: {detail}")

            stage = "dedupe"
            for prev in accepted:
                # Compare on symbols the answers USE: declared-but-unused
                # extras must not hide a duplicate.
                names = sorted(set(prev["symbols"]) | set(rec["symbols"]))
                ua = {x.name for x in verify.safe_parse(
                    prev["answer_expression"], names).free_symbols}
                ub = {x.name for x in verify.safe_parse(
                    rec["answer_expression"], names).free_symbols}
                if ua == ub and equivalent(prev["answer_expression"],
                                           rec["answer_expression"], sorted(ua))[0]:
                    raise ValueError(f"duplicate of {prev['id']}")

            stage = "verify"
            results = verify.check(rec)
            failed = [(n, d) for n, good, d in results if not good]
            if failed:
                raise ValueError("; ".join(f"{n}: {d}" for n, d in failed))

            rec["provenance"]["agreement"] = detail
            accepted.append(rec)
            print(f"   ACCEPT  {rec['answer_expression']}")
        except Unavailable as e:
            unavailable.append({"id": rid, "topic": topic, "stage": stage,
                                "reason": str(e)[:300]})
            print(f"   SKIP    [{stage}] model unavailable")
        except QuotaExhausted as e:
            stop_reason = str(e)
            print(f"   STOP    {e}")
            break
        except Exception as e:
            rec["rejected_at"] = stage
            rec["reason"] = f"{type(e).__name__}: {e}"[:500]
            rejected.append(rec)
            print(f"   REJECT  [{stage}] {rec['reason']}")
        time.sleep(PAUSE)

    for name, data in (("accepted", accepted), ("rejected", rejected)):
        with open(os.path.join(outdir, f"{name}.json"), "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    attempted = len(accepted) + len(rejected) + len(unavailable)
    by_stage = {}
    for r in rejected:
        by_stage[r["rejected_at"]] = by_stage.get(r["rejected_at"], 0) + 1
    lines = [
        f"# Batch {batch}", "",
        f"- Requested {count}, attempted {attempted}, "
        f"**accepted {len(accepted)}**, rejected {len(rejected)}, "
        f"skipped (model unavailable) {len(unavailable)}",
        f"- Stopped early: {stop_reason}" if stop_reason else "- Ran to completion",
        "", "## Engines", "",
    ] + router.report_lines() + ["", "## Rejections by stage", ""]
    lines += [f"- {s}: {n}" for s, n in sorted(by_stage.items())] or ["- none"]
    lines += ["", "## Accepted (awaiting human review)", ""]
    lines += [f"- `{r['id']}` [{r['tier']}] {r.get('topic')}: "
              f"`{r['answer_expression']}` "
              f"({r['provenance']['author']} / {r['provenance']['solver']})"
              for r in accepted] or ["- none"]
    lines += ["", "## Rejected", ""]
    lines += [f"- `{r['id']}` [{r['rejected_at']}] {r.get('topic') or ''} — "
              f"{r['reason'][:200]}" for r in rejected] or ["- none"]
    report = "\n".join(lines) + "\n"
    with open(os.path.join(outdir, "README.md"), "w") as f:
        f.write(report)
    print("\n" + report)


if __name__ == "__main__":
    main()
