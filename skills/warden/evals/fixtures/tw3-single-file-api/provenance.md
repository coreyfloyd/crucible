# Ground-truth provenance — `tw3-single-file-api` (INV-P10, API escalation)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 1.** Block 1 (escalators): the single
  changed path `src/api/util.py` matches `**/api/**` in the INTERFACE/API/SCHEMA glob set
  (`api/` is a directory segment with content after it) → **run inquisitor** (escalator
  dominates; strictly additive). Blocks 2–4 are never reached. siege absent (non-security).
  So the set is temper, delve, red-team, inquisitor.

- **`verdict` = PASS.** All running legs clean → PASS.

- **Contrast with today.** Under the old crude clause (`>1 changed file OR >1 top-level
  module`) this single-file diff would SKIP inquisitor; the risk-aware predicate RUNS it
  because an interface/API change is high-blast-radius. That flip is exactly what INV-P10
  asserts.

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
