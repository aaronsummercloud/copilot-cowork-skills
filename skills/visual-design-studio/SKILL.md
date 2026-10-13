---
name: visual-design-studio
description: >
  Art-directs and builds visually impressive deliverables from one design system: web pages and UI
  (single-file HTML), reports (Word .docx and PDF), Excel dashboards (live formulas, KPI tiles,
  native charts), presentations (HTML converted to native PowerPoint with charts and motion),
  posters and Markdown pages. Writes a DESIGN.md of tokens, draws every chart from one data spec,
  and runs design, accessibility and render QA. Use for "design a page", "landing page", "UI
  mockup", "design a report", "make this look professional", "create a deck", "pitch deck",
  "Excel dashboard", "fact sheet", "poster", "README", "design system" or "it looks generic". Do
  NOT use to edit an existing .pptx/.docx/.xlsx, build financial models, or fill a corporate
  template (use the built-in PowerPoint, Word or Excel skill).
---

# Overview
This skill does the work of a design director: deliverables that look art-directed, not generated. It applies one method to every medium:

1. **Read the brief.**
2. **Commit to a direction drawn from the subject.**
3. **Write the design system once** in DESIGN.md.
4. **Compose** with layouts that don't look templated.
5. **Build, inspect once in a batch, and fix.**

A page, a report and a deck made from the same DESIGN.md share one palette, one type pairing and one motif.

The rules come from widely used design skills: `frontend-design` (Anthropic), `web-design-guidelines` (Vercel), `taste-skill`, `impeccable`, `ui-ux-pro-max`, `ui-animation`/`animate`, `dataviz` and `pptx`. They're distilled in `reference/`.

**Environment (Copilot Cowork):** Python 3.12 with python-pptx, python-docx, openpyxl, lxml, Pillow and matplotlib; LibreOffice and pdftotext; built-in image generation; and an HTML preview pane. Don't install anything.

**Tools:** one entry point, `python3 scripts/vds.py <command>`, with the commands lint, chart, pdf, render, deck-check, deck, docx, xlsx and lowpoly. They're listed with examples in `reference/media-adapters.md`.

# Where files go
- Inside a work cycle, save to `<project_path>/outputs/design/`, reading `project_path` from the cycle ledger. Decks go in `outputs/deck/`.
- Otherwise, ask which project the work belongs to, and use `Documents/Projects/<project-stub>/outputs/…`.
- The HTML files are the source of truth. Never overwrite a file the user may have edited; save a new version with a `-v2` suffix.

# Instructions

## 1. Design read: decide the direction before designing
1. **Identify the signals:**
   - **Medium:** page, UI, document, dashboard or deck.
   - **Mode:** what success looks like for the person using it.

     | Mode | Success | Examples | Bias |
     |---|---|---|---|
     | **Persuade** | The visitor acts | Landing page, pitch | One strong visual, one call to action |
     | **Operate** | The user completes a task | UI, dashboard | Scannability, consistency, density |
     | **Read** | The reader understands | Report, guide | Measure, rhythm, figures that explain |
     | **Experience** | The work leads | Portfolio, showcase | The interface recedes |

     Choose the mode from the surface, not the company.
   - **Audience:** who it's for. The audience chooses the aesthetic, not your taste.
   - **Vibe words** the user used.
   - **Brand assets** that already exist: use them, never override them silently.
   - **Quiet constraints** such as accessibility, regulation or the public sector. These override aesthetic preference.
2. **State the read in one line:** "Reading this as: {medium} in {mode} mode for {audience}, with a {vibe} language, leaning toward {aesthetic family}."
3. **Set three dials, 1–10:**

   | Dial | Low | High |
   |---|---|---|
   | Variance | Symmetric | Art-directed |
   | Motion | Static | Cinematic |
   | Density | Airy | Packed |

   | Preset | Variance / Motion / Density |
   |---|---|
   | Mainstream landing page | 7/6/4 |
   | Creative landing page | 9/8/3 |
   | UI or dashboard | 4/3/7 |
   | Report | 5/1/5 |
   | Live deck | 6/3/3 |
   | Public sector | 3/2/5 |

   Above variance 4, avoid a centered hero. Above density 7, avoid decorative cards.
