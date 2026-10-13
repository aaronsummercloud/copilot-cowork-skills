# Quality: anti-patterns and the QA checklist

## Part 1: anti-patterns, the generic-AI tells

These are merged from `frontend-design`, `taste-skill`, `stitch-skill`, `gpt-taste`, `impeccable`, `pptx` and `humanize-writing`. Each one is a default, not a choice. **The brief always wins:** if the user asks for one of these looks, do it well. Otherwise, don't spend your design freedom on them. Items marked *(lint)* are caught by `scripts/vds.py lint`.

### Palette
- Purple or violet gradients and neon glows: the default "AI gradient" *(lint)*.
- A warm cream background (around `#F4F1EA`) with a serif display font and a terracotta, brass or oxblood accent. This is the default "premium craft" palette *(cream is linted)*.
- A near-black background with a single acid-green or vermilion accent.
- Pure `#000000`; use a tinted off-black instead *(lint)*.
- More than one accent, an oversaturated accent, warm and cool greys mixed together, or the accent changing color in a later section.
- Gradient text on headings *(lint)*.
- Sections that switch between light and dark themes mid-page. Lock one theme; one deliberate switch per page at most.

### Type
- Inter, or system fonts only, as the "choice" *(lint)*. Pick a face with character that suits the subject.
- A serif only "because creative". A serif needs a reason: editorial, publication or heritage.
- Highlighting one word of a headline in a different family or color. If emphasis is needed, use italic or bold of the same family.
- A tracked-out ALL-CAPS eyebrow above every heading. Allow at most one per three sections *(lint)*.
- Headlines that wrap to four or more lines (the container is too narrow) or that just shout. Hierarchy comes from weight, color and space.
- Meta strings joined with middle dots ("A · B · C · D"), labels like "WORD — fragment", and monospace for decoration.
- An em dash anywhere in the copy *(lint)*, and `...` instead of `…` *(lint)*.

### Layout
- A row of three identical feature cards *(lint)*.
- A centered hero over a gradient blob, when variance is above 4.
- Every section chopped into identical rounded cards with the same soft grey shadow. Use cards only where elevation means hierarchy.
- A row-after-row left-image/right-text zigzag. Allow at most two in a row, and use at least four different layout families on a long page.
- `01 / 02 / 03` numbering when the content isn't a sequence; "Step 1 / Phase 2" labels *(lint)*; "SECTION 04" eyebrows.
- An accent line under every title, decorative edge stripes, and hairline grids drawn only to look designed.
- Floating corner paragraphs next to big headlines (the split header with filler on the right).
- Bento grids with empty cells, or with only text on white tiles.
- Mixed corner radii with no rule *(lint)*.

### Imagery
- A text-only "hero" with a gradient blob. A hero needs a real visual.
- Fake product UI built from divs: fake dashboards, fake terminals, fake task lists.
- Random stock photos that don't match the subject. Use Cowork's image generation for on-subject imagery, or a subject-specific illustration, and unify mixed sources with one treatment (duotone, grain or crop ratio).
- Pills or tags laid over photos, decorative photo credits, and invented brand logos shown as plain text.
- Emoji as icons.

### Copy
- Filler verbs: elevate, seamless, unleash, next-gen, revolutionize, empower, supercharge, effortless *(lint)*.
- Placeholder people and brands: John Doe, Jane Doe, Acme, Nexus *(lint)*. Lorem ipsum is an error *(lint)*.
- Scroll cues such as "Scroll to explore" or a bouncing chevron *(lint)*.
- Fake-precise numbers (99.99%, 4.1×) that the brief doesn't support.
- Two CTAs with the same intent but different labels ("Get started" and "Sign up free"). Use one label per intent.
- Cute, mock-poetic labels ("Field notes", "Quietly trusted by").

### Charts and SVG *(lint)*
- Fixed hex colours inside inline SVG on a page that has a dark theme: the chart vanishes in dark mode.
- SVG images without `xmlns`, which show as XML source.
- No `svg { max-width: 100% }` guard, so wide charts overflow phones.
- Typed-in ALL-CAPS labels (e.g. "BRIGHTWATER ENERGY CO-OP"). Write sentence case and let type size and weight set the hierarchy.

### Slides *(vds.py deck-check)*
- An accent line under the title, or decorative edge stripes and header bars.
- Text-only slides, or the same layout on consecutive slides.
- Titles that move position or size between content slides, or that end with a period.
- Centered body text; body text under 14pt; more than about 90 words on a slide.
- Fonts that don't ship with Office.
- Colors that aren't palette tokens.
- Low contrast, computed against whatever is painted underneath.
- Text that overflows its box (estimated).
- Auto-play builds on content slides, a hidden title, more than 5 clicks per slide, and a card and its text entering separately.

