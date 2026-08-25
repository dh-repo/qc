# Structural Audit — Sub-Audit Reference

Deterministic codebase analysis. No LLM required. Detects stubs, dead code, dangling references, duplication, type coverage gaps, and unused dependencies using static tooling only.

## S1 — Stub Detection

Scan for unfinished implementation markers in non-abstract code paths:

**Python patterns:**
- `TODO`, `FIXME`, `HACK`, `XXX` in comments
- `raise NotImplementedError` outside abstract methods
- `pass` as sole body of non-abstract, non-protocol method
- `...` (Ellipsis) as sole body of non-protocol, non-TYPE_CHECKING method

**Not flagged:** `abc.abstractmethod` stubs, `typing.Protocol` stubs, `TYPE_CHECKING` blocks, test fixtures with intentional empty setup.

**Severity:** P1 if in production path (P0 if the stub is an unimplemented method reachable at runtime), P3 if test-only.

## S2 — Dead Code and Dangling References

Build full import graph via AST parsing. Cross-reference for:

- **Orphan exports:** in `__all__` but never imported
- **Orphan definitions:** public functions/classes with zero external consumers
- **Broken imports:** import statements referencing symbols that don't exist
- **Shadowed imports:** same name imported from two modules in one file

**Tools:** `vulture` (Python) as secondary check. Deduplicate by location.

**Exceptions:** Entry points (`@app.route`, CLI commands, `if __name__`) are terminal consumers, not dead code. `__init__.py` re-exports are valid consumers.

**Severity:** P0 if broken import (crashes at import time), P2 otherwise.

## S3 — Duplication Detection

AST-level clone detection for semantically equivalent code blocks.

**Classification:**
- **Exact clones:** identical token sequences → always flag
- **Parametric clones:** same structure, different variable names → flag if 3+ occurrences
- **Semantic clones:** different structure, same behavior → flag if matching test profiles

**Key check:** Does a shared utility already exist that does this? If yes → P1 (extraction target exists but unused). If no → P2 (extraction candidate).

**Threshold:** 6+ lines duplicated 2+ times, or 3+ lines duplicated 3+ times.

**Exceptions:** Test setup code intentionally duplicated for isolation. Framework boilerplate.

## S4 — Type Coverage

Run `mypy --strict` (Python) or `tsc --strict` (TypeScript).

**Flag:**
- Public function without full type annotations: P2
- `Any` as parameter or return type (outside genuinely dynamic contexts): P2
- `# type: ignore` without explanatory comment: P1
- Type errors from checker: P0

**Floor:** 95% type coverage on production code. Ratchet — can only go up.

## S5 — Unused Dependencies

Compare dependency manifest against actual imports:

1. Parse `pyproject.toml` / `package.json` dependencies
2. Build set of all imported packages across codebase
3. Map package names to importable module names (e.g., `Pillow` → `PIL`)
4. Flag packages with zero matching imports

**Exceptions:** Build/dev tools (pytest, mypy, ruff), entry-point plugins, transitive dependencies.

**Severity:** P3 (cleanup candidate).
