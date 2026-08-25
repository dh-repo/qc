# Suite composition

`qc-all` is the router. Algebra and order live here; skip logic and the watch manifest live in `qc-all`.

## Legal order

```
qc-packaging → qc-hardening → qc-coherence → qc-docs
```

Rationale: packaging wraps what exists and must not wait on defect work. Hardening drives residual runtime failure scenarios to zero (mechanical, then deep — never reversed) and harvests invariants. Coherence consumes that ledger plus the invariant registry so it can guarantee compositional consistency instead of rediscovering local defects under new ids. Docs run last so the truth-map and Known limitations match the system that survived.

Do not run docs before hardening on a full suite pass. A standalone `/qc-docs` is still legal.

## Prior-skill inputs

| Skill | Must read |
|-------|-----------|
| qc-hardening | `.qc-profile.json` |
| qc-coherence | profile + `.qc-findings/qc-hardening.json` (deferred items → `priorState`) |
| qc-docs | profile + hardening and coherence ledgers; truth-map against current code |

## Rollup

```
python3 <qc-core>/scripts/suite_rollup.py --findings-dir .qc-findings --skipped skipped.json
python3 <qc-all>/references/scripts/append_history.py .qc-findings/_rollup.json
```

Verdict: [verdict.md](verdict.md). Dispatch: `qc-all/references/supervisor-dispatch.md`.
