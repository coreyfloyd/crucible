# Ground-truth provenance — `tw5-marker-temper-fix` (T-W5 / I-W7)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` = temper, delve, red-team, inquisitor.** inquisitor unconditional in
  `full`; siege absent (non-security) — §Reviewer set.

- **`verdict` = PASS.** temper trips but FIXES to termination (§Fix behavior: temper
  "loops+fixes to merge-verdict termination"); after the fix no native gate trips, so the
  disjunction is all-false → PASS. The verdict binds the **post-commit frozen HEAD** that
  contains temper's fix (§Ordering step 4, F-A).

- **`marker`** — §Verdict marker ownership / I-W7. warden writes the **one**
  `gate-verdict-*.md` carrying the **caller's** PipelineID with the aggregate verdict
  (`aggregate_marker_count: 1`, `aggregate_pipeline_id_source: "caller"`,
  `aggregate_build_tagged: true`), stamped **after the freeze** (so it binds the HEAD that
  contains the fix). The quality-gate red-team leg is invoked with **warden's own run-id**
  as PipelineID, so its `gate-verdict-<warden-run-id>.md` is tagged with warden's run-id
  and **never matches build's PipelineID filter** (`redteam_leg_marker_pipeline_id_source:
  "warden"`, `redteam_leg_marker_build_tagged: false`).

- **`leg_commit_subjects` = ["chore(warden): temper fixes <run-id>"]** — §Fix behavior +
  M-c. temper edits the working tree in uncommitted mode and never advances HEAD, so
  warden commits its residual with a **non-`fix:`** `chore(warden): temper fixes <run-id>`
  subject (the actual run-id is elided to `<run-id>` when recording — an ID token, not a
  cross-scale normalization). A `fix:` prefix here would be a rule violation (see the
  mismatch proof in test_run_evals_score.py).
