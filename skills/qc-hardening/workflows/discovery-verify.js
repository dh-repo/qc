export const meta = {
  name: 'qc-hardening-discovery-verify',
  description: 'Discovery + Verify half of qc-hardening: parallel deep-read across module groups, adversarial finding-verification, dedup, ranked findings ledger. Remediation stays model-driven (the caller fixes/tests/commits).',
  phases: [
    { title: 'Deep-Read', detail: 'one adversarial reader per module group (correctness + sequence + error-handling + concurrency + Carmack)' },
    { title: 'Verify', detail: '2-vote adversarial refutation per finding (does it reach? is severity right? off-limits / golden-pin sensitive?)' },
    { title: 'Synthesize', detail: 'dedup cross-module concerns, rank by severity x confidence, emit ledger' },
  ],
}

// ── args contract (passed by the qc-hardening skill) ───────────────────────────
//   args.repoPath      : string  — absolute repo root (agents Read files under it)
//   args.groups        : [{ key, label, files: [string], untestedLines?: string,
//                           lenses?: string }]  — module groups (the skill partitions)
//   args.offLimits     : [string]  — files the caller must NOT modify (in-flight work);
//                                    findings there are reported as deferred, never as fixes
//   args.priorFindings : string    — prior ledger / pass-debt / hot-spots (for multi-order analysis)
//   args.goldenNote    : string    — how to recognize golden/pinned values in this repo
// `args` is normally an object, but some callers/harnesses deliver it as a
// JSON-encoded string — parse defensively so groups aren't silently dropped.
let a = args || {}
if (typeof a === 'string') {
  try {
    a = JSON.parse(a)
  } catch (_e) {
    a = {}
  }
}
const GROUPS = Array.isArray(a.groups) ? a.groups : []
const OFF_LIMITS = (a.offLimits || []).join(', ') || '(none)'
const PRIOR = a.priorFindings || '(no prior findings supplied)'
const GOLDEN = a.goldenNote || 'Some computed values may be pinned by golden/regression tests; a finding that would shift a pinned value is higher-risk to "fix".'
const REPO = a.repoPath || '.'

if (GROUPS.length === 0) {
  log('No module groups supplied in args.groups — nothing to read. Pass groups: [{key,label,files}].')
  return { findings: [], clean: [], crossModule: [], note: 'empty groups' }
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    group: { type: 'string' },
    findings: {
      type: 'array',
      description: 'Only real findings with a CONCRETE failure scenario. Empty array is a valid, expected result on hardened code.',
      items: {
        type: 'object',
        properties: {
          tag: { type: 'string', description: 'short stable handle, e.g. G1-bug-1' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          what: { type: 'string' },
          why: { type: 'string', description: 'the concrete scenario / invariant / sequence — not "could cause issues"' },
          fix: { type: 'string', description: 'the specific change' },
          self_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['tag', 'severity', 'file', 'what', 'why', 'fix'],
      },
    },
    cross_module_concerns: {
      type: 'array',
      description: 'Assumptions this group makes about another module (the coordinator verifies + promotes).',
      items: {
        type: 'object',
        properties: {
          assumption: { type: 'string' },
          depends_on: { type: 'string', description: 'the other module' },
          risk: { type: 'string' },
        },
        required: ['assumption', 'depends_on'],
      },
    },
    clean: {
      type: 'array',
      description: 'Every function/area examined with NO finding — proves the group was read, not skimmed.',
      items: { type: 'string' },
    },
  },
  required: ['group', 'findings', 'clean'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'overstated', 'refuted', 'uncertain'] },
    severity_adjusted: { type: 'string', enum: ['P0', 'P1', 'P2', 'drop'] },
    reaches_in_practice: { type: 'boolean', description: 'can a realistic input actually reach this code path?' },
    touches_off_limits: { type: 'boolean' },
    golden_sensitive: { type: 'boolean', description: 'would the fix risk shifting a pinned/golden value?' },
    reasoning: { type: 'string' },
    caveat: { type: 'string', description: 'the condition under which the finding is wrong or the fix is unsafe' },
  },
  required: ['verdict', 'severity_adjusted', 'reaches_in_practice', 'reasoning'],
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    ranked_findings: {
      type: 'array',
      description: 'Verified findings, deduped and ranked: P0>P1>P2, confirmed>overstated, then by reach.',
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
          verdict: { type: 'string' },
          recommendation: { type: 'string', enum: ['fix', 'defer', 'drop'], description: 'fix=safe low-risk; defer=real but needs judgment/untestable/off-limits/golden-sensitive; drop=refuted' },
          defer_reason: { type: 'string' },
        },
        required: ['tag', 'severity', 'file', 'what', 'why', 'fix', 'verdict', 'recommendation'],
      },
    },
    promoted_cross_module: {
      type: 'array',
      description: 'Cross-module concerns confirmed into first-class findings (with the same fields).',
      items: { type: 'object' },
    },
    coverage: {
      type: 'object',
      description: 'Per-group examined/clean accounting so the caller can see nothing was skimmed.',
    },
    summary: { type: 'string' },
  },
  required: ['ranked_findings', 'summary'],
}

