---
name: warden
description: 'Consolidated pre-push review gate — runs the full reviewer set (temper, delve, red-team, plus siege/inquisitor when the diff warrants) as one gate and emits a single PASS/BLOCKED verdict. Use when you want the *complete* pre-push bar in one call — "gate this before I push", "run the full review gate", "run all the reviewers", "warden". NOT for a single-reviewer pass: a fresh-eyes code review stays with temper, red-teaming a design/plan stays with quality-gate, a bug-hunt on a diff stays with delve.'
---

# Warden

<!-- CANONICAL: shared/dispatch-convention.md -->
<!-- CANONICAL: shared/return-convention.md -->

## Overview

warden is an **orchestrator-tier pre-push review gate** — a peer of
build/finish/quality-gate, not a find-and-report-only leaf reviewer. It
consolidates the pre-push review passes (temper, delve, red-team, plus
siege/inquisitor when the diff warrants) into a single gate that emits one
PASS/BLOCKED verdict. Like build and finish, warden is permitted to drive
fixes; the report-only rule binds only leaf reviewers.

warden runs each reviewer on its **own** severity scale — there is **no
cross-scale normalization** (`severity-verdict-contract.md`). The gate is a
**disjunction of native gates** (the boolean OR of each leg's native verdict),
and the combined report is sectioned per reviewer, never one merged ranking.

## Reviewer set (native scales, no normalization)

warden runs each reviewer on its **own** severity scale. Cross-scale
conversion is forbidden (`shared/severity-verdict-contract.md:155-174`); the
gate is a **disjunction of native gates**, and the combined report is
**sectioned per reviewer**, never one merged ranking.

The "Runs" column is split by **reviewer-set** (the dispatch parameter
`reviewer-set: full | standalone`): `full` is the build/finish pipeline set,
`standalone` is a bare `/warden` invocation where per-push cost matters.

| Reviewer | Runs (`full`) | Runs (`standalone`) | Native gate predicate (blocks if true) | Notes |
|---|---|---|---|---|
| temper | always | always | `T = {CONFIRMED,PLAUSIBLE} × {Critical,Important}` non-empty | the merge-verdict loop |
| delve | always | always | any kept finding at `{CONFIRMED,PLAUSIBLE} × {Critical,Important}` (trio scale; `PLAUSIBLE@Crit/Imp` is a real regression per contract) | delve is **report-only with no fix loop** — warden applies the predicate to delve's kept findings and owns the fix path (see Fix behavior) |
| red-team (via quality-gate) | always | always | quality-gate verdict ≠ PASS (Fatal>0 ∨ Significant>0) | delegates to existing `crucible:quality-gate` on the `code` artifact to reuse its red-team loop, invoked so the QG leg **re-dispatches siege** exactly as build's Step-6 gate does (warden does **not** suppress the QG-internal siege) — the second of warden's two siege passes (I-W4 / S-A); the leg's marker is **not** build-tagged (see Integration mapping / I-W7) — warden owns the aggregate verdict marker; it writes **no** calibration ledger entry (each leg self-emits its native entry, I-W8) |
| siege | conditional — security-surface diff (reuse build's existing Step 5.5 trigger) | conditional — same security-surface trigger | Critical>0 ∨ High>0 | heavy 6-agent Opus audit; not run on non-security diffs. **siege is warden's own native leg on its own CVSS scale** (disjunction-of-native-gates, a LOCKED decision). warden sieges **twice**, **coverage-equal to build's two sieges (position redistributed across the two passes)**: warden's own siege leg at step-1 HEAD (≈ build Step 5.5), and the QG red-team leg's internal siege auto-dispatch at `SHA_pre_redteam` (≈ build Step 6) — the QG leg is invoked so it **re-dispatches** its internal siege as build does (warden does **not** suppress it) (I-W4 / S-A) |
| inquisitor | **always (unconditional)** — preserves build Phase 4 Step 4 coverage | conditional — `>1 changed file OR >1 top-level module touched` | any adversarial test `Result: FAIL` | heavy 5-dim fan-out. In the `full` set it stays unconditional so a single-file build does **not** lose the inquisitor pass it gets today; the diff-shape condition applies only standalone, where per-push cost matters |

temper and delve share the trio contract scale, so their two legs use one
predicate; the other three keep their own. No leg's severity is converted into
another's.

**inquisitor coverage (S3 resolution).** build Phase 4 Step 4 runs inquisitor
unconditionally today. Making it conditional everywhere would silently narrow
the strongest orchestrator's review coverage on single-file builds. So the
trigger is split by reviewer-set: **unconditional in `full`** (no build
regression), **conditional (multi-file / cross-module) in `standalone`** where
the per-push Opus fan-out cost is the dominant concern. T-W8 asserts the `full`
behavior.

## Fix behavior

Each leg's fix path is **not** uniform — the earlier "warden drives each
reviewer's existing fix loop" framing was wrong for delve, which has no loop.
And an earlier premise — "each fixer leg commits its own working-tree delta" — is
**false for temper**: temper's fixer **edits the working tree** (its Step 3 fixes
every member of `T`, `temper/SKILL.md:188`) but in **uncommitted mode**
(`temper/SKILL.md:197-198`) **never advances HEAD**. The `git stash create` temper
uses in that mode only snapshots the tree to compute each round's fix-delta scope —
*that snapshot* is what leaves HEAD, the index, and the working tree untouched; it is
**not** how the fix is applied. So temper's edits sit in the working tree,
**uncommitted**, for warden to commit. delve `--fix` and the
quality-gate red-team leg likewise edit the working tree and never commit; only
inquisitor (`inquisitor/SKILL.md:163`) and siege self-commit. So warden cannot assume
"the leg committed its own fix" — it must commit each leg's residual itself, or the
frozen HEAD can omit temper's (or delve's, or the red-team leg's) fixes.

**Universal per-leg residual commit (I-W6).** After **each** fixer leg terminates —
and **before the next fixer leg runs** — warden commits **that leg's residual
working-tree changes, if any**. Under the clean-working-tree precondition (below), a
leg's residual **is** the entire set of uncommitted changes — tracked edits **and
newly-created (untracked) files alike** — so warden commits **all** of it with
`git add -A && git commit` (which stages new files too, so a fixer leg that creates a
new module/test lands it in the frozen HEAD) and a
leg-labeled **non-`fix:`** subject (`chore(warden): temper fixes <run-id>`,
`chore(warden): delve fixes <run-id>`, `chore(warden): red-team fixes <run-id>`, etc. —
see M-c). Committing the full residual (rather than path-scoping it) captures delve's
out-of-scope `--fix` edits **by construction** — the clean-tree base guarantees the only
uncommitted changes (tracked **or** untracked) are the current leg's delta, so there is
nothing unrelated to sweep. A leg that already self-committed (inquisitor, siege) leaves **no residual**, so
the commit is a no-op for it; temper, delve, and the red-team leg — which never commit —
get their edits committed here. This is a **single universal rule**, not a per-leg
special case, and it corrects the false "each fixer leg commits its own delta" premise
to: *warden commits each leg's residual; self-committing legs leave none;
temper/delve/red-team leave working-tree edits that warden commits.* HEAD advances as
each leg completes, so downstream `finish` / PR-creation see every leg's fixes **already
committed**, and — because each residual is committed once, between legs — there is **no
double-commit**.

**Working-tree-clean precondition (the inductive base — ASSERTED on all paths).** For
"commit this leg's residual" to capture only that leg's delta (never unrelated edits),
warden requires a **clean working tree at entry**, and **asserts** it on **every** path:
`git status --porcelain` must be **fully empty** — **no** tracked modifications **and no
untracked files**. This is a hard precondition, not an assumption; the fully-empty check
(rather than "empty for tracked files") is what makes `git add -A && git commit` safe —
the only thing it can stage after a leg is exactly that leg's delta, so per-leg
attribution holds by construction (a pre-existing entry-untracked file could otherwise be
swept into the first leg's `chore(warden):` commit). A standalone `/warden` on a
**dirty-or-untracked** tree **REFUSES** with an
actionable error (`commit, stash, or clean untracked files, then re-run /warden`) —
matching how warden already treats a detached HEAD (require explicit action from the
user). Inside **build**, build **guarantees** a fully-clean tree at warden entry (see the
build-side integration requirement in Integration mapping): a dirty **or untracked** tree
at build→warden entry is a **surfaced build/test defect** (warden errors) — it is never
silently swept into the first `chore(warden):` commit. **Standalone `/warden` and
standalone `/finish` both fall to the assert-and-REFUSE rule** (only *build* supplies a
clean-tree guarantee — finish has no clean-tree gate of its own; see the finish
integration note). Without this asserted base the per-leg residual is not well-defined; it
is the base of the induction that makes the frozen HEAD provably contain every leg's
fixes.

Per leg:

- **temper** — loops+fixes to merge-verdict termination (its own loop), in
  **uncommitted mode** (`temper/SKILL.md:198`, HEAD untouched), so
  **warden commits temper's residual working-tree changes** itself
  (`chore(warden): temper fixes <run-id>`, non-`fix:` per M-c) per the universal rule
  above.
- **quality-gate (red-team leg)** — loops+fixes its red-team rounds (its own
  loop). quality-gate's `code` fixes are **working-tree edits, never committed**: the
  fix agent's capabilities are `apply-edits` + `run-tests` with no git step
  (`quality-gate/SKILL.md:75`), those edits run against the working tree, the pre-qg-fix
  **checkpoint snapshots the working directory as rollback** (`:460` — which only makes
  sense because code fixes mutate that tree), and there is no `git commit` anywhere in
  quality-gate's directory. The leg is invoked so its internal
  siege auto-dispatch runs (warden does **not** suppress it) — warden's second siege
  pass, mirroring build (see the reviewer table / I-W4). So — like temper and delve —
  **warden commits the red-team leg's residual working-tree changes itself** after the loop
  terminates, with a **non-`fix:` subject** (`chore(warden): red-team fixes <run-id>` —
  see M-c). As the **terminal** fixer this commit is made at Ordering step 3; its range
  `SHA_pre_redteam..HEAD` is what the terminating freeze-guard re-checks (Ordering step
  3→4). HEAD advances so downstream `finish` / PR-creation see the red-team fixes
  **already committed**.
- **siege** — loops+fixes to 0 Critical/High (its own loop); **self-commits**, so it
  leaves no residual (the universal commit is a no-op for it).
- **inquisitor** — writes+runs tests and manages its own fix cycle; **self-commits**
  (`inquisitor/SKILL.md:163`), so it leaves no residual.
- **delve** — **report-only, no fix loop** (`delve/SKILL.md:25,125`; runs the
  engine once and reports). warden owns delve's convergence with a **bounded**
  path. On a delve native-gate trip (`{CONFIRMED,PLAUSIBLE} × {Critical,Important}`),
  warden runs `delve --fix`, which applies the unambiguous repairs and **surfaces
  rather than applies** the findings whose repair is ambiguous (`delve/SKILL.md:133`
  — the discriminator is a judgment delve's `--fix` step makes, not a schema field
  on the report). delve `--fix` edits the **working tree only and never commits**
  (`delve/SKILL.md:130`), so **warden commits the applied fixes itself** with a
  **non-`fix:` subject** (`chore(warden): delve fixes <run-id>` — see M-c) before
  re-running plain delve to re-check the
  predicate — this is what gives the delve leg fix commits for the scoped
  re-temper (I-W6) and lands them in the frozen HEAD (S-4). The
  **surfaced-not-applied** findings are the BLOCK set: warden does not auto-fix
  them and **BLOCKs with a named user hand-off**, since the repair is ambiguous
  and there is no safe auto-repair. The re-run loop is **capped at ≤2 re-runs**
  (delve's finder fan-out is non-deterministic, so a one-shot `--fix` need not
  clear a `PLAUSIBLE@Critical`); if the native predicate still trips after the
  cap, warden **BLOCKs with the same named user hand-off** rather than looping
  open-endedly. This gives delve a defined, bounded convergence path instead of a
  leg that can block forever.

**M-c note (`fix:` subject vs reconcile's candidate walk — resolved).**
calibration-reconcile walks merged `fix`/`hotfix` commits as falsification
candidates, so a `fix:`-prefixed intra-gate commit that reached a **merged branch
un-squashed** could be picked up as a candidate falsifying a *prior* verdict over
the same files. To make correctness independent of the downstream repo's merge
strategy, **every warden-owned per-leg residual commit — temper, delve, the red-team
leg, and any other leg whose residual warden commits — must use a non-`fix:` subject**
(`chore(warden): temper fixes <run-id>`, `chore(warden): delve fixes <run-id>`,
`chore(warden): red-team fixes <run-id>`) — **mandated, not optional**. Each is a
warden-authored commit of a leg's working-tree changes, and any could otherwise hit the
identical `fix`/`hotfix` candidate-walk collision. A non-`fix:` subject is never a
candidate in reconcile's `fix`/`hotfix` walk regardless of whether the branch is
squashed, so the subject-prefix collision cannot arise for any warden-owned commit even
in a rebase/merge-commit repo.

**M-2 caveat (`chore()` also suppresses *legitimate* prior-gate falsifications).** The
non-`fix:` subject is blanket: because `delve --fix` may repair pre-existing
out-of-scope files (M-d), a `chore(warden):` commit that genuinely fixes a bug a
**prior merged gate** missed never enters reconcile's `fix`/`hotfix` candidate walk
(`reconcile_ledger.py:910,914`), so that prior verdict keeps an undeserved Brier point.
This is a small calibration-precision loss, disclosed here; the reconcile tier-filter
fix that would recover it stays out of scope.

**M-d note (delve `--fix` may touch out-of-scope files).** `delve --fix` may edit
**any file a kept finding names**, including files outside the original push scope
(delve's cross-file angle, `delve/SKILL.md:137`). warden commits those **by
construction** — the unscoped per-leg residual commit (above) captures every
uncommitted tracked change, so delve's out-of-scope edits are committed like any other,
not as a special case. The scoped re-temper (Ordering step 2) covers them on temper's
axis, and — because delve is pinned **before** the red-team leg (Ordering step 1) —
the **second siege** (the QG leg's internal auto-dispatch at `SHA_pre_redteam`) re-sieges
over those edits on the security axis. So only **inquisitor does not re-run** on
newly-touched out-of-scope files (it binds its step-1 HEAD, per S-D / S-E). This is a
small accepted coverage asymmetry: temper/delve/siege cover the widened scope; only the
inquisitor leg does not. **M-4 (pushed-footprint expansion):** beyond the *review*
asymmetry, warden **commits and pushes** these out-of-scope `delve --fix` edits — a
scope-expansion of what *ships*, not just of what is reviewed (a user gating a 1-file
change may push edits to unrelated files delve's cross-file angle touched). Disclosed and
accepted.

warden blocks **only if a native gate still trips after that leg's fix path (its
own loop, or warden-owned delve/red-team fixes) terminates**. warden adds no new
fix mechanism beyond running `delve --fix` and committing **each leg's residual
working-tree changes** (temper, delve, and the red-team leg — inquisitor/siege
self-commit and leave no residual), as described above.

<!-- SCAFFOLD: later #464 Phase-A tasks author the remaining sections
(ordering, gate/enforcement, double-run avoidance, integration, invariants). -->
