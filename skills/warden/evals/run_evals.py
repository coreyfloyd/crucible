#!/usr/bin/env python3
"""Warden behavior-eval harness — `stage` + `score` (#464).

Mirrors the delve/siege eval-harness shape (package-relative helper imports,
`if __name__ == "__main__": sys.exit(main())`). Invoked as a module from repo root
(relative imports require `-m`):

    python3 -m skills.warden.evals.run_evals stage <run-id> [--fixture ID]
    python3 -m skills.warden.evals.run_evals score <run-id> [--allow-incomplete]

THE SHAPE (why this is a scorer over a RECORDED run, not a gate engine). warden has
**no runtime** — its disjunction / reviewer-set / marker / ordering rules live ONLY in
`skills/warden/SKILL.md`, interpreted by the *live* `/warden` run. There is deliberately
NO Python re-encoding of those rules (no `gate_logic.py`): re-encoding them and testing
the Python against itself would prove only self-consistency and duplicate the prose spec
(a "link, never copy" violation). Instead:

- `stage <run-id>` reads each fixture's `descriptor.json` (a diff-shape descriptor + the
  synthetic per-leg-verdict vector the operator feeds the live run) and writes a
  `stage-manifest.json` + a per-fixture operator dispatch note.
- The operator runs `/warden` **live (manual)** with that diff shape / leg vector and
  records warden's PRODUCED reviewer-set + disjunction verdict + marker fields + per-leg
  commit subjects to the cell's result file (with a `DISPATCH_STATUS: OK|ERROR`
  sentinel, mirroring delve).
- `score <run-id>` runs the deterministic COMPARATOR (`_scorer.py`) comparing that
  recorded outcome (the thing UNDER TEST) against each fixture's `ground-truth.json`
  (the expected outcome, authored BY HAND from the SKILL.md rule — NOT copied from the
  live run). It writes `last_run.json` + `results.md`.

**Anti-tautology separation (structural, load-bearing):** `score` reads ONLY
`ground-truth.json` + the recorded result file. It NEVER opens `descriptor.json` — the
per-leg vector is `stage`-only input. So neither `score` nor `_scorer.py` can derive the
verdict/reviewer-set from the leg vector; they can only compare the hand-authored
expected outcome to the recorded one.
"""
from __future__ import annotations
import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from ._dispatch_paths import resolve_dispatch_dir
from ._runid import validate_run_id
from ._scorer import score_outcome

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVALS_DIR = Path(__file__).resolve().parent
_FIXTURES_DIR = _EVALS_DIR / "fixtures"

# The dispatch-health sentinel the operator prepends to each recorded result file
# (mirrors delve). An `OK` sentinel is consumed; an `ERROR` (or malformed/missing)
# sentinel marks the cell dispatch_failed — an unrecorded leg is not a pass.
_STATUS_PREFIX = "DISPATCH_STATUS:"


def _fixture_dirs() -> list:
    """Every fixture dir under fixtures/ that carries a ground-truth.json (the expected
    outcome). A fixture's per-leg vector lives in descriptor.json, read only by stage."""
    if not _FIXTURES_DIR.exists():
        return []
    return sorted(d for d in _FIXTURES_DIR.iterdir()
                  if d.is_dir() and (d / "ground-truth.json").exists())


def _dispatch_note(fixture_id: str, scope: str, reviewer_set_mode: str,
                   result_file: str, descriptor: dict) -> str:
    """The human-operator instruction rendered into the manifest for one cell. It
    describes the diff shape + per-leg vector to feed the LIVE `/warden` run and the
    outcome fields to record — it is the ONLY place the per-leg vector is surfaced."""
    vector = json.dumps(descriptor.get("per_leg_verdict_vector", {}), indent=2)
    diff_shape = descriptor.get("diff_shape", "(see descriptor.json)")
    return (
        f"# Warden behavior-eval — collect step for fixture {fixture_id!r}\n\n"
        f"1. Run `/warden {scope}` in the `{reviewer_set_mode}` reviewer-set with the "
        f"diff shape: {diff_shape}.\n"
        f"2. Feed each leg the synthetic native verdict from this fixture's per-leg "
        f"vector:\n{vector}\n"
        f"3. Record warden's PRODUCED outcome — the reviewer-set that actually ran, the "
        f"aggregate PASS/BLOCKED verdict, the marker shape (aggregate build-tagged? "
        f"red-team leg marker build-tagged?), and each warden-owned per-leg residual "
        f"commit subject (elide the actual run-id to the literal token `<run-id>`) — as "
        f"a JSON object to `{result_file}` in this dispatch dir.\n"
        f"4. Prepend the line `{_STATUS_PREFIX} OK` then a blank line before the JSON "
        f"(use `{_STATUS_PREFIX} ERROR` if the dispatch failed — that cell is marked "
        f"dispatch_failed).\n"
        f"5. When every cell is recorded, write an empty `.collect-status` file in this "
        f"dispatch dir.\n\n"
        f"NB: the expected outcome in ground-truth.json was authored BY HAND from "
        f"skills/warden/SKILL.md — do NOT copy this recording into it.\n"
    )


