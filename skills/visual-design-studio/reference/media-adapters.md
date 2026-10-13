# Media adapters: one design system, every output

The design brief and tokens are the source of truth. Each medium applies them through its own adapter. Everything below runs in Copilot Cowork's sandbox: Python 3.12 with python-docx, python-pptx, openpyxl, Pillow and matplotlib, plus LibreOffice and pdftotext. Nothing gets installed. Files are saved to `Documents/Projects/<project-stub>/outputs/` when a cycle ledger exists, and otherwise to a folder the user chooses.

## The command line
Every tool is one entry point: `python3 scripts/vds.py <command>`. Run it with no arguments to list the commands.

| Command | Does |
|---|---|
| `lint page.html` or `lint doc.md` | Design and accessibility lint (errors and warnings) |
| `chart data.json out.svg` or `out.png` | One chart spec to a token-styled SVG (HTML/PDF, follows light and dark themes) or a PNG (Word) |
| `pdf in.html out.pdf` or `pdf in.docx out.pdf` | Print to PDF, then check page fill (see PDF rules) |
| `render file [outdir]` | QA render of .pptx, .docx, .xlsx, .html or .pdf: text check, PDF and page images |
| `deck-check deck.html` / `deck deck.html out.pptx` | Check the deck, then convert it to native PowerPoint |
| `docx content.md out.docx` / `xlsx spec.json out.xlsx` | Build a Word document or Excel dashboard |
| `lowpoly scene out-base [--tokens deck.html]` | A low-poly 3D scene as poster PNG, MP4 and GIF, for decks and documents |

## One data source for every medium
Keep each dataset once, as a chart spec, and draw it everywhere from that one file:
- **HTML and PDF:** `vds.py chart spec.json chart.svg`, pasted inside `<figure class="chart-scroll">`.
- **Word:** `vds.py chart spec.json chart.png`, then `![alt](chart.png)` in the Markdown.
- **Deck:** the same categories and values in the `data-chart` JSON (`reference/deck-contract.md`).
- **Excel:** the same rows as a data table in the dashboard spec.

Chart spec fields:

| Field | Values |
|---|---|
| `type` | `column`, `bar` or `line` |
| `categories` | the category labels |
| `series` | `[{"name", "values"}]` |
| `format` | `"0%"`, `"#,##0"`, `"€#,##0"`, … |
| `highlight` | `"last"` or an index; the one point in the accent |
| `reference` | `{"value", "label"}` for an average or target line |
| `labels` | direct labels (default true) |
| `aria` | the chart's accessible description |
| `width`, `height` | the viewBox size |
| `theme` | hex fallbacks for when the CSS tokens are absent (always used for PNG) |

| Output | How | Tools | QA |
|---|---|---|---|
| **Web page, landing page, microsite** | One self-contained `.html` file built from `template/page.html` and the tokens | Cowork's HTML preview pane | `scripts/vds.py lint`; check the preview at desktop and phone widths |
| **UI screen or prototype** | One `.html` file (Operate mode) with real states: empty, loading, error | The same | The linter, plus a keyboard-only walkthrough |
| **Report or document (HTML/PDF)** | A print-ready HTML file with `@page` A4 sheets (`examples/report-urban-canopy.html`) | `vds.py pdf` (see PDF rules for which route to use) | Page-fill check, then inspect every page |
| **PDF** | Choose by route: (1) HTML through a browser engine; (2) Word or deck through LibreOffice (faithful); (3) a cover or poster (layout-patterns, Posters) | `vds.py pdf` | `vds.py render file.pdf` |
| **Markdown** (wiki, README, Teams or SharePoint page) | A plain `.md` file that follows the Markdown rules below | Any editor | `vds.py lint doc.md` |
| **Word document** | Markdown with theme keys in the front matter, run through `scripts/vds.py docx` | python-docx | `vds.py render out.docx`, then inspect every page |
| **Excel dashboard or workbook** | A JSON spec (data tables, KPIs, panels), run through `scripts/vds.py xlsx`, giving live formulas and native charts | openpyxl | `vds.py render out.xlsx` (formula-error scan and PDF) |
| **Presentation (.pptx)** | `template/deck.html` with the DESIGN.md tokens (`reference/deck-contract.md`), then `scripts/vds.py deck`, giving native text, shapes, charts, tables, notes, transitions and builds | python-pptx; LibreOffice turns SVG into PNG fallbacks | `vds.py deck-check`, then `vds.py render deck.pptx` |
| **Images and illustrations** | Cowork's built-in image generation | Prompts written from the design brief | View each image in context on the page |
| **Email** | Use the Email skill. Keep it to a single column, 600px wide, with live text and no web fonts. | Built-in Email skill | Draft only |

