#!/usr/bin/env python3
"""Append a qc-all rollup JSON as one line to .qc-history.jsonl with bounded trim."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a rollup JSON to .qc-history.jsonl with automatic 20-line trim.",
    )
    parser.add_argument("rollup_json", help="Path to the rollup JSON file")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=20,
        help="Maximum history lines to keep (default: 20)",
    )
    parser.add_argument(
        "--history-path",
        default=".qc-history.jsonl",
        help="Path to the history file (default: .qc-history.jsonl)",
    )
    return parser.parse_args()


def load_rollup(path: Path) -> dict:
    """Read and minimally validate a rollup JSON file.

    Raises OSError on I/O failure, ValueError (or json.JSONDecodeError) on bad content.
    """
    with path.open(encoding="utf-8") as f:
        rollup = json.load(f)
    if not isinstance(rollup, dict):
        raise ValueError("rollup JSON must be a JSON object")
    missing = [k for k in ("run_id", "git_sha") if k not in rollup]
    if missing:
        raise ValueError(f"rollup missing required keys: {', '.join(missing)}")
    return rollup


def trim_and_write(history_path: Path, lines: list[str]) -> None:
    """Atomically rewrite history_path with lines, one per line."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=history_path.parent,
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write("\n".join(lines) + "\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, history_path)


def append_to_history(rollup: dict, history_path: Path, max_lines: int) -> None:
    """Append rollup as one JSON line, then trim oldest if over max_lines."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rollup) + "\n")
    with history_path.open("r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if len(lines) > max_lines:
        trim_and_write(history_path, lines[-max_lines:])


def main() -> None:
    args = parse_args()
    rollup_path = Path(args.rollup_json)
    history_path = Path(args.history_path)

    try:
        rollup = load_rollup(rollup_path)
    except ValueError as exc:
        print(f"ERROR: malformed rollup: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"ERROR: cannot read rollup file: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        append_to_history(rollup, history_path, args.max_lines)
    except OSError as exc:
        print(f"ERROR: I/O error writing history: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
