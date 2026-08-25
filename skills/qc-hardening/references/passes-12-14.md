## PASS 12: CARMACK REVIEW

Read the code the way John Carmack would. No tools, no checklists — just deep reading and reasoning about correctness from first principles. The previous 11 passes used categorical checks. This pass uses adversarial thinking.

**This pass is different from all others.** It does not follow a checklist. It reads the codebase as a connected system and asks hard questions. Findings from this pass often cut across multiple categories — a single finding might combine correctness, performance, and error handling concerns. That's the point.

**How to execute:**

**Step 0: Run coverage and build the audit manifest.** Before reading any code, run the coverage tool and produce a per-module table. Write it to profile `examination.qc-hardening` (this **is** the Carmack manifest; Pass 1 CLEAN stays on the ledger `examined[]`).

```
| Module | LOC | Coverage | Untested Lines | Live I/O / adapter | Carmack Status |
|--------|-----|----------|----------------|--------------------|----------------|
| parser.py | 534 | 91% | 261-263, 419-431 | no | NOT YET |
| ingest.py | 410 | 70% | 12-40 | excel + parquet readers | NOT YET |
| ... | ... | ... | ... | ... | ... |
```

Update status as you go (`NOT_YET` → `EXAMINED` → `FINDING`). At the end, every module must be `EXAMINED` or `FINDING`. If any say `NOT_YET`, the pass is incomplete.

**`EXAMINED` is hard to fake.** A one-sentence invariant is not enough. Each `EXAMINED` module requires either answers to the five questions or `{invariant, assumptions, sequence_risk}` — all substantive. `verify_profile.py` rejects the rest.

**Priority order:** untested **live external and adapter paths first**, then other untested lines, then the rest. Code that has never executed is code that has never been proven correct. Live I/O is where residual production defects hide after mechanical noise is gone.

**Step 0b: Read the findings ledger.** Passes 1-11 write their findings to `.qc-findings/qc-hardening.json` as they execute. Before deep reading any code, read this file. It contains every finding, its location, severity, and fix from the mechanical passes. **If `.qc-findings/qc-hardening.json` is absent (a first run, or a single deep pass invoked standalone), proceed with no prior-findings input — seed the multi-order analysis from this pass's own reading.** Use it as input to your analysis:

- **First-order effects:** For each finding, ask in those words: **"same pattern in other backends / dual paths?"** A boundary coercion bug in CSV reading likely exists in Excel and Parquet reading too. A missing null check in one orchestrator likely exists in the other.
- **Second-order effects:** For each fix applied in earlier passes, ask "did the fix introduce a new assumption?" A type coercion fix assumes the input is one of a known set of types — what if it isn't?
- **Third-order effects:** Look for *patterns* across findings. Three findings in the same module about the same category (boundary coercion, missing validation, implicit contracts) suggest a missing abstraction or a systemic design gap — not just three individual bugs. Harvest each finding's `violated_invariant` into profile `invariants[]` (`source: carmack`). Do not invent invariants that were not observed.

Report systemic patterns as findings. "Three boundary coercion bugs in ingest.py suggest all external I/O should pass through a single sanitization layer" is a valid Carmack finding if you can show the concrete risk of the current scattered approach.

**Step 1: Deep read.** For each module, for each function, each data flow, each state transition, ask:

1. **"What invariant makes this correct?"** If you can't state the invariant, the code may be correct by accident. An invariant is a property that must always be true — "this dict always has a key for every item in the list," "this value is never negative after this point," "this function is only called after validation." If the invariant isn't enforced or documented, it's fragile.

2. **"What happens when my assumptions are wrong?"** Every function assumes something about its inputs, its environment, or the order of operations. Name the assumptions. Then break each one. What if the list is empty? What if the string contains characters you didn't expect? What if this function is called before that one? What if it's called twice?

3. **"What sequence of valid operations produces an invalid state?"** Individual functions may each be correct in isolation, but calling them in unexpected combinations can corrupt state. Look for mutable state that multiple callers modify. Look for sequences where step 2 assumes step 1 already ran. Look for cleanup that doesn't happen on error paths.

