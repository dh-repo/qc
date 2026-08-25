# Production Hardening (`qc-hardening`)

A multi-pass code audit that finds and fixes defects **without changing functional
behavior**. Run it after feature development is complete — before production
deployment, a release branch, a merge, or a security review.

> **This README is the human-facing overview — the *why* and the *shape*.** The
> canonical pass list, severity model, ledger contract, and execution rules live in
> **[`SKILL.md`](SKILL.md)** and **[`references/`](references/)**, which are the single
> source of truth; if anything here ever disagrees with them, SKILL.md wins.
> Deliberately, this file restates no pass count, filename, or rule that could drift —
> the documentation-accuracy pass audits exactly that kind of drift, and this skill
> should not fail its own audit.

## What makes it different

Most code review checks categories: "any security issues?" "any type errors?" This
skill does all of that in a sequence of **mechanical passes** — correctness, security,
error handling, type safety, concurrency, performance, logging, test coverage,
documentation, backward-compatibility, and env/config/build — each committed
independently so any single fix is trivial to revert.

Then it goes where checklists can't, with three passes that justify the whole skill:

**Carmack Review** reads every function and reasons from first principles, asking five
adversarial questions:

1. What invariant makes this correct?
2. What happens when my assumptions are wrong?
3. What sequence of valid operations produces an invalid state?
4. If this runs a million times, what breaks?
5. What would make this code wrong tomorrow?

**Chaos Monkey** *runs* the code with adversarial input and watches what actually
breaks — across encoding, boundary values, type confusion, structural garbage,
timing/ordering, and real-world malformed data. Every crash is escalated: before
fixing, grep for the same pattern elsewhere and fix all instances together.

**Maintainability & Consistency** is the closing synthesis. It turns the evidence
from every prior pass into A–F grades and an explicit release judgment, grounded in
proven hot spots rather than taste.

> These deep passes found real bugs in a well-tested 4.6K-LOC Python library that had
> already cleared every mechanical pass — see the table below. The mechanical passes
> made the code *clean*; Carmack and Chaos made it *correct*.

## How it learns

The skill gets sharper across runs through two persisted artifacts (mechanics in
[`references/pass-debt.md`](references/pass-debt.md)):

- **Hardening Profile** (`.hardening-profile.md`, committed to the repo) — run history,
  maintainability trend, per-pass *clean streaks* (a pass clean for 3+ runs with no new
  code in scope can downgrade to a tool-only quick-check), repeat-offender **hot spots**,
  **pass debt** (when a deep pass catches what a mechanical pass should have), and the
  Carmack audit manifest of which modules have actually been deeply read.
- **Findings ledger** (`.qc-findings/qc-hardening.json`) — the run's structured findings,
  written for the deep passes to consume for first/second/third-order analysis ("this
  boundary bug in CSV reading — does it exist in Excel and Parquet reading too?") and
  shared, through one schema, with the broader `qc-all` suite's rollup.

## Scaling

- **Inline mode** (default, smaller codebases): run every pass directly.
- **Chunked mode** (large codebases or context pressure): partition into module groups
  and fan out the deep-read + adversarial-verify half as a dynamic workflow
  ([`workflows/discovery-verify.js`](workflows/discovery-verify.js)) — one rubric across
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
