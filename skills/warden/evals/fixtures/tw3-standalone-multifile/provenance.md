# Ground-truth provenance — `tw3-standalone-multifile` (T-W3 / INV-P3, "runs" branch)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 3.** The predicate is evaluated on
  the entry diff in order. Block 1 (escalators): none of the 3 changed paths match the
  INTERFACE/API/SCHEMA glob set or the DEPENDENCY/lockfile glob set, and there is no
  binary/unparseable path → miss. Block 2 (pure-doc bounded subtraction): the paths are
  code, not `.md`/`.rst`/`.adoc`, so NOT every path is pure-doc → miss. Block 3 (retained
  reach clause): the diff changes 3 files across 2 top-level modules, so `>1 changed file
  OR >1 top-level module` holds → **run inquisitor**. siege is absent (non-security). So
  the set is temper, delve, red-team, inquisitor.

- **`verdict` = PASS.** All running legs clean → disjunction all-false → PASS.

Pairs with `tw3-standalone-singlefile` (inquisitor SKIPPED via block-4 fall-through on a
single-file standalone diff) and contrasts with `tw8-full-singlefile` (inquisitor still
RUNS on a single-file diff in the `full` set). Outcome is unchanged from the old
single-clause predicate; only the block-path derivation was re-authored.