4. **Ground the design in the subject.** Its materials, light, place and era give you the palette, motif and imagery. Name one signature element and keep everything around it quiet.
5. **If the read genuinely forks**, ask one question. For a deck, also ask the job, whether it's live or a pre-read, and the data source. For a dashboard, ask the decisions it supports, the data source, and how often it refreshes.

## 2. Design system: plan, then critique, then get approval
1. **Read** `reference/typography-color.md`, `reference/layout-patterns.md` and `reference/quality.md` (Part 1, anti-patterns).
2. **Fill in `template/design-brief.md`** and save it as `DESIGN.md`. It covers:
   - the atmosphere, the signature element and the motif
   - color roles, with contrast ratios
   - web fonts **and** their Office mapping
   - the section plan, or for a deck the slide story (one claim per slide, with layouts varied)
   - imagery, with generation prompts
   - a motion plan, in which each moving item names its purpose ("no motion" is valid)
   - bans
3. **Critique the plan with the swap test.** For each choice, ask: would I have made this same choice for an unrelated brief? If so, it's a default; replace it with a decision taken from the subject, and write down what changed.
4. **Show the user** the design read, the palette, the type pairing and the section plan or slide story in a compact form, and get approval before building. **Exception:** if the user asked for the whole job end to end (for example "make all of them", "just build it", or a scheduled or automated run), state the brief in one compact message and carry on without waiting.

## 3. Assets
- **Images:**
  - Use Cowork's image generation, writing each prompt from DESIGN.md: the subject, the palette hex values, the light, the style, the aspect ratio, and "no text, no logos, no real people's likenesses".
  - If generation isn't possible, draw a subject-specific inline SVG illustration in the palette (see the landing example).
  - Never use random stock photos or fake UI built from divs.
- **Icons:** simple single-color inline SVGs. No emoji.
- **Charts:** keep each dataset once, as a chart spec, and draw it for every medium from that file (`reference/media-adapters.md`, One data source):
  - `vds.py chart spec.json chart.svg` for HTML and PDF. Colours are CSS tokens, so the chart follows light and dark themes.
  - `chart.png` for Word.
  - The same values in the deck's `data-chart` and the dashboard's tables.

  Follow the dataviz method in `reference/typography-color.md`: highlight the one point the title talks about. Use only the user's data, and include a source line.

## 4. Build for the medium (read `reference/media-adapters.md`)
- **Web page or UI:**
  1. Start from `template/page.html` and paste in the filled `template/tokens.css`.
  2. Compose the sections from `reference/layout-patterns.md`.
  3. Add motion as described in `reference/motion.md`. For a single 3D signature moment (a globe, a package opening, a product turning), use the low-poly canvas pattern in `examples/motion-lowpoly.html`; it needs no libraries.
  4. Model the result on `examples/landing-night-train.html`.
- **Report (HTML or PDF):** use the A4 sheet pattern in `examples/report-urban-canopy.html`.
- **PDF:** run `python3 scripts/vds.py pdf source out.pdf`. It prints HTML through a browser engine when one exists. In Cowork, which has no browser engine, produce the PDF from the Word document or the deck (LibreOffice converts those faithfully). Fix any underfilled-page warnings. For posters and covers, use the Posters pattern in `reference/layout-patterns.md`.
- **Markdown** (README, wiki, Teams or SharePoint page): follow the Markdown rules in `reference/media-adapters.md`. Use a claim H1, tables as figures, chart images with fallbacks, and relative links to the other artifacts. Then run `vds.py lint doc.md`.
- **Word document:**
  1. Write the content in the Markdown subset, with the DESIGN.md Office mapping in the front matter; see `examples/report-urban-canopy.md`.
  2. Run `python3 scripts/vds.py docx content.md out.docx`.
