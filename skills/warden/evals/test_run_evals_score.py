#!/usr/bin/env python3
"""`score` mechanics for the warden behavior-eval harness (#464) — fully synthetic,
no live agents. Stages a committed hand-authored RECORDED OUTCOME (a warden run's
produced reviewer-set / verdict / marker / per-leg commit subjects) + .collect-status,
and asserts the deterministic COMPARATOR's per-field pass/fail against each fixture's
INDEPENDENTLY-AUTHORED ground truth.

The anti-tautology proof lives here: `test_score_mismatch_fails` feeds a recorded
outcome that DISAGREES with the ground truth on load-bearing fields (a flipped
verdict AND a forbidden `fix:`-prefixed leg subject) and asserts the scorer reports
those fields FAILED — so `score` is proven to catch a bad outcome, not rubber-stamp
`expected == recorded`.

NOTE (mirrors delve/README): these recorded outcomes are the harness's stand-in for a
live `/warden` run. The scorer NEVER derives the verdict/reviewer-set from a per-leg
vector — it compares the recorded fields to the hand-authored expected fields only.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from skills.warden.evals import run_evals  # noqa: E402

_EVALS_DIR = pathlib.Path(__file__).resolve().parent

# A hand-authored recorded outcome for the `tw6-clean-pass` fixture that MATCHES its
# ground truth (all 5 reviewers ran on the security diff, clean → PASS, single
# build-tagged aggregate marker + non-build-tagged red-team leg marker, no residual
# fix commits). Scoring it against tw6's GT must report all fields PASS.
TW6_MATCH = {
    "reviewer_set": ["red-team", "temper", "delve", "siege", "inquisitor"],
    "verdict": "PASS",
    "marker": {
        "aggregate_marker_count": 1,
        "aggregate_pipeline_id_source": "caller",
        "aggregate_build_tagged": True,
        "redteam_leg_marker_pipeline_id_source": "warden",
        "redteam_leg_marker_build_tagged": False,
    },
    "leg_commit_subjects": [],
}

# A hand-authored recorded outcome for tw6 that DISAGREES with the ground truth on two
# load-bearing fields: the disjunction verdict is flipped (PASS→BLOCKED) and a leg
# residual subject uses the FORBIDDEN `fix:` prefix (M-c mandates non-`fix:`). The
# scorer must flag BOTH as failed — proving it is non-tautological.
TW6_MISMATCH = {
    "reviewer_set": ["red-team", "temper", "delve", "siege", "inquisitor"],
    "verdict": "BLOCKED",  # WRONG: GT is PASS
    "marker": {
        "aggregate_marker_count": 1,
        "aggregate_pipeline_id_source": "caller",
        "aggregate_build_tagged": True,
        "redteam_leg_marker_pipeline_id_source": "warden",
        "redteam_leg_marker_build_tagged": False,
    },
    "leg_commit_subjects": ["fix(warden): temper fixes <run-id>"],  # WRONG: GT is []
}


class _DispatchEnv(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("XDG_RUNTIME_DIR")
        os.environ["XDG_RUNTIME_DIR"] = self._tmp.name
        self._lr = _EVALS_DIR / "last_run.json"
        self._md = _EVALS_DIR / "results.md"
        self._saved = {p: (p.read_bytes() if p.exists() else None)
                       for p in (self._lr, self._md)}

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("XDG_RUNTIME_DIR", None)
        else:
            os.environ["XDG_RUNTIME_DIR"] = self._prev
        self._tmp.cleanup()
        for p, data in self._saved.items():
            if data is None:
                if p.exists():
                    p.unlink()
            else:
                p.write_bytes(data)

    def _stage_and_record(self, run_id, fixture, outcome,
                          *, sentinel="DISPATCH_STATUS: OK", collect=True):
        dispatch_dir = run_evals.stage(run_id, fixture=fixture)
        m = json.loads((dispatch_dir / "stage-manifest.json").read_text("utf-8"))
        cell = next(c for c in m["cells"] if c["fixture_id"] == fixture)
        body = json.dumps(outcome)
        text = f"{sentinel}\n\n{body}" if sentinel else body
        (dispatch_dir / cell["result_file"]).write_text(text, encoding="utf-8")
        if collect:
            (dispatch_dir / ".collect-status").write_text("", encoding="utf-8")
        return dispatch_dir

    def _score_one(self, run_id, fixture, outcome, **kw):
        self._stage_and_record(run_id, fixture, outcome, **kw)
        rc = run_evals.score(run_id)
        lr = json.loads((_EVALS_DIR / "last_run.json").read_text("utf-8"))
        return rc, lr


class TestScoreMatch(_DispatchEnv):
    def test_score_match_all_fields_pass(self):
        rc, lr = self._score_one("test-w-match", "tw6-clean-pass", TW6_MATCH)
        self.assertEqual(rc, 0)
        self.assertTrue(lr["complete"])
        pf = lr["per_fixture"][0]
        self.assertEqual(pf["fixture_id"], "tw6-clean-pass")
        self.assertTrue(pf["all_pass"])
        self.assertFalse(pf["dispatch_failed"])
        self.assertEqual(pf["n_pass"], pf["n_fields"])
        self.assertTrue(lr["aggregate"]["all_pass"])
        self.assertEqual(lr["aggregate"]["passed_fixtures"], 1)
        self.assertTrue((_EVALS_DIR / "results.md").exists())


class TestScoreMismatch(_DispatchEnv):
    def test_score_mismatch_fails(self):
        # THE ANTI-TAUTOLOGY PROOF: a recorded outcome that disagrees with the
        # independently-authored ground truth must be scored FAILED — the scorer is
        # not a rubber stamp of expected==recorded.
        rc, lr = self._score_one("test-w-mismatch", "tw6-clean-pass", TW6_MISMATCH)
        self.assertEqual(rc, 0)  # scoring RAN fine; the outcome under test failed
        pf = lr["per_fixture"][0]
        self.assertFalse(pf["all_pass"])
        self.assertFalse(lr["aggregate"]["all_pass"])
        self.assertEqual(lr["aggregate"]["passed_fixtures"], 0)

        by_field = {f["field"]: f for f in pf["fields"]}
        # verdict flip caught
        self.assertFalse(by_field["verdict"]["pass"])
        self.assertEqual(by_field["verdict"]["expected"], "PASS")
        self.assertEqual(by_field["verdict"]["recorded"], "BLOCKED")
        # forbidden `fix:` subject caught
        self.assertFalse(by_field["leg_commit_subjects"]["pass"])
        # the fields that DO agree still pass (the scorer is per-field, not all-or-none)
        self.assertTrue(by_field["reviewer_set"]["pass"])
        self.assertTrue(by_field["marker"]["pass"])


class TestScoreProtocol(_DispatchEnv):
    def test_score_refuses_without_collect_status(self):
        self._stage_and_record("test-w-nocollect", "tw6-clean-pass", TW6_MATCH,
                               collect=False)
        self.assertEqual(run_evals.score("test-w-nocollect"), 1)
        self.assertEqual(
            run_evals.score("test-w-nocollect", allow_incomplete=True), 0)
        lr = json.loads((_EVALS_DIR / "last_run.json").read_text("utf-8"))
        self.assertFalse(lr["complete"])

    def test_score_error_sentinel_marks_dispatch_failed(self):
        rc, lr = self._score_one("test-w-err", "tw6-clean-pass", TW6_MATCH,
                                 sentinel="DISPATCH_STATUS: ERROR")
        self.assertEqual(rc, 0)
        pf = lr["per_fixture"][0]
        self.assertTrue(pf["dispatch_failed"])
        self.assertFalse(pf["all_pass"])  # an unrecorded leg is not a pass
        self.assertFalse(lr["aggregate"]["all_pass"])

    def test_score_no_manifest_fails(self):
        self.assertEqual(run_evals.score("test-w-missing"), 1)

    def test_score_reviewer_set_is_order_insensitive(self):
        # reviewer_set is a SET of which reviewers ran; recording them in a different
        # order than the ground truth still matches (the comparator sorts before ==).
        shuffled = dict(TW6_MATCH)
        shuffled["reviewer_set"] = ["inquisitor", "temper", "siege", "delve",
                                    "red-team"]
        rc, lr = self._score_one("test-w-order", "tw6-clean-pass", shuffled)
        by_field = {f["field"]: f for f in lr["per_fixture"][0]["fields"]}
        self.assertTrue(by_field["reviewer_set"]["pass"])


if __name__ == "__main__":
    unittest.main()
