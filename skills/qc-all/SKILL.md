---
name: qc-all
description: Run the full quality control suite in the correct order — packaging, hardening, coherence, docs. Use before releases, after major feature cycles, or when you want a comprehensive quality gate. Triggers include "qc-all", "full QC", "run all quality checks", "release readiness", "quality gate".
---

# QC-All — Full Quality Control Suite

**REQUIRED:** Load `qc-core` first. Suite order, verdict algebra, profile, and ledger contract live there. This skill is the router: skip logic, watch manifest, history, supervisor dispatch.

Legal order (do not reorder): **qc-packaging → qc-hardening → qc-coherence → qc-docs**. Mechanical-then-deep happens inside hardening. Docs run last so they match the code that survived.

## When to Use

- Before cutting a release branch
- After a major feature cycle (3+ sessions of feature work)
- When preparing for a customer deployment
- When you want a single comprehensive quality gate

## Execution Flow

**Pre-flight:** Load qc-core and `.qc-profile.json`. Read `references/qc-watch-manifest.json`. Last-run SHA = last line of `.qc-history.jsonl` → `git_sha`, else null. If last SHA is set, compute `changed_files` and the hardening/coherence **reexam set**:

```
python3 ../qc-core/scripts/partition.py --reexam --since $last_sha --profile .qc-profile.json --json
```

**Per-skill loop** — for each skill in `[qc-packaging, qc-hardening, qc-coherence, qc-docs]`:
- Apply **Skip Decision** (below).
- If running: invoke `/qc-<skill>` with **prior-skill ledgers as mandatory input** (hardening ledger → coherence `priorState`; hardening + coherence → docs). Pass the reexam set as scope for hardening and coherence. Then read `.qc-findings/<skill>.json`.
- If skipped: record `{skill, last_covered_sha: last_sha}`.

**Aggregate:** `python3 ../qc-core/scripts/suite_rollup.py --findings-dir .qc-findings` (algebra: [qc-core verdict](../qc-core/references/verdict.md)).

**Persist:** `_rollup.json` is current state. `python3 references/scripts/append_history.py .qc-findings/_rollup.json` appends one line to `.qc-history.jsonl` (20-line trim).

## Skip Decision

```
1. No .qc-history.jsonl → run ALL skills.
2. last_sha = last history line .git_sha; current_sha = git rev-parse HEAD
3. last_sha == current_sha → skip ALL (last_covered_sha = last_sha)
4. Else changed_files = git diff --name-only $last_sha..HEAD
5. Per skill: if any watch-manifest glob matches a changed file → run; else skip
```

## Output Contract

Write `.qc-findings/_rollup.json`. Schema: `../qc-core/references/qc-finding.schema.json`. `findings` is always empty in the rollup; provenance is `run_id`, `git_sha`, `skipped`, `findings_by_skill`, `skill_verdicts`.

Run ID: `<YYYY-MM-DD>T<HH:MM:SS>Z-<7-char-sha>`.

```json
{
  "schema_version": "1.1",
  "skill": "qc-all",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234567890",
  "findings": [],
  "verdict": "READY_WITH_DEBT",
  "skipped": [
    {"skill": "qc-packaging", "last_covered_sha": "abc1234"}
  ],
  "findings_by_skill": {
    "qc-hardening": {"P0": 0, "P1": 0, "P2": 3, "P3": 1},
    "qc-coherence": {"P0": 0, "P1": 1, "P2": 0, "P3": 0}
  },
  "skill_verdicts": {
    "qc-hardening": "READY_WITH_DEBT",
    "qc-coherence": "READY_WITH_DEBT"
  }
}
```

Any skill `NOT_READY`, or any P0 anywhere (fixed or not), → suite `NOT_READY`. Else any `READY_WITH_DEBT` or deferred P1 → `READY_WITH_DEBT`. Else `READY`.

Supervisor dispatch: [references/supervisor-dispatch.md](references/supervisor-dispatch.md).
