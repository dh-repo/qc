# qc

Source: [github.com/dh-repo/qc](https://github.com/dh-repo/qc)

Quality-control skills for coding agents. Same `SKILL.md` trees run in Claude Code, Codex, Grok Build, Cursor, and any other client that speaks the [Agent Skills](https://agentskills.io) format.

This is not a hosted product. The agent follows the skill; a small Python harness checks the findings ledger so a standalone run and a full-suite rollup never disagree on the verdict.

## Install

```bash
npx skills add dh-repo/qc
```

That command does not talk to Claude, Codex, or Grok. It clones this repo, finds each `skills/<name>/SKILL.md` tree, detects which agents you have installed, and copies (or symlinks) those folders into the directories those agents already watch. After that, the next session loads `name` + `description` from every `SKILL.md` it finds. A matching prompt, or a slash command like `/qc-hardening`, loads the rest.

Default is **this project** (next to the directory you ran it from). `-g` is **user-wide**, every repo on this machine.

```bash
npx skills add dh-repo/qc -g
npx skills add dh-repo/qc --skill qc-hardening
npx skills add dh-repo/qc --skill qc-hardening -a claude-code -g -y
npx skills add dh-repo/qc --list
```

### Where the files land

| Agent | Global (`-g`) | Project (default) | How it picks the skill up |
|---|---|---|---|
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` | Session start reads frontmatter; slash `/qc-hardening`; auto-invoke from `description` |
| Codex | `~/.codex/skills/<name>/` | `.agents/skills/<name>/` | Same `SKILL.md` format; description decides when to apply |
| Grok Build | `~/.grok/skills/<name>/` | `.grok/skills/<name>/` | Slash `/qc-hardening`; auto-invoke from `description`; reloads when files change |
| Cursor / Copilot / Gemini CLI | `~/.cursor/skills/` or `~/.agents/skills/` | `.agents/skills/` | Same Agent Skills discovery |

Each installed folder is the full skill: `SKILL.md`, `references/`, `scripts/verify_ledger.py`. That is the whole install. No API key, no marketplace account, no runtime registration.

### Manual copy

Equivalent to a per-skill install:

```bash
git clone https://github.com/dh-repo/qc.git
cp -R qc/skills/qc-hardening ~/.claude/skills/
cp -R qc/skills/qc-hardening ~/.codex/skills/
cp -R qc/skills/qc-hardening ~/.grok/skills/
```

Claude Code can also load the repo as a plugin (`.claude-plugin/plugin.json` at the root; skills auto-discovered under `skills/`).

Each skill is self-contained. `npx skills add dh-repo/qc --skill qc-hardening` is enough to run hardening; you do not need the rest of the suite unless you want `qc-all` to roll the four skills up.

The install does **not** run a QC pass. It only plants the instructions. You still say “harden” or `/qc-hardening` in that agent, against whatever repo is open.

## Skills

| Skill | Use when |
|---|---|
| `qc-hardening` | Feature work is done and the code needs a 14-pass production audit before release |
| `qc-coherence` | Several sessions have landed and the tree may have drifted; or `--scope=module` composition checks |
| `qc-docs` | README, runbooks, and handoff docs need to match the codebase that exists |
| `qc-packaging` | A Python repo needs release packaging (pyproject, CI, provenance) with no functional changes |
| `qc-all` | You want the four skills in order, with skip logic and a single rollup verdict |

Slash-style triggers once installed: `/qc-hardening`, `/qc-coherence`, `/qc-docs`, `/qc-packaging`, `/qc-all`. Agents also pick them up from the `description` frontmatter.

## What a run writes (in the *target* repo)

| Path | Role |
|---|---|
| `.qc-findings/qc-hardening.json` (and siblings) | Per-skill findings ledger |
| `.qc-findings/_rollup.json` | Suite verdict from `qc-all` |
| `.qc-history.jsonl` | Bounded run history |
| `.hardening-profile.md` | Hardening hot spots and pass debt (committed) |

Verdicts are one enum: `READY`, `READY_WITH_DEBT`, `NOT_READY`. Any P0 (fixed or not) or any open P1 blocks release. The copy of `scripts/verify_ledger.py` inside each skill recomputes that verdict; if it disagrees with the ledger, fix the ledger.

## Docs

Reconstruction specs — enough to rebuild each skill in another agent without the original tree:

| PDF | What it covers |
|---|---|
| [`docs/qc-hardening.pdf`](docs/qc-hardening.pdf) | 14-pass production audit, Carmack/Chaos, ledger and verdict math |
| [`docs/qc-coherence.pdf`](docs/qc-coherence.pdf) | Cross-cutting drift, S/C/M/A sub-audits, module-scope checks |
| [`docs/qc-docs.pdf`](docs/qc-docs.pdf) | Landing page + operational docs, truth hierarchy, quality gates |

`qc-packaging` and `qc-all` are specified in their `SKILL.md` files; they do not have a separate reconstruction PDF yet.

## Layout

```
skills/
  qc-hardening/     SKILL.md + references + scripts/verify_ledger.py
  qc-coherence/
  qc-docs/
  qc-packaging/
  qc-all/           router, schema, rollup, history
docs/
  qc-hardening.pdf
  qc-coherence.pdf
  qc-docs.pdf
.claude-plugin/     Claude plugin manifest
```

## License

MIT. See [LICENSE](LICENSE).
