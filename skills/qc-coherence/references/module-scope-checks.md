# Module Scope Sub-Audits (--scope=module)

These six checks run when `qc-coherence` is invoked with `--scope=module`. They audit whether individual modules and their protocol implementations still compose correctly — a targeted lens that complements the codebase-wide sub-audits.

Finding IDs use the `MS-N.N` prefix (Module Scope). Severity uses the P0–P3 scale:
- **P0** — Actively broken; must fix before any feature work
- **P1** — Will break under realistic conditions; fix before next session
- **P2** — Increases maintenance cost; address in current cycle
- **P3** — Suboptimal but functional; log and track

---

## MS-1: Protocol Conformance Parity

**Question:** Do all backend implementations of the same protocol behave identically for identical inputs?

**How to audit:**

1. List every Protocol class and its methods.
2. For each Protocol, list every concrete implementation (e.g., `InMemoryShipmentStore`, `SQLiteShipmentStore`, `FabricSQLStore`).
3. For each method on each Protocol, check: does a conformance test exist that runs the same assertion against every implementation?
4. Check for methods that exist on one implementation but not the Protocol — these are leaking implementation details.
5. Check for methods added to the Protocol since the last audit that don't have conformance tests yet.

**Finding format:**

```
MS-1.N | Protocol | Method | Implementations | Conformance test exists? | Gap
```

**Severity:**
- **P0:** A Protocol method has no conformance test across backends. Backends will silently diverge.
- **P1:** A conformance test exists but only covers a subset of implementations.
- **P3:** Every Protocol method is tested across every implementation.

**Fix guidance:** Write the missing conformance tests. Do not change production code in this check — the goal is to detect drift, not fix it.

---

## MS-2: Responsibility Density

**Question:** Are any modules accumulating responsibilities that belong in separate units?

**How to audit:**

1. For each module over 500 LOC, list the distinct responsibilities it handles (by reading section comments, method groups, and table names it manages).
2. For each module, count:
   - Number of database tables it owns
   - Number of distinct Protocol interfaces it serves
   - Number of unrelated domain concepts (e.g., "run state" + "intelligence snapshots" + "pending events")
3. Flag modules where a single lock serializes access to multiple unrelated tables.
4. Check if the module's responsibilities have grown since the last audit.

**Threshold signals:**
- Module > 800 LOC with 3+ unrelated responsibilities: P1
- Module > 1200 LOC with 5+ tables behind one lock: P0
- Module where a new responsibility was added in the last 3 sessions: check if it belongs

**Finding format:**

```
MS-2.N | Module | LOC | Responsibilities | Tables | Recommendation
```

**Severity:**
- **P0:** A module has grown past the point where a reader can hold it in context. Split is overdue.
- **P1:** A module is accumulating but still manageable. Document the boundary for the next reviewer.
- **P3:** Each module has one clear purpose.

**Fix guidance:** Propose a split with specific module boundaries, but do not execute it. Structural changes require a design discussion, not an inline fix.

---

## MS-3: Coordination Surface

**Question:** Is the coordination logic (locks, gates, events, state machines) still comprehensible?

**How to audit:**

1. List every synchronization primitive in the codebase: `threading.Lock`, `asyncio.Lock`, `asyncio.Event`, `threading.Event`, semaphores, gates.
2. For each primitive, identify:
   - What state it protects
   - Which methods acquire it
   - Whether it's always acquired in the same order relative to other primitives
