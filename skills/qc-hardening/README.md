# Production Hardening (`qc-hardening`)

Requires **qc-core**. Installing or running this folder without `qc-core` is an incomplete port.

A multi-pass audit that drives residual **concrete failure scenarios** — especially
under realistic call sequences, dual/public paths, and live external/adapter
boundaries — to zero or explicit deferral, **without changing functional behavior**.
Run it after feature development is complete: before production, a release branch,
a merge, or a security review. Clean Carmack across all modules plus a green Chaos
suite is the expected terminal state.

> **This README is the human-facing overview — the *why* and the *shape*.** The
> canonical pass list, severity model, ledger contract, and execution rules live in
> **[`SKILL.md`](SKILL.md)** and **[`references/`](references/)**, which are the single
> source of truth; if anything here ever disagrees with them, SKILL.md wins.
> Deliberately, this file restates no pass count, filename, or rule that could drift —
> the documentation-accuracy pass audits exactly that kind of drift, and this skill
> should not fail its own audit.

## What makes it different

Most code review checks categories: "any security issues?" "any type errors?" This
skill does all of that in a sequence of **mechanical passes** that remove noise
(correctness-as-composition, security, error handling, types, concurrency,
performance, logging, coverage, docs, compat, env/config) — each committed
independently so any single fix is trivial to revert. Correctness treats
**sequence, dual-path parity, field population, and every ingest path** as the
main lens; isolated pure-function bugs are the easy residual.

Then it goes where checklists can't, with three passes that justify the whole skill:

**Carmack Review** reads every function and reasons from first principles, asking five
adversarial questions:

1. What invariant makes this correct?
2. What happens when my assumptions are wrong?
3. What sequence of valid operations produces an invalid state?
4. If this runs a million times, what breaks?
5. What would make this code wrong tomorrow?

**Chaos Monkey** *runs* the code with adversarial input and watches what actually
breaks — encoding, boundaries, type confusion, and production-shaped sequences
(wrong order of valid steps, partial success then failure, empty-then-large,
double-submit). The assertion bar stays no-crash / right exception / graceful
degradation. Every crash is Carmack-escalated and stays in `tests/test_chaos.py`
as living coverage.

**Maintainability & Consistency** converts the evidence into a **release judgment**
(release-ready / releasable-with-debt / not-yet). Letter grades are supporting
evidence: every sub-A grade names a concrete change that would force whole-system
context.

> These deep passes found real bugs in a well-tested 4.6K-LOC Python library that had
> already cleared every mechanical pass — see the table below. The mechanical passes
> made the code *clean*; Carmack and Chaos made it *correct*.

## How it learns

The skill gets sharper across runs through two persisted artifacts (mechanics in
[`references/pass-debt.md`](references/pass-debt.md)):

- **Profile** (`.qc-profile.json`, committed to the repo; `.qc-profile.md` is generated) — run history,
  maintainability trend, per-pass *clean streaks* (a pass clean for 3+ runs with no new
  code in scope can downgrade to a tool-only quick-check), repeat-offender **hot spots**,
  **pass debt** (missed *combination* a mechanical pass should have caught), Carmack
  examination records (five questions, not a one-liner), harvested **invariants**,
  and the **reexam set** on later runs (changed files plus hot-spot/pass-debt neighbors).
- **Findings ledger** (`.qc-findings/qc-hardening.json`) — the run's structured findings,
  written for the deep passes to consume for first/second/third-order analysis ("this
  boundary bug in CSV reading — does it exist in Excel and Parquet reading too?") and
  shared, through one schema, with the broader `qc-all` suite's rollup.

## Scaling

- **Inline mode** (default, smaller codebases): run every pass directly.
- **Chunked mode** (large codebases or context pressure): partition into module groups
  and fan out the deep-read + adversarial-verify half as a dynamic workflow
  ([qc-core `workflows/discovery-verify.js`](../qc-core/workflows/discovery-verify.js)) — one rubric across
  all groups, schema-enforced findings, a 2-vote refutation of every finding, automatic
  cross-module dedup. Remediation (fix → regression test → narrow gate → isolated commit)
  always stays model-driven; the workflow reads and verifies but never edits or commits.

## Usage

```
# In Claude Code, just say:
harden
run production hardening
run pass 12 only
run chaos monkey
```

The skill reads project conventions (`CLAUDE.md` / `AGENTS.md`, tooling config),
establishes a passing-test baseline, runs the passes in order, commits fixes
independently, updates the profile, and ends with a fixed-format summary and an
explicit release verdict.

## Results from real use

On AddressNormalization Light (4.6K-LOC Python, 16 modules, 600+ tests):

| Source            | Found                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| Mechanical passes | Type errors, missing `.gitignore`, lint, unused imports — routine cleanup                            |
| Carmack (4 runs)  | Excel float ZIP codes, NaN crash, dead confidence signal, dead comparator code — bugs no tool caught |
| Chaos (1 run)     | `.strip()` on `None`/`int` crashing both batch orchestrators — 3 crashes from 61 adversarial tests   |
