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

## Ordering (F1 — the gate binds a single frozen final artifact)

A gate's verdict is only fully sound if it is evaluated against the **final code
state**. warden enforces this for the legs it re-evaluates on the frozen HEAD —
**temper, delve, and the red-team leg** — by ordering the code-mutating legs and
re-checking after later fixers (below). siege runs **twice** (neither pass at the
frozen HEAD) and inquisitor runs **once** at its step-1 HEAD — accepted cost tradeoffs:

- **siege** runs **twice**, **coverage-equal to build's two sieges (position
  redistributed across the two passes)** — warden's siege#1 runs at step-1 (before the
  step-2 re-temper), whereas build's Step-5.5 siege runs after Step-5's re-temper; the
  step-2 re-temper is covered by siege#2, so this is a position redistribution, not a
  coverage gap: (a) warden's **own siege leg** at the **step-1 HEAD** (≈ build Step 5.5),
  and (b) the **quality-gate red-team leg's internal siege auto-dispatch** at the
  red-team HEAD (`SHA_pre_redteam`, parallel with red-team round 1 — ≈ build Step 6). The
  second siege covers the **step-2 scoped re-temper commits** and delve's `--fix` edits,
  mirroring build's Step-6 siege over its Step-5.5.e re-temper. Re-running the 6-agent
  Opus siege on *every* fix commit would be prohibitively expensive, so neither pass
  binds the **frozen** HEAD: the only window either misses is the **red-team leg's own
  fix rounds** — and build's Step-6 siege runs parallel with red-team round 1, so build
  misses that window too. warden's siege coverage is therefore **coverage-equal to build's
  two sieges (position redistributed across the two passes)** — no coverage reduction
  relative to build.
- **inquisitor** binds its step-1 HEAD (it is excluded from the terminating
  read-only leg per S-D, since it writes tests). Its coverage is delivered by the
  unconditional step-1 run; a later fixer regressing the cross-component surface is
  out of scope for the cheap terminating pass — an accepted tradeoff. **inquisitor is
  the sole leg that binds step-1-only** — siege now runs a second pass at
  `SHA_pre_redteam`.

Because the code-mutating legs edit the shared artifact the other legs already
judged, warden runs them in a **deliberate order** that mirrors build Phase 4
(temper → inquisitor → siege → quality-gate last, `build/SKILL.md:1212-1263`),
committing **each leg's residual working-tree changes as it completes** so the frozen
HEAD provably contains every leg's fixes (see Fix behavior — Universal per-leg residual
commit):

0. **Working-tree-clean precondition (inductive base — ASSERTED).** warden **asserts** a
   **clean working tree at entry** on **all** paths (`git status --porcelain` **fully
   empty** — no tracked modifications **and no untracked files**) — the base that makes
   each per-leg residual commit capture only that leg's delta. Standalone `/warden` on a
   **dirty-or-untracked** tree **REFUSES** with an actionable
   error (`commit, stash, or clean untracked files, then re-run /warden`), matching
   warden's detached-HEAD handling. Inside **build**, **build guarantees** the tree is
   fully clean at warden entry (see the build-side integration requirement in Integration
   mapping); a dirty **or untracked** tree at build→warden entry is a **surfaced
   build/test defect** — warden errors, it never sweeps it into the first `chore(warden):`
   commit. **Standalone `/warden` and standalone `/finish` both fall to the
   assert-and-REFUSE rule** — only *build* supplies the clean-tree guarantee (finish has
   no clean-tree gate of its own).
