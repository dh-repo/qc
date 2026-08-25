---
name: qc-hardening
description: Use when development is functionally complete and code needs hardening before production deployment, release, or merge. Triggers include "harden", "production-ready", "hardening pass", "code audit", "pre-production review", or when user says "run this against the codebase" after feature work is done. Also use after major refactors, before cutting release branches, or when preparing for security review.
---

# Production Hardening

Systematic, multi-pass code audit that finds and fixes defects without changing functional behavior. Each pass is additive and idempotent, and the sequence closes with an evidence-based maintainability and consistency judgment.

**Core principle:** Find and fix problems. Do not add features. Do not refactor architecture. Do not change functional behavior. Harden what exists. If the maintainability scan exposes structural debt that cannot be fixed locally, record it explicitly instead of forcing a rewrite.

## When to Use

- Feature development is functionally complete
- Tests exist and pass (if not, fix them first)
- Preparing for production, release, or merge

**Do not use when:** feature work is in progress, architecture needs changing, or the code is a throwaway prototype.

## How to Execute

1. Run Pre-Flight (below).
2. Run passes 1–11 per [references/passes-1-11.md](references/passes-1-11.md).
3. Run passes 12–14 per [references/passes-12-14.md](references/passes-12-14.md).
4. For codebases >5K LOC or under context pressure, apply scaling and dispatch strategy from [references/scaling-and-dispatch.md](references/scaling-and-dispatch.md).
5. Write findings to `.qc-findings/qc-hardening.json` after each pass (see Output Contract below).
6. Record pass debt and update `.hardening-profile.md` per [references/pass-debt.md](references/pass-debt.md).
7. Before emitting the Summary Report, machine-check the ledger. From the *target repository root*, run the copy of `scripts/verify_ledger.py` that ships with this skill (the directory that contains this `SKILL.md`):

```bash
python3 "$SKILL_DIR/scripts/verify_ledger.py" .qc-findings/qc-hardening.json
```

`$SKILL_DIR` is wherever the agent installed this skill (`~/.claude/skills/qc-hardening`, `~/.codex/skills/qc-hardening`, `~/.grok/skills/qc-hardening`, or a project `.claude/skills/qc-hardening`). The script validates the ledger against the bundled schema and recomputes the verdict; if it reports a mismatch or a malformed finding, fix the ledger (not the script) before reporting.

## Pre-Flight

**1. Read project conventions.** Read `CLAUDE.md` (or `AGENTS.md`, `GEMINI.md`) — it defines test commands, code style, framework choices, and gotchas that override defaults here. Read `pyproject.toml` / `package.json` for tooling config. For codebases over ~5K LOC, read the directory tree and module index first, then read each module during the relevant pass.

**2. Check for prior hardening.** Run `git log --oneline --grep="harden"`. Clean passes on re-runs are a positive signal, not a reason to manufacture findings.

**2b. Load the hardening profile** (if `.hardening-profile.md` exists). Use it to focus on hot spots, skip quick-check-eligible passes, and carry forward the Carmack audit manifest.

**2c. Quick-check mode.** If a pass has been clean for 3+ consecutive runs AND no new code added to its scope, downgrade to tool-only (skip manual audit). Eligible: passes 4, 5, 6, 7, 10, 11. Never quick-checked: 1, 2, 3, 8, 9, 12, 13, 14.

**3. Detect project shape and toolchain:**

| Signal | Detection | Implication |
|--------|-----------|-------------|
| Language | File extensions, shebang lines | Determines toolchain |
| Package manager | `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml` | Dependency audit tool |
| CI | `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml` | Cross-reference with local checks |
| Container | `Dockerfile`, `docker-compose.yml` | Check for secrets in build layers |
| Secrets management | `.env.example`, vault references | Determines secrets audit scope |
| Public API surface | Library exports, REST/gRPC endpoints, CLI args | Whether Pass 10 applies |
| Concurrency | Threads, async/await, multiprocessing, signal handlers | Whether Pass 5 applies |

**Toolchain matrix** (used by passes 4, 8; use isolated runners — `pipx run`, `npx` — to avoid dependency conflicts):

