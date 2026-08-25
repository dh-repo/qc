#!/usr/bin/env python3
"""Machine-check a qc-hardening findings ledger.

Validates ``.qc-findings/qc-hardening.json`` against the shared qc-finding schema
and recomputes the release verdict with the canonical qc-all rollup algorithm,
then fails (non-zero exit) if the ledger's stated ``verdict`` disagrees or any
finding is malformed. This closes the one Output-Contract seam that is otherwise
only exhorted in prose: a standalone hardening run (which never invokes qc-all)
can otherwise ship a ledger whose stated verdict does not match what the suite
rollup would compute from the same findings.

Canonical verdict algorithm: ``qc-all/references/rollup.md``, Aggregation step 4 —
keep this in sync with that file. (Note: ``qc_deterministic.sh`` treats *any*
finding as debt, whereas rollup.md — and qc-hardening's Output Contract table —
only treat P1>0 or an open P2 as debt. This script follows rollup.md, which is
what qc-hardening's verdict table is written against.)

Usage:
  verify_ledger.py <path-to-ledger.json>
  verify_ledger.py --self-test

Exit codes:
  0  ledger valid and stated verdict matches the recomputed verdict
  1  verdict mismatch, malformed finding, or unreadable / non-JSON ledger
  2  bad invocation
"""

from __future__ import annotations

import json
import os
import sys


VALID_VERDICTS = {"READY", "READY_WITH_DEBT", "NOT_READY", "SKIPPED"}
FINDING_REQUIRED = ("id", "severity", "file", "what", "fixed")


def compute_verdict(findings: list[dict]) -> str:
    """Recompute the release verdict from findings — qc-all rollup.md step 4."""
    def of_severity(s: str) -> list[dict]:
        return [f for f in findings if f.get("severity") == s]

    def is_open(f: dict) -> bool:
        return f.get("fixed") is False and not (f.get("deferred_because") or "")

    if of_severity("P0"):
        return "NOT_READY"  # any P0 blocks, fixed or not (matches rollup + qc_deterministic)
    if any(is_open(f) for f in of_severity("P1")):
        return "NOT_READY"
    if of_severity("P1"):
        return "READY_WITH_DEBT"  # P1s present but all fixed or deferred
    if any(is_open(f) for f in of_severity("P2")):
        return "READY_WITH_DEBT"  # unaddressed P2 = acknowledged debt
    return "READY"


def malformed(findings: list[dict]) -> list[str]:
    """Return human-readable problems for findings missing required fields."""
    problems = []
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            problems.append(f"finding[{i}] is not an object")
            continue
        missing = [k for k in FINDING_REQUIRED if k not in f]
        if missing:
            problems.append(f"finding[{i}] ({f.get('id', '?')}) missing {missing}")
        if "fixed" in f and not isinstance(f["fixed"], bool):
            problems.append(f"finding[{i}] ({f.get('id', '?')}) `fixed` is not a boolean")
    return problems


def _schema_path() -> str:
    """Resolve qc-finding.schema.json whether this script lives in qc-all or a per-skill copy."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "qc-finding.schema.json"),  # qc-all/references/scripts/
        os.path.join(here, "..", "references", "qc-finding.schema.json"),  # skills/<name>/scripts/
        os.path.join(here, "qc-finding.schema.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]


def schema_check(obj: dict) -> str | None:
    """Validate against the shared schema if jsonschema is available, else skip."""
    schema_path = _schema_path()
    try:
        import jsonschema
    except ImportError:
        print(
            "  [warn] jsonschema not installed — skipping schema validation "
            "(verdict recompute still runs)",
            file=sys.stderr,
        )
        return None
    try:
        with open(schema_path, encoding="utf-8") as fh:
            schema = json.load(fh)
    except OSError as exc:
        print(f"  [warn] could not read schema at {schema_path}: {exc}", file=sys.stderr)
        return None
    try:
        jsonschema.validate(obj, schema)
    except jsonschema.ValidationError as exc:
        return f"schema validation failed: {exc.message}"
    return None


def verify(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except FileNotFoundError:
        print(f"FAIL: ledger not found: {path}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"FAIL: ledger unreadable or not JSON: {path}: {exc}", file=sys.stderr)
        return 1

    findings = obj.get("findings")
    if not isinstance(findings, list):
        print("FAIL: ledger has no `findings` array", file=sys.stderr)
        return 1

    problems = malformed(findings)
    schema_problem = schema_check(obj)
    if schema_problem:
        problems.append(schema_problem)

    stated = obj.get("verdict")
    if stated not in VALID_VERDICTS:
        problems.append(f"`verdict` is {stated!r}, not one of {sorted(VALID_VERDICTS)}")

    computed = compute_verdict(findings)
    if stated in VALID_VERDICTS and stated != computed:
        problems.append(
            f"verdict mismatch: ledger says {stated!r} but findings compute to "
            f"{computed!r} (qc-all rollup algorithm)"
        )

    if problems:
        print(f"FAIL: {path}", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        f"OK: {path} — verdict {stated} matches recomputed {computed} "
        f"({len(findings)} findings)"
    )
    return 0


def _self_test() -> int:
    cases = [
        ([{"severity": "P0", "fixed": True}], "NOT_READY", "fixed P0 still blocks"),
        ([{"severity": "P0", "fixed": False}], "NOT_READY", "open P0 blocks"),
        ([{"severity": "P1", "fixed": False}], "NOT_READY", "open P1 blocks"),
        (
            [{"severity": "P1", "fixed": False, "deferred_because": "needs API owner"}],
            "READY_WITH_DEBT",
            "deferred P1 is debt",
        ),
        ([{"severity": "P1", "fixed": True}], "READY_WITH_DEBT", "fixed P1 is debt"),
        ([{"severity": "P2", "fixed": False}], "READY_WITH_DEBT", "open P2 is debt"),
        ([{"severity": "P2", "fixed": True}], "READY", "fixed P2 is clean"),
        ([{"severity": "P3", "fixed": False}], "READY", "P3 never blocks"),
        ([], "READY", "empty ledger is ready"),
    ]
    ok = True
    for findings, expected, label in cases:
        got = compute_verdict(findings)
        if got != expected:
            ok = False
        print(f"  [{'PASS' if got == expected else 'FAIL'}] {label}: expected {expected}, got {got}")
    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--self-test":
        return _self_test()
    if len(argv) != 2 or argv[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    return verify(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
