---
name: qc-hardening
description: Use when development is functionally complete and code needs hardening before production deployment, release, or merge. Triggers include "harden", "production-ready", "hardening pass", "code audit", "pre-production review", or when user says "run this against the codebase" after feature work is done. Also use after major refactors, before cutting release branches, or when preparing for security review.
---

# Production Hardening

**REQUIRED:** Load `qc-core` first. Laws, ledger, verdict, profile, Discovery+Verify, severity, deferred vocabulary, CLEAN lists, commits, and the anti-rationalization table live there. This skill is the 14-pass specialization.

Drive residual **concrete failure scenarios** — especially under realistic call sequences, dual/public paths, and live external/adapter boundaries — to zero or explicit deferral, without changing functional behavior. Mechanical passes remove noise; Carmack and Chaos prove the absences tools miss; Maintainability converts the evidence into a release judgment. Clean Carmack across all modules plus a green Chaos suite is the expected terminal state of well-hardened code.

Coherence owns static contracts and canonical forms. This skill owns the runtime proof of sequences and live paths. Harvest Carmack `violated_invariant` values into profile `invariants[]`. If maintainability debt cannot be fixed locally, defer it (`needs-architecture`); do not rewrite.

## When to Use

- Feature development is functionally complete; tests exist and pass (if not, fix them first)
- Preparing for production, release, or merge

**Do not use when:** feature work is in progress, architecture needs changing, or the code is a throwaway prototype.

## How to Execute

1. Load `qc-core`. Read `.qc-profile.json` (migrate `.hardening-profile.md` on first run — [qc-core profile](../qc-core/references/profile.md)).
2. Run Pre-Flight (below).
3. Passes 1–11 (mechanical) per [references/passes-1-11.md](references/passes-1-11.md). Do not skip or reorder.
4. Passes 12–14 (deep) per [references/passes-12-14.md](references/passes-12-14.md). Carmack/Chaos findings need the structured scenario triple. Profile `examination.qc-hardening` is the Carmack manifest: `EXAMINED` requires the five questions or `{invariant, assumptions, sequence_risk}` — a one-sentence invariant is not enough. Pass 1 CLEAN stays on the ledger `examined[]`.
5. Scale with import-graph partitioning and the shared workflow: [qc-core discovery-verify](../qc-core/references/discovery-verify.md) plus [references/scaling-and-dispatch.md](references/scaling-and-dispatch.md).
6. After each pass, atomically rewrite `.qc-findings/qc-hardening.json` and update `.qc-profile.json` (examination, hot spots, pass debt, streaks).
7. Before the summary: `python3 ../qc-core/scripts/verify_ledger.py .qc-findings/qc-hardening.json`. Fix the ledger, not the script.

## Pre-Flight

1. Read `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`, then `pyproject.toml` / `package.json`. Over ~5K LOC, read the tree first.
2. `git log --oneline --grep="harden"`. Clean re-runs are a positive signal, not a reason to manufacture findings.
3. Profile: re-validate `invariants[]` and `pass_debt[]` against current code. Focus hot spots. Compute the reexam set (`partition.py --reexam --since <last_examined_sha>`): changed files plus import-graph neighbors that sit in `hot_spots[]` / `pass_debt[]`. Those neighbors are mandatory composition re-examination even if they did not change. Quick-check eligible passes (4, 5, 6, 7, 10, 11) after 3 clean streaks and no new code in scope — never 1, 2, 3, 8, 9, 12, 13, 14.
4. Detect shape (language, package manager, CI, container, secrets, public API, concurrency). Toolchain for passes 4 and 8 — isolated runners (`pipx run`, `npx`), never add audit tools as project deps:

| Language | Type checker | Linter | Coverage |
|----------|-------------|--------|----------|
| Python | `mypy . --strict` | `ruff check . --fix && ruff format --check .` | `coverage run -m <test_runner> && coverage report --show-missing` |
| TypeScript | `npx tsc --noEmit` | `npx eslint .` | `npx jest --coverage` |
| Rust | `cargo check` | `cargo clippy -- -D warnings` | `cargo tarpaulin` |
| Go | `go vet ./...` | `staticcheck ./...` | `go test -cover ./...` |

5. Full test suite is the baseline. Failures: stop and fix. No suite at all: P1; Pass 8 starts coverage; do not grade `READY` until a suite exists and passes.
6. Record the starting commit. Every pass commits independently (`harden: pass N — <name> (<ids>)`). Batch consecutive clean passes; never batch-skip execution.

## Output

Ledger schema, atomic write, scenario triple, CLEAN lists, closed deferred codes, related_findings, and verdict math: **qc-core**. Skill name is `qc-hardening`. Presence P0 policy: any P0, even fixed, is `NOT_READY`.

```json
{
  "schema_version": "1.1",
  "skill": "qc-hardening",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "F12.3",
      "pass": 12,
      "scope": "module",
      "severity": "P1",
      "confidence": "proven",
      "file": "app/foo.py",
      "line": 42,
      "what": "Race in concurrent write path",
      "why": "Two threads pass the _closed guard before either acquires the lock",
      "scenario": {
        "trigger": "Thread A and thread B call write() after close() has been requested",
        "violated_invariant": "close() is serialized; no write proceeds after close begins",
        "observable": "handle closed under an in-flight write; truncated output"
      },
      "fix": "Move _closed check inside the lock acquisition",
      "fixed": true
    }
  ],
  "examined": [
    {
      "artifact": "app/clean.py",
      "invariant": "add(a, b) returns the numeric sum of its two arguments with no hidden state"
    }
  ],
  "verdict": "READY_WITH_DEBT"
}
```

Pass debt (deep pass catches what a mechanical pass should have): write `pass_debt[]` on the profile. Details: [references/pass-debt.md](references/pass-debt.md).

## What Not to Do (hardening-specific)

- Do not add features, refactor architecture, or change public signatures / parameter defaults.
- Do not change test assertions to match buggy code without an independent proof the test is wrong.
- Do not fix P3. Do not optimize without a concrete n.
- Do not manufacture findings. Clean pass = clean pass. "Systems always run degraded" is not a reason to invent residual work.
- Do not run production chaos, Game Days, or invent recovery/monitoring. Blast radius is in-repo tests.

A run is incomplete if findings were handled but examination, `invariants[]`, and `pass_debt[]` were not updated. Empty findings plus updated artifacts is a valid win.

Hardening-specific loopholes (shared table is in qc-core):

| Excuse | Reality |
|--------|---------|
| "The `[]`→`None` sentinel fix is behavior-preserving, so changing the default doesn't change the signature." | The default is part of the public signature. Defer `public-signature`. Private functions: fix in place. |
| "Pass 3/13 say add validation, so I'll trim/lowercase/canonicalize." | Detect-and-report is hardening. Rewriting the value is a feature. Defer `behavior-change`. |
| "This isn't a refactor — it's the only real fix for a systemic Carmack P1, and P1 means fix-this-pass." | The only-architecture fix *is* a deferred finding. `fixed: false` + `needs-architecture` satisfies "fix this pass." |

Summary banner: qc-core skeleton, with a 14-pass table and the maintainability scorecard (Consistency / Maintainability / Overall, hot spots) from Pass 14.