function readPrompt(g) {
  return [
    'You are doing a production-hardening DEEP READ (Carmack-style adversarial review). AUDIT ONLY — report findings, DO NOT modify any file.',
    'Repo root: ' + REPO,
    '',
    '## Module group: ' + (g.label || g.key),
    'Read each file FULLY:',
    (g.files || []).map((f) => '  - ' + f).join('\n'),
    g.untestedLines ? '\n## Untested lines — reason about these FIRST (never executed = never proven):\n' + g.untestedLines : '',
    '',
    '## Lenses (apply ALL that fit this group)',
    g.lenses || 'correctness (returns/conditionals/loops/numerics/collections/coercion); sequence/composition (write-then-read order, read-modify-write atomicity, cleanup on all paths); error handling (boundaries, bare except, UnicodeDecodeError vs OSError, timeouts); concurrency/async where present (shared state, check-then-act, missing await, lock scope); Carmack 5Q (invariant? assumptions-wrong? sequence->invalid-state? million-runs? wrong-tomorrow?); injection/data-flow where the group ingests user-facing input (SQL/command/path-traversal/template/SSRF/deserialization/log-injection — trace untrusted data to its sink); degenerate inputs that pass validation.',
    '',
    '## Prior findings / pass-debt / hot-spots (for multi-order analysis — does the same pattern exist here? did a prior fix add an assumption?)',
    PRIOR,
    '',
    '## Off-limits files (report issues there as a finding, but the caller will DEFER not fix): ' + OFF_LIMITS,
    '## Golden/pinned values: ' + GOLDEN,
    '',
    '## Rules',
    '- A finding REQUIRES a concrete failure scenario. "Could theoretically" is NOT a finding. No P3/style.',
    '- This may be hardened code — an empty findings list with a full CLEAN list is a valid, expected result. Do NOT manufacture findings.',
    '- Verify suspicions with executable probes (Bash/Read) where cheap, rather than reasoning in the abstract.',
    'Output is structured data (the schema), not prose.',
  ].join('\n')
}

function verifyPrompt(f, g) {
  return [
    'AUDIT ONLY — use Read/Bash to inspect; never edit a file or run the proposed fix. You are judging the finding, not applying it.',
    'You are an adversarial verifier for a hardening finding. DEFAULT to skeptical — try to REFUTE it or prove it is overstated.',
    'Repo root: ' + REPO + '   Module group: ' + (g.label || g.key),
    '',
    'FINDING (' + f.severity + ') ' + f.file + (f.line ? ':' + f.line : ''),
    'WHAT: ' + f.what,
    'WHY: ' + f.why,
    'PROPOSED FIX: ' + f.fix,
    '',
    'Read the actual code (Read/Bash) and decide:',
    '- Is it real and as described, or overstated/refuted? Can a REALISTIC input actually reach this path (reaches_in_practice)?',
    '- Is the severity right? (severity_adjusted, or "drop" if not real.)',
    '- Does the file fall under off-limits (' + OFF_LIMITS + ')? (touches_off_limits)',
    '- Would the proposed fix risk shifting a pinned/golden value? (golden_sensitive). ' + GOLDEN,
    'Name the condition under which the finding is wrong or the fix is unsafe in `caveat`.',
  ].join('\n')
}

phase('Deep-Read')
log('Discovery+Verify over ' + GROUPS.length + ' module groups (read → adversarial-verify → synthesize). Remediation stays with the caller.')

const perGroup = await pipeline(
  GROUPS,
  // Stage 1 — adversarial deep read of the group.
  (g) => agent(readPrompt(g), { label: 'read:' + g.key, phase: 'Deep-Read', schema: FINDINGS_SCHEMA }),
  // Stage 2 — verify this group's findings (2 skeptics each), as soon as the read returns.
  (res, g) => {
    if (!res) return null
    const findings = res.findings || []
    if (findings.length === 0) return { ...res, verified: [] }
    return parallel(
      findings.map((f) => () =>
        parallel([0, 1].map((v) => () =>
          agent(verifyPrompt(f, g), { label: 'verify:' + g.key + ':' + v, phase: 'Verify', schema: VERDICT_SCHEMA }),
        )).then((votes) => ({ finding: f, votes: votes.filter(Boolean) })),
      ),
    ).then((verified) => ({ ...res, verified: verified.filter(Boolean) }))
  },
)

const groups = perGroup.filter(Boolean)

phase('Synthesize')
const synthesis = await agent(
  [
    'AUDIT ONLY — emit the structured ledger; do not modify any file.',
    'You are the qc-hardening coordinator. Below are per-group deep-read findings, each with 2 adversarial verdicts, plus cross-module concerns and CLEAN lists.',
    'Produce a single ranked, deduplicated findings ledger for the (model) caller to remediate.',
    '',
    'PER-GROUP RESULTS (JSON):',
    JSON.stringify(groups),
    '',
    'Rules:',
    '- Dedup findings that are the same defect seen from two groups (keep one, note both locations).',
    '- For each finding set recommendation: "fix" only if BOTH verdicts confirm AND it is not off-limits, not golden_sensitive, and reaches_in_practice; "defer" if real but needs judgment / untestable-locally / off-limits / golden-sensitive (give defer_reason); "drop" if a majority refuted it.',
    '- Promote any cross-module concern you can confirm from the two groups into a first-class finding.',
    '- Rank: P0 > P1 > P2; confirmed > overstated; reaches_in_practice first.',
    '- Report coverage: which groups were examined and whether each returned a CLEAN list (so the caller can see nothing was skimmed).',
  ].join('\n'),
  { label: 'synthesize:ledger', phase: 'Synthesize', schema: SYNTH_SCHEMA },
)

return {
  ranked_findings: synthesis.ranked_findings || [],
  promoted_cross_module: synthesis.promoted_cross_module || [],
  coverage: synthesis.coverage || {},
  summary: synthesis.summary || '',
  groups_read: groups.length,
  raw_by_group: groups.map((g) => ({ group: g.group, n_findings: (g.findings || []).length, clean_count: (g.clean || []).length })),
}
