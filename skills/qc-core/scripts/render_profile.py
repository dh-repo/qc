#!/usr/bin/env python3
"""Render .qc-profile.md from .qc-profile.json. JSON is the source of truth.

Usage:
  render_profile.py [.qc-profile.json] [--out .qc-profile.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def render(profile: dict) -> str:
    lines = [
        "# QC Profile",
        "",
        "Generated from `.qc-profile.json`. Edit the JSON (or let a qc-* skill write it); do not hand-edit this file.",
        "",
        f"Updated: {profile.get('updated_at', '(unknown)')}",
        "",
        "## Run History",
        "",
        "| Run | Skill | Verdict | Findings |",
        "|-----|-------|---------|----------|",
    ]
    for row in profile.get("run_history") or []:
        findings = row.get("findings") or {}
        tally = " ".join(f"{k}:{v}" for k, v in findings.items()) if isinstance(findings, dict) else findings
        lines.append(
            f"| {row.get('run_id', '')} | {row.get('skill', '')} | {row.get('verdict', '')} | {tally} |"
        )
    lines += ["", "## Hot Spots", ""]
    spots = profile.get("hot_spots") or []
    if not spots:
        lines.append("(none)")
    for s in spots:
        ids = ", ".join(s.get("finding_ids") or [])
        lines.append(f"- `{s.get('artifact')}` — {s.get('rationale', '')} ({ids})")
    lines += ["", "## Deferred", ""]
    deferred = profile.get("deferred") or []
    if not deferred:
        lines.append("(none)")
    for d in deferred:
        lines.append(
            f"- {d.get('id')} ({d.get('skill')}, {d.get('severity')}, {d.get('code')}) — {d.get('detail', '')}"
        )
    lines += ["", "## Pass Debt", ""]
    debt = profile.get("pass_debt") or []
    if not debt:
        lines.append("(none)")
    else:
        lines += [
            "| Finding | Found by | Should have been | Module | Why missed |",
            "|---------|----------|------------------|--------|------------|",
        ]
        for d in debt:
            lines.append(
                f"| {d.get('finding_id')} | {d.get('found_by')} | {d.get('should_have_been')} | "
                f"{d.get('module')} | {d.get('why_missed', '')} |"
            )
    lines += ["", "## Operating Facts", ""]
    facts = profile.get("operating_facts") or []
    if not facts:
        lines.append("(none)")
    for f in facts:
        lines.append(f"- `{f.get('id')}` ({f.get('source')}, {f.get('timestamp')}): {f.get('fact')}")
    lines += ["", "## Invariants", ""]
    invs = profile.get("invariants") or []
    if not invs:
        lines.append("(none)")
    for inv in invs:
        lines.append(
            f"- `{inv.get('id')}` [{inv.get('status')}, {inv.get('source')}] {inv.get('statement')}"
            + (f" — enforced by `{inv.get('enforced_by')}`" if inv.get("enforced_by") else "")
        )
    lines += ["", "## Canonical Forms", ""]
    forms = profile.get("canonical_forms") or []
    if not forms:
        lines.append("(none)")
    for c in forms:
        aliases = ", ".join(c.get("aliases") or []) or "(none)"
        lines.append(f"- {c.get('concept')}: `{c.get('canonical')}` (aliases: {aliases})")
    layer = profile.get("layer_model")
    lines += ["", "## Layer Model", ""]
    if not layer:
        lines.append("(none)")
    else:
        lines.append("Layers: " + ", ".join(layer.get("layers") or []))
        for rule in layer.get("rules") or []:
            lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?", default=".qc-profile.json")
    parser.add_argument("--out", default=".qc-profile.md")
    args = parser.parse_args(argv)
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FAIL: unreadable profile {args.profile}: {exc}", file=sys.stderr)
        return 1
    Path(args.out).write_text(render(profile), encoding="utf-8")
    print(f"OK: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
