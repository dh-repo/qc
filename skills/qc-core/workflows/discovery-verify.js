export const meta = {
  name: 'qc-discovery-verify',
  description: 'Shared Discovery+Verify: pluggable Audit (groups or lenses), fixed dual-vote Verify, fixed Synthesize. Mechanical/human hits skip Verify. Remediation stays with the caller.',
  phases: [
    { title: 'Audit', detail: 'one agent per group and/or lens; CLEAN list required' },
    { title: 'Verify', detail: '2-vote adversarial; skip mechanical/human; both-real → fix else defer' },
    { title: 'Synthesize', detail: 'dedup, rank, coverage vs inventory, related_findings' },
  ],
}

let a = args || {}
if (typeof a === 'string') {
  try { a = JSON.parse(a) } catch (_e) { a = {} }
}

const KIND = a.kind || (Array.isArray(a.lenses) && a.lenses.length ? 'lenses' : 'groups')
const REPO = a.repoPath || '.'
const OFF_LIMITS = (a.offLimits || []).join(', ') || '(none)'
const PRIOR = a.priorState || a.priorFindings || '(no prior state supplied)'
const GOLDEN = a.goldenNote || 'Pinned/golden values: a finding that would shift one is higher-risk to fix.'
const SCOPE = a.scope || 'the supplied groups / inventory'
const CONVENTIONS = a.conventions || 'See CLAUDE.md / AGENTS.md.'
const STRUCTURAL = a.structuralContext || '(no structural pre-pass context)'
const INVENTORY = a.moduleInventory || '(no module inventory supplied)'
const STRUCT_CANDIDATES = Array.isArray(a.structuralCandidates) ? a.structuralCandidates : []
const GROUPS = Array.isArray(a.groups) && a.groups.length
  ? a.groups
  : (Array.isArray(a.moduleGroups) && a.moduleGroups.length ? a.moduleGroups.map((g, i) => (typeof g === 'string' ? { key: 'g' + i, label: g, files: [] } : g)) : [])
const DEFAULT_LENSES = [
  { key: 'conformance', title: 'Conformance (C1)', rubric: 'Protocol/ABC with 2+ implementations: missing methods, stubs, signature mismatches AND observable equivalence under the same inputs (serialization shapes, optional fields, error types, side-effects). Parameterized behavioral coverage must include ALL implementations. Scenario shape: under input sequence X, backend A returns Y while B returns Z / a different exception.' },
  { key: 'semantic', title: 'Semantic (M1-M5)', rubric: 'M1 same concept different names. M2 equivalent errors raising different types. M3 deserialize(serialize(x)) != x. M4 same interface method behaving differently. M5 magic values. Emit clusters[] (symbols + rationale) AND canonical_forms[] (concept, canonical, aliases). Later runs only re-flag regressions. Scenario: under X, A and B disagree.' },
  { key: 'architectural', title: 'Architectural (A1-A5)', rubric: 'A1 write/diff layer_model (layers + permitted import direction). A2 layer boundary. A3 mixed responsibility (clusters[] + rationale). A4 harvest must/never into invariants[] and flag untested registry rows. A5 operational consistency: logging field shapes, correlation IDs, config/env key naming, error-propagation, feature-flag discovery — still A5, not a new pass.' },
]
const LENSES = Array.isArray(a.lenses) && a.lenses.length ? a.lenses : (KIND === 'lenses' ? DEFAULT_LENSES : [])

const CLEAN_ITEM = {
  type: 'object',
  properties: {
    artifact: { type: 'string', description: 'named module/function/file examined' },
    invariant: { type: 'string', description: 'one-sentence invariant; boilerplate (looks fine / seems correct) is incomplete' },
  },
  required: ['artifact', 'invariant'],
}

const SCENARIO = {
  type: 'object',
  properties: {
    trigger: { type: 'string' },
    violated_invariant: { type: 'string' },
    observable: { type: 'string' },
  },
  required: ['trigger', 'violated_invariant', 'observable'],
}

const GROUP_FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    group: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          tag: { type: 'string' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          what: { type: 'string' },
          why: { type: 'string' },
          fix: { type: 'string' },
          confidence: { type: 'string', enum: ['mechanical', 'pattern', 'proven', 'human'] },
          scenario: SCENARIO,
          related_findings: { type: 'array', items: { type: 'string' } },
        },
        required: ['tag', 'severity', 'file', 'what', 'why', 'fix', 'confidence'],
      },
    },
    cross_module_concerns: {
      type: 'array',
      items: {
        type: 'object',
        properties: { assumption: { type: 'string' }, depends_on: { type: 'string' }, risk: { type: 'string' } },
        required: ['assumption', 'depends_on'],
      },
    },
    clean: { type: 'array', items: CLEAN_ITEM },
  },
  required: ['group', 'findings', 'clean'],
}

