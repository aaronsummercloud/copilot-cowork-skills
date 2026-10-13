# Copilot Cowork Skill Suite: plan → test → implement → review → verify → remember → improve

## 1. Platform constraints that shape the design

From Microsoft's Cowork docs and the Copilot Camp lab (as of Sept 2026):

| Constraint | Design consequence |
|---|---|
| A skill is a folder holding `SKILL.md` (YAML frontmatter with `name` and `description`, plus an optional `cowork:` block with `category` and `icon`). `name` is kebab-case and matches the folder name. | One folder per phase. All folders share a naming prefix so they sort together. |
| Cowork picks skills by matching their `description`. Several skills can load at once. **There is no formal way for one skill to call another.** | Skills hand off through a **shared ledger file** and explicit "next phase" lines, not through calls. Each description names its trigger phrases and the phase it follows. |
| Skills live in OneDrive under `Documents/Cowork/skills/<name>/`. An archive can bundle up to 100 companion files. | Each skill can bundle its own templates. The state shared between skills lives in OneDrive, not inside the skills. |
| Custom instructions (Preferences tab, up to 20 KB) apply to every task. | A short "constitution" snippet there is the backstop that keeps the cycle enforced even when a skill doesn't trigger. |
| Skills have no documented native memory. | **Remember** writes to a OneDrive memory file that **plan** reads at the start of every cycle. |
| Plugin upload accepts Claude-compatible plugin packages and converts them. | Option to ship the whole suite as **one plugin**: one install, one share, versioned together. |
| Users get up to 50 custom skills, and a skill should be tested in a new conversation. | 8 skills fits easily. The test plan is built around starting new conversations. |

## 2. Suite architecture

```
                 ┌──────────────── cycle-run (orchestrator / gatekeeper) ────────────────┐
                 │  reads/writes ledger header, enforces gate order, routes to next phase │
                 └───────────────────────────────────────────────────────────────────────┘
   memory ──► cycle-plan ─► cycle-test ─► cycle-implement ─► cycle-review ─► cycle-verify ─► cycle-remember ─► cycle-improve
     ▲                                          ▲                 │ fail          │ fail                │
     │                                          └─────────────────┴───────────────┘                     │
     └──────────────────────────────────────── lessons ──────────────────────────────────────────────────┘
```

