---
name: qc-coherence
description: Use when multiple feature sessions have landed without a full-codebase review, before a release, when a new subsystem was added, or when cross-cutting drift, naming inconsistency, duplication, stubs, or dangling references are suspected but per-function checks come back clean. Triggers include "coherence audit", "coherence check", "cross-cutting audit", "codebase coherence". Supports --scope=module for module-level composition checks (formerly qc-structural).
---

# QC-Coherence — Codebase Coherence Audit

**REQUIRED:** Load `qc-core` first. Laws, ledger, verdict, profile, Discovery+Verify, deferred vocabulary, CLEAN lists, and clustering artifacts live there.

Guarantee **compositional consistency**: every public contract has complete and behaviorally aligned implementations; domain concepts, errors, and data shapes use single canonical forms; architectural boundaries and cross-cutting operational concerns are uniform; previously discovered invariants remain enforced. Produces maps and an invariant registry, not one-shot opinions.

C1, MS-4, and A1 exist to catch divergence between **static contracts (system as imagined)** and **observed composition (system as found)**. Hardening owns the runtime proof of sequences and live paths. This skill owns static contracts and canonical forms. The durable artifacts (`invariants[]`, `canonical_forms[]`, `layer_model`, `clusters[]`) are the bridge. `--scope=module` audits whether modules and protocols compose.

A run is incomplete if findings were handled but `canonical_forms[]` / `layer_model` / `invariants[]` were not updated. Empty findings plus updated artifacts is a valid win.

## When to Use

- Before a release; after 5+ sessions of feature work without a full audit
- When something feels inconsistent but hardening comes back clean
- When a new subsystem was added
- When called by qc-all (after hardening, before docs)

**Do not use when:** active feature work is in progress, or a targeted hardening pass is more appropriate.

## The Four Sub-Audits

Dependency order — each builds on the prior:

```
1. Structural     → deterministic (S1–S5). Import graph feeds partitioning.
2. Conformance    → protocol/implementation matrix (C1)
3. Semantic       → naming, error taxonomy, serialization (M1–M5)
4. Architectural  → dependency direction, layers, invariants (A1–A5)
```

References: [structural-audit.md](references/structural-audit.md), [conformance-audit.md](references/conformance-audit.md), [semantic-audit.md](references/semantic-audit.md), [architectural-audit.md](references/architectural-audit.md).

Judgment-heavy checks (M1, A3, MS-2) MUST write `clusters[]` **and** the corresponding durable map: Semantic → `canonical_forms[]`; Architectural A1 → `layer_model`; A4/Carmack harvest → `invariants[]`. Later runs load these as ground truth and only re-flag regressions. Semantic/Architectural findings use the scenario shape: under input sequence X, backend A returns Y while B returns Z / a different exception.

## Pre-Flight

1. Read project conventions.
2. Load `.qc-profile.json` and **the hardening ledger** (`.qc-findings/qc-hardening.json`). Deferred hardening findings are priorState by default; link `related_findings` instead of minting a parallel id.
3. Build module inventory with LOC. Partition via `../qc-core/scripts/partition.py` (import-graph primary).
4. Git history since last coherence run. Diff-mode: previous `.qc-findings/qc-coherence.json` as baseline. If a new implementation or module was added, `partition.py --reexam` neighbors that are existing backends or hot spots get C1/MS-4 behavioral parity even if they did not change.
5. `--scope=module` → MS-1–MS-6; default `--scope=codebase` → the four sub-audits. Re-validate `invariants[]` against current code.

## Execution

**Sub-Audit 1: Structural** — inline, tool-driven (ruff / mypy / vulture / AST). Produces the symbol table + import graph. Mechanically-certain hits (broken imports, mypy errors, unused deps): `confidence: mechanical`, no dual-verify, record and fix. Ambiguous hits (stubs S1, orphans S2, duplication S3): `confidence: pattern`, route through Verify.

**Sub-Audits 2–4 (LLM-assisted)** — shared workflow:

