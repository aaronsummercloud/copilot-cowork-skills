# Typography and color

This draws on `frontend-design`, `taste-skill`, `stitch-skill`, `ui-ux-pro-max`, `dataviz` and `web-design-guidelines`.

## Type
- **Families:** one or two. If two, make them clearly different, for example a grotesque display with a humanist or serif body. Weight, size and color create the hierarchy; size alone shouldn't.
- **Scale:** fluid on the web (`template/tokens.css` steps −1 to 5, ratio about 1.25 for body and steeper for display). Fixed in points for print and Office.
- **Display text:** line-height 1.0–1.1, letter-spacing −0.01 to −0.03em, and `text-wrap: balance`. Headlines run two or three lines at most, and a headline that wraps more is a font-size or container-width error.
- **Body text:** line-height 1.45–1.6, a 60–70ch measure, and `text-wrap: pretty`. Give a serif body slightly more leading.
- **Numbers:** `font-variant-numeric: tabular-nums` in tables, stats and timelines.
- **Characters:** `…` not `...`, curly quotes, the minus sign `−` for negatives, and non-breaking spaces in values like `10 MB` and `4.1 °C`.

### Choosing fonts by medium
| Medium | Where fonts come from | Rule |
|---|---|---|
| Web page in Cowork's preview | Google Fonts `<link>` plus a fallback stack | The page must still look right if the font fails to load. List close system fallbacks: "Avenir Next", "Segoe UI", system-ui. |
| Word or PowerPoint | Fonts installed with Microsoft 365 | The reader's machine renders the file. Map each web face to an Office face in the "Office mapping" section of DESIGN.md. |
| PDF from HTML | The same as web, but embedded at print time | Check the PDF render. LibreOffice substitutes fonts it doesn't have. |

**Pairings by aesthetic family.** These are starting points, not defaults; apply the swap test:

| Family | Web (display / body) | Office mapping |
|---|---|---|
| Contemporary grotesque | Bricolage Grotesque / Figtree | Segoe UI Semibold / Segoe UI |
| Civic editorial | Archivo / Newsreader | Segoe UI Semibold / Cambria |
| Swiss neutral (for Operate) | Geist or Manrope / the same | Segoe UI / Segoe UI |
| Engineered and condensed | Barlow Condensed / Barlow | Bahnschrift / Calibri |
| Literary and heritage | Fraunces or Playfair (justify it) / Source Serif 4 | Georgia / Cambria |
| Humanist and friendly | Nunito Sans / the same | Trebuchet MS / Calibri |

Inter, system fonts only, and serif "because creative" are defaults to avoid unless the brief asks for them *(lint)*.

### Fonts for Word and PowerPoint
These are the fonts installed with Microsoft 365 that the deck checker accepts. Any other font is an error, because PowerPoint would substitute it.

| Pairing (heading / body) | Character | Fit reliable in the LibreOffice preview? |
|---|---|---|
| Cambria / Calibri | Classic, calm | Yes |
| Bookman Old Style / Arial | Sturdy, old-style | Yes |
| Century Schoolbook / Calibri | Academic | Yes |
| Georgia / Calibri | Warm, editorial | Body yes, heading approximate |
| Rockwell / Calibri | Slab, industrial | Heading approximate |
| Segoe UI Semibold / Segoe UI | Product, neutral | Approximate |
| Bahnschrift / Bahnschrift | Engineered, condensed | Approximate |
| Franklin Gothic Medium / Calibri | News, assertive | Heading approximate |

- Avoid Aptos as the default; older Office installs lack it.
- Leave 15% slack where the fit is only approximate.
- In the deck's `:root` tokens, list the Office font first and preview fallbacks after it: `Calibri, Carlito, 'Segoe UI', Arial, sans-serif`.

