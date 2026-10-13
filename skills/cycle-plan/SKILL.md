---
name: cycle-plan
description: >
  Phase 1 of the work cycle. Use when a task needs a plan before work starts, or when the user
  says "plan this", "scope this", "what's the approach", "help me think through", or
  "let's plan". Captures the goal, audience, scope, constraints, sources, risks, and approach,
  after first reading past lessons from memory. Do NOT use to write acceptance criteria
  (use cycle-test) or to draft the deliverable (use cycle-implement). If no task ledger
  exists yet, use cycle-run first.
---

# Overview
Turn a request into a plan the user approves before anything else happens. A good plan makes
testing obvious and makes implementing boring.

# Entry Check
- Read the ledger. If there's none, follow `cycle-run` to create one first.
- If `gates.research` isn't `passed` or `skipped`, warn the user and offer to go to `cycle-research` or to continue. If they continue, log an override.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Load the research brief** (ledger section 0). Base the plan on `CONFIRMED` and `CHANGED` facts, citing them by F-#. Never rely on a fact marked `UNVERIFIED` unless the user accepted the risk; if they did, list it under Risks.
2. **Load memory.** Read `Documents/Cowork/memory/lessons.md` and `preferences.md` if they exist. Pick out up to 5 entries relevant to this task by tag, deliverable type, audience, or work_type, and list them under "Applied lessons".
3. **Ground in context.** Search the user's M365 data for relevant sources, such as prior versions, threads, meeting notes, and files. For `code`, identify the code location, the language or framework, how tests are run, and whether you can execute code in this environment. Take versions from the research brief, not from model memory.
4. **Ask, don't assume.** Ask at most 5 targeted questions, and only for gaps that would change the deliverable. Batch them into one message.
5. **Write the plan** into section 1 using the format below.
6. **Get approval.** Show the plan and ask the user to approve it or change it. Approval passes the gate.

# Output: ledger section 1
Write the ledger section using `template/ledger-section-1-plan.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
Set `gates.plan: passed` and `phase: test`, then end with:
`Gate plan: PASSED — Next: cycle-test — plan approved`
If the user won't approve yet, leave the gate open and end with
`Gate plan: FAILED — Next: cycle-plan — awaiting <what>`.

# Guardrails
- Don't start drafting the deliverable, even partially.
- Mark anything you inferred rather than were told as `(assumed)`.
- Keep the plan to one screen. Brevity forces clarity.
