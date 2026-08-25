---
name: qc-docs
description: Use for production documentation standardization of an existing repository. Trigger on phrases like "production docs", "standardize docs", "documentation pass", "repo docs", "landing page", "deployment docs", "handoff docs", "operator docs", "runbook", "knowledge transfer", "team handoff", or when README, deployment, operations, architecture, troubleshooting, or handoff documentation is missing, inconsistent, or ad hoc. Do not use for feature implementation, packaging metadata, CI hardening, or runtime debugging.
---

# Production Docs

**REQUIRED:** Load `qc-core` first. Laws, ledger, verdict, profile (`operating_facts`, `truth_map`), deferred vocabulary, and suite order live there. This skill is the documentation specialization. It runs last in `qc-all` so the truth-map matches the code that survived hardening and coherence.

Produce the **minimal complete documentation set** that lets a new engineer or operator correctly understand, run, diagnose, recover, and hand off the system that actually exists. Document the **system as found**, including residual debt from prior audits — never the system as hoped. Every claim is evidence-linked; every operator-relevant surface the code exposes is covered; every known limitation from prior hardening/coherence runs is surfaced; nothing is invented.

**Core principle:** Documentation must match the codebase that exists. Do not invent features, infrastructure, SLAs, or operating procedures that are not grounded in the repository or verified user input.

## When to Use

- Documentation exists but is inconsistent in structure, tone, or completeness
- A repository needs a standardized GitHub landing page and a defined supporting document set
- Deployment, operations, troubleshooting, or handoff knowledge is trapped in code, chat history, or scattered notes
- A team wants a repeatable documentation format across repositories

**Do not use when:** the primary need is packaging/release polish, feature work, code hardening, or speculative architecture design without a real implementation target.

## Output Contract

This skill standardizes docs into two layers.

**Layer 1, GitHub landing page:** `README.md` is the entry point. It explains the problem, the system, how to run it, and where deeper docs live.

**Layer 2, operational document set:** dedicated documents hold durable reference material so the README stays readable.

The minimum standard document set is:

| File | Purpose | Required When |
|------|---------|---------------|
| `README.md` | GitHub landing page and operator entry point | Always |
| `ARCHITECTURE.md` | System structure, data flow, major components, boundaries | Always |
| `DEPLOYMENT.md` | Environment setup, deploy/run path, configuration, rollback basics | Deployable systems or scheduled jobs |
| `OPERATIONS.md` | Day-2 runbook, routine tasks, health checks, monitoring, backup/restore if applicable | Services, pipelines, schedulers, or persistent systems |
| `TROUBLESHOOTING.md` | Known failure modes, symptoms, checks, recovery steps | Any non-trivial system |
| `HANDOFF.md` | Team transfer notes, ownership model, commands, critical files, known risks | Repos intended for another maintainer or team |
| `SECURITY.md` | Security posture and disclosure/contact process | Public or shared repos |
| `CHANGELOG.md` | Versioned change history | Repos with releases or recurring milestones |
| `API.md` | Routes, contracts, payloads, examples, auth expectations | APIs, CLIs with machine interfaces, SDKs |
| `DATA_MODEL.md` | Core entities, schemas, lifecycle state, file formats | Data-heavy or integration-heavy systems |

If a file is not applicable, do not create placeholder noise. The README must still point to the applicable set.

## Repo Archetype Matrix

Choose the closest repo archetype before writing. If a repo fits multiple archetypes, use the union of required docs. When in doubt, bias toward the more operational archetype.

