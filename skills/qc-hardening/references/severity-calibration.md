## Severity Classification

| Severity | Definition | Action |
|----------|-----------|--------|
| **P0 — Outage** | Data loss, security breach, or service failure in production | Fix immediately. Block release. |
| **P1 — Defect** | Incorrect behavior, degraded performance, or user-facing error under realistic conditions | Fix in this pass. |
| **P2 — Weakness** | Edge-condition issues, harder debugging, best-practice violation with concrete risk | Fix if low-risk. Note if complex. |
| **P3 — Style/observation** | Style, minor inconsistency, or theoretical concern | Do not fix. Note only if systemic. |

**The bar for filing a finding:** You must describe a concrete scenario where the issue causes a real problem. "This could theoretically..." is not a finding.

**Severity calibration across passes:** Not all P1s are equal. A P1 from Carmack (invariant violation proven by reasoning) or Chaos (crash reproduced by test) is higher confidence than a P1 from a mechanical pass (pattern-matched but not tested). When prioritizing fixes:
- Carmack/Chaos P1 > Mechanical P1 (proven vs. pattern-matched)
- Any P0 > any P1 (regardless of source)
- Mechanical P2 with a concrete scenario > Carmack P2 based on speculation

## Evidence Standard

Two formats depending on whether the finding requires judgment or is mechanical.

**Full evidence (judgment passes: 1, 2, 3, 12, 13)** — six fields, all required:

1. **ID:** `F<pass>.<sequence>` (e.g., `F12.3`). Referenced in commit messages.
2. **Location:** `file_path:line_number`
3. **What:** The specific defect
4. **Why:** The concrete failure scenario (for Carmack: the invariant, assumptions, or sequence)
5. **Severity:** P0/P1/P2 with justification
6. **Fix:** The specific change

**Lightweight evidence (tool passes: 4, 5, 6, 7, 8, 9, 10, 11)** — four fields:

1. **ID:** `F<pass>.<sequence>`
2. **Location:** `file_path:line_number`
3. **What:** The tool output or rule violated
4. **Fix:** The change applied

No "Why" needed — the tool IS the why. A mypy type error or a ruff lint violation doesn't need a failure scenario narrative. Just fix it.

## Pass Ordering Rationale

Passes 1-11 are cheap mechanical checks (tools, checklists). Passes 12-13 are expensive deep passes (reading, adversarial testing). Pass 14 is a closing synthesis pass that turns the earlier evidence into a maintainability and consistency judgment. This order is deliberate:
- Mechanical passes clean up noise first (linting, types, missing tests)
- Deep passes then operate on clean code, focusing on real logic issues
- Carmack and Chaos don't waste time on things ruff or mypy would catch
- Maintainability grading happens last, when it can be based on real hot spots and proven change-risk instead of stylistic preference

Do not reorder passes unless you have a specific reason for this project.
