"""Unit tests for tools/curriculum.py and tools/validate_curriculum.py."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "tools"))
import curriculum as cur  # noqa: E402
import validate_curriculum as vc  # noqa: E402

SEQ = "impulse-first"


class ExpandTests(unittest.TestCase):
    def setUp(self):
        self.order = cur.load_sequence(SEQ)["order"]

    def test_first_concept(self):
        s = cur.expand(SEQ, self.order[0], "algebra-trig")
        self.assertEqual(s.covered, {self.order[0]})
        self.assertEqual(s.forbidden, set(self.order[1:]))

    def test_last_concept(self):
        s = cur.expand(SEQ, self.order[-1], "full-calculus")
        self.assertEqual(s.covered, set(self.order))
        self.assertEqual(s.forbidden, frozenset())

    def test_cursor_absent_from_sequence(self):
        with self.assertRaises(ValueError):
            cur.expand(SEQ, "no-such-concept", "graphical")

    def test_preset_vs_literal_flags(self):
        a = cur.expand(SEQ, "impulse", "graphical")
        b = cur.expand(SEQ, "impulse", ["trig-decomposition", "graphical-slope",
                                         "graphical-area"])
        self.assertEqual(a.calculus, b.calculus)

    def test_unknown_preset_and_flag(self):
        with self.assertRaises(ValueError):
            cur.expand(SEQ, "impulse", "no-such-preset")
        with self.assertRaises(ValueError):
            cur.expand(SEQ, "impulse", ["no-such-flag"])

    def test_covered_and_forbidden_partition_order(self):
        s = cur.expand(SEQ, "impulse-momentum-theorem", "graphical")
        self.assertFalse(s.covered & s.forbidden)
        self.assertEqual(s.covered | s.forbidden, set(self.order))
        # the spec's key windows
        self.assertIn("newton-3rd", s.forbidden)
        self.assertIn("momentum-conservation-1d", s.forbidden)

    def test_work_before_kinetic_energy(self):
        s = cur.expand(SEQ, "work-variable-force", "graphical")
        self.assertIn("work-variable-force", s.covered)
        self.assertIn("kinetic-energy", s.forbidden)

    def test_representations_follow_cursor(self):
        early = cur.expand(SEQ, "newton-1st", "graphical")
        later = cur.expand(SEQ, "newton-2nd", "graphical")
        self.assertNotIn("free-body-diagram", early.representations)
        self.assertIn("free-body-diagram", later.representations)
        self.assertNotIn("energy-bar-chart", cur.expand(
            SEQ, self.order[-1], "graphical").representations)

    def test_request_target_must_be_covered(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"sequence": SEQ, "cursor": "impulse", "calculus": "graphical",
                       "target_concepts": ["kinetic-energy"]}, f)
        try:
            with self.assertRaises(ValueError):
                cur.load_request(f.name)
        finally:
            os.unlink(f.name)


class ValidatorTests(unittest.TestCase):
    """The validator must reject bad registries, not just accept good ones."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "curriculum")
        shutil.copytree(cur.ROOT, self.root)
        self._orig = cur.ROOT
        cur.ROOT = self.root

    def tearDown(self):
        cur.ROOT = self._orig
        shutil.rmtree(self.tmp)

    def _edit(self, rel, fn):
        p = os.path.join(self.root, rel)
        with open(p) as f:
            data = json.load(f)
        fn(data)
        with open(p, "w") as f:
            json.dump(data, f)

    def test_real_registry_is_valid(self):
        self.assertEqual(vc.validate(self.root), [])

    def test_out_of_order_sequence_rejected(self):
        def swap(seq):
            o = seq["order"]
            i, j = o.index("newton-3rd"), o.index("momentum-conservation-1d")
            o[i], o[j] = o[j], o[i]
        self._edit("sequences/impulse-first.json", swap)
        errs = vc.validate(self.root)
        self.assertTrue(any("before its prerequisite" in e for e in errs), errs)

    def test_cycle_rejected(self):
        self._edit("concepts.json",
                   lambda c: c["newton-1st"]["requires"].append("newton-2nd"))
        self.assertTrue(any("cycle" in e for e in vc.validate(self.root)))

    def test_unknown_concept_rejected(self):
        self._edit("sequences/impulse-first.json",
                   lambda s: s["order"].append("made-up-concept"))
        self.assertTrue(any("unknown concept" in e for e in vc.validate(self.root)))

    def test_bad_representation_anchor_rejected(self):
        self._edit("sequences/impulse-first.json",
                   lambda s: s["representations_at"].update(
                       {"energy-bar-chart": "not-in-order"}))
        self.assertTrue(any("representation" in e for e in vc.validate(self.root)))

    def test_bad_calculus_hint_rejected(self):
        self._edit("sequences/impulse-first.json",
                   lambda s: s["calculus_hint"].update(
                       {"power": {"any_of": ["telepathy"]}}))
        self.assertTrue(any("calculus_hint" in e for e in vc.validate(self.root)))

    def test_r1_denylist_rejected(self):
        self._edit("sequences/impulse-first.json",
                   lambda s: s.update(description="follows chapter 9"))
        self.assertTrue(any(e.startswith("R1") for e in vc.validate(self.root)))


if __name__ == "__main__":
    unittest.main()
