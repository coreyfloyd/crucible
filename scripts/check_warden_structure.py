#!/usr/bin/env python3
"""Structural check for the warden skill scaffold (#464).

Invocation (from repo root):
    python3 scripts/check_warden_structure.py            # gate the real file
    python3 scripts/check_warden_structure.py --selftest # in-memory logic test

Asserts `skills/warden/SKILL.md` exists and carries the load-bearing structural
clauses: the `name: warden` frontmatter, a `description:` line, both canonical
link comments (dispatch + return conventions, per CLAUDE.md "link, never copy"),
and a citation of the severity-verdict-contract. Exits 0 when every clause is
present, 1 with a per-clause diff summary otherwise. Stdlib only, no argparse.

Style mirrors `scripts/check_canonical_drift.py`: ROOT-from-`__file__`, error
accumulation, `sys.exit(main())`.

EXTENSION POINT (Phase-A tasks 2-8): add the substring a later task authors into
warden's SKILL.md to `REQUIRED_SUBSTRINGS` (label -> literal substring). The
frontmatter `name:`/`description:` guards live in `check_frontmatter()`. The
`--selftest` GOOD/BAD samples are self-contained and must stay in sync with the
list so the logic is exercised without reading the real file.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills/warden/SKILL.md"

# label -> literal substring that MUST appear somewhere in SKILL.md. Later
# Phase-A tasks EXTEND this dict; keep the selftest samples below in sync.
REQUIRED_SUBSTRINGS: dict[str, str] = {
    "dispatch canonical link": "<!-- CANONICAL: shared/dispatch-convention.md -->",
    "return canonical link": "<!-- CANONICAL: shared/return-convention.md -->",
    "severity-verdict-contract citation": "severity-verdict-contract.md",
}


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


def check_text(text: str) -> list[str]:
    """Run every structural assertion against SKILL.md content. Pure (takes the
    text) so `--selftest` can exercise it on in-memory samples."""
    errs = check_frontmatter(text)
    for label, sub in REQUIRED_SUBSTRINGS.items():
        if sub not in text:
            errs.append(f"missing {label}: `{sub}`")
    return errs


# --------------------------------------------------------------------------
# selftest — self-contained GOOD/BAD samples (do NOT read the real file)
# --------------------------------------------------------------------------
_GOOD_SAMPLE = """\
---
name: warden
description: Consolidated pre-push review gate.
---

# Warden

<!-- CANONICAL: shared/dispatch-convention.md -->
<!-- CANONICAL: shared/return-convention.md -->

## Overview

warden is an orchestrator-tier pre-push review gate. No cross-scale
normalization (see `severity-verdict-contract.md`).
"""

# Missing the return canonical link — must be flagged.
_BAD_SAMPLE = """\
---
name: warden
description: Consolidated pre-push review gate.
---

# Warden

<!-- CANONICAL: shared/dispatch-convention.md -->

## Overview

warden is a gate. See `severity-verdict-contract.md`.
"""


def selftest() -> int:
    good_errs = check_text(_GOOD_SAMPLE)
    assert good_errs == [], f"GOOD sample should pass, got: {good_errs}"

    bad_errs = check_text(_BAD_SAMPLE)
    assert bad_errs, "BAD sample should fail (missing return canonical link)"
    assert any("return canonical link" in e for e in bad_errs), (
        f"BAD sample should flag the missing return link, got: {bad_errs}")

    print("selftest OK — GOOD sample passes, BAD sample flags the missing clause.")
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
