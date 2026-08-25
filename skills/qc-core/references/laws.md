# The Seven Laws

These do not change. A port that weakens any of them is not a port.

1. **Harden what exists.** Find and fix problems. Do not add features, do not change architecture, do not change functional behavior. Documentation matches the codebase that exists. If a surface (supply-chain, AI-specific, observability) exists in the repo, existing Security / Env / Carmack / Architectural checks will see it. Do not expand the surface.

2. **Concrete failure scenario or it is not a finding.** Deep findings (Correctness, Carmack, Chaos, Semantic, Architectural) and any P1+ judgment finding carry a structured triple: `trigger`, `violated_invariant`, `observable`. "This could theoretically…" is not a finding. Mechanical tool hits stay lightweight.

3. **Fix in place or defer.** The smallest behavior-preserving patch in the existing structure, or `fixed: false` plus a closed-vocabulary `deferred_because`. A bug in code that needs refactoring is not a license to refactor.

4. **P0 blocks even if fixed.** A run that found an outage-class bug grades `NOT_READY` as a human-review gate. Record the fix (`fixed: true`); a human clears the release. This is a suite-level policy: any P0 in any skill ledger blocks the rollup.

5. **Isolated commits.** Each pass commits independently so any fix is trivial to revert. Batch *clean* passes into one commit; never batch-skip *execution*.

6. **Mechanical before deep.** Hardening passes 1–11 before 12–14. Coherence Structural before Conformance/Semantic/Architectural. Do not collapse the 14 hardening passes or reverse this order. The mechanical gate keeps Carmack/Chaos from drowning in lint noise.

7. **Dual-vote to fix.** Both adversarial votes must say the finding is real before it is fixed. Split or any `uncertain` → defer, never silently drop. Do not soften the threshold. Route fewer candidates into the expensive path (mechanical and human-confirmed hits skip verification); the rule for the ones that enter does not change.

North star: three clean passes is the expected output of clean code, not a reason to manufacture findings.

## Why the deep passes exist

These are why mechanical cleanliness is not enough. They do not add a pass, a Game Day, or a production experiment.

- **Catastrophe is multi-factor.** Single-function bugs are rarely the production problem. Combinations, sequences, dual paths, and multi-step interactions are.
- **Latent failures remain after mechanical passes.** The tree runs with a changing mixture of them. Continuous probing and durable memory of prior findings are necessary.
- **There is no isolated root cause.** Deep findings and escalations are systemic and scenario-based, not one-line theater.
- **Change creates new combinations** with pieces that did not themselves change. New/changed files plus import-graph neighbors that are already hot spots or pass-debt get composition re-examination.
- **Invariants are continuously created.** One-shot cleanliness is less valuable than permanent artifacts that retain concrete experience with *this* codebase’s failure modes.
- **System as imagined ≠ system as found.** Static contracts and docs are never identical to live paths. Coherence and docs exist to catch that gap — still only what exists, never invented recovery.

Clean Carmack across all modules plus a green Chaos suite remains the expected terminal state. These bullets explain why the deep passes are required to *reach* it, not why cleanliness is fake.
