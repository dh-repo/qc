---
name: qc-packaging
description: Use for production packaging of an existing Python repository. Trigger on phrases like "production packaging", "package this repo", "prepare for release", "public-ready", "release-ready", "package for distribution", "open-source packaging", "professionalize this repo", or when packaging polish is needed because pyproject.toml, README, CI, .editorconfig, or .gitattributes are missing or weak. Do not use for feature work, new project scaffolding, or runtime debugging.
---

# Production Packaging for Public Release

**REQUIRED:** Load `qc-core` first. Ledger, verdict, deferred vocabulary, and suite order live there. This skill wraps an existing Python repo for distribution. It runs first in `qc-all`.

Package an existing Python project for public release without altering any functional code. Adds packaging metadata, documentation, CI, and developer tooling artifacts only.

**Core principle:** The codebase is finished. This skill wraps it for distribution. Zero functional changes, zero domain logic changes, zero test assertion changes.

## When to Use

- Project has working code and passing tests but lacks professional packaging
- Repository is about to go public or be shared externally
- Missing any of: pyproject.toml, .editorconfig, .gitattributes, comprehensive .gitignore, README, CI workflow, architecture diagrams

**Do not use when:** feature work is in progress, creating a new project from scratch, or the project is not Python-based.

## Process

**IMPORTANT:** Read the entire codebase first. Understand what it does, how it is structured, what its entry points are, what its dependencies are, and how its tests run. Do not start packaging until you have a complete mental model.

Run this from the root of the working project.

### Step 1: PYPROJECT.TOML

Create or update `pyproject.toml`.

**If pyproject.toml already exists:** Preserve all existing sections you are not explicitly updating. Do not overwrite `[build-system]`, `[tool.setuptools]`, `[tool.hatch]`, `[tool.poetry]`, or any other tool configuration that already works. Merge new fields into existing sections. If the project uses Poetry (`[tool.poetry]`), work within Poetry's format rather than forcing PEP 621 `[project]` metadata.

**[project] metadata:**
- `name`, `version`, `description`, `requires-python`, `license`, `authors`

**[project.dependencies]:**
- Only what the application needs at runtime (imports used by non-test, non-dev code)

**[project.optional-dependencies] split by concern:**

| Extra | Contents |
|-------|----------|
| `db` | Database/persistence dependencies (if applicable) |
| `dev` | Linting, formatting, type checking: ruff, mypy |
| `test` | Test runners and test-only deps: pytest, aiosqlite, etc. |

**[project.scripts]:**
- All CLI entry points discovered in the codebase (functions with `if __name__ == '__main__'` blocks, existing console_scripts, argparse/click/typer entry points)
- Do NOT create new wrapper scripts or `__main__.py` files that do not already exist

**[tool.ruff]:** Linting and formatting configuration.

**[tool.mypy]:** Type checking configuration.

**[tool.pytest.ini_options]:** Configure if using pytest (testpaths, verbosity).

**[tool.coverage]:** Set `fail_under = 90` (or appropriate threshold for the project).

**requirements.txt reconciliation:**
- If `requirements.txt` exists AND `function_app.py` exists: keep requirements.txt for Azure Functions compatibility
- If `requirements.txt` exists but no Azure Functions: remove it, pyproject.toml is the single source

### Step 2: EDITORCONFIG AND GITATTRIBUTES

**.editorconfig:**
```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml,json,html,css,js}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

**.gitattributes:**
```
* text=auto eol=lf
*.pdf binary
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.sqlite binary
*.db binary
```

Add linguist overrides if needed (e.g., exclude generated fixtures from language stats).

### Step 3: GITIGNORE

Create or update `.gitignore` covering all of:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Environment
.env
*.local
local.settings.json

# Project-specific (adapt per project)
# private fixtures, generated test output, etc.
```

**Critical:** Remove any already-committed files that should be ignored (e.g., `.DS_Store`). Use `git rm --cached` to untrack without deleting.

