# Ledger, evidence, deferred vocabulary

## Artifact

Write `.qc-findings/<skill>.json` as **one JSON object** conforming to [`qc-finding.schema.json`](qc-finding.schema.json). Schema version `1.1`. Do not split per pass or convert to JSON Lines.

`qc-all` reads these exact paths. If a skill is vendored without the suite, still use this schema (copy `qc-core`, not a fork of the schema).

## Atomic write

The file holds the run's *full accumulated findings so far*. After each pass or sub-audit, rewrite the whole object to a temp file in the same directory and `os.replace()` it over the target. Never in-place edit. An interrupted run leaves the last complete state.

```
python3 <qc-core>/scripts/write_ledger.py .qc-findings/<skill>.json
# JSON object on stdin
```

Then machine-check:

```
python3 <qc-core>/scripts/verify_ledger.py .qc-findings/<skill>.json
```

If it reports a mismatch, fix the ledger, not the script.

## Finding fields

Required: `id`, `severity`, `file`, `what`, `fixed`. Carry `pass`, `line`, `why`, `fix`, `scope` where known.

`id` pattern: `^[A-Z]+-?[0-9]+(\.[0-9]+)?$` (e.g. `F12.3`, `C1.1`, `MS-1.1`, `D2.1`).

**Confidence** (required on new findings): `mechanical` | `pattern` | `proven` | `human`.

- `mechanical` — tool output (mypy, ruff, broken import). Lightweight evidence. Skips dual-verify.
- `pattern` — checklist / heuristic match. Dual-verify.
- `proven` — Chaos reproduction or Carmack structured scenario. Dual-verify (reasoning can still be wrong).
- `human` — user-confirmed. Skips dual-verify.

**Scenario** (required when `needs_scenario` is true — any P1+ that is not `mechanical`, plus Correctness / Carmack / Chaos / Semantic / Architectural):

```json
"scenario": {
  "trigger": "Two threads call close() after a write has begun",
  "violated_invariant": "close() is serialized; no write proceeds after close begins",
  "observable": "handle closed under an in-flight write; truncated output file"
}
```

Carmack's five questions map onto this triple: Q1 → `violated_invariant`, Q2/Q3 → `trigger`, Q4/Q5 → `observable`.

Skill-specific scenario wording (same three fields):

- **Hardening:** the runtime failure (sequence, dual path, live adapter).
- **Coherence Semantic/Architectural:** `under input sequence X, backend A returns Y while B returns Z / a different exception`.
- **Docs Accuracy:** `operator following the documented path encounters X because the claim is false`.

**Reject root-cause theater.** Mechanical hits may be single-site. For Carmack, Chaos, Semantic, and Architectural findings, `trigger` names a **combination** — a second step, a second implementation, a second location, or a dual path. A trigger that is only "this function is wrong" is incomplete for those lenses. "Could theoretically combine" with no observable is still not a finding.

**related_findings**: array of ids in this or another skill's ledger for the same underlying issue. Do not mint a third id at a different severity. When coherence sees a deferred hardening finding about the same defect, link it.

## Deferred vocabulary

`deferred_because` is `code` or `code: detail`. Codes:

| Code | Use when |
|------|----------|
| `needs-architecture` | Fix requires a new module, split, or public surface |
| `public-signature` | Fix would change a public signature or default |
| `behavior-change` | Fix would change functional behavior (feature, not hardening) |
| `needs-owner` | Product / API owner must decide |
| `golden-sensitive` | Fix would shift a pinned/golden value |
| `off-limits` | In-flight / uncommitted files the run must not touch |
| `needs-canonical-site` | Coherence: which site is canonical is a design call |
| `needs-module-split` | Mixed responsibility; split is the real fix |
| `user-provided-unknown` | Docs: fact is not in the repo and the user has not supplied it |
| `accepted-debt` | Explicitly accepted P2/P3 |
| `needs-migration` | Schema / ops migration required |
| `cross-backend` | Coordinated multi-backend change |

A deferral recorded any other way reads as an *open* finding and blocks release.

## CLEAN list (`examined`)

Every LLM-assisted pass writes `examined`: named artifacts with a one-sentence invariant, or (Carmack) the five questions at module granularity. Empty or boilerplate (`looks fine`, `seems correct`, `examined`) renders the pass incomplete. `verify_ledger.py` rejects that for `qc-hardening` and `qc-coherence` in `mode: "full"`.

Quick-check runs set `"mode": "quick-check"` and skip this requirement.

## Lightweight vs full evidence

- Mechanical (`confidence: mechanical`): id, location, what, fix. The tool is the why.
- Everything else: full evidence plus scenario when `needs_scenario`.