| Language | Type checker | Linter | Coverage |
|----------|-------------|--------|----------|
| Python | `mypy . --strict` | `ruff check . --fix && ruff format --check .` | `coverage run -m <test_runner> && coverage report --show-missing` (detect runner from `pyproject.toml`, `conftest.py`, or CLAUDE.md) |
| TypeScript | `npx tsc --noEmit` | `npx eslint .` | `npx jest --coverage` |
| Rust | `cargo check` | `cargo clippy -- -D warnings` | `cargo tarpaulin` |
| Go | `go vet ./...` | `staticcheck ./...` | `go test -cover ./...` |

**4. Verify tooling.** Install audit tools using isolated runners. Do NOT add them to project dependencies.

**5. Run the full test suite.** Record the baseline. If tests fail, stop and fix them first. If the project has **no test suite at all**, record that as a P1 (a passing suite is a hardening prerequisite): let Pass 8 establish the initial coverage, write regression tests alongside every deep-pass (12-13) fix, and do not grade the run `READY` until a suite exists and passes.

**6. Record the starting commit hash.** Every pass commits independently for isolated revert.

## Severity & Evidence

Findings use four severity levels: **P0** (outage — fix immediately, block release), **P1** (defect — fix this pass), **P2** (weakness — fix if low-risk), **P3** (style/observation — do not fix, note only if systemic). Full calibration table, evidence standard (full vs. lightweight), and cross-pass severity guidance: [references/severity-calibration.md](references/severity-calibration.md).

## Output Contract

Write findings to `.qc-findings/qc-hardening.json` (project root) — a **single JSON object** conforming to the suite-shared schema [`references/qc-finding.schema.json`](references/qc-finding.schema.json). `qc-all`'s rollup reads this exact path and shape, so do not rename it, split it per pass, or convert it to JSON Lines. Legacy `.hardening-findings.json` / `.hardening-findings.tmp` are retired — do not use them on new runs. A copy of the schema ships in this skill so a standalone install still validates.

**Accumulate, then write atomically.** The file holds the run's *full accumulated findings so far*, not a per-pass fragment. After each pass, rewrite the whole object (every finding to date) to a temp file and `rename()` it over the target. Atomic replace — never an in-place edit — so a concurrent reader (the `qc-all` rollup, or another agent working the same tree) never observes a half-written file, and an interrupted run leaves the last complete state intact. Update incrementally through the run; do not wait until pass 14.

**Required fields** (per schema): `schema_version` (`"1.0"`), `skill` (`"qc-hardening"`), `run_id` (`<ISO8601>Z-<7-char-sha>`), `git_sha`, `findings[]`, `verdict`. Each finding requires `id`, `severity`, `file`, `what`, `fixed`; carry `pass`, `line`, `why`, `fix`, `scope` where known. A **deferred** finding sets `fixed: false` **and** a `deferred_because` string — the rollup's verdict math keys off exactly that field, so a deferral recorded any other way reads as an *open* finding and blocks release.

```json
{
  "schema_version": "1.0",
  "skill": "qc-hardening",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "F12.3",
      "pass": 12,
      "scope": "module",
      "severity": "P1",
      "file": "app/foo.py",
      "line": 42,
      "what": "Race condition in concurrent write path",
      "why": "Two threads can pass the _closed guard before either acquires the lock",
      "fix": "Move _closed check inside the lock acquisition",
      "fixed": true
    }
  ],
  "verdict": "READY_WITH_DEBT"
}
```

**Verdict — one enum, shared with `qc-all`.** Compute it the way the rollup does, so a standalone hardening run and a suite run never disagree:

| Verdict | Condition | Summary banner |
|---------|-----------|----------------|
| `NOT_READY` | Any P0 (fixed or not), **or** any *open* P1 (`fixed: false` with no `deferred_because`) | **RELEASE BLOCKED** |
| `READY_WITH_DEBT` | Zero P0; every P1 fixed or deferred; debt remains (deferred findings or unaddressed P2) | Shippable with recorded debt |
| `READY` | Zero P0, zero P1; P2/P3 clean or deferred | Release-ready as-is |

Pass 14's prose judgment maps onto the same enum: "release-ready as-is" → `READY`, "releaseable with deferred debt" → `READY_WITH_DEBT`, "not yet releaseable" → `NOT_READY`. (`SKIPPED` is reserved for `qc-all` to mark a sub-skill it did not run this cycle — a hardening run that executes never emits it.)