| Archetype | Typical Signals | Required Docs | README Emphasis |
|-----------|-----------------|---------------|-----------------|
| Library or SDK | Reusable package, exported modules, no long-running runtime | `README.md`, `ARCHITECTURE.md`, `API.md`, `SECURITY.md`, `CHANGELOG.md` | Installation, compatibility, public interface, release expectations |
| CLI or local tool | `argparse`, `click`, `typer`, local file I/O, batch outputs | `README.md`, `ARCHITECTURE.md`, `TROUBLESHOOTING.md`, `HANDOFF.md` | Invocation, inputs, outputs, common command paths |
| API or service | HTTP server, health endpoint, deployable runtime, persistent config | `README.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `API.md`, `SECURITY.md`, `HANDOFF.md` | Service purpose, deploy path, health signals, interface contract |
| Scheduled job or pipeline | Cron, scheduler, queue worker, generated artifacts, recurring runs | `README.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `HANDOFF.md`, `DATA_MODEL.md` | Schedule, source inputs, outputs, reruns, failure recovery |
| Data or integration system | File formats, schemas, connectors, ingestion, transformation | `README.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `HANDOFF.md`, `DATA_MODEL.md` | Sources, schemas, lineage, artifact flow |
| Infra-only repository | Terraform, Bicep, Ansible, deployment orchestration, no app runtime | `README.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `SECURITY.md`, `CHANGELOG.md`, `HANDOFF.md` | Environments, rollout, rollback, operational boundaries |

If the repo is public or release-managed, `SECURITY.md` and `CHANGELOG.md` should usually exist even when the archetype table would otherwise omit them.

## Documentation Layout Standard

Use one canonical layout unless the repo already has a stable, well-linked documentation structure. Normalize content first; move files only when the benefit exceeds the churn.

| Path | Role |
|------|------|
| `README.md` | GitHub landing page and entry point |
| `SECURITY.md` | Security and disclosure policy |
| `CHANGELOG.md` | Release or milestone history |
| `docs/ARCHITECTURE.md` | System structure and execution flow |
| `docs/DEPLOYMENT.md` | Build, configuration, deploy, rollback |
| `docs/OPERATIONS.md` | Day-2 runbook and routine operations |
| `docs/TROUBLESHOOTING.md` | Symptom-driven diagnosis and recovery |
| `docs/HANDOFF.md` | Maintainer transfer notes |
| `docs/API.md` | API, CLI, or machine interface contract |
| `docs/DATA_MODEL.md` | Core entities, schemas, and lifecycle |
| `docs/diagrams/` | Diagrams and visual assets when the count exceeds a few inline files |
| `docs/examples/` | Example payloads, example configs, or sample outputs when useful |
| `docs/internal/` | Internal-only docs for private repos or explicitly internal documentation mode |

Layout rules:
- Keep the README short and route deeper detail into canonical docs.
- Do not duplicate full runbooks inside the README.
- Root-level docs should be limited to the landing page and high-signal repository policies unless the repo already has a stable alternative layout.
- Every document linked from the README must be canonical, not a draft or duplicate.

## Truth Hierarchy

When documentation sources disagree, use this order of precedence.

1. Executable behavior: CLI help output, route definitions, config loaders, tests that exercise the path, generated artifacts, and observed runtime behavior.
2. Source code and configuration: application code, `pyproject.toml`, `package.json`, Dockerfiles, workflow files, infrastructure files, and environment-variable lookups.
3. Verified user-supplied operating facts: deployment venue, ownership, support path, unpublished operational constraints. If these facts are not inferable from code, state them as user-provided context.
4. Existing documentation and comments.
5. Assumptions.

Conflict rules:
- If docs conflict with code, code wins.
- If code and tests conflict, investigate and document the ambiguity before writing definitive prose.
- If the user provides operating facts not encoded in the repo, include them only where they belong and avoid presenting them as code-derived truth.
- If a fact cannot be verified, state it as unknown or provisional instead of guessing.

## Standardization Process

### First-Pass vs Delta Mode

Before starting, determine which mode applies.

**First-pass mode** (docs are missing, skeletal, or structurally broken):
- Follow the full execution checklist: audit, write bottom-up, then README, then validate.
- This is the default for repos with no docs or docs that fail the structural check below.

**Delta mode** (docs exist and are structurally sound):
- The required doc set for the repo archetype exists.
- Each doc has substantive, repo-specific content (not a placeholder).
- The README links to the doc set and follows the required structure.

If all three conditions hold, skip the full write sequence:
1. Re-validate every existing `truth_map[]` row against current code (and `operating_facts[]` `last_verified` timestamps).
2. Rewrite only claims whose evidence moved.
3. Run the validation matrix and quality gates (including Gate 4).
4. Stop when gates pass.