## Web page rules for Cowork
- **One file.** Inline the CSS and JavaScript. Images can be relative files in an `assets/` folder next to the page, or `data:` URIs. Use a URI if the preview pane doesn't resolve relative paths.
- **External resources are optional enhancements.** Google Fonts and a CDN library may fail offline, so every font has fallbacks and the page works without the script.
- **Imagery:**
  1. Generate it with Cowork's image skill, writing the prompt from the brief: subject, palette (named hex colors), light, lens or style, aspect ratio, and "no text, no logos".
  2. Otherwise use a subject-specific inline SVG illustration drawn in the palette.
  3. Otherwise leave a labelled slot such as `<!-- IMAGE: hero, 4:5, prompt: … -->`, and list the slots for the user.

  Unify images from mixed sources with one treatment (the duotone CSS in the landing example).
- **Accessibility floor:**
  - `lang`, a `<title>`, and the viewport meta tag
  - a skip link
  - visible `:focus-visible`
  - semantic elements (`button` and `a`)
  - `alt` text on every image
  - `width` and `height` on images
  - 44px tap targets
  - reduced motion
  - no horizontal scroll at 360px

## Word document rules
- **Fonts and colors:** only fonts that ship with Microsoft 365. Copy the DESIGN.md "Office mapping" keys into the Markdown front matter (see `examples/report-urban-canopy.md`).
- **Structure from styles:** real Heading 1–3 styles, so the Navigation pane and a table of contents work, plus List Bullet and List Number.
- **Figures:** `![Renewable share by month, 2026](chart.png){width=150}` places a figure with alt text and a caption. Make the PNG with `vds.py chart`, from the same spec as the web chart.
- **Contents:** a `[TOC]` line inserts a table of contents, which Word fills in when the file is opened.
- **Design devices** `vds.py docx` supports:
  - a cover band with the title
  - key-figure blocks (`!stat`)
  - callouts (`> [!NOTE]`)
  - pull quotes
  - ruled tables, with the numbers right-aligned
  - a running footer with the page number
- **Beyond what the script covers** (tracked changes, an existing template, Word fields), use Cowork's built-in Word skill and give it the brief.

## Excel rules
- **Use formulas, never pasted results.** KPIs and table panels reference the data tables through placeholders (`{Table.Column}`, `[last]`, `[0]`, `[-2]`), so edits flow through.
- **Use functions LibreOffice can evaluate:** SUMIFS, INDEX/MATCH, COUNTIF, AVERAGEIFS, IFERROR. The builder refuses XLOOKUP, FILTER, SORT, UNIQUE, SEQUENCE, LET and LAMBDA, and adds the `_xlfn.` prefix to TEXTJOIN, CONCAT, IFS, SWITCH, MAXIFS and MINIFS.
- **Sort, filter and aggregate in Python first**, then write the table.
- **Mixed units in one table** (euros in one row, hours in another): give the table `"row_formats"`, one format per row. It applies to value columns without their own `format`, and table panels copy each cell's format.
- **Recalculation:** openpyxl writes no cached values, so the workbook recalculates when it's opened. Previews that read cached values show blanks until Excel or LibreOffice opens the file; `vds.py render` converts through LibreOffice, which computes them.
- **Editing an existing workbook, or building a financial model:** use the built-in Excel skill and keep the file's own conventions. This builder is for new dashboards and reporting workbooks.