def stage(run_id: str, *, fixture: str | None = None, force: bool = False) -> Path:
    """Render a stage-manifest.json enumerating one cell per fixture + the operator
    dispatch note. Returns the dispatch dir path."""
    validate_run_id(run_id)
    fixtures = _fixture_dirs()
    if fixture is not None:
        fixtures = [d for d in fixtures if d.name == fixture]
        if not fixtures:
            raise ValueError(f"--fixture {fixture!r} not found under {_FIXTURES_DIR}")
    if not fixtures:
        raise ValueError(f"no fixtures with ground-truth.json under {_FIXTURES_DIR}")

    dispatch_dir = resolve_dispatch_dir(run_id)
    if dispatch_dir.exists():
        if not force:
            raise FileExistsError(
                f"dispatch dir {dispatch_dir} already exists; pass force=True")
        import shutil
        shutil.rmtree(dispatch_dir)
    dispatch_dir.mkdir(parents=True)

    ts = _dt.datetime.now(_dt.timezone.utc).isoformat()
    cells = []
    for d in fixtures:
        descriptor = json.loads((d / "descriptor.json").read_text(encoding="utf-8"))
        scope = descriptor.get("scope", str(d.relative_to(_REPO_ROOT)))
        mode = descriptor.get("reviewer_set_mode", "full")
        result_file = f"{d.name}-outcome.json"
        cells.append({
            "fixture_id": d.name,
            "scope": scope,
            "reviewer_set_mode": mode,
            "result_file": result_file,
            "dispatch_note": _dispatch_note(d.name, scope, mode, result_file,
                                            descriptor),
        })

    out = {
        "run_id": run_id,
        "stage_timestamp": ts,
        "engine": "warden",
        "fixtures": len(fixtures),
        "cells": cells,
    }
    (dispatch_dir / "stage-manifest.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    return dispatch_dir


def _parse_recorded(path: Path) -> tuple:
    """Parse a recorded outcome file → (outcome_dict, dispatch_failed).

    Strips an optional leading `DISPATCH_STATUS:` sentinel: an `OK` sentinel is consumed
    and the rest parses as a JSON object; an `ERROR` (or non-OK/malformed) sentinel →
    ({}, True). A file with no sentinel parses as a bare JSON object. A missing/empty
    file → ({}, True)."""
    if not path.exists():
        return {}, True
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith(_STATUS_PREFIX):
        first, _, rest = stripped.partition("\n")
        sentinel = first.strip()
        if sentinel.startswith(f"{_STATUS_PREFIX} ERROR"):
            return {}, True
        if not sentinel.startswith(f"{_STATUS_PREFIX} OK"):
            return {}, True  # malformed sentinel → dispatch failure
        text = rest
    text = text.strip()
    if not text:
        return {}, True
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"recorded outcome in {path} is not a JSON object")
    return data, False


