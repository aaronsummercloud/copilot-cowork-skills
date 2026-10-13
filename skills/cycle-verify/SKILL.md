---
name: cycle-verify
description: >
  Phase 5 of the work cycle: evidence-based pass/fail check of every acceptance criterion
  before anything is finalized or sent. Use after review passes, or when the user says
  "verify", "check it against the criteria", "is it done", "run the tests", "ready to send?",
  or "final check". Requires concrete evidence (source quotes, test output) for every
  criterion. Do NOT use for subjective critique (use cycle-review) or to fix failures
  (use cycle-implement).
---

# Overview
The deliverable is done only when every acceptance criterion has **evidence** of passing. "Looks
good" isn't evidence.

# Entry Check
- Read the ledger. If `gates.review` isn't `passed`, warn the user and offer to go to `cycle-review` or to continue. If they continue, log an override.
- Load the AC table from section 2 and the deliverable.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Check every AC independently**, using its check method.
   - **source-check:** re-retrieve the source now rather than relying on memory. For an AC that cites an F-#, re-open that fact's source from the research brief and confirm it hasn't changed since the retrieval date. Quote the passage and the matching text in the deliverable.
   - **rubric:** score it, state the threshold, and justify the score in one line.
   - **format-check:** state the measured value, such as the word count or which sections are present.
   - **test-run (code):** run the full test command from section 2, plus lint and type checks if the project has them.
     - Record the command and a summary of the output: passed, failed, and errors.
     - If you can't execute code, ask the user to run the command and paste the output. **Never report PASS without real output.**
   - **user-signoff:** ask the user directly, and record their answer verbatim.
2. **Look for regressions.**
   - **code:** confirm that tests not related to this change still pass.
   - **m365:** confirm that fixes from review didn't break other ACs.
3. **Decide.**
   - All ACs PASS: the gate passes. Only now may the user finalize, send, or merge, and you must ask them to confirm before taking any outbound action.
   - Any AC FAILS: the gate fails. Increment `loops.verify`. If the AC was met but the criterion itself is wrong, route to `cycle-test`. Otherwise route to `cycle-implement`.

# Output: append to ledger section 5
Append a new entry to the ledger section using `template/ledger-section-5-verification.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
- Pass: set `gates.verify: passed` and `phase: remember`.
  `Gate verify: PASSED — Next: cycle-remember — <n>/<n> ACs passed`
- Fail: leave the gate open.
  `Gate verify: FAILED — Next: cycle-implement — AC-4 failed`
  If the criterion itself is wrong, use `Next: cycle-test` instead.
- If `loops.verify` reaches 3, set `status: blocked` and ask the user to decide.

# Guardrails
- One unverifiable AC means the gate FAILS, not "mostly passed".
- Never fabricate test output or quotes.
- Never take outbound action without the user's explicit confirmation in this turn.
