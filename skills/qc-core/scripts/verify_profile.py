#!/usr/bin/env python3
"""Validate .qc-profile.json against qc-profile.schema.json and examination rules.

Usage:
  verify_profile.py <path-to-profile.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from qc import DEFERRED_CODES, invariant_ok, schema_path

_CARMACK_5Q = (
    "invariant",
    "assumptions_wrong",
    "invalid_sequence",
    "million_runs",
    "wrong_tomorrow",
)
_CARMACK_COMPACT = ("invariant", "assumptions", "sequence_risk")
_INVARIANT_SOURCES = frozenset({"carmack", "comment", "test", "doc"})
_INVARIANT_STATUSES = frozenset({"enforced", "untested", "deferred"})


def _carmack_examined_ok(rec: dict) -> bool:
    """Carmack EXAMINED: five questions, or invariant + assumptions + sequence_risk."""
    carmack = rec.get("carmack")
    if isinstance(carmack, dict):
        if all(invariant_ok(carmack.get(k) or "") for k in _CARMACK_5Q):
            return True
        if all(invariant_ok(carmack.get(k) or "") for k in _CARMACK_COMPACT):
            return True
    return all(invariant_ok(rec.get(k) or "") for k in _CARMACK_COMPACT)


def problems(obj: dict) -> list[str]:
    out = []
    if obj.get("schema_version") != "1.1":
        out.append(f"schema_version is {obj.get('schema_version')!r}, expected '1.1'")
    exam = obj.get("examination") or {}
    if not isinstance(exam, dict):
        out.append("examination must be an object keyed by skill")
        exam = {}
    for skill, arts in exam.items():
        if not isinstance(arts, dict):
            out.append(f"examination.{skill} must be an object keyed by artifact")
            continue
        for artifact, rec in arts.items():
            if not isinstance(rec, dict):
                out.append(f"examination.{skill}.{artifact} must be an object")
                continue
            status = rec.get("status")
            if status not in ("EXAMINED", "FINDING", "NOT_YET"):
                out.append(f"examination.{skill}.{artifact} status {status!r}")
            if status == "EXAMINED":
                if skill == "qc-hardening":
                    if not _carmack_examined_ok(rec):
                        out.append(
                            f"examination.{skill}.{artifact} EXAMINED needs Carmack 5Q "
                            f"or invariant+assumptions+sequence_risk (one sentence is not enough)"
                        )
                elif not rec.get("carmack") and not invariant_ok(rec.get("invariant") or ""):
                    out.append(
                        f"examination.{skill}.{artifact} EXAMINED without a substantive invariant"
                    )
            if status == "FINDING" and not rec.get("finding_ids"):
                out.append(f"examination.{skill}.{artifact} FINDING without finding_ids")
    for i, d in enumerate(obj.get("deferred") or []):
        if not isinstance(d, dict):
            out.append(f"deferred[{i}] is not an object")
            continue
        if d.get("code") not in DEFERRED_CODES:
            out.append(f"deferred[{i}] code {d.get('code')!r} not in closed vocabulary")
    for i, c in enumerate(obj.get("clusters") or []):
        if not isinstance(c, dict):
            out.append(f"clusters[{i}] is not an object")
            continue
        if not c.get("symbols") or not isinstance(c.get("symbols"), list):
            out.append(f"clusters[{i}] needs a symbols list (clustering is not a finding without one)")
        if not (isinstance(c.get("rationale"), str) and len(c["rationale"].strip()) >= 8):
            out.append(f"clusters[{i}] needs a rationale")
    for i, t in enumerate(obj.get("truth_map") or []):
        if not isinstance(t, dict):
            continue
        if t.get("kind") not in ("code", "test", "user-provided"):
            out.append(f"truth_map[{i}] kind {t.get('kind')!r}")
        if t.get("kind") == "user-provided" and not t.get("fact_id"):
            out.append(f"truth_map[{i}] user-provided claim needs fact_id pointing at operating_facts")
    for i, d in enumerate(obj.get("pass_debt") or []):
        if not isinstance(d, dict):
            continue
        if not invariant_ok(d.get("why_missed") or ""):
            out.append(
                f"pass_debt[{i}] why_missed must name the mechanical blind spot, not be empty/boilerplate"
            )
    for i, inv in enumerate(obj.get("invariants") or []):
        if not isinstance(inv, dict):
            out.append(f"invariants[{i}] is not an object")
            continue
        if not inv.get("id") or not invariant_ok(inv.get("statement") or ""):
            out.append(f"invariants[{i}] needs id and a substantive statement")
        if inv.get("source") not in _INVARIANT_SOURCES:
            out.append(f"invariants[{i}] source {inv.get('source')!r} not in {sorted(_INVARIANT_SOURCES)}")
        if inv.get("status") not in _INVARIANT_STATUSES:
            out.append(f"invariants[{i}] status {inv.get('status')!r}")
        if inv.get("status") == "enforced" and not (inv.get("enforced_by") or "").strip():
            out.append(f"invariants[{i}] enforced rows need enforced_by")
    for i, c in enumerate(obj.get("canonical_forms") or []):
        if not isinstance(c, dict):
            out.append(f"canonical_forms[{i}] is not an object")
            continue
        if not (c.get("concept") or "").strip() or not (c.get("canonical") or "").strip():
            out.append(f"canonical_forms[{i}] needs concept and canonical")
    layer = obj.get("layer_model")
    if layer is not None:
        if not isinstance(layer, dict) or not isinstance(layer.get("layers"), list) or not layer.get("layers"):
            out.append("layer_model.layers must be a non-empty list")
    for i, f in enumerate(obj.get("operating_facts") or []):
        if not isinstance(f, dict):
            continue
        if f.get("source") == "user-provided" and not (f.get("last_verified") or "").strip():
            out.append(f"operating_facts[{i}] user-provided fact needs last_verified")
    return out


def schema_check(obj: dict) -> str | None:
    path = schema_path("qc-profile.schema.json")
    try:
        import jsonschema
    except ImportError:
        return None
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(obj, schema)
    except Exception as exc:  # noqa: BLE001 — report any schema failure
        return f"schema validation failed: {exc}"
    return None


def verify(path: str) -> int:
    try:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {path}: {exc}", file=sys.stderr)
        return 1
    found = problems(obj)
    sc = schema_check(obj)
    if sc:
        found.append(sc)
    if found:
        print(f"FAIL: {path}", file=sys.stderr)
        for p in found:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"OK: {path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    if len(argv) != 2 or argv[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    return verify(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
