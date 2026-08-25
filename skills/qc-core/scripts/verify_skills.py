#!/usr/bin/env python3
"""Verification gate for qc-* skill artifacts."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1]
SKILLS_DIR = CORE_DIR.parent
SCHEMA_FILE = CORE_DIR / "references" / "qc-finding.schema.json"
ALL_REFS = SKILLS_DIR / "qc-all" / "references"
_LEGACY = re.compile(r"\b(CRITICAL|HIGH|MEDIUM|LOW|CONCERN)\b", re.IGNORECASE)
_EXEMPT = re.compile(r"legacy|migration|old|outcome", re.IGNORECASE)
_JSON_FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)
_SKIP_EXAMPLE = {"qc-core"}


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
    mds = [md for md in _skill_mds(f) if md.parent.name not in _SKIP_EXAMPLE]
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
    m = ALL_REFS / "qc-watch-manifest.json"
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
    ok, msg = _script_ok(ALL_REFS / "scripts" / "qc_deterministic.sh")
    if not ok:
        return False, f"{msg} (R6)"
    return True, "qc_deterministic.sh executable, --help OK (R6)"


def check_history_script_exists(_f: str | None) -> tuple[bool, str]:
    ok, msg = _script_ok(ALL_REFS / "scripts" / "append_history.py")
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
    if not (ALL_REFS / "supervisor-dispatch.md").exists():
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
    if files[0].resolve() != SCHEMA_FILE.resolve():
        return False, f"schema lives at {files[0]}, expected {SCHEMA_FILE}"
    return True, "1 schema file in qc-core (R13)"


def check_schema_version(_f: str | None) -> tuple[bool, str]:
    if not SCHEMA_FILE.exists():
        return False, "schema file not found (R13)"
    try:
        schema = json.loads(SCHEMA_FILE.read_text())
    except json.JSONDecodeError as e:
        return False, f"schema invalid JSON: {e} (R13)"
    const = schema.get("properties", {}).get("schema_version", {}).get("const")
    if const != "1.1":
        return False, f"schema_version.const is {const!r}, expected '1.1' (R13)"
    return True, '"1.1" (R13)'


def check_qc_core_exists(_f: str | None) -> tuple[bool, str]:
    required = [
        CORE_DIR / "SKILL.md",
        SCHEMA_FILE,
        CORE_DIR / "references" / "qc-profile.schema.json",
        CORE_DIR / "scripts" / "qc.py",
        CORE_DIR / "scripts" / "verify_ledger.py",
        CORE_DIR / "workflows" / "discovery-verify.js",
    ]
    missing = [str(p.relative_to(SKILLS_DIR)) for p in required if not p.exists()]
    if missing:
        return False, f"qc-core missing {missing}"
    return True, "qc-core present"


def check_single_compute_verdict(_f: str | None) -> tuple[bool, str]:
    hits = []
    for path in SKILLS_DIR.rglob("*"):
        if path.suffix not in {".py", ".sh", ".md"} or "__pycache__" in path.parts:
            continue
        if path.name in {"test_core.py", "verify_skills.py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"^def compute_verdict\b", text, re.MULTILINE) or re.search(
            r"^compute_verdict\(\)", text, re.MULTILINE
        ):
            hits.append(str(path.relative_to(SKILLS_DIR)))
    if hits != ["qc-core/scripts/qc.py"]:
        return False, f"compute_verdict defined in {hits}, expected only qc-core/scripts/qc.py"
    return True, "one compute_verdict (qc.py)"


def check_skills_load_core(f: str | None) -> tuple[bool, str]:
    missing = []
    for md in _skill_mds(f):
        if md.parent.name == "qc-core":
            continue
        if "qc-core" not in md.read_text():
            missing.append(md.parent.name)
    if missing:
        return False, f"skills that never mention qc-core: {missing}"
    return True, "every specialization names qc-core"


def check_fixtures_exist(_f: str | None) -> tuple[bool, str]:
    missing = []
    for name in ("hardening", "coherence", "docs"):
        expected = CORE_DIR / "fixtures" / name / "expected.json"
        repo = CORE_DIR / "fixtures" / name / "repo"
        if not expected.is_file():
            missing.append(str(expected.relative_to(SKILLS_DIR)))
        if not repo.is_dir():
            missing.append(str(repo.relative_to(SKILLS_DIR)))
    if missing:
        return False, f"missing seeded fixtures: {missing}"
    return True, "hardening/coherence/docs fixtures present"


def check_legal_order_documented(_f: str | None) -> tuple[bool, str]:
    md = (SKILLS_DIR / "qc-all" / "SKILL.md").read_text() if (SKILLS_DIR / "qc-all" / "SKILL.md").exists() else ""
    core = (CORE_DIR / "SKILL.md").read_text() if (CORE_DIR / "SKILL.md").exists() else ""
    text = md + "\n" + core
    for skill in ("qc-packaging", "qc-hardening", "qc-coherence", "qc-docs"):
        if skill not in text:
            return False, f"{skill} missing from suite-order docs"
    if "qc-hardening" in md and md.find("qc-hardening") > md.find("qc-docs") and "qc-docs" in md:
        # order in the execution list should be packaging, hardening, coherence, docs
        pass
    if not re.search(r"qc-packaging.+qc-hardening.+qc-coherence.+qc-docs", text, re.S):
        return False, "legal order qc-packaging → qc-hardening → qc-coherence → qc-docs not documented"
    return True, "legal suite order documented"


_MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_PY_SKILLS_CMD = re.compile(r"python3\s+(skills/qc-core/scripts/[A-Za-z0-9_.-]+\.py)")
_README_FORBIDDEN = (
    (re.compile(r"self-contained", re.I), "claims a specialization is self-contained"),
    (re.compile(r"\bhistorical\b", re.I), "labels reconstruction PDFs as historical"),
    (re.compile(r"may lag", re.I), "says reconstruction PDFs may lag"),
    (re.compile(r"\.hardening-profile\.md"), "presents .hardening-profile.md as current"),
    (re.compile(r"\.structural-integrity\.md"), "presents .structural-integrity.md as current"),
)
_LANDING_PDFS = ("qc-core", "qc-hardening", "qc-coherence", "qc-docs")
_LANDING_PRODUCTS = (
    "qc-core",
    "qc-hardening",
    "qc-coherence",
    "qc-docs",
    "qc-packaging",
    "qc-all",
)
_PDF_FORBIDDEN = (
    ".hardening-profile.md",
    ".structural-integrity.md",
    "from qc-all",
    'schema_version "1.0"',
    "schema_version 1.0",
)


def _repo_root() -> Path:
    return SKILLS_DIR.parent


def _is_pack_checkout() -> bool:
    """True only when qc-core sits inside the GitHub pack (README + reconstruction PDFs).

    A standalone port is qc-core plus specializations under an agent skills dir.
    That layout has no pack README; landing checks must skip, not raise.
    """
    root = _repo_root()
    return (root / "README.md").is_file() and (root / "docs" / "qc-core.pdf").is_file()


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to extract landing PDFs") from exc
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def check_readme_docs_contract(_f: str | None) -> tuple[bool, str]:
    if not _is_pack_checkout():
        return True, "landing checks skipped (not the qc pack checkout)"
    readme_path = _repo_root() / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    missing_products = [name for name in _LANDING_PRODUCTS if name not in text]
    if missing_products:
        return False, f"README omits products: {missing_products}"
    if "npx skills add" not in text:
        return False, "README omits install path npx skills add"
    if "Antigravity" in text:
        if "~/.gemini/config/skills" not in text:
            return False, "README omits Antigravity load path ~/.gemini/config/skills"
        if re.search(r"Antigravity\s*\|\s*`~/\.agents/skills/`", text):
            return False, "README lists Antigravity global as ~/.agents/skills/"
    if ".qc-profile.json" not in text:
        return False, "README omits .qc-profile.json"
    if ".qc-findings/" not in text:
        return False, "README omits .qc-findings/"
    if not re.search(r"qc-packaging.+qc-hardening.+qc-coherence.+qc-docs", text, re.S):
        return False, "README missing legal suite order"
    hits = [msg for pat, msg in _README_FORBIDDEN if pat.search(text)]
    if hits:
        return False, "; ".join(hits)
    if "```mermaid" not in text:
        return False, "README omits suite mermaid diagram"
    if "## What it does not do" not in text:
        return False, "README omits What it does not do"
    return True, "README names six products, install path, profile, order; diagram and does-not; no pre-core claims"


def check_readme_links_exist(_f: str | None) -> tuple[bool, str]:
    if not _is_pack_checkout():
        return True, "landing checks skipped (not the qc pack checkout)"
    readme_path = _repo_root() / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    missing = []
    for target in _MD_LINK.findall(text):
        href = target.strip()
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        href = href.split("#", 1)[0]
        if not href:
            continue
        dest = (_repo_root() / href).resolve()
        try:
            dest.relative_to(_repo_root().resolve())
        except ValueError:
            missing.append(href)
            continue
        if not dest.exists():
            missing.append(href)
    if missing:
        return False, f"README links missing: {missing}"
    return True, "README markdown links resolve"


def check_readme_python_commands(_f: str | None) -> tuple[bool, str]:
    if not _is_pack_checkout():
        return True, "landing checks skipped (not the qc pack checkout)"
    readme_path = _repo_root() / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    scripts = list(dict.fromkeys(_PY_SKILLS_CMD.findall(text)))
    if not scripts:
        return False, "README has no python3 skills/qc-core/scripts/ commands"
    missing = [s for s in scripts if not (_repo_root() / s).is_file()]
    if missing:
        return False, f"README commands not on disk: {missing}"
    return True, f"{len(scripts)} README python3 skills/ commands exist"


def check_landing_pdfs(_f: str | None) -> tuple[bool, str]:
    if not _is_pack_checkout():
        return True, "landing checks skipped (not the qc pack checkout)"
    docs = _repo_root() / "docs"
    problems = []
    for name in _LANDING_PDFS:
        path = docs / f"{name}.pdf"
        if not path.is_file():
            problems.append(f"missing {path.relative_to(_repo_root())}")
            continue
        try:
            text = _extract_pdf(path)
        except Exception as exc:  # noqa: BLE001 — extraction failure is a docs-contract fail
            problems.append(f"{path.name} extract failed: {exc}")
            continue
        if not text.strip():
            problems.append(f"{path.name} extracted empty text")
            continue
        if "qc-core" not in text:
            problems.append(f"{path.name} missing qc-core")
        if ".qc-profile.json" not in text:
            problems.append(f"{path.name} missing .qc-profile.json")
        for tok in _PDF_FORBIDDEN:
            if tok in text:
                problems.append(f"{path.name} still contains {tok!r}")
        if name == "qc-docs":
            if "Handoff Readiness" not in text:
                problems.append("qc-docs.pdf missing Handoff Readiness")
            if not re.search(r"all four gates", text, re.I):
                problems.append("qc-docs.pdf missing four-gate completion bar")
    if problems:
        return False, "; ".join(problems)
    return True, "landing PDFs extractable; current tokens present; pre-core tokens absent"


def check_core_self_test(_f: str | None) -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, str(CORE_DIR / "scripts" / "test_core.py")],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        tail = (r.stdout or r.stderr)[-400:]
        return False, f"test_core.py failed:\n{tail}"
    return True, "test_core.py PASS"


REGISTRY: list[tuple[str, object]] = [
    ("severity_vocabulary_in_skills", check_severity_vocabulary_in_skills),
    ("example_finding_blocks", check_example_finding_blocks),
    ("qc_hardening_size", check_qc_hardening_size),
    ("qc_hardening_references", check_qc_hardening_references),
    ("qc_structural_deleted", check_qc_structural_deleted),
    ("qc_coherence_absorbed_structural", check_qc_coherence_absorbed_structural),
    ("watch_manifest_exists", check_watch_manifest_exists),
    ("deterministic_script_exists", check_deterministic_script_exists),
    ("history_script_exists", check_history_script_exists),
    ("qc_all_size", check_qc_all_size),
    ("no_prose_step_orchestration", check_no_prose_step_orchestration),
    ("supervisor_dispatch_single_source", check_supervisor_dispatch_single_source),
    ("rollup_provenance_example", check_rollup_provenance_example),
    ("schema_single_source", check_schema_single_source),
    ("schema_version", check_schema_version),
    ("qc_core_exists", check_qc_core_exists),
    ("single_compute_verdict", check_single_compute_verdict),
    ("skills_load_core", check_skills_load_core),
    ("fixtures_exist", check_fixtures_exist),
    ("legal_order_documented", check_legal_order_documented),
    ("readme_docs_contract", check_readme_docs_contract),
    ("readme_links_exist", check_readme_links_exist),
    ("readme_python_commands", check_readme_python_commands),
    ("landing_pdfs", check_landing_pdfs),
    ("core_self_test", check_core_self_test),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify qc-* skill artifacts")
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
        passed, msg = fn(args.skill)  # type: ignore[operator]  # REGISTRY values are untyped callables
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
