## PASS 1: CORRECTNESS

Logic errors in production are the most expensive defects. **Composition is the main lens.** Sequence-level correctness, dual-path API parity, complete field population, classification completeness, and I/O coercion on every ingest path are the checks that catch the defects Carmack later finds. Isolated pure-function bugs are the easy residual. A Pass 1 that only reads functions in isolation is incomplete.

**1.1 Test suite gate** — Run the full suite. Fix failing code (not tests) unless the test is provably wrong. If fixing a test, add a comment explaining why the original assertion was incorrect.

**Pass 1 is a deep-read pass.** Like Carmack (Pass 12), its quality degrades with context size. In chunked mode, dispatch per module group: audit manifest, CLEAN lists, untested-line priority, live I/O first. Profile hot spots and `pass_debt[]` modules for Pass 1 are mandatory extra attention, not optional.

**1.2 Sequence-level audit (primary)** — For every pair of functions that touch the same file, shared state, or resource within a module:

- **Write-then-read ordering:** If function A writes to a resource and function B reads it, verify B runs *after* A. If both can run in the same loop iteration, verify the ordering is enforced, not coincidental. Example: `_write_state()` before `_check_stop_signal()` on the same file — if write runs first, it can erase data that check needs to read.
- **Read-modify-write atomicity:** If a function reads a file/dict, modifies it, and writes it back, check what happens if another function writes to the same target between the read and the write.
- **Cleanup-on-all-paths:** If function A allocates a resource (temp file, lock, connection) and function B releases it, verify B runs on *every* exit path from A — including exceptions, early returns, and loop breaks.

**1.3 Dual-path API parity (primary)** — For every pair of public functions that serve the same data through different paths (e.g., a normalize-only orchestrator and a full-pipeline orchestrator), verify they accept the same metadata parameters and populate the same output fields. A parameter or field present on one path but missing from the other is a P1 finding. Common misses: lineage identifiers (`batch_id`), metadata stamps (`carrier`, `source_file`), and output fields (`row_number`, `fix_hint`) that one code path populates and the other silently leaves as defaults.

**1.4 Field population of every output type (primary)** — For every output dataclass, verify that every field is actually populated by every code path that constructs it. The check: if a field has a default of `None`, `""`, or `[]`, trace every constructor call site and confirm the field is set. A field that defaults to empty and is never set by any code path is either intentionally optional (documented as such) or a latent bug. Pay special attention to fields populated by helper functions — verify the helper is actually *called*, not just *defined*.

**1.5 Classification completeness (primary)** — When code uses a set, enum, or mapping to classify items into categories (e.g., "which signals apply to which address types"), verify the classification is *complete*. For every item that *could* be in the set, confirm it either is or has an explicit reason not to be. Incomplete classification sets are invisible to function-level audits because the code that reads the set works correctly — the bug is in *what the set contains*, not in *how the set is used*.

**1.6 I/O coercion on every ingest path (primary)** — At every boundary where external data enters the system (file readers, API responses, deserialization), trace the type of each value from the source format (CSV string, Excel cell, JSON field) through to its first use. Verify that type cleaning/coercion functions are called on *every* ingestion path, not just the primary one. Common miss: a utility function like `_clean_cell_value()` exists and is tested, but is only called from one of three file-reading functions.

**1.7 Isolated function-level residual** — After the composition lenses, read remaining functions for local bugs (easy residual, not the main pass):

- **Return paths:** None/null/undefined where a value is expected? Fall-through without explicit return?
- **Conditionals:** Unreachable branches? Inputs matching no branch? Inverted logic?
- **Loops:** Runs zero times when it shouldn't? Infinite loop? Empty collection handling?
- **Strings:** None/null concatenation, encoding assumptions, empty string edges, format string mismatches.
- **Numerics:** Division by zero, integer overflow, float equality without epsilon, off-by-one.
- **Collections:** Access without containment check, mutation during iteration, empty-where-non-empty-assumed.
- **Type coercion:** Implicit conversions that lose precision or change semantics.

**1.8 Regression tests** — For every fix, write a test that would have caught the defect. After every fix, grep other backends and dual paths for the same pattern (see Cross-Backend Awareness).

---

## PASS 2: SECURITY

