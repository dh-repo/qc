#!/usr/bin/env python3
"""Unit tests for qc-core invariants. Run: python3 test_core.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qc import (  # noqa: E402
    DEFERRED_CODES,
    LEGAL_ORDER,
    atomic_write_json,
    compute_verdict,
    dual_vote_recommendation,
    invariant_ok,
    needs_scenario,
    parse_deferred,
    skip_dual_verify,
    suite_verdict,
)
from partition import git_changed, partition, reexam_set  # noqa: E402
from verify_port import verify as verify_port  # noqa: E402
from verify_profile import problems as profile_problems  # noqa: E402


class Fail(Exception):
    pass


passed = 0
failed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))


def test_verdict() -> None:
    print("verdict")
    check("fixed P0 presence-blocks", compute_verdict([{"severity": "P0", "fixed": True}]) == "NOT_READY")
    check("open P1 blocks", compute_verdict([{"severity": "P1", "fixed": False}]) == "NOT_READY")
    check(
        "deferred P1 is debt",
        compute_verdict([{"severity": "P1", "fixed": False, "deferred_because": "needs-owner: x"}])
        == "READY_WITH_DEBT",
    )
    check("open P2 is debt", compute_verdict([{"severity": "P2", "fixed": False}]) == "READY_WITH_DEBT")
    check("fixed P2 is ready", compute_verdict([{"severity": "P2", "fixed": True}]) == "READY")
    check("P3 never blocks", compute_verdict([{"severity": "P3", "fixed": False}]) == "READY")
    check("empty is ready", compute_verdict([]) == "READY")
    check(
        "open-policy fixed P0 is ready",
        compute_verdict([{"severity": "P0", "fixed": True}], p0_policy="open") == "READY",
    )


def test_suite_algebra() -> None:
    print("suite algebra")
    hardening = {
        "verdict": "NOT_READY",
        "findings": [{"severity": "P0", "fixed": True, "id": "F2.1", "file": "a.py", "what": "secret", "fixed": True}],
    }
    # the dict above duplicated fixed; rebuild cleanly
    hardening = {
        "verdict": "NOT_READY",
        "findings": [
            {"id": "F2.1", "severity": "P0", "file": "a.py", "what": "secret in file", "fixed": True}
        ],
    }
    docs = {"verdict": "READY", "findings": []}
    v, _, sv = suite_verdict({"qc-hardening": hardening, "qc-docs": docs})
    check("skill NOT_READY → suite NOT_READY", v == "NOT_READY")

    packaging = {
        "verdict": "READY",
        "findings": [
            {"id": "P1.1", "severity": "P0", "file": "pyproject.toml", "what": "broken build", "fixed": True}
        ],
    }
    v, _, _ = suite_verdict({"qc-packaging": packaging, "qc-docs": docs})
    check("suite human-gate: any P0 (even fixed, even non-hardening) → NOT_READY", v == "NOT_READY")

    debt = {
        "verdict": "READY_WITH_DEBT",
        "findings": [
            {"id": "F3.1", "severity": "P1", "file": "a.py", "what": "gap", "fixed": False, "deferred_because": "needs-architecture: split"}
        ],
    }
    v, _, _ = suite_verdict({"qc-hardening": debt, "qc-docs": docs})
    check("READY_WITH_DEBT skill → suite READY_WITH_DEBT", v == "READY_WITH_DEBT")

    v, _, _ = suite_verdict({"qc-docs": docs})
    check("all READY → READY", v == "READY")

    v, _, _ = suite_verdict({"qc-docs": docs}, skipped=["qc-docs"])
    check("all skipped → READY", v == "READY")
    check("legal order includes hardening before docs", LEGAL_ORDER.index("qc-hardening") < LEGAL_ORDER.index("qc-docs"))
    check("legal order includes coherence before docs", LEGAL_ORDER.index("qc-coherence") < LEGAL_ORDER.index("qc-docs"))


def test_deferred() -> None:
    print("deferred vocab")
    check("plain code", parse_deferred("needs-architecture") == ("needs-architecture", ""))
    check("code + detail", parse_deferred("needs-owner: product naming")[0] == "needs-owner")
    check("free text rejected", parse_deferred("Requires schema migration") is None)
    check("empty rejected", parse_deferred("") is None)
    check("accepted-debt in vocab", "accepted-debt" in DEFERRED_CODES)


def test_scenario() -> None:
    print("scenario bar")
    check(
        "mechanical P1 exempt",
        needs_scenario({"severity": "P1", "confidence": "mechanical", "id": "F4.1"}) is False,
    )
    check("P1 judgment requires", needs_scenario({"severity": "P1", "id": "F3.1"}) is True)
    check("Carmack id requires", needs_scenario({"severity": "P2", "id": "F12.1"}) is True)
    check("semantic id requires", needs_scenario({"severity": "P2", "id": "M1.1"}) is True)
    check("architectural id requires", needs_scenario({"severity": "P2", "id": "A3.1"}) is True)
    check("ruff P2 mechanical exempt", needs_scenario({"severity": "P2", "confidence": "mechanical", "id": "F4.2"}) is False)


def test_dual_vote() -> None:
    print("dual-vote")
    check("both confirmed → fix", dual_vote_recommendation("confirmed", "confirmed") == "fix")
    check("both real_incoherence → fix", dual_vote_recommendation("real_incoherence", "real_incoherence") == "fix")
    check("split → defer", dual_vote_recommendation("confirmed", "refuted") == "defer")
    check("uncertain → defer", dual_vote_recommendation("confirmed", "uncertain") == "defer")
    check("both refuted → drop", dual_vote_recommendation("refuted", "intentional") == "drop")
    check("mechanical skips verify", skip_dual_verify({"confidence": "mechanical"}) is True)
    check("pattern does not skip", skip_dual_verify({"confidence": "pattern"}) is False)
    check("proven still verifies", skip_dual_verify({"confidence": "proven"}) is False)


def test_invariants() -> None:
    print("CLEAN invariants")
    check("boilerplate rejected", invariant_ok("looks fine") is False)
    check("short rejected", invariant_ok("ok") is False)
    check(
        "substantive accepted",
        invariant_ok("close() holds the lock for the entire mutation of _state") is True,
    )


def test_atomic_write() -> None:
    print("atomic write")
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "ledger.json"
        atomic_write_json(dest, {"ok": True})
        check("file exists", dest.is_file())
        check("content", json.loads(dest.read_text())["ok"] is True)
        leftovers = list(Path(td).glob("*.tmp"))
        check("no tmp leftover", leftovers == [])


def test_partition() -> None:
    print("partition")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "app").mkdir()
        (root / "app" / "a.py").write_text("from app import b\n\n" + ("x = 1\n" * 40), encoding="utf-8")
        (root / "app" / "b.py").write_text("from app import a\n\n" + ("y = 2\n" * 40), encoding="utf-8")
        (root / "app" / "solo.py").write_text("VALUE = 1\n" * 20, encoding="utf-8")
        (root / "app" / "other.ts").write_text("export const z = 1;\n" * 20, encoding="utf-8")
        groups = partition(root, max_loc=800, min_loc=10)
        files_by_group = [set(g["files"]) for g in groups]
        coupled = None
        for g in groups:
            names = set(Path(f).name for f in g["files"])
            if "a.py" in names or "b.py" in names:
                coupled = names
        check("a.py and b.py stay together", coupled is not None and "a.py" in coupled and "b.py" in coupled)
        ts_groups = [g for g in groups if g["language"] == "ts" or any(f.endswith(".ts") for f in g["files"])]
        check(
            "language boundary respected",
            any(f.endswith("other.ts") for g in groups for f in g["files"]),
        )
        mixed = [g for g in groups if any(f.endswith(".py") for f in g["files"]) and any(f.endswith(".ts") for f in g["files"])]
        check("no py+ts mixed group", mixed == [], str(mixed))
        check("produced groups", len(groups) >= 1)
        _ = files_by_group
        result = reexam_set(root, ["app/a.py"], {"app/b.py"})
        check("changed a.py listed", "app/a.py" in result["changed"] or any(f.endswith("a.py") for f in result["changed"]))
        check(
            "hot-spot neighbor b.py is mandatory",
            any(f.endswith("b.py") for f in result["mandatory_neighbors"])
            or any(f.endswith("b.py") for f in result["reexam"]),
        )
        solo = reexam_set(root, ["app/a.py"], {"app/solo.py"})
        check(
            "unrelated hot spot is not a neighbor",
            not any(f.endswith("solo.py") for f in solo["mandatory_neighbors"]),
        )


def test_git_changed() -> None:
    print("git changed")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        import subprocess as sp

        git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
        sp.run([*git, "init"], cwd=root, check=True, capture_output=True)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        sp.run([*git, "add", "a.py"], cwd=root, check=True, capture_output=True)
        sp.run([*git, "commit", "-m", "one"], cwd=root, check=True, capture_output=True)
        sha = sp.check_output([*git, "rev-parse", "HEAD"], cwd=root, text=True).strip()
        (root / "b.py").write_text("y = 2\n", encoding="utf-8")
        sp.run([*git, "add", "b.py"], cwd=root, check=True, capture_output=True)
        sp.run([*git, "commit", "-m", "two"], cwd=root, check=True, capture_output=True)
        paths = git_changed(root, sha)
        check("new file in diff", any(p.endswith("b.py") for p in paths))
        check("old file not in diff", not any(p.endswith("a.py") for p in paths))
        check("HEAD..HEAD is empty", git_changed(root, "HEAD") == [])


def test_profile() -> None:
    print("profile")
    good = {
        "schema_version": "1.1",
        "examination": {
            "qc-hardening": {
                "app/clean.py": {
                    "status": "EXAMINED",
                    "invariant": "add(a, b) returns the numeric sum of its two arguments",
                    "assumptions": "both arguments are ints; no overflow is in scope for this module",
                    "sequence_risk": "add is pure; no call sequence can corrupt hidden state",
                }
            }
        },
        "deferred": [{"id": "F12.1", "skill": "qc-hardening", "severity": "P1", "code": "needs-architecture"}],
        "clusters": [{"id": "cl-1", "skill": "qc-coherence", "symbols": ["run_id", "execution_id"], "rationale": "same request identifier"}],
        "canonical_forms": [{"concept": "request identifier", "canonical": "run_id", "aliases": ["execution_id"], "cluster_id": "cl-1"}],
        "invariants": [{
            "id": "inv-1",
            "statement": "add(a, b) returns the numeric sum with no hidden state",
            "source": "carmack",
            "source_ref": "app/clean.py",
            "enforced_by": "tests/test_clean.py::test_add",
            "status": "enforced",
        }],
        "layer_model": {"layers": ["app"], "rules": ["app may import the stdlib only"]},
    }
    check("good profile", profile_problems(good) == [])
    sentence_only = {
        "schema_version": "1.1",
        "examination": {
            "qc-hardening": {
                "app/clean.py": {
                    "status": "EXAMINED",
                    "invariant": "add(a, b) returns the numeric sum of its two arguments",
                }
            }
        },
    }
    check(
        "Carmack EXAMINED rejects one-sentence-only",
        any("Carmack 5Q" in p for p in profile_problems(sentence_only)),
    )
    bad = {
        "schema_version": "1.1",
        "examination": {"qc-hardening": {"app/x.py": {"status": "EXAMINED", "invariant": "ok"}}},
        "deferred": [{"id": "F1", "skill": "qc-hardening", "severity": "P1", "code": "because I said so"}],
        "clusters": [{"id": "cl-1", "skill": "qc-coherence", "symbols": [], "rationale": "x"}],
        "invariants": [{"id": "inv-x", "statement": "ok", "source": "guess", "status": "maybe"}],
        "canonical_forms": [{"concept": "", "canonical": ""}],
        "pass_debt": [{"finding_id": "F12.1", "found_by": "12", "should_have_been": "1", "module": "x.py", "why_missed": "missed"}],
    }
    probs = profile_problems(bad)
    check("Carmack EXAMINED flagged", any("Carmack 5Q" in p or "invariant" in p for p in probs))
    check("closed vocab flagged", any("closed vocabulary" in p for p in probs))
    check("empty cluster symbols flagged", any("symbols" in p for p in probs))
    check("registry source flagged", any("invariants" in p and "source" in p for p in probs))
    check("canonical form flagged", any("canonical_forms" in p for p in probs))
    check("pass_debt why_missed flagged", any("why_missed" in p for p in probs))


def test_port_contract() -> None:
    print("port contract")
    expected = {
        "skill": "qc-hardening",
        "must_find": [
            {"file_substring": "secret.py", "severity": "P0", "what_contains": ["sk-"]},
        ],
        "must_mark_clean": ["app/clean.py"],
    }
    ledger = {
        "findings": [
            {"id": "F2.1", "severity": "P0", "file": "app/secret.py", "what": "hardcoded sk-live key", "fixed": True}
        ],
        "examined": [
            {
                "artifact": "app/clean.py",
                "invariant": "add(a, b) returns the numeric sum of its two arguments",
            }
        ],
    }
    profile = {
        "examination": {
            "qc-hardening": {
                "app/clean.py": {
                    "status": "EXAMINED",
                    "invariant": "add(a, b) returns the numeric sum of its two arguments",
                    "assumptions": "both arguments are ints; callers do not share mutable state",
                    "sequence_risk": "add is pure; no call order can corrupt hidden state",
                }
            }
        }
    }
    check("seeded recovery", verify_port(expected, ledger, profile) == [])
    miss = {"findings": [], "examined": []}
    check("missing seed fails", len(verify_port(expected, miss, None)) >= 1)


def test_vendored_landing_checks_skip() -> None:
    print("vendored landing checks")
    import verify_skills as vs

    orig = vs._repo_root
    vs._repo_root = lambda: Path("/tmp/qc-not-a-pack-checkout")
    try:
        ok_docs, msg_docs = vs.check_readme_docs_contract(None)
        ok_links, msg_links = vs.check_readme_links_exist(None)
        ok_cmds, msg_cmds = vs.check_readme_python_commands(None)
        ok_pdfs, msg_pdfs = vs.check_landing_pdfs(None)
        check("docs contract skips", ok_docs and "skipped" in msg_docs, msg_docs)
        check("links skip without raise", ok_links and "skipped" in msg_links, msg_links)
        check("python commands skip", ok_cmds and "skipped" in msg_cmds, msg_cmds)
        check("pdfs skip", ok_pdfs and "skipped" in msg_pdfs, msg_pdfs)
    finally:
        vs._repo_root = orig


def test_docs_contract() -> None:
    print("docs contract")
    from verify_skills import (  # noqa: E402
        check_landing_pdfs,
        check_readme_docs_contract,
        check_readme_links_exist,
        check_readme_python_commands,
    )

    for name, fn in (
        ("readme names qc-core", check_readme_docs_contract),
        ("readme links exist", check_readme_links_exist),
        ("readme python3 commands exist", check_readme_python_commands),
        ("landing PDFs current", check_landing_pdfs),
    ):
        ok, msg = fn(None)
        check(name, ok, msg)


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    print("test_core.py")
    test_verdict()
    test_suite_algebra()
    test_deferred()
    test_scenario()
    test_dual_vote()
    test_invariants()
    test_atomic_write()
    test_partition()
    test_git_changed()
    test_profile()
    test_port_contract()
    test_vendored_landing_checks_skip()
    test_docs_contract()
    print(f"\n{passed} PASS, {failed} FAIL")
    print("verdict:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
