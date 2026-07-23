# Ground-truth provenance — `tw3-mixed-binary-text` (INV-P9, binary/unparseable fail-safe)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 3 (block-1 binary clause subsumed).**
  The diff is 2 files: 1 binary (`assets/logo.png`) + 1 text (`src/util.py`). Block 1
  (escalators): the binary/unparseable-path clause matches the `.png` → this alone would
  RUN. But note that block 3 (retained reach clause) ALSO fires independently here:
  `>1 changed file` (2 files) → RUN. So inquisitor RUNS either way; the block-1 binary
  clause is **belt-and-suspenders**, subsumed by block-3 in this (the only constructible
  reachable) shape. siege absent (non-security).

- **`verdict` = PASS.** All running legs clean → PASS.

## DROPPED: the single-file-*unparseable* dedicated fixture

The design listed a dedicated single-file-unparseable fixture as "the only input where
block 1's binary/unparseable clause is non-redundant." This plan **drops it** (sanctioned
by the handoff Minor: "name a concrete constructible artifact **or** drop the
dedicated-fixture claim"). Reason: git classifies a single changed path as **text**
(parses fine → not this clause) or **binary** — and a *single-file binary-only* diff
**short-circuits to PASS upstream** (a shipped warden failure-mode) so it never reaches the
predicate. There is thus no constructible single-file git state that is
"unparseable-but-not-binary" AND reaches the predicate. The binary/unparseable clause's
real reach is the **mixed** diff (this fixture), where it is subsumed by block-3
(`>1 file`) and stands purely as a fail-safe.

**Consequence for INV-P9:** after this drop, block-1's binary/unparseable clause retains
**NO isolating CI fixture** — in every constructible reachable (mixed binary+text) case it
is fully subsumed by block-3, so it is documentation-only, and its behavioral teeth defer
to the install-gated live pass (Acceptance Gate 2) alongside INV-P7/INV-P8/INV-P10. This
is a plan-level correction to the design's fixture enumeration — disclosed, not silent.

Schema-gated only; behavioral teeth defer to the live pass. Not a live run.