| # | Skill (`name`) | Job | Must NOT do |
|---|---|---|---|
| 0 | `cycle-run` | Entry point for any non-trivial task. Opens or resumes the ledger, reports the current phase, enforces gate order, and routes to the next phase. | Produce the deliverable itself. |
| 1 | `cycle-plan` | Reads memory first. Captures goal, audience, scope and non-scope, constraints, sources, deliverable format, and risks. Ends with the user approving the plan. | Start drafting the deliverable. |
| 2 | `cycle-test` | Writes acceptance criteria **before any work starts**. Each criterion is observable, gets an ID (AC-1…), and states how it will be checked (source check, rubric, format check, or the user's sign-off). | Change scope without going back to plan. |
| 3 | `cycle-implement` | Builds the deliverable against the plan and the ACs. Grounds every claim in retrieved sources. Outbound messages stay as drafts only. Logs any deviation from the plan. | Mark anything as reviewed or verified. |
| 4 | `cycle-review` | Takes an adversarial critic's stance. Lists findings by severity (blocker, major, minor) covering quality, clarity, risk, and gaps against the plan. A blocker or major finding sends the work back to implement. | Fix things silently. It reports, and implement fixes. |
| 5 | `cycle-verify` | Gives an evidence-backed PASS or FAIL for each AC, re-checking facts against the sources. Every AC must pass before anything is sent or finalized. A FAIL routes to implement, or back to test if the criterion itself was wrong. | Accept "looks good" as evidence. |
| 6 | `cycle-remember` | Distills what was learned (what worked, what failed, user preferences, reusable checks) into the memory file as structured, deduplicated entries. | Store anything sensitive or specific to a single task. |
| 7 | `cycle-improve` | Mines memory and recent ledgers for patterns, then proposes concrete edits to skills, AC templates, or custom instructions as before/after text. A human approves and applies them. | Edit skills without approval. |

## 3. The interoperability contract (the most important part)

### 3.1 Ledger: one file per task
Path: `OneDrive/Documents/Cowork/cycles/YYYY-MM-DD-<slug>.md`

```markdown
---
cycle_id: 2026-10-12-q3-board-summary
status: in-progress        # in-progress | blocked | done | abandoned
phase: test                # plan | test | implement | review | verify | remember | improve
gates: {plan: passed, test: open, implement: open, review: open, verify: open, remember: open, improve: open}
loop_count: {review: 0, verify: 0}
---
## 1. Plan            (owned by cycle-plan)
## 2. Acceptance Criteria   (owned by cycle-test)   AC-1 … AC-n, each with "Check:" line
## 3. Implementation Log    (owned by cycle-implement) deliverable link + deviations
## 4. Review Findings       (owned by cycle-review)  R-1 … with severity + status
## 5. Verification          (owned by cycle-verify)  AC-n: PASS/FAIL + evidence
## 6. Lessons               (owned by cycle-remember) what was written to memory
## 7. Improvements          (owned by cycle-improve)  proposals + decision
```

### 3.2 Rules every skill follows
1. **Entry check:** read the ledger header. If the previous gate isn't `passed`, stop and route to that phase.
2. **Write only to your own section.** You may set your own gate and `phase`, and nothing else.
3. **Exit line:** every phase ends with the same block:
   `Gate <phase>: PASSED|FAILED — Next: <skill-name> — Reason: …`
4. **Loop limit:** after 3 review→implement or verify→implement loops, set `status: blocked` and hand the decision to the user.
5. **Ask the user at:** plan approval, AC approval, and before anything is sent or finalized after verify.

### 3.3 Memory
Path: `OneDrive/Documents/Cowork/memory/`
- `lessons.md` holds entries in the form `L-### | date | tag | lesson | evidence(cycle_id) | times-confirmed`
- `ac-library.md` holds reusable acceptance criteria by deliverable type (exec email, report, deck…)
- `preferences.md` holds stable user and stakeholder preferences

`cycle-plan` and `cycle-test` read these. `cycle-remember` writes them. `cycle-improve` prunes and promotes them.

### 3.4 Fast path
For small tasks, `cycle-run` can merge phases into one turn, but **no phase is skipped**: a single-line plan, two or three ACs, the draft, a one-paragraph self-review, the PASS/FAIL table, and a one-line lesson. This keeps the enforcement from becoming tedious.

## 4. Backstop: custom-instructions snippet (about 1 KB)
> For any task producing a deliverable, follow the cycle: plan → test → implement → review → verify → remember → improve, using the cycle-* skills and a ledger in Documents/Cowork/cycles/. Never finalize or send anything until cycle-verify has passed every acceptance criterion. Read Documents/Cowork/memory/lessons.md before planning.

## 5. SKILL.md template (shared shape)
```markdown
---
name: cycle-review
description: >
  Phase 4 of the cycle. Use after cycle-implement has produced a draft, or when the user
  says "review this", "critique", "what's wrong with this draft". Do NOT use to check
  acceptance criteria (use cycle-verify) or to start new work (use cycle-run).
cowork:
  category: productivity
  icon: <icon>
---
# Overview
# Entry Check        (ledger gate rules)
# Instructions       (numbered)
# Output             (exact section format written to ledger)
# Exit               (gate line + next skill)
# Guardrails
```

## 6. Build and validation order
1. Lock the ledger template and the exit-line format. Every other skill depends on them.
2. Write `cycle-run`, `cycle-plan`, and `cycle-test`, then run a real task through them in Cowork and refine the triggers.
3. Write `cycle-implement`, `cycle-review`, and `cycle-verify`, and test the fail loops deliberately.
4. Write `cycle-remember` and `cycle-improve`, then run two cycles and confirm the lessons from the first cycle show up in the second cycle's plan.
5. Trigger tests: for each skill, check about 5 phrases that should load it and 3 that shouldn't, using the Skills panel in new conversations.
6. Package the suite as individual uploads or as a single plugin zip, and add the custom-instructions snippet.

## 7. Decisions (2026-10-12)
- **Domain:** M365 and code. Each ledger has `work_type: m365 | code`, which switches how test, implement, review, and verify behave. For code, cycle-test writes failing tests first. If Cowork can't run code, the user runs the command and pastes the output, and verify never reports a PASS without real output.
- **Ledger:** a Markdown file.
- **Gates:** soft. A skipped gate gives a warning and appends an entry to `overrides` in the ledger.
- **Distribution:** individual skill uploads. Because there are no shared files, each SKILL.md is self-contained, and the full ledger template lives in `cycle-run`.
- **Still to verify in Cowork:** whether skills can write to OneDrive. If they can't, every skill falls back to keeping the ledger inline in the conversation for the user to paste.

## 8. Change: research phase added (2026-10-12)
`cycle-research` (phase 0) runs before `cycle-plan`. It writes ledger section "0. Research Brief": every external or time-sensitive claim is listed as an F-# with a status of CONFIRMED, CHANGED, or UNVERIFIED, a source link, and the date retrieved. For code, the versions installed in the project take precedence over the latest docs. Facts flow into the other phases like this:
- **cycle-plan** cites F-#s.
- **cycle-test** turns key facts into source-check ACs, and never accepts an UNVERIFIED fact as an AC.
- **cycle-verify** re-opens each F-# source.
- **cycle-remember** records CHANGED facts as `stale-knowledge` lessons.
- **cycle-research** re-checks those `stale-knowledge` lessons in future cycles.

The gate can be `skipped`, with a reason, when the task depends on no external facts. The suite is now 9 skills.

## 9. Change: project folders (2026-10-12)
`cycle-run` creates `Documents/Projects/<project-stub>/` for each new project. The folder holds `README.md` (the project index), `cycles/` (ledgers), `outputs/` (deliverables and code), and `research/` (source snapshots). All generated content goes there.
- The ledger header now has `project` and `project_path` fields.
- A project can hold multiple cycles.
- Memory stays shared across projects in `Documents/Cowork/memory/`.
- If code lives in an existing codebase outside the project folder, it is edited in place, and a change summary is saved to `outputs/`.
- The stub is lowercase kebab-case and confirmed with the user. An existing project folder is never overwritten.

## 10. Change: skill folder layout and build (2026-10-12)
Each skill folder contains `SKILL.md` and, when it needs them, these subfolders:
- `template/`: Markdown templates using `{{placeholder}}` syntax (ledger sections, the ledger, the project README, memory files, research snapshots).
- `reference/`: reference material. `cycle-contract.md` is kept in `shared/reference/` and copied into every skill.
- `scripts/`: none so far.

`python3 tools/build.py` does three things:
1. Copies the shared files into each skill.
2. Validates each skill: frontmatter, name matches the folder, every `template/`, `reference/`, and `scripts/` path the skill mentions exists, and Cowork's size and file-count limits.
3. Writes upload-ready zips to `dist/<skill>.zip`, with `SKILL.md` at the root of each zip.

`--check` validates only. Skills must now be uploaded as zips, because a single `.md` upload would drop the subfolders.

## 11. Added: slide-deck-studio and cowork-env-probe (2026-10-12)
**What the sandbox has.** `cowork-env-probe` confirmed that Cowork's sandbox runs Azure Linux 3.0 with Python 3.12.15, Node 24.7, LibreOffice, pdftotext, pandoc and ffmpeg. The Python libraries include python-pptx, python-docx, openpyxl, Pillow, matplotlib, pandas, pypdf and requests. PyMuPDF is missing. The report didn't cover pdftoppm, cairosvg, browsers or fonts.

**How `slide-deck-studio` works.** It designs decks web-first:
1. A design brief, critiqued before building.
2. One HTML file (960×540 px slides) following `reference/html-contract.md`, with inline geometry and `:root` tokens.
3. `check_deck.py`, which checks the contract and the design rules: contrast, overflow, Office fonts, palette drift, title drift, AI-design tells and buzzwords.
4. `html_to_pptx.py`, which builds a native python-pptx deck (text, shapes, native charts, tables, SVG with a PNG fallback, and speaker notes).
5. `render_preview.py`, which renders through LibreOffice to PDF, then to PNGs if pdftoppm exists, plus a contact sheet.

The design rules come from the installed skills frontend-design, pptx, pptx-generator, ui-ux-pro-max, dataviz and humanize-writing.

**Tested locally:**
- The template deck passes the checker with no errors and no warnings, and converts to 8 slides.
- The output passes the pptx skill's OOXML validator (`validate.py`).
- A deliberately broken deck produces the expected errors.
- It has **not** yet been rendered in PowerPoint or LibreOffice.

The sample output is `examples/harbour-sample.pptx`.

## 12. Change: motion added to slide-deck-studio (2026-10-12)
The installed `ui-animation` and `animate` skills are now built in. Motion is opt-in, and every transition and build must name a purpose in the brief's motion plan. Purposes are explanation, continuity, emphasis, pacing, or delight on rare moments.

**Attributes.** Slides take `data-transition` (none, fade, push, morph). Elements take `data-build`, `data-anim` (fade, float-up, wipe-up, wipe-right, appear), `data-duration`, `data-delay` and `data-morph`. `<body data-mode="pre-read">` turns builds off.

**PowerPoint output.** `scripts/motion.py` writes native PowerPoint transition and timing XML, which python-pptx has no API for. Morph is written with a Fade fallback for older PowerPoint versions. Entrances decelerate, so they ease out.

**Preview.** The template has a present mode (press P) that plays the same motion with the skills' curves, and respects reduced motion.

**Checks.** The checker adds motion rules: valid values, duration bands, no hidden titles, auto-play only on cover, section and closing slides, at most 5 clicks per slide, one entrance per container, one transition style per deck, Morph keys that pair, no builds in pre-reads, and no motion on most slides.

**Tested.** The validator passes and the present mode renders with no JavaScript errors. Neither has been played in PowerPoint yet.

## 13. Added: visual-design-studio (2026-10-12)
**Sources.** The skill was synthesized from top-ranked skills.sh design skills, read but not installed:
- anthropics/frontend-design (977K)
- vercel-labs/web-design-guidelines (726K)
- leonxlnx/taste-skill (596K), plus its stitch-skill and gpt-taste
- pbakaus/impeccable (328K)
- heygen-com/hyperframes-animation

It also uses these locally installed skills: ui-ux-pro-max, ui-animation, animate, pptx and dataviz.

**What it is.** One design method for every medium: a design read with a mode and three dials, then a `DESIGN.md` of tokens, then layouts, then a single batched inspection. It covers web and UI as single-file HTML, documents as A4 HTML/PDF and as Word via `build_docx.py`, and hands presentations to slide-deck-studio.

**Scripts.**
- `lint_design.py` (stdlib only) checks accessibility, contrast computed from tokens, motion, and about 30 generic-AI tells.
- `build_docx.py` (python-docx) builds the cover band, key figures, callouts, pull quotes, ruled tables and page-number footer.

**Examples.** A Persuade landing page (night train) and a Read report (urban canopy), both linting clean and screenshot-checked at desktop and mobile. A docx built from the report's Markdown passes the OOXML validator. The build tool now also allows an `examples/` folder.

## 14. Change: slide-deck-studio merged into visual-design-studio (2026-10-12)
One skill now covers pages, UI, reports, Word documents and decks from a single DESIGN.md. To stay within Cowork's 20-companion-file limit, the files were consolidated:

**Scripts** (5):
- `lint_design.py`
- `build_docx.py`, which now takes theme keys from the Markdown front matter, so `doc-theme.json` was dropped
- `deck_check.py` = deckparse + motion vocabulary + check_deck
- `deck_to_pptx.py` = html_to_pptx + motion XML writer
- `render_preview.py`, which now handles pptx, docx, html and pdf

**References** (8): the slide layouts, Office fonts, chart rules, AI tells, motion and QA were folded into the existing seven files, and a new `deck-contract.md` was added.

**Templates** (4): `tokens.css`, `page.html`, `design-brief.md` (now with an Office mapping and a deck story), and `deck.html`.

**Examples** (3): unchanged.

**Archive:** the old skill moved to `archive/slide-deck-studio/` and is no longer built.

**Verified from the packaged zip:**
- The deck check passes, and the conversion writes 8 slides with the package verified. The pptx passes the OOXML validator.
- The two examples lint clean.
- The docx builds and passes the OOXML validator.

## 15. Change: Excel dashboards added to visual-design-studio (2026-10-12)
**New files:**
- `scripts/build_xlsx.py` (openpyxl) turns a JSON spec into a workbook with:
  - Data sheets holding formatted Excel Tables.
  - A Dashboard sheet on a 12-column grid: a claim title, KPI tiles with direction-colored deltas, and chart, table and text panels.
  - Live formulas through `{Table.Column[last]}` placeholders. Functions LibreOffice can't evaluate are refused, and post-2007 functions get the `_xlfn.` prefix.
  - One-page landscape print, and `fullCalcOnLoad`.
- `examples/dashboard-harbour.json`, which uses the same harbour palette as the deck template.

**Consolidated** to stay within 20 companion files: `design-read.md` was inlined into SKILL.md, and `anti-patterns.md` plus `qa-checklist.md` became `quality.md`. `render_preview.py` now also handles xlsx, scanning the LibreOffice PDF for #NAME?, #REF! and similar.

**Local QA with the user's Craft apps.**

| App | How it's driven | What it showed |
|---|---|---|
| GridCraft | Control server on `GRIDCRAFT_CONTROL_PORT`, no auth; `file.open` and `file.exportPdf` | All formulas computed. Five defects found and fixed, listed below. |
| WordCraft | `WORDCRAFT_CONTROL_PORT`, with a key file in Application Support; `file.open` and `file.exportPng` | Cover band had no padding and the footer appeared on the cover. Fixed: `tcMar` in schema order, and a different first page. |
| PdfCraft | `--control <file>` writes a port and token | Control calls were blocked by the auto-mode classifier as credential use. Needs the user's permission. |

The five GridCraft defects:
1. KPI alignment
2. Delta units (now percentage points)
3. A chart title shown automatically; `autoTitleDeleted` is now injected, though GridCraft ignores it
4. Two-page print
5. Charts overrunning their span; charts now use two-cell anchors so they fit the grid in any viewer

## 16. Change: one `vds.py` CLI, no ArtCraft references, low-poly motion, six-format rerun (2026-10-12)
**Implemented the first test's 13 recommendations** (`test-run/TEST-REPORT.md`):
- The six scripts were merged into `scripts/vds.py` (lint, chart, pdf, render) and `vds_deck.py` / `vds_office.py` (deck-check and deck, docx and xlsx). This freed room in the 20-companion budget.
- `vds.py chart` draws one data spec as a token-styled SVG (follows light and dark themes) or a PNG (Word). Supports single-point highlight and a reference line.
- New Markdown and PDF adapters, a Markdown lint mode, and a PDF page-fill check.
- Deck chart highlight, per-font width calibration with `data-fit="verified"`, Excel `row_formats`, Word images and `[TOC]`, plus page-template overflow guards and a mobile header.

**ArtCraft references removed from the skill.** The skill now names only Cowork's default tools: Python libraries, LibreOffice, pdftotext, image generation and the preview pane. `tools/craft_qa.py` remains as a repo-only local QA tool and isn't packaged.

**Low-poly motion:** `examples/motion-lowpoly.html` is a flat-shaded canvas engine in plain JavaScript with no libraries. It includes a spinning globe, a package opening on click, a wind turbine and a coin flip. Each has pause controls, a reduced-motion still frame, and an off-screen pause. `reference/motion.md` has a "Low-poly 3D in plain JavaScript" section.

**Six-format rerun** (`test-run2/TEST-REPORT.md`):
- All six formats passed their checks.
- deck-check passed without `--force`.
- The PDF has no underfilled page.
- One new defect was fixed: bar labels colliding with the reference line (SVG and PNG).
- Office files were checked structurally only, because LibreOffice isn't installed locally.

## 17. Added: low-poly animations in PowerPoint (2026-10-12)
PowerPoint can't run canvas JavaScript, and Cowork has no browser to record one, so the renderer was ported to Python.
- **`scripts/vds_lowpoly.py`** (`vds.py lowpoly`): the same engine and scenes as `examples/motion-lowpoly.html` (globe, turbine and cabinet loop; package and coin play once).
  - Colours come from a deck's or page's `:root` tokens (`--tokens deck.html`).
  - Outputs a poster PNG, an H.264 MP4 through ffmpeg (a seamless cycle, or the one-shot plus a 1 s hold), and a GIF that plays once.
  - Pillow draws at 3× and scales down to smooth the edges. A 14 s cabinet loop takes about 17 s to render here and comes to about 340 KB.
- **Deck contract:** a new `<video data-pptx="video" src poster data-play="auto|click" [loop] aria-label>` element.
  - The converter embeds it with python-pptx's `add_movie` and writes native timing: `mediacall playFrom` for the start, and `repeatCount="indefinite"` for loops. It merges this into the slide's build timing, so a slide has one `p:timing`.
  - `--no-motion` places the poster as a picture, and turns a GIF into its last frame.
  - `deck-check` checks the file, poster, alt text and `data-play`. It warns on more than one video per slide, files over 25 MB, and GIFs that loop forever.
  - `verify_package` now decodes only image media.
- **Template preview:** present mode plays videos (`auto` with the slide, `click` at its build step) and never hides them as builds. The chart preview now uses the number format's decimals and shows data labels and the highlighted point. Before this, labels like 4.62000001 were clipped.
- **Example:** `motion-lowpoly.html` gained the arcade cabinet, a non-convex shape that needs a draw-order bias and two-sided faces.
- **Test deck** (`demo-arcade/deck/`), with 4 slides:
  - Results: deck-check passed with 0/0, the package verified, and OOXML validation passed. The same steps also passed from a fresh copy extracted from the zip.
  - DeckCraft renders show each poster in place.
  - In headless Chrome, present mode autoplays the cover loop, and the click starts the package video. Chrome's virtual clock doesn't advance video started after page load, so full click-to-end playback needs a real browser.
  - **Not verified:** playback in PowerPoint itself (not installed here), and whether PowerPoint honours a GIF's play-once setting.