Delta mode is high-signal: the prior evidence map is the target, not a full rewrite. If the matrix reveals structural gaps (a required doc is missing, a doc is a placeholder), fall back to first-pass mode for the affected docs only.

### 1. Audit Before Writing

Read the codebase first, plus **prior-skill ledgers** (`.qc-findings/qc-hardening.json`, `.qc-findings/qc-coherence.json`) and `.qc-profile.json`. Determine:
- Actual entry points
- Actual deployment model
- Actual operators or users
- Actual external dependencies
- Actual commands that work
- Actual persistent artifacts and outputs
- **Operator-relevant surfaces the code exposes** (health endpoint, recovery path, config keys, error modes, scheduler, public CLI flags) — Completeness is dual: missing coverage of a code-surfaced concern is a Completeness finding, not an Accuracy finding

If the repo already has docs, preserve accurate material and normalize it. Do not rewrite for style alone if the existing text is already clear and correct.

### 2. Build the Documentation Map (truth-map artifact)

Write `truth_map[]` on `.qc-profile.json` before editing. Every **non-trivial** claim in ARCHITECTURE, OPERATIONS, API, and DATA_MODEL → evidence pointer: `file:line`, a test name, or `user-provided:<id>` referencing `operating_facts[]`. Missing pointers on those docs fail Accuracy, not just "required evidence." P1+ accuracy findings use the operator-path scenario: the operator following the documented path encounters X because the claim is false.

Also record:
- What belongs in the landing page vs deep reference vs runbooks
- What is still unknown and must be labeled as a limitation
- User-provided operating facts (deployment venue, ownership, support path) in `operating_facts[]` with `timestamp` **and** `last_verified` — never present those as code-derived truth
- **Known limitations** synthesized from profile `deferred[]` + `hot_spots[]` + `pass_debt[]` + untested `invariants[]` (skip this section on a standalone docs run with no prior ledgers). Do not invent mitigations.

### 3. Plan Top Down, Write Bottom Up

Plan the documentation from the landing page outward, but do not usually rewrite the landing page first. In most repos, the correct execution order is:

1. `ARCHITECTURE.md`
2. `DEPLOYMENT.md`
3. `OPERATIONS.md`
4. `TROUBLESHOOTING.md`
5. `HANDOFF.md`
6. Remaining conditional docs (`API.md`, `DATA_MODEL.md`, `SECURITY.md`, `CHANGELOG.md`)
7. `README.md`
8. Cross-reference and contradiction validation

Rationale:
- Deep docs establish the operational truth.
- The README should summarize and route, not discover its structure while the rest of the docs are still moving.
- Cross-reference validation is only meaningful after the full document set exists.

The README must not become a dump of all information. It should route readers into the deeper docs.

## Default Execution Checklist

Use this checklist as the default work breakdown for a first-pass production-docs run. In delta mode, skip to step 9 (validation) and fix what fails.

Steps marked with archetype conditions should be skipped when the condition does not apply. Do not create placeholder docs for skipped steps.

| Step | Action | Skip When | Notes |
|------|--------|-----------|-------|
| 1 | Audit the codebase and classify the repo archetype | Never | Determines which steps to skip |
| 2 | Create or normalize `ARCHITECTURE.md` | Never | Required for all archetypes |
| 3 | Create or normalize `DEPLOYMENT.md` | Library/SDK, CLI tool without deploy target | Required for services, pipelines, infra, data systems |
| 4 | Create or normalize `OPERATIONS.md` | Library/SDK, CLI tool | Required for services, pipelines, schedulers, persistent systems |
| 5 | Create or normalize `TROUBLESHOOTING.md` | Trivial projects only | Recommended for all non-trivial systems |
| 6 | Create or normalize `HANDOFF.md` | No team transfer planned | Required when repo is changing hands |
| 7 | Create conditional docs: `API.md`, `DATA_MODEL.md`, `SECURITY.md`, `CHANGELOG.md` | See archetype matrix | `API.md` for SDKs/APIs; `DATA_MODEL.md` for data-heavy systems; `SECURITY.md` for public/shared repos; `CHANGELOG.md` for release-managed repos |
| 8 | Restructure `README.md` as the landing page | Never | Link to the finalized canonical docs |
| 9 | Validate all cross-references, commands, and contradictions | Never | Run validation matrix and quality gates |

