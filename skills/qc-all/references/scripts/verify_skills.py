#!/usr/bin/env python3
"""Shim — canonical verify_skills.py lives in qc-core."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[3] / "qc-core" / "scripts" / "verify_skills.py"
raise SystemExit(subprocess.call([sys.executable, str(TARGET), *sys.argv[1:]]))
