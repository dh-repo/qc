---
name: qc-coherence
description: Use when multiple feature sessions have landed without a full-codebase review, before a release, when a new subsystem was added, or when cross-cutting drift, naming inconsistency, duplication, stubs, or dangling references are suspected but per-function checks come back clean. Triggers include "coherence audit", "coherence check", "cross-cutting audit", "codebase coherence". Supports --scope=module for module-level composition checks (formerly qc-structural).
---

# QC-Coherence — Codebase Coherence Audit

Unbounded codebase-wide verification. No mission scope. Finds cross-cutting drift, inconsistency, duplication, stubs, dangling references, and architectural violations that accumulate between scoped missions.

**Core insight:** The hardening skill guarantees quality within individual functions. This skill guarantees coherence *across the entire codebase* — two clean missions can still leave the codebase inconsistent with each other. Use `--scope=module` to also audit whether modules and protocols compose correctly.

## Relationship to Other QC Skills

| Skill | Scope | Question |
|-------|-------|----------|
| **qc-hardening** | Per-function | Does each function work correctly? |
| **qc-coherence --scope=module** | Per-module | Do modules compose correctly? |
| **qc-coherence** | Full codebase | Is the codebase internally consistent? |
| **qc-all** | All of the above | Is the codebase release-ready? |

qc-coherence runs less frequently than hardening — typically before releases or after major feature cycles. Its findings feed into the autonomous supervisor for remediation.

## When to Use

- Before a release (comprehensive quality gate)
- After 5+ sessions of feature work without a full audit
- When something feels inconsistent but hardening and `--scope=module` come back clean
- When a new subsystem was added (e.g., recovery module, coherence subsystem)
- When called by qc-all as part of the release readiness flow

**Do not use when:** active feature work is in progress, or when a targeted qc-hardening audit is more appropriate.

## The Four Sub-Audits

Run in dependency order — each builds on the prior's output:

```
1. Structural Audit   → deterministic, fast, no LLM needed
2. Conformance Audit  → protocol/implementation matrix
3. Semantic Audit     → LLM-assisted naming, error taxonomy, serialization
4. Architectural Audit → dependency direction, layer boundaries, invariants
```

See `references/` for detailed check definitions:
- [references/structural-audit.md](references/structural-audit.md) — S1-S5 checks
- [references/conformance-audit.md](references/conformance-audit.md) — C1 checks
- [references/semantic-audit.md](references/semantic-audit.md) — M1-M5 checks
- [references/architectural-audit.md](references/architectural-audit.md) — A1-A5 checks

## Pre-Flight

1. Read project conventions (`CLAUDE.md`, `pyproject.toml`)
2. Load prior audit state (`.structural-integrity.md`, `.hardening-profile.md`)
3. Build module inventory with LOC
4. Check recent git history since last coherence audit
5. Determine scope from invocation flag: `--scope=module` runs the six module-level checks (MS-1–MS-6); default (`--scope=codebase`) runs the four codebase-wide sub-audits
6. Determine focus paths (full codebase or caller-specified paths)

## Execution

### Sub-Audit 1: Structural (Deterministic)

Fast, no LLM required. Produces the clean symbol table and import graph that later sub-audits consume.

| Check | What it finds |
|-------|--------------|
| **S1 — Stub Detection** | `TODO`, `FIXME`, `raise NotImplementedError`, `pass`-only methods |
| **S2 — Dead Code** | Orphan exports, orphan definitions, broken imports, shadowed imports |
| **S3 — Duplication** | Semantically equivalent code blocks in multiple locations |
| **S4 — Type Coverage** | Missing type annotations, `Any` usage, unexplained `type: ignore` |
| **S5 — Unused Dependencies** | Packages in manifest but never imported |

**Tools:** `ruff`, `mypy --strict`, `vulture` (if available), AST-based import graph

### Sub-Audit 2: Conformance

Protocol/implementation matrix — generalizes the conformance suite pattern.

| Check | What it finds |
|-------|--------------|
| **C1 — Conformance Matrix** | Missing methods, stub implementations, signature mismatches across all Protocol/ABC pairs |

