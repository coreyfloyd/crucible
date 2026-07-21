# Ground-truth provenance — `tw1-single-gate-trip` (T-W1)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` = all five.** temper/delve/red-team always run; siege runs
  (security-surface diff); inquisitor runs (unconditional in `full`) — §Reviewer set.

- **`verdict` = BLOCKED.** §Gate + enforcement: warden's verdict is BLOCKED "if any run
  reviewer's native gate trips after its fix path terminates … else PASS." Exactly one
  leg trips (red-team, `quality-gate verdict != PASS` per the §Reviewer set predicate),
  and the **disjunction of native gates** is the boolean OR of the legs — so one trip is
  sufficient to BLOCK regardless of the four clean legs.

- **`block_reason`** names the tripping leg + its native predicate. It is scored as an
  **opaque string** (the comparator does no severity normalization and does not
  recompute the block from the vector — it only compares the recorded string to this
  authored one).