1. **Non-terminal fixers first, each residual committed as it terminates.** Run the
   **non-terminal** code-mutating legs — temper, inquisitor, siege, and warden-owned
   delve fixes — to loop-termination first, in the build-mirroring order
   temper → inquisitor → siege, with the **warden-owned `delve --fix` leg pinned among
   these non-terminal fixers, before the red-team leg (step 3)** — so delve's cross-file
   security-relevant edits are already committed when the red-team leg's internal
   **second siege** runs at `SHA_pre_redteam`, keeping them inside that siege's coverage.
   temper (uncommitted mode, `temper/SKILL.md:198`) and delve `--fix` are
   working-tree-only and never commit, so after **each** such leg terminates — and
   **before the next fixer leg runs** — warden **commits that leg's full residual
   working-tree changes, if any** (`git add -A && git commit -m '<subject>'` — stages
   new/untracked files too; no path-scoping), with a leg-labeled
   non-`fix:` subject (`chore(warden): temper fixes <run-id>`, `chore(warden): delve fixes
   <run-id>`, per M-c). Under the fully-empty clean-tree precondition (step 0) that
   residual is exactly the current leg's delta (a new file the leg created is staged and
   committed, and no pre-existing untracked file exists to misattribute). Committing between legs (not batched at the end) keeps
   each residual attributable to the leg that produced it — so every non-terminal leg's
   repairs enter HEAD with correct provenance (S-4; see Fix behavior). inquisitor
   (`inquisitor/SKILL.md:163`) and siege **self-commit**, so their residual is empty and
   the commit is a no-op for them. (The red-team leg is **also** a warden-committed fixer,
   but as the **terminal** fixer its residual is committed at **step 3**, not here.)