### Step 4: PROVENANCE CLEANUP

Scrub the repository of artifacts that signal AI-generated or AI-assisted authorship. The goal is a repository that reads as professionally authored with no tooling provenance visible.

**Scan and remove/rewrite:**

- **Co-Authored-By lines** in git commit messages referencing AI models (Claude, GPT, Copilot, etc.). These are in committed history and cannot be removed, but flag them for the user. In any new commits made by this skill, do NOT include Co-Authored-By lines.
- **Comments and docstrings** containing phrases like "generated by", "created by AI", "written by Claude/GPT/Copilot", "AI-assisted", or similar attribution markers. Remove the attribution phrase; keep the comment if the rest is useful.
- **README sections** or badges referencing AI generation ("Built with Claude", "Generated by GPT", Copilot badges, etc.). Remove entirely.
- **File headers** with AI tool credits. Remove the credit line; keep any license headers intact.
- **CHANGELOG or commit message templates** with AI co-author defaults. Clean them.
- **Boilerplate phrases** characteristic of AI output that weaken professional tone: "I'd be happy to", "Here's a", "Let me know if", "Feel free to", "As an AI", "Note:", "Important:", overuse of "robust", "comprehensive", "streamlined", "leverage". Rewrite in direct, declarative voice per the README style rules.
- **Overly cautious hedging** in documentation: "This might", "You could potentially", "It's worth noting that". Replace with direct statements.
- **Unnecessary inline explanations** that read like a tutorial rather than reference documentation. Tighten to professional reference style.