If the repo already has a strong README, still write or normalize the deeper docs first, then tighten the landing page against the finished document set.

## Public vs Internal Mode

Every documentation pass must choose a visibility mode before writing.

| Mode | Use When | Allowed Detail | Restricted Detail |
|------|----------|----------------|-------------------|
| Public | Repo is public, may go public, or serves as an external landing page | Public commands, sanitized architecture, supported workflows, public interfaces, high-level deployment shape | Internal hostnames, dashboard URLs, ticket queues, exact escalation contacts, environment nicknames, private topology |
| Internal | Repo is private and the docs are meant for operators or an internal engineering team | Environment names, state file paths, dashboards, operational ownership, rollback detail, incident inputs, scheduler specifics | Secrets, tokens, credentials, or anything that should live in a secret store |
| Hybrid | Public landing page with private operational material separated cleanly | Public README and sanitized supporting docs, plus internal runbooks in `docs/internal/` or another private location | Mixing internal-only detail into the public README or public-facing deep docs |

For `DEPLOYMENT.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `HANDOFF.md`, and `API.md`, prefer a small header block near the top:

```text
Audience: engineers | operators | maintainers
Visibility: public | internal
Last verified against: <commit hash, tag, or release>
```

If the repo is public and deeper internal runbooks cannot live in the repository, say that explicitly and keep the public docs sanitized.

## README Standard

`README.md` is the GitHub landing page. It must be readable by a new engineer in under five minutes.

### Required README Structure

```
# Project Name
[1 short tagline sentence]

[Problem paragraph]
[Solution paragraph]
[Hero diagram if it adds real value]

---
## Quick Start
[Install/run commands or operator start path]

---
## What It Does
[Core capabilities or workflow]

---
## Architecture
[High-level system explanation with diagram if useful]

---
## Repository Map
[File/component table]

---
## Operations
[Short summary with links to OPERATIONS.md / TROUBLESHOOTING.md / DEPLOYMENT.md]

---
## Documentation Map
[Table linking to supporting docs]

---
## Validation
[How to run tests/lint/health checks that actually exist]

