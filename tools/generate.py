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

Rate limits are honored, never evaded: on HTTP 429 we wait the server's
retryDelay and retry a bounded number of times; a per-day quota stops the
batch cleanly and keeps what was produced.

Env: GEMINI_API_KEY (required), COUNT, AUTHOR_MODEL, SOLVER_MODEL, BATCH.
"""
import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

import sympy
from sympy import Symbol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402

BASE = "https://generativelanguage.googleapis.com/v1beta"
PAUSE = 4.0            # seconds between calls; stay well under per-minute caps
CALL_TIMEOUT = 240
MAX_429_RETRIES = 3

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


class QuotaExhausted(Exception):
    pass


def call_model(model, prompt, key):
    """One generateContent call returning parsed JSON. Honors 429s."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7,
                             "responseMimeType": "application/json"},
    }
    for attempt in range(MAX_429_RETRIES + 1):
        req = urllib.request.Request(
            f"{BASE}/models/{model}:generateContent",
            data=json.dumps(payload).encode(),
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code != 429:
                raise RuntimeError(f"HTTP {e.code} from {model}: {body[:300]}")
            if "PerDay" in body or "per day" in body.lower():
                raise QuotaExhausted(f"{model}: daily quota reached")
            if attempt == MAX_429_RETRIES:
                raise QuotaExhausted(f"{model}: still rate-limited after "
                                     f"{MAX_429_RETRIES} waits")
            m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', body)
            wait = float(m.group(1)) + 1 if m else 30 * (attempt + 1)
            print(f"   429 from {model}; waiting {wait:.0f}s as instructed")
            time.sleep(wait)
    usage = data.get("usageMetadata", {})
    cands = data.get("candidates") or []
    parts = (cands[0].get("content", {}).get("parts") if cands else None) or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        reason = cands[0].get("finishReason") if cands else "no candidates"
        raise RuntimeError(f"{model} returned no text ({reason})")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(text), usage.get("totalTokenCount", 0)


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
    subs = {Symbol(k, positive=True): verify.safe_parse(v, [])
            for k, v in rec["given"].items()}
    val = complex(expr.subs(subs).evalf())
    if abs(val.imag) > 1e-9 * max(1, abs(val.real)) or not val.real > 0:
        raise ValueError(f"given values make the answer non-positive/complex: {val}")
    return float(sympy.Float(val.real, 6))


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
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY is not set")
    count = int(os.environ.get("COUNT", "30"))
    author = os.environ.get("AUTHOR_MODEL", "gemini-4-hydrogen")
    solver = os.environ.get("SOLVER_MODEL", "gemini-3-flash-preview")
    batch = os.environ.get("BATCH") or datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%d-%H%M")
    outdir = os.path.join("candidates", batch)
    os.makedirs(outdir, exist_ok=True)

    rng = random.Random(batch)
    jobs = [(rng.choice(TOPICS), TIERS[i % 3]) for i in range(count)]
    accepted, rejected = [], []
    tokens, calls, stop_reason = 0, 0, None

    for i, (topic, tier) in enumerate(jobs, 1):
        rid = f"gen-{batch}-{i:03d}"
        print(f"\n[{i}/{count}] {tier}: {topic}")
        rec = {"id": rid, "tier": tier}
        stage = "author"
        try:
            out, t = call_model(author, AUTHOR_PROMPT.format(
                tier=tier, topic=topic, reserved=", ".join(sorted(RESERVED)),
                units=UNIT_VOCAB), key)
            calls += 1; tokens += t
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
            sol, t = call_model(solver, SOLVER_PROMPT.format(
                statement=rec["statement"], symbols=sym_list), key)
            calls += 1; tokens += t
            rec["solver_expression"] = str(sol.get("answer_expression", ""))

            stage = "agreement"
            ok, detail = equivalent(rec["answer_expression"],
                                    rec["solver_expression"], list(rec["symbols"]))
            if not ok:
                raise ValueError(f"author and blind solver disagree: {detail}")

            stage = "verify"
            results = verify.check(rec)
            failed = [(n, d) for n, good, d in results if not good]
            if failed:
                raise ValueError("; ".join(f"{n}: {d}" for n, d in failed))

            rec["provenance"] = {"author": author, "solver": solver,
                                 "agreement": detail}
            accepted.append(rec)
            print(f"   ACCEPT  {rec['answer_expression']}")
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

    attempted = len(accepted) + len(rejected)
    by_stage = {}
    for r in rejected:
        by_stage[r["rejected_at"]] = by_stage.get(r["rejected_at"], 0) + 1
    lines = [
        f"# Batch {batch}", "",
        f"- Author model: `{author}`; blind solver: `{solver}`",
        f"- Requested {count}, attempted {attempted}, "
        f"**accepted {len(accepted)}**, rejected {len(rejected)}",
        f"- Model calls: {calls}; total tokens: {tokens}",
        f"- Stopped early: {stop_reason}" if stop_reason else "- Ran to completion",
        "", "## Rejections by stage", "",
    ]
    lines += [f"- {s}: {n}" for s, n in sorted(by_stage.items())] or ["- none"]
    lines += ["", "## Accepted (awaiting human review)", ""]
    lines += [f"- `{r['id']}` [{r['tier']}] {r.get('topic')}: "
              f"`{r['answer_expression']}`" for r in accepted] or ["- none"]
    lines += ["", "## Rejected", ""]
    lines += [f"- `{r['id']}` [{r['rejected_at']}] {r.get('topic') or ''} — "
              f"{r['reason'][:200]}" for r in rejected] or ["- none"]
    report = "\n".join(lines) + "\n"
    with open(os.path.join(outdir, "README.md"), "w") as f:
        f.write(report)
    print("\n" + report)


if __name__ == "__main__":
    main()
