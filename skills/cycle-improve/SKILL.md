---
name: cycle-improve
description: >
  Phase 7 of the work cycle: retrospective that turns accumulated lessons into concrete,
  approved improvements to the cycle-* skills, acceptance-criteria library, or the user's
  Cowork custom instructions. Use after cycle-remember, or when the user says "retro",
  "retrospective", "improve the process", "what should we change", "tune the skills", or
  "how can we do this better". Proposes before/after edits for human approval. Do NOT use to
  record lessons (use cycle-remember) or to edit skills without approval.
---

# Overview
Close the loop. Look across this cycle **and** past memory for patterns, and propose small,
specific changes to how the work is done. A human approves and applies every change.

# Entry Check
- Read the ledger. If `gates.remember` isn't `passed`, warn the user and offer to go to `cycle-remember` or to continue. If they continue, log an override.
- Read `Documents/Cowork/memory/lessons.md`, plus the 10 most recent ledgers across `Documents/Projects/*/cycles/` if they're available.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Find patterns**, using this cycle plus the history. Look for:
   - lessons with `confirmed >= 3`
   - the same review finding type appearing in 2 or more cycles
   - frequent overrides of a particular gate, which may mean the gate is too heavy
   - repeated verify loops
   - ACs that never fail, which may be dead weight
   - repeated `stale-knowledge` lessons in one area, which suggest that area should always be researched
   - research skips that later caused a verify failure
2. **Propose at most 3 improvements**, ranked by expected impact. Each one names:
   - **Target:** a specific `cycle-*` skill and section, `ac-library.md`, `preferences.md`, or the Cowork custom instructions.
   - **Change:** exact before/after text.
   - **Why:** the evidence, citing L-### numbers or cycle_ids.
   - **Risk:** what could get worse.
3. **Ask for a decision** on each one: approve, modify, or reject.
4. **Apply approved changes.**
   - Memory files and `ac-library.md`: you may edit these directly once approved.
   - Skills and custom instructions: give the full revised `SKILL.md` text, or the instructions snippet, for the user to apply through **Customize → Skills**, using edit or re-upload. Remind them to test it in a new conversation.
   - Mark lessons that were turned into a skill change as `promoted → <target>`.
5. **Close the cycle.** Set `status: done`.

# Output: ledger section 7
Write the ledger section using `template/ledger-section-7-improvements.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
Set `gates.improve: passed`, `phase: improve`, and `status: done`, then end with:
`Gate improve: PASSED — Next: none — cycle complete (<k> improvements approved)`
If nothing is worth changing, say so plainly. That's a valid outcome.

# Guardrails
- Never modify a skill or the custom instructions without explicit approval.
- Prefer deleting or simplifying over adding rules. The suite should get leaner over time.
- Make no more than 3 proposals per cycle.