---
> **Scope note.**
> **Known limitations.** (from prior qc ledgers when they exist; otherwise omit)
```

### README Rules

- H1 once only, project name only
- Every H2 preceded by `---`
- H3 allowed inside H2 sections, no H4+
- No badges, shields, emoji, or table of contents by default
- No marketing language, hype, or AI attribution
- No invented roadmap language unless verified by repo docs or user request
- Use tables for structured material: commands, docs map, files, endpoints, env vars
- Keep the README narrative short; move detail to supporting docs
- Every command shown must be real and repo-valid
- Every file referenced must exist or be created in the same pass

## Supporting Document Standards

### `ARCHITECTURE.md`

Must answer:
- What are the major components?
- How does data move through the system?
- What boundaries matter?
- What is synchronous vs scheduled vs external?
- What outputs/artifacts are produced?

Recommended sections:
- System Overview
- Execution Flow
- Component Responsibilities
- Data Flow
- External Integrations
- Key Constraints
- Architecture Risks

### `DEPLOYMENT.md`

Must answer:
- What environments exist?
- What prerequisites are required?
- What config/env vars are required?
- How is the system built, started, scheduled, or published?
- How is rollback or recovery handled?

Recommended sections:
- Deployment Model
- Prerequisites
- Configuration
- Build and Release Path
- Run/Deploy Steps
- Rollback or Recovery
- Post-Deploy Verification

### `OPERATIONS.md`

Must answer:
- What routine tasks do operators perform?
- How is health assessed?
- What logs, outputs, or state files matter?
- What cleanup, retention, scheduling, or rerun tasks exist?

Recommended sections:
- Operational Overview
- Routine Tasks
- Health Checks
- Monitoring Signals
- State and Artifacts
- Maintenance Tasks
- Escalation Inputs

### `TROUBLESHOOTING.md`

Must be symptom-driven, not theory-driven.

Use a table:

| Symptom | Likely Cause | Verify | Fix |
|---------|--------------|--------|-----|

Include only issues supported by the codebase, tests, or verified operator knowledge.

### `HANDOFF.md`

This file is mandatory when the repo is changing hands.

Must answer:
- What is this repo responsible for?
- Who will touch it and why?
- What commands matter most?
- What files are critical?
- What is fragile or unfinished?
- What should the next maintainer check first?
- What is the first-day path and the first-incident path the code actually supports?

Recommended sections:
- Purpose and Scope
- Current Status
- Ownership and Responsibilities
- First-Day Commands
- Critical Files and Directories
- Known Risks and Sharp Edges
- Known limitations (from prior qc-hardening / qc-coherence ledgers — skip if none)
- Immediate Next Steps

### `API.md`

For each interface include:
- Route or command
- Method or invocation shape
- Inputs
- Outputs
- Errors
- Auth/config requirements
- Example request/response when useful

### `DATA_MODEL.md`

Document only real entities and real fields. Prefer tables. Include:
- Entity name
- Key fields
- Source of truth
- Lifecycle/state transitions
- File or API origin if applicable

## Style Standard

All docs in this skill follow the same voice.

- Direct, technical, declarative
- Short paragraphs, dense but readable
- No tutorial filler
- No hedging unless uncertainty is real and stated explicitly
- No sales tone
- No AI provenance markers
- Use inline code for commands, paths, env vars, field names, and identifiers
- Use tables for structured reference material
- Prefer explicit limitations over vague reassurance
- When documenting constants in tables, show the value as it appears in code. Describe the effect in the Purpose or Description column, not the Value column. Example: `PENALTY` with value `0.15` and purpose "Subtracted from score when X" — not value `-0.15`.
- Claims about where code lives ("all X are in Y") must name specific items or be verified with grep. Blanket claims rot faster than specific ones.

## Documentation Map Standard

The README must include a table like this when multiple docs exist:

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | System structure and execution flow |
| `DEPLOYMENT.md` | Build, configuration, deployment, and verification |
| `OPERATIONS.md` | Routine operating procedures and health checks |
| `TROUBLESHOOTING.md` | Symptom-driven diagnosis and fixes |
| `HANDOFF.md` | Maintainer transfer notes and known risks |

Adapt rows to the actual document set.

## Documentation Change Triggers

Documentation updates should ship with the code changes that require them. If a trigger fires, update the corresponding docs in the same pass or explain why no change was needed.

| Change in the Repository | Docs That Must Be Reviewed or Updated |
|--------------------------|----------------------------------------|
| New or changed CLI command, subcommand, or flag | `README.md`, `API.md` or CLI interface section, `OPERATIONS.md`, `HANDOFF.md` |
| New or changed environment variable, config file, or default | `DEPLOYMENT.md`, `OPERATIONS.md`, `README.md` Quick Start, `TROUBLESHOOTING.md` if failures change |
| New or changed endpoint, payload, response shape, or error contract | `API.md`, `DATA_MODEL.md`, `README.md`, `TROUBLESHOOTING.md` |
| New or changed output directory, artifact, state file, or retention behavior | `OPERATIONS.md`, `TROUBLESHOOTING.md`, `HANDOFF.md`, `ARCHITECTURE.md` if flow changes |
| New or changed deployment model, container path, infrastructure, or hosting target | `DEPLOYMENT.md`, `ARCHITECTURE.md`, `OPERATIONS.md`, `SECURITY.md` |
| New or changed scheduler cadence, automation, or recurring run behavior | `OPERATIONS.md`, `DEPLOYMENT.md`, `TROUBLESHOOTING.md`, `HANDOFF.md` |
| New or changed ownership, support path, or escalation model | `HANDOFF.md`, `OPERATIONS.md` |
| New or changed core entity, schema, state model, or file format | `DATA_MODEL.md`, `ARCHITECTURE.md`, `README.md` |
| Public release, open-sourcing, or repo visibility change | `README.md`, `SECURITY.md`, `CHANGELOG.md`, and visibility review across all docs |

## Documentation Quality Gates

A production-docs pass is only complete when all four gates pass.

### Gate 1: Completeness

Treat completeness as a coverage problem, not a writing-style judgment.

Completeness is **dual**: (1) the required docs exist; (2) every operator-relevant surface the *code* exposes is documented when it is relevant to the archetype.

Pass conditions:
- The repo archetype has been identified and the required document set for that archetype exists.
- Every critical concern has a canonical home: entry points, commands, configuration, environment variables, interfaces, outputs, state files, deployment path, operating procedures, failure modes, and ownership.
- Every inventoried code-surfaced concern (health endpoint, recovery path, config key, error mode, scheduler, public CLI flag) has a documented home, or is explicitly out of scope for the archetype.
- The README points to the deeper docs instead of silently omitting required operational material.
- No required doc remains as a placeholder or empty shell.

Fail conditions:
- A required doc for the repo archetype is missing.
- A critical concern exists in the codebase but has no documented home. **Absence of coverage for a code-surfaced concern is a Completeness finding.**
- Important operational facts exist only in scattered notes, code comments, or chat history.
- The README implies a complete story while deeper required docs do not exist.

Required evidence:
- A documentation coverage map, explicit or implicit, showing where each concern is documented.
- A completed execution checklist with skipped items justified by repo archetype or visibility mode.

### Gate 2: Accuracy

Treat accuracy as a verification problem. Documentation is not accepted just because it sounds plausible.

Pass conditions:
- Commands are verified against the real CLI, scripts, or tested run paths when feasible.
- Environment variables, configuration files, defaults, and paths are verified against code or config loaders.
- Interfaces, routes, flags, payloads, and outputs match the implementation.
- Deployment and operations claims match the actual deployment model encoded in the repository or verified user-supplied operating facts.
- Unknown or unverified facts are labeled explicitly instead of guessed.

Fail conditions:
- Docs contradict code, tests, startup paths, or config.
- A documented command, flag, endpoint, env var, or output path does not exist.
- Operational claims are invented, overstated, or copied from generic guidance without repo evidence.
- User-supplied operating facts are presented as code-derived truth when they are not encoded in the repository.
- A non-trivial ARCHITECTURE / OPERATIONS / API / DATA_MODEL claim has no `truth_map[]` row.

Required evidence:
- The profile `truth_map[]` (every non-trivial claim in those four docs → `file:line`, test name, or `user-provided:<id>`). Absence of the map fails this gate.
- P1+ accuracy findings state the operator-path scenario: following the documented path encounters X because the claim is false.
- A verification log, lightweight or formal, showing which commands, interfaces, config paths, and outputs were checked.
- `Last verified against` headers on deeper operational docs when those docs are created or substantially rewritten.

### Gate 3: Clarity

Treat clarity as a reader-experience problem. A doc can be complete and accurate while still being difficult to use.

Pass conditions:
- The README answers three questions quickly: what this repo is, how it is run or used, and where to go next.
- Each document has a single clear job and does not duplicate large bodies of content from another canonical doc.
- Structured material is presented as tables, ordered steps, or concise reference sections instead of long prose dumps.
- Troubleshooting is symptom-driven, not theory-driven.
- Audience and visibility are clear for operational docs.

Fail conditions:
- The README is overloaded and tries to be the full runbook.
- Multiple docs repeat or contradict the same procedures.
- Readers cannot tell which doc is canonical for deployment, operations, interfaces, or handoff.
- Important instructions are buried in narrative prose rather than presented as reference material.

Required evidence:
- A readability check that confirms the landing page still works as a five-minute orientation path.
- A contradiction and duplication sweep across the canonical docs.

### Gate 4: Handoff Readiness

Treat handoff as a human-outcome problem. Files that exist and are accurate can still leave a new person stuck.

Pass conditions:
- A competent new engineer or operator can perform the archetype's **first-day path** (install/run or deploy+health) using only the doc set.
- They can perform the archetype's **first-incident path** (the most likely failure the code actually supports — missing config, bad input, downstream timeout) using TROUBLESHOOTING.md / OPERATIONS.md, without tribal knowledge.
- Both paths are strictly limited to what the code supports. Do not invent recovery procedures.

Fail conditions:
- First-day or first-incident steps require knowledge that exists in code or prior qc ledgers but not in HANDOFF.md, TROUBLESHOOTING.md, or the README.
- HANDOFF.md is missing when the repo is changing hands or `qc-all` is running a full suite (HANDOFF is then in-scope even if the archetype table would skip it for a library).
- Known limitations from prior hardening/coherence runs (profile `deferred[]`, `hot_spots[]`, untested `invariants[]`) are missing from HANDOFF.md, TROUBLESHOOTING.md, and the README scope note when those ledgers exist.

Required evidence:
- Named first-day and first-incident paths, each with doc pointers.
- A **Known limitations** heading (or an explicit skip because no prior ledgers exist).

### Done Definition

The pass is done only when:
- Completeness is green.
- Accuracy is green.
- Clarity is green.
- Handoff Readiness is green.

If any gate is red, the documentation pass is not complete even if the prose is polished.

### Convergence and Stopping

Multiple passes may be needed if the first pass introduces new content that itself contains errors (e.g., a new API.md section with a wrong import). Each pass should find fewer and lower-severity issues than the previous one.

**Stop when:** All four gates pass and the current pass found only P3 issues (stale counts, minor wording, cosmetic separators) or no issues at all. Do not run additional passes for style preferences.

**Warning sign:** If a pass finds new P1/P2 issues that the previous pass should have caught, the verification process has a gap. Investigate why the validation matrix missed it before continuing — the issue may indicate a systematic blind spot (e.g., non-markdown assets, blanket claims about code organization) rather than a one-off miss.

## What Not to Do

- Do not create empty template files with no repo-specific content
- Do not copy generic cloud guidance unrelated to the actual deployment model
- Do not document endpoints, commands, or environment variables that are not present
- Do not leave contradictory instructions across files
- Do not let the README become longer than the combined value of the deeper docs warrants
- Do not rewrite code comments as a substitute for real documentation

## Issue Severity Tiers

When a pass finds multiple issues, fix them in severity order. Do not spend time on P3 issues while P1 issues remain.

| Severity | Category | Examples | Priority |
|----------|----------|----------|----------|
| P1 | Feature claims that contradict code | Doc says feature is "not implemented" but it ships in the current version; doc describes a bug that has been fixed; doc omits a major exported function | Fix immediately — misleads users and integrators |
| P2 | Wrong references to code artifacts | Wrong module names, wrong constant values, wrong function signatures, wrong dataclass locations, broken links, missing imports in examples | Fix in same pass — breaks trust and copy-paste workflows |
| P3 | Stale counts and cosmetic prose | Test counts, module counts, minor wording, style inconsistencies, H2 separators | Fix only after P1/P2 are resolved |

On a first pass, address all severities. On subsequent delta passes, stop after resolving P1/P2 issues unless P3 issues are trivially fixable in the same edit.

## Validation Matrix

| Check | Compare Against | Minimum Standard |
|-------|-----------------|------------------|
| Commands | `README.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, `HANDOFF.md` vs actual CLI entry points, scripts, or tested commands | Every documented command is real; run it when feasible or mark it unverified explicitly |
| Environment Variables | `DEPLOYMENT.md`, `OPERATIONS.md`, `API.md` vs code lookups and config loaders | Each documented variable has a real source in code or verified user input; required vs optional is clear |
| Interfaces | `API.md`, `README.md` vs route definitions, CLI parser, SDK surface | Methods, paths, **parameter types**, **return types**, flags, and error conditions match the code. Check parameter types (not just names): if the doc says `dict` but code says `list[X]`, that's a blocker. Check return type internals: if the doc says `list of str` but code returns `list[SomeDataclass]`, that's a blocker. |
| Outputs and Artifacts | `ARCHITECTURE.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md` vs generated files, state files, output paths | Paths, file names, and artifact meanings are accurate |
| Deployment Path | `DEPLOYMENT.md`, `README.md`, `OPERATIONS.md` vs Dockerfiles, workflows, infra files, startup code | One consistent deployment story, no contradictory paths |
| Documentation Links | `README.md` and docs cross-links vs filesystem | No broken links; every referenced file exists |
| Cross-Doc Consistency | All docs against each other | Entry points, env vars, deployment model, and ownership do not contradict each other |
| Visibility and Confidentiality | Public or internal mode vs actual doc content | Public docs contain no internal-only operational detail; internal docs still contain no secrets |
| Unknowns and Limits | All docs | Unknown facts are labeled explicitly, not guessed |
| Embedded Assets | SVG text content, diagram labels, image alt text vs current prose claims | Rendered content in SVGs, PNGs, and diagrams matches the numbers and names in prose; alt text matches rendered content |
| Requirements Mapping | SCOPE.md or equivalent requirements-traceability doc, if present | Every item appears in exactly one category (covered, partial, not yet implemented, out of scope); no item appears in two categories |
| Code Examples | Every Python/JS/etc. code block in docs vs actual source | Every import resolves. Every function call uses correct parameter names and types. Every attribute access (`obj.field`) references a field that exists on that class. Every method call exists. Run or trace each example mentally to verify it would not raise `AttributeError`, `ImportError`, or `TypeError`. |
| Dataclass/Model Fields | Field lists in `API.md` or schema tables vs actual dataclass definitions | Every documented field exists on the class. No ghost fields (documented but not in code). Field types match. Check ALL dataclasses, not just the primary one — secondary dataclasses (e.g., return types of helper functions, nested result objects) are where ghost fields hide. |
| Status Tables | Risk tables, known-issues sections, bug lists vs current code state | Entries describing issues that have been fixed must be marked as resolved. An active-risk entry for a resolved issue misleads maintainers into unnecessary workarounds. |

