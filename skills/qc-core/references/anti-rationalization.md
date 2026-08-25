# Anti-rationalization

Every excuse below sounds principled. Each is a known loophole. When you hear yourself making one, stop.

| Excuse | Reality |
|--------|---------|
| "Three clean passes looks lazy — I'll re-read at a stricter altitude and file the borderline things." | Fabricating severity is the same offense as fabricating a finding. Three zeros is the expected output of clean code. |
| "This could theoretically fail if an attacker / cosmic ray / future requirement…" | Not a finding. Need `trigger` + `violated_invariant` + `observable`. |
| "The tangled structure *is* the defect, so restructuring is the minimal fix." | A structural split is never the minimal fix. Patch in place or defer `needs-architecture`. |
| "Dual-vote is expensive on this many hits, I'll take the obvious ones." | Mechanical and human-confirmed hits skip verification. Everything else votes. The threshold does not move because the queue is long. |
| "I'll invent a P2 so the run has something to show." | Manufacturing findings is the original sin of this suite. |
| "Docs can describe the intended design; the code will catch up." | Docs match the codebase that exists. Unknowns are labeled unknown. |
| "Different name, same idea — not worth a finding / too fuzzy to decide." | Emit a `clusters[]` row (symbols + rationale) or it is not a finding. Fuzzy clustering with no artifact is ledger churn. |
| "I examined the module; I don't need to write it down." | If you cannot name the artifact and state the invariant, you did not examine it. |
| "A deferred hardening P1 doesn't belong in coherence priorState." | Prior-skill ledgers are mandatory inputs. Link via `related_findings`; do not mint a parallel id. |
| "This repo has AI / supply-chain / observability surfaces the 14 passes don't name, so I'll add a pass." | Existing Security, Env/Config, Carmack, and Architectural checks cover surfaces that exist. Expanding the surface violates law 1. |
| "Systems always run degraded, so three clean Carmack passes are impossible / I should invent residual findings." | Clean terminal state is the expected outcome of well-hardened code. Deep passes exist to *reach* it, not to prove cleanliness is fake. |
| "These two things could theoretically combine…" | Not a finding. `trigger` must name the combination **and** `observable` must be real. |
| "The root cause is this one line." | Deep findings are combination/sequence/dual-path scenarios. Grep the pattern; fix all instances in one commit; record the missed combination as pass-debt. |
| "Chaos engineering means Game Days / prod failure injection / adaptive-capacity metrics." | Out of scope. Blast radius is in-repo tests, never production. |

## Red flags — STOP

- Rewriting a function that has no defect
- Adding a module, class, or abstraction to "fix" a finding
- Changing public signatures or parameter defaults
- Re-grading a style nit above P3
- Changing a test's expected value to match current output without an independent proof the test is wrong
- Normalization that rewrites already-accepted input (trim/canonicalize/default/emit a field) — detect-and-report is fine
- Empty CLEAN list on an LLM-assisted pass
- Theoretical failure scenarios with no `observable`
- Skipping Verify because "it's obviously real"
- Reordering mechanical and deep passes
- Documenting a feature the code does not have
- Inventing a finding because "systems always run degraded"
- A deep-finding `trigger` that names only one function with no second step, impl, or location
- Production failure injection, Game Days, or invented recovery/monitoring
