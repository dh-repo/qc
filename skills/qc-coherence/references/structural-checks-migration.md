# Structural Checks Migration Table

Maps the six checks from the former `qc-structural` skill to their equivalents in `qc-coherence --scope=module`.

Invoke with: `/qc-coherence --scope=module` (replaces `/qc-structural`)

| Old (qc-structural) | New (qc-coherence --scope=module) | Finding ID change | Notes |
|:---|:---|:---|:---|
| Check 1 — Protocol Conformance Parity | Module-Scope Check MS-1 — Protocol Conformance Parity | SI-1.N → MS-1.N | Verbatim; FAIL→P0, CONCERN→P1 |
| Check 2 — Responsibility Density | Module-Scope Check MS-2 — Responsibility Density | SI-2.N → MS-2.N | Verbatim; FAIL→P0, CONCERN→P1 |
| Check 3 — Coordination Surface | Module-Scope Check MS-3 — Coordination Surface | SI-3.N → MS-3.N | Verbatim; FAIL→P0, CONCERN→P1 |
| Check 4 — Backend Parity | Module-Scope Check MS-4 — Backend Parity | SI-4.N → MS-4.N | Verbatim; FAIL→P0, CONCERN→P1 |
| Check 5 — Cross-Session Consistency | Module-Scope Check MS-5 — Cross-Session Consistency | SI-5.N → MS-5.N | Verbatim; FAIL→P0, CONCERN→P1 |
| Check 6 — Test Architecture | Module-Scope Check MS-6 — Test Architecture | SI-6.N → MS-6.N | Verbatim; FAIL→P0, CONCERN→P1 |

## Severity Mapping

| qc-structural verdict | qc-coherence severity |
|:---|:---|
| FAIL | P0 |
| CONCERN | P1 |
| PASS | P3 (no finding emitted) |

## Verdict Mapping

| qc-structural verdict | qc-coherence verdict |
|:---|:---|
| COHERENT | COHERENT |
| DRIFTING | DRIFTING |
| ACTION REQUIRED | ACTION REQUIRED |

## Persistence File Migration

| qc-structural artifact | qc-coherence artifact |
|:---|:---|
| `.structural-integrity.md` | Migrated into `.qc-profile.json` `deferred[]` (qc-core). Read the markdown only if the JSON does not exist yet. |
| Output report (inline) | Folded into `.qc-coherence-report.md` under MODULE SCOPE section |
