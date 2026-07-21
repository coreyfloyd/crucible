#!/usr/bin/env python3
"""Structural check for build's clean-tree contract at the review-gate entry (#464).

Invocation (from repo root):
    python3 scripts/check_build_clean_tree_contract.py            # gate the real file
    python3 scripts/check_build_clean_tree_contract.py --selftest # in-memory logic test

The warden design (2026-07-19-warden-design.md L465-487) makes warden's entry
precondition `git status --porcelain` **fully empty** (tracked AND untracked).
Because the Phase-4 test runs sit between the Phase-3 commit and the review gate,
build must **guarantee** that clean tree — by PRODUCING it (commit the
test-regenerated artifacts / gitignore the incidentals), not by a bare
"assert-clean" branch that would spuriously halt a healthy build. This check
asserts build Phase 4 carries the five load-bearing clauses of that dischargeable
contract.

CLAUSE-PRESENCE, NOT POSITIONAL: at Task 11 there is no `Use crucible:warden` in
build yet (the cutover that inserts it is Task 12), so this asserts only that the
five clauses are PRESENT within the `## Phase 4: Completion` section — it does NOT
assert their ordering against the warden call.

The section is extracted (`## Phase 4: Completion` up to the next `## ` heading or
EOF) and the five substrings are asserted **within that slice** — a whole-file
grep would let an unrelated clause elsewhere (the stale-prose sweep, or Task 12's
future warden mention) satisfy the check vacuously.

Style mirrors `scripts/check_canonical_drift.py`: ROOT-from-`__file__`, error
accumulation, `sys.exit(main())`, stdlib only, no argparse. The five pins are
mutually disjoint (none a substring of another), so the `--selftest` auto-generates
a per-clause RED case for free (`GOOD.replace(pin, …)` → assert that clause flags).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "skills/build/SKILL.md"

# label -> literal substring that MUST appear within build's Phase 4 section.
# The five clauses of the dischargeable clean-tree contract (design L465-487).
REQUIRED_SUBSTRINGS: dict[str, str] = {
    # 1. the clean-tree precondition command build runs before the review gate.
    "clean-tree precondition command": "git status --porcelain",
    # 2. tracked test-regenerated artifacts are COMMITTED (normal output).
    "commit test-regenerated clause": "commit test-regenerated",
    # 3. incidental artifacts are GITIGNORED (test-hygiene fix).
    "gitignore incidentals clause": "gitignore",
    # 4. NO bare assert-clean branch — build produces the clean tree, not merely
    #    checks for one (an assert-clean would spuriously halt a healthy build).
    "no bare assert-clean clause": "assert-clean",
    # 5. a tree still dirty after commit/gitignore is a SURFACED defect, not swept.
    "still-dirty surfaced-defect clause": "surfaced build/test defect",
}

# Extract the `## Phase 4: Completion` section body: everything from that heading
# up to the next `## ` heading (or EOF). Scoping the five-clause assertion to this
# slice is the load-bearing rigor — see module docstring.
#
# build/SKILL.md carries the heading TWICE: an early `pipeline-status.md` TEMPLATE
# block (`## Phase 4: Completion\nStatus: NOT_STARTED`, inside a ``` fence) and the
# real WORKFLOW section further down. The template block always precedes the
# workflow section, so we take the LAST match — the real Phase-4 workflow.
_PHASE4_RE = re.compile(
    r"^## Phase 4: Completion\b.*?(?=^## |\Z)",
    re.DOTALL | re.MULTILINE,
)


def extract_phase4(text: str) -> str:
    """Return the real `## Phase 4: Completion` WORKFLOW section body, or '' if
    absent. Takes the LAST heading match — an earlier `pipeline-status.md` template
    block reuses the same heading and must not shadow the workflow section."""
    matches = _PHASE4_RE.findall(text)
    return matches[-1] if matches else ""


def check_section(section: str) -> list[str]:
    """Assert every required clause is present in the Phase-4 section. Pure (takes
    the slice) so `--selftest` can exercise it on in-memory samples. A distinct
    'section not found' error is returned when the slice is empty."""
    if not section:
        return ["Phase 4 section not found (no `## Phase 4: Completion` heading)"]
    return [
        f"missing {label} within Phase 4: `{sub}`"
        for label, sub in REQUIRED_SUBSTRINGS.items()
        if sub not in section
    ]


# --------------------------------------------------------------------------
# selftest — self-contained GOOD/BAD samples (do NOT read the real file)
# --------------------------------------------------------------------------
_GOOD_SAMPLE = """\
## Phase 4: Completion

