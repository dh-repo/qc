export const meta = {
  name: 'qc-coherence-discovery-verify',
  description: 'Discovery + Verify for qc-coherence: fan out the LLM-assisted sub-audits (conformance, semantic, architectural) across the scope, adversarially verify each finding as REAL-incoherence vs INTENTIONAL, dedup, and emit a ranked supervisor-compatible ledger. The deterministic structural sub-audit runs inline (caller) and feeds context; remediation stays model-driven.',
  phases: [
    { title: 'Audit', detail: 'one agent per coherence lens (conformance / semantic / architectural), chunked per module group when supplied' },
    { title: 'Verify', detail: 'two perspective-diverse adversarial verdicts per finding (intentionality hunter + mechanics validator); split or uncertain → defer' },
    { title: 'Synthesize', detail: 'dedup across lenses + structural candidates, rank, cross-check coverage vs module inventory, emit supervisor-compatible ledger' },
  ],
}

// `args` may arrive as an object or a JSON-encoded string — parse defensively.
let a = args || {}
if (typeof a === 'string') {
  try {
    a = JSON.parse(a)
  } catch (_e) {
    a = {}
  }
}
const REPO = a.repoPath || '.'
const SCOPE = a.scope || 'the whole codebase (read the module inventory)'
const CONVENTIONS = a.conventions || 'See CLAUDE.md / AGENTS.md in the repo for declared conventions.'
const STRUCTURAL = a.structuralContext || '(no structural pre-pass context supplied)'
const PRIOR = a.priorState || '(no prior coherence/structural state supplied)'
const OFF_LIMITS = (a.offLimits || []).join(', ') || '(none)'
// Optional chunking: on large scopes (>~50K LOC) one agent per lens will skim. Pass moduleGroups
// (path-group strings) and each lens fans out once per group; synthesis dedups across groups.
const GROUPS = Array.isArray(a.moduleGroups) && a.moduleGroups.length ? a.moduleGroups : [null]
// Module inventory from Pre-Flight — synthesis cross-checks lens coverage against it.
const INVENTORY = a.moduleInventory || '(no module inventory supplied)'
// Deterministic structural-sub-audit candidates (S1 stubs / S2 dead code / S3 duplication)
// to ADVERSARIALLY VERIFY (tool-flagged != real coherence problem).
const STRUCT_CANDIDATES = Array.isArray(a.structuralCandidates) ? a.structuralCandidates : []

// The LLM-assisted lenses, with the qc-coherence check rubrics baked in so the workflow
// is self-contained. Callers normally use these; pass args.lenses to override.
const DEFAULT_LENSES = [
  {
    key: 'conformance',
    title: 'Conformance (C1) — Protocol/implementation matrix',
    rubric: 'For every interface (Protocol/ABC) with 2+ implementations: missing methods, stub implementations, signature mismatches, and whether parameterized conformance tests exist and cover ALL implementations. Flag interfaces lacking a drift guard.',
  },
  {
    key: 'semantic',
    title: 'Semantic (M1-M5) — meaning drift static tools miss',
    rubric: 'M1 Naming: the same concept under different names across modules (run_id vs execution_id). M2 Error taxonomy: equivalent conditions raising different exception types. M3 Serialization round-trip: deserialize(serialize(x)) != x, missing round-trip tests, key mismatches. M4 Behavioral contract: the same interface method behaving differently across implementations. M5 Magic values: hardcoded literals carrying domain meaning not centralized as constants. ALSO: code-vs-docs drift — a function/diagnostic whose behavior changed but whose docstring / README / catalog still describes the OLD behavior.',
  },
  {
    key: 'architectural',
    title: 'Architectural (A1-A5) — invariants & boundaries',
    rubric: 'A1 Dependency direction: lower layers importing higher layers, circular deps. A2 Layer boundary: direct access to internal implementation across a boundary. A3 Module responsibility: modules with 2+ distinct responsibility domains (God classes, grab-bag utils). A4 Documented invariants: constraints stated in comments/docs but NOT enforced by a test. A5 Cross-cutting consistency: logging, auth, retry, transactions, correlation used inconsistently across modules.',
  },
]
const LENSES = Array.isArray(a.lenses) && a.lenses.length ? a.lenses : DEFAULT_LENSES

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      description: 'Cross-cutting coherence findings. Empty is a valid, expected result on a coherent scope.',
      items: {
        type: 'object',
        properties: {
          check: { type: 'string', description: 'the check id, e.g. M1 / C1 / A2' },
          title: { type: 'string' },
          locations: { type: 'array', items: { type: 'string' }, description: 'file:line for EACH site (coherence findings are usually multi-location)' },
          what: { type: 'string' },
          why_incoherent: { type: 'string', description: 'the specific inconsistency / drift / violation across the locations' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'], description: 'P0 = actively broken (runtime failure, data corruption, security hole); P1 = breaks under realistic conditions; P2 = maintenance cost; P3 = cosmetic' },
          proposed_fix: { type: 'string', description: 'how to converge (which site is canonical / which doc to update)' },
          maybe_intentional: { type: 'boolean', description: 'true if this could be a deliberate seam / per-layer pattern (the verifier will adjudicate)' },
        },
        required: ['check', 'title', 'locations', 'why_incoherent', 'severity', 'proposed_fix'],
      },
    },
    clean: { type: 'array', items: { type: 'string' }, description: 'areas examined and found coherent — proves the lens was applied, not skimmed' },
  },
  required: ['lens', 'findings', 'clean'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['real_incoherence', 'intentional', 'overstated', 'uncertain'] },
    is_real: { type: 'boolean', description: 'true only if this is a genuine cross-cutting incoherence worth fixing' },
    reasoning: { type: 'string' },
    intentional_evidence: { type: 'string', description: 'if intentional/overstated: the comment, seam doc, layer separation, or version note that makes the divergence deliberate or correct' },
  },
  required: ['verdict', 'is_real', 'reasoning'],
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    ranked_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          check: { type: 'string' },
          title: { type: 'string' },
          locations: { type: 'array', items: { type: 'string' } },
          why_incoherent: { type: 'string' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
          proposed_fix: { type: 'string' },
          verdict: { type: 'string' },
          recommendation: { type: 'string', enum: ['fix', 'defer', 'drop'], description: 'fix=real + safe to converge; defer=real but needs a judgment/design call; drop=verified intentional or overstated' },
          remediation_hint: { type: 'string', description: 'supervisor-compatible: canonical site, docs to update, or test to add' },
        },
        required: ['check', 'title', 'locations', 'severity', 'verdict', 'recommendation'],
      },
    },
    coverage: { type: 'object', description: 'per-lens (and per-module-group) examined/clean accounting, plus an "unexamined" array of inventory modules no lens touched — the caller treats those as audit gaps, not as coherent' },
    summary: { type: 'string' },
  },
  required: ['ranked_findings', 'summary'],
}

