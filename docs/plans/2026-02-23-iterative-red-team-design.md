# Iterative Red-Team and Innovation Pipeline Design

> **For Claude:** REQUIRED SUB-SKILL: Use crucible:executing-plans to implement this plan task-by-task.

**Goal:** Add iterative adversarial review loops, a standalone red-team skill, a standalone innovate skill, and port executing-plans — making every quality gate in crucible iterate until clean.

**Architecture:** Two new standalone skills (`red-team`, `innovate`) plus iterative loops added to all existing review touchpoints. The `red-team` skill owns adversarial attack logic; `requesting-code-review` owns code quality review logic. Both use the same loop pattern independently. The `innovate` skill provides a one-shot divergent creativity injection before red-teaming.

**Repo:** raddue/crucible

---

## Design Decisions

### Iterative Loop Pattern (uniform everywhere)

Every review touchpoint uses this loop:

```
Orchestrator dispatches FRESH reviewer subagent (no prior context)
  -> Reviewer returns findings with issue count
  -> No issues? Clean -- proceed.
  -> Issues found?
    -> Dispatch fix subagent (or Plan Writer for plan/design reviews)
    -> Dispatch NEW fresh reviewer (different subagent, no anchoring)
    -> Compare issue count to prior round
      -> Strictly fewer issues? Progress -- loop again
      -> Same or more issues? Stagnation -- escalate to user
  -> Architectural concerns? Immediate escalation (unchanged)
```

**Key rules:**
1. **Fresh reviewer every round** -- never pass prior findings to the next reviewer. No anchoring, no confirmation bias. Each reviewer sees the artifact cold.
2. **Stagnation = escalation** -- if Round N+1 finds >= the number of issues as Round N, stop and escalate to user with full findings.
3. **Architectural concerns bypass the loop** -- immediate escalation regardless of round.
4. **No round cap** -- the loop runs as long as each round makes progress. Most things clean up in 2-3 rounds in practice.
5. **Issue count is the metric** -- simple, clear, hard to game. Count of Fatal+Significant (for red-team) or Critical+Important (for code review). Minor issues are logged but don't count toward stagnation.

### Innovation Step

A divergent creativity injection that fires after an artifact is finalized but before red-teaming:

- **One shot, one proposal** -- proposes the single most impactful addition
- **No user approval gate** -- the red team that follows is the gate. If the addition is YAGNI, the red team kills it
- **Not iterative** -- runs once per artifact
- **Output format:** The single best addition, rationale, why this over alternatives, impact, cost

### Separate Skills for Different Review Types

- **`crucible:red-team`** -- adversarial attack ("how could this fail?")
- **`crucible:requesting-code-review`** -- quality check ("is this well-built?")

Both have the same iterative loop pattern but are separate skills because:
- Different mental models (adversarial vs quality)
- Different reviewer prompts
- Different output formats (challenges vs issues)
- The loop logic is ~5 bullet points -- duplication cost is negligible
- Standalone invocation semantics are clearer

---

## Pipeline Flow (Updated `build` Skill)

```
Phase 1: Brainstorm (interactive)
  -> User approves design doc
  -> crucible:innovate on design doc (one shot)
  -> Plan Writer incorporates innovation
  -> crucible:red-team on design doc (iterative until clean)
  -> Design doc finalized

Phase 2: Plan (autonomous)
  -> Plan Writer creates implementation plan
  -> Plan Reviewer checks plan (iterative until clean)
  -> crucible:innovate on plan (one shot)
  -> Plan Writer incorporates innovation
  -> crucible:red-team on plan (iterative until clean)
  -> Plan approved

Phase 3: Execute (autonomous, team-based)
  -> Per-task: Implementer builds + tests
  -> Per-task: crucible:requesting-code-review (iterative until clean)
  -> Verification gates between waves (unchanged)
  -> Architectural checkpoint at ~50% (unchanged)

Phase 4: Completion
  -> Full test suite
  -> crucible:requesting-code-review on full implementation (iterative until clean)
  -> crucible:red-team on full implementation (iterative until clean)
  -> Present merge/PR options
```

---

## New Skills

### `crucible:red-team`

**Standalone invokable skill for adversarial review of any artifact.**

- Dispatches a Devil's Advocate subagent (Opus) to attack the artifact
- Handles the iterative loop: fresh reviewer each round, stagnation detection, escalation
- Caller provides: artifact content, context, fix mechanism (who fixes issues)
- Prompt template: `red-team/red-team-prompt.md` (moved from build/)
- Can be invoked standalone on any artifact (design doc, plan, code, PR, documentation)

