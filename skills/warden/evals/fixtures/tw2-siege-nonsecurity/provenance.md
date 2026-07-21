# Ground-truth provenance — `tw2-siege-nonsecurity` (T-W2)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` = temper, delve, red-team, inquisitor — siege ABSENT.** §Reviewer
  set: siege is "conditional — security-surface diff (reuse build's existing Step 5.5
  trigger)". This diff is a non-security refactor, so the trigger does not fire and siege
  does not run. inquisitor is present (unconditional in `full`). A **condition-skipped**
  siege is a **normal PASS input, not a dead leg** (§Gate + enforcement, M5) — so it is
  simply absent from the set, not a fail-closed BLOCK.

- **`verdict` = PASS.** Every leg that ran is clean, and the skipped siege is not a
  trip; the disjunction is all-false → PASS (§Gate).

The contrasting security-diff branch (siege PRESENT) is `tw6-clean-pass`.