function auditPrompt(lens, group) {
  return [
    'You are running one lens of a codebase COHERENCE audit. AUDIT ONLY — report findings, DO NOT modify any file.',
    'Repo root: ' + REPO + '   Scope: ' + SCOPE,
    group
      ? 'YOUR MODULE GROUP (audit ONLY this slice; sibling agents cover the rest): ' + group + '. You may Grep outside your group to confirm the counterpart site of a cross-cutting finding, but every finding must cite at least one location inside your group.'
      : '',
    '',
    '## Your lens: ' + lens.title,
    lens.rubric,
    '',
    '## Declared conventions (the conformance baseline)',
    CONVENTIONS,
    '',
    '## Structural pre-pass context (symbol table / import graph / duplication+stub candidates)',
    STRUCTURAL,
    '',
    '## Prior coherence/structural state (do not re-report already-recorded items unless they regressed)',
    PRIOR,
    '',
    '## Off-limits files (report issues there, but the caller will DEFER not fix): ' + OFF_LIMITS,
    '',
    '## Rules',
    '- Coherence findings are CROSS-CUTTING: cite EVERY location and state the inconsistency BETWEEN them (drift, divergence, missing convergence). A single-site observation is not a coherence finding.',
    '- Use Grep/Read/Bash to confirm each site actually exists and says what you claim — do not reason in the abstract.',
    '- A coherent scope yields an empty findings list + a full CLEAN list. Do NOT manufacture findings. Mark maybe_intentional=true when a divergence could be a deliberate per-layer pattern or seam.',
    'Output is structured data (the schema).',
  ].join('\n')
}

// Two perspective-diverse verifiers per finding — diversity catches failure modes a second
// identical refuter cannot. Perspective 0 hunts intentionality; perspective 1 validates mechanics.
const VERIFY_PERSPECTIVES = [
  'YOUR PERSPECTIVE — INTENTIONALITY HUNTER. Coherence audits over-report: the dominant false positives are DELIBERATE seams, intentional per-layer patterns, naming that is different-but-correct, and "drift" that is actually the correct current state. Hunt for the comment, seam doc, ADR, layer rationale, CLAUDE.md rule, or version note that makes this divergence deliberate. verdict=intentional only with cited evidence; if you find none after genuinely looking, say real_incoherence.',
  'YOUR PERSPECTIVE — MECHANICS VALIDATOR. Confirm the finding is mechanically accurate: does EVERY cited location exist and say what the finding claims (verbatim — Read it)? Is the inconsistency actually present between the sites, or is the claim overstated/stale? Is the severity right per P0=actively broken, P1=breaks under realistic conditions, P2=maintenance cost, P3=cosmetic? Wrong locations or inflated claims → verdict=overstated.',
]

