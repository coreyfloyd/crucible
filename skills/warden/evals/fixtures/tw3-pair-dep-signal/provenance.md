# Ground-truth provenance — `tw3-pair-dep-signal` (INV-P7 monotonicity, dep pair — SIGNAL)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 1.** Block 1 (escalators): the single
  changed path `crates/app/Cargo.toml` matches `**/Cargo.toml` in the DEPENDENCY/lockfile
  glob set. A non-root nested path is chosen deliberately so the `**/` match is
  unambiguous for a strict live matcher (repo-root `Cargo.toml` could be read as not
  requiring the `**/` prefix) → **run inquisitor**. Blocks 2–4 never reached. siege absent
  (non-security).

- **`verdict` = PASS.** All running legs clean → PASS.

- **Pair role (INV-P7).** This is the SIGNAL of the dependency monotonicity pair. It
  differs from its base `tw3-pair-dep-base` (`src/util.py`, SKIP) ONLY by the
  dependency-glob signal, at the SAME 1-file count. Because both members are 1 file, block
  3 (`>1 file`) cannot fire for either, so the block-1 dependency escalator is the SOLE
  cause of this member's RUN. The pair isolates the skip→run monotonic transition to the
  escalator clause alone.

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
