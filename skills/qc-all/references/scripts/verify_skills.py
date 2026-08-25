#!/usr/bin/env python3
"""Verification gate for qc-* skill artifacts — 15-check PRD registry."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parents[3]
REFS_DIR = Path(__file__).parents[1]
SCHEMA_FILE = REFS_DIR / "qc-finding.schema.json"
_LEGACY = re.compile(r"\b(CRITICAL|HIGH|MEDIUM|LOW|CONCERN)\b", re.IGNORECASE)
_EXEMPT = re.compile(r"legacy|migration|old|outcome", re.IGNORECASE)
_JSON_FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)


def _skill_mds(skill_filter: str | None) -> list[Path]:
    dirs = sorted(SKILLS_DIR.glob("qc-*/"))
    if skill_filter:
        dirs = [d for d in dirs if d.name == skill_filter]
    return [d / "SKILL.md" for d in dirs if (d / "SKILL.md").exists()]


def _script_ok(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"{path.name} not found"
    if not path.stat().st_mode & 0o111:
        return False, f"{path.name} not executable"
    r = subprocess.run([str(path), "--help"], capture_output=True)
    if r.returncode != 0:
        return False, f"{path.name} --help exited {r.returncode}"
    return True, ""


def check_severity_vocabulary_in_skills(f: str | None) -> tuple[bool, str]:
    hits = []
    for md in _skill_mds(f):
        for n, line in enumerate(md.read_text().splitlines(), 1):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")]
            non_empty = [c for c in cells if c]
            if non_empty and _EXEMPT.match(non_empty[0]):
                continue
            # Only flag cells whose entire content is a legacy severity token.
            for cell in cells:
                bare = re.sub(r"[*_`]", "", cell).strip()
                if bare and _LEGACY.fullmatch(bare):
                    hits.append(f"{md.relative_to(SKILLS_DIR)}:{n}")
                    break
    if hits:
        return False, f"legacy severity tokens in table rows: {', '.join(hits)} (R1)"
    return True, "no legacy severity tokens (R1)"


def check_example_finding_blocks(f: str | None) -> tuple[bool, str]:
    try:
        import jsonschema
        schema = json.loads(SCHEMA_FILE.read_text())
    except ImportError:
        return False, "jsonschema not installed (R2,R10)"
    mds = _skill_mds(f)
    missing: list[str] = []
    for md in mds:
        name = md.parent.name
        found = False
        for block in _JSON_FENCE.findall(md.read_text()):
            try:
                obj = json.loads(block)
            except json.JSONDecodeError:
                continue
            if obj.get("skill") != name:
                continue
            try:
                jsonschema.validate(obj, schema)
                found = True
                break
            except jsonschema.ValidationError:
                pass
        if not found:
            missing.append(name)
    if missing:
        return False, f"missing valid examples: {missing} (R2,R10)"
    return True, f"{len(mds)}/{len(mds)} SKILL.md files have valid examples (R2,R10)"


def check_qc_hardening_size(_f: str | None) -> tuple[bool, str]:
    md = SKILLS_DIR / "qc-hardening" / "SKILL.md"
    if not md.exists():
        return False, "qc-hardening/SKILL.md not found (R3)"
    n = len(md.read_text().splitlines())
    if n > 250:
        return False, f"qc-hardening/SKILL.md:0 size {n} lines, budget 250 (R3)"
    return True, f"{n} lines / 250 budget (R3)"


def check_qc_hardening_references(_f: str | None) -> tuple[bool, str]:
    refs = SKILLS_DIR / "qc-hardening" / "references"
    if not refs.exists():
        return False, "qc-hardening/references/ not found (R3)"
    files = [p for p in refs.iterdir() if p.is_file()]
    if len(files) < 5:
        return False, f"only {len(files)}/5 reference files under qc-hardening/references/ (R3)"
    return True, f"{len(files)}/5 reference files (R3)"


def check_qc_structural_deleted(_f: str | None) -> tuple[bool, str]:
    if (SKILLS_DIR / "qc-structural").exists():
        return False, "qc-structural/ still exists (R4)"
    return True, "qc-structural absent (R4)"


def check_qc_coherence_absorbed_structural(_f: str | None) -> tuple[bool, str]:
    skill_md = SKILLS_DIR / "qc-coherence" / "SKILL.md"
    checks_md = SKILLS_DIR / "qc-coherence" / "references" / "module-scope-checks.md"
    if not skill_md.exists():
        return False, "qc-coherence/SKILL.md not found (R4)"
    if "--scope=module" not in skill_md.read_text():
        return False, "qc-coherence/SKILL.md does not mention --scope=module (R4)"
    if not checks_md.exists():
        return False, "qc-coherence/references/module-scope-checks.md not found (R4)"
    count = len(re.findall(r"^##\s+MS-\d+", checks_md.read_text(), re.MULTILINE))
    if count < 6:
        return False, f"only {count}/6 module-scope checks in module-scope-checks.md (R4)"
    return True, f"--scope=module documented; {count} module-scope checks (R4)"


def check_watch_manifest_exists(_f: str | None) -> tuple[bool, str]:
    m = REFS_DIR / "qc-watch-manifest.json"
    if not m.exists():
        return False, "qc-watch-manifest.json not found (R5)"
    try:
        data = json.loads(m.read_text())
    except json.JSONDecodeError as e:
        return False, f"qc-watch-manifest.json invalid JSON: {e} (R5)"
    missing = {"qc-packaging", "qc-docs", "qc-hardening", "qc-coherence"} - set(data)
    if missing:
        return False, f"missing keys: {missing} (R5)"
    return True, "4 keys present (R5)"


def check_deterministic_script_exists(_f: str | None) -> tuple[bool, str]:
    ok, msg = _script_ok(REFS_DIR / "scripts" / "qc_deterministic.sh")
    if not ok:
        return False, f"{msg} (R6)"
    return True, "qc_deterministic.sh executable, --help OK (R6)"


def check_history_script_exists(_f: str | None) -> tuple[bool, str]:
    ok, msg = _script_ok(REFS_DIR / "scripts" / "append_history.py")
    if not ok:
        return False, f"{msg} (R7)"
    return True, "append_history.py executable, --help OK (R7)"


def check_qc_all_size(_f: str | None) -> tuple[bool, str]:
    md = SKILLS_DIR / "qc-all" / "SKILL.md"
    if not md.exists():
        return False, "qc-all/SKILL.md not found (R8)"
    n = len(md.read_text().splitlines())
    if n > 150:
        return False, f"qc-all/SKILL.md:0 size {n} lines, budget 150 (R8)"
    return True, f"{n} lines / 150 budget (R8)"


def check_no_prose_step_orchestration(_f: str | None) -> tuple[bool, str]:
    md = SKILLS_DIR / "qc-all" / "SKILL.md"
    if not md.exists():
        return False, "qc-all/SKILL.md not found (R8)"
    for n, line in enumerate(md.read_text().splitlines(), 1):
        if re.search(r"### Step \d+: Invoke /qc-", line):
            return False, f"qc-all/SKILL.md:{n} prose step orchestration found (R8)"
    return True, "no `### Step N: Invoke` lines (R8)"


def check_supervisor_dispatch_single_source(_f: str | None) -> tuple[bool, str]:
    if not (REFS_DIR / "supervisor-dispatch.md").exists():
        return False, "qc-all/references/supervisor-dispatch.md not found (R9)"
    dupes = [md.parent.name for md in _skill_mds(None) if "Mission: Resolve" in md.read_text()]
    if dupes:
        return False, f"'Mission: Resolve' in SKILL.md files: {dupes} (R9)"
    return True, "1 doc, 0 duplicates (R9)"


def check_rollup_provenance_example(_f: str | None) -> tuple[bool, str]:
    md = SKILLS_DIR / "qc-all" / "SKILL.md"
    if not md.exists():
        return False, "qc-all/SKILL.md not found (R12)"
    required = {"git_sha", "run_id", "skipped", "findings_by_skill"}
    for block in _JSON_FENCE.findall(md.read_text()):
        try:
            obj = json.loads(block)
        except json.JSONDecodeError:
            continue
        if obj.get("skill") == "qc-all" and required.issubset(obj):
            return True, "git_sha,run_id,skipped,findings_by_skill present (R12)"
    return False, "no rollup example with all 4 provenance fields in qc-all/SKILL.md (R12)"


def check_schema_single_source(_f: str | None) -> tuple[bool, str]:
    files = list(SKILLS_DIR.rglob("qc-finding.schema.json"))
    if len(files) != 1:
        return False, f"{len(files)} schema files found, expected 1 (R13)"
    return True, "1 schema file (R13)"


def check_schema_version(_f: str | None) -> tuple[bool, str]:
    if not SCHEMA_FILE.exists():
        return False, "schema file not found (R13)"
    try:
        schema = json.loads(SCHEMA_FILE.read_text())
    except json.JSONDecodeError as e:
        return False, f"schema invalid JSON: {e} (R13)"
    const = schema.get("properties", {}).get("schema_version", {}).get("const")
    if const != "1.0":
        return False, f"schema_version.const is {const!r}, expected '1.0' (R13)"
    return True, '"1.0" (R13)'


REGISTRY: list[tuple[str, object]] = [
    ("severity_vocabulary_in_skills",    check_severity_vocabulary_in_skills),
    ("example_finding_blocks",           check_example_finding_blocks),
    ("qc_hardening_size",                check_qc_hardening_size),
    ("qc_hardening_references",          check_qc_hardening_references),
    ("qc_structural_deleted",            check_qc_structural_deleted),
    ("qc_coherence_absorbed_structural", check_qc_coherence_absorbed_structural),
    ("watch_manifest_exists",            check_watch_manifest_exists),
    ("deterministic_script_exists",      check_deterministic_script_exists),
    ("history_script_exists",            check_history_script_exists),
    ("qc_all_size",                      check_qc_all_size),
    ("no_prose_step_orchestration",      check_no_prose_step_orchestration),
    ("supervisor_dispatch_single_source",check_supervisor_dispatch_single_source),
    ("rollup_provenance_example",        check_rollup_provenance_example),
    ("schema_single_source",             check_schema_single_source),
    ("schema_version",                   check_schema_version),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify qc-* skill artifacts against PRD requirements")
    parser.add_argument("--skill", metavar="NAME", help="Scope checks to one skill")
    parser.add_argument("--strict", action="store_true", help="Treat WARN messages as failures")
    args = parser.parse_args()

    try:
        import jsonschema as _  # noqa: F401
    except ImportError:
        print("Missing dependency: pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    print(f"verify_skills.py: {len(REGISTRY)} checks")
    failures = 0
    for name, fn in REGISTRY:
        passed, msg = fn(args.skill)  # type: ignore[operator]
        if args.strict and msg.startswith("WARN:"):
            passed = False
        if not passed:
            failures += 1
        print(f"{'PASS' if passed else 'FAIL'}  {name:<42} {msg}")

    print(f"\n{len(REGISTRY) - failures} PASS, {failures} FAIL")
    print(f"verdict: {'PASS' if failures == 0 else 'FAIL'}")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