const LENS_FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          check: { type: 'string' },
          title: { type: 'string' },
          locations: { type: 'array', items: { type: 'string' } },
          what: { type: 'string' },
          why_incoherent: { type: 'string' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
          proposed_fix: { type: 'string' },
          confidence: { type: 'string', enum: ['mechanical', 'pattern', 'proven', 'human'] },
          scenario: SCENARIO,
          maybe_intentional: { type: 'boolean' },
          cluster: {
            type: 'object',
            properties: {
              symbols: { type: 'array', items: { type: 'string' } },
              rationale: { type: 'string' },
            },
          },
          related_findings: { type: 'array', items: { type: 'string' } },
        },
        required: ['check', 'title', 'locations', 'why_incoherent', 'severity', 'proposed_fix'],
      },
    },
    clean: { type: 'array', items: CLEAN_ITEM },
  },
  required: ['lens', 'findings', 'clean'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'real_incoherence', 'overstated', 'refuted', 'intentional', 'uncertain'] },
    is_real: { type: 'boolean' },
    severity_adjusted: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3', 'drop'] },
    reaches_in_practice: { type: 'boolean' },
    touches_off_limits: { type: 'boolean' },
    golden_sensitive: { type: 'boolean' },
    reasoning: { type: 'string' },
    intentional_evidence: { type: 'string' },
    caveat: { type: 'string' },
  },
  required: ['verdict', 'reasoning'],
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    ranked_findings: { type: 'array', items: { type: 'object' } },
    promoted_cross_module: { type: 'array', items: { type: 'object' } },
    coverage: { type: 'object' },
    summary: { type: 'string' },
  },
  required: ['ranked_findings', 'summary'],
}

function skipVerify(f) {
  return f && (f.confidence === 'mechanical' || f.confidence === 'human')
}

function groupReadPrompt(g) {
  return [
    'You are doing a production-hardening DEEP READ (Carmack-style). AUDIT ONLY — do not modify any file.',
    'Repo root: ' + REPO,
    '## Module group: ' + (g.label || g.key),
    'Read each file FULLY:',
    (g.files || []).map((f) => '  - ' + f).join('\n'),
    g.untestedLines ? '\n## Untested lines — live I/O / adapter paths FIRST, then the rest:\n' + g.untestedLines : '',
    '',
    '## Lenses (apply ALL that fit; composition is primary)',
    g.lenses || 'sequence/composition (write-then-read, RMW atomicity, cleanup-on-all-paths); dual-path API parity; field population of every output type; classification completeness; I/O coercion on EVERY ingest path; then residual isolated function bugs; error handling; concurrency/async where present; Carmack 5Q (EXAMINED = five answers or invariant+assumptions+sequence_risk, not a one-liner); injection/data-flow on untrusted input; degenerate inputs that pass validation. After any finding ask: same pattern in other backends / dual paths?',
    '',
    '## Prior state / pass-debt / hot-spots / prior-skill deferred findings',
    PRIOR,
    '',
    '## Off-limits: ' + OFF_LIMITS,
    '## Golden/pinned: ' + GOLDEN,
    '',
    '## Rules',
    '- A judgment finding REQUIRES scenario.{trigger, violated_invariant, observable}. trigger names a combination (second step, impl, location, or dual path), not "this function is wrong". "Could theoretically" is NOT a finding. No P3/style.',
    '- CLEAN for this deep-read: each artifact needs invariant+assumptions+sequence_risk OR the five Carmack questions. A one-sentence "looks fine" is incomplete.',
    '- Harvest each finding violated_invariant into invariants[] (source: carmack). Do not invent invariants.',
    '- confidence: pattern (checklist) or proven (you can name the observable). Do not mark mechanical unless a tool emitted it.',
    '- Empty findings + a full CLEAN list is valid. Do NOT manufacture findings.',
    '- If a prior-skill deferred finding is the same issue, set related_findings rather than minting a new severity.',
    'Output is structured data (the schema).',
  ].join('\n')
}