Runs early — secrets and injection are higher-severity than missing error handling. Apply OWASP Top 10 thinking.

**2.1 Secrets audit**

- Grep everything (code, comments, tests, Dockerfiles, CI) for: `password\s*=`, `secret\s*=`, `api_key`, `token\s*=`, `-----BEGIN`, `AKIA`, `sk-`, `ghp_`, `Bearer `, base64 blobs in config.
- Verify `.gitignore` covers `.env`, `*.pem`, `*.key`, credentials files, IDE workspace files.
- Check git history: `git log --all -p -- '*.env' '*.pem' 'local.settings.json'`. Previously committed secrets = P0 (rotation required).
- Check Dockerfiles for secrets in build args, ENV, or COPY.

**2.2 Injection audit** — For each user-facing input, trace data flow:

| Vector | Check |
|--------|-------|
| SQL | Parameterized queries everywhere? No `f"SELECT ... {var}"`? |
| Command | No `shell=True` with unsanitized input? No string-concat commands? |
| Path traversal | User input in file paths canonicalized? `../` blocked? |
| Template | User content escaped? No `\| safe` on user data? |
| SSRF | User-supplied URLs allowlisted before server-side fetch? |
| Deserialization | No `pickle.load()`, `yaml.load()` (without SafeLoader), eval or exec on untrusted data? |
| Log injection | User input in logs sanitized? Newlines that forge entries? |

**2.3 Dependency security**

- Lockfile committed and not stale?
- Run the ecosystem's audit tool (`pip-audit`, `npm audit`, `cargo audit`, `govulncheck`) — match what CI runs if applicable. Run ad-hoc (`pipx run pip-audit`), do not add to deps.
- Known CVE with fix available = P1. Known CVE with no fix = P2.

---

## PASS 3: ERROR HANDLING AND RESILIENCE

Production systems fail at boundaries.

**3.1 Boundary inventory** — Enumerate every external boundary:

| Boundary | Examples | Required handling |
|----------|----------|-------------------|
| File I/O | `open()`, `pathlib.read_text()` | FileNotFoundError, PermissionError, IsADirectoryError, **UnicodeDecodeError** (from `read_text(encoding=...)` — inherits from `ValueError`, NOT `OSError`, so `except OSError` will NOT catch it) |
| Network | HTTP clients, SDK calls, gRPC | Timeout, connection refused, DNS, 4xx/5xx |
| Database | Queries, transactions, pools | Connection lost, deadlock, constraint violation |
| User input | CLI args, forms, API bodies | Validation before use |
| Environment | `os.environ`, config files | Missing key with actionable error message |
| Subprocess | `subprocess.run()` | Non-zero exit, timeout, stderr capture |
| Deserialization | JSON/YAML/CSV parsing | Malformed input, missing fields, wrong types |

**3.2 Audit each boundary:**
- Explicit error handling? Bare `except:` / empty `catch` = P1.
- Diagnostic error messages? (include file path, operation, cause — not just "Error").
- Recoverable state after partial failure? (temp+rename for files, context managers for transactions).
- Timeout on every network and subprocess call? No timeout = potential hang = P1.

**3.3 Resource lifecycle** — File handles via context managers? Connections returned to pool on all paths? Temp files cleaned up? Background tasks cancellable?

**3.4 Data validation and schema integrity**
- API responses: expected fields checked before access? Handles missing/extra/wrong-type fields?
- Serialized data from older versions: deserialization handles schema drift (missing/renamed/changed-type fields)?
- External contracts: API clients that break silently if upstream response shape changes?

---

## PASS 4: TYPE SAFETY AND CONTRACTS

**4.1 Static analysis** — Run the type checker from the toolchain matrix. Fix all errors. If the project has no type annotations and the checker produces only noise, skip with a note in the summary.

