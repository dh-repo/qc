# Discovery + Verify

Shared workflow: `workflows/discovery-verify.js`. Pluggable Audit, fixed Verify, fixed Synthesize. Remediation stays with the caller — the workflow never edits or commits.

## When

Chunked / LLM-assisted discovery. Hardening: chunked mode (>5K LOC or context pressure). Coherence: codebase scope, highest yield >5K LOC. Fallback: manual subagent dispatch with the same dual-vote rule.

## Partitioning (before Audit)

```
python3 <qc-core>/scripts/partition.py --root . --json
```

Priority:

1. **Import graph** — coupled files stay in one group (the Structural sub-audit already builds this graph; reuse it).
2. **Language boundary** — never mix languages in a group.
3. **LOC pack** — target 500–800 LOC; split only after (1) and (2).

Pure LOC groups that split a tightly-coupled set are wrong even if the sizes look even.

Partial-rerun: if the profile shows >80% of modules `EXAMINED` and only N new/changed modules exist, run deep-read on the **reexam set**, not the whole tree:

```
python3 <qc-core>/scripts/partition.py --root . --reexam --since <last_examined_sha> --profile .qc-profile.json --json
```

That set is changed files plus import-graph neighbors that already sit in `hot_spots[]` or `pass_debt[]` (new code combining with existing latent pieces). Unrelated unchanged modules stay out.

## Args

```
Workflow({
  scriptPath: "<qc-core>/workflows/discovery-verify.js",
  args: {
    kind: "groups" | "lenses",
    repoPath: "<abs>",
    groups: [{ key, label, files, untestedLines? }],   // kind=groups (hardening)
    lenses: [{ key, title, rubric }],                   // kind=lenses (coherence)
    moduleGroups: ["path group", ...],                  // optional, lenses fan out per group
    offLimits: [...],
    priorState: "<profile deferred + prior skill ledgers>",
    structuralCandidates: [...],                        // ambiguous mechanical hits only
    moduleInventory: "...",
    conventions: "...",
    goldenNote: "..."
  }
})
```

## Audit (pluggable)

One agent per unit (group, or lens × group). Output includes findings **and** a CLEAN list. Hardening CLEAN is five Carmack questions or `{invariant, assumptions, sequence_risk}` — a one-liner is incomplete. Coherence CLEAN is `{artifact, invariant}`. Empty findings + full CLEAN is valid. Do not manufacture findings.

Hardening composition is primary (sequences, dual paths, every ingest path); live I/O first. Coherence writes `canonical_forms[]` / `layer_model` / enforces `invariants[]`.

## Verify (fixed)

Two perspective-diverse votes per candidate. **Skip** when `confidence` is `mechanical` or `human`. Ambiguous structural hits (stubs, duplication, orphan exports) still verify — tools over-report deliberate seams.

Recommendation:

- both votes say **real** → `fix`
- both say **refuted / intentional** → `drop` (keep `intentional_evidence`)
- split or any `uncertain` → `defer`

Never silently drop a contested finding. Do not weaken this.

## Synthesize (fixed)

Dedup. Rank P0 > P1 > P2 > P3. Coverage: every unit returned a CLEAN list; any inventory module in neither a finding location nor CLEAN is `unexamined` — that is an incomplete audit, not a clean one. Attach `related_findings` when a prior-skill deferred item is the same issue. Put harvestable `invariants[]` / `canonical_forms[]` / `layer_model` on coverage for the caller to persist.

## What stays model-driven

Triage → fix → regression test → narrow gates → isolated commit. Severity calibration against off-limits / golden pins. Canonical-site / module-split judgment (defer those).