### Slide type scale (px on the 960 × 540 canvas; pt = px × 0.75)
| Element | px |
|---|---|
| Stat | 72–110 |
| Cover title | 56–80 |
| Slide title | 40–48 |
| Card title | 26–32 |
| Body | 20–24 (minimum 18.7 = 14pt) *(checked)* |
| Caption or source | 14–16 (minimum 13.3 = 10pt) *(checked)* |

## Color
- **Name colors by role**, not hue: `--surface`, `--surface-raised`, `--surface-sunken`, `--ink`, `--ink-muted`, `--line`, `--accent`, `--accent-ink`. Define them once in `:root`; components never use raw hex *(lint)*.
- **Dominance:** one color carries 60–70% of the visual weight, one or two supporting tones carry 20–30%, and the accent carries about 10%, used for a single highlight per view.
- **One accent**, below 80% saturation, kept the same across the whole deliverable.
- **Contrast** (WCAG, computed by the linter):

| Text | Ratio |
|---|---|
| `--ink` on `--surface` | at least 7:1 (aim) |
| Body and muted text on any surface | at least 4.5:1 |
| Large text (24px+, or 18.7px+ bold) and UI icons | at least 3:1 |
| `--accent-ink` on `--accent` | at least 4.5:1 |

- **Dark themes are designed, not inverted.** Use a tinted dark surface (never `#000`), lift raised surfaces lighter, desaturate the accent slightly, and recheck every pair.
- **Ground the palette in the subject:** materials, light, place, era. Then run the swap test.
- **Status colors** (success, warning, error) are reserved for state and always paired with an icon or label.

### Palette families to rotate between (instead of cream with brass)
Cold luxury (silver, smoke and chrome) · forest and bone with an amber accent · true off-black and tan · cobalt and cream · terracotta and slate · olive, brick and paper · monochrome with one saturated pop · night blue with sodium amber (`examples/landing-night-train.html`) · civic green and white (`examples/report-urban-canopy.html`).

## Number formats (Excel, and the deck chart JSON)
| Value | Format | Note |
|---|---|---|
| Currency | `£#,##0` · `£#,##0.0,,"m"` · `$#,##0,"k"` | Put the unit in the format or the header, never in both |
| Percentages | `0%` · `0.0%` | Stored as fractions (0.15) |
| Change | `+0.0%;-0.0%;0.0%` · `+0.0" pts";-0.0" pts"` | Always signed, with the reference in the label or format (`" vs Jan"`) |
| Counts | `#,##0` | Align right, with tabular numbers |
| Zero as a dash | `#,##0;-#,##0;"–"` | Financial tables |

Color in spreadsheets follows the same roles: ink text, muted labels, one accent, and good/bad status colors reserved for direction. Financial models keep the standard input and formula colors: blue for inputs, black for formulas, green for links.

## Charts in any medium
Follow the dataviz method:
1. Choose the form from the data's job.
2. Assign color by its job: grey everything, and put the accent on the series the headline talks about.
3. Use one axis only and thin marks.
4. Label directly when there are few marks.
5. Include a source line.
6. Make sure identity never depends on color alone.

- **HTML and PDF:** inline SVG from `vds.py chart` (column, bar or line, with a highlight, a reference line and direct labels). Its colors are CSS variables with hex fallbacks, so the chart follows the page's light and dark themes, and it has an `aria-label` summarising the data.
- **Word:** the same spec as a PNG (`vds.py chart spec.json chart.png`), placed with `![alt](chart.png)`.
- **Excel:** native charts on the dashboard grid, from the `chart` panel spec in `examples/dashboard-harbour.json`. They have no chart title (the panel title carries the claim), no border, rounded corners off, light gridlines and theme series colors.
- **PowerPoint:** a native, editable chart from the `data-chart` JSON in `reference/deck-contract.md`. Types: column, bar, stacked, line, pie or doughnut, with one series color per palette token.

**Chart rules** *(checked in decks)*:
- Use a legend only for two or more series.
- Add data labels when there are 8 bars or fewer.
- Put no more than 5 slices in a pie.
- Use no more than 6 series.
- Keep the same label style on every chart.
