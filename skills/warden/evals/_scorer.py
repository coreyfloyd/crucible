"""The deterministic COMPARATOR for the warden behavior-eval harness (#464).

LLM-free, pure, stdlib-only — this is the CI-gated half of the harness, so its
comparison is pinned by test_run_evals_score.py.

WHY A COMPARATOR, NOT A GATE ENGINE (the crux — do not "fix" this into a producer).
warden has **no runtime**: its disjunction / reviewer-set / ordering / marker rules
live ONLY in `skills/warden/SKILL.md`, and the *live* `/warden` run interprets them.
So this harness never re-encodes those rules in Python (there is deliberately NO
`gate_logic.py`). Instead it RECORDS a live warden run's produced outcome and scores it
against a per-fixture ground truth that a human authored BY HAND from the SKILL.md rule
(see each fixture's `ground-truth.json` + `provenance.md`). This module is that scorer:
it takes an `expected` outcome (the hand-authored ground truth) and a `recorded`
outcome (the live run under test) and reports, PER FIELD, whether they agree.

**Anti-tautology guarantee (structural):** this module — and `run_evals.score` — read
ONLY `ground-truth.json` (the expected outcome) and the recorded result file. Neither
reads a fixture's per-leg-verdict vector (`descriptor.json`, consumed only by `stage`
to render the operator note). So the scorer CANNOT derive the verdict/reviewer-set from
the leg vector; it can only compare two authored/recorded values. If `expected` were
ever copied from the run being scored, `score` would degrade to a tautology — which is
exactly what the independent hand-authoring + the `test_score_mismatch_fails` proof
guard against.

**I-W1 (no cross-scale severity normalization):** the comparison is a pure field
match. It NEVER maps one reviewer's severity scale onto another's; any per-leg severity
that appears in an outcome is an opaque string compared only against the same field.
There is no `severity` helper here by design.
"""
from __future__ import annotations

# Fields whose value is a SET of members (order-insensitive) rather than an ordered
# list or scalar. `reviewer_set` = which reviewers ran; recording them in run order vs
# GT order must still match. Everything else is compared by exact equality (leg commit
# subjects are an ordered list; marker is a dict; verdict/block_reason are scalars).
_SET_FIELDS = frozenset({"reviewer_set"})

_MISSING = object()


def _as_sorted(value):
    """Canonicalize a set-valued field for order-insensitive comparison. Non-list
    values pass through unchanged (so a malformed recording fails the `==` honestly)."""
    if isinstance(value, list):
        return sorted(value, key=repr)
    return value


def _fields_equal(field: str, expected, recorded) -> bool:
    """Pure value comparison for one field. `reviewer_set` is order-insensitive; every
    other field is exact equality. This is the ONLY comparison logic — no derivation of
    a verdict/reviewer-set from any per-leg vector, and no cross-scale normalization."""
    if field in _SET_FIELDS:
        return _as_sorted(expected) == _as_sorted(recorded)
    return expected == recorded


def score_outcome(expected: dict, recorded: dict) -> dict:
    """Compare a recorded warden outcome against the hand-authored expected outcome,
    field by field.

    Scores ONLY the fields present in `expected` (a fixture asserts the subset of the
    outcome schema it is about — reviewer_set, verdict, marker, leg_commit_subjects,
    block_reason). A field expected but absent from the recording is a FAIL (an unrun /
    unrecorded assertion is not a pass). Returns:

        {
          "fields": [{"field", "expected", "recorded", "recorded_present", "pass"}...],
          "n_fields": int, "n_pass": int, "all_pass": bool,
        }
    """
    field_results = []
    for field in sorted(expected):
        exp = expected[field]
        rec = recorded.get(field, _MISSING)
        present = rec is not _MISSING
        passed = _fields_equal(field, exp, rec) if present else False
        field_results.append({
            "field": field,
            "expected": exp,
            "recorded": (rec if present else None),
            "recorded_present": present,
            "pass": passed,
        })
    n_pass = sum(1 for f in field_results if f["pass"])
    return {
        "fields": field_results,
        "n_fields": len(field_results),
        "n_pass": n_pass,
        "all_pass": all(f["pass"] for f in field_results),
    }
