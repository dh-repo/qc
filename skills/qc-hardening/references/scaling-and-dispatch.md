## Scaling Strategy

Hardening must scale to large codebases without losing depth. Two modes:

**Inline mode** (default, <5K LOC): Execute all passes directly. Read modules as needed per pass.

**Chunked mode** (>5K LOC or when context pressure is felt): Partition the codebase into module groups and dispatch subagents for audit-heavy passes. The coordinator reads the project structure, assigns module groups, dispatches subagents, synthesizes findings, and applies fixes.

**When to switch to chunked mode:**
- Codebase exceeds ~5K LOC of *total* production code (not just new code)
- You notice you're skimming modules instead of deeply reading them
- Prior Carmack runs revealed coverage gaps (modules never questioned)
- The project has more than ~8 production modules

**Partial-rerun scoping:** The 5K LOC threshold is based on *total* codebase size, but that doesn't mean you must dispatch subagents for every module on every run. If the hardening profile shows >80% of modules were EXAMINED in prior runs and only N new/changed modules exist, run deep-read passes (1, 12) inline on just the new modules, and scope Pass 14 to the new/changed modules plus any existing hot spots. Only dispatch subagents for the full codebase if: (a) no prior profile exists, (b) the profile shows modules still marked NOT YET, or (c) the total new+changed LOC exceeds ~2K (enough to benefit from parallel review).

**Which passes benefit from subagents:**

| Pass | Subagent strategy |
|------|-------------------|
| 1 (Correctness) | **Dispatch per module group** — deep-read pass, same rigor as Carmack (audit manifest, CLEAN lists, hot-spot priority) |
| 2 (Security) | Secrets grep can run as one agent; injection audit per module group |
| 3-7 | Usually fine inline — these are tool-driven (mypy, ruff, coverage) or lightweight |
| 8 (Test Coverage) | Dispatch per module group for test writing |
| 12 (Carmack) | **Always dispatch per module group** — deep reading degrades with context size |
| 14 (Maintainability) | Usually coordinator synthesis after passes 12-13; dispatch targeted hot-spot rereads if maintainability risks span multiple module groups |