def score(run_id: str, *, allow_incomplete: bool = False) -> int:
    """Read stage-manifest.json + each cell's recorded outcome; compare against each
    fixture's ground-truth.json via the deterministic comparator; write last_run.json +
    results.md. Returns an exit code (1 for a missing manifest / missing .collect-status;
    0 once scoring runs — a per-fixture/aggregate all_pass:false is a recorded eval
    result, not a harness error)."""
    validate_run_id(run_id)
    dispatch_dir = resolve_dispatch_dir(run_id)
    manifest_path = dispatch_dir / "stage-manifest.json"
    if not manifest_path.exists():
        print(f"[fatal] no stage-manifest.json at {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not (dispatch_dir / ".collect-status").exists() and not allow_incomplete:
        print(f"[fatal] no .collect-status in {dispatch_dir}; collect is incomplete "
              f"(pass --allow-incomplete for a smoke/debug score)", file=sys.stderr)
        return 1
    complete = not allow_incomplete

    per_fixture = []
    total_fields = 0
    total_pass = 0
    passed_fixtures = 0
    for cell in manifest["cells"]:
        fixture_dir = _FIXTURES_DIR / cell["fixture_id"]
        # score reads ONLY ground-truth.json (the expected outcome) — never
        # descriptor.json (the per-leg vector), keeping the comparator non-derivational.
        gt = json.loads(
            (fixture_dir / "ground-truth.json").read_text(encoding="utf-8"))
        expected = gt["expected"]
        recorded, dispatch_failed = _parse_recorded(
            dispatch_dir / cell["result_file"])

        if dispatch_failed:
            fields, n_fields, n_pass, all_pass = [], 0, 0, False
        else:
            result = score_outcome(expected, recorded)
            fields = result["fields"]
            n_fields = result["n_fields"]
            n_pass = result["n_pass"]
            all_pass = result["all_pass"]

        total_fields += n_fields
        total_pass += n_pass
        if all_pass:
            passed_fixtures += 1

        per_fixture.append({
            "fixture_id": cell["fixture_id"],
            "reviewer_set_mode": cell.get("reviewer_set_mode"),
            "n_fields": n_fields,
            "n_pass": n_pass,
            "all_pass": all_pass,
            "dispatch_failed": dispatch_failed,
            "fields": fields,
        })

    last_run = {
        "run_id": run_id,
        "engine": "warden",
        "complete": complete,
        "fixtures": len(manifest["cells"]),
        "aggregate": {
            "fields": total_fields,
            "pass": total_pass,
            "passed_fixtures": passed_fixtures,
            "all_pass": passed_fixtures == len(manifest["cells"]),
        },
        "per_fixture": per_fixture,
    }

    (_EVALS_DIR / "last_run.json").write_text(
        json.dumps(last_run, indent=2), encoding="utf-8")
    (_EVALS_DIR / "results.md").write_text(
        _render_results(last_run), encoding="utf-8")
    return 0


def _render_results(lr: dict) -> str:
    agg = lr["aggregate"]
    lines = [
        f"# Warden behavior-eval — run {lr['run_id']}",
        "",
        f"- engine: {lr['engine']} · fixtures: {lr['fixtures']} · "
        f"complete: {lr['complete']}",
        "",
        "## Aggregate",
        f"- fixtures passing: {agg['passed_fixtures']}/{lr['fixtures']}",
        f"- fields agreeing: {agg['pass']}/{agg['fields']}",
        f"- all pass: {agg['all_pass']}",
        "",
        "## Per fixture",
    ]
    for pf in lr["per_fixture"]:
        status = "PASS" if pf["all_pass"] else "FAIL"
        if pf["dispatch_failed"]:
            status = "DISPATCH FAILED"
        lines.append(
            f"- {pf['fixture_id']} [{pf['reviewer_set_mode']}]: {status} "
            f"({pf['n_pass']}/{pf['n_fields']} fields)")
        for f in pf["fields"]:
            if not f["pass"]:
                lines.append(
                    f"    - MISMATCH `{f['field']}`: expected {f['expected']!r} "
                    f"got {f['recorded']!r}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="run_evals",
                                description="Warden behavior-eval harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("stage", help="render the dispatch manifest")
    ps.add_argument("run_id")
    ps.add_argument("--fixture", default=None, help="stage only this fixture dir name")
    ps.add_argument("--force", action="store_true",
                    help="overwrite an existing dispatch dir")

    pc = sub.add_parser("score", help="score recorded outcomes against ground truth")
    pc.add_argument("run_id")
    pc.add_argument("--allow-incomplete", action="store_true",
                    help="score without .collect-status (stamps complete:false)")

    args = p.parse_args(argv)
    if args.cmd == "stage":
        dispatch_dir = stage(args.run_id, fixture=args.fixture, force=args.force)
        print(dispatch_dir)
        return 0
    if args.cmd == "score":
        return score(args.run_id, allow_incomplete=args.allow_incomplete)
    return 2  # pragma: no cover (argparse requires a subcommand)


if __name__ == "__main__":
    sys.exit(main())