**Scope:** This cleanup applies to all files this skill creates or rewrites (README, CHANGELOG, SECURITY.md, CI workflow, pyproject.toml comments). It also applies to existing documentation files (docs/*.md) that will be referenced from the README. Do NOT modify application source code, test files, or functional code comments to remove AI markers. If AI attribution exists in source code, flag it for the user.

**Git history:** AI co-author lines in existing git commits cannot be removed without history rewriting. Note their presence in the validation output and let the user decide whether to rebase.

### Step 5: DOCUMENTATION (SVG DIAGRAMS)

Create `/docs` directory if it does not exist.

**Required diagrams (minimum 4, maximum 8):**

| Diagram | Purpose |
|---------|---------|
| Architecture overview | Top-to-bottom system flow showing all major components and their connections |
| Problem illustration | What the system solves, ideally as a left/right comparison (wrong path vs correct path) |
| Key internal mechanism | The most important engine, pipeline, or algorithm in the codebase |
| Test coverage map | What the test suites cover, organized by fixture/module, with badge-style counts |

Additional diagrams only if a concept is genuinely unclear without one (decision flowcharts, data routing, pipeline stages). Do not create diagrams for concepts that are self-evident from the code or README text.

**All SVGs must follow the design system defined in `SVG_DESIGN_SYSTEM.md` (same directory as this skill).** Every diagram is self-contained, dark-background, and uses the shared color palette, font stack, and CSS class conventions. Read that file before creating any SVG.

### Step 6: README.MD

Write or rewrite `README.md`. The README tells a story: what the problem is, how this solves it, then progressively deeper detail. Every conceptual section gets its own SVG diagram inline.

**Required sections (always include):**

```
# Project Name                          <- H1, one bold tagline below
[paragraph: problem statement]
[paragraph: solution statement]
![Architecture](docs/architecture.svg)  <- hero diagram
---
## Quick Start                          <- install profiles table
---
## Architecture                         <- SVG embedded (can reuse hero)
  ### Subsections as needed             <- H3 only, tables for structured data
---
## Key Files                            <- categorical H3 sub-tables
  ### Core Engine                       <- File | Purpose table
  ### Configuration and Infrastructure  <- File | Purpose table
  ### Tests                             <- File | Purpose table
  ### Documentation                     <- File | Purpose table
---
## Test Suite                           <- SVG test coverage map
---
## Security                             <- link to SECURITY.md if exists
---
> **Scope note.**                       <- blockquote at the very end
```

**Conditional sections (include when applicable):**

| Section | Include when |
|---------|-------------|
| `## The Problem` with SVG | The problem domain benefits from visual explanation (e.g., before/after comparison) |
| `## [Engine/Core Mechanism]` with SVG | The project has a non-trivial internal algorithm or pipeline |
| `## Integration and Setup` | The project requires deployment, configuration, or external service setup |
| `## [Operations sections]` | The project has audit tools, demo modes, corpus management, etc. |
| `## Cost` | The project uses paid services (APIs, cloud resources) |
| `## Troubleshooting` | Known failure modes exist that benefit from documentation |
| `## Team Handoff` | The project is being transferred to another team |

**README style rules:**
- H1 appears once (project name only). Every H2 preceded by `---`. H3 within H2 only. No H4+.
- No badges, shields, TOC, emojis, or exclamation marks.
- No em dashes. Use commas, semicolons, or separate sentences.
- SVGs embedded with markdown image syntax: `![Alt text sentence](docs/filename.svg)`
- Tables for all structured data (fields, settings, files, modes, endpoints).
- Code blocks tagged `bash` only (no `python`, `json`, etc.). No `$` prompts.
- Technical, direct, declarative. No hedging ("might", "could try").
- Third person and passive: "The engine analyzes", "The generator derives". No "we" or "you."
- Bold for key term introductions: "**Flag-based extraction.**"
- Inline code for field names, values, file paths, CLI commands.
- Failure modes stated bluntly. Limitations acknowledged explicitly.
- Paragraphs are dense but short (3-5 sentences typical).
- No AI attribution markers anywhere in the README ("generated by", "built with Claude/GPT", AI badges, etc.).

### Step 7: GITHUB ACTIONS CI

Create `.github/workflows/ci.yml`:

- **Job name:** `quality`
- **Runs on:** `ubuntu-latest`
- **Trigger:** push and pull_request (all branches)
- **Matrix:** minimum supported Python version + latest stable (e.g., `[3.11, 3.12]`)
- **Timeout:** 10 minutes
- **Steps:** checkout, setup-python, pip install with full dev extras, ruff check, ruff format --check, mypy (if type hints present), pytest/unittest with coverage, `python -m build`, `twine check dist/*`
- If the project has self-generating test fixtures, generate them before tests
- If the project has a CLI entry point, add a smoke test step (e.g., `lefturn --help`)
- One job. No deployment steps. CI validates code quality, test passage, and build integrity only.

### Step 8: SUPPORTING DOCUMENTS

Create if they do not exist:

- **SECURITY.md** - Responsible disclosure instructions, scope of security considerations, contact method. Referenced from the README Security section.
- **CHANGELOG.md** - Version history. Start with current version if new; preserve existing entries if updating.

### Step 9: VALIDATE

Run all checks and confirm:

| Check | Command / Action |
|-------|-----------------|
| Install | `pip install -e .` in a clean venv (or `pip install -e ".[dev,test]"`). Verify it completes without error. Every `[project.scripts]` entry resolves. |
| Lint | `ruff check .` -- fix issues ONLY in files created or modified by this skill. Report application code issues to the user without fixing. |
| Format | `ruff format --check .` -- same scope rule. |
| Tests | `pytest -v` -- all must pass. If no tests exist (exit code 5), note in README and continue. |
| Build | `python -m build && twine check dist/*` -- verify the built artifact is valid. |
| README | No broken image links, no malformed tables. |
| .gitignore | No .DS_Store, no __pycache__, no local secrets committed. |
| Provenance | Grep for AI attribution markers (Co-Authored-By AI, "generated by", "written by Claude/GPT", etc.) in all non-source files. Report any found in source code to user. |
| Orphan audit | List anything in the codebase not covered by the README file listing. Report to user; do not delete or modify. |

**Validation scope:** If ruff or mypy flag issues in application code, list them for the user as a post-packaging recommendation. Do NOT fix them yourself. This is packaging, not refactoring.

## Output Contract

qc-core ledger at `.qc-findings/qc-packaging.json`. Packaging hits are `confidence: mechanical` or `pattern`. Verify: `python3 ../qc-core/scripts/verify_ledger.py .qc-findings/qc-packaging.json`.

**Severity vocabulary:**

| Legacy term | P-scale equivalent |
|:---|:---|
| Blocks install or build | P0 |
| Blocks release (missing required metadata, broken CI) | P1 |
| Reduces quality (missing optional sections, weak CI) | P2 |
| Minor polish (cosmetic gaps, style) | P3 |

```json
{
  "schema_version": "1.1",
  "skill": "qc-packaging",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "P1.1",
      "severity": "P1",
      "confidence": "mechanical",
      "file": "pyproject.toml",
      "line": 12,
      "what": "Missing [project.urls] table; PyPI page will lack homepage/repo links",
      "fix": "Add [project.urls] with Homepage and Repository keys",
      "fixed": true
    }
  ],
  "verdict": "READY_WITH_DEBT"
}
```

Verdict math is qc-core (open P0 policy for this skill). A fixed P1 is `READY_WITH_DEBT`. Suite human-gate still blocks on any P0.

## Edge Cases

| Scenario | What to do |
|----------|-----------|
| **Monorepo with multiple packages** | Package the root only. Note sub-packages in the README scope section. Do not create multiple pyproject.toml files. |
| **Project has no tests** | Skip pytest in CI. Note "no test suite" in the README test section. Do not create tests. |
| **Existing Makefile or tox.ini** | Preserve them. Do not create conflicting task definitions. Note their existence in the README. |
| **Poetry or PDM project** | Work within the existing tool's format. Do not convert `[tool.poetry]` to `[project]`. Add missing metadata within the existing format. |
| **src/ layout** | Ensure `[tool.setuptools.packages.find]` includes `where = ["src"]` if using setuptools. Do not restructure to flat layout. |
| **C extensions or compiled deps** | Note build requirements in README. Do not modify `setup.py` or build scripts. |
| **Existing CI workflow** | Merge packaging validation steps into the existing workflow rather than overwriting it. Preserve deployment, secrets, and environment config. |
| **No environment variables** | Skip the Configuration section in the README, or write "No configuration required." |
| **Azure Functions project** | Keep `requirements.txt` for compatibility. Create `local.settings.example.json` as template with placeholder values. Note in README that `local.settings.json` is gitignored. |
| **Committed .DS_Store or junk** | `git rm --cached .DS_Store` before updating .gitignore. |
| **requirements.txt without Azure Functions** | Delete it. pyproject.toml is the single source. |

## Red Flags - STOP

If you catch yourself doing any of these, stop. This skill is packaging only.

- Changing a function signature, test assertion, or import path in application code
- Adding a new feature "while packaging"
- Refactoring code for "clarity"
- Changing how tests work rather than how they are run
- "Fixing" ruff/mypy errors in application code
- Creating new `__init__.py`, `__main__.py`, or wrapper scripts that did not exist
- Rewriting imports to match a "better" package structure
- Adding default values to application code to "match the README documentation"

| Rationalization | Reality |
|-----------------|---------|
| "I need to add `__init__.py` so the package is importable" | That is a functional change. If it was not importable before, flag it; do not fix it. |
| "ruff found lint errors and the skill says fix any issues" | The skill says fix issues in packaging files only. Report application lint errors to the user. |
| "The import path won't work with the new package structure" | Do not change the package structure. Packaging wraps what exists. |
| "I'll just clean up this one function while I'm here" | No. Not even one line of functional code. |
| "The tests were already passing so validation is redundant" | Run validation anyway. Packaging files can break tests (e.g., ruff config changes). |
| "The project has no tests, so I should add a basic one" | No. Note the absence in the README. Do not create test files. |
