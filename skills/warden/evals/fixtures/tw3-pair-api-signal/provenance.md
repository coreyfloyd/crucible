# Ground-truth provenance — `tw3-pair-api-signal` (INV-P7 monotonicity, API pair — SIGNAL)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 1.** Block 1 (escalators): the single
  changed path `src/api/util.py` matches `**/api/**` in the INTERFACE/API/SCHEMA glob set
  (`api/` is a directory segment with content after it) → **run inquisitor**. Blocks 2–4
  never reached. siege absent (non-security).

- **`verdict` = PASS.** All running legs clean → PASS.

- **Pair role (INV-P7).** This is the SIGNAL of the API monotonicity pair. It differs from
  its base `tw3-pair-api-base` (`src/util.py`, SKIP) ONLY by the API-glob signal, at the
  SAME 1-file count. Because both members are 1 file, block 3 (`>1 file`) cannot fire for
  either, so the block-1 escalator is the SOLE cause of this member's RUN. The pair thus
  isolates the skip→run monotonic transition to the escalator clause alone.

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