### Spreadsheets and dashboards *(vds.py xlsx warns on some)*
- Default Excel look: gridlines on, Calibri 11 everywhere, rainbow default series colors, chart titles repeating the panel title, 3D charts, chart borders with rounded corners.
- Charts in random places and sizes. Every object sits on the 12-column grid.
- KPI tiles with no comparison: a number needs a delta or a target to mean anything.
- More than 6 KPIs *(warned)*, more than 6 series *(warned)*, pies with more than 5 slices *(warned)*, and dual axes.
- Hardcoded numbers where a formula belongs, and functions LibreOffice can't evaluate (XLOOKUP, FILTER, SORT, UNIQUE, SEQUENCE) *(error)*.
- Traffic-light conditional formatting on every cell. Use color for the one exception that matters.

### Motion
- Fade-and-slide on every section, hover effects on everything, and motion on page load with no purpose.
- `transition: all` *(lint)*; animating width, height, top or left; ease-in on entrances.
- No reduced-motion variant *(lint)*.
- Perpetual loops beside content, without pause controls.

## Part 2: QA checklist (one batched pass, then one confirmation pass)

Run the automated checks, look at the actual render, fix everything in one batch, and confirm once. Stop polishing after that.

### Automated
- [ ] `python3 scripts/vds.py lint page.html` reports **0 errors**. Every warning is fixed or recorded as deliberate.
- [ ] Word: `vds.py docx` succeeded, and the LibreOffice PDF render has been inspected page by page.
- [ ] Spreadsheets: `vds.py xlsx` printed no WARN lines, or they are recorded as deliberate.
- [ ] Decks: `python3 scripts/vds.py deck-check deck.html` reports 0 errors, `vds.py deck` reports "package verified", and `vds.py render deck.pptx` has been inspected slide by slide. Look for overflow first, then titles drifting between slides and chart labels colliding.

### Look at it: desktop (about 1,440px), phone (about 390px, true width), light and dark, and every printed page
- [ ] **First impression:** the signature element is obvious, and the page doesn't look like a template. Re-run the swap test on the result.
- [ ] **Hero:** the headline is at most 2–3 lines, the subtext at most 20 words, and the CTA is visible without scrolling; the visual is on-subject.
- [ ] **Rhythm:** at least four layout families on a long page, no repeated family back to back, and section spacing larger than the spacing inside sections.
- [ ] **Alignment:** edges line up to the grid, there are no orphaned floating elements, and gaps are consistent.
- [ ] **Type:** no widows in headlines, body text at 65ch or less, tabular numbers where figures compare, and no text overflowing or clipped. Check italic descenders.
- [ ] **Color:** one accent, used for one thing per view; muted text is readable; nothing sits on a busy image without a scrim.
- [ ] **Imagery:** every image matches the subject and shares one treatment; there's no fake UI made of divs.
- [ ] **Mobile:** single-column collapse, no horizontal scroll, 44px targets, and readable sizes.
- [ ] **Print** (documents): page breaks don't split tables or headings from their text, running footers are correct, and the cover has no footer.

### Decks
- [ ] One message per slide, with the title stating it. Every content slide has a visual element. Speaker notes are written for a live deck.
- [ ] The HTML preview and the PowerPoint render match, including stacking order and SVG artwork. Text widths may differ slightly where the font fit is only approximate.
- [ ] Press P in `deck.html` and step through: every build has a purpose from the motion plan, and Morph pairs visibly travel.
- [ ] Videos: the poster reads alone (check the `--no-motion` copy), loops start with the slide, and one-shots play on their click and hold the end frame.

### Markdown
- [ ] `vds.py lint doc.md` reports 0 errors: one H1 claim, no skipped levels, alt text on images, real link text, and table separator rows.
- [ ] It reads well in a plain-text viewer: tables have aligned number columns, and every chart has a table or sentence fallback.

### PDF
- [ ] `vds.py pdf` reports no underfilled last page and no empty pages. Every page has been inspected (`vds.py render file.pdf`).
- [ ] HTML-to-PDF used a browser engine. Without one, the document went through Word or the deck route.

### Spreadsheets
- [ ] `vds.py render out.xlsx` shows no formula errors (#NAME?, #REF!, #DIV/0!, #VALUE!), and the PDF of the dashboard has been inspected.
- [ ] The dashboard prints on one page wide, in landscape. Every chart and table aligns to the grid, with equal gutters.
- [ ] Changing a number on a data sheet updates the KPIs and charts, because everything is live.
- [ ] Number formats carry units, columns are wide enough that nothing shows `####`, and the header is frozen on data sheets.

### Interaction and motion
- [ ] Keyboard only: the tab order follows the layout, focus is always visible, and the skip link works.
- [ ] Hover, active, focus, disabled, empty, loading and error states all exist where they apply.
- [ ] Each motion has a named purpose. Entrances are quick and play once. Reduced motion has been tested (enable it in the OS).

### Content
- [ ] Every visible string has been re-read. There are no placeholders, no filler words, no em dashes, and no fake-precise numbers.
- [ ] One label per intent: the same CTA label in the navigation, the hero and the footer.
- [ ] Numbers carry units and sources, and charts have a source line.
- [ ] Fictional content is labelled as an example.
