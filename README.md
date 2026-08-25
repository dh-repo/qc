# qc

Quality-control skills for coding agents.

Source: [github.com/dh-repo/qc](https://github.com/dh-repo/qc)

This is not a hosted product. The agent follows the skill. Same `SKILL.md` trees run in Claude Code, Codex, Grok Build, Cursor, and any other client that speaks the [Agent Skills](https://agentskills.io) format.

`qc-core` is the shared contract: seven laws, ledger schema 1.1, verdict math, unified `.qc-profile.json`, Discovery+Verify, and reexam. Specializations do not reimplement those invariants. Installing a specialization without `qc-core` is incomplete.

---

## Install

Fastest path, any agent:

```bash
npx skills add dh-repo/qc
```

That copies each `skills/<name>/` folder into the agent(s) you have installed. Use `-g` for a user-wide install.

A **standalone** port is `qc-core` plus one specialization (not the full pack):

```bash
npx skills add dh-repo/qc --skill qc-core -g
npx skills add dh-repo/qc --skill qc-hardening -g
```

`npx skills add dh-repo/qc --list` lists skills in this pack. It does not install anything and does not confirm that a skill landed on disk.

### By agent

| Agent | Global install location | Project install location |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex | `~/.codex/skills/` | `.agents/skills/` |
| Grok Build | `~/.grok/skills/` | `.grok/skills/` |
| Cursor / Copilot / Gemini CLI | `~/.cursor/skills/` or `~/.agents/skills/` | `.agents/skills/` |

Manual copy (core first, then the specialization). Destination is the matching row in the table above. Create the destination directory first so the skill folder is not flattened:

```bash
git clone https://github.com/dh-repo/qc.git
mkdir -p ~/.claude/skills
cp -R qc/skills/qc-core ~/.claude/skills/qc-core
cp -R qc/skills/qc-hardening ~/.claude/skills/qc-hardening
```

Claude Code can also load the repo as a plugin (`.claude-plugin/plugin.json` at the root; skills auto-discovered under `skills/`).

The install does not run a QC pass. Say "harden" or `/qc-hardening` in that agent, against the target repo. A Claude plugin load may namespace the same skill as `/qc:qc-hardening`.

---

## Skills

| Skill | Tries to achieve | Use when |
|---|---|---|
| `qc-core` | Shared laws, ledger, verdict, profile, Discovery+Verify | Always, with any other qc-* skill |
| `qc-hardening` | Drive residual concrete failure scenarios under sequences, dual paths, and live adapters to zero or explicit deferral | Feature work is done; before production, release, or merge |
| `qc-coherence` | Guarantee compositional consistency and enforce previously discovered invariants | Several sessions have landed; before a release; `--scope=module` composition checks |
| `qc-docs` | Enable a new engineer or operator to run, diagnose, recover, and hand off the system that exists | README, runbooks, or handoff docs need to match the codebase |
| `qc-packaging` | Wrap an existing Python repo for distribution with no functional changes | Missing pyproject, CI, provenance, or release packaging |
| `qc-all` | Roll the four specializations in legal order to one suite verdict | Full quality gate before a release |

Legal suite order: **qc-packaging → qc-hardening → qc-coherence → qc-docs**.

Slash-style triggers once a skill folder is installed: `/qc-core`, `/qc-hardening`, `/qc-coherence`, `/qc-docs`, `/qc-packaging`, `/qc-all`. Agents also pick them up from the `description` frontmatter. If the repo is loaded as a Claude plugin, the slash form may be `/qc:qc-hardening` instead.

---

## What a run writes (in the target repo)

| Path | Role |
|---|---|
| `.qc-findings/qc-hardening.json` (and siblings) | Per-skill findings ledger, schema 1.1 |
| `.qc-findings/_rollup.json` | Suite verdict from `qc-all` |
| `.qc-history.jsonl` | Bounded run history |
| `.qc-profile.json` | Unified examination, pass debt, deferred findings, invariant registry, canonical forms, layer model, operating facts, truth-map (committed) |
| `.qc-profile.md` | Generated human summary of the profile |

Verdicts are one enum: `READY`, `READY_WITH_DEBT`, `NOT_READY`. Per-skill math lives in `qc-core`. Hardening uses presence P0 (any P0, even fixed, is `NOT_READY`). Packaging, coherence, and docs use open P0 (only an open P0 blocks). The suite rollup is a human-review gate: any P0 in any ledger, fixed or not, or any skill `NOT_READY`, makes the suite `NOT_READY`.

---

## Validation

These scripts check artifacts **after** a skill run. They do not run the 14 hardening passes, coherence lenses, or docs gates. The agent follows `SKILL.md`. `verify_ledger.py` recomputes one skill ledger. `suite_rollup.py` computes the suite verdict. If either disagrees with the written JSON, fix the JSON.

From this repo root, these entry points print usage and exit 0:

```bash
python3 skills/qc-core/scripts/verify_ledger.py --help
python3 skills/qc-core/scripts/verify_profile.py --help
python3 skills/qc-core/scripts/suite_rollup.py --help
python3 skills/qc-core/scripts/partition.py --help
python3 skills/qc-core/scripts/verify_port.py --help
python3 skills/qc-core/scripts/verify_skills.py --help
python3 skills/qc-core/scripts/test_core.py --help
python3 skills/qc-core/scripts/render_profile.py --help
```

After install, the scripts live in the **skill tree**, not inside the target repo. From the target repo, call the installed copy (substitute the destination from the install table; examples below use a global Claude install):

```bash
python3 ~/.claude/skills/qc-core/scripts/verify_ledger.py .qc-findings/qc-hardening.json
python3 ~/.claude/skills/qc-core/scripts/verify_profile.py .qc-profile.json
python3 ~/.claude/skills/qc-core/scripts/suite_rollup.py --findings-dir .qc-findings
python3 ~/.claude/skills/qc-core/scripts/partition.py --reexam --since HEAD~1 --profile .qc-profile.json --json
```

Port acceptance is `verify_port.py` against a **produced** ledger (not `--help`). Seeded fixtures exist for hardening, coherence, and docs. Packaging has no seeded fixture; its port gate is the packaging `SKILL.md` output contract plus `verify_ledger.py` on `.qc-findings/qc-packaging.json`.

```bash
python3 skills/qc-core/scripts/verify_port.py --expected skills/qc-core/fixtures/hardening/expected.json --ledger path/to/ledger.json
python3 skills/qc-core/scripts/verify_port.py --expected skills/qc-core/fixtures/coherence/expected.json --ledger path/to/ledger.json
python3 skills/qc-core/scripts/verify_port.py --expected skills/qc-core/fixtures/docs/expected.json --ledger path/to/ledger.json
```

---

## Documentation

Canonical source is the `SKILL.md` trees. Reconstruction PDFs describe those same trees so a porter has a printable spec; they are not a second design.

| Path | What it covers |
|---|---|
| [`skills/qc-core/SKILL.md`](skills/qc-core/SKILL.md) | Laws, ledger schema 1.1, verdict, `.qc-profile.json`, Discovery+Verify, fixtures |
| [`skills/qc-hardening/SKILL.md`](skills/qc-hardening/SKILL.md) | 14-pass specialization (canonical) |
| [`skills/qc-coherence/SKILL.md`](skills/qc-coherence/SKILL.md) | Coherence S/C/M/A and MS-1–MS-6 (canonical) |
| [`skills/qc-docs/SKILL.md`](skills/qc-docs/SKILL.md) | Docs specialization; four quality gates including Handoff Readiness (canonical) |
| [`skills/qc-packaging/SKILL.md`](skills/qc-packaging/SKILL.md) | Packaging wrap; no seeded `verify_port` fixture |
| [`skills/qc-all/SKILL.md`](skills/qc-all/SKILL.md) | Suite router, skip logic, rollup |
| [`docs/qc-core.pdf`](docs/qc-core.pdf) | Printable reconstruction of `qc-core` |
| [`docs/qc-hardening.pdf`](docs/qc-hardening.pdf) | Printable reconstruction of hardening |
| [`docs/qc-coherence.pdf`](docs/qc-coherence.pdf) | Printable reconstruction of coherence |
| [`docs/qc-docs.pdf`](docs/qc-docs.pdf) | Printable reconstruction of docs |
| [`LICENSE`](LICENSE) | MIT |

`.qc-profile.md` is generated by `python3 skills/qc-core/scripts/render_profile.py`.

---

## Layout

```
skills/
  qc-core/          SKILL.md + schema + scripts + Discovery+Verify + fixtures
  qc-hardening/     14-pass specialization
  qc-coherence/
  qc-docs/
  qc-packaging/
  qc-all/           router, watch manifest, history, supervisor dispatch
docs/
  qc-core.pdf
  qc-hardening.pdf
  qc-coherence.pdf
  qc-docs.pdf
.claude-plugin/     Claude plugin manifest
```

---

## License

MIT. See [LICENSE](LICENSE).

> **Scope note.** This repository is an Agent Skills pack, not a deployable service. There is no hosted runtime, SLA, or operator dashboard. Known limitations of a *target* repo belong in that repo's `.qc-profile.json` after a qc run, not here.
