#!/usr/bin/env python3
"""Atomically write a QC JSON object (ledger or profile).

Usage:
  write_ledger.py <dest.json>                 # JSON object on stdin
  write_ledger.py <dest.json> <src.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from qc import atomic_write_json


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    dest = argv[1]
    if len(argv) == 3:
        obj = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    else:
        obj = json.load(sys.stdin)
    atomic_write_json(dest, obj)
    print(f"OK: wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
