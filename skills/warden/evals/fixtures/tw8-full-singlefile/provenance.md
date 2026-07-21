# Ground-truth provenance — `tw8-full-singlefile` (T-W8)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` includes inquisitor despite the single-file diff.** §Reviewer set +
  §"inquisitor coverage (S3 resolution)": in the `full` set inquisitor is
  "**always (unconditional)** — preserves build Phase 4 Step 4 coverage", so a single-file
  build does not lose the inquisitor pass it gets today. The diff-shape condition applies
  only in `standalone`. siege is absent (non-security). So the set is temper, delve,
  red-team, inquisitor.

- **`verdict` = PASS.** All running legs clean → PASS.

This is the load-bearing contrast to `tw3-standalone-singlefile`: SAME single-file diff,
inquisitor present in `full` and absent in `standalone` — the reviewer-set split.