For every interface with 2+ implementations: verify parameterized conformance tests exist and cover all implementations. Generate drift guards for interfaces without them.

### Sub-Audit 3: Semantic (LLM-Assisted)

Detects inconsistencies that static tools miss.

| Check | What it finds |
|-------|--------------|
| **M1 — Naming Consistency** | Same concept with different names across modules (`run_id` vs `execution_id`) |
| **M2 — Error Handling Taxonomy** | Equivalent conditions raising different exception types |
| **M3 — Serialization Round-Trip** | `deserialize(serialize(x)) != x` — missing round-trip tests, key mismatches |
| **M4 — Behavioral Contract Consistency** | Same interface method behaving differently across implementations |
| **M5 — Magic Values** | Hardcoded literals carrying domain meaning, not centralized as constants |

**Dispatch strategy:** For codebases >5K LOC, run the LLM-assisted sub-audits (2-4) via the dynamic workflow — see "Discovery + Verify via dynamic workflow" below; it fans out per lens and adversarially verifies each finding (real vs intentional). Manual per-module-group subagent dispatch (the qc-hardening Carmack chunking heuristic) is the fallback when the Workflow tool is unavailable.

### Sub-Audit 4: Architectural

Enforces architectural invariants — turns design decisions into executable tests.

| Check | What it finds |
|-------|--------------|
| **A1 — Dependency Direction** | Lower layers importing from higher layers, circular dependencies |
| **A2 — Layer Boundary** | Direct access to internal implementation details across layer boundaries |
| **A3 — Module Responsibility** | Modules with 2+ distinct responsibility domains (God classes, grab-bag utilities) |
| **A4 — Documented Invariants** | Constraints documented in comments/docs but not enforced by tests |
| **A5 — Cross-Cutting Concern Consistency** | Logging, auth, retry, transactions used inconsistently across modules |

## Discovery + Verify via dynamic workflow (preferred for codebase scope)

Run the three **LLM-assisted** sub-audits — Conformance (C1), Semantic (M1-M5), Architectural
(A1-A5) — as a single **dynamic workflow** instead of sequential manual analysis. The workflow ships
with this skill at `workflows/coherence-discovery-verify.js`: it fans out one agent per lens across
the scope (or per lens × module-group when `moduleGroups` is supplied — required above ~50K LOC so
no lens agent skims), **adversarially verifies every finding as real-incoherence vs intentional**,
dedups across lenses, and returns a ranked, supervisor-compatible ledger.

Sub-Audit 1 (Structural) stays **deterministic and inline** — it is tool-driven (ruff / mypy /
vulture / AST) and produces the symbol table + import graph + duplication/stub candidates the
workflow consumes as context (and re-verifies: a tool-flagged stub or duplicate is frequently a
deliberate seam).

**Structural-candidate tiering:** only route AMBIGUOUS structural hits through the workflow's
adversarial verify — stubs (S1), duplication (S3), orphan exports/definitions (S2) — because those
are the ones that can be deliberate seams. Mechanically-certain hits (broken imports, mypy errors,
unused dependencies) need no adversarial verification: record them as findings directly and fix
them inline. Verifying a broken import wastes two agents proving the obvious.

