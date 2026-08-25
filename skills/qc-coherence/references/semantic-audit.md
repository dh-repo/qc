# Semantic Audit — Sub-Audit Reference

LLM-assisted analysis of semantic consistency. Detects naming drift, error handling inconsistency, serialization gaps, and behavioral contract violations that static tools miss.

## M1 — Naming Consistency

Same domain concept must use the same name everywhere. `run_id` in one module and `execution_id` in another is semantic drift even when the code works.

**Method:**
1. Extract symbol table from structural audit's import graph
2. Cluster symbols by semantic similarity (LLM-assisted)
3. For each cluster, identify canonical name (most frequent or protocol-defined)
4. Flag variants that deviate
5. **Write the cluster to `.qc-profile.json` `clusters[]`:** `symbols` (every name in the cluster) + `rationale` (why they are the same domain concept). Without that artifact the finding is incomplete — later verification or a human must be able to audit the clustering itself.
6. **Write `canonical_forms[]`:** `concept`, `canonical` (most frequent or protocol-defined), `aliases`, `cluster_id`. Later Semantic runs load this as ground truth and only re-flag a new alias or a canonical regression. Do not re-derive the same cluster under a new id.

**Special attention to:**
- Function parameters accepting the same data with different names across modules
- DB column names vs Python attribute names vs API field names for the same entity
- Abbreviation inconsistency: `txn` vs `transaction`, `cfg` vs `config`

**Severity:** P2

## M2 — Error Handling Taxonomy

Equivalent error conditions should raise equivalent exception types.

**Method:**
1. Extract all `raise` statements. Build table: (module, function, condition, exception_type, message_pattern)
2. Cluster by condition semantics: invalid input, missing config, external failure, data integrity, permission, timeout
3. Check consistency within each cluster: same exception type? same message structure?
4. Check for missing error handling: external calls without try/except

**Severity:** P1 if missing handling, P2 if type inconsistency. Also write the error-type cluster to `canonical_forms[]` (concept = condition class, canonical = exception type).

## M3 — Serialization Round-Trip Integrity

`deserialize(serialize(x)) == x` must hold for all valid `x`.

**Method:**
1. Identify serialization boundaries: `to_dict`/`from_dict`, `to_json`/`from_json`, ORM models, API schemas
2. For each serializable class: does a round-trip test exist?
3. Verify structural compatibility: `to_dict` output keys match `from_dict` expected keys?
4. Check: optional field handling symmetric? enum values survive? datetime timezone handling correct?
5. For JSON-blob columns (relevant to FabricSQL's SI-4.2 pattern): is the JSON schema documented or enforced?

**Severity:** P1 if key mismatch or asymmetry, P2 if missing test.

## M4 — Behavioral Contract Consistency

Functions serving the same logical role across implementations should behave consistently under equivalent inputs.

**Method:**
1. For each interface with multiple implementations (from conformance matrix)
2. Identify behavioral contracts from: docstrings, existing tests, caller assumptions
3. Check all implementations handle: None/empty input, invalid input exceptions, return types, side effects
4. Where behavior diverges: is the interface underspecified or is an implementation wrong?

**Severity:** P1 if implementation bug, P2 if underspecified interface.

## M5 — Magic Values and Implicit Constants

Hardcoded values carrying domain meaning but not named or centralized.

**Method:**
1. Scan for literals in non-test code: strings in comparisons appearing in 2+ files, numeric literals in business logic, timeout/retry/batch values
2. For each repeated literal: is a named constant defined? Are all usages referencing it?
3. Status strings used as enum-like comparisons (`if status == "completed"` vs `if state == "done"`)
4. Repeated literals that are the same domain concept also write `canonical_forms[]`.

**Severity:** P2
