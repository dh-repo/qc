# qc

Source: [github.com/dh-repo/qc](https://github.com/dh-repo/qc)

Quality-control skills for coding agents. Same `SKILL.md` trees run in Claude Code, Codex, Grok Build, Cursor, and any other client that speaks the [Agent Skills](https://agentskills.io) format.

This is not a hosted product. The agent follows the skill; a small Python harness checks the findings ledger so a standalone run and a full-suite rollup never disagree on the verdict.

## Install

Fastest path, any agent:

```bash
npx skills add dh-repo/qc
```

That copies each `skills/<name>/` folder into the agent(s) you have installed (Claude Code, Codex, Grok, Cursor, …). Use `-g` for a user-wide install.

```bash
npx skills add dh-repo/qc -g
npx skills add dh-repo/qc --skill qc-hardening
npx skills add dh-repo/qc --list
```

### By agent

| Agent | Global install location | Project install location |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex | `~/.codex/skills/` | `.agents/skills/` |
| Grok Build | `~/.grok/skills/` | `.grok/skills/` |
| Cursor / Copilot / Gemini CLI | `~/.cursor/skills/` or `~/.agents/skills/` | `.agents/skills/` |

Manual copy (equivalent to a per-skill install):

```bash
git clone https://github.com/dh-repo/qc.git
cp -R qc/skills/qc-hardening ~/.claude/skills/
cp -R qc/skills/qc-hardening ~/.codex/skills/
cp -R qc/skills/qc-hardening ~/.grok/skills/
```

Claude Code can also load the repo as a plugin (`.claude-plugin/plugin.json` at the root; skills auto-discovered under `skills/`).

Each skill is self-contained. `npx skills add dh-repo/qc --skill qc-hardening` is enough to run hardening; you do not need the rest of the suite unless you want `qc-all` to roll the four skills up.

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