After all tasks complete:

1. Run acceptance tests — verify they PASS.
2. Run full test suite (unit + integration).
2.5. **Guarantee a fully-clean working tree before the review gate.** Run
   `git status --porcelain` and drive the tree to fully empty by producing that
   clean state, not merely checking for one:
   - Tracked modifications (a passing test regenerated a golden/snapshot) →
     commit them: `chore(build): commit test-regenerated artifacts before gate`.
   - Non-ignored new untracked files → classify: a golden/fixture that belongs in
     the repo → commit it; an incidental artifact (coverage, cache) → gitignore it.
   - There is NO bare "assert-clean" branch — build must PRODUCE the clean tree.
   - A tree still dirty after that step is a surfaced build/test defect — not swept.
3. Use crucible:temper on the full implementation.

## Escalation Triggers
"""

# A section missing exactly one clause (the surfaced-defect clause) must FAIL.
_BAD_SAMPLE = _GOOD_SAMPLE.replace(
    "surfaced build/test defect", "fine and ignored")

# Mirrors the real file: a `pipeline-status.md` TEMPLATE block reuses the
# `## Phase 4: Completion` heading BEFORE the real workflow section. The extractor
# must pick the LAST (workflow) match — the template block carries none of the five
# clauses, so selecting it would spuriously FAIL a correctly-authored build.
_TEMPLATE_THEN_WORKFLOW_SAMPLE = (
    "## Phase 4: Completion\nStatus: NOT_STARTED\n```\n\nsome prose\n\n" + _GOOD_SAMPLE)


def selftest() -> int:
    # 1. GOOD sample (a Phase-4-shaped slice with all five clauses) passes.
    section = extract_phase4(_GOOD_SAMPLE)
    assert section, "GOOD sample should yield a Phase 4 section"
    good_errs = check_section(section)
    assert good_errs == [], f"GOOD sample should pass, got: {good_errs}"

    # 2. Per-clause RED: removing any single required substring flags exactly that
    #    clause. Auto-generated so every entry gets its own RED case; the five pins
    #    are mutually disjoint, so a single replace never collaterally hides another.
    for label, sub in REQUIRED_SUBSTRINGS.items():
        bad = extract_phase4(_GOOD_SAMPLE.replace(sub, "‹removed›"))
        errs = check_section(bad)
        assert any(label in e for e in errs), (
            f"removing {label!r} (`{sub}`) should flag it, got: {errs}")

    # 3. The concrete BAD sample (one clause dropped) FAILS on that clause.
    bad_errs = check_section(extract_phase4(_BAD_SAMPLE))
    assert any("surfaced-defect" in e for e in bad_errs), (
        f"BAD sample (dropped surfaced-defect clause) should flag it, got: {bad_errs}")

    # 4. A text with NO Phase 4 heading yields the distinct 'section not found'.
    nf_errs = check_section(extract_phase4("## Phase 3: Execution\n\nno phase 4 here\n"))
    assert any("section not found" in e for e in nf_errs), (
        f"missing Phase 4 heading should give 'section not found', got: {nf_errs}")

    # 5. A template block reusing the heading BEFORE the workflow section must not
    #    shadow it — the extractor takes the LAST match, so this still passes.
    tw_errs = check_section(extract_phase4(_TEMPLATE_THEN_WORKFLOW_SAMPLE))
    assert tw_errs == [], (
        f"a `pipeline-status.md` template Phase-4 heading must not shadow the "
        f"workflow section (extractor takes the last match), got: {tw_errs}")

    print("selftest OK — GOOD passes; each of the five clauses has an auto-generated "
          "per-clause RED case; a section missing the surfaced-defect clause FAILS; "
          "and a text with no `## Phase 4: Completion` heading yields the distinct "
          "'section not found' error.")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        return selftest()

    if not BUILD.is_file():
        print("BUILD CLEAN-TREE CONTRACT CHECK FAILED:")
        print(f"  - {BUILD.relative_to(ROOT)} does not exist")
        return 1

    section = extract_phase4(BUILD.read_text(encoding="utf-8"))
    errs = check_section(section)
    if errs:
        print("BUILD CLEAN-TREE CONTRACT CHECK FAILED:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("OK — build Phase 4 carries every clause of the dischargeable "
          "clean-tree contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