function lensAuditPrompt(lens, group) {
  return [
    'You are running one lens of a codebase COHERENCE audit. AUDIT ONLY — do not modify any file.',
    'Repo root: ' + REPO + '   Scope: ' + SCOPE,
    group ? 'YOUR MODULE GROUP (audit ONLY this slice): ' + (group.label || group.key || group) + '. Grep outside to confirm a counterpart site, but every finding must cite at least one location inside your group.' : '',
    '',
    '## Your lens: ' + lens.title,
    lens.rubric,
    '',
    '## Declared conventions',
    CONVENTIONS,
    '',
    '## Structural pre-pass context',
    STRUCTURAL,
    '',
    '## Prior coherence state AND prior-skill ledgers (do not re-report unless they regressed; link related_findings)',
    PRIOR,
    '',
    '## Off-limits: ' + OFF_LIMITS,
    '',
    '## Rules',
    '- Coherence findings are CROSS-CUTTING: cite EVERY location and the inconsistency BETWEEN them. A single-site observation is not a coherence finding.',
    '- P1+ and Semantic/Architectural findings need scenario.{trigger, violated_invariant, observable} in the shape: under input sequence X, backend A returns Y while B returns Z / a different exception. trigger names a combination, not a single-line root cause.',
    '- Any clustering or "unrelated responsibilities" judgment MUST include cluster.{symbols, rationale} AND write canonical_forms[] or layer_model as appropriate. Later runs treat those as ground truth.',
    '- Enforce the invariant registry in priorState: untested testable rows are findings; do not mint a second id for the same statement.',
    '- Empty findings + full CLEAN {artifact, invariant} is valid. Do NOT manufacture findings. Mark maybe_intentional=true when a divergence could be a deliberate seam.',
    'Output is structured data (the schema).',
  ].join('\n')
}

const VERIFY_PERSPECTIVES_GROUPS = [
  'YOUR PERSPECTIVE — REACHABILITY SKEPTIC. DEFAULT to refute. Can a REALISTIC input reach this path? Is severity the worst honest scenario? Off-limits? Golden-sensitive?',
  'YOUR PERSPECTIVE — MECHANICS VALIDATOR. Read the cited code. Does it say what the finding claims? Is the scenario triple actually grounded in that code? Inflated claims → overstated.',
]

const VERIFY_PERSPECTIVES_LENSES = [
  'YOUR PERSPECTIVE — INTENTIONALITY HUNTER. Dominant false positives are DELIBERATE seams, per-layer patterns, different-but-correct naming. Hunt for the comment/ADR/CLAUDE.md rule that makes this divergence deliberate. verdict=intentional only with cited evidence.',
  'YOUR PERSPECTIVE — MECHANICS VALIDATOR. Does EVERY cited location exist and say what is claimed? Is the inconsistency actually present? Severity right? Wrong locations or inflated claims → overstated.',
]

function verifyPrompt(f, perspective, kind) {
  const perspectives = kind === 'lenses' ? VERIFY_PERSPECTIVES_LENSES : VERIFY_PERSPECTIVES_GROUPS
  return [
    'You are an adversarial verifier. DEFAULT to skeptical. AUDIT ONLY — never edit or apply the fix.',
    perspectives[perspective] || perspectives[0],
    'Repo root: ' + REPO,
    '',
    'FINDING: ' + JSON.stringify(f),
    'Off-limits: ' + OFF_LIMITS,
    'Golden: ' + GOLDEN,
    '',
    'Decide verdict: confirmed|real_incoherence|overstated|refuted|intentional|uncertain.',
    'Both-real is the only path to fix (the synthesizer applies that rule). Uncertain routes to defer, never drop.',
  ].join('\n')
}

async function verifyFinding(f, labelPrefix, kind) {
  if (skipVerify(f)) {
    return { finding: f, votes: [{ verdict: 'confirmed', reasoning: 'short-circuit: confidence=' + f.confidence, is_real: true }], skipped: true }
  }
  const votes = await parallel([0, 1].map((v) => () =>
    agent(verifyPrompt(f, v, kind), { label: labelPrefix + ':' + v, phase: 'Verify', schema: VERIFY_SCHEMA }),
  ))
  return { finding: f, votes: (votes || []).filter(Boolean) }
}

if (KIND === 'groups' && GROUPS.length === 0) {
  log('No module groups supplied in args.groups — nothing to read.')
  return { findings: [], clean: [], note: 'empty groups' }
}

phase('Audit')

