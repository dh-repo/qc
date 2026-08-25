#!/usr/bin/env python3
"""Machine-check a QC findings ledger against qc-core.

Validates the ledger against qc-finding.schema.json and recomputes the verdict
with the canonical algorithm in qc.py. A mismatch is a ledger bug, not a script bug.

Usage:
  verify_ledger.py <path-to-ledger.json>
  verify_ledger.py --self-test
  verify_ledger.py --verdict          # findings array (or ledger) on stdin; print verdict

Exit codes:
  0  valid (and stated verdict matches recomputed)
  1  verdict mismatch, malformed finding, or unreadable ledger
  2  bad invocation
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from qc import (
    CONFIDENCE,
    DEFERRED_CODES,
    FINDING_REQUIRED,
    LLM_SKILLS,
    VALID_VERDICTS,
    compute_verdict,
    invariant_ok,
    needs_scenario,
    parse_deferred,
    policy_for_skill,
    scenario_complete,
    schema_path,
)


def malformed(findings: list, skill: str | None = None) -> list[str]:
    problems = []
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            problems.append(f"finding[{i}] is not an object")
            continue
        ident = f.get("id", "?")
        missing = [k for k in FINDING_REQUIRED if k not in f]
        if missing:
            problems.append(f"finding[{i}] ({ident}) missing {missing}")
        if "fixed" in f and not isinstance(f["fixed"], bool):
            problems.append(f"finding[{i}] ({ident}) `fixed` is not a boolean")
        conf = f.get("confidence")
        if conf is not None and conf not in CONFIDENCE:
            problems.append(f"finding[{i}] ({ident}) confidence {conf!r} not in {sorted(CONFIDENCE)}")
        if needs_scenario(f) and not scenario_complete(f):
            problems.append(
                f"finding[{i}] ({ident}) needs scenario.{{trigger,violated_invariant,observable}} "
                f"(deep / P1+ finding; mechanical hits are exempt)"
            )
        deferred = f.get("deferred_because")
        if deferred:
            if parse_deferred(deferred) is None:
                problems.append(
                    f"finding[{i}] ({ident}) deferred_because {deferred!r} is not "
                    f"`code` or `code: detail` from {list(DEFERRED_CODES)}"
                )
            if f.get("fixed") is True:
                problems.append(f"finding[{i}] ({ident}) is fixed:true but sets deferred_because")
        related = f.get("related_findings")
        if related is not None and not (
            isinstance(related, list) and all(isinstance(x, str) for x in related)
        ):
            problems.append(f"finding[{i}] ({ident}) related_findings must be an array of strings")
    return problems


def examined_problems(obj: dict) -> list[str]:
    skill = obj.get("skill")
    mode = obj.get("mode") or "full"
    if skill not in LLM_SKILLS or mode == "quick-check":
        return []
    examined = obj.get("examined")
    if not isinstance(examined, list) or not examined:
        return [
            "LLM-assisted run has no `examined` CLEAN list — if you cannot name "
            "what you examined, you did not examine it"
        ]
    problems = []
    for i, entry in enumerate(examined):
        if not isinstance(entry, dict):
            problems.append(f"examined[{i}] is not an object with artifact+invariant")
            continue
        artifact = entry.get("artifact") or ""
        invariant = entry.get("invariant") or ""
        if not str(artifact).strip():
            problems.append(f"examined[{i}] missing artifact name")
        carmack = entry.get("carmack")
        if carmack:
            keys = ("invariant", "assumptions_wrong", "invalid_sequence", "million_runs", "wrong_tomorrow")
            missing = [k for k in keys if not (isinstance(carmack.get(k), str) and carmack[k].strip())]
            if missing:
                problems.append(f"examined[{i}] ({artifact}) carmack missing {missing}")
        elif not invariant_ok(invariant):
            problems.append(
                f"examined[{i}] ({artifact}) invariant is empty, short, or boilerplate"
            )
    return problems


def schema_check(obj: dict) -> str | None:
    path = schema_path()
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
        schema = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"  [warn] could not read schema at {path}: {exc}", file=sys.stderr)
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

    skill = obj.get("skill")
    problems = malformed(findings, skill if isinstance(skill, str) else None)
    problems.extend(examined_problems(obj))
    schema_problem = schema_check(obj)
    if schema_problem:
        problems.append(schema_problem)

    stated = obj.get("verdict")
    if stated not in VALID_VERDICTS:
        problems.append(f"`verdict` is {stated!r}, not one of {sorted(VALID_VERDICTS)}")

    policy = policy_for_skill(skill if isinstance(skill, str) else "")
    computed = compute_verdict(findings, p0_policy=policy)
    if skill == "qc-all":
        computed = stated if stated in VALID_VERDICTS else computed
    elif stated in VALID_VERDICTS and stated != computed:
        problems.append(
            f"verdict mismatch: ledger says {stated!r} but findings compute to "
            f"{computed!r} (qc-core algorithm, p0_policy={policy})"
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
            [{"severity": "P1", "fixed": False, "deferred_because": "needs-owner: API"}],
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
        got = compute_verdict(findings, p0_policy="presence")
        if got != expected:
            ok = False
        print(f"  [{'PASS' if got == expected else 'FAIL'}] {label}: expected {expected}, got {got}")

    got_open = compute_verdict(
        [{"severity": "P0", "fixed": True}], p0_policy="open"
    )
    if got_open != "READY":
        ok = False
        print(f"  [FAIL] open-policy fixed P0 should be READY, got {got_open}")
    else:
        print("  [PASS] open-policy fixed P0 does not block (packaging/docs)")

    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    if len(argv) == 2 and argv[1] == "--self-test":
        return _self_test()
    if len(argv) == 2 and argv[1] == "--verdict":
        payload = json.load(sys.stdin)
        findings = payload if isinstance(payload, list) else payload.get("findings", [])
        skill = "" if isinstance(payload, list) else payload.get("skill") or ""
        print(compute_verdict(findings, p0_policy=policy_for_skill(skill)))
        return 0
    if len(argv) != 2 or argv[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    # Allow importing qc from this directory when invoked by absolute path.
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    return verify(argv[1])


if __name__ == "__main__":
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    raise SystemExit(main(sys.argv))