**Any P0 blocks even when fixed.** The suite rollup (`qc-all/references/rollup.md`) and `qc_deterministic.sh` count P0 by presence, not by `fixed` state — so a run that hit and repaired an outage-class bug still grades `NOT_READY`. That is a deliberate human-review gate, not a bug: record the fix (`fixed: true`) so the reviewer sees it was addressed, and let a human clear the release. Gating on "unfixed P0" instead would split-verdict against the suite on the single most release-critical severity.

## Pass Debt

When a deep pass (12 or 13) catches a bug that an earlier mechanical pass missed, record it in the Pass Debt table in `.hardening-profile.md`. Future runs use this table to direct extra attention to affected modules and passes. Full Pass Debt mechanism, findings ledger lifecycle, Hardening Profile format, Reverting, and Re-Running: [references/pass-debt.md](references/pass-debt.md).

## Persistence

`.hardening-profile.md` in the project root persists across runs. Commit it alongside the summary commit — it's project metadata, not ephemeral state. It records run history, hot spots, pass streaks, pass debt, and the Carmack audit manifest. Load it in Pre-Flight (step 2b) and update it incrementally through the run so interrupted runs preserve all findings discovered so far.

## Pass Execution Rules

- Run passes in order. Each pass commits before the next begins.
- Commit format: `harden: pass N — <name> (<finding IDs, e.g., F2.1 F2.3>)` or `(0 fixes)` if clean.
- **Batch clean passes into a single commit.** If passes 3, 5, 6, and 7 all find nothing, commit once: `harden: passes 3,5,6,7 — clean`. Clean passes with zero code changes need no commit at all.
- Write findings to `.qc-findings/qc-hardening.json` after each pass. The file is read by Carmack (pass 12) for multi-order analysis and by Pass 13 to target adjacent code.
- If a fix creates a test regression, fix it before committing.
- **Test breakage from later passes:** Update broken tests in the same commit as the production fix, verifying new correct behavior — not preserving the old expectation.
- **Do not batch-skip passes.** Run each one. Batch the commits, not the execution.

## What Not to Do

- **Do not add features.** "While I'm here, this would be better with..." — stop.
- **Do not refactor architecture.** Fix defects within the existing structure.
- **Do not change test assertions to match buggy code.** Investigate first.
- **Do not manufacture findings.** Clean pass = clean pass.
- **Do not fix P3 findings.** P2 is the floor for code changes.
- **Do not optimize without evidence.** "This is O(n^2) and n can reach 100k" is a finding. "This might be slow" is not.

## Rationalization Table

Every excuse below sounds principled. Each is a known loophole the pressure-tests confirmed agents fall for. When you hear yourself making one, stop.

| Excuse | Reality |
|--------|---------|
| "The tangled structure *is* the defect, so restructuring is the minimal fix for this P1." | A structural split is never the minimal fix. Apply the smallest behavior-preserving patch in place; if none exists without splitting, defer it (`fixed:false` + `deferred_because`). A bug in code that needs refactoring is not a license to refactor. |
| "It's technically a style/naming nit, but the reviewer always blocks it (or fixing it now saves a round-trip), so it's really a P2." | Reviewer preference and cycle time are not severity inputs. Severity measures effect on the running system; naming/style is always P3. Re-grading it up to clear the P2 floor is manufacturing a finding. |
| "Three clean passes looks lazy — I'll re-read at a stricter altitude and file the borderline things at P2." | Fabricating *severity* is the same offense as fabricating a finding. Severity is the worst honest scenario, never how the count reads. You may drop a finding you can't justify; you may never raise one for the tally. Three zeros is the expected output of clean code. |
| "The `[]`→`None`-sentinel fix is behavior-preserving, so changing the default doesn't really change the signature." | A parameter's default value is part of the public signature (`help()`, `inspect.signature()`, stubs all read it). The bug is real but the clean fix is unavailable in place: defer it. (Private/internal functions: fix in place.) |
| "No time to investigate — release is in N minutes; the test is probably stale, I'll match its expected value to current output." | A deadline is not evidence about which side is correct, and the code's own output can't prove its test wrong (circular). Prove it from an independent source, or the assertion stays red and is filed. "Investigate first" has no express lane. |
| "This input clearly should be normalized — Pass 3/13 say add validation — so I'll trim/lowercase/canonicalize it." | Validation that *detects and reports* a bad input is hardening. Validation that *changes the value* flowing downstream (trim, canonicalize, default a field, emit a new field) is a behavior change = a feature. File it and defer. |
| "This isn't a refactor — it's the only real fix for a systemic P1 Carmack surfaced, and P1 means fix-this-pass." | A finding whose only fix is new architecture is, by definition, a deferred finding — regardless of which pass found it. "Fix this pass" is satisfied by recording it `fixed:false` + `deferred_because`, not by refactoring. "Reduces future defect risk" is the spirit of the *whole skill*; if it licenses this, it licenses disabling scope discipline entirely. |

