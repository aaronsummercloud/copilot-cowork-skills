---
name: cycle-remember
description: >
  Phase 6 of the work cycle: capture durable lessons from a finished task into the user's
  memory files so future cycles start smarter. Use after verification passes, or when the
  user says "remember this", "save the lessons", "note that for next time", "log what we
  learned", or "what did we learn". Writes deduplicated lessons, reusable acceptance criteria,
  and stable preferences. Do NOT use to change skills or instructions (use cycle-improve).
---

# Overview
Turn this cycle's experience into memory that `cycle-plan` and `cycle-test` will read next
time. Store only what is durable, reusable, and safe to keep.

# Entry Check
- Read the ledger. If `gates.verify` isn't `passed`, warn the user and offer to go to `cycle-verify` or to continue. If they continue, log an override. Abandoned tasks may still record lessons.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Harvest candidates** from the ledger:
   - review findings, especially blockers and repeats
   - verify failures and loop counts
   - deviations and overrides
   - the user's corrections and stated preferences
   - ACs that proved useful
   - `CHANGED` facts from the research brief. Save these as lessons tagged `stale-knowledge`, recording the old belief and the new fact, for example "Library X v5 removed method Y; use Z".
2. **Filter.** Keep a candidate only if it's:
   - **durable:** likely true next month.
   - **reusable:** applies beyond this one task.
   - **actionable:** it changes what someone would do.
   - **safe:** contains no confidential content, personal data, credentials, or customer specifics. Generalize it, or drop it.
3. **Deduplicate.** Read the existing memory files first. If a lesson already exists, increment its `confirmed` count and update the date, rather than adding a duplicate. If a new lesson contradicts an old one, mark the old one `superseded-by L-###`.
4. **Write** to `Documents/Cowork/memory/`. If a file is missing, create it from its template first:
   - `lessons.md` from `template/memory-lessons.md`
   - `ac-library.md` from `template/memory-ac-library.md`: ACs grouped by deliverable type, for example "exec email", "board deck", or "python module".
   - `preferences.md` from `template/memory-preferences.md`
5. **Show the user** what you wrote in one compact list and let them veto any line.

# Output: ledger section 6
Write the ledger section using `template/ledger-section-6-lessons.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
Set `gates.remember: passed` and `phase: improve`, then end with:
`Gate remember: PASSED — Next: cycle-improve — <a> added, <c> confirmed`

# Guardrails
- Keep it to 1–5 entries per cycle. No diary entries.
- Never store secrets, personal data, or verbatim confidential content.
- If OneDrive writing isn't available, output the exact lines for the user to paste.
