# Warden behavior-eval harness (#464)

A regression harness for `warden` (the consolidated pre-push review gate). It mirrors
the **delve/siege `stage`/`score` shape** — but warden has **no runtime**. warden's
disjunction / reviewer-set / ordering / marker rules live ONLY in
`skills/warden/SKILL.md` and are interpreted by the *live* `/warden` run. So this harness
does **not** re-encode those rules in Python (there is deliberately **no `gate_logic.py`**
and no module that derives a verdict/reviewer-set from a per-leg vector). Instead it
**records a live warden run's produced outcome** and scores it against a per-fixture
**ground truth authored by hand from the SKILL.md rule**. The scorer (`_scorer.py`) is a
deterministic **field comparator**, never a producer of the verdict — so scoring is
LLM-free and CI-gated; the live `/warden` run between `stage` and `score` is manual.

## Invocation (module form)

Run from the repo root (`-m` required — the package uses relative imports):

```
python3 -m skills.warden.evals.run_evals stage <run-id> [--fixture ID] [--force]
python3 -m skills.warden.evals.run_evals score <run-id> [--allow-incomplete]
```

`stage` prints the dispatch dir path.

## The scorer (comparator, not a gate engine)

`score` compares the **recorded** outcome (the live run, UNDER TEST) against each
fixture's **expected** outcome (`ground-truth.json`, the GROUND TRUTH) **field by field**,
scoring only the fields a fixture asserts:

- **`reviewer_set`** — which reviewers actually ran (order-insensitive set comparison).
- **`verdict`** — the aggregate `PASS`/`BLOCKED` disjunction.
- **`marker`** — the marker shape (aggregate build-tagged + count; red-team leg marker
  NOT build-tagged).
- **`leg_commit_subjects`** — each warden-owned per-leg residual commit subject (the
  non-`fix:` `chore(warden): <leg> fixes <run-id>` shape; run-id elided to `<run-id>`).
- **`block_reason`** — an opaque compared string on a BLOCK.

`_scorer.py` does **no** cross-scale severity normalization (I-W1): a per-leg severity is
an opaque string compared only against the same field; one leg's scale is never mapped
onto another's.

### Anti-tautology (the crux)

The expected outcome is authored **independently** — a human applies warden's
SKILL.md rule by hand (per-field derivation recorded in each fixture's `provenance.md`)
— and is **not** copied from the run being scored. Structurally, `score` and `_scorer.py`
read **only** `ground-truth.json` + the recorded result file; they **never** read a
fixture's per-leg-verdict vector (`descriptor.json`, consumed only by `stage`). So the
scorer *cannot* derive the outcome from the vector — it can only compare two
authored/recorded values. `test_run_evals_score.py::test_score_mismatch_fails` proves the
scorer FAILS a recorded outcome that disagrees with the ground truth (a flipped verdict
AND a forbidden `fix:`-prefixed leg subject), so `score` is not a rubber stamp.

## Workflow (stage → manual collect → score)

1. **`stage <run-id>`** reads each fixture's `descriptor.json` (diff shape + per-leg
   vector + reviewer-set mode) and writes `stage-manifest.json` enumerating one cell per
   fixture (`{fixture_id, scope, reviewer_set_mode, result_file, dispatch_note}`).

2. **collect** (manual — no `collect` subcommand). For each cell, follow its
   `dispatch_note`: run `/warden` live with the fixture's diff shape + leg vector, and
   record warden's PRODUCED outcome (reviewer-set, verdict, marker shape, leg commit
   subjects) as a JSON object to the cell's `result_file`, prepending
   `DISPATCH_STATUS: OK` (or `DISPATCH_STATUS: ERROR` on a failed dispatch). Write an
   empty `.collect-status` when every cell is recorded. **Do not** copy the recording
   into `ground-truth.json`.

3. **`score <run-id>`** reads the manifest + recorded outcomes, runs the comparator
   against each `ground-truth.json`, and writes `last_run.json` + `results.md` (both
   git-ignored). It refuses without `.collect-status` unless `--allow-incomplete`.

## Fixtures

`fixtures/<id>/`:
- `descriptor.json` — the **operator input**: diff shape + synthetic per-leg-verdict
  vector + reviewer-set mode. **Read only by `stage`** (never the scorer).
- `ground-truth.json` — the **expected outcome**, authored by hand from the SKILL.md rule.
- `provenance.md` — the per-field hand-derivation, each field citing the governing
  SKILL.md section (warden's checkable analog to delve's blind-token boundary).

Coverage maps to warden's test obligations: `tw1` (T-W1 one-gate-trip → BLOCKED),
`tw6` (T-W6 clean → PASS + T-W2 siege-present + T-W8 inquisitor + T-W5 marker),
`tw2` (T-W2 siege skipped on non-security), `tw3-*` (T-W3 standalone inquisitor
conditional), `tw8` (T-W8 full inquisitor unconditional), `tw5` (T-W5 marker shape),
`tw9` (T-W9 mechanical: non-`fix:` residual subjects + empty terminating range),
`tw11` (T-W11 delve surfaced-not-applied → BLOCK). T-W9's live commit-ordering and T-W14
are inherently live and are routed to Acceptance-Gate-2, **not** scored here.

## Files

- `run_evals.py` — `stage` + `score` (no `collect`).
- `_scorer.py` — the deterministic field comparator (warden-original; no verdict
  derivation, no cross-scale normalization).
- `_dispatch_paths.py`, `_runid.py` — copied from temper. `scripts/check_warden_helper_drift.py`
  is **function-scoped** to the functions warden imports, so the copies may omit temper's
  unused helpers without reddening CI.
- `test_run_evals_stage.py`, `test_run_evals_score.py`, `test_runid.py` — the gating unit
  tests (run by `scripts/run_tests.sh`).
