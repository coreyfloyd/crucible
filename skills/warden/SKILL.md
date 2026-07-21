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

<!-- SCAFFOLD: later #464 Phase-A tasks author the full sections
(dispatch/return wiring, fix behavior, double-run avoidance, integration). -->
