# Architectural Audit — Sub-Audit Reference

Enforces architectural invariants: dependency direction, layer boundaries, module responsibility, and documented constraints. Turns design decisions into executable tests that break when violated.

## A1 — Dependency Direction

Modules should only import in permitted directions. Lower layers must not import from higher layers.

**Method:**
1. Define or discover the layer hierarchy. If documented (README, ADR, design doc), extract it. If not, infer from the import graph (module with most inbound/fewest outbound imports is likely core). Flag missing documentation as P2.
2. Build full import graph (reuse from structural audit)
3. Classify every import edge:
   - **Permitted:** higher layer imports lower layer
   - **Lateral:** same-layer import (acceptable, track if excessive)
   - **Upward:** lower layer imports higher layer — VIOLATION
   - **Circular:** A imports B and B imports A — VIOLATION
4. For violations: is it a `TYPE_CHECKING`-only import? Runtime violation is P1, TYPE_CHECKING-only is P2.
5. **Write `layer_model`** on `.qc-profile.json`: `layers` (ordered) + `rules` (permitted directions). Later A1 runs diff the import graph against this model and only re-flag regressions. If a prior `layer_model` exists, do not re-infer from scratch unless the graph grew a new top-level package.

**Enforcement:** If `import-linter` is available, generate declarative rules for CI.

## A2 — Layer Boundary Enforcement

Each architectural layer should have a clear boundary — a defined public API.

**Method:**
1. For each package: identify public API (`__init__.py`, `__all__`) vs internal implementation (`_` prefixed, not in `__all__`)
2. Scan cross-module imports for:
   - Direct access to internal implementation across boundaries
   - Bypassing `__init__.py` to import submodules directly
3. Domain/core layer specifically: verify zero imports from infrastructure, adapters, or framework code (`import sqlalchemy`, `import requests` in domain code = violation)

**Severity:** P1 if infrastructure in domain, P2 otherwise.

## A3 — Module Responsibility

Each module should have a single, coherent responsibility. Directly relevant to SI-2.1 (`fabric_sql.py`) and SI-2.2 (`run_state.py`).

**Method:**
1. For modules over 500 LOC: count public symbols, import fan-in, import fan-out (measurable first half)
2. LLM-assisted: classify each public function/class into responsibility domains (data access, validation, serialization, business logic, coordination)
3. If 2+ distinct domains present: flag as mixed responsibility. **Write `clusters[]`:** the symbols in each domain + `rationale` for why they are unrelated. The LOC/fan-in numbers are the first half; "unrelated" is the second half and must sit in `rationale`, not in implicit judgment.
4. Determine: is a split feasible without changing public API? Does it need a design spec? If the fix is a split, defer `needs-module-split` — do not execute the split inside this audit.

**Severity:** P2 (structural debt). Modules over 1200 LOC with 5+ tables = P1.

## A4 — Documented Invariants as Tests

Every documented architectural constraint should have a corresponding test.

**Method:**
1. Scan for documented invariants: comments with "invariant", "must", "always", "never", "constraint", "ordering", "guarantee", "assumes", "requires". README architecture sections. ADR files. Class/module docstrings.
2. Classify: testable statically (imports, naming), testable at runtime (ordering, concurrency), not directly testable (rationale only)
3. For testable invariants: search for enforcing test. Flag if missing.
4. **Harvest into profile `invariants[]`** (`source: comment` or `source: test`). Also load Carmack-harvested rows (`source: carmack`). This run: any registry row with `status: untested` and a testable invariant is a finding (same bar as a missing test). Do not mint a second id for the same statement. Mark `enforced` only with `enforced_by` pointing at a real test.

Directly relevant to SI-3.2 (lock ordering documented as invariant but only in docstring, not in test).

**Severity:** P1 if runtime invariant without test, P2 if static.

## A5 — Cross-Cutting Concern Consistency

Cross-cutting concerns should be implemented consistently. This is still A5 — not a new sub-audit and not an observability product pass.

**Method:**
1. Identify patterns: logger, format, levels; auth (decorator vs middleware); retry (strategy, backoff, trigger exceptions); transactions (boundary placement).
2. Also check, as consistency problems:
   - **Logging field shapes and correlation IDs** — same request id field name and type across modules
   - **Config/env key naming** — same concept, same key (not `RUN_ID` vs `EXECUTION_ID`)
   - **Error-propagation patterns** — equivalent failures raise equivalent types (ties to M2)
   - **Capability / feature-flag discovery** — flags discovered the same way, not a mix of env, hardcoded booleans, and missing checks
3. For each concern: is there a shared utility? Is it used everywhere, or do some modules roll their own?
4. Are parameters consistent? Same retry count, same log format, same cache TTL for equivalent operations.
5. Are there modules that should use the concern but don't?

Write accepted naming clusters to `canonical_forms[]`. **Severity:** P1 if auth/transaction inconsistency, P2 otherwise.

## Architectural Rule Generation

When the audit identifies patterns worth enforcing permanently, emit architectural rules as remediation artifacts (not auto-committed):

- `import-linter` contract definitions
- Custom pytest fixtures asserting structural properties
- Pre-commit hook configurations
- Linter rule configurations

Each rule references the finding that generated it and includes the invariant in a docstring.
