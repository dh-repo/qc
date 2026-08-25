---
name: qc-all
description: Run the full quality control suite in the correct order — packaging, docs, hardening, structural integrity. Use before releases, after major feature cycles, or when you want a comprehensive quality gate. Triggers include "qc-all", "full QC", "run all quality checks", "release readiness", "quality gate".
---

# QC-All — Full Quality Control Suite

Router that invokes four sub-skills, applies watch-manifest skip logic, and emits a structured `_rollup.json` with full provenance.

## When to Use

- Before cutting a release branch
- After a major feature cycle (3+ sessions of feature work)
- When preparing for a customer deployment
- When you want a single comprehensive quality gate

## Execution Flow

**Pre-flight:**
1. Read `qc-all/references/qc-watch-manifest.json` (glob lists per skill).
2. Determine last-run SHA: if `.qc-history.jsonl` exists, read its last line and extract `git_sha` as `last_sha`. Otherwise `last_sha = null`.
3. If `last_sha` is non-null, compute `changed_files = git diff --name-only $last_sha..HEAD`.

**Per-skill loop** — for each skill in `[qc-packaging, qc-docs, qc-hardening, qc-coherence]`:
- Apply **Skip Decision** (see below).
- If running: invoke `/qc-<skill>`, then read `.qc-findings/<skill>.json`.
- If skipped: record `{skill, last_covered_sha: last_sha}` in the skipped list.

**Aggregate:** Follow `references/rollup.md` to compute verdict and compose `_rollup.json`.

**Persist:** Write `.qc-findings/_rollup.json`; append one line to `.qc-history.jsonl` (TODO: bounded trim — ticket 582c2d8b).

## Skip Decision

```
1. If .qc-history.jsonl does not exist → run ALL sub-skills (no skip).
2. last_sha = last line of .qc-history.jsonl → .git_sha
3. current_sha = git rev-parse HEAD
4. If last_sha == current_sha → skip ALL sub-skills (last_covered_sha = last_sha).
5. Otherwise: changed_files = git diff --name-only $last_sha..HEAD
6. For each sub-skill:
     manifest_globs = qc-watch-manifest.json[skill]   # e.g. ["**/*.py", "tests/**/*"]
     if any glob in manifest_globs matches any file in changed_files → run skill
     else → mark skipped with last_covered_sha = last_sha
```

Read `.qc-history.jsonl[-1].git_sha` to inspect the last covered SHA at any time.

## Output Contract

Write `.qc-findings/_rollup.json`. Schema: `qc-all/references/qc-finding.schema.json`.

The `findings` array is always empty in the rollup — raw findings live in the per-skill files. Provenance is carried by `run_id`, `git_sha`, `skipped`, and `findings_by_skill`.

**Run ID format:** `<YYYY-MM-DD>T<HH:MM:SS>Z-<7-char-sha>`  
Pattern: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z-[0-9a-f]{7}$`

**Example `_rollup.json`:**

```json
{
  "schema_version": "1.0",
  "skill": "qc-all",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234567890",
  "findings": [],
  "verdict": "READY_WITH_DEBT",
  "skipped": [
    {"skill": "qc-packaging", "last_covered_sha": "abc1234"},
    {"skill": "qc-docs",      "last_covered_sha": "9876543"}
  ],
  "findings_by_skill": {
    "qc-hardening": {"P0": 0, "P1": 0, "P2": 3, "P3": 1},
    "qc-coherence": {"P0": 0, "P1": 1, "P2": 0, "P3": 0}
  }
}
```

## Verdict Rules

Computed deterministically from the aggregated findings per `references/rollup.md`: `NOT_READY` if any P0 or any open P1 (unfixed, no `deferred_because`); `READY_WITH_DEBT` if zero P0 and all P1s are fixed or deferred; `READY` if zero P0, zero P1, and all P2/P3 clean or deferred.

## Supervisor Dispatch

See `references/supervisor-dispatch.md` for payload structure, per-finding-type actions, and agent path note.

## Persistence

Writes `.qc-findings/_rollup.json` (overwrite each run — represents current state, not history). Appends one JSON line to `.qc-history.jsonl` containing at minimum `{run_id, git_sha, verdict, skipped}`. Ring-buffer trim behavior (bounded history) is defined in ticket 582c2d8b.

After writing `.qc-findings/_rollup.json`, invoke the copy of `references/scripts/append_history.py` that ships with this skill:

```bash
python3 "$SKILL_DIR/references/scripts/append_history.py" .qc-findings/_rollup.json
```

`$SKILL_DIR` is the directory that contains this `SKILL.md`. The JSON path is relative to the *target repository* root. The script appends to `.qc-history.jsonl` with automatic 20-line trim.