After the matrix check:
- Verify every referenced document exists.
- Verify the landing page still reads cleanly without opening every supporting doc.
- Remove placeholder sections that survived the pass without repo-specific content.

### Deep verification with subagents

The Code Examples, Dataclass/Model Fields, and Interfaces checks require reading source code line-by-line against documentation claims. This is slow and error-prone when done manually in a single pass. For repos with `API.md` or integration guides containing code examples, **dispatch parallel subagents** — one per doc file — to cross-reference every attribute access, import, and type claim against the actual source. This catches issues that surface-level checks consistently miss:

- Ghost fields (documented on a dataclass but not in code)
- Parameter type mismatches (`dict` vs `list[X]`)
- Return type mismatches (`list of str` vs `list[SomeDataclass]`)
- Stale code examples using pre-refactor field names
- Resolved issues still listed as active in risk/status tables

These issues survive multiple manual passes because they require simultaneously reading the doc AND the source class definition. A subagent given both files and a specific verification mandate catches them reliably.

## Findings Output Contract

qc-core ledger at `.qc-findings/qc-docs.json`. P1+ accuracy contradictions need the operator-path scenario triple (`operator following the documented path encounters X because the claim is false`). Unknown operating facts defer as `user-provided-unknown`. Verify: `python3 ../qc-core/scripts/verify_ledger.py .qc-findings/qc-docs.json`.

```json
{
  "schema_version": "1.1",
  "skill": "qc-docs",
  "run_id": "2026-05-17T14:30:00Z-abc1234",
  "git_sha": "abc1234",
  "findings": [
    {
      "id": "D2.1",
      "severity": "P2",
      "confidence": "pattern",
      "file": "README.md",
      "line": 1,
      "what": "README does not document the canonical run command, but CLI help shows one",
      "fix": "Add a Quickstart section quoting the working `python -m claims_agent --help` invocation",
      "fixed": false,
      "deferred_because": "needs-owner: product naming decision"
    }
  ],
  "verdict": "READY_WITH_DEBT"
}
```

Verdict math is qc-core (open P0 policy for this skill). Persist `truth_map[]` and `operating_facts[]` on `.qc-profile.json`.

## Relationship to Other Skills

- `qc-packaging` — packaging, release polish, repository hygiene
- `qc-hardening` — defect reduction (runs before docs in the suite)
- `qc-coherence` — cross-cutting consistency (runs before docs in the suite)
- `qc-docs` — documentation structure, accuracy, handoff, operational standardization
