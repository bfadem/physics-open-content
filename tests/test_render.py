"""Tests for tools/render.py using the guard records as input."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "tools"))
import render  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)


class RenderTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "problems", "false-rejection-guards.json")) as f:
            self.records = json.load(f)

    def test_canvas_is_a_bare_fragment(self):
        out = render.render_canvas(self.records, "Problems")
        for banned in ("<html", "<body", "<style", "<link", "<script", "$$"):
            self.assertNotIn(banned, out.lower())
        self.assertIn(r"\(", out)
        self.assertIn(r"\[", out)

    def test_latex_is_standalone_and_escaped(self):
        out = render.render_latex(self.records, "Problems")
        self.assertTrue(out.startswith(r"\documentclass"))
        self.assertIn(r"\usepackage{amsmath}", out)
        self.assertIn(r"\section*{Answers}", out)
        self.assertEqual(out.count(r"\begin{enumerate}"), 2)

    def test_symbol_latex(self):
        self.assertEqual(render.sym_latex("theta"), r"\theta")
        self.assertEqual(render.sym_latex("v_i"), "v_{i}")
        self.assertEqual(render.sym_latex("F_avg"), r"F_{\mathrm{avg}}")
        self.assertEqual(render.sym_latex("mu_k"), r"\mu_{k}")

    def test_text_escaping(self):
        self.assertEqual(render.latex_text("50% & v_f < v_i"),
                         r"50\% \& v\_f \(<\) v\_i")


if __name__ == "__main__":
    unittest.main()