**4.2 Contract audit**
- Return types match all return paths? Optional/nullable marked correctly?
- Public API functions validate inputs? (Internal functions called from validated contexts don't need redundant checks.)
- Dataclass/model defaults: `field(default_factory=list)` not `field(default=[])`?
- Enum consistency: raw literals used where an enum is defined?

**4.3 Linter** — Run the linter from the toolchain matrix. Fix all errors. Fix warnings only if trivially safe. **Format-check scoping:** If `ruff format --check` (or equivalent) flags the entire codebase but the project has never used autoformatting, this is a pre-existing style choice, not a hardening finding. Only fix formatting in files *you* changed during this run. Do not reformat the whole codebase — that creates a massive diff that obscures real fixes and breaks `git blame`. If the project's CLAUDE.md or ruff config explicitly enables formatting, follow that.

---

## PASS 5: CONCURRENCY AND ASYNC CORRECTNESS

**Skip if Pre-Flight detected no concurrency signals.**

**5.1 Shared state** — All mutable state accessed from multiple threads/tasks has explicit synchronization? Lock ordering consistent? Lock scope minimal (no I/O under lock)?

**5.2 Async correctness** — No blocking I/O in async code paths? No missing `await`? Cancellation handled? Async-safe pools with exhaustion handling?

**5.3 Race conditions** — Check-then-act without atomicity? Read-modify-write without sync? Assumed ordering without enforcement?

---

## PASS 6: PERFORMANCE AND SCALE

Do not micro-optimize. Focus on algorithmic and I/O issues with concrete evidence.

**6.1 Algorithmic** — O(n^2)+ on growable collections? Repeated linear searches (use set/dict)? String concat in loops (use join)? Redundant expensive computation (compute once or memoize)?

**6.2 I/O** — N+1 queries? Row-by-row where bulk works? Unbounded `file.read()` / `SELECT *`? New HTTP client per request?

**6.3 Memory** — Unbounded list/dict growth in long-running processes? Large object retention past need? Full list where generator suffices?

---

## PASS 7: LOGGING AND OBSERVABILITY

Production code must be debuggable without a debugger.

**7.1 Error logging** — Every caught exception logged (or intentionally suppressed with a comment explaining why)? `except SomeError: return default` without logging = P2. Error logs include operation, identifiers, and exception details? Correct log levels (warning=recoverable, error=needs attention, critical=service-impacting)?

**7.2 Sensitive data in logs** — Secrets/PII in log output? (Cross-reference patterns from Pass 2.1.) Auth headers or session tokens in logged request/response bodies? User PII (emails, IPs) = P2 with compliance note.

**7.3 Log hygiene** — Ad-hoc `print()` in production code = P2 (use the project's logger). Long-running operations (batch processing, external API calls) log start/end with elapsed time? **CLI tool exemption:** If the project is a CLI tool (detected by `[project.scripts]` in `pyproject.toml`, `argparse`/`click` usage, or CLAUDE.md describing it as a CLI), `print()` in the main entry point and user-facing output paths is intentional, not a finding. Only flag `print()` in library/utility modules that should use the project's logger instead. Similarly, `print(..., file=sys.stderr)` for operational logging in scheduler/daemon code is acceptable when the project has no structured logger configured.

---

## PASS 8: TEST COVERAGE GAPS

This pass writes tests only. No production code changes. **Runs twice** — once here (8a) for functional coverage, and once after passes 12-13 (8b) to verify deep-pass fixes have tests.

### 8a: Functional coverage (runs here, before deep passes)

**8a.1 Coverage analysis** — Run the coverage tool from the toolchain matrix. If unavailable, manually trace untested functions/branches.

**8a.2 Priority targets** (in order):
1. Core modules below 80% — focus on specific missing lines, not hypotheticals.
2. Error paths at external boundaries (file not found, timeout, malformed input).
3. Edge cases for core business logic (empty, single, max, boundary).
4. Branches never exercised (`--show-missing` line numbers).
5. Code paths added during earlier hardening passes (1-7).

**8a.3 Test placement** — Use the existing test file closest to the module under test, following project conventions. Only create a new file if none exists.

**8a.4 Test quality** — Deterministic (no uncontrolled time/random/network)? Isolated (no leaked state)? Assertions check return values, not just "no exception"? No `sleep()`-based timing?

**8a.5 Re-run full suite.** All tests must pass.

### 8b: Post-deep-pass coverage (runs after passes 12-13)

After Carmack and Chaos have found and fixed bugs, re-run coverage:

**8b.1** Run coverage again. Compare to 8a baseline.

**8b.2** Check that every Carmack fix (pass 12) has a regression test. If Carmack found a bug and fixed it but no test covers the fix, write one.

**8b.3** Verify Chaos tests (pass 13) actually cover the crash paths they were designed for. Run coverage on `test_chaos.py` alone to confirm.

**8b.4** Report final coverage in the summary. The summary should show both 8a and 8b numbers.

---

## PASS 9: DOCUMENTATION ACCURACY

Documentation that disagrees with code is worse than no documentation.

**9.1 Docstrings** — Match what the function does? Parameters, return values, exceptions match actual behavior? **Fix docs to match code, not the reverse.**

**9.2 README** — Every command runs? Every file reference exists? Config docs match actual config loading? Architectural claims still true?

**9.3 Inline comments** — Contradicts code → fix or remove. Resolved TODO/FIXME → remove. Commented-out code → remove (it's in git).

---

## PASS 10: BACKWARD COMPATIBILITY

**Skip if Pre-Flight detected no public API surface** (standalone app, no library consumers, no external integrations).

**10.1 Public API surface** — Identify all exports (library functions, endpoints, CLI args, event schemas, serialization formats). Diff against starting commit. If any hardening pass changed a public signature, return type, error type, or serialized field name — revert or fix.

**10.2 Behavioral contracts** — Run integration/contract tests if they exist. Verify error types/codes returned to callers are unchanged. If the project has versioned APIs, verify behavior is unchanged per version.

**10.3 Validation permissiveness** — If a hardening pass added input validation that didn't exist before, ensure it doesn't reject inputs that production currently sends. Default to permissive where existing behavior was permissive.

**10.4 Self-check: hardening-induced compat breaks** — Review the diff from the starting commit to now (`git diff <starting_commit>..HEAD`). If any hardening fix changed an error type (e.g., `ValueError` to `SystemExit`), return code, or exception message format that callers or scripts might depend on, flag it. Hardening should not change the contract observed by external callers — if it does, the fix needs a compatibility shim or the change needs explicit documentation. Common offenders: wrapping bare exceptions in `parser.error()` (changes the exit path from traceback to clean exit), adding `ImportError` guards (changes the error from `ModuleNotFoundError` to `SystemExit(2)`), tightening type checks that previously returned `None` silently.

---

## PASS 11: ENVIRONMENT, CONFIG, AND BUILD INTEGRITY

**11.1 Environment variables**
- Grep for all env var reads (`os.environ`, `os.getenv`, `process.env`).
- Cross-reference against `.env.example` and docs. Referenced but undocumented = P2.
- Missing var produces a `KeyError` in production = P1. Unsafe default (e.g., `DEBUG=True`) = P0.

**11.2 Config loading** — All config keys documented? Stale keys in docs that code no longer reads? Config typos produce clear errors, not silent misbehavior?

**11.3 Dependency integrity** — Lockfile committed and not stale? All manifest deps actually imported? All imported deps in manifest? Dev/test deps separated from production?

**11.4 CI alignment** — Local test command matches CI (same flags, discovery, linter config)? All CI steps pass locally? Missing CI steps (lint, type check, test)?

**11.5 Container audit (if applicable)** — Specific image tags (not `:latest`)? Multi-stage build? No secrets in Dockerfile? `.dockerignore` excludes `.git`, `.env`, `node_modules`, `__pycache__`? Non-root user? Health check?

---

## Cross-Backend Awareness

When fixing a defect in one backend implementation, check whether the same pattern exists in alternative backends. This is a mandatory step for Passes 1 and 12.

**After every fix (escalation loop):**
1. Identify the pattern (e.g., missing rollback, LIMIT/OFFSET syntax, missing `_closed` guard)
2. Grep for the same pattern in all other store implementations and dual paths
3. If the same pattern exists elsewhere, fix all instances in the same commit
4. If a conformance test exists, verify it passes for all backends
5. If a mechanical pass should have caught this **combination**, write `pass_debt[]` with `why_missed` naming that combination

This step was added after Run 22 found two P0s (`LIMIT/OFFSET` invalid T-SQL, missing `rollback()`) that existed only in `FabricSQLStore` because fixes applied to the SQLite stores were never cross-checked against the alternative backend.