2. **Re-temper after later fixers (S1).** After inquisitor's, siege's, or delve's
   fix path terminates, warden re-runs temper **scoped to that leg's fix
   commits** before the red-team leg — mirroring build Step 5 (re-temper on
   inquisitor commits) and Step 5.5.e (re-temper on siege commits). A fix that
   satisfies siege's CVSS gate can still regress temper's maintainability/
   correctness axis; this catches it. The scoped re-temper is itself a temper
   (uncommitted-mode) fixer, so warden **commits its residual too**
   (`chore(warden): temper fixes <run-id>`, per M-c) before proceeding. (This is
   build's existing scoped re-temper, not a new open-ended fixpoint loop.)
3. **Red-team leg (itself a fixer) next.** Once no non-terminal fixer has more
   work, warden captures **`SHA_pre_redteam = HEAD`** and runs the quality-gate
   red-team leg against that HEAD (invoked so its **internal siege auto-dispatch** runs —
   warden does **not** suppress it — warden's **second** siege pass over `SHA_pre_redteam`,
   parallel with red-team round 1, mirroring build's Step-6 siege; see the reviewer table
   / I-W4). This leg **edits the working tree** — it
   loops+fixes its red-team rounds but, like temper and delve, **does not commit** (its
   fix agent has `apply-edits`/`run-tests` and no git step,
   `quality-gate/SKILL.md:75,462`). So **warden commits the red-team leg's residual
   working-tree changes, if any**, here — `chore(warden): red-team fixes <run-id>`,
   non-`fix:` subject per M-c — advancing HEAD **before the terminating leg (step 4)
   and the freeze**. The red-team fix range is then **`SHA_pre_redteam..HEAD`** — a
   distinct, isolable range even though earlier legs also committed. These fixes land
   after the other four gates were evaluated, so they must not ship un-re-reviewed —
   which is exactly what the terminating freeze-guard (step 4) re-checks over **that**
   range.
4. **Read-only instance-bug freeze-guard over the red-team leg's fixes, then
   freeze.** After the red-team leg's fix loop terminates **and warden has committed
   its residual (step 3)**, warden runs **plain delve in its
   native report-only mode** (`delve/SKILL.md:25`, "report only … never gates") over
   **`SHA_pre_redteam..HEAD`** (the red-team leg's fix commits) — a **read-only
   instance-bug freeze-guard**. If the red-team leg made no edits this range is
   **empty**, and the terminating delve reviews an empty range and benignly passes —
   there is no "non-empty range" requirement. warden does **not** pass `--fix` on this
   leg
   (`delve/SKILL.md:25,125`), so it is **provably non-code-mutating** — the
   terminating leg writes **nothing** into the frozen HEAD. This is deliberately
   **NOT** a temper-the-skill re-run: temper-the-skill is a fix loop (its Step 3 is
   "**Fix every member of `T`**", `temper/SKILL.md:188`) and would mutate the frozen
   HEAD. The terminating leg runs **no temper enumeration or adjudication at all** —
   it is plain delve, run once. In particular the freeze-guard **does not pass `--fix`**
   and is **not** a `temper-reviewer` re-run — it is plain report-only delve.

   **Coverage scope (honest, bounded tradeoff).** The terminating leg is a
   **read-only instance-bug freeze-guard** over the red-team leg's fix commits (plain
   delve, report-only, `--fix` not passed → provably non-mutating). temper's broader
   review angles are applied at step 1 and the scoped re-tempers; they are **not**
   re-applied to the red-team fixer's own commits — an accepted, bounded tradeoff of
   the same class build already lives with (e.g. its inquisitor-step-1-only carve-out).
   This closes the coverage question by
   **disclosing the scope**, not by asserting that delve's coverage subsumes
   temper's. **inquisitor is likewise excluded** because it writes tests (S-D):
   including it would land un-re-reviewed test files in the frozen HEAD, breaking the
   very "single, fully-reviewed frozen artifact" guarantee this leg exists to
   provide. inquisitor's coverage is delivered by its **unconditional step-1 run**;
   the accepted tradeoff is that a red-team fix which regresses the cross-component
   surface is **out of scope** for this cheap terminating pass (it would only be
   caught on a subsequent full gate run).

   This pass runs **exactly once** (detect → BLOCK): there is no fix loop, so no
   round cap — warden **BLOCKs** if delve reports any gating finding
   (`{CONFIRMED,PLAUSIBLE}×{Critical,Important}`); it does not re-fix or loop.
   Because this **final leg warden runs is read-only**, the artifact is stable; only
   then is HEAD frozen and the disjunction evaluated on that single frozen final
   artifact, with the verdict bound to the frozen HEAD SHA. Because warden committed
   **every leg's residual as it completed** (temper's and delve's at steps 1–2, the
   red-team leg's in step 3), **the frozen HEAD now contains every leg's fixes** — so
   F1's "single frozen final artifact" guarantee covers temper's uncommitted-mode fixes
   and the red-team leg's own repairs, not only the legs that self-commit. The verdict
   and its marker (and the ledger `gated_files`/SHA) therefore bind a HEAD that
   **contains the fixes that earned the PASS** — closing the broken verdict-to-artifact
   binding F-A raised.

This is codified as invariant **I-W6**.

## Gate + enforcement

warden's verdict is `BLOCKED` if any run reviewer's native gate trips after its
fix path terminates — its own loop, or warden-owned delve/red-team fixes, evaluated
on the frozen final HEAD per the Ordering section (I-W6) — else `PASS`.

**Escalation verdicts are fail-closed (BLOCKED, never PASS).** The native gate
predicates above are stated over *findings*, but a leg can also terminate on an
**escalation** verdict rather than a findings predicate: temper Stagnation /
Architectural / Max-Rounds (`temper/SKILL.md:332`) from the step-1 / scoped
re-temper legs, or the quality-gate red-team leg STAGNATION / ESCALATED. Any such
escalation **propagates as a warden BLOCK (fail-closed) — never a PASS** — the same
handling build Phase 4 already gives a quality-gate escalation today (it does not
swallow it). warden mints no third verdict: an escalation folds into `BLOCKED` and
halts the pipeline like any other block.

**A reviewer sub-dispatch that dies is fail-closed too (an unrun gate is not a
pass).** If a reviewer sub-dispatch **dies** (crashes, times out, or returns no
parseable receipt), warden **surfaces the failed leg and returns `BLOCKED`**
(fail-closed — **an unrun gate is not a pass**), never silently drops it. A
**condition-skipped** leg (siege on a non-security diff, standalone-inquisitor on a
single-file diff) is **not** an "unrun gate" for this rule: only a leg that was
*supposed to run* and died triggers the fail-closed BLOCK; a correctly
condition-skipped leg is a **normal PASS input, not a failure** (M5).

Enforcement teeth:

- **Inside build/finish (real teeth):** a `BLOCKED` warden verdict halts the
  pipeline before the push/PR step, exactly like quality-gate non-PASS halts
  Phase 4 today.
- **Standalone `/warden` (honored, not intercepting):** a slash command cannot
  intercept `git push`; standalone warden emits a `BLOCKED` verdict the user
  honors — same enforcement strength finish's soft gate has today, but now
  named and consistent. No git hook (rejected: per-push Opus fan-out cost +
  install friction; may revisit as an opt-in follow-up).

## Verdict marker ownership (F2 — single build-tagged emitter)

Two facts make a naive delegation fail-open: quality-gate *always* writes its
marker even as a sub-skill (`quality-gate/SKILL.md:1111`) and *never* deletes it
("build orchestrator is responsible for their lifecycle"). If warden invoked the
red-team leg with **build's** PipelineID, both the leg and warden would write a
`gate-verdict-*.md` carrying build's PipelineID with potentially divergent
verdicts, and build's most-recent-by-Timestamp verification
(`skills/build/SKILL.md:231-243`) would resolve the ambiguity only by timing luck.
So:

- warden invokes the quality-gate red-team leg with **warden's own run-id** as the
  PipelineID (and `Phase: code`), **not** build's PipelineID. A PipelineID is
  present, so the leg stays **non-interactive** — quality-gate does not drop into
  standalone between-rounds check-in mode (`quality-gate/SKILL.md:1111`; this
  resolves M3) — while its `gate-verdict-<warden-run-id>.md` marker carries
  warden's run-id and therefore **never matches build's PipelineID filter**.
- warden writes the **one** `gate-verdict-*.md` that carries **build's** PipelineID
  (and `Phase: code`), stamped with warden's **aggregate** verdict.
- build's Verdict Marker Verification **read** logic — glob → PipelineID-filter →
  PASS-check (`skills/build/SKILL.md:231-243`) — is **unchanged** and now resolves
  **deterministically**: its filter surfaces exactly one marker (warden's
  aggregate), because the leg's marker is tagged with a different (warden)
  PipelineID.

What **does** change is deferred to **Phase E**: the two build sites that hard-name
`quality-gate` — the recovery re-invoke on a missing/mismatched marker
(`build/SKILL.md:241`) and the Step-6 gate invocation (`build/SKILL.md:1263`) —
must **repoint to `warden`** (Tasks 12/16). If the recovery re-invoke were left
naming `quality-gate`, a crashed/orphaned warden run would recover as a **bare
red-team-only** gate (no temper/delve/inquisitor/siege) — a coverage fail-open in
the recovery path; repointing both to warden closes it. This is invariant **I-W7**.
(This task authors the marker-ownership prose only; it does **not** edit build —
the repoint lands in Phase E.)

## Calibration-ledger entries — each leg self-emits, warden emits none

warden emits **no** `code` calibration entry to `runs.jsonl` — it writes
no calibration row of its own. Each leg **self-emits its native per-skill calibration
entry**, exactly as it does under build today: temper's Tier-A `code` entry
(`temper/SKILL.md:323`), siege's (`siege/SKILL.md:690`), the quality-gate red-team
leg's terminal `code` entry (`quality-gate/SKILL.md:1066`, unconditional), and
delve's and inquisitor's Tier-B **stub** `code` entries (`delve/SKILL.md:164`,
`inquisitor/SKILL.md:222`; `backfilled:false`, no merge verdict — a stub entry, not
*no* entry). None are suppressed, and **no leg's SKILL.md is edited** (Option C).

warden **mirrors build** — the existing orchestrator that dispatches these very
same calibrated legs and has **zero `runs.jsonl` touchpoints** (build self-emits
nothing; every leg emits its own entry, which is what per-skill Brier is *for*).
warden's verdict is a *determined disjunction* of its legs' native verdicts (the
boolean OR), so it carries no predictive content beyond that OR; any aggregate
`confidence` / `predicted_falsifier` would be **synthesized** from the legs — a
double-count. No independent content → no independent calibration row. Per-skill
Brier stays fed by the leg entries, and per-leg falsification resolution (which leg
missed a bug) is **preserved** — it would be *lost* under a single aggregate entry.

**Inherited attribution imprecision (warden neither introduces nor solves it).**
These co-timed leg `code` entries over overlapping files attribute
**earliest-first** in `reconcile_ledger.py`'s skill-blind walkback
(`reconcile_ledger.py:352-377`, no tier and no confidence filter). warden **adds
delve's Tier-B stub entries** — which build's Phase 4 lacked: warden runs delve
several times per gate, each a distinct `run_id` (UUIDv7, **not** deduped by the
`(run_id, skill)` emit key), so a 2-iteration fix path is initial +
(`--fix` + recheck)×2 + step-4 ≈ **up to ~6** distinct stubs — but **no aggregate
row**. The earliest-first, skill-blind attribution is therefore **unchanged in
kind** from build's inherited imprecision: a delve stub can become the earliest
overlapping `code` entry and absorb a future fix's falsification exactly as build's
own **inquisitor** stub already can. **The change from build is one of
degree, not kind (M-5):** ~6× the stub surface (up to ~6 delve stubs per warden run vs build's
single inquisitor stub), which correspondingly **raises** — while keeping bounded —
the probability a low-value stub absorbs a future falsification. It is an inherited,
bounded tradeoff — out of scope to fix (the fix would need the `reconcile_ledger.py`
tier filter this design explicitly rejects) — stated plainly so it is not mistaken
for something warden solved.

Consistent with the LOCKED double-siege decision, warden does **not** pass
`skip_siege`/`force_siege` to the quality-gate red-team leg (they are real
`quality-gate/SKILL.md:187-188` params); suppressing the QG-internal siege would
silently break warden's second siege pass (I-W4). Per-leg forensics at gate time
also live in (a) the sectioned-per-reviewer report (I-W2) and (b) the per-reviewer
receipts bound into `receipt-ledger.jsonl` (see Dispatch + return conventions).
This is invariant **I-W8**.

## Double-run avoidance

warden writes a coverage marker keyed by the **pre-run base SHA** (the HEAD warden
observed at entry, *before* its own fixer legs mutate HEAD) + reviewer-set. Keying
on the pre-run base — not the post-fix HEAD warden itself moves — means a legitimate
immediate re-run over the same starting state matches the marker and is skipped,
rather than misfiring because warden's own fix commits changed HEAD (M4). build's
finish-skip instruction is the **primary** guard; the marker is the backstop so a
standalone warden immediately after a build doesn't re-run the identical set.

**M-b caveat:** the marker is **near-inert exactly when warden committed fixes** —
once warden's fixer legs move HEAD, an immediate re-run's pre-run base is the *new*
post-fix HEAD, which no longer matches the prior run's recorded base, so the skip
does not fire. The marker therefore only helps after a **clean, no-commit** warden
pass; whenever warden actually did work, build's finish-skip is the only guard that
prevents a re-run. This is acceptable (a double-run is wasteful, not incorrect), but
the marker must not be relied on as the de-dup mechanism after a fixing run.

## Routing boundary (warden vs temper / quality-gate / delve)

warden's hardest routing problem is that it **runs temper as a leg**, so the
user-facing intents overlap ("review before I push" vs "is this ready to ship").
This is resolved here, not deferred to selection-evals alone: temper's **live**
description already claims "before merging" (`temper/SKILL.md:3`) — the exact
push-gate intent warden wants — so the fix also **edits temper's description** to
cede that phrasing (see the temper frontmatter edit in the Integration mapping) as
well as constraining warden's. Selection-evals prove point-in-time routing; the
description edit removes the standing overlap (MEMORY #371/#358: description-phrase
collisions are fixed by editing the descriptions, not by evals alone).

The discriminator is **whole-set gate** (warden) vs **single reviewer**
(temper / quality-gate / delve).

**Phrase-ownership split:**

| Phrase / intent | Owner | Why |
|---|---|---|
| "gate this before I push", "run the full review gate", "run all the reviewers", "warden", "review my changes **before I push**" / "**before pushing**" / "**before merging**" | **warden** | wants the whole reviewer set + one verdict; the "before I push" / "before pushing" / "before merging" push-gate fragment is warden-owned even when attached to "review my changes" (M2 / S-C — "before merging" ceded from temper's live description) |
| "is this ready to ship", "review my changes" (bare), "review this PR", "code review", "check the diff" | **temper** (kept) | single fresh-eyes merge-verdict review; temper's existing description keeps these — but a trailing "before I push" / "before pushing" / "before merging" hands the utterance to warden (M2 / S-C) |
| "red-team this", "quality gate this design/plan", "is this design sound" | **quality-gate** | red-team of a typed artifact, not a code push gate |
| "find bugs in this diff", "scan this for defects", "instance-bug sweep" | **delve** | report-only bug finder, not a gate |

warden deliberately does **not** claim temper's "is this ready to ship" / "review
my changes" phrases (I-W3): a fresh-eyes single-reviewer pass stays with temper,
red-teaming a typed design/plan stays with quality-gate, and a report-only bug-hunt
on a diff stays with delve. warden owns only the *whole-set gate* — the discriminator
is *whole-set gate* (warden) vs *single reviewer* (temper / quality-gate / delve).

The boundary is asserted by selection-eval prompts in `skills/skill-selection-evals/`.

<!-- SCAFFOLD: later #464 Phase-A tasks author the remaining sections
(dispatch + return conventions, integration mapping, invariants). -->
