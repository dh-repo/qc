# Verdict math

One algorithm, in `scripts/qc.py::compute_verdict`. Do not reimplement in a skill, a shell script, or a prompt.

## Per-skill

| Verdict | Condition |
|---------|-----------|
| `NOT_READY` | Open P1 (`fixed: false`, no `deferred_because`). Under **presence** P0 policy (hardening): any P0, fixed or not. Under **open** P0 policy (packaging, docs, coherence): only an *open* P0. |
| `READY_WITH_DEBT` | No blocking P0/open P1; at least one P1 (fixed or deferred) or an open P2 |
| `READY` | No P0 (under policy), no P1; P2/P3 clean or deferred |
| `SKIPPED` | Reserved for `qc-all` marking a skill it did not run |

`P3` never blocks. `verify_ledger.py` recomputes this and fails on mismatch.

Hardening standalone uses presence policy so a repaired outage still grades `NOT_READY` — the original human-review gate.

## Suite (`scripts/suite_rollup.py`)

Legal order: **qc-packaging → qc-hardening → qc-coherence → qc-docs**.

Mechanical hardening (passes 1–11) before deep hardening (12–14) happens *inside* `qc-hardening`, not as a separate suite step.

```
1. Any skill verdict NOT_READY → suite NOT_READY
2. Any P0 in any non-skipped ledger (fixed or not) → suite NOT_READY   # human-gate
3. Else any skill READY_WITH_DEBT, or any deferred P1 → suite READY_WITH_DEBT
4. Else READY
All-skipped / empty → READY
```

Skipped skills contribute nothing. Prior-skill ledgers are mandatory inputs to later skills: hardening's deferred findings appear in coherence `priorState` by default; hardening + coherence ledgers appear in docs `priorState`. Cross-skill `related_findings` links the same issue.

The rollup object has empty `findings` (raw findings stay per-skill), plus `verdict`, `skipped`, `findings_by_skill`, `skill_verdicts`.
