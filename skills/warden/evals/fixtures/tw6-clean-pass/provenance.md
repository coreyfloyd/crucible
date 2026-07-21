# Ground-truth provenance — `tw6-clean-pass` (T-W6 / T-W2 / T-W8 / T-W5)

The `expected` outcome in `ground-truth.json` was derived **by hand** from
`skills/warden/SKILL.md`, applied to this fixture's diff shape + per-leg vector in
`descriptor.json`. It was **not** recorded from a live `/warden` run. Per-field
derivation (each field cites the governing SKILL.md rule):

- **`reviewer_set` = temper, delve, red-team, siege, inquisitor.**
  - temper, delve, red-team run **always** (§Reviewer set table, "Runs (`full`)" =
    always).
  - siege runs because the diff is **security-surface** (§Reviewer set: siege
    "conditional — security-surface diff"; the descriptor's diff touches an auth/session
    module).
  - inquisitor runs because the reviewer-set is **`full`**, where it is **unconditional**
    (§Reviewer set: inquisitor "always (unconditional)" in `full`; §"inquisitor coverage
    (S3)"; T-W8). So a single-file consideration does not skip it here.

- **`verdict` = PASS.** The gate is a **disjunction of native gates** (§Gate +
  enforcement: "BLOCKED if any run reviewer's native gate trips … else PASS"). Every leg
  is clean in the vector, so no native predicate trips → PASS. (T-W6.)

- **`marker`.** §Verdict marker ownership / I-W7: warden writes the **one**
  `gate-verdict-*.md` carrying the **caller's** (build's) PipelineID stamped with the
  aggregate verdict (`aggregate_marker_count: 1`, `aggregate_pipeline_id_source:
  "caller"`, `aggregate_build_tagged: true`). It invokes the quality-gate red-team leg
  with **warden's own run-id** as PipelineID, so the leg's marker is tagged with warden's
  run-id and is **not** build-tagged (`redteam_leg_marker_pipeline_id_source: "warden"`,
  `redteam_leg_marker_build_tagged: false`) — so build's PipelineID filter surfaces
  exactly one marker (T-W5).

- **`leg_commit_subjects` = [].** No leg tripped, so no leg ran a fix path; §Fix
  behavior — a clean pass produces no `chore(warden):` residual commits.
