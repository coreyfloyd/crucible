# Ground-truth provenance — `tw3-doc-nested-depth` (INV-P8 any-depth match)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` = temper, delve, red-team — inquisitor SKIPPED via block 2.** Block 1
  (escalators): neither `sub/a.md` nor `sub/b.md` matches any INTERFACE/API/SCHEMA or
  DEPENDENCY/lockfile glob, no binary path → miss. Block 2 (pure-doc bounded subtraction):
  PURE-DOC is matched at **any depth** (gitignore-style), so the nested `sub/*.md` paths
  are pure-doc; EVERY path is pure-doc → **skip inquisitor**. siege absent (non-security).

- **`verdict` = PASS.** All three running legs clean → PASS.

- **Teeth (why 2 files, not 1).** The 2-file shape isolates the any-depth property: if the
  any-depth matcher were broken and read `sub/*.md` as non-doc, block 2 would fail, and
  block 3 (`>1 changed file`) would then force inquisitor to **run** — flipping this
  fixture's expected. A lone nested `.md` would skip via block-4 fall-through regardless of
  the matcher (block 3 needs `>1 file`), so it would prove nothing. Two nested docs make
  block 2 the only thing standing between SKIP and a block-3 RUN.

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