## Markdown rules
Markdown is read in many viewers: GitHub, Teams, SharePoint, Cowork's preview, and plain text. Design for the weakest one.
- **Structure:** one H1 that states the claim, then H2 sections with claim titles and no skipped levels. Open with a one-paragraph summary and put the ask in a blockquote.
- **Tables are the figures.** Align numbers right (`--:`), bold the key value, and put the unit in the header or the value.
- **Charts:** a `vds.py chart` SVG or PNG image with alt text (`![Renewable share by month](chart.svg)`). Mermaid only where the viewer supports it, and always followed by a table or a sentence carrying the numbers *(lint)*.
- **Links:** relative links to sibling files; the link text says where it goes *(lint)*; no bare URLs *(lint)*.
- **No HTML** apart from `<sub>` for footnotes, no emoji used as icons, no ALL CAPS *(lint)*, and no em dashes *(lint)*.
- **Close** with a source line and a file table that links the other artifacts.

## PDF rules
- **HTML to PDF needs a browser engine** for faithful CSS (grid, flex, custom properties, `@page`). `vds.py pdf` uses Chrome, Chromium or Edge when one is installed.
- **Cowork has no browser engine.** There, LibreOffice would drop the layout, so `vds.py pdf page.html` stops and says so. Build the document as Word (`vds.py docx`) or as a deck, then run `vds.py pdf out.docx out.pdf`: LibreOffice converts Office files faithfully.
- **Page fill:** `vds.py pdf` warns when the last page is less than 40% full, or when any page is empty. Tighten the copy, merge pages, or move content up.
- **Posters, covers and one-page pieces** follow the Posters pattern in `reference/layout-patterns.md`.

## Deck rules
- **The HTML file is the source of truth.** Edit `deck.html` and convert again; never hand-edit the `.pptx`. Save revisions as `deck-v2.pptx`.
- **`--no-motion`** writes a static copy for handouts.
- **The converter verifies every package** before reporting success (XML parses, relationships resolve, images decode), and exits with an error if PowerPoint wouldn't open the file.
- **SVG images need `xmlns="http://www.w3.org/2000/svg"`.** The converter adds it when it's missing and warns, because without it every renderer shows the SVG as plain XML. The linter treats a missing namespace as an error for HTML pages.
- **If scripts can't run in a session:**
  1. Write a build sheet: one table per slide, with each element's position in inches (px ÷ 96), size in points (px × 0.75), font, colors and text.
  2. Have the built-in PowerPoint skill build the deck from it.
  3. Tell the user that fidelity is lower on this path.
- **A corporate .pptx template that must be used** goes to the built-in PowerPoint skill, with the design brief.

## Rendering for visual QA in Cowork
```bash
python3 scripts/vds.py lint page.html
python3 scripts/vds.py render out.docx preview/     # or deck.pptx / dashboard.xlsx / page.html / file.pdf
```
- **LibreOffice's HTML renderer** ignores much modern CSS (grid, clamp(), custom properties). Treat its PDF of a web page as a rough check only, and judge web pages in the preview pane. For Word files, the LibreOffice PDF is a close proxy for Word.
- **Check the dark theme as well as the light one.** Charts must use tokens, not hex *(lint)*.
- **Check at a true phone width (360–390px).** If you screenshot with headless Chrome, load the page inside a 390px iframe, because Chrome won't make a window narrower than 500px.
- **Viewer quirks are not file bugs.** Some lightweight viewers ignore chart settings that Office honours: deleted automatic titles, single-point colours, axis deletion and axis number formats. Confirm in LibreOffice before changing the builder.
