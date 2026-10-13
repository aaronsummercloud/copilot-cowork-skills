# Copilot Cowork Skills

Agent skills (`SKILL.md` folders) for Microsoft 365 Copilot Cowork:

- **A work-cycle suite.** It enforces research → plan → test → implement → review → verify → remember → improve on any task that produces a deliverable.
- **visual-design-studio.** It art-directs and builds web pages, Word reports, PDFs, Excel dashboards, PowerPoint decks, posters and Markdown pages, all from one design system.

Each skill is uploaded to Cowork on its own, as a zip.

## Skills

| Skill | What it does |
|---|---|
| `cycle-run` | Entry point and gatekeeper. It starts a cycle, creates `Documents/Projects/<project-stub>/` and routes the work to the next phase. |
| `cycle-research` | Checks current, sourced facts before planning, so outdated model knowledge doesn't creep in. |
| `cycle-plan` | Sets the goal, audience, scope, constraints, risks and approach. |
| `cycle-test` | Writes acceptance criteria, or failing tests for code, before any work starts. |
| `cycle-implement` | Builds the deliverable against the plan and criteria. |
| `cycle-review` | Reviews the draft adversarially. |
| `cycle-verify` | Gives an evidence-based pass or fail for every criterion before anything is sent. |
| `cycle-remember` | Saves durable lessons to `Documents/Cowork/memory/`. |
| `cycle-improve` | Runs a retrospective and turns lessons into approved improvements. |
| `cowork-env-probe` | Reports what the Cowork sandbox can run: Python packages, command-line tools and fonts. |
| `visual-design-studio` | Design direction, a DESIGN.md token system, and builds for every medium (see below). |

### visual-design-studio
Everything runs through one command, `python3 scripts/vds.py <command>`, using only what Cowork already provides: Python 3.12, python-docx, python-pptx, openpyxl, Pillow, matplotlib, LibreOffice and ffmpeg.

| Command | Does |
|---|---|
| `lint` | Design and accessibility lint for HTML and Markdown |
| `chart` | Draws one data spec as an SVG that follows the page's colour tokens, or as a PNG |
| `pdf` | Prints to PDF and checks how full each page is |
| `render` | Renders .pptx, .docx, .xlsx, .html or .pdf files for visual QA |
| `deck-check`, `deck` | Checks an HTML deck, then converts it to native, editable PowerPoint with transitions and builds |
| `docx`, `xlsx` | Builds a designed Word report, or an Excel dashboard with live formulas |
| `lowpoly` | Renders a low-poly 3D scene (globe, turbine, arcade cabinet, package, coin) as a still image, MP4 or GIF, for decks |

## Install in Cowork
1. Build the zips with `python3 tools/build.py`. It syncs `shared/reference/` into the cycle skills, checks every skill (name, the files it references, file count and size), and writes `dist/<skill>.zip`. Use `--check` to check without building.
2. In Cowork, upload each zip as a custom skill.
3. Optionally, paste `custom-instructions.md` into **Cowork → Customize → Preferences**. It keeps the cycle enforced even when a skill doesn't trigger by itself.
4. Test each skill in a new conversation.

## Layout
```
skills/<name>/SKILL.md      one folder per skill, with template/, scripts/, reference/ and examples/ subfolders
shared/reference/           the cycle contract, copied into every cycle-* skill by the build
tools/build.py              validate and package
PLAN.md                     design decisions and change log
custom-instructions.md      the Cowork Preferences snippet
```

All example content in the skills (Brightwater, Copper Comet, Port Halden and others) is fictional.

## License
MIT. See `LICENSE`.
