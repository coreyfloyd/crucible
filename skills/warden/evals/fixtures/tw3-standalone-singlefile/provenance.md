# Ground-truth provenance — `tw3-standalone-singlefile` (T-W3 / INV-P4, "skipped" branch)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` = temper, delve, red-team — inquisitor AND siege absent — via block-4
  fall-through.** The predicate is evaluated on the entry diff in order. Block 1
  (escalators): the single changed path is non-API, non-dependency code and there is no
  binary/unparseable path → miss. Block 2 (pure-doc bounded subtraction): the path is
  code, not `.md`/`.rst`/`.adoc`, so NOT every path is pure-doc → miss. Block 3 (retained
  reach clause): only 1 file in 1 module, so `>1 changed file OR >1 top-level module` is
  false → miss. Block 4 → **skip inquisitor**. siege is skipped (non-security). Both skips
  are **normal PASS inputs, not dead legs** (M5), so the set is just the three always-run
  legs.

- **`verdict` = PASS.** All three running legs clean → PASS.

Contrast `tw8-full-singlefile`: the SAME single-file diff in the `full` set still runs
inquisitor (unconditional), proving the reviewer-set split (S3 / T-W8). Outcome is
unchanged from the old single-clause predicate; only the block-path derivation was
re-authored (the old "single-file diff fails the `>1 file` condition" reasoning is now
block-4 fall-through after blocks 1–3 miss).
