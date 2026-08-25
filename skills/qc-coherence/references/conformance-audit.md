# Conformance Audit — Sub-Audit Reference

Verifies every abstract interface, protocol, and base class has complete concrete implementations. Generalizes the conformance suite pattern proven on RunStateStore/FabricSQLStore into a universal protocol-implementation matrix.

## Phase 1 — Discovery

### Find All Interfaces

**Python:**
- Classes inheriting from `abc.ABC` or using `abc.abstractmethod`
- Classes inheriting from `typing.Protocol`
- Classes with `__subclasshook__`
- Classes documented as interfaces (docstring contains "interface", "protocol", "contract")

For each interface, extract: all method signatures, property declarations, class-level attributes.

### Find All Implementations

For each interface, find concrete classes that:
- Explicitly inherit/implement it
- Are registered via `register()` (ABCs)
- Structurally conform (duck typing — match Protocol signature without explicit inheritance)

### Build the Conformance Matrix

```
                    | MethodA | MethodB | MethodC | PropX |
---------------------------------------------------------
Interface Def       |  sig    |  sig    |  sig    | sig   |
ConcreteImpl1       |  YES    |  YES    |  MISSING|  YES  |
ConcreteImpl2       |  YES    |  STUB   |  YES    |  YES  |
```

Cell statuses:
- **YES** — method exists with matching signature
- **MISSING** — method does not exist. P0 if the implementation is deployed, P1 otherwise.
- **STUB** — method exists but body is stub. P1.
- **SIGNATURE-MISMATCH** — method exists but types differ. P1.
- **PARTIAL** — method exists but missing error handling the contract specifies. P2.

## Phase 2 — Verification

### Static Verification

For every non-YES cell: file a finding with severity based on status.

### Behavioral Verification

For every interface with 2+ implementations: verify parameterized conformance test exists covering ALL implementations. If an implementation was added but not included in the test parameter list → P1 finding.

If no conformance test exists → P1 finding. Generate test skeleton as remediation artifact.

### Drift Guard

For interfaces that pass today, emit a drift guard test:

```python
def test_interface_method_count(implementation):
    """Fails when interface gains methods not on impl."""
    interface_methods = get_public_methods(InterfaceName)
    impl_methods = get_public_methods(type(implementation))
    missing = interface_methods - impl_methods
    assert not missing, f"Missing: {missing}"
```

## Output

```
C[n] [severity] CONFORMANCE
Interface: [name] ([file:line])
Implementations: [count]
Matrix gaps: [count]
  [ImplName].[method]: [MISSING|STUB|SIGNATURE-MISMATCH]
Conformance test exists: [YES path:line | NO]
Drift guard exists: [YES path:line | NO]
```