**Why a workflow here:** one rubric per lens, schema-enforced findings, **and the verification step
coherence needs most** — coherence audits over-report (deliberate seams, per-layer patterns,
different-but-correct naming, "drift" that is actually correct), so every finding gets two
**perspective-diverse** verdicts: an intentionality hunter (finds the seam doc / comment / layer
rationale that makes the divergence deliberate) and a mechanics validator (confirms every cited
location exists and says what's claimed, and that severity is right). Tie-handling is strict: a
finding is only `fix` when BOTH verdicts say real; a split or any `uncertain` verdict → `defer`,
never silently dropped. That is what keeps the ledger trustworthy. Plus auto-dedup across lenses,
resumability (`resumeFromRunId`), and live progress (`/workflows`). Invoking this skill is the opt-in.

**What STAYS model-driven — do NOT put in the workflow:** the deterministic structural sub-audit
(tools), and **all remediation** — converging a name/duplication to its canonical site, updating
drifted docstrings/READMEs/catalogs, adding the missing conformance-matrix or round-trip test, and
the isolated commits. The workflow reads and verifies; it never edits or commits. Convergence is a
judgment call (which site is canonical, whether to split a module) the fan-out cannot make.

How to run it (after the inline Structural pre-pass and Pre-Flight):

```
Workflow({
  scriptPath: "<this skill's base dir>/workflows/coherence-discovery-verify.js",
  args: {
    repoPath: "<absolute repo root>",
    scope: "<changed-surface paths, or 'whole codebase' + the module inventory>",
    conventions: "<key CLAUDE.md / AGENTS.md rules — the conformance baseline>",
    structuralContext: "<symbol table / import graph summary from Sub-Audit 1>",
    structuralCandidates: [ { check, title, locations, what, severity }, ... ],  // AMBIGUOUS S1/S2/S3 hits only — see tiering note
    moduleGroups: [ "<path group 1>", "<path group 2>", ... ],  // optional; >50K LOC scope → lenses fan out per group
    moduleInventory: "<module list with LOC from Pre-Flight>",  // synthesis cross-checks lens coverage against this
    priorState: "<.structural-integrity.md + prior coherence ledger>",
    offLimits: [ "<uncommitted / in-flight files you must NOT modify>" ]
  }
})
```

It returns `{ ranked_findings, coverage }`. Each finding carries a `recommendation`: **fix** (both
verdicts say real, convergence safe/local), **defer** (real but needs a canonical-site / module-split
design call), or **drop** (verified intentional or overstated — keep its `intentional_evidence`).
Then, INLINE: apply each **fix** (converge to the canonical site / update the drifted docs / add the
guard test), commit isolated (stage only files you changed); record **defer** in the ledger; discard
**drop**. Use `coverage` to confirm every lens returned a CLEAN list. The `remediation_hint` on each
finding is supervisor-ready.

**Gating:** workflow for codebase scope (default), highest yield >5K LOC or after several changes
landed. Structural sub-audit is always inline. `--scope=module` (MS-1–MS-6) and small scopes can run
inline. If the Workflow tool is unavailable, fall back to Sub-Audit 3's per-module-group subagent dispatch.

## Module Scope Sub-Audits (--scope=module)

When invoked with `--scope=module`, qc-coherence runs six module-level composition checks instead of (or in addition to) the four codebase-wide sub-audits. These checks were formerly the `qc-structural` skill.

The six checks audit whether modules and protocol implementations compose correctly:

| Check | What it finds |
|-------|--------------|
| **MS-1 — Protocol Conformance Parity** | Missing conformance tests across backend implementations |
| **MS-2 — Responsibility Density** | Modules accumulating too many distinct responsibilities |
| **MS-3 — Coordination Surface** | Lock/event/gate interaction complexity exceeding safe thresholds |
| **MS-4 — Backend Parity** | Feature gaps between alternative backend implementations |
| **MS-5 — Cross-Session Consistency** | Reintroduced patterns that prior hardening fixed |
| **MS-6 — Test Architecture** | Oversized test files, fixture duplication, missing test modules |

Full check definitions, thresholds, finding formats, and fix guidance: [`references/module-scope-checks.md`](references/module-scope-checks.md)

Migration from qc-structural: [`references/structural-checks-migration.md`](references/structural-checks-migration.md)

Module-scope findings appear in the main FINDINGS list and affect the overall verdict using the same P0–P3 scale.

## Severity Definitions

| Severity | Definition |
|----------|-----------|
| **P0** | Actively broken: runtime failure, data corruption, security hole |
| **P1** | Will break under realistic conditions: missing error handling, unimplemented protocol method |
| **P2** | Increases maintenance cost: naming drift, duplication, undocumented invariant |
| **P3** | Suboptimal but functional: style inconsistency, minor dead code |

## Output Format

```
COHERENCE REPORT
================
Date:            YYYY-MM-DD
Scope:           [codebase | module | focused paths]
Modules audited: N

SUB-AUDIT RESULTS
  Structural:     N findings (P0: _, P1: _, P2: _, P3: _)
  Conformance:    N findings (P0: _, P1: _, P2: _, P3: _)
  Semantic:       N findings (P0: _, P1: _, P2: _, P3: _)
  Architectural:  N findings (P0: _, P1: _, P2: _, P3: _)

SUMMARY
  P0: N
  P1: N
  P2: N
  P3: N
  CLEAN: N modules with zero findings

FINDINGS
  [ID] [P0|P1|P2|P3] [sub-audit] — [one-line summary]
  ...

OVERALL VERDICT
  [COHERENT | DRIFTING | ACTION REQUIRED]
```

### Verdicts

- **COHERENT:** 0 P0, 0 P1. The codebase is internally consistent.
- **DRIFTING:** 0 P0, 1+ P1 or 3+ P2. Working today but accumulating risk.
- **ACTION REQUIRED:** 1+ P0 or 3+ P1. Fix before continuing development.

## Deduplication

When multiple sub-audits flag the same location:
- Keep the highest-severity finding
- Merge evidence from all sub-audits
- Reference all source sub-audits in the finding

When a finding overlaps with an existing `.structural-integrity.md` accepted debt entry: note the overlap, do not re-flag unless new evidence changes the severity.

## Remediation: Dispatching the Autonomous Supervisor

| Verdict | Action |
|---------|--------|
| **COHERENT** | No dispatch. Log and move on. |
| **DRIFTING** | Dispatch with P1 + P2 findings. |
| **ACTION REQUIRED** | Dispatch with ALL findings. Block further feature work. |

Dispatch the autonomous supervisor (`.github/agents/autonomous-supervisor.agent.md`) with the findings section and recommended priority order.

Dispatch payload format: see [`references/supervisor-dispatch.md`](references/supervisor-dispatch.md).

## Output Contract

After each audit, write findings to `.qc-findings/qc-coherence.json` in the project root. The file must conform to schema [`references/qc-finding.schema.json`](references/qc-finding.schema.json).

When findings come from the workflow ledger, translate fields explicitly — the ledger and the
contract use different names:

| Workflow ledger field | qc-finding.json field |
|:---|:---|
| `check` (+ sequence) | `id` (e.g. `M1.2`) |
| `locations[0]` | `file`, `line` (remaining locations go in `what`) |
| `title` | `what` (prefix; append the location list) |
| `why_incoherent` | `why` |
| `remediation_hint` (fallback `proposed_fix`) | `fix` |
| `recommendation: "fix"` + applied | `fixed: true` |
| `recommendation: "defer"` | `fixed: false` + `deferred_because` |
| `recommendation: "drop"` | omit from the file entirely |

**Example finding:**

```json
{
  "schema_version": "1.0",
  "skill": "qc-coherence",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "C1.1",
      "scope": "codebase",
      "severity": "P1",
      "file": "app/stores/fabric_sql.py",
      "line": 88,
      "what": "FabricSQLStore missing `delete_by_id` method present on Protocol and on SQLiteShipmentStore",
      "why": "Protocol/implementation drift; production deploys on Fabric backend would fail at runtime",
      "fix": "Implement `delete_by_id` on FabricSQLStore using the existing batch-delete pattern",
      "fixed": false,
      "deferred_because": "Requires schema migration coordinated with ops"
    }
  ],
  "verdict": "NOT_READY"
}
```

**Verdict mapping:**

| Prose verdict | JSON rollup verdict | Condition |
|:---|:---|:---|
| COHERENT | `READY` | Zero findings |
| DRIFTING | `READY_WITH_DEBT` | Only P2/P3 findings, all fixed or `deferred_because` set |
| ACTION REQUIRED | `NOT_READY` | Any P0/P1 with `fixed: false` and no `deferred_because` |

## Persistence

Write or update `.qc-coherence-report.md` in the project root after each audit. This is overwritten on each run — it represents current state, not history.

**Diff mode:** before overwriting, copy the previous `.qc-findings/qc-coherence.json` to
`.qc-coherence-baseline.json` and pass its contents as part of `priorState` — lenses suppress
already-recorded findings unless they regressed, so the new report reads as a delta against the
baseline. Use diff mode when a full audit ran recently and you only need "what drifted since."