3. Map the state machine: what are the valid states, what transitions between them, and which methods trigger each transition?
4. Check for coordination patterns that have caused bugs before (from the hardening profile's pass debt table).
5. Count the number of distinct lock/gate/event interactions a developer must understand to safely modify the orchestration layer.

**Threshold signals:**
- 3+ synchronization primitives interacting in one module: P1 (document the interaction model)
- A coordination path that has produced 2+ hardening findings across runs: P0 (the pattern is too subtle to maintain safely)
- Any method that acquires locks in an order different from every other method: P0 (deadlock risk)

**Finding format:**

```
MS-3.N | Module | Primitives | Interaction | Risk | Recommendation
```

**Fix guidance:** Document the state machine and lock ordering as an inline comment or architecture doc. Simplify only if a concrete simplification is available without changing behavior.

---

## MS-4: Backend Parity

**Question:** Do alternative backend implementations (e.g., SQLite vs Fabric SQL) support the same feature set?

**How to audit:**

1. For each Protocol, list every public method on the Protocol interface.
2. For each concrete implementation, verify it implements every Protocol method.
3. Check for methods added to one implementation (e.g., SQLite `RunStateStore`) that aren't on the Protocol and aren't on alternative implementations. These are features that only work on one backend — a deployment-time surprise.
4. Check for SQL dialect assumptions: `LIMIT/OFFSET` vs `OFFSET/FETCH`, `ON CONFLICT` vs `MERGE`, `PRAGMA` vs `INFORMATION_SCHEMA`, `CREATE TABLE IF NOT EXISTS` vs `IF NOT EXISTS (SELECT FROM sys.tables)`.
5. Verify that serialization/deserialization helpers are shared (not duplicated) between implementations.

**Finding format:**

```
MS-4.N | Protocol | Method/Feature | SQLite | FabricSQL | Gap
```

**Severity:**
- **P0:** A Protocol method exists on one backend but not the other. Feature works in dev, breaks in prod.
- **P1:** Shared logic is duplicated rather than imported. Future changes will diverge.
- **P3:** All backends implement the full Protocol with shared serialization.

**Fix guidance:** Add missing methods to the lagging backend. Extract duplicated logic into shared helpers. Add conformance tests for the gaps found.

---

## MS-5: Cross-Session Consistency

**Question:** Have recent changes introduced patterns that prior hardening flagged as problems?

**How to audit:**

1. Read the hardening profile's pass debt table and hot spots.
2. For each pattern listed (e.g., "double-lock TOCTOU", "use-after-close", "missing rollback"), grep the current codebase for new instances of the same pattern.
3. Check whether external changes (visible in git log) touched modules that are documented hot spots.
4. For each new module added since the last audit, verify it follows the established patterns:
   - `from __future__ import annotations`
   - `_closed` guard on all public methods
   - Lock acquisition before any `_connection` access
   - `commit()` after every write
   - Error handling at boundaries
5. Check for regression in conventions: new files missing type hints, new tests missing builder functions, new modules with bare `except:` or `print()`.

**Finding format:**

```
MS-5.N | Pattern | Where found | Prior hardening finding | Risk
```

**Severity:**
- **P0:** A pattern that was fixed by hardening has been reintroduced in new code.
- **P1:** New code follows a slightly different convention than established code (but not a known-bad pattern).
- **P3:** New code is consistent with established patterns and avoids known-bad patterns.

**Fix guidance:** Fix reintroduced bad patterns immediately (they're proven bugs). For convention drift, add the finding to the hardening profile's pass debt table so the next hardening run catches it.

---

## MS-6: Test Architecture

**Question:** Is the test suite itself structurally sound, or is it accumulating its own maintenance burden?

**How to audit:**

1. List test files over 500 LOC. Flag any over 1,000 LOC.
2. Check for fixture duplication — are `_make_shipment()`, `_make_event()`, or similar builders defined in multiple test files instead of shared via `conftest.py`?
3. Check parameterization coverage — are conformance tests parameterized across all backends, or do some only cover a subset?
4. Check for test interdependence — do any tests rely on ordering or shared mutable state?
5. Verify that new production modules added since the last audit have corresponding test files.

**Finding format:**

```
MS-6.N | File/Pattern | LOC | Issue | Recommendation
```

**Severity:**
- **P0:** A test file exceeds 1,500 LOC or a production module has zero tests.
- **P1:** Fixture duplication across 3+ files, or a test file exceeds 1,000 LOC.
- **P3:** Tests are focused, fixtures are shared, parameterization is complete.

**Fix guidance:** Extract shared fixtures to `conftest.py`. Split oversized test files by domain. Add missing test files for uncovered modules.

---

## Accepted Debt Staleness

Every accepted debt entry in `.structural-integrity.md` must include a `Last reviewed: YYYY-MM-DD` date. On each module-scope audit:

1. Check the `Last reviewed` date on every accepted debt item.
2. If an item has not been reviewed in 30+ days, flag it as **STALE** (P1).
3. For stale items, re-evaluate: is the debt still acceptable, or has the codebase changed enough that the resolution path should be executed?
4. Update the `Last reviewed` date for items that are still valid.

Debt that sits unreviewed for 60+ days is automatically promoted from accepted debt to P1 — it must be actively re-accepted or resolved.

---

## Module Scope Output Format

When `--scope=module` is active, the coherence report gains a "MODULE SCOPE" section:

```
MODULE SCOPE RESULTS (--scope=module)
  MS-1 (Protocol Conformance Parity):  P0: _ P1: _ P3: _
  MS-2 (Responsibility Density):        P0: _ P1: _ P3: _
  MS-3 (Coordination Surface):          P0: _ P1: _ P3: _
  MS-4 (Backend Parity):                P0: _ P1: _ P3: _
  MS-5 (Cross-Session Consistency):     P0: _ P1: _ P3: _
  MS-6 (Test Architecture):             P0: _ P1: _ P3: _
```

Module-scope findings are included in the top-level FINDINGS list and affect the overall COHERENT / DRIFTING / ACTION REQUIRED verdict.