function verifyPrompt(f, perspective) {
  return [
    'You are an adversarial verifier for a COHERENCE finding. DEFAULT to skeptical — the burden of proof is on the finding.',
    VERIFY_PERSPECTIVES[perspective] || VERIFY_PERSPECTIVES[0],
    'Repo root: ' + REPO,
    '',
    'FINDING [' + f.check + '] ' + f.title + '  (' + f.severity + ')',
    'LOCATIONS: ' + (f.locations || []).join(' ; '),
    'WHY CLAIMED INCOHERENT: ' + f.why_incoherent,
    'PROPOSED FIX: ' + f.proposed_fix,
    '',
    'Read the ACTUAL code/docs at each location (Read/Grep). Decide: is this a genuine cross-cutting incoherence worth converging, or is the divergence intentional (a documented seam, a layer boundary, a versioned change) or overstated? If intentional/overstated, cite the specific evidence (comment, docstring, CLAUDE.md rule, version stamp) in intentional_evidence. Use verdict=uncertain only when you genuinely cannot adjudicate — it routes the finding to a human-judgment defer, not to the fix list.',
  ].join('\n')
}

phase('Audit')
const UNITS = LENSES.flatMap((lens) => GROUPS.map((group, gi) => ({ lens, group, gi })))
log('Coherence Discovery+Verify: ' + LENSES.length + ' lenses x ' + GROUPS.length + ' group(s) + ' + STRUCT_CANDIDATES.length + ' structural candidates -> perspective-diverse verify -> ranked ledger. Remediation stays with the caller.')

// Lens-x-group audits, each verifying its own findings as soon as the audit returns.
const perUnit = await pipeline(
  UNITS,
  (u) => agent(auditPrompt(u.lens, u.group), { label: 'audit:' + u.lens.key + (u.group ? ':g' + u.gi : ''), phase: 'Audit', schema: FINDINGS_SCHEMA }),
  (res, u) => {
    if (!res) return null
    const findings = res.findings || []
    if (findings.length === 0) return { ...res, verified: [] }
    return parallel(
      findings.map((f) => () =>
        parallel([0, 1].map((v) => () =>
          agent(verifyPrompt(f, v), { label: 'verify:' + u.lens.key + ':' + v, phase: 'Verify', schema: VERDICT_SCHEMA }),
        )).then((votes) => ({ finding: f, votes: votes.filter(Boolean) })),
      ),
    ).then((verified) => ({ ...res, verified: verified.filter(Boolean) }))
  },
)

// Adversarially verify the deterministic structural candidates too (tool-flagged stubs /
// duplication / dead code are frequently intentional seams or per-layer patterns).
const structVerified = STRUCT_CANDIDATES.length
  ? await parallel(
      STRUCT_CANDIDATES.map((c) => () => {
        const f = {
          check: c.check || 'S?',
          title: c.title || 'structural candidate',
          locations: c.locations || [],
          why_incoherent: c.what || c.why_incoherent || '',
          severity: c.severity || 'P2',
          proposed_fix: c.proposed_fix || '',
        }
        return parallel([0, 1].map((v) => () =>
          agent(verifyPrompt(f, v), { label: 'verify:structural:' + v, phase: 'Verify', schema: VERDICT_SCHEMA }),
        )).then((votes) => ({ finding: f, votes: votes.filter(Boolean) }))
      }),
    )
  : []

const units = perUnit.filter(Boolean)

phase('Synthesize')
const synthesis = await agent(
  [
    'You are the qc-coherence coordinator. Below are per-lens coherence findings (each with 2 perspective-diverse adversarial verdicts: an intentionality hunter and a mechanics validator) plus adversarially-verified structural candidates. Produce ONE ranked, deduplicated, supervisor-compatible ledger for the (model) caller to remediate.',
    '',
    'PER-LENS VERIFIED FINDINGS (JSON; one entry per lens-x-module-group unit):',
    JSON.stringify(units),
    '',
    'VERIFIED STRUCTURAL CANDIDATES (JSON):',
    JSON.stringify(structVerified),
    '',
    'MODULE INVENTORY (the full set of modules the audit was supposed to cover):',
    INVENTORY,
    '',
    'Rules:',
    '- Dedup findings that are the same incoherence seen from two lenses or two module groups (keep one, union the locations).',
    '- recommendation: "fix" ONLY when BOTH verdicts say real_incoherence AND convergence is safe/local. "drop" ONLY when BOTH verdicts judged it intentional or overstated (carry the intentional_evidence). ANY split vote (1-1) or ANY "uncertain" verdict -> "defer" — a contested finding is never fixed and never silently dropped. "defer" also applies when both say real but convergence needs a design/judgment call (which site becomes canonical, a module split).',
    '- Rank P0 > P1 > P2 > P3; within a tier, multi-location drift over single divergences.',
    '- remediation_hint must be actionable: name the canonical site, the exact docs/docstrings to update, or the drift-guard/round-trip test to add (supervisor-ready).',
    '- coverage: list each lens (and module group, if chunked) + whether it returned a CLEAN list. Then cross-check the MODULE INVENTORY: any module that appears in NO finding location and NO clean list goes in an "unexamined" array — the caller treats unexamined modules as an incomplete audit, not as coherent.',
  ].join('\n'),
  { label: 'synthesize:ledger', phase: 'Synthesize', schema: SYNTH_SCHEMA },
)

return {
  ranked_findings: synthesis.ranked_findings || [],
  coverage: synthesis.coverage || {},
  summary: synthesis.summary || '',
  units_run: units.length,
  lenses: LENSES.length,
  module_groups: GROUPS.length,
  structural_candidates_verified: structVerified.length,
}
