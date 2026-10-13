# Cycle Contract

Shared rules for every `cycle-*` skill. Read this before you act. The canonical copy is kept in `shared/reference/` in the source repo, and `tools/build.py` copies it into each skill's `reference/` folder.

**Phase order:** research → plan → test → implement → review → verify → remember → improve

| Phase | Skill | Ledger section | Gate values |
|---|---|---|---|
| 0 research | cycle-research | 0. Research Brief | open, passed, skipped |
| 1 plan | cycle-plan | 1. Plan | open, passed |
| 2 test | cycle-test | 2. Acceptance Criteria | open, passed |
| 3 implement | cycle-implement | 3. Implementation Log | open, passed |
| 4 review | cycle-review | 4. Review Findings | open, passed |
| 5 verify | cycle-verify | 5. Verification | open, passed |
| 6 remember | cycle-remember | 6. Lessons | open, passed |
| 7 improve | cycle-improve | 7. Improvements | open, passed |

## Rules
- **Project folder:** every project gets its own folder in the user's OneDrive at `Documents/Projects/<project-stub>/`. **All generated content is saved there**, never anywhere else:
```
Documents/Projects/<project-stub>/
  README.md        project index: title, created date, owner, list of cycles with status
  cycles/          ledgers, one per cycle: YYYY-MM-DD-<cycle-slug>.md
  outputs/         deliverables: documents, decks, spreadsheets, email drafts (.md copy), code
  research/        optional source snapshots or excerpts referenced by the research brief
```
- **Ledger:** one Markdown file per cycle at `Documents/Projects/<project-stub>/cycles/YYYY-MM-DD-<cycle-slug>.md`. A project may hold several cycles.
- **Paths:** every phase reads `project_path` from the ledger header and saves into it. Never save to the OneDrive root, `Documents/`, or Cowork's default location.
- **Memory:** `Documents/Cowork/memory/` holds `lessons.md`, `ac-library.md`, and `preferences.md`. Memory is shared across projects, so it is the one thing that lives **outside** the project folder.
- Each phase writes **only its own section** of the ledger and updates only its own gate, plus `phase`.
- **Soft gates:** if the previous gate isn't `passed` (or `skipped`, which only research may use), warn the user and offer two choices. They can go back to that phase, or continue anyway. If they continue, append a line to `overrides` saying who, which phase was skipped, and why.
- **Loop limit:** after 3 review→implement or verify→implement loops, set `status: blocked` and ask the user how to proceed.
- **Exit line:** every phase ends its reply with
  `Gate <phase>: PASSED | FAILED | OVERRIDDEN — Next: <skill-name> — <one-line reason>`
