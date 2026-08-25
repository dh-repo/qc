#!/usr/bin/env python3
"""Import-graph-primary module partitioning for Discovery+Verify.

Priority: local import graph (keep coupled files together) → language
boundary → LOC pack into [min_loc, max_loc] groups.

Usage:
  partition.py [--root .] [--max-loc 800] [--min-loc 200] [--json]
  partition.py --reexam --changed a.py,b.py [--profile .qc-profile.json] [--json]
  partition.py --reexam --since <sha> [--profile .qc-profile.json] [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", ".tox", ".eggs",
}
PY_EXT = {".py"}
JS_EXT = {".js", ".ts", ".tsx", ".mjs", ".cjs"}
SOURCE_EXT = PY_EXT | JS_EXT | {".go", ".rs"}

_JS_FROM = re.compile(r"""from\s+['"]([^'"]+)['"]""")
_JS_IMPORT = re.compile(r"""import\s+['"]([^'"]+)['"]""")
_JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")


def iter_source_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_EXT:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def file_loc(path: Path) -> int:
    try:
        return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def language_of(path: Path) -> str:
    if path.suffix in PY_EXT:
        return "py"
    if path.suffix in JS_EXT:
        return "js"
    return path.suffix.lstrip(".") or "other"


def _py_imports(path: Path, root: Path) -> set[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except (OSError, SyntaxError):
        return set()
    rels: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            rels.add(node.module)
            for alias in node.names:
                if alias.name != "*":
                    rels.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                rels.add(alias.name)
    resolved: set[Path] = set()
    for mod in rels:
        parts = mod.split(".")
        candidates = [
            root.joinpath(*parts).with_suffix(".py"),
            root.joinpath(*parts) / "__init__.py",
            path.parent.joinpath(*parts).with_suffix(".py"),
            path.parent.joinpath(*parts) / "__init__.py",
        ]
        for cand in candidates:
            try:
                cand = cand.resolve()
            except OSError:
                continue
            if cand.is_file() and cand != path.resolve():
                resolved.add(cand)
                break
    return resolved


def _js_imports(path: Path) -> set[Path]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    specs = set(_JS_FROM.findall(text)) | set(_JS_IMPORT.findall(text)) | set(_JS_REQUIRE.findall(text))
    resolved: set[Path] = set()
    for spec in specs:
        if not spec.startswith("."):
            continue
        base = (path.parent / spec).resolve()
        for cand in (base, Path(str(base) + ".js"), Path(str(base) + ".ts"), base / "index.js"):
            if cand.is_file() and cand != path.resolve():
                resolved.add(cand)
                break
    return resolved


def build_graph(files: list[Path], root: Path) -> dict[Path, set[Path]]:
    graph: dict[Path, set[Path]] = {p.resolve(): set() for p in files}
    file_set = set(graph)
    for path in list(graph):
        lang = language_of(path)
        if lang == "py":
            deps = _py_imports(path, root)
        elif lang == "js":
            deps = _js_imports(path)
        else:
            deps = set()
        for dep in deps:
            if dep in file_set:
                graph[path].add(dep)
                graph[dep].add(path)
    return graph


def connected_components(graph: dict[Path, set[Path]]) -> list[list[Path]]:
    seen: set[Path] = set()
    comps: list[list[Path]] = []
    for node in graph:
        if node in seen:
            continue
        stack = [node]
        comp = []
        seen.add(node)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in graph[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))
    return comps


def pack_groups(
    components: list[list[Path]],
    locs: dict[Path, int],
    languages: dict[Path, str],
    max_loc: int,
    min_loc: int,
) -> list[dict]:
    """Pack connected components into groups. Never mix languages.

    Split a component over max_loc along weakest remaining edges by walking in
    path order (LOC tertiary). Merge undersized leftover fragments of the same
    language when the combination stays under max_loc.
    """
    raw: list[tuple[str, list[Path], int]] = []
    for comp in components:
        by_lang: dict[str, list[Path]] = defaultdict(list)
        for p in comp:
            by_lang[languages[p]].append(p)
        for lang, files in by_lang.items():
            files = sorted(files)
            loc = sum(locs[p] for p in files)
            if loc <= max_loc:
                raw.append((lang, files, loc))
                continue
            chunk: list[Path] = []
            chunk_loc = 0
            for p in files:
                ploc = locs[p]
                if chunk and chunk_loc + ploc > max_loc:
                    raw.append((lang, chunk, chunk_loc))
                    chunk, chunk_loc = [], 0
                chunk.append(p)
                chunk_loc += ploc
            if chunk:
                raw.append((lang, chunk, chunk_loc))

    merged: list[tuple[str, list[Path], int]] = []
    for lang, files, loc in sorted(raw, key=lambda t: (t[0], str(t[1][0]))):
        if merged and merged[-1][0] == lang and loc < min_loc and merged[-1][2] + loc <= max_loc:
            prev_lang, prev_files, prev_loc = merged[-1]
            merged[-1] = (prev_lang, prev_files + files, prev_loc + loc)
        else:
            merged.append((lang, files, loc))

    groups = []
    for i, (lang, files, loc) in enumerate(merged, 1):
        rel = [str(p) for p in files]
        label = str(Path(rel[0]).parent) if rel else f"g{i}"
        groups.append({"key": f"g{i}", "label": label, "files": rel, "loc": loc, "language": lang})
    return groups


def partition(root: Path, max_loc: int = 800, min_loc: int = 200) -> list[dict]:
    root = root.resolve()
    files = iter_source_files(root)
    if not files:
        return []
    locs = {p.resolve(): file_loc(p) for p in files}
    languages = {p.resolve(): language_of(p) for p in files}
    graph = build_graph(files, root)
    comps = connected_components(graph)
    groups = pack_groups(comps, locs, languages, max_loc, min_loc)
    for g in groups:
        g["files"] = [str(Path(f).relative_to(root)) for f in g["files"]]
    return groups


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def anchors_from_profile(profile: dict) -> set[str]:
    """Hot-spot artifacts and pass-debt modules — the latent pieces new code can combine with."""
    anchors: set[str] = set()
    for row in profile.get("hot_spots") or []:
        if isinstance(row, dict) and row.get("artifact"):
            anchors.add(str(row["artifact"]).replace("\\", "/"))
        elif isinstance(row, str):
            anchors.add(row.replace("\\", "/"))
    for row in profile.get("pass_debt") or []:
        if isinstance(row, dict) and row.get("module"):
            anchors.add(str(row["module"]).replace("\\", "/"))
    return anchors


def _matches_anchor(rel: str, anchors: set[str]) -> bool:
    name = Path(rel).name
    for a in anchors:
        if rel == a or rel.endswith("/" + a) or name == Path(a).name or a.endswith("/" + name):
            return True
    return False


def reexam_set(root: Path, changed: list[str], anchors: set[str]) -> dict:
    """Changed files plus import-graph neighbors that are already hot spots or pass-debt.

    Unrelated unchanged modules are omitted. This is the Cook #14 rule: new code
    creates combinations with existing latent pieces.
    """
    root = root.resolve()
    files = iter_source_files(root)
    graph = build_graph(files, root)
    rel_of = {p: _rel(root, p) for p in graph}
    by_rel = {rel: p for p, rel in rel_of.items()}

    changed_paths: set[Path] = set()
    for raw in changed:
        key = raw.replace("\\", "/").lstrip("./")
        if key in by_rel:
            changed_paths.add(by_rel[key])
            continue
        for rel, path in by_rel.items():
            if Path(rel).name == Path(key).name or rel.endswith("/" + key):
                changed_paths.add(path)

    neighbors: set[Path] = set()
    for path in changed_paths:
        for nb in graph.get(path, ()):
            if _matches_anchor(rel_of[nb], anchors):
                neighbors.add(nb)

    changed_rel = sorted({rel_of[p] for p in changed_paths if p in rel_of})
    neighbor_rel = sorted({rel_of[p] for p in neighbors if p in rel_of} - set(changed_rel))
    return {
        "changed": changed_rel,
        "mandatory_neighbors": neighbor_rel,
        "reexam": sorted(set(changed_rel) | set(neighbor_rel)),
    }


def git_changed(root: Path, since: str) -> list[str]:
    """Paths changed from ``since`` to HEAD. Empty if *since* is HEAD or unknown."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "diff", "--name-only", f"{since}..HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-loc", type=int, default=800)
    parser.add_argument("--min-loc", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--reexam",
        action="store_true",
        help="Emit changed files plus hot-spot/pass-debt import-graph neighbors",
    )
    parser.add_argument(
        "--changed",
        default="",
        help="Comma-separated paths (from git diff --name-only)",
    )
    parser.add_argument(
        "--since",
        default="",
        help="Git SHA/ref; changed files are git diff --name-only SINCE..HEAD",
    )
    parser.add_argument("--profile", default="", help="Path to .qc-profile.json (anchors)")
    parser.add_argument(
        "--anchors",
        default="",
        help="Comma-separated hot-spot/pass-debt paths if no --profile",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.reexam:
        changed = [c.strip() for c in args.changed.split(",") if c.strip()]
        if args.since:
            changed = list(dict.fromkeys(changed + git_changed(root, args.since)))
        anchors: set[str] = set()
        profile_path = Path(args.profile) if args.profile else root / ".qc-profile.json"
        if profile_path.is_file():
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            anchors |= anchors_from_profile(profile)
        if args.anchors:
            anchors |= {a.strip().replace("\\", "/") for a in args.anchors.split(",") if a.strip()}
        result = reexam_set(root, changed, anchors)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("changed: " + (", ".join(result["changed"]) or "(none)"))
            print("mandatory_neighbors: " + (", ".join(result["mandatory_neighbors"]) or "(none)"))
            print("reexam: " + (", ".join(result["reexam"]) or "(none)"))
        return 0
    groups = partition(root, args.max_loc, args.min_loc)
    if args.json:
        print(json.dumps({"groups": groups}, indent=2))
    else:
        for g in groups:
            print(f"{g['key']} [{g['language']}, {g['loc']} LOC] {g['label']}: {len(g['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