**Module grouping heuristic:**
1. List all production modules with LOC
2. Group into chunks of 500-800 LOC each (target: one module group fits comfortably in a subagent's working context)
3. Keep tightly-coupled modules together (e.g., `parser.py` + `normalizer.py` share the parse-then-normalize contract)
4. Reference data modules (pure dicts/maps) can be skipped or grouped into a single "reference data" chunk

## Discovery + Verify via dynamic workflow (preferred in chunked mode)

In chunked mode, run the **Discovery + Verify** half of hardening — the parallel deep-read across
module groups, the adversarial verification of each finding, and cross-module dedup — as a single
**dynamic workflow** instead of hand-dispatching subagents per pass. The workflow ships with this
skill at `workflows/discovery-verify.js` and returns a ranked, verified findings ledger.

**Why a workflow here:** one rubric across N groups (no copy-paste drift), schema-enforced
findings, a **2-vote adversarial refutation of every finding** (kills false positives, sharpens
severity and the fix-vs-defer call), automatic cross-module dedup, resumability (`resumeFromRunId`)
for long runs, and live progress (`/workflows`). Invoking this skill is the opt-in for the workflow.

**What STAYS model-driven — do NOT put in the workflow:** triage → fix → write the regression test
→ run the narrow gates + any golden/regression suite → **isolated commit**. The workflow reads and
verifies; it never edits code or commits. Remediation needs judgment a concurrent fan-out cannot
have — severity calibration, the off-limits / in-flight-file boundary, golden-pin sensitivity, and
commit isolation — plus sequential side effects that must not run concurrently.

How to run it (after partitioning modules with the grouping heuristic above):

```
Workflow({
  scriptPath: "<this skill's base dir>/workflows/discovery-verify.js",
  args: {
    repoPath: "<absolute repo root>",
    groups: [ { key, label, files: [...], untestedLines?, lenses? }, ... ],
    offLimits: [ "<uncommitted / in-flight files you must NOT modify>" ],
    priorFindings: "<profile hot-spots + pass-debt + prior ledger, for multi-order analysis>",
    goldenNote: "<how pinned/golden values present in this repo>"
  }
})
```

It returns `{ ranked_findings, promoted_cross_module, coverage }`. Each finding carries a
`recommendation`: **fix** (both verdicts confirm, reachable, not off-limits, not golden-sensitive),
**defer** (real but needs judgment / untestable locally / off-limits / golden-sensitive — with a
`defer_reason`), or **drop** (refuted). Then, INLINE:

- For each **fix**: apply the change, add a regression test that would have caught it, run the
  narrowest relevant gates plus any golden suite, and commit it isolated (stage only files you
  changed — never `git add -a` when in-flight work is in the tree).
- For each **defer**: record it in `.qc-findings/qc-hardening.json` and the profile hot-spots; do
  not fix.
- Use `coverage` to confirm every group returned a CLEAN list (nothing was skimmed).

This replaces the *read + verify* portion of Passes 1, 2 (injection audit 2.2), 3, 5, and 12 in chunked mode. The
tool-driven passes (2 deps, 4 types/lint, 6 perf, 8 coverage, 11 env) still run as direct commands;
Pass 13 (Chaos) and Pass 14 (Maintainability) run as in their references.

**Gating:** workflow only in chunked mode (>5K LOC). In inline mode, read modules directly — no
workflow. If the Workflow tool is unavailable, use the manual dispatch pattern below.

**Manual subagent dispatch (fallback when the Workflow tool is unavailable):**

```
Coordinator:
  1. Read project structure, compute module groups
  2. For each module group, dispatch subagent with:
     - The pass instructions (from this skill)
     - Full text of the modules in this group
     - Module interface summaries for OTHER groups (imports, public functions, types)
       so the subagent understands cross-module contracts without reading everything
     - Instruction: "Report findings only. Do not fix. Use the evidence standard."
  3. Collect findings from all subagents
  4. Deduplicate (same finding reported by two groups seeing the same interface)
  5. Apply fixes for confirmed findings
  6. Run tests, commit
```

**Cross-module findings:** The coordinator is responsible for findings that span module boundaries (e.g., "module A produces X but module B expects Y"). Subagents flag potential cross-module concerns; the coordinator verifies them with the full picture.

**Cross-module findings are first-class findings.** They get the same F-ID, severity, and evidence treatment as single-module findings. When the coordinator confirms a cross-module concern:
1. Assign it `F<pass>.X` like any other finding (e.g., `F12.6`)
2. Classify severity using the same P0/P1/P2 scale — a race condition between two modules is not less severe because it spans a boundary
3. Either fix it in the current pass, or explicitly defer it with severity and justification: `F12.6 (P1, deferred) — <what> — Deferred because: <reason>`. Deferred findings appear in REMAINING CONCERNS with their F-ID and severity, not as unnamed bullet points.
4. Add deferred cross-module findings to the hardening profile Hot Spots section so the next run picks them up

Do NOT report cross-module issues as second-class "concerns" without IDs. If it has a concrete failure scenario, it's a finding. If it doesn't, it's not worth reporting.

---

## Remediation: Dispatching the Autonomous Supervisor

When hardening produces deferred findings or findings too complex to fix inline, dispatch the autonomous supervisor agent.

### When to dispatch

| Situation | Action |
|-----------|--------|
| All findings fixed inline | No dispatch needed |
| Deferred P2 findings | Optional — dispatch if the fixes are mechanical |
| Deferred P1 findings | Dispatch — these should not remain open |
| Cross-module findings requiring coordinated changes | Dispatch with specific fix instructions |

### How to dispatch

After the summary report, invoke the autonomous supervisor (`.github/agents/autonomous-supervisor.agent.md`) with:

```
Mission: "Fix deferred hardening findings from Run N."
Mode: Attainment
Quality bar: "Every deferred P1 is fixed. P2 findings are fixed or documented
             as accepted debt. Full test suite passes. Coverage ≥ threshold."
Constraints:
  - Do not change functional behavior
  - Run the full test suite after every fix
  - Cross-check every fix against alternative backend implementations
Stop condition: "All deferred P1 findings fixed. All P2 findings fixed or
                documented."

Deferred findings:
[Paste from the DEFERRED FINDINGS section of the summary report]
```