### `crucible:innovate`

**Standalone invokable skill for divergent creativity injection.**

- Dispatches an Innovation subagent (Opus) to propose the single most impactful addition
- One shot per artifact, not iterative
- Output: single best addition, rationale, alternatives considered, impact, cost
- Caller incorporates the proposal, then red-team validates it
- Can be invoked standalone on any artifact
- Prompt template: `innovate/innovate-prompt.md`

### `crucible:executing-plans` (ported from superpowers)

**Standalone plan executor with iterative review loops.**

- Ported from superpowers:executing-plans
- All review loops updated to iterative pattern:
  - Spec compliance review (high-risk tasks): iterative until clean
  - Code quality review (medium+ risk tasks): iterative until clean
  - Fix protocol: iterative with stagnation detection
- References updated from `superpowers:` to `crucible:`
- Prompt templates ported: implementer-prompt.md, spec-reviewer-prompt.md, architecture-reviewer-prompt.md

---

## Modified Skills

### `crucible:build`

- **Phase 1:** Add innovate + red-team steps after design doc approval (before Phase 2)
- **Phase 2, Step 2 (Plan Review):** Remove 2-round hard cap, add iterative loop with stagnation detection
- **Phase 2, Step 3 (Red Team):** Replace inline red-team logic with `crucible:red-team` call. Add innovate step before red-team.
- **Phase 3 (Code Review):** Remove 2-round revision cap, add iterative loop with stagnation detection
- **Phase 4:** Add `crucible:red-team` on full implementation after code review
- **Escalation Triggers:** Update to reference stagnation instead of round caps
- **Prompt Templates:** Remove `red-team-prompt.md` (moved to red-team skill), keep all others
- **Context Management:** Unchanged

### `crucible:requesting-code-review`

- Add iterative loop: after fixes, dispatch fresh code review subagent
- Track issue count (Critical + Important) between rounds
- Escalate on stagnation (same or more issues)
- Fresh reviewer each round (no anchoring)
- Code-reviewer.md prompt template: unchanged (reviewers don't know about the loop)

### `crucible:finishing-a-development-branch`

- Step 2 (Code Review): Inherits iterative loop from updated `requesting-code-review`
- New Step 2.5: Red-team the full implementation via `crucible:red-team` after code review passes
- Present merge options only after both code review AND red-team pass

### `README.md`

- Add `red-team`, `innovate`, and `executing-plans` to skill inventory
- Update pipeline description to include innovation and iterative red-team steps

---

## Unchanged Skills

- `brainstorming` -- build handles post-brainstorm innovate + red-team, not brainstorming itself
- `writing-plans` -- produces plans, build reviews them
- `test-driven-development`
- `systematic-debugging`
- `verification-before-completion`
- `receiving-code-review`
- `using-git-worktrees`
- `dispatching-parallel-agents`
- `writing-skills`
- `using-crucible`

---

## File Changes

### New files:
- `skills/red-team/SKILL.md` -- standalone red-team skill with iterative loop
- `skills/red-team/red-team-prompt.md` -- devil's advocate prompt (moved from build/)
- `skills/innovate/SKILL.md` -- standalone innovation skill
- `skills/innovate/innovate-prompt.md` -- innovation subagent prompt
- `skills/executing-plans/SKILL.md` -- ported from superpowers, with iterative loops
- `skills/executing-plans/implementer-prompt.md` -- ported from superpowers
- `skills/executing-plans/spec-reviewer-prompt.md` -- ported from superpowers
- `skills/executing-plans/architecture-reviewer-prompt.md` -- ported from superpowers
- `docs/plans/2026-02-23-iterative-red-team-design.md` -- this document

### Modified files:
- `skills/build/SKILL.md` -- add innovate + red-team gates, iterative loops, remove caps
- `skills/build/plan-reviewer-prompt.md` -- unchanged (reviewer doesn't know about loop)
- `skills/build/build-reviewer-prompt.md` -- unchanged
- `skills/build/build-implementer-prompt.md` -- unchanged
- `skills/build/plan-writer-prompt.md` -- unchanged
- `skills/requesting-code-review/SKILL.md` -- add iterative loop
- `skills/requesting-code-review/code-reviewer.md` -- unchanged
- `skills/finishing-a-development-branch/SKILL.md` -- add red-team step
- `README.md` -- add new skills to inventory

### Removed files:
- `skills/build/red-team-prompt.md` -- moved to `skills/red-team/red-team-prompt.md`
