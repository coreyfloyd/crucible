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

<!-- SCAFFOLD: later #464 Phase-A tasks author the full sections (reviewer set,
dispatch/return wiring, fix behavior, double-run avoidance, integration). -->
