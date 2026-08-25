---
name: qc-core
description: Use when running any qc-* quality-control skill (qc-hardening, qc-coherence, qc-docs, qc-packaging, qc-all), or when porting the suite. Load before the specialization. Shared ledger, verdict, profile, Discovery+Verify, and the seven laws live here.
---

# QC Core

Shared machinery for the QC suite. Specializations own ordered passes and what counts as a finding. This skill owns every invariant they would otherwise copy.

| Specialization | Outcome it drives |
|----------------|-------------------|
| `qc-hardening` | Residual concrete failure scenarios under sequences, dual paths, and live adapters → zero or explicit deferral |
| `qc-coherence` | Compositional consistency + enforcement of the invariant registry |
| `qc-docs` | A new operator can run, diagnose, recover, and hand off the system that exists |
| `qc-packaging` | Distribution wrap with zero functional change |

A standalone port is **this tree plus one specialization**. A suite port is this tree plus the specializations plus `qc-all`. Installing a specialization without `qc-core` is an incomplete port.

## The Seven Laws

Do not weaken these. Full text: [references/laws.md](references/laws.md).

1. Harden what exists. No features, no architecture, no behavior change. Do not expand the audit surface.
2. Concrete failure scenario or it is not a finding. Deep / P1+ findings carry `trigger`, `violated_invariant`, `observable`.
3. Fix in place or defer (`fixed: false` + closed-vocabulary `deferred_because`).
4. P0 blocks even if fixed (suite-level human-review gate).
5. Isolated commits. Batch clean units, never skip execution.
6. Mechanical before deep. Do not collapse the 14 hardening passes or reverse the order.
7. Dual-vote to fix. Both votes say real → fix; otherwise defer. Never silently drop.

North star: three clean passes is the expected output of clean code, not a reason to manufacture findings. Why the deep passes exist: [laws.md](references/laws.md).

## Load this first

On every qc-* run:

1. Apply the laws and the [anti-rationalization table](references/anti-rationalization.md).
2. Read/write `.qc-profile.json` ([profile.md](references/profile.md)).
3. Write `.qc-findings/<skill>.json` atomically ([ledger.md](references/ledger.md)).
4. Compute verdict only via `scripts/qc.py` ([verdict.md](references/verdict.md)).
5. LLM-assisted discovery uses [Discovery+Verify](references/discovery-verify.md) with import-graph partitioning.

```
python3 <this-skill>/scripts/verify_ledger.py .qc-findings/<skill>.json
python3 <this-skill>/scripts/partition.py --root . --json
python3 <this-skill>/scripts/partition.py --reexam --since <sha> --profile .qc-profile.json --json
python3 <this-skill>/scripts/suite_rollup.py --findings-dir .qc-findings
python3 <this-skill>/scripts/verify_profile.py .qc-profile.json
```

## Index

| Topic | Where |
|-------|-------|
| Laws | [references/laws.md](references/laws.md) |
| Ledger, scenario, deferred vocab, CLEAN lists | [references/ledger.md](references/ledger.md) |
| Schema | [references/qc-finding.schema.json](references/qc-finding.schema.json) |
| Severity | [references/severity.md](references/severity.md) |
| Verdict + suite algebra | [references/verdict.md](references/verdict.md) |
| Profile + examination + truth-map + clusters + invariant registry + canonical forms | [references/profile.md](references/profile.md) |
| Discovery+Verify, partitioning, reexam set, confidence routing | [references/discovery-verify.md](references/discovery-verify.md) |
| Anti-rationalization | [references/anti-rationalization.md](references/anti-rationalization.md) |
| Commits + summary banner | [references/commits.md](references/commits.md) |
| Suite order | [references/suite.md](references/suite.md) |
| Seeded fixtures (port acceptance) | [references/fixtures.md](references/fixtures.md) |

## Suite order

`qc-packaging` → `qc-hardening` → `qc-coherence` → `qc-docs`. Details in [suite.md](references/suite.md).

## Port gate

A reconstruction is faithful only when `scripts/verify_port.py` recovers the seeded set under `fixtures/` at the declared severities and marks clean modules `EXAMINED`. See [fixtures.md](references/fixtures.md).
