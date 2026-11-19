#!/usr/bin/env python3
"""Render ACCEPTED records of a batch as LaTeX and/or Canvas-ready HTML.

  python3 tools/render.py candidates/<batch> [--format latex|canvas|both]

latex  -> out/latex/<sequence>_<cursor>.tex : standalone, amsmath, problems
          as an enumerate, answers in a separate section.
canvas -> out/canvas/<sequence>_<cursor>.html : MathJax-ready fragment,
          inline math \\( \\), display math \\[ \\], no <html>/<body>
          wrapper and no CSS, for pasting into a rich-content editor.
Batches without a request (topic mode) are named by batch id.

No network, no model calls. out/ is gitignored.
"""
import argparse
import html
import json
import os
import re
import sys

import sympy
from sympy import Symbol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402

# Symbol names that are also ordinary English words are left as text.
TEXT_WORDS = {"a", "A"}


def sym_latex(name):
    """theta -> \\theta, v_i -> v_{i}, F_avg -> F_{\\mathrm{avg}}."""
    base, _, sub = name.partition("_")
    out = sympy.latex(Symbol(base))
    if sub:
        if len(sub) > 1 and sub.isalpha() and sympy.latex(Symbol(sub)) == sub:
            out += r"_{\mathrm{" + sub + "}}"
        else:
            out += "_{" + sympy.latex(Symbol(sub)) + "}"
    return out


def unit_latex(unit):
    u = str(unit).strip()
    if u in ("", "1"):
        return ""
    u = re.sub(r"\^\(?(-?\d+)\)?", r"^{\1}", u)
    u = u.replace("*", r"\,")
    return r"\mathrm{" + u + "}"


def answer_latex(rec):
    expr = verify.safe_parse(rec["answer_expression"], list(rec["symbols"]))
    names = {Symbol(n, positive=True): sym_latex(n) for n in rec["symbols"]}
    return sympy.latex(expr, symbol_names=names)


def value_latex(x):
    s = f"{x:.4g}"
    if "e" in s:
        mant, exp = s.split("e")
        return rf"{mant} \times 10^{{{int(exp)}}}"
    return s


def split_text_and_symbols(text, names):
    """Yield ('text', str) / ('sym', name) pieces of a statement."""
    names = sorted((n for n in names if n not in TEXT_WORDS), key=len, reverse=True)
    if not names:
        yield "text", text
        return
    rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, names))
                    + r")(?![A-Za-z0-9_])")
    pos = 0
    for m in rx.finditer(text):
        yield "text", text[pos:m.start()]
        yield "sym", m.group(1)
        pos = m.end()
    yield "text", text[pos:]


LATEX_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
             "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
             "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
             "<": r"\(<\)", ">": r"\(>\)"}


def latex_text(s):
    s = "".join(LATEX_ESC.get(c, c) for c in s)
    # common Unicode the model emits
    for a, b in {"‑": "-", "–": "--", "—": "---", "’": "'",
                 "“": "``", "”": "''", "Δ": r"$\Delta$", "θ": r"$\theta$",
                 "μ": r"$\mu$", "°": r"$^\circ$"}.items():
        s = s.replace(a, b)
    return s


def statement_latex(rec):
    out = []
    for kind, piece in split_text_and_symbols(rec["statement"], rec["symbols"]):
        out.append(rf"\({sym_latex(piece)}\)" if kind == "sym" else latex_text(piece))
    return "".join(out)


def statement_html(rec):
    out = []
    for kind, piece in split_text_and_symbols(rec["statement"], rec["symbols"]):
        out.append(rf"\({html.escape(sym_latex(piece))}\)" if kind == "sym"
                   else html.escape(piece))
    return "".join(out)


def given_math(rec):
    parts = []
    for name, val in rec["given"].items():
        unit = unit_latex(rec["symbols"][name].get("unit", ""))
        v = verify.parse_value(val)
        num = value_latex(float(v)) if v.is_number and v.is_Float else sympy.latex(v)
        parts.append(f"{sym_latex(name)} = {num}" + (rf"\ {unit}" if unit else ""))
    return parts


def answer_math(rec):
    unit = unit_latex(rec["answer_unit"])
    return (answer_latex(rec),
            rf"\approx {value_latex(rec['expected_value'])}" + (rf"\ {unit}" if unit else ""))


def render_latex(records, title):
    L = [r"\documentclass[11pt]{article}", r"\usepackage{amsmath}",
         r"\usepackage[margin=1in]{geometry}", r"\begin{document}",
         r"\section*{" + latex_text(title) + "}", r"\begin{enumerate}"]
    for r in records:
        L.append(r"\item " + statement_latex(r))
        L.append(r"\\[4pt] \emph{Use} " + ", ".join(rf"\({g}\)" for g in given_math(r)) + ".")
    L += [r"\end{enumerate}", r"\section*{Answers}", r"\begin{enumerate}"]
    for r in records:
        sym, num = answer_math(r)
        L.append(rf"\item \[ {sym} {num} \]")
    L += [r"\end{enumerate}", r"\end{document}", ""]
    return "\n".join(L)


def render_canvas(records, title):
    H = [f"<h3>{html.escape(title)}</h3>", "<ol>"]
    for r in records:
        uses = ", ".join(rf"\({html.escape(g)}\)" for g in given_math(r))
        H.append(f"<li><p>{statement_html(r)}</p><p><em>Use</em> {uses}.</p></li>")
    H += ["</ol>", "<h3>Answers</h3>", "<ol>"]
    for r in records:
        sym, num = answer_math(r)
        H.append(rf"<li>\[ {html.escape(sym)} {html.escape(num)} \]</li>")
    H += ["</ol>", ""]
    return "\n".join(H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", help="candidates/<batch> directory")
    ap.add_argument("--format", choices=["latex", "canvas", "both"], default="both")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    with open(os.path.join(args.batch, "accepted.json")) as f:
        records = json.load(f)
    if not records:
        sys.exit("No accepted records to render.")
    req_path = os.path.join(args.batch, "request.json")
    if os.path.exists(req_path):
        with open(req_path) as f:
            req = json.load(f)
        stem = f"{req['sequence']}_{req['cursor']}"
    else:
        stem = os.path.basename(os.path.normpath(args.batch))
    title = "Problems"

    written = []
    if args.format in ("latex", "both"):
        p = os.path.join(args.out, "latex", f"{stem}.tex")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(render_latex(records, title))
        written.append(p)
    if args.format in ("canvas", "both"):
        p = os.path.join(args.out, "canvas", f"{stem}.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(render_canvas(records, title))
        written.append(p)
    for p in written:
        print(f"wrote {p} ({len(records)} problems)")


if __name__ == "__main__":
    main()
