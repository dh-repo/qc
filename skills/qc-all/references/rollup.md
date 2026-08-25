# Rollup: Deterministic Verdict Computation

Describes how `qc-all` aggregates per-skill JSON files into `_rollup.json`.

## Input

```
.qc-findings/qc-packaging.json
.qc-findings/qc-docs.json
.qc-findings/qc-hardening.json
.qc-findings/qc-coherence.json
```

Plus the set of `skipped[]` skills from the skip-decision phase (skills that were not run this cycle).

## Aggregation Steps

```
1. For each non-skipped skill, read its .qc-findings/{skill}.json.
   Build findings_by_skill[skill] = {
     P0: count of findings where severity=="P0",
     P1: count of findings where severity=="P1",
     P2: count of findings where severity=="P2",
     P3: count of findings where severity=="P3"
   }

2. Sum totals across all non-skipped skills:
   total_P0 = sum of findings_by_skill[*].P0
   total_P1 = sum of findings_by_skill[*].P1

3. Compute open P1 count:
   open_P1 = count of P1 findings where fixed==false AND deferred_because is absent or empty

4. Apply verdict rules (in priority order):
   a. If total_P0 > 0:
        verdict = NOT_READY
   b. Else if open_P1 > 0:
        verdict = NOT_READY
   c. Else if total_P1 > 0 (all P1s have fixed==true or deferred_because set):
        verdict = READY_WITH_DEBT
   d. Else if any P2 finding has fixed==false and no deferred_because:
        verdict = READY_WITH_DEBT   # unaddressed P2 = debt acknowledged
   e. Else:
        verdict = READY

5. Compose _rollup.json:
   {
     "schema_version": "1.0",
     "skill": "qc-all",
     "run_id": "<ISO-timestamp>Z-<7-char-sha>",   # e.g. 2026-05-17T14:30:00Z-abc1234
     "git_sha": "<full or 7-char SHA of HEAD>",
     "findings": [],                              # rollup never holds raw findings
     "verdict": <verdict from step 4>,
     "skipped": [ {"skill": "...", "last_covered_sha": "..."}, ... ],
     "findings_by_skill": { "<skill>": {P0,P1,P2,P3}, ... }
   }
```

## Run ID Format

`<YYYY-MM-DD>T<HH:MM:SS>Z-<7-char-git-sha>`

Pattern: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z-[0-9a-f]{7}$`

Example: `2026-05-17T14:30:00Z-abc1234`

## Skipped Skills

Skipped skills contribute no findings to the aggregation. Their `last_covered_sha` is recorded in `skipped[]` for traceability. If ALL skills are skipped, `verdict = READY` (no new evidence of regression) and `findings_by_skill` is empty.

## Verdict Summary

| Condition | Verdict |
|-----------|---------|
| Any P0 finding | `NOT_READY` |
| Any P1 with `fixed: false` and no `deferred_because` | `NOT_READY` |
| All P1s fixed or deferred, zero P0 | `READY_WITH_DEBT` |
| Zero P0, zero P1, all P2/P3 clean or deferred | `READY` |
