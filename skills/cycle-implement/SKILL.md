---
name: cycle-implement
description: >
  Phase 3 of the work cycle: build the deliverable against the approved plan and acceptance
  criteria. Use after acceptance criteria/tests exist, when review or verification sent work
  back for fixes, or when the user says "draft it", "build it", "write it", "implement",
  "make the changes", or "fix the findings". Produces documents, emails (draft only), decks,
  analysis, or code. Do NOT use to plan, to write acceptance criteria, or to judge/approve the
  work (use cycle-review and cycle-verify).
---

# Overview
Do the work, guided by the plan and aimed at the ACs. Log every deviation. You build. You never
grade your own work.

# Entry Check
- Read the ledger. If `gates.test` isn't `passed`, warn the user that no acceptance criteria exist yet. Offer to go to `cycle-test` or to continue. If they continue, log an override.
- **Rework mode:** if you arrived from review or verify, read the open findings (`R-#`) or failed ACs, and fix **only** those unless the user asks for more.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Map the work to the ACs.** Before you start, list which part of the deliverable satisfies each AC.
2. **Build.**
   - **m365:**
     - Ground every factual claim in a retrieved source, and keep a source note for each one.
     - Use the user's templates and preferences from memory.
     - Save the deliverable to `<project_path>/outputs/`, taking `project_path` from the ledger. Use descriptive file names, and add a `-v<n>` suffix on rework passes instead of overwriting.
     - For an email or message draft, also save a `.md` copy of the text in `outputs/`.
     - Outbound email, chat, or invites are created as **drafts only**.
   - **code:**
     - Write the minimum change that makes the failing tests pass, then refactor while they stay green.
     - Follow the project's existing style.
     - **Where code goes:** new code is saved under `<project_path>/outputs/code/`. If the plan names an existing codebase elsewhere, edit it there, and save a summary of the change to `outputs/` (`change-<n>.md`, listing the files touched and the diff or patch).
     - **Never edit a test to make it pass** without logging it as a deviation and the reason.
     - If you can execute code, run the tests. If you can't, give the user the exact command.
3. **Log deviations.** Record anything that departs from the plan, along with the reason. If a deviation changes scope, stop and route to `cycle-plan`.
4. **Self-check.** Run a quick self-check only to catch obvious omissions. This isn't review.

# Output: append to ledger section 3
Append a new entry to the ledger section using `template/ledger-section-3-implementation-log.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.
Set `deliverable` in the ledger header.

# Exit
Set `gates.implement: passed` and `phase: review`, then end with:
`Gate implement: PASSED — Next: cycle-review — pass <n> ready for review`

# Guardrails
- Never send, publish, merge, or share anything. Finalizing happens only after verify passes.
- Never invent facts, figures, quotes, or APIs. If a source is missing, write `[NEEDS SOURCE]` and flag it.
- Never mark review or verify as passed.