let units
if (KIND === 'lenses') {
  const groupsOrNull = GROUPS.length ? GROUPS : [null]
  const UNITS = LENSES.flatMap((lens) => groupsOrNull.map((group, gi) => ({ lens, group, gi })))
  log('Discovery+Verify lenses: ' + LENSES.length + ' lenses x ' + groupsOrNull.length + ' group(s). Dual-vote except mechanical/human.')
  const perUnit = await pipeline(
    UNITS,
    (u) => agent(lensAuditPrompt(u.lens, u.group), { label: 'audit:' + u.lens.key + (u.group ? ':g' + u.gi : ''), phase: 'Audit', schema: LENS_FINDINGS_SCHEMA }),
    (res, u) => {
      if (!res) return null
      const findings = res.findings || []
      if (findings.length === 0) return { ...res, verified: [] }
      return parallel(findings.map((f) => () => verifyFinding(f, 'verify:' + u.lens.key, 'lenses')))
        .then((verified) => ({ ...res, verified: (verified || []).filter(Boolean) }))
    },
  )
  const structVerified = STRUCT_CANDIDATES.length
    ? await parallel(STRUCT_CANDIDATES.map((c) => () => {
        const f = {
          check: c.check || 'S?',
          title: c.title || 'structural candidate',
          locations: c.locations || [],
          why_incoherent: c.what || c.why_incoherent || '',
          severity: c.severity || 'P2',
          proposed_fix: c.proposed_fix || '',
          confidence: c.confidence || 'pattern',
        }
        return verifyFinding(f, 'verify:structural', 'lenses')
      }))
    : []
  units = { kind: 'lenses', perUnit: (perUnit || []).filter(Boolean), structVerified }
} else {
  log('Discovery+Verify groups: ' + GROUPS.length + ' groups. Dual-vote except mechanical/human.')
  const perGroup = await pipeline(
    GROUPS,
    (g) => agent(groupReadPrompt(g), { label: 'read:' + g.key, phase: 'Audit', schema: GROUP_FINDINGS_SCHEMA }),
    (res, g) => {
      if (!res) return null
      const findings = res.findings || []
      if (findings.length === 0) return { ...res, verified: [] }
      return parallel(findings.map((f) => () => verifyFinding(f, 'verify:' + g.key, 'groups')))
        .then((verified) => ({ ...res, verified: (verified || []).filter(Boolean) }))
    },
  )
  units = { kind: 'groups', perGroup: (perGroup || []).filter(Boolean) }
}

phase('Synthesize')
const synthesis = await agent(
  [
    'AUDIT ONLY — emit the structured ledger; do not modify any file.',
    'You are the qc-core synthesizer. Apply the FIXED dual-vote rule: recommendation is "fix" ONLY when BOTH votes say real (confirmed/real_incoherence/overstated). "drop" ONLY when BOTH say refuted or intentional (keep intentional_evidence). ANY split or ANY uncertain → "defer". Never silently drop.',
    'Mechanical/human short-circuits arrive as a single confirmed vote with skipped=true — treat as confirmed, do not invent a second vote.',
    'Dedup the same defect seen twice; union locations; set related_findings when a prior-skill deferred item is the same issue.',
    'Rank P0>P1>P2>P3. Coverage: every unit must have a CLEAN list; boilerplate invariants mean unexamined. Inventory modules in neither a finding location nor CLEAN go in coverage.unexamined — that is an incomplete audit, not a pass.',
    'Put harvestable durable artifacts on coverage for the caller to persist: invariants[] (from Carmack violated_invariant), canonical_forms[], layer_model. Do not invent them.',
    'Defer (do not fix) when off-limits, golden-sensitive, or the only fix is architecture / canonical-site / module-split. Use deferred codes: needs-architecture, public-signature, behavior-change, needs-owner, golden-sensitive, off-limits, needs-canonical-site, needs-module-split, accepted-debt, needs-migration, cross-backend.',
    '',
    'UNITS (JSON):',
    JSON.stringify(units),
    '',
    'MODULE INVENTORY:',
    INVENTORY,
    '',
    'PRIOR STATE:',
    PRIOR,
  ].join('\n'),
  { label: 'synthesize:ledger', phase: 'Synthesize', schema: SYNTH_SCHEMA },
)

return {
  ranked_findings: (synthesis && synthesis.ranked_findings) || [],
  promoted_cross_module: (synthesis && synthesis.promoted_cross_module) || [],
  coverage: (synthesis && synthesis.coverage) || {},
  summary: (synthesis && synthesis.summary) || '',
  kind: KIND,
}
