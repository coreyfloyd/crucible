# Ground-truth provenance — `tw3-pair-api-base` (INV-P7 monotonicity, API pair — BASE)

Hand-derived from `skills/warden/SKILL.md` (the *Standalone inquisitor-inclusion
predicate* subsection); not recorded from a live run.

- **`reviewer_set` = temper, delve, red-team — inquisitor SKIPPED via block-4.** Block 1
  (escalators): the single changed path `src/util.py` is non-API, non-dependency code, no
  binary → miss. Block 2: code, not pure-doc → miss. Block 3: 1 file, 1 module, not `>1` →
  miss. Block 4 → **skip inquisitor**. siege absent (non-security).

- **`verdict` = PASS.** All three running legs clean → PASS.

- **Pair role (INV-P7).** This is the BASE of the API monotonicity pair. Its signal member
  `tw3-pair-api-signal` differs ONLY by the API-glob signal (`src/api/util.py`) at the SAME
  1-file count. With both at 1 file, block 3 (`>1 file`) can never fire for either member,
  so the ONLY thing that flips the signal member to RUN is the block-1 escalator — a broken
  or removed escalator would flip the signal member back to SKIP and the pair would lose
  its skip→run transition. That equal file count is what makes the pair genuinely isolate
  INV-P7 (a 1-file-base / 2-file-signal shape would let block 3 run the signal member on
  file count alone, so deleting the escalator would still pass — no teeth).

Schema-gated only; behavioral teeth defer to the install-gated live pass (Acceptance
Gate 2). Not a live run.
