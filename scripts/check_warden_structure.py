#!/usr/bin/env python3
"""Structural check for the warden skill scaffold (#464).

Invocation (from repo root):
    python3 scripts/check_warden_structure.py            # gate the real file
    python3 scripts/check_warden_structure.py --selftest # in-memory logic test

Asserts `skills/warden/SKILL.md` exists and carries the load-bearing structural
clauses: the `name: warden` frontmatter, a `description:` line, both canonical
link comments (dispatch + return conventions, per CLAUDE.md "link, never copy"),
a citation of the severity-verdict-contract, and — as of Task 2 — the reviewer-set
section's load-bearing clauses (the five-reviewer table, the disjunction-of-native-
gates statement, the sectioned-per-reviewer clause, the `reviewer-set` parameter,
and inquisitor's `unconditional` full-set coverage). Also asserts the ABSENCE of a
cross-scale normalization construct (I-W1). Exits 0 when every clause is present
and no forbidden construct is found, 1 with a per-clause diff summary otherwise.
Stdlib only, no argparse.

Style mirrors `scripts/check_canonical_drift.py`: ROOT-from-`__file__`, error
accumulation, `sys.exit(main())`.

EXTENSION POINT (Phase-A tasks 3-8): add the substring a later task authors into
warden's SKILL.md to `REQUIRED_SUBSTRINGS` (label -> literal substring). The
frontmatter `name:`/`description:` guards live in `check_frontmatter()`; the
I-W1 negative guard lives in `check_forbidden()`. The `--selftest` GOOD/BAD
samples are self-contained and must stay in sync — the per-clause RED cases are
generated automatically from `REQUIRED_SUBSTRINGS`, so a new required substring
gets its own RED case for free; add a dedicated BAD case for any new *negative*.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills/warden/SKILL.md"

# label -> literal substring that MUST appear somewhere in SKILL.md. Later
# Phase-A tasks EXTEND this dict; the selftest generates a RED case per entry.
REQUIRED_SUBSTRINGS: dict[str, str] = {
    "dispatch canonical link": "<!-- CANONICAL: shared/dispatch-convention.md -->",
    "return canonical link": "<!-- CANONICAL: shared/return-convention.md -->",
    "severity-verdict-contract citation": "severity-verdict-contract.md",
    # Task 2 — reviewer set (native scales, no normalization), design L94-123.
    "disjunction-of-native-gates statement": "disjunction of native gates",
    "sectioned-per-reviewer clause (I-W2)": "sectioned per reviewer",
    "reviewer table header": "| Reviewer |",
    "reviewer leg: temper": "temper",
    "reviewer leg: delve": "delve",
    "reviewer leg: red-team": "red-team",
    "reviewer leg: siege": "siege",
    "reviewer leg: inquisitor": "inquisitor",
    "reviewer-set parameter (full | standalone)": "reviewer-set: full | standalone",
    "inquisitor unconditional in full set": "unconditional",
}

# I-W1 negative guard. Matches a real cross-scale normalization construct — a
# prose "convert <X> to <Y> scale" mapping — within a single sentence
# (`[^.\n]*` never crosses a `.` or newline). Deliberately NOT a table-shaped
# arrow-map detector: that would false-positive on warden's own legitimate
# reviewer table (full of `Critical`/`High`/`Important` cells). Negation prose
# ("no cross-scale normalization", "conversion is forbidden", "converted into
# another's") does NOT trip it — `convert\w*` never matches "conversion"
# (7th char is `s`, not `t`) and `\bto\b` never matches inside "into".
_FORBIDDEN_NORMALIZATION = re.compile(
    r"convert\w*\b[^.\n]*\bto\b[^.\n]*\bscale\b", re.IGNORECASE)


def check_frontmatter(text: str) -> list[str]:
    """The `name: warden` scalar and a `description:` line must be present in
    the leading `---`-fenced YAML block."""
    errs: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["missing leading `---` frontmatter fence"]
    fm: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm.append(line)
    else:
        return ["frontmatter block is not closed by a `---` fence"]
    if not any(ln.strip() == "name: warden" for ln in fm):
        errs.append("missing frontmatter `name: warden`")
    if not any(ln.lstrip().startswith("description:") for ln in fm):
        errs.append("missing frontmatter `description:` line")
    return errs


def check_forbidden(text: str) -> list[str]:
    """I-W1: warden must carry NO cross-scale normalization construct. Returns
    an error if a 'convert <X> to <Y> scale' mapping is present; negation prose
    must NOT trip it (see `_FORBIDDEN_NORMALIZATION`)."""
    m = _FORBIDDEN_NORMALIZATION.search(text)
    if m:
        return [f"forbidden cross-scale normalization construct present (I-W1): "
                f"{m.group(0)!r}"]
    return []


def check_text(text: str) -> list[str]:
    """Run every structural assertion against SKILL.md content. Pure (takes the
    text) so `--selftest` can exercise it on in-memory samples."""
    errs = check_frontmatter(text)
    for label, sub in REQUIRED_SUBSTRINGS.items():
        if sub not in text:
            errs.append(f"missing {label}: `{sub}`")
    errs.extend(check_forbidden(text))
    return errs


# --------------------------------------------------------------------------
# selftest — self-contained GOOD/BAD samples (do NOT read the real file)
# --------------------------------------------------------------------------
_GOOD_SAMPLE = """\
---
name: warden
description: Consolidated pre-push review gate — temper, delve, red-team, siege, inquisitor.
---

