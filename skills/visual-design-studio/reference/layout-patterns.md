# Layout patterns that impress

This is a vocabulary for composing pages and documents that don't look templated. It draws on `taste-skill` (block vocabulary and layout discipline), `gpt-taste` (rhythm and spacing) and `pptx-generator` (slide types). Choose by the content's job, and **use at least four different layout families on a long page**, never the same family twice in a row.

## Grid and rhythm
- **Container:** 1,200–1,280px maximum, with a fluid gutter (`clamp(1rem, 0.5rem + 2.5vw, 2.5rem)`). Body text is no wider than 65ch.
- **Asymmetric splits beat 50/50:** `1.15fr 0.85fr`, `1.4fr 1fr`, `0.8fr 1.2fr`. Use 12 columns for documents and reports.
- **Section spacing:** `clamp(4.5rem, 3rem + 7vw, 9rem)` on marketing pages, half that in product UI. Inside a section, spacing is tighter than between sections. That contrast is what creates rhythm.
- **One spacing scale** (4px base) and **one radius family** throughout the deliverable.
- Use CSS Grid for two-dimensional layouts and flex for one-dimensional rows. Never use `calc()` percentage hacks.
- **Mobile:** declare the fallback below 768px for every multi-column section. Everything collapses to one column, with no horizontal scroll and tap targets of at least 44px.

## Heroes (Persuade)
| Pattern | When | Note |
|---|---|---|
| **Asymmetric split** | Default above variance 4 | Text left (headline at most 2–3 lines, a subtext of at most 20 words, one CTA plus at most one quiet CTA), with the visual on the right at 4:5 |
| **Editorial manifesto** | The message is the design | A huge headline and almost nothing else; centering is allowed here |
| **Full-bleed image with a scrim panel** | Imagery is the product | Text sits on a solid or translucent panel, never directly on a busy photo |
| **Kinetic type** | Motion 7+ | One orchestrated entrance, with a reduced-motion fallback |
| **Product-in-context** | Software or physical products | A real screenshot or generated image, never fake div UI |

A hero has at most four text elements: an optional eyebrow, the headline, the subtext and the CTAs. Logo walls, feature bullets and pricing teasers go below it.

## Content sections (mix the families)
- **Bento:** two to five tiles with deliberately unequal spans, as many cells as items, and at least two tiles with real visual variation (an image, an accent fill, a chart). There's an example in `examples/landing-night-train.html`.
- **Sticky stack or pinned title:** a title pinned on one side while a *real sequence* scrolls past (a timeline, a process, the moments of a night).
- **Route, timeline or process line:** stops on a drawn line. This is information, not decoration.
- **Big-number band:** one dominant figure with a caption, and supporting figures smaller. Never three equal stat cards.
- **Full-width quote:** a quote of at most three lines with a real attribution, plus a portrait or monogram.
- **Comparison:** two columns with the recommended option visually dominant.
- **Feature-plus-detail:** one large tile with four small ones, or a 2+3 split.
- **Logo wall:** logos only, under the hero, monochrome.
- **Closing CTA:** one large line and one button, with the same label used for that intent everywhere.

## Product UI (Operate)
- **Layout:** a sidebar (240–280px) or top bar, a content area with a page title and its primary action at top right, then filters, then the content.
- **Data first:** tables use tabular numbers, align numbers right, have a sticky header, and use row hover only.
- **Cards** only when grouping means something; otherwise use dividers and space.
- **States are part of the design:** empty, loading (skeletons the same shape as the content), error (inline, with the fix), and success (confirm in place).
- **Density 6–8:** 13–14px body text and 32–36px row height. Keep the 44px tap rule on touch devices.

## Documents and reports (Read)
| Page | Pattern |
|---|---|
| **Cover** | A full-bleed accent color or image, the title at 40–60pt in two or three lines, a subtitle of at most 30 words, organisation and date, and one subject motif. An optional band carries the key figure. |
| **Summary spread** | A claim headline, one dominant finding plus two supporting ones (asymmetric), two-column body text and a pull quote. |
| **Evidence page** | A claim headline, a lede, a chart with one highlighted series and a source line, and a method sidebar (about 50mm) on a sunken tint. |
| **Table page** | A ruled table (heavy rule under the header, hairlines between rows, the key row tinted) with numbered recommendations. Numbers are allowed because they're a sequence. |
| **Running footer** | Title and page number on a hairline. Never on the cover. |

- **Typography for reading:** body 10–11pt at line-height 1.45–1.55 with a 60–70ch measure. Headings in a contrasting display face; a serif body is justified in Read mode.
- **Print:** `@page { size: A4; margin: 0 }`, sheets of 210 × 297mm, `break-after: page`. There's an example in `examples/report-urban-canopy.html`.

## Charts on small screens
- **Width:** a chart drawn for a 720px column shrinks its labels to unreadable sizes on a phone. Wrap it in `<figure class="chart-scroll">`, so it keeps a 560px minimum and scrolls sideways, or swap in a horizontal bar chart (`vds.py chart` with `"type": "bar"`), which reads well when narrow.
- **Labels:** keep effective label size at 11px or more. Drop data labels before you drop the axis.