## Red Flags — STOP

If you catch yourself doing any of these, return to the current pass:

- Rewriting a function "for clarity" that has no defect
- Adding a new module, class, or abstraction
- Changing public API signatures or adding configuration options
- Refactoring test infrastructure
- Writing a test for a scenario that cannot happen given the current code
- Rabbit-holing on a single P2 — if the fix is not obvious after one focused read, note it (P2, with a one-line reason) and move on. One attempt, not five.
- Splitting or extracting from a function to fix *its* defect — a split is never the minimal fix; patch in place or defer (`fixed:false` + `deferred_because`).
- Re-grading a style/naming/formatting nit above P3 for a reviewer's sake or to save a round-trip — the floor never moves for authority or speed.
- Editing a public function's `def` line or parameter default to fix a bug (incl. `[]`→`None`) — the default is part of the signature; defer it. (Private functions: fix in place.)
- Changing a test's expected value to match what the code emits — the code can't prove its own test wrong; disprove it from an independent source or leave it red and file it.
- Adding normalization that changes the output value for an already-accepted input (trim/canonicalize/default/emit a field) — that's a feature; detect-and-report is fine, rewriting values is not.
- Building any new module, class, or abstraction to fix a finding — even one a deep pass surfaced, even with identical behavior. You've left hardening scope; defer it.

## Summary Report

After all passes, produce this exact format:

```
HARDENING SUMMARY
=================
Starting commit: <hash>
Final commit:    <hash>
Passes run:      <N executed of 14 — note any SKIPPED or quick-checked>
Lines changed:   +<added> / -<removed>

FINDINGS BY PASS
  Pass 1  (Correctness):          X findings (P0: _, P1: _, P2: _)
  Pass 2  (Security):             X findings (P0: _, P1: _, P2: _)
  Pass 3  (Error Handling):       X findings (P0: _, P1: _, P2: _)
  Pass 4  (Type Safety):          X findings (P0: _, P1: _, P2: _)
  Pass 5  (Concurrency):          X findings (P0: _, P1: _, P2: _) [or SKIPPED]
  Pass 6  (Performance):          X findings (P0: _, P1: _, P2: _)
  Pass 7  (Logging):              X findings (P0: _, P1: _, P2: _)
  Pass 8  (Test Coverage):        X tests written
  Pass 9  (Documentation):        X fixes
  Pass 10 (Backward Compat):      X findings (P0: _, P1: _, P2: _) [or SKIPPED]
  Pass 11 (Env/Config/Build):     X findings (P0: _, P1: _, P2: _)
  Pass 12 (Carmack Review):       X findings (P0: _, P1: _, P2: _)
  Pass 13 (Chaos Monkey):         X findings, Y chaos tests written
  Pass 14 (Maintainability):      X findings (P0: _, P1: _, P2: _)

MAINTAINABILITY SCORECARD
  Consistency:                    <A-F>
  Maintainability:                <A-F>
  Overall:                        <A-F>
  Hot spots:                      <module list or none>

FINDING INDEX
  F1.1 (P1) — <one-line summary> — fixed in <commit-hash>
  ...

TOTALS
  Findings fixed:     X
  New tests written:  X
  P0 findings:        X (any P0 → NOT_READY; even a fixed P0 needs release sign-off)
  P1 remaining:       X

CLEAN PASSES
  X of 14 passes found no issues
  [If prior hardening detected: "Prior hardening commits detected — clean passes are expected"]

DEFERRED FINDINGS (confirmed but not fixed this run)
  F12.6 (P1, deferred) — <one-line summary> — Deferred because: <reason>
  ...

REMAINING CONCERNS (require human judgment)
  - [description — why this needs a human decision]

TEST SUITE STATUS
  Full suite: PASS (X tests)
  New tests:  X added this session
```

Set the machine `verdict` (see Output Contract) consistently with this banner: any P0 (fixed or not) **or** any open P1 (`fixed: false`, no `deferred_because`) → `verdict: NOT_READY`, and the summary must say **RELEASE BLOCKED** with the specific items listed.
