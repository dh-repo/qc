#!/usr/bin/env python3
"""Acceptance test for a QC skill port: recover seeded defects at declared severities.

A port is incomplete until it finds every planted defect and marks every declared
clean module EXAMINED with a substantive invariant.

Usage:
  verify_port.py --expected fixtures/hardening/expected.json --ledger <ledger.json> [--profile <profile.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qc import invariant_ok


def _matches(finding: dict, spec: dict) -> bool:
    ffile = str(finding.get("file") or "")
    if spec.get("file_substring") and spec["file_substring"] not in ffile:
        return False
    if spec.get("severity") and finding.get("severity") != spec["severity"]:
        return False
    what = (finding.get("what") or "") + " " + (finding.get("why") or "")
    needles = spec.get("what_contains") or []
    if needles and not any(n.lower() in what.lower() for n in needles):
        return False
    return True


def verify(expected: dict, ledger: dict, profile: dict | None) -> list[str]:
    problems = []
    findings = ledger.get("findings") or []
    for spec in expected.get("must_find") or []:
        hits = [f for f in findings if _matches(f, spec)]
        if not hits:
            problems.append(f"missing planted finding: {spec}")
            continue
        want_sev = spec.get("severity")
        if want_sev and not any(f.get("severity") == want_sev for f in hits):
            problems.append(
                f"planted finding {spec.get('file_substring')} found but not at {want_sev}"
            )
    clean = expected.get("must_mark_clean") or []
    exam = ((profile or {}).get("examination") or {}).get(expected.get("skill") or "", {})
    ledger_exam = {e.get("artifact"): e for e in (ledger.get("examined") or []) if isinstance(e, dict)}
    for artifact in clean:
        rec = exam.get(artifact) or {}
        status = rec.get("status")
        inv = rec.get("invariant") or (ledger_exam.get(artifact) or {}).get("invariant")
        if status == "FINDING":
            problems.append(f"{artifact} was planted clean but marked FINDING")
        if status == "NOT_YET" or (not status and artifact not in ledger_exam):
            problems.append(f"{artifact} was planted clean but never EXAMINED")
        if (status == "EXAMINED" or artifact in ledger_exam) and not rec.get("carmack") and not invariant_ok(inv or ""):
            problems.append(f"{artifact} EXAMINED with empty/boilerplate invariant")
        extra = [f for f in findings if artifact in str(f.get("file") or "") and f.get("severity") in ("P0", "P1")]
        if extra:
            problems.append(f"{artifact} is planted clean but ledger has P0/P1 { [e.get('id') for e in extra] }")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--profile", default=None)
    args = parser.parse_args(argv)
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8")) if args.profile else None
    found = verify(expected, ledger, profile)
    if found:
        print("FAIL: port did not recover the seeded set", file=sys.stderr)
        for p in found:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("OK: seeded defects recovered, clean modules examined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
