#!/usr/bin/env python3
"""Compose .qc-findings/_rollup.json from per-skill ledgers.

Usage:
  suite_rollup.py --findings-dir .qc-findings [--skipped skipped.json] [--out .qc-findings/_rollup.json]

skipped.json is a JSON array of {skill, last_covered_sha} objects.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from qc import LEGAL_ORDER, SCHEMA_VERSION, atomic_write_json, suite_verdict


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return "0000000"


def _run_id(sha: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{ts}-{sha[:7]}"


def load_ledgers(findings_dir: Path) -> dict[str, dict]:
    ledgers = {}
    for skill in LEGAL_ORDER:
        path = findings_dir / f"{skill}.json"
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            ledgers[skill] = json.load(fh)
    return ledgers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings-dir", default=".qc-findings")
    parser.add_argument("--skipped", default=None, help="JSON file of skipped[] entries")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    findings_dir = Path(args.findings_dir)
    skipped_entries = []
    if args.skipped:
        skipped_entries = json.loads(Path(args.skipped).read_text(encoding="utf-8"))
    skipped_names = [s["skill"] if isinstance(s, dict) else s for s in skipped_entries]

    ledgers = load_ledgers(findings_dir)
    missing = [s for s in LEGAL_ORDER if s not in skipped_names and s not in ledgers]
    if missing:
        print(f"FAIL: missing ledgers for non-skipped skills: {missing}", file=sys.stderr)
        return 1

    verdict, by_skill, skill_verdicts = suite_verdict(ledgers, skipped_names)
    sha = _git_sha()
    rollup = {
        "schema_version": SCHEMA_VERSION,
        "skill": "qc-all",
        "run_id": _run_id(sha),
        "git_sha": sha if len(sha) >= 7 else sha,
        "findings": [],
        "verdict": verdict,
        "skipped": skipped_entries,
        "findings_by_skill": by_skill,
        "skill_verdicts": skill_verdicts,
    }
    out = Path(args.out) if args.out else findings_dir / "_rollup.json"
    atomic_write_json(out, rollup)
    print(f"OK: {out} — suite verdict {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
