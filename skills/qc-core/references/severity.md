# Severity

| Level | Meaning | Action |
|-------|---------|--------|
| **P0** | Outage: data loss, security breach, or service failure in production | Fix immediately. Presence blocks release (even if fixed) as a human-review gate. |
| **P1** | Defect: incorrect behavior or user-facing error under realistic conditions | Fix this pass, or defer with a closed-vocabulary code. |
| **P2** | Weakness: edge condition, harder debugging, best-practice violation with concrete risk | Fix if low-risk; otherwise defer. |
| **P3** | Style / observation | Do not fix. Note only if systemic. |

The bar: a concrete failure scenario, or it is not a finding. See [ledger.md](ledger.md) for the structured triple and confidence tiers.

Calibration: Carmack/Chaos P1 (proven) outranks a mechanical P1 (pattern-matched) when *prioritizing fixes*. Any P0 still outranks any P1. Mechanical P2 with a concrete scenario outranks a speculative Carmack P2.

Docs uses the same scale with skill-specific examples (contradicting feature claims = P1; wrong artifact references = P2; stale counts = P3). Do not invent a fifth level.
