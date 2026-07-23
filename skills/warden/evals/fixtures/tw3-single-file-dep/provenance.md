# Ground-truth provenance — `tw3-single-file-dep` (INV-P10, dependency/supply-chain)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 1.** Block 1 (escalators): the single
  changed path `web/package.json` matches `**/package.json` in the DEPENDENCY/lockfile
  glob set (nested path chosen so the `**/` match is unambiguous for a strict live
  matcher) → **run inquisitor**. Blocks 2–4 are never reached. siege absent (non-security).
  So the set is temper, delve, red-team, inquisitor.

- **`verdict` = PASS.** All running legs clean → PASS.

- **Contrast with today.** A single-file dependency-manifest change would SKIP under the
  old `>1 file` clause; the risk-aware predicate RUNS it because a supply-chain/dependency
  edit is high-blast-radius. That flip is what INV-P10 asserts on the dependency axis.

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
