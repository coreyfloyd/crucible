# Ground-truth provenance — `tw11-delve-block` (T-W11)

Hand-derived from `skills/warden/SKILL.md` against `descriptor.json`; not recorded from
a live run.

- **`reviewer_set` = temper, delve, red-team, inquisitor.** inquisitor unconditional in
  `full`; siege absent (non-security).

- **`verdict` = BLOCKED.** §Fix behavior (delve leg): delve is report-only with no fix
  loop, so warden owns a **bounded** convergence path. On a native-gate trip warden runs
  `delve --fix`, which **surfaces rather than applies** the findings whose repair is
  ambiguous. "The **surfaced-not-applied** findings are the BLOCK set: warden does not
  auto-fix them and **BLOCKs with a named user hand-off**." So the delve leg's native
  predicate still trips → the disjunction trips → BLOCKED.

- **`block_reason`** names the delve hand-off. The **same BLOCKED outcome** also covers
  the second T-W11 arm — "if the native predicate still trips after the [≤2-re-run] cap,
  warden BLOCKs with the same named user hand-off." Both arms resolve to `verdict:
  BLOCKED` + a delve hand-off; the reason is scored as an **opaque string** and the
  comparator does **not** re-derive the cap logic (that would be the forbidden
  reimplementation).
