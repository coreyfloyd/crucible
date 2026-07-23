# Ground-truth provenance — `tw3-code-under-docs` (INV-P8, code-under-docs exclusion)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` includes inquisitor — via block 3, NOT via an escalator.** Block 1
  (escalators): neither `docs/conf.py` nor `docs/guide.md` matches any INTERFACE/API/SCHEMA
  or DEPENDENCY/lockfile glob (`conf.py` is not `__init__.py`/`index.*`; there is no
  `api/`/`schema*`/lockfile match), no binary path → miss. Block 2 (pure-doc bounded
  subtraction): `docs/conf.py` is a **code** file, and SKILL.md is explicit that "a code
  file (e.g. `docs/conf.py`) … under `docs/` is **not** a pure-doc file, so a diff
  containing one is not all-doc and does not take block 2" → the `.py` sibling defeats
  block 2. Block 3 (retained reach clause): `>1 changed file` (2 files) → **run
  inquisitor**. siege absent (non-security).

- **`verdict` = PASS.** All running legs clean → PASS.

- **Teeth (why 2 files, and why block 3 not an escalator).** The 2-file shape gives the
  exclusion its teeth: a lone `docs/conf.py` would SKIP via block-4 fall-through (block 3
  needs `>1 file`), proving nothing about the doc-sibling exclusion. The `docs/guide.md`
  sibling is precisely what the exclusion must prevent from earning an all-doc skip — with
  the `.py` present, block 2 must NOT fire, and block 3 then runs inquisitor on the file
  count alone. This deliberately RUNS via block 3, not via an escalator (neither path
  escalates).

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