## Posters, covers and one-page pieces (Experience mode; from Anthropic's canvas-design)
- **Philosophy:** write a short visual philosophy first, 3–4 sentences naming the movement: form, colour, scale and rhythm. Then express it: about 90% visual and 10% text, with text as a rare, deliberate gesture.
- **Composition:** one dominant form (the motif at scale), generous negative space, and a strict grid with one intentional break. The title is the only large text.
- **Craft:** every alignment is checked and nothing is accidental. Render it and look at it at full size and as a thumbnail.
- **Output:** an A4 or A3 HTML sheet printed with `vds.py pdf` where a browser engine exists. In Cowork, use the deck route (a single 16:9 or portrait slide converted with `vds.py deck`, then `vds.py pdf deck.pptx out.pdf`).

## Dashboards and workbooks (Excel, Operate mode; built by `scripts/vds.py xlsx`)
A designed workbook separates **data** from **presentation**. The data sheets hold formatted Excel Tables that people edit. The Dashboard sheet only references them, so every KPI and chart stays live.

**Grid:** a 2.5-character gutter column, then 12 grid columns 11 characters wide (about 82px), and 20pt rows. Every tile, chart and table spans whole grid columns, and charts are anchored to cells and sized to their span. Gridlines are off on the dashboard.

| Zone | Rows | Composition |
|---|---|---|
| **Title block** | 2–4 | The claim as the title (22pt display font), what and when as the subtitle, "Updated …" right-aligned, and a hairline below |
| **KPI band** | 6–9 | 2–6 tiles of equal span. Each has a label, a value (26pt) and a delta with direction coloring (good or bad from the theme; set `"good": "down"` where lower is better). One `lead` tile may use the accent fill. |
| **Panels** | Flow below the KPI band | Each panel has a claim title (12pt), a caption (9pt muted) and then a chart, a table or a text note. Spans should add up to 12 per band: 8+4, 6+6, 4+4+4 or 12. Use different chart types across the bands. |
| **Footer** | Last row | Source and a note on fictional or provisional data |

**Panel types:**
- **Chart:** column, bar, stacked, line, pie or doughnut. Highlight one point (`"highlight": "last"`); use labels instead of an axis when there are 8 bars or fewer. One axis only.
- **Table:** live references to a data table, numbers right-aligned, with an optional data bar on one column.
- **Text:** the "so what", in 2–4 sentences on a tinted panel.

**Data sheets:**
- Bold header with a heavy rule, hairline rows, and no banding. Number formats state the unit.
- Freeze the header and turn on filters.
- Optional `bar` (data bar) or `scale` (one-hue color scale) on a column.
- Put each table that has row formulas on its own sheet, so the A1 references stay simple.

**Print:** landscape, one page wide, horizontally centered.

## Presentations (960 × 540 px canvas; see `reference/deck-contract.md`)
**Grid:** 56px side margins, 12 columns of 50px with 24px gutters (848px of content), and a 40px top margin. On content slides the title sits at `left:56 top:40 w:848 h:64`, at 40–48px, in **the same place on every content slide** *(checked)*. Set `data-layout` on every slide, and never use the same content layout twice in a row *(checked)*.

| `data-layout` | Job | Composition |
|---|---|---|
| `cover` | Open the deck and set its tone | A 56–80px title (two lines at most), a subtitle, a meta line, and the motif or visual on the right 40–45%. Dark background. |
| `agenda` | 3–5 sections | A vertical list for 3, a 2-column grid for 4–6. Numbered only because sections are a sequence. |
| `section` | A pause between parts | A 100–140px number or icon, a 48–56px title, a different background, and the same style on every divider |
| `stats` | 2–4 headline numbers | 72–110px numbers with 20px labels. One number may use the accent. Never three identical cards with no hierarchy. |
| `chart` | Evidence | A native chart over about 60% of the width, 2–3 takeaways, and a source line *(checked)* |
| `comparison` | A vs B | Two equal columns with the recommended option (or the problem) visually dominant |
| `process` | 3–5 steps in sequence | Circles on a connector line, with labels under them |
| `table` | Exact figures | At most about 6 rows by 5 columns at 18–20px, numbers right-aligned, the key row bold |
| `image` | Mixed media | A half-bleed image (`object-fit: cover`) with 2–3 points, or a full-bleed image with a scrim panel |
| `quote` | A voice | A 32–40px quote with an 18px attribution and lots of space |
| `icons` | 3–4 parallel points | Icons in colored circles with a bold header and one line each |
| `closing` | The ask | The decision as the title, numbered next steps, and a dark background that mirrors the cover |

**Slide craft:**
- One message per slide, with the title written as a claim.
- Every content slide needs a non-text visual element *(checked)*.
- Use a sandwich structure: dark cover and closing slides, light content slides.
- Repeat one motif throughout.
- Leave 10–15% slack in every text box *(overflow checked)*.
- Keep body text to 60 words or fewer *(over 90 is checked)*, and put the narration in speaker notes.
