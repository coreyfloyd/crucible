# Ground-truth provenance — `tw3-standalone-singlefile` (T-W3, "skipped" branch)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` = temper, delve, red-team — inquisitor AND siege absent.** §Reviewer
  set: in `standalone`, inquisitor is conditional on `>1 changed file OR >1 top-level
  module`; a single-file diff fails it, so inquisitor is condition-skipped. siege is
  skipped (non-security). Both skips are **normal PASS inputs, not dead legs** (M5), so
  the set is just the three always-run legs.

- **`verdict` = PASS.** All three running legs clean → PASS.

Contrast `tw8-full-singlefile`: the SAME single-file diff in the `full` set still runs
inquisitor (unconditional), proving the reviewer-set split (S3 / T-W8).
