#!/usr/bin/env python3
"""Canonical QC invariants — one home for verdict math, deferred vocab, evidence bar.

Imported by verify_ledger.py, suite_rollup.py, and the self-test. Do not reimplement
these functions in a skill, a shell script, or a workflow prompt.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1.1"

LEGAL_ORDER = ("qc-packaging", "qc-hardening", "qc-coherence", "qc-docs")

VALID_VERDICTS = frozenset({"READY", "READY_WITH_DEBT", "NOT_READY", "SKIPPED"})
FINDING_REQUIRED = ("id", "severity", "file", "what", "fixed")
SEVERITIES = ("P0", "P1", "P2", "P3")
CONFIDENCE = frozenset({"mechanical", "pattern", "proven", "human"})

# Closed deferred vocabulary. `deferred_because` is `code` or `code: detail`.
DEFERRED_CODES = (
    "needs-architecture",
    "public-signature",
    "behavior-change",
    "needs-owner",
    "golden-sensitive",
    "off-limits",
    "needs-canonical-site",
    "needs-module-split",
    "user-provided-unknown",
    "accepted-debt",
    "needs-migration",
    "cross-backend",
)
_DEFERRED_RE = re.compile(
    r"^(" + "|".join(re.escape(c) for c in DEFERRED_CODES) + r")(: .+)?$"
)

# Deep / judgment-heavy IDs that always need a structured scenario (unless mechanical).
_DEEP_ID = re.compile(r"^(F(1|12|13)|[MA]\d|MS-\d)")
DEEP_PASSES = frozenset({1, 12, 13})
LLM_SKILLS = frozenset({"qc-hardening", "qc-coherence"})

_BOILERPLATE_INVARIANT = re.compile(
    r"^(looks? (fine|good|ok|okay|correct|clean)|"
    r"seems? (fine|ok|okay|correct|clean)|"
    r"no issues?|n/a|none|ok|okay|clean|fine|good|"
    r"examined|reviewed|checked|lgtm)\.?$",
    re.IGNORECASE,
)

_REAL_VOTES = frozenset({"confirmed", "real_incoherence", "overstated", "real"})
_DROP_VOTES = frozenset({"refuted", "intentional", "drop"})


def is_open(finding: dict) -> bool:
    return finding.get("fixed") is False and not (finding.get("deferred_because") or "")


def parse_deferred(value: str) -> tuple[str, str] | None:
    """Return (code, detail) or None if the string is not in the closed vocabulary."""
    if not isinstance(value, str):
        return None
    m = _DEFERRED_RE.match(value.strip())
    if not m:
        return None
    code = m.group(1)
    detail = (m.group(2) or "").lstrip(": ").strip()
    return code, detail


def needs_scenario(finding: dict) -> bool:
    """Structured (trigger, violated_invariant, observable) is required.

    Mechanical tool hits stay lightweight. Deep passes, semantic/architectural
    checks, and any P1+ judgment finding need the triple.
    """
    if finding.get("confidence") == "mechanical":
        return False
    if finding.get("severity") in ("P0", "P1"):
        return True
    if finding.get("pass") in DEEP_PASSES:
        return True
    ident = str(finding.get("id") or "")
    return bool(_DEEP_ID.match(ident))


def scenario_complete(finding: dict) -> bool:
    s = finding.get("scenario")
    if not isinstance(s, dict):
        return False
    for key in ("trigger", "violated_invariant", "observable"):
        val = s.get(key)
        if not isinstance(val, str) or len(val.strip()) < 8:
            return False
    return True


def invariant_ok(text: str) -> bool:
    """Reject empty, short, or boilerplate CLEAN-list invariants."""
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if len(stripped) < 24:
        return False
    return _BOILERPLATE_INVARIANT.match(stripped) is None


def dual_vote_recommendation(vote_a: str, vote_b: str) -> str:
    """Both votes must say real → fix; both drop → drop; otherwise defer.

    Never silently drop a split or uncertain pair. Vote tokens from either
    hardening (confirmed/refuted) or coherence (real_incoherence/intentional)
    vocabularies are accepted.
    """
    a = (vote_a or "").strip().lower()
    b = (vote_b or "").strip().lower()
    if a in _REAL_VOTES and b in _REAL_VOTES:
        return "fix"
    if a in _DROP_VOTES and b in _DROP_VOTES:
        return "drop"
    return "defer"


def skip_dual_verify(finding: dict) -> bool:
    """High-certainty mechanical or human-confirmed hits skip the expensive path."""
    return finding.get("confidence") in ("mechanical", "human")


def compute_verdict(
    findings: list[dict],
    *,
    p0_policy: str = "presence",
) -> str:
    """Recompute the release verdict from findings.

    p0_policy:
      - ``presence`` (hardening, suite human-gate): any P0 blocks, fixed or not
      - ``open`` (packaging/docs/coherence standalone): only an *open* P0 blocks
    """
    def of_severity(s: str) -> list[dict]:
        return [f for f in findings if f.get("severity") == s]

    p0 = of_severity("P0")
    if p0_policy == "presence":
        if p0:
            return "NOT_READY"
    elif any(is_open(f) for f in p0):
        return "NOT_READY"

    if any(is_open(f) for f in of_severity("P1")):
        return "NOT_READY"
    if of_severity("P1"):
        return "READY_WITH_DEBT"
    if any(is_open(f) for f in of_severity("P2")):
        return "READY_WITH_DEBT"
    return "READY"


def policy_for_skill(skill: str) -> str:
    return "presence" if skill == "qc-hardening" else "open"


def count_by_severity(findings: Iterable[dict]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        sev = f.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def suite_verdict(
    skill_ledgers: dict[str, dict],
    skipped: Iterable[str] = (),
) -> tuple[str, dict[str, dict[str, int]], dict[str, str]]:
    """Deterministic suite rollup.

    1. Any skill NOT_READY → NOT_READY
    2. Any P0 in any non-skipped ledger (fixed or not) → NOT_READY (human-gate)
    3. Else any READY_WITH_DEBT or deferred P1 → READY_WITH_DEBT
    4. Else READY
    All-skipped (or empty) → READY
    """
    skipped_set = set(skipped)
    findings_by_skill: dict[str, dict[str, int]] = {}
    skill_verdicts: dict[str, str] = {}
    all_findings: list[dict] = []

    active = {k: v for k, v in skill_ledgers.items() if k not in skipped_set}
    if not active:
        return "READY", {}, {}

    for skill, ledger in active.items():
        findings = ledger.get("findings") if isinstance(ledger.get("findings"), list) else []
        all_findings.extend(findings)
        findings_by_skill[skill] = count_by_severity(findings)
        stated = ledger.get("verdict")
        computed = compute_verdict(findings, p0_policy=policy_for_skill(skill))
        skill_verdicts[skill] = stated if stated in VALID_VERDICTS else computed

    if any(v == "NOT_READY" for v in skill_verdicts.values()):
        return "NOT_READY", findings_by_skill, skill_verdicts
    if any(f.get("severity") == "P0" for f in all_findings):
        return "NOT_READY", findings_by_skill, skill_verdicts
    if any(v == "READY_WITH_DEBT" for v in skill_verdicts.values()):
        return "READY_WITH_DEBT", findings_by_skill, skill_verdicts
    if any(f.get("severity") == "P1" and (f.get("deferred_because") or "") for f in all_findings):
        return "READY_WITH_DEBT", findings_by_skill, skill_verdicts
    return "READY", findings_by_skill, skill_verdicts


def atomic_write_json(path: str | Path, obj: Any) -> None:
    """Write JSON via temp file + os.replace so readers never see a partial object."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def core_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def schema_path(name: str = "qc-finding.schema.json") -> Path:
    return core_dir() / "references" / name
