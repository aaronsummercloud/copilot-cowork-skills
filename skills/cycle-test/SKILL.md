---
name: cycle-test
description: >
  Phase 2 of the work cycle: define how success will be checked BEFORE any work is done
  (test-first). Use after a plan is approved, or when the user says "acceptance criteria",
  "definition of done", "how will we know it's right", "write the tests first", "test cases",
  or "success criteria". For code it writes failing tests; for documents, emails, decks and
  analysis it writes checkable acceptance criteria. Do NOT use to run final checks on finished
  work (use cycle-verify) or to critique quality (use cycle-review).
---

# Overview
Write the checks before the work exists, so the implementation is judged against an agreed
target and not against itself.

# Entry Check
- Read the ledger. If `gates.plan` isn't `passed`, warn the user and offer to go back to `cycle-plan` or to continue. If they continue, log an override.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Reuse first.** Read `Documents/Cowork/memory/ac-library.md`, if it exists, and pull in the criteria that match this deliverable type.
2. **Derive acceptance criteria (ACs)** from the plan. Give each one an ID (`AC-1`…) and write it as an observable statement, never a vague one like "high quality". Cover:
   - **Goal:** does it achieve the stated outcome for the audience?
   - **Facts:** list the specific claims, figures, names, and dates that must match the sources. Every fact listed under "Key facts for ACs" in the research brief becomes a `source-check` AC that cites its F-#. A fact marked `UNVERIFIED` must never become an AC; send it back to `cycle-research` or to the user.
   - **Format:** length, structure, template, and required sections.
   - **Constraints:** tone, policy, deadline, and anything the plan put out of scope.
   - **Risks:** one check for each risk listed in the plan.
3. **Assign a check method** to each AC:
   - `source-check`: compare against a cited source.
   - `rubric`: score it on a stated scale with a pass threshold.
   - `format-check`: confirm structure or length.
   - `test-run`: a code test passes.
   - `user-signoff`: only for genuinely subjective items, and at most 2 per cycle.
4. **When `work_type: code`:**
   - Write the actual test code in the project's framework: unit tests for each behavior, plus edge cases and error paths. Each test maps to an AC.
   - Save the tests to `<project_path>/outputs/code/tests/`, or to the existing codebase's test folder if the plan names one.
   - Record the test file paths and the exact command that runs them.
   - If you can execute code, run the tests now and confirm they **fail** (red) for the right reason. If you can't, give the user the command and ask them to paste the output. Record it as `red-confirmed: yes/no/user-run`.
5. **Get approval.** Show the ACs and ask the user to approve them. Approval passes the gate.

# Output: ledger section 2
Write the ledger section using `template/ledger-section-2-acceptance-criteria.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
Set `gates.test: passed` and `phase: implement`, then end with:
`Gate test: PASSED — Next: cycle-implement — <n> ACs approved`

# Guardrails
- Keep it to 3–12 ACs. If you have more, the scope is probably too big, so suggest splitting the task.
- Never write criteria that can only pass by inspecting the finished work subjectively, unless the check is `user-signoff`.
- Don't change scope. If writing the ACs exposes a scope gap, route back to `cycle-plan`.
