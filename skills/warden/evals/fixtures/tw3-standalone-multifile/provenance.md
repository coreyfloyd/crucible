# Ground-truth provenance — `tw3-standalone-multifile` (T-W3, "runs" branch)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` includes inquisitor.** §Reviewer set: in `standalone`, inquisitor is
  "conditional — `>1 changed file OR >1 top-level module touched`". This diff changes 3
  files across 2 modules, so the condition holds and inquisitor RUNS. siege is absent
  (non-security). So the set is temper, delve, red-team, inquisitor.

- **`verdict` = PASS.** All running legs clean → disjunction all-false → PASS.

Pairs with `tw3-standalone-singlefile` (inquisitor SKIPPED on a single-file standalone
diff) and contrasts with `tw8-full-singlefile` (inquisitor still RUNS on a single-file
diff in the `full` set).