4. **"If this code runs a million times, what breaks?"** Not performance (Pass 6 covered that). Think about: accumulated state that never gets cleared. Cache entries that grow without bound. Counters that overflow. File handles that leak one per call. Error counts that wrap around.

5. **"What would make this code wrong tomorrow?"** What implicit coupling exists? If someone changes module A, does module B silently break? Are there magic strings shared across files? Are there ordering dependencies that aren't enforced? Does the code work only because of a coincidence in the current data (e.g., all addresses currently happen to be US, but the code doesn't actually enforce that)?

**What to look for specifically:**

- **State corruption across calls**: mutable defaults, module-level state modified by functions, caches that go stale
- **Silent data loss**: operations that drop data without logging (truncation, filtering, dedup that merges different records)
- **Ordering dependencies**: code that works only because functions happen to be called in a certain order, without enforcement
- **Implicit contracts**: function A returns something that function B parses, but neither documents the format — if A changes, B breaks silently
- **Degenerate inputs that pass validation**: inputs that are technically valid but cause meaningless output (empty strings that survive `.strip()`, zero-length collections that pass `is not None` checks)

**Cross-backend check (mandatory here when alternative backend implementations exist):** after any fix, grep the other backend(s) for the same pattern and fix all instances in the same commit — see "Cross-Backend Awareness" in [passes-1-11.md](passes-1-11.md).

**Finding format:** qc-core full evidence plus the structured scenario triple (`trigger`, `violated_invariant`, `observable`). `trigger` names a **combination** (second step, second impl, second location, or dual path) — not "this function is wrong." Carmack's five questions map onto that triple (Q1 → invariant, Q2/Q3 → trigger, Q4/Q5 → observable). "Could cause issues" is not a finding.

**Escalation loop (every finding):** grep the pattern → fix all instances in one commit → if a mechanical pass should have caught the combination, write `pass_debt[]`.

