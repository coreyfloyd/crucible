#!/usr/bin/env python3
"""Structural check for the warden skill scaffold (#464).

Invocation (from repo root):
    python3 scripts/check_warden_structure.py            # gate the real file
    python3 scripts/check_warden_structure.py --selftest # in-memory logic test

Asserts `skills/warden/SKILL.md` exists and carries the load-bearing structural
clauses: the `name: warden` frontmatter, a `description:` line, both canonical
link comments (dispatch + return conventions, per CLAUDE.md "link, never copy"),
a citation of the severity-verdict-contract, the reviewer-set section's
load-bearing clauses (the five-reviewer table, the disjunction-of-native-gates
statement, the sectioned-per-reviewer clause, the `reviewer-set` parameter, and
inquisitor's `unconditional` full-set coverage), and — as of Task 3 — the
Fix-behavior section's clauses: the per-leg residual commit primitive
(`git add -A && git commit`), the fully-empty clean-tree precondition
(`git status --porcelain` + "fully empty"/"no untracked"), the non-`fix:` subject
mandate (`chore(warden):` + a non-fix note), and the dirty-tree REFUSE clause
(`commit, stash, or clean untracked files`). Also asserts the ABSENCE of two
cross-scale + fix-path footguns: a cross-scale normalization construct (I-W1),
`git commit -a` (R11), and `git stash` in COMMAND form (R12) — the latter matched
as the command (`git stash`, mutating forms), NOT the bare word "stash" (warden's
own REFUSE clause contains "stash") and NOT the read-only `git stash create`
temper snapshot the design describes. Exits 0 when every clause is present and no
forbidden construct is found, 1 with a per-clause diff summary otherwise.
Stdlib only, no argparse.

Style mirrors `scripts/check_canonical_drift.py`: ROOT-from-`__file__`, error
accumulation, `sys.exit(main())`.

EXTENSION POINT (Phase-A tasks 4-8): add the substring a later task authors into
warden's SKILL.md to `REQUIRED_SUBSTRINGS` (label -> literal substring), or to
`REQUIRED_ANY` (label -> alternatives, at least one must appear) for an OR clause.
The frontmatter `name:`/`description:` guards live in `check_frontmatter()`; the
I-W1 normalization guard lives in `check_forbidden()`; the fix-path command
negatives (R11 `git commit -a`, R12 `git stash`) live in `check_negatives()`. The
`--selftest` GOOD/BAD samples are self-contained and must stay in sync — the
per-clause RED cases are generated automatically from `REQUIRED_SUBSTRINGS` and
`REQUIRED_ANY`, so a new required clause gets its own RED case for free; add a
dedicated BAD case for any new *negative*.
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
    # Task 3 — fix behavior (Universal per-leg residual commit + clean-tree
    # precondition), design L125-278.
    "per-leg residual commit primitive (M-c)": "git add -A && git commit",
    "clean-tree precondition command": "git status --porcelain",
    "non-`fix:` subject label (M-c)": "chore(warden):",
    "dirty-tree REFUSE clause": "commit, stash, or clean untracked files",
}

# label -> alternatives; at least ONE must appear (an OR clause). The dispatch
# frames these as disjunctions, so requiring both alternatives would be stricter
# than the spec. A RED case is auto-generated per label (removes every
# alternative, asserts the label is flagged).
REQUIRED_ANY: dict[str, tuple[str, ...]] = {
    # clean-tree precondition is "fully empty" (no tracked mods AND no untracked).
    "fully-empty clean-tree wording": ("fully empty", "no untracked"),
    # M-c non-`fix:` mandate note (backticked or bare).
    "non-fix subject note (M-c)": ("non-`fix:`", "non-fix"),
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

# R12 negative guard — `git stash` in COMMAND form. THE CRUX (M-o2): warden's own
# required REFUSE clause literally contains the word "stash" ("commit, stash, or
# clean untracked files"), so a bare-word `stash` grep would self-contradict
# against warden's own required clause and could never go green. So match the
# COMMAND (the `git ` prefix), never the bare word. The negative lookahead
# excludes the ONE allowed mention: `git stash create` — the read-only snapshot
# temper uses that leaves HEAD/index/tree untouched (design L133-134, authored
# verbatim). Every mutating form (`git stash` bare / push / save / pop) trips it;
# `git stash create` and the REFUSE-clause bare "stash" do not.
_FORBIDDEN_GIT_STASH = re.compile(r"\bgit\s+stash\b(?!\s+create\b)")


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


def check_negatives(text: str) -> list[str]:
    """Fix-path command negatives (regression guards from the design's R11/R12
    fixes). R11: no `git commit -a` (would commit only tracked edits, dropping a
    leg's new/untracked files — the design mandates `git add -A && git commit`).
    R12: no `git stash` in COMMAND form (warden has no working-tree save/restore
    machinery; `git stash create`, temper's read-only snapshot, is exempt — see
    `_FORBIDDEN_GIT_STASH`)."""
    errs: list[str] = []
    if "git commit -a" in text:
        errs.append("forbidden `git commit -a` present (R11): warden must use "
                    "`git add -A && git commit` so a leg's new/untracked files "
                    "land in the frozen HEAD")
    m = _FORBIDDEN_GIT_STASH.search(text)
    if m:
        errs.append(f"forbidden `git stash` command present (R12): {m.group(0)!r} "
                    "— warden has no working-tree save/restore machinery")
    return errs


def check_text(text: str) -> list[str]:
    """Run every structural assertion against SKILL.md content. Pure (takes the
    text) so `--selftest` can exercise it on in-memory samples."""
    errs = check_frontmatter(text)
    for label, sub in REQUIRED_SUBSTRINGS.items():
        if sub not in text:
            errs.append(f"missing {label}: `{sub}`")
    for label, alts in REQUIRED_ANY.items():
        if not any(alt in text for alt in alts):
            errs.append(f"missing {label}: none of {list(alts)} present")
    errs.extend(check_forbidden(text))
    errs.extend(check_negatives(text))
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

## Fix behavior

temper edits the working tree but never commits. The `git stash create` temper
uses in that mode only snapshots the tree; it is not how the fix is applied. So
temper's edits sit in the working tree, uncommitted, for warden to commit.

Universal per-leg residual commit (I-W6): after each fixer leg, warden commits
that leg's residual with `git add -A && git commit -m '<subject>'` and a
non-`fix:` subject (`chore(warden): temper fixes <run-id>`, per M-c).

Working-tree-clean precondition: warden asserts `git status --porcelain` is
fully empty — no tracked modifications and no untracked files. Standalone warden
on a dirty tree REFUSES: commit, stash, or clean untracked files, then re-run.
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

# ---- Task 3 fix-path negative/allow samples (R11 / R12) -------------------
# (a) R11 — a real `git commit -a` (would drop a leg's untracked files) FAILS.
_GIT_COMMIT_A_SAMPLE = (
    _GOOD_SAMPLE + "\nBad: warden runs `git commit -a` to commit the leg.\n")

# (b) THE CRUX trap — a sample whose ONLY "stash" occurrence is inside the
# REFUSE clause must NOT trip the R12 git-stash negative (bare word, no `git `
# prefix). This is what a bare-word grep would self-contradict against.
_REFUSE_ONLY_SAMPLE = (
    "Standalone warden on a dirty tree REFUSES: commit, stash, or clean "
    "untracked files, then re-run /warden.\n")

# (c) R12 — an actual `git stash` command line (mutating form) FAILS.
_GIT_STASH_CMD_SAMPLE = (
    _GOOD_SAMPLE + "\nBad: warden runs `git stash pop` to restore the tree.\n")

# (d) The ONE allowed mention — `git stash create` (temper's read-only snapshot,
# design L133-134) must NOT trip R12; the negative lookahead exempts it.
_GIT_STASH_CREATE_SAMPLE = (
    "temper uses `git stash create` to snapshot the tree; it is read-only.\n")


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

    # 2b. Per-clause RED for the OR clauses: removing EVERY alternative flags the
    #     label. Auto-generated, so a new REQUIRED_ANY entry gets its RED case.
    for label, alts in REQUIRED_ANY.items():
        bad = _GOOD_SAMPLE
        for alt in alts:
            bad = bad.replace(alt, "‹removed›")
        errs = check_text(bad)
        assert any(label in e for e in errs), (
            f"removing all of {list(alts)} for {label!r} should flag it, "
            f"got: {errs}")

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

    # 6. Fix-path negatives (R11 / R12) — the three required cases + the crux allow.
    # (a) a real `git commit -a` FAILS (R11).
    a_errs = check_negatives(_GIT_COMMIT_A_SAMPLE)
    assert any("R11" in e for e in a_errs), (
        f"`git commit -a` should trip R11, got: {a_errs}")
    # (b) THE CRUX: a sample whose only "stash" is the REFUSE clause must NOT
    #     trip R12 (bare word, no `git ` prefix) — verify it passes clean.
    b_errs = check_negatives(_REFUSE_ONLY_SAMPLE)
    assert b_errs == [], (
        f"REFUSE-clause 'stash' must NOT trip the git-stash negative, got: {b_errs}")
    # (c) an actual `git stash` command line FAILS (R12).
    c_errs = check_negatives(_GIT_STASH_CMD_SAMPLE)
    assert any("R12" in e for e in c_errs), (
        f"`git stash pop` command should trip R12, got: {c_errs}")
    # (d) the allowed `git stash create` snapshot must NOT trip R12.
    d_errs = check_negatives(_GIT_STASH_CREATE_SAMPLE)
    assert d_errs == [], (
        f"`git stash create` (read-only snapshot) must NOT trip R12, got: {d_errs}")

    print("selftest OK — GOOD passes; each required clause (incl. OR clauses), "
          "the I-W1 normalization negative, the R11 `git commit -a` and R12 "
          "`git stash`-command negatives (with the REFUSE-clause bare-word and "
          "`git stash create` allow-cases), and the frontmatter guard each have "
          "an exercised path.")
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