- **Excel dashboard or workbook:**
  1. Copy `examples/dashboard-harbour.json` and replace its content. Keep the structure: a theme taken from the DESIGN.md Office mapping; data tables; 2–6 KPIs, each with a delta; and panels whose spans add up to 12 per band (see `reference/layout-patterns.md`, Dashboards).
  2. Sort and aggregate the data in Python first. Every KPI and panel references the tables through `{Table.Column}` placeholders, so the workbook stays live.
  3. Run `python3 scripts/vds.py xlsx spec.json dashboard.xlsx`. It refuses functions LibreOffice can't evaluate, and warns on more than 6 KPIs, more than 6 series, or a pie with more than 5 slices.
- **Presentation:**
  1. Copy `template/deck.html` and set its `:root` tokens from DESIGN.md, with Office fonts first.
  2. Follow `reference/deck-contract.md` exactly: inline geometry, `var(--token)` colors, and `data-layout` on every slide. Use the layouts in `reference/layout-patterns.md` (Presentations) and add speaker notes.
  3. Add only the motion that the plan names (`data-transition`, `data-build`, `data-anim`, `data-morph`). For a low-poly 3D moment, render it with `vds.py lowpoly` and place it as a `video` element (Video and low-poly 3D in `reference/deck-contract.md`).
  4. Run `python3 scripts/vds.py deck-check deck.html` and repeat until it reports 0 errors.
  5. **Design gate:** the user reviews `deck.html` in the preview pane, pressing **P** to present and the arrow keys to step through builds.
  6. Run `python3 scripts/vds.py deck deck.html deck.pptx`. It checks the deck again, writes native objects and motion, and verifies the package. Add `--no-motion` for a static handout copy.

## 5. Inspect once in a batch, fix once (read `reference/quality.md`, Part 2)
1. **Automated checks:**
   - Pages, reports and Markdown: `python3 scripts/vds.py lint page.html|doc.md` must report 0 errors.
   - Decks: `vds.py deck-check` must report 0 errors.
   - Fix every warning, or record why it's deliberate.
2. **Look at the real render:**
   - Pages: the preview pane at desktop and true phone width, in both light and dark themes.
   - Decks, documents and dashboards: `python3 scripts/vds.py render file.pptx|file.docx|file.xlsx preview/`, which runs a text check, produces a PDF, scans `.xlsx` files for formula errors, and produces page images if `pdftoppm` exists.
   - Inspect every page or slide. Check overflow first.
3. Fix everything you found in the HTML or Markdown source, rebuild, confirm once, then stop polishing.

## 6. Deliver
1. Save the files.
2. Summarize in 5 lines or fewer:
   - the design read
   - the signature element
   - the files produced
   - any warnings kept on purpose
   - image slots still waiting for assets, or a motion summary for decks
3. Offer one next step, for example the matching deck, report, dashboard or page from the same DESIGN.md.

# Fallback: no code execution
1. Still do steps 1–3, and build the HTML. The preview pane needs no scripts. Review it by eye against `reference/quality.md`.
2. **For a deck,** write a build sheet: one table per slide, with each element's position in inches (px ÷ 96), size in points (px × 0.75), font, hex colors and text. Have the built-in PowerPoint skill build the deck from it.
3. **For a Word document or Excel dashboard,** give the built-in Word or Excel skill DESIGN.md, the layout rules and the content.
4. Tell the user that fidelity is lower on this path.

# Guardrails
- **The brief wins.** If the user names a style, palette or font, follow it, even when it's on the anti-pattern list.
- **Never fabricate** data, testimonials, logos, client names or statistics. Clearly label fictional example content.
- **Accessibility is the floor, not a bonus:** contrast, focus, semantics, alt text, reduced motion, and no horizontal scroll at 360px.
- **Don't send, publish or share.** Delivering means saving to the project folder.
- **Don't change an existing corporate template's identity**, unless the user asks for a redesign.
