# Unified profile

**Source of truth:** `.qc-profile.json` at the target repo root, schema [`qc-profile.schema.json`](qc-profile.schema.json). Every qc-* skill reads and writes it. Human summary `.qc-profile.md` is generated (`scripts/render_profile.py`) and must not be edited by hand.

Legacy `.hardening-profile.md` and `.structural-integrity.md` are inputs on the first run after upgrade: copy hot spots, pass debt, accepted-debt, and Carmack status into the JSON, then stop treating the markdown as authoritative.

## Contents

| Section | Role |
|---------|------|
| `examination` | Per skill, per module/symbol: `EXAMINED` / `FINDING` / `NOT_YET`, plus invariant or Carmack 5Q |
| `pass_streaks` | Consecutive clean runs; drives hardening quick-check eligibility |
| `hot_spots` | Repeat-offender artifacts |
| `pass_debt` | Deep-pass hits a mechanical pass should have caught |
| `deferred` | Closed-vocabulary deferred findings, visible to every later skill |
| `run_history` | Per-skill run records |
| `maintainability_trend` | Pass 14 grades over time |
| `operating_facts` | User-provided docs facts with timestamps (`source: user-provided`) |
| `clusters` | Machine-checkable clustering/responsibility judgments (symbols + rationale) |
| `canonical_forms` | Semantic ground truth: concept → canonical name + aliases. Later runs only re-flag regressions |
| `layer_model` | Architectural ground truth: layers + permitted import direction. Later A1 diffs the import graph against it |
| `invariants` | Living registry harvested from Carmack, must/never comments, and tests. Coherence enforces it |
| `truth_map` | Docs claims → evidence pointer (`file:line`, test name, or `user-provided:<id>`) |

Write atomically (same temp+rename protocol as the ledger). Update incrementally so an interrupted run preserves state. Commit the JSON; it is project metadata.

## Examination claims are auditable

`EXAMINED` without a named artifact is not examined. For **qc-hardening**, profile `examination.qc-hardening` **is** the Carmack manifest (Pass 1 CLEAN lists stay on the ledger `examined[]` only). A hardening `EXAMINED` row requires either the five Carmack questions or `{invariant, assumptions, sequence_risk}` — all substantive. A lone one-sentence invariant is incomplete. Other skills still use a one-sentence invariant. `verify_profile.py` rejects boilerplate.

## Clustering / responsibility judgments

Any check that partitions symbols or responsibilities (coherence M1, A3, MS-2, and similar) writes a `clusters[]` row: list of symbols + short rationale. Thresholds produce a measurable first half (`module LOC=912, public symbols=14, tables=5`); the second half (whether those are "unrelated") goes in `rationale`. Later verification or a human can audit the clustering itself.

## Invariant registry

Harvested, never invented. Writers: Carmack findings (`statement` = `violated_invariant`, `source: carmack`), A4 must/never comments (`source: comment`), existing tests (`source: test`). Status is `enforced` (has `enforced_by`), `untested`, or `deferred`. Coherence **enforces** the registry: an `untested` testable row is a finding; a regression of an `enforced` row is a finding. Do not mint a second id for the same statement.

## Canonical forms and layer model

Semantic M1/M2/M5 clusters that are accepted write `canonical_forms[]`. Later Semantic runs load it and only re-flag new aliases or a canonical regression.

Architectural A1 writes `layer_model` once (layers + permitted directions). Later A1 diffs the import graph against it.

## Docs truth-map

During the docs audit step, every non-trivial ARCHITECTURE / OPERATIONS / API / DATA_MODEL claim gets a `truth_map[]` row. Accuracy-gate evidence is this list, not vibes. User-provided facts live in `operating_facts` with `last_verified` and are referenced by `fact_id`. Never present them as code-derived.

Docs **Known limitations** (HANDOFF, TROUBLESHOOTING, README scope note) are synthesized from `deferred[]` + `hot_spots[]` + `pass_debt[]` + untested `invariants[]`. Do not keep a fourth list.

## Quick-check eligibility (hardening)

A pass with 3+ consecutive clean runs and no new code in its scope may downgrade to tool-only. Eligible: passes 4, 5, 6, 7, 10, 11. Never: 1, 2, 3, 8, 9, 12, 13, 14.
