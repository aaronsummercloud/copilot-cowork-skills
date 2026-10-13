---
name: cycle-run
description: >
  Entry point and gatekeeper for the work cycle (research → plan → test → implement → review →
  verify → remember → improve). Use at the start of any task that produces a deliverable — a document,
  email, deck, analysis, spreadsheet, or code change — or when the user says "start a cycle",
  "new task", "resume", "where are we", "what phase", "continue the cycle", or "status".
  Opens or resumes the task ledger and routes to the correct phase skill. Do NOT use for
  one-off questions with no deliverable, and do NOT use to do the phase work itself
  (use cycle-research, cycle-plan, cycle-test, cycle-implement, cycle-review, cycle-verify, cycle-remember,
  cycle-improve).
---

# Overview
You are the gatekeeper of an eight-phase cycle. You don't produce deliverables. You open or
resume the **ledger**, report where the task stands, enforce phase order, and hand off to the
right phase skill.

Phases and the skills that own them:
0. research → `cycle-research` (may be `skipped`, with a reason, when there are no external facts)
1. plan → `cycle-plan`
2. test → `cycle-test`
3. implement → `cycle-implement`
4. review → `cycle-review`
5. verify → `cycle-verify`
6. remember → `cycle-remember`
7. improve → `cycle-improve`

# Cycle Contract
Read `reference/cycle-contract.md` before acting. It defines the project folder layout, ledger location, memory location, section ownership, soft gates, loop limit, and exit line. Every cycle-* skill follows it.

# Instructions
1. **Find the project.**
   - If the user names a project, or a ledger is already in context, use that project.
   - Otherwise, list the folders in `Documents/Projects/` and check each project's `cycles/` for ledgers with `status: in-progress` or `blocked`. Ask whether to resume one of those, start a new cycle in an existing project, or start a **new project**.
2. **New project: create the folder.**
   - Propose a `<project-stub>`: lowercase kebab-case, 3–40 characters, letters, digits, and hyphens only, taken from the project's name. For example, "Q3 Board Summary" becomes `q3-board-summary`. Confirm it with the user.
   - If `Documents/Projects/<project-stub>/` already exists, don't overwrite it. Ask whether to use that existing project or pick a new stub, for example by adding `-2`.
   - Create `Documents/Projects/<project-stub>/` with the subfolders `cycles/`, `outputs/`, and `research/`, plus a `README.md` from `template/project-readme.md`.
3. **New cycle:** create the ledger in `<project_path>/cycles/` from `template/ledger.md`, and add a line for it to the project `README.md`. Set `work_type` to `code` if the deliverable is source code, scripts, queries, formulas-as-code, or configuration. Otherwise set it to `m365`. Ask the user if it's unclear.
4. **Research comes first.** New cycles start at `cycle-research`. It decides whether the task depends on external or time-sensitive facts, and logs a skip if it doesn't.
5. **Choose the mode.**
   - **Full** is the default.
   - **Fast path** applies when the user says "quick" or the task is plainly small, such as a short email or a one-function fix. All eight phases still run, compressed into one reply: a research line (facts checked, or "skipped: <reason>"), a one-line plan, 2–3 ACs, the deliverable, a short review, a PASS/FAIL table, and one lesson. No phase may be skipped. Record `mode: fast`.
6. **Report status** in 3 lines or fewer: the project, the cycle, the current phase, the gates passed so far, any overrides, and the next step.
7. **Route.** State the exit line and continue directly into the next phase skill's instructions.
8. **Close.** When `improve` passes, set `status: done` and update the cycle's line in the project `README.md`.

# Output
- The status block (3 lines or fewer), then the exit line, for example:
  `Gate run: PASSED — Next: cycle-research — created Documents/Projects/q3-board-summary/ and cycle 2026-10-12-first-draft`

# Guardrails
- Never draft the deliverable here.
- Never mark another phase's gate as passed.
- If you can't create folders or write files in OneDrive, tell the user. Then keep the ledger inline in the conversation under the heading `LEDGER`, and ask them to create `Documents/Projects/<project-stub>/` and save it there.
- Never delete or overwrite an existing project folder or its files.
