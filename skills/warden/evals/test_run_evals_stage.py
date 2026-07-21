#!/usr/bin/env python3
"""`stage` mechanics for the warden behavior-eval harness (#464) — fully synthetic, no
live agents. Asserts stage writes a well-formed stage-manifest.json enumerating one cell
per fixture with the operator dispatch note + result_file + reviewer_set_mode.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from skills.warden.evals import run_evals  # noqa: E402

_FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


class TestStage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("XDG_RUNTIME_DIR")
        os.environ["XDG_RUNTIME_DIR"] = self._tmp.name

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("XDG_RUNTIME_DIR", None)
        else:
            os.environ["XDG_RUNTIME_DIR"] = self._prev
        self._tmp.cleanup()

    def test_stage_writes_wellformed_manifest(self):
        dispatch_dir = run_evals.stage("test-w-stage-1")
        manifest_path = dispatch_dir / "stage-manifest.json"
        self.assertTrue(manifest_path.exists())
        m = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(m["run_id"], "test-w-stage-1")
        self.assertEqual(m["engine"], "warden")
        self.assertGreaterEqual(m["fixtures"], 1)
        self.assertEqual(len(m["cells"]), m["fixtures"])

        # Every fixture dir with a ground-truth.json must appear as a cell.
        gt_dirs = {d.name for d in _FIXTURES_DIR.iterdir()
                   if d.is_dir() and (d / "ground-truth.json").exists()}
        self.assertEqual({c["fixture_id"] for c in m["cells"]}, gt_dirs)

        c6 = next(c for c in m["cells"] if c["fixture_id"] == "tw6-clean-pass")
        self.assertEqual(c6["result_file"], "tw6-clean-pass-outcome.json")
        self.assertEqual(c6["reviewer_set_mode"], "full")
        self.assertIn("/warden", c6["dispatch_note"])
        self.assertIn("DISPATCH_STATUS: OK", c6["dispatch_note"])
        self.assertIn(".collect-status", c6["dispatch_note"])
        # The standalone fixture carries its mode through to the cell.
        c3 = next(c for c in m["cells"]
                  if c["fixture_id"] == "tw3-standalone-singlefile")
        self.assertEqual(c3["reviewer_set_mode"], "standalone")

    def test_stage_named_fixture(self):
        dispatch_dir = run_evals.stage("test-w-stage-named",
                                       fixture="tw6-clean-pass")
        m = json.loads((dispatch_dir / "stage-manifest.json").read_text("utf-8"))
        self.assertEqual([c["fixture_id"] for c in m["cells"]], ["tw6-clean-pass"])

    def test_stage_unknown_fixture_raises(self):
        with self.assertRaises(ValueError):
            run_evals.stage("test-w-stage-x", fixture="does-not-exist")

    def test_stage_refuses_existing_dir_without_force(self):
        run_evals.stage("test-w-stage-dup")
        with self.assertRaises(FileExistsError):
            run_evals.stage("test-w-stage-dup")
        run_evals.stage("test-w-stage-dup", force=True)  # force re-stages cleanly


if __name__ == "__main__":
    unittest.main()
