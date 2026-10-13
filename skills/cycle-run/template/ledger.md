---
project: {{project-stub}}
project_path: Documents/Projects/{{project-stub}}
cycle_id: YYYY-MM-DD-{{cycle-slug}}
title: {{short task title}}
owner: {{user}}
work_type: m365            # m365 | code
mode: full                 # full | fast
status: in-progress        # in-progress | blocked | done | abandoned
phase: research
gates: {research: open, plan: open, test: open, implement: open, review: open, verify: open, remember: open, improve: open}
loops: {review: 0, verify: 0}
overrides: []
deliverable: {{path under project_path/outputs/, filled by cycle-implement}}
---
<!-- TEMPLATE: ledger
     Used by: cycle-run, which writes it to {{project_path}}/cycles/{{cycle_id}}.md
     Replace every {{placeholder}}. Keep headings, IDs and table columns unchanged so other cycle-* skills can parse them. -->

## 0. Research Brief
<!-- owned by cycle-research -->

## 1. Plan
<!-- owned by cycle-plan -->

## 2. Acceptance Criteria
<!-- owned by cycle-test -->

## 3. Implementation Log
<!-- owned by cycle-implement -->

## 4. Review Findings
<!-- owned by cycle-review -->

## 5. Verification
<!-- owned by cycle-verify -->

## 6. Lessons
<!-- owned by cycle-remember -->

## 7. Improvements
<!-- owned by cycle-improve -->