# Warden

<!-- CANONICAL: shared/dispatch-convention.md -->
<!-- CANONICAL: shared/return-convention.md -->

## Overview

warden runs each reviewer on its own severity scale — there is no cross-scale
normalization (see `severity-verdict-contract.md`).
The gate is a disjunction of native gates.
The combined report is sectioned per reviewer.
No leg's severity is converted into another's.

## Reviewer set (native scales, no normalization)

The "Runs" column is split by reviewer-set: full | standalone.

| Reviewer | Runs (`full`) | Runs (`standalone`) | Gate | Notes |
|---|---|---|---|---|
| temper | always | always | T non-empty | the merge-verdict loop |
| delve | always | always | any kept finding | report-only, warden owns the fix |
| red-team | always | always | quality-gate ≠ PASS | via quality-gate |
| siege | conditional | conditional | Critical>0 | 6-agent Opus audit |
| inquisitor | always (unconditional) | conditional | any FAIL | stays unconditional in full |
"""

# The negation prose above must NOT trip the I-W1 guard; a real
# convert-to-scale construct MUST. This sample carries one.
_FORBIDDEN_SAMPLE = (
    _GOOD_SAMPLE
    + "\nTo merge, convert temper's Critical to siege's CVSS scale first.\n"
)

# Only "scale"/"normaliz"/"convert" mentions here are negation prose — the
# I-W1 guard must stay quiet on this in isolation.
_NEGATION_ONLY_SAMPLE = """\
warden runs each reviewer on its own severity scale — there is no cross-scale
normalization. Cross-scale conversion is forbidden. No leg's severity is
converted into another's.
"""

# Frontmatter regression case (missing `name: warden`).
_BAD_FRONTMATTER_SAMPLE = _GOOD_SAMPLE.replace("name: warden", "name: notwarden")


def selftest() -> int:
    # 1. GOOD sample passes every assertion.
    good_errs = check_text(_GOOD_SAMPLE)
    assert good_errs == [], f"GOOD sample should pass, got: {good_errs}"

    # 2. Per-clause RED: removing any single required substring flags exactly
    #    that clause. Auto-generated so every new entry gets its own RED case.
    for label, sub in REQUIRED_SUBSTRINGS.items():
        bad = _GOOD_SAMPLE.replace(sub, "‹removed›")
        errs = check_text(bad)
        assert any(label in e for e in errs), (
            f"removing {label!r} (`{sub}`) should flag it, got: {errs}")

    # 3. I-W1 negative RED path: a real convert-to-scale construct is flagged.
    fb_errs = check_forbidden(_FORBIDDEN_SAMPLE)
    assert any("I-W1" in e for e in fb_errs), (
        f"convert-to-scale construct should trip I-W1, got: {fb_errs}")
    assert any("I-W1" in e for e in check_text(_FORBIDDEN_SAMPLE)), (
        "I-W1 trip should also surface through check_text")

    # 4. Negation prose in isolation must NOT trip I-W1.
    assert check_forbidden(_NEGATION_ONLY_SAMPLE) == [], (
        "negation prose must not trip I-W1, got: "
        f"{check_forbidden(_NEGATION_ONLY_SAMPLE)}")

    # 5. Frontmatter guard still catches a broken `name:`.
    fm_errs = check_text(_BAD_FRONTMATTER_SAMPLE)
    assert any("name: warden" in e for e in fm_errs), (
        f"missing `name: warden` should be flagged, got: {fm_errs}")

    print("selftest OK — GOOD passes; each required clause, the I-W1 negative, "
          "and the frontmatter guard each have an exercised RED path.")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        return selftest()

    if not SKILL.is_file():
        print("WARDEN STRUCTURE CHECK FAILED:")
        print(f"  - {SKILL.relative_to(ROOT)} does not exist")
        return 1

    errs = check_text(SKILL.read_text(encoding="utf-8"))
    if errs:
        print("WARDEN STRUCTURE CHECK FAILED:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("OK — warden SKILL.md carries every required structural clause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
