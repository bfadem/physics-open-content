"""Golden-file and R3 denylist tests for tools/prompt.py."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "tools"))
import check_rules  # noqa: E402
import curriculum as cur  # noqa: E402
import prompt as P  # noqa: E402

HERE = os.path.dirname(__file__)
GOLDEN = os.path.join(HERE, "golden",
                      "prompt_impulse-momentum-theorem_graphical_multi-step_3.txt")
BANNED_WORDS = ["sequence", "curriculum", "course", "syllabus", "textbook",
                "semester", "lecture", "university", "college"]


def every_prompt():
    seq = cur.load_sequence("impulse-first")
    for preset in cur.load_calculus()["presets"]:
        for cursor in seq["order"]:
            state = cur.expand(seq, cursor, preset)
            for tier in P.TIER_GUIDE:
                yield state, P.build_prompt(state, [cursor], tier, 2)


class GoldenTest(unittest.TestCase):
    def test_matches_golden(self):
        state = cur.expand("impulse-first", "impulse-momentum-theorem", "graphical")
        got = P.build_prompt(state, ["impulse-momentum-theorem"], "multi-step", 3)
        with open(GOLDEN) as f:
            self.assertEqual(got, f.read(),
                             "prompt changed; regenerate the golden file deliberately")


class R3DenylistTest(unittest.TestCase):
    """Nothing but explicit sets of ordinary vocabulary reaches a provider."""

    @classmethod
    def setUpClass(cls):
        cls.ids = set(cur.load_concepts()) | set(cur.load_calculus()["flags"]) \
            | set(cur.load_representations()) | set(cur.load_calculus()["presets"])
        # Single-word IDs (e.g. "torque") are indistinguishable from ordinary
        # vocabulary; hyphenated IDs are the distinctive form and are asserted.
        cls.hyphenated = sorted(i for i in cls.ids if "-" in i)

    def test_every_prompt_is_clean(self):
        n = 0
        for state, text in every_prompt():
            n += 1
            low = text.lower()
            self.assertEqual(check_rules.scan_text(text), [],
                             f"R1 pattern in prompt at {state.cursor}")
            self.assertNotIn(state.sequence_name, text)
            for w in BANNED_WORDS:
                self.assertIsNone(re.search(rf"\b{w}\b", low),
                                  f"banned word {w!r} at {state.cursor}")
            for i in self.hyphenated:
                self.assertIsNone(re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text),
                                  f"ID {i!r} leaked at {state.cursor}")
        self.assertGreater(n, 100)

    def test_forbidden_labels_are_listed(self):
        state = cur.expand("impulse-first", "impulse", "algebra-trig")
        text = P.build_prompt(state, ["impulse"], "plug-and-chug", 1)
        self.assertIn("Newton's third law", text)
        self.assertIn("kinetic energy", text)
        self.assertNotIn("area under a graph", text)   # flag not in algebra-trig


class LabelMappingTest(unittest.TestCase):
    def setUp(self):
        self.state = cur.expand("impulse-first", "work-variable-force", "graphical")

    def test_round_trip(self):
        meta = {"requires": ["Spring force and Hooke's law", "work done by a variable force"],
                "intended_path": "work done by a variable force",
                "trivial_if_available": [],
                "representations": ["free-body diagram"],
                "calculus_all_of": [],
                "calculus_any_of": ["read an accumulated quantity as the area under a graph"]}
        out = P.map_curriculum_fields(meta, self.state)
        self.assertEqual(out["requires"], ["spring-force-hookes-law", "work-variable-force"])
        self.assertEqual(out["intended_path"], "work-variable-force")
        self.assertEqual(out["calculus_any_of"], ["graphical-area"])
        self.assertEqual(out["sequence"], "impulse-first")
        self.assertEqual(out["cursor"], "work-variable-force")

    def test_tolerated_variants(self):
        # Real model output from the first gated batch: article dropped,
        # head-before-colon only, and a non-breaking hyphen (U+2011).
        cmap = cur.concept_label_map()
        for lab in ["impulse-momentum theorem: impulse equals change in momentum",
                    "impulse-momentum theorem", "The impulse\u2011momentum theorem",
                    "rotational inertia", "Newton\u2019s second law"]:
            self.assertEqual(len(cur.labels_to_ids([lab], cmap, "concept")), 1, lab)

    def test_unicode_cannot_evade_lexical_scan(self):
        import verify
        state = cur.expand("impulse-first", "impulse", "graphical")
        rec = {"statement": "By Newton\u2019s third law and the impulse\u2011momentum "
                            "theorem, find J.", "symbols": {},
               "curriculum": {"requires": [], "intended_path": None}}
        lex = [r for r in verify.curriculum_checks(rec, state) if r[0] == "lexical"][0]
        self.assertFalse(lex[1])
        self.assertIn("newton-3rd", lex[2])
        self.assertIn("impulse-momentum-theorem", lex[2])

    def test_math_and_diagram_labels_under_requires_are_rerouted(self):
        # Real model output (batch 20261119-1802): the trig calculus flag's
        # label listed as a required concept.
        meta = {"requires": ["work as the dot product of force and displacement",
                             "resolve a vector into components using sine and cosine",
                             "free-body diagram"],
                "intended_path": "work as the dot product of force and displacement"}
        out = P.map_curriculum_fields(meta, self.state)
        self.assertEqual(out["requires"], ["work-dot-product"])
        self.assertEqual(out["calculus_all_of"], ["trig-decomposition"])
        self.assertEqual(out["representations"], ["free-body-diagram"])

    def test_unknown_label_rejected(self):
        with self.assertRaises(ValueError):
            P.map_curriculum_fields({"requires": ["quantum tunnelling"],
                                     "intended_path": "kinetic energy"}, self.state)


if __name__ == "__main__":
    unittest.main()
