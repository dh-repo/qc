# Autonomous Supervisor Dispatch

Single source of truth for the payload passed to the autonomous supervisor when qc-all (or a sub-skill) escalates findings.

## When to Dispatch

| qc-all Verdict | Action |
|----------------|--------|
| `READY` | No dispatch. Record run in `.qc-history.jsonl` and exit. |
| `READY_WITH_DEBT` | Dispatch with P1 findings (fixed or deferred) + all P2 findings. |
| `NOT_READY` | Dispatch with ALL findings. Block further feature work. |

## Payload Structure

Pass the following fields to the autonomous supervisor invocation:

```
Mission:      Resolve all P0 and P1 findings in _rollup.json before the next release gate.
Mode:         Autonomous — read findings, plan fixes, implement, verify, commit.
Quality bar:  Zero P0. Zero open P1 (each P1 must be fixed:true or have deferred_because set).
Constraints:
  - Do not change public interfaces without a matching update to docs and tests.
  - Do not introduce new findings while fixing existing ones (re-run qc-hardening after each fix batch).
  - Preserve all existing passing tests.
Stop condition: _rollup.json verdict == READY or READY_WITH_DEBT (no open P0/P1).
```

## Per-Finding-Type Supervisor Actions

| Finding severity | Finding scope | Supervisor action |
|-----------------|---------------|-------------------|
| P0 | any | Fix immediately; do not defer. Re-run affected sub-skill to confirm resolved. |
| P1 | function | Fix in the same file. Mark `fixed: true`. |
| P1 | module | Fix across module; update tests. Mark `fixed: true` or set `deferred_because`. |
| P1 | codebase | Escalate to human if fix requires architectural decision. Set `deferred_because` with owner. |
| P2 | any | Fix if <30 min effort; otherwise set `deferred_because` with rationale. |
| P3 | any | Defer. Set `deferred_because: "P3 — accepted cosmetic debt"`. |

## Findings Payload Format

Pass the contents of `.qc-findings/_rollup.json` plus the per-skill files for context:

```
findings_source: .qc-findings/_rollup.json
per_skill_detail:
  - .qc-findings/qc-packaging.json
  - .qc-findings/qc-docs.json
  - .qc-findings/qc-hardening.json
  - .qc-findings/qc-coherence.json
```

## Agent Path Note

The autonomous supervisor agent file (`.github/agents/autonomous-supervisor.agent.md`) is **project-specific**. Each consumer repository provides its own agent definition. This document defines the **dispatch payload** — what to send — not the agent itself.

When no agent file exists in the consuming repo, print the payload to stdout and prompt the user to create `.github/agents/autonomous-supervisor.agent.md` using the payload structure above as the mission input.
