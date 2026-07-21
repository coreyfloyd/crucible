#!/usr/bin/env python3
"""Fixture-integrity tests for the warden behavior-eval harness (#464).

`score` only ever parses a fixture's `ground-truth.json` when that fixture is recorded +
scored, and the CI score test records only `tw6`. Without this suite, a malformed or
empty `expected` in any OTHER fixture (tw1/tw5/tw9/tw11/…) would rot undetected. This
suite parses EVERY committed fixture at authoring time and pins the schema invariants the
scorer relies on — most importantly that `expected` is a NON-EMPTY dict, so the
anti-vacuous-pass property (`all([])` is True) can never be defeated by a stray fixture.
"""
import json
import pathlib
import unittest

_FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"
_ALLOWED_FIELDS = {"reviewer_set", "verdict", "marker", "leg_commit_subjects",
                   "block_reason"}
_REVIEWERS = {"temper", "delve", "red-team", "siege", "inquisitor"}


def _fixture_dirs():
    return sorted(d for d in _FIXTURES_DIR.iterdir()
                  if d.is_dir() and (d / "ground-truth.json").exists())


class TestFixtureIntegrity(unittest.TestCase):
    def test_at_least_the_expected_fixtures_exist(self):
        names = {d.name for d in _fixture_dirs()}
        # The mechanical decision points the dispatch enumerates.
        for required in ("tw1-single-gate-trip", "tw6-clean-pass",
                         "tw2-siege-nonsecurity", "tw3-standalone-multifile",
                         "tw3-standalone-singlefile", "tw8-full-singlefile",
                         "tw5-marker-temper-fix", "tw9-residual-nonfix",
                         "tw11-delve-block"):
            self.assertIn(required, names)

    def test_every_ground_truth_has_a_nonempty_expected(self):
        for d in _fixture_dirs():
            gt = json.loads((d / "ground-truth.json").read_text("utf-8"))
            self.assertIn("expected", gt, f"{d.name}: no `expected`")
            expected = gt["expected"]
            self.assertIsInstance(expected, dict, f"{d.name}: `expected` not a dict")
            # NON-EMPTY: a fixture that asserts nothing can never fail (all([])==True).
            self.assertTrue(expected, f"{d.name}: `expected` is empty (vacuous pass)")
            # every asserted field is a known outcome field
            unknown = set(expected) - _ALLOWED_FIELDS
            self.assertFalse(unknown, f"{d.name}: unknown expected field(s) {unknown}")

    def test_expected_field_shapes(self):
        for d in _fixture_dirs():
            expected = json.loads(
                (d / "ground-truth.json").read_text("utf-8"))["expected"]
            if "reviewer_set" in expected:
                rs = expected["reviewer_set"]
                self.assertIsInstance(rs, list)
                self.assertTrue(set(rs) <= _REVIEWERS,
                                f"{d.name}: reviewer_set has unknown reviewers")
                self.assertIn("temper", rs, f"{d.name}: temper always runs")
            if "verdict" in expected:
                self.assertIn(expected["verdict"], ("PASS", "BLOCKED"))
            if "leg_commit_subjects" in expected:
                for s in expected["leg_commit_subjects"]:
                    # M-c: every warden-owned residual commit is NON-`fix:`.
                    self.assertFalse(s.startswith("fix"),
                                     f"{d.name}: `fix:`-prefixed leg subject {s!r} "
                                     f"violates M-c (must be chore(warden): …)")
                    self.assertTrue(s.startswith("chore(warden):"),
                                    f"{d.name}: leg subject {s!r} not chore(warden):")

    def test_descriptor_present_and_carries_the_operator_vector(self):
        # descriptor.json is the OPERATOR INPUT (per-leg vector); the scorer never reads
        # it. Pin that it exists + carries a vector, so stage always has a note to render.
        for d in _fixture_dirs():
            desc = json.loads((d / "descriptor.json").read_text("utf-8"))
            self.assertIn("per_leg_verdict_vector", desc, f"{d.name}: no leg vector")
            self.assertIsInstance(desc["per_leg_verdict_vector"], dict)
            self.assertIn(desc.get("reviewer_set_mode"), ("full", "standalone"),
                          f"{d.name}: bad reviewer_set_mode")
            self.assertTrue((d / "provenance.md").exists(),
                            f"{d.name}: no provenance.md (hand-derivation record)")


if __name__ == "__main__":
    unittest.main()
