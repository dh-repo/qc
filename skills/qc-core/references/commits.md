# Commits and summary banner

## Commits

Each pass (or each coherence sub-audit, or each docs gate-fix batch) commits independently.

Format: `<skill>: <unit> — <name> (<ids>)` or `(0 fixes)` if clean.

Examples:

```
harden: pass 2 — Security (F2.1 F2.3)
harden: passes 3,5,6,7 — clean
coherence: semantic — M1.2
docs: accuracy gate (D2.1)
```

Batch consecutive *clean* units into one commit. Clean units with zero code changes need no commit. Do not batch-skip execution.

If a fix breaks a test, fix the test in the same commit — verifying new correct behavior, not preserving a stale expectation.

Never `git add -a` when in-flight work is in the tree. Stage only files this unit changed.

## Summary banner

After the run, emit this skeleton (skills fill the middle):

```
<SKILL> SUMMARY
===============
Starting commit: <hash>
Final commit:    <hash>
Units run:       <N — note SKIPPED / quick-checked>
Lines changed:   +<added> / -<removed>

<SKILL-SPECIFIC UNIT TABLE>

FINDING INDEX
  <id> (P#) — <one-line> — fixed in <hash> | deferred: <code>

TOTALS
  Findings fixed:     X
  P0 findings:        X (any P0 → NOT_READY; even a fixed P0 needs release sign-off)
  P1 remaining:       X

CLEAN
  X of N units found no issues
  Examined artifacts: N (see ledger `examined`)

DEFERRED (confirmed, not fixed)
  <id> (P#, deferred) — <one-line> — <code>: <detail>

REMAINING CONCERNS (human judgment)
  - ...

TEST SUITE STATUS
  Full suite: PASS/FAIL (X tests)
```

Machine `verdict` must match this banner. Any blocking P0 or open P1 → `NOT_READY` and the banner says **RELEASE BLOCKED** with the items listed.
