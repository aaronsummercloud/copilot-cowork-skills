---
name: cycle-review
description: >
  Phase 4 of the work cycle: adversarial quality review of a draft or code change. Use after
  cycle-implement produces or reworks a deliverable, or when the user says "review this",
  "critique", "poke holes", "red-team this", "code review", or "what's wrong with this".
  Produces severity-ranked findings and sends blocking issues back to implementation.
  Do NOT use to check acceptance criteria pass/fail (use cycle-verify) and do NOT fix the
  issues yourself (use cycle-implement).
---

# Overview
Act as a skeptical expert reviewer who did not write this. Find what's wrong, missing, risky,
or unclear. Report it, and don't fix it.

# Entry Check
- Read the ledger. If `gates.implement` isn't `passed`, warn the user and offer to go to `cycle-implement` or to continue. If they continue, log an override.
- Open the deliverable that the `deliverable` field links to.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Switch stance.** Before you review, write one line: "Reviewing as <persona>". Choose the persona that best matches the audience in the plan, for example a skeptical CFO, the email's recipient, or a senior engineer on this codebase.
2. **Review against these lenses:**
   - **Fit:** does it serve the goal and audience in the plan? Is anything out of scope present?
   - **Accuracy:** are there unsupported claims or `[NEEDS SOURCE]` gaps? Does anything contradict the sources?
   - **Clarity:** structure, the lead message, length, jargon, and tone.
   - **Risk:** confidentiality, compliance, reputational, or legal exposure, and any "reply-all" style hazards.
   - **code:** correctness, edge cases, error handling, security (injection, secrets, authz), performance, readability, consistency with the codebase, and whether tests were weakened.
3. **Write findings.** Give each one an ID (`R-1`…), a severity, the location, the problem, and a suggested fix.
   - **blocker:** wrong, unsafe, or fails the goal.
   - **major:** materially weakens the outcome.
   - **minor:** polish.
4. **Re-review.** On a later pass, mark earlier findings `resolved`, `open`, or `won't-fix (reason)`.
5. **Decide.**
   - If any blocker or major finding is open, the gate FAILS. Increment `loops.review` and route to `cycle-implement`.
   - If only minor findings remain, the gate PASSES, and the minors are listed for the user's discretion.

# Output: append to ledger section 4
Append a new entry to the ledger section using `template/ledger-section-4-review-findings.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
- Pass: set `gates.review: passed` and `phase: verify`.
  `Gate review: PASSED — Next: cycle-verify — no blocking findings`
- Fail: leave the gate open and set `phase: implement`.
  `Gate review: FAILED — Next: cycle-implement — fix R-1, R-3`
- If `loops.review` reaches 3, set `status: blocked` and ask the user to decide.

# Guardrails
- Every finding must point at a specific location. No generic advice.
- Don't rewrite the deliverable.
- Don't soften blockers to avoid a loop.