**What this pass does NOT do:**
- Style, formatting, naming (those are P3s, not findings)
- Hypothetical future requirements ("what if we need to support X")
- Performance micro-optimization (covered in Pass 6)
- Anything already caught by Passes 1-11 (don't duplicate)

### Carmack subagent dispatch (chunked mode)

In chunked mode, this pass MUST use subagents. Deep adversarial reading degrades with context size — a subagent reviewing 600 LOC will catch things a coordinator skimming 4K LOC will miss.

**Per-module-group subagent prompt:**

```
You are doing a Carmack Review of [module_group_name].

Read this code and answer five questions for every function, data flow,
and state transition:

1. "What invariant makes this correct?"
2. "What happens when my assumptions are wrong?"
3. "What sequence of valid operations produces an invalid state?"
4. "If this code runs a million times, what breaks?"
5. "What would make this code wrong tomorrow?"

## Code to review

[FULL TEXT of modules in this group]

## Untested lines (from coverage report — live I/O / adapter paths FIRST, then the rest)

[List of file:line ranges with 0% coverage in this module group.
These lines have NEVER executed. They are the highest-priority
targets for adversarial reasoning.]

## Interfaces with other modules (do not review these — use for context)

[Public function signatures + types from other module groups, so the
subagent can reason about cross-module contracts]

## Findings from passes 1-11 (use as input for multi-order analysis)

[Contents of .qc-findings/qc-hardening.json — the ledger of all findings from
mechanical passes. For each finding in modules you're reviewing:
- First-order: same pattern in other backends / dual paths?
- Second-order: did the fix introduce a new assumption?
- Third-order: do multiple findings in the same module suggest a systemic gap?]

## Rules

- Report findings only. Do not fix code.
- Every finding must have: ID, Location (file:line), What, Why (concrete
  scenario), Severity (P0/P1/P2), Fix (specific change).
- If you can't fill all fields, it's not a finding. Move on.
- Do not report style, naming, or hypothetical concerns.
- Do not duplicate findings from passes 1-11 (assume those ran already).
- If you see a potential cross-module issue (this module assumes something
  about another module's behavior), file it as a FINDING with the same six
  fields and a combination-shaped trigger. Do not use a second-class
  "concern" list.

Report format:
- FINDINGS: [list of findings with all 6 fields; cross-module included]
- CLEAN: named artifacts, each with the five Carmack questions answered at module granularity (boilerplate "looks fine" is incomplete)
```

**Coordinator responsibilities after subagent reports:**
1. Collect all FINDINGS (including cross-module). Combination-shaped triggers stay first-class — same F-ID, severity, scenario.
2. Verify any finding that spans a group boundary by reading both sides. Discard only if the assumption is actually enforced. Never leave a confirmed combination as an untracked "concern."
3. Track CLEAN lists — if a module group has none, the subagent may have skimmed. Re-dispatch.
4. After all groups reviewed: look for systemic patterns across groups; harvest `violated_invariant` into `invariants[]`; write `pass_debt[]` for missed combinations.

### Re-running the Carmack pass

This pass is designed to be run multiple times. Each run should:
1. Re-run coverage to get fresh untested lines (prior runs may have added tests)
2. Update the audit manifest — carry forward EXAMINED/FINDING status from prior runs
3. Target modules still marked NOT YET, untested lines in EXAMINED modules, and import-graph neighbors of changed files that sit in hot_spots/pass_debt
4. Question fixes from prior runs ("did the fix introduce a new assumption?")

Three runs is typical. If run 3 is clean across all modules, the codebase is well-hardened.

**Completion criteria:** The pass is complete when:
- Every module row in the audit manifest is EXAMINED or FINDING
- Every EXAMINED row has five-question answers or `{invariant, assumptions, sequence_risk}`
- Every untested line range — live I/O first — has been explicitly reasoned about (even if no finding)
- Harvested `invariants[]` rows exist for each Carmack finding's `violated_invariant`

If you can't state what you examined in a module, you didn't examine it.

---

## PASS 13: CHAOS MONKEY

The Carmack pass reads code and reasons about it. This pass *runs* the code with adversarial inputs and observes what actually happens. Theory vs. reality.

**Core principle:** Generate inputs designed to break invariants, corrupt state, or trigger unhandled edge cases — then feed them through the real pipeline and verify the system degrades gracefully. Every crash, hang, or silent data corruption is a finding.

**This pass writes tests only.** It does not change production code. Each production-shaped test is an explicit **hypothesis** ("this sequence must not crash or corrupt"). Blast radius is the test file — never production, never Game Days. Findings use the structured scenario triple; `trigger` names the combination. The fix is typically "add input validation" or "handle this edge case," implemented in a subsequent commit. `tests/test_chaos.py` is **living production-shaped coverage** — every crash stays in the suite permanently.

### How to execute

**Step 1: Identify the chaos categories** relevant to this codebase. Not all apply to every project.

| Category | What to throw | Looking for |
|----------|--------------|-------------|
| **Encoding chaos** | Non-ASCII, mixed encodings, null bytes, RTL markers, zero-width chars, emoji, surrogate pairs | Crashes in string operations, mojibake in output, silent truncation |
| **Boundary values** | Empty strings, single chars, strings >10K chars, max-int values, negative numbers, NaN, Inf | IndexError, OverflowError, infinite loops, memory blowup |
| **Type confusion** | None where string expected, int where string expected, list where dict expected, nested nulls | TypeError, AttributeError, silent wrong-type propagation |
| **Injection payloads** | SQL fragments, shell metacharacters, format strings (`%s`, `{0}`), path traversal (`../`) | Not for security (Pass 2 covered that) — for crashes and corruption |
| **Structural chaos** | Deeply nested input, circular references, duplicate keys, extremely wide rows, columns with no data | RecursionError, KeyError, memory exhaustion |
| **Timing/ordering** | Same function called twice, functions called in wrong order, empty batch followed by large batch | State corruption, stale caches, counter drift |
| **Real-world garbage** | Actual malformed carrier data: mixed delimiters, BOM markers, trailing whitespace everywhere, inconsistent quoting, numeric columns with text ("N/A"), dates as numbers | The bugs that actually happen in production |

**Step 2: For each public function, write chaos tests.** Group by function, not by chaos category. Each test:

1. Constructs a specific adversarial input
2. Calls the function
3. Asserts one of:
   - **No crash** (function returns without exception)
   - **Specific exception** (if the input should be rejected, verify it's the right exception with a useful message)
   - **Graceful degradation** (output may be empty/default but is not corrupt)

**Do NOT assert specific output values** for garbage input. The point is "doesn't crash and doesn't corrupt," not "produces the correct parse of emoji addresses."

**Step 3: Run chaos tests.** Any crash or unhandled exception is a finding.

### Chaos test structure

```python
class TestChaosMonkey<Module>:
    """Adversarial inputs for <module>."""

    def test_<category>_<specific_case>(self):
        """<What we're throwing and why it might break>."""
        result = function(adversarial_input)
        # Assert graceful degradation, not specific output
        assert isinstance(result, ExpectedType)
```

### What this pass does NOT do

- Change production code (chaos tests only)
- Production failure injection, Game Days, or adaptive-capacity measurement
- Test performance under load (Pass 6)
- Test security/injection for exploitation (Pass 2)
- Test correct output for valid inputs (Pass 1)
- Duplicate existing edge-case tests (check existing tests first)

### Chaos and the test suite

Chaos tests go in a dedicated file: `tests/test_chaos.py`. They are part of the permanent test suite — they run on every test invocation (whether `pytest`, `unittest discover`, or the project's test command from CLAUDE.md). A future code change that introduces a crash on adversarial input will be caught immediately. **Match the project's test framework:** If the project uses `unittest`, write chaos tests as `unittest.TestCase` subclasses. If it uses `pytest`, use plain functions or classes. Check CLAUDE.md and existing test files for the convention.

**Naming convention:** `test_chaos_<module>_<category>_<case>` — makes it clear these are adversarial tests, not functional tests.

### Findings from chaos

When a chaos test crashes:
1. File the finding (ID, Location, What, Why, Severity, Fix)
2. Keep the chaos test (it now documents the bug)
3. **Before fixing: Carmack escalation.** Grep for the same pattern elsewhere in the codebase. If the crash was `.strip()` on a non-string, search for every `.strip()` call on user-provided data. If a `float` value crashed `int()`, search for every `int()` on external data. This takes 60 seconds and typically doubles the finding count. Write chaos tests for each additional instance found.
4. Fix ALL instances (not just the one that crashed) in a single commit
5. If a mechanical pass should have caught the combination, write `pass_debt[]` (`why_missed` names it)
6. Verify all chaos tests pass after the fix

**The Carmack escalation is not optional.** Every crash is evidence of a pattern. A single instance is a bug; two instances are a systemic gap. The escalation grep is how you find out which one you're dealing with. If you skip it, you'll find the same class of bug on the next Chaos run.

When a chaos test passes (no crash): it's still valuable — it proves the code handles that input. Keep it.

### Property-based chaos (Hypothesis)

If the project's language supports property-based testing (Python: `hypothesis`, JS: `fast-check`, Rust: `proptest`), use it to auto-generate chaos inputs instead of hand-writing every case.

**Strategy:** For each public function, define the input space by type, then let the property-based engine explore it:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(raw=st.text(min_size=0, max_size=10000))
@settings(max_examples=200)
def test_chaos_parser_hypothesis_any_string(raw):
    """parse_address must not crash on any string input."""
    result = parse_address(raw)
    assert isinstance(result, ParsedAddress)

@given(rows=st.lists(
    st.fixed_dictionaries({
        "raw_address": st.one_of(st.text(), st.none(), st.integers()),
        "raw_name": st.one_of(st.text(), st.none()),
    }),
    min_size=0, max_size=50,
))
@settings(max_examples=100)
def test_chaos_batch_hypothesis_any_rows(rows):
    """normalize_batch must not crash on any list of dicts."""
    result = normalize_batch(rows)
    assert isinstance(result, NormalizationResult)
```

**When to use Hypothesis vs. hand-written chaos:**
- Use Hypothesis for "must never crash on any input of type X" properties
- Use hand-written tests for specific real-world garbage patterns (BOM markers, carrier data quirks) that Hypothesis won't naturally generate
- Both are permanent test suite members

**Do NOT add hypothesis to project dependencies.** Use it if already installed; otherwise, wrap in `pytest.importorskip("hypothesis")` so chaos tests run without it (just the hand-written ones).

### Production-shaped sequences (mandatory when the surface exists)

If the repo has a pipeline, orchestrator, or state machine, these cases are **required**, not extras. Assert no-crash / right exception / graceful degradation only — not output values for garbage.

- **Wrong order of otherwise-valid steps** — call step 2 then step 1; call close then write; skip an intermediate step the happy path always runs.
- **Partial success then failure** — first N items succeed, item N+1 raises; the batch must not corrupt committed state or double-apply the successes.
- **Empty-then-large** — empty batch (or empty input) followed by a large valid batch; no stale counters, caches, or skip counts.
- **Double-submit under the real state machine** — same `batch_id` / same transition fired twice; second call is idempotent or rejected, never a corrupt half-state.

Individual function chaos tests miss bugs that only appear when modules interact. Also feed adversarial inputs at the pipeline entry point and verify the full chain survives:

```python
def test_chaos_pipeline_garbage_through_full_chain(self):
    """Adversarial input through parse -> normalize -> validate."""
    raw = "\x00﻿123 Main\tSt \U0001f3e0, Springfield, IL 62701"
    parsed = parse_address(raw)
    normalized = normalize_address(parsed)
    validate_address(normalized)
    # No crash through the full chain
    assert normalized.ag_validation_status in ("valid", "warning", "error", "")
```

For batch orchestrators, feed mixed garbage rows and verify the batch completes with correct skip/success counts — don't just test that it "doesn't crash," test that valid rows in the same batch still produce correct output despite surrounding garbage.

### Stateful chaos

Single-call tests miss bugs caused by operation sequences. Test:

- **Double-call:** Call `normalize_batch` twice with the same `batch_id` — does the second call produce identical results? (Idempotency)
- **Re-validation:** Call `validate_address` on an already-validated address — does it produce the same status and scores? (No accumulated state)
- **Cache interference:** Call `clear_comparison_caches()` between two `group_addresses` calls — does the second call still produce correct groups? (Cache rebuild)
- **Interleaved batches:** Process batch A, then batch B, then batch A again — does A produce identical results both times? (No cross-batch contamination)

The invariant: every public function must produce identical output for identical input regardless of what happened before.

### Resource exhaustion bounds

Current chaos tests check "doesn't crash." These check "doesn't hang."

For each public function, identify the input dimension that drives computation cost (string length, list size, nesting depth) and test at the adversarial extreme with a timeout:

```python
import signal

def test_chaos_comparator_timeout_long_strings(self):
    """Jaro-Winkler on 50K-char strings must complete in <5 seconds."""
    a = _addr(ag_street_name="A" * 50000)
    b = _addr(ag_street_name="B" * 50000)
    
    def handler(signum, frame):
        raise TimeoutError("Comparison took >5 seconds")
    
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(5)
    try:
        result = compare_addresses(a, b)
        assert isinstance(result.score, float)
    finally:
        signal.alarm(0)
```

Use `pytest.mark.timeout(seconds)` if the `pytest-timeout` plugin is available. Otherwise, use `signal.alarm` (Unix only) or skip on Windows.

Targets: Jaro-Winkler on long strings, `group_addresses` on large batches, `parse_address` on deeply nested multi-line input, `normalize_name` on very long names.

### Roundtrip integrity

Test that the pipeline is idempotent: processing output through the pipeline again produces the same result.

```python
def test_chaos_roundtrip_parse_normalize_reparse(self):
    """Re-parsing a normalized address's raw_input should produce
    compatible output (not necessarily identical, but no crash and
    key fields stable)."""
    original = parse_address("123 N Main St, Springfield, IL 62701")
    norm1 = normalize_address(original)
    
    # Re-parse the raw input
    reparsed = parse_address(norm1.ag_raw_input)
    norm2 = normalize_address(reparsed)
    
    # Key grouping fields must be stable
    assert norm1.ag_primary_number == norm2.ag_primary_number
    assert norm1.ag_street_name == norm2.ag_street_name
    assert norm1.ag_zip_code == norm2.ag_zip_code

def test_chaos_roundtrip_to_dict_from_dict_grouping_stable(self):
    """Serialize -> deserialize -> re-compute must produce same group key."""
    addr = normalize_address(parse_address("456 Oak Ave, Chicago, IL 60601"))
    key1 = addr.address_group_key()
    
    restored = NormalizedAddress.from_dict(addr.to_dict())
    key2 = restored.address_group_key()
    
    assert key1 == key2
```

Roundtrip failures reveal implicit state that doesn't survive serialization — the most dangerous kind of bug in distributed systems where addresses are stored in Fabric and restored later.

### Return to Pass 8b

After Chaos fixes land, return to **Pass 8b** ([passes-1-11.md](passes-1-11.md)) to re-run coverage and confirm every Carmack (Pass 12) and Chaos (Pass 13) fix has a regression test — then proceed to Pass 14.

---

## PASS 14: MAINTAINABILITY AND CONSISTENCY

This is the closing synthesis pass. It translates the evidence from passes 1-13 into a judgment about how easy the code is to reason about and how safely it can be changed.

**Do not run this pass early.** Maintainability judgments made before the deep passes are usually just taste. Run this pass after Pass 13, using the findings ledger, pass debt, hot-spot history, coverage output, and direct rereads of the highest-risk modules.

**14.1 Evidence base**

- Re-read modules with repeated findings, pass debt, or unusually high integration density.
- Re-read modules touched by earlier passes where a small change required disproportionately wide test setup or fixture churn.
- Use the project's tests, docs, and tooling config as evidence of its actual conventions and change surface.

**14.2 Score the repo on six criteria**

1. **Standards and style discipline** — One visible set of conventions, little drift, and few special-case idioms.
2. **Module boundaries and dependency direction** — Responsibilities are separated and interfaces stay narrow.
3. **Local reasoning cost** — A reader can understand a unit without mentally simulating half the codebase.
4. **Typed or validated data contracts** — State shape is explicit at boundaries, not hidden in loose dicts or magic strings.
5. **Testability and change safety** — Small changes can be verified with focused tests instead of broad end-to-end scaffolding.
6. **Operational and documentation consistency** — Runtime behavior, logs, scripts, and docs agree on the contract.

**14.3 Grade guidance**

- **A** — Conventions hold consistently, hot spots are isolated, and local changes stay local.
- **B** — Good discipline overall, but a few concentrated modules still impose high reasoning cost or broader-than-ideal edits.
- **C** — Repeated drift, broad integration hubs, or weak contracts make normal changes riskier than they should be.
- **D/F** — Routine modifications are unsafe without whole-system context, or the codebase has no stable internal contract.

**Every sub-A grade (B–F) requires at least one concrete past or future change that would force whole-system context.** No grade without that sentence. "Feels messy" is not a grade. Letter grades are supporting evidence; the **release judgment** (release-ready / releasable-with-debt / not-yet) is the primary output of this pass.

**14.4 Findings bar**

- A maintainability finding must describe a concrete change-risk, reasoning burden, or drift risk.
- "I would have designed this differently" is not a finding.
- Multi-concern integration hubs, repeated dict-shaped payload seams, duplicated invariants, or stringly typed contracts count only when you can describe the concrete maintenance failure mode.

**14.5 Severity guidance**

- **P1** — Concentrated change-risk or contract ambiguity likely to cause real regressions during normal modification.
- **P2** — Local inconsistency or duplicated invariant with clear debugging or drift cost and a safe local fix.
- **P3** — Style preference or large refactor idea. Do not fix.

**14.6 Fix policy**

- Fix only behavior-preserving, local maintainability defects: align repeated validation paths, replace stringly or dict-shaped transport with an existing typed model, extract a small internal helper inside the same module, remove dead branches that obscure the active contract, or tighten docs/tests to the real behavior.
- If the clean fix requires splitting modules, moving public surfaces, introducing new architecture, or changing user-visible behavior, defer it and say why.
- Pass 14 is allowed to end with deferred findings only. The goal is an honest maintainability judgment, not a forced rewrite.

**14.7 Required output**

- **Primary:** release judgment — release-ready as-is, releasable with deferred maintainability debt, or not yet releasable because maintainability risks are still concrete blockers.
- Supporting: three grades (`Consistency`, `Maintainability`, `Overall`). Each sub-A grade names the concrete change that would force whole-system context.
- Name the top hot spots with a one-line rationale for each.