```
Workflow({
  scriptPath: "<qc-core>/workflows/discovery-verify.js",
  args: {
    kind: "lenses",
    repoPath: "<abs>",
    scope: "<paths or whole codebase>",
    conventions: "<CLAUDE.md rules>",
    structuralContext: "<symbol table / import graph>",
    structuralCandidates: [ /* ambiguous S1/S2/S3 only */ ],
    moduleGroups: [ /* from partition.py; required ≳50K LOC */ ],
    moduleInventory: "<from Pre-Flight>",
    priorState: "<profile + hardening ledger + prior coherence ledger>",
    offLimits: [ ... ]
  }
})
```

Both votes must say real → fix; otherwise defer. CLEAN lists are named `{artifact, invariant}`. Unexamined inventory modules mean an incomplete audit, not a coherent one. If the Workflow tool is unavailable, fall back to per-module-group subagent dispatch with the same dual-vote rule.

Inline after the workflow: apply `fix`, isolated commits (`coherence: <sub-audit> — <ids>`); record `defer` with a closed-vocabulary code; discard `drop`.

## Module Scope (`--scope=module`)

Six composition checks (formerly `qc-structural`): MS-1–MS-6. Definitions: [references/module-scope-checks.md](references/module-scope-checks.md). Migration: [references/structural-checks-migration.md](references/structural-checks-migration.md). Accepted debt lives in the profile `deferred[]`, not `.structural-integrity.md`.

When 2+ backends exist, run **MS-4 immediately after MS-1**. If `pass_debt[]` / `hot_spots[]` already name adapter modules, MS-4 is not skippable. Ids stay MS-1…MS-6; only priority changes.

## Dedup

Same location from multiple sub-audits: keep highest severity, merge evidence, list source checks. Overlap with a profile deferred item: note it, set `related_findings`, do not re-flag unless new evidence raises severity.

## Remediation

| Suite verdict | Action |
|---------------|--------|
| `READY` | No dispatch |
| `READY_WITH_DEBT` | Dispatch P1 + P2 |
| `NOT_READY` | Dispatch all; block feature work |

Payload: [`../qc-all/references/supervisor-dispatch.md`](../qc-all/references/supervisor-dispatch.md).

## Output

qc-core ledger at `.qc-findings/qc-coherence.json`. Workflow → contract field map: `check`+sequence → `id`; `locations[0]` → `file`/`line`; `title` → `what`; `why_incoherent` → `why`; `remediation_hint` → `fix`; `fix`/`defer`/`drop` → `fixed` + `deferred_because` / omit.

Prose COHERENT / DRIFTING / ACTION REQUIRED maps onto suite `READY` / `READY_WITH_DEBT` / `NOT_READY` via qc-core (open P0/P1 policy for this skill; suite human-gate still blocks on any P0).

```json
{
  "schema_version": "1.1",
  "skill": "qc-coherence",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "C1.1",
      "scope": "codebase",
      "severity": "P1",
      "confidence": "pattern",
      "file": "app/stores/fabric_sql.py",
      "line": 88,
      "what": "FabricSQLStore missing `delete_by_id` present on Protocol and SQLiteShipmentStore",
      "why": "Protocol/implementation drift; Fabric deploys fail at runtime",
      "scenario": {
        "trigger": "Production is configured on the Fabric backend and a caller invokes delete_by_id",
        "violated_invariant": "Every Protocol method exists on every implementation",
        "observable": "AttributeError at runtime in production only"
      },
      "fix": "Implement `delete_by_id` on FabricSQLStore using the existing batch-delete pattern",
      "fixed": false,
      "deferred_because": "needs-migration: schema change coordinated with ops",
      "related_findings": []
    }
  ],
  "examined": [
    {
      "artifact": "app/clean.py::ping",
      "invariant": "ping() returns the literal string ok with no I/O or hidden state"
    }
  ],
  "verdict": "READY_WITH_DEBT"
}
```

Write `.qc-coherence-report.md` as the human snapshot (overwrite each run). Persist examination, clusters, and deferred items on `.qc-profile.json`.
