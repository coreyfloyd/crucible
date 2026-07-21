# Ground-truth provenance — `tw9-residual-nonfix` (T-W9, mechanical part)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

**Scope note.** T-W9 has a live-ordering half (a later fixer's commits trigger a scoped
re-temper *before* the red-team leg) that is inherently a live sequencing property — it
is routed to Acceptance-Gate-2, NOT scored here. This fixture scores only the two
**mechanical** halves:

- **`leg_commit_subjects`** — §Fix behavior (Universal per-leg residual commit, I-W6) +
  M-c. temper (uncommitted mode) and `delve --fix` (working-tree only) never commit, so
  warden commits each leg's residual with a **non-`fix:`** `chore(warden): <leg> fixes
  <run-id>` subject. inquisitor and siege self-commit and leave **no** residual, so they
  contribute no subject. red-team is clean (no fix rounds) → no `chore(warden): red-team
  fixes` subject. Hence exactly the two subjects listed, in leg order (temper before
  delve, per §Ordering step 1 build-mirroring order). The `<run-id>` token stands in for
  the elided actual run-id (an ID token, not a cross-scale normalization). Every subject
  is non-`fix:` — the M-c mandate that keeps warden-owned commits out of
  calibration-reconcile's `fix`/`hotfix` candidate walk.

- **`verdict` = PASS (empty terminating range benignly passes).** §Ordering step 4:
  after the red-team leg, warden runs plain report-only delve over `SHA_pre_redteam..HEAD`.
  The red-team leg made no edits, so that range is **empty**; "the terminating delve
  reviews an empty range and benignly passes — there is no 'non-empty range'
  requirement." With every leg clean-after-fix, the disjunction is all-false → PASS.
