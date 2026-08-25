# Rollup

Canonical algebra: `qc-core/references/verdict.md` and `qc-core/scripts/qc.py::suite_verdict`.
Do not reimplement it here.

```
python3 ../qc-core/scripts/suite_rollup.py --findings-dir .qc-findings --skipped skipped.json
```

Legal order: qc-packaging → qc-hardening → qc-coherence → qc-docs.

Inputs: `.qc-findings/<skill>.json` for each non-skipped skill, plus `skipped[]`.

The rollup object has empty `findings` (raw findings stay per-skill), plus `verdict`, `skipped`, `findings_by_skill`, `skill_verdicts`.

Any skill `NOT_READY`, or any P0 anywhere (fixed or not), → suite `NOT_READY`.
Else any `READY_WITH_DEBT` or deferred P1 → `READY_WITH_DEBT`.
Else `READY`. All-skipped → `READY`.
