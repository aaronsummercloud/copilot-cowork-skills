# Deck contract: HTML slides that convert to native PowerPoint

The deck is one self-contained HTML file built with the same tokens as the rest of the project (DESIGN.md). Cowork shows it in the preview pane, and `scripts/vds.py deck` converts it into native, editable PowerPoint objects.

The converter reads the HTML directly. No browser lays it out, so **everything that affects the PowerPoint output must be written inline on the element**. CSS classes and the `<style>` block only affect the preview, with one exception: the `:root` tokens.

Start from `template/deck.html`. Run `scripts/vds.py deck-check` after every edit.

## Canvas
- Each slide is `<section class="slide" data-layout="…" style="background: var(--token)">`.
- The canvas is **960 × 540 px**, which equals 10 × 5.625 in (16:9). 96 px = 1 in, and 1 px = 0.75 pt.
- `data-layout` names the slide type (see `reference/layout-patterns.md (Presentations)`). The checker uses it to catch repeated layouts and text-only slides.
- Speaker notes go in `<aside class="notes">…</aside>` inside the section.

## Tokens
- Every color and font is defined once in `:root`, for example `--ink: #12343B;`.
- Elements use `var(--ink)`. Never write a raw hex value on an element, or the checker will flag palette drift.
- Font tokens list the Office font first, then preview fallbacks: `--font-body: Calibri, Carlito, 'Segoe UI', Arial, sans-serif;`. The converter uses only the first family.

## Elements
Every element is a **direct child of its slide section**, carries `data-pptx="<type>"`, and has inline `left`, `top`, `width` and `height` in px. **Document order is stacking order**, so put backgrounds first.

| `data-pptx` | Tag | Becomes in PowerPoint | Inline CSS used |
|---|---|---|---|
| `text` | `div` containing `p`, `h1`–`h6`, `ul`/`ol`/`li`, `b`, `strong`, `i`, `em`, `span`, `br` | Text box | Text properties (below) |
| `shape` | `div`, optionally with text | Rectangle, rounded rectangle (`border-radius: Npx`) or ellipse (`border-radius: 50%`) | `background`, `border: Npx solid var(--x)`, `border-radius`, `opacity`, plus text properties |
| `image` | `img` (`src` is a relative path or a `data:` URI for PNG, JPG, GIF or SVG) | Picture. SVG is embedded for PowerPoint 365, with a PNG fallback. | `object-fit: cover` (crops to fill the box) |
| `video` | `video` with `src` (H.264 `.mp4`), `poster` (PNG or JPG), `data-play` and `aria-label` (see Video) | Embedded video with its poster frame; `--no-motion` places the poster as a picture | None beyond geometry |
| `chart` | `div` with a `data-chart` JSON attribute | Native, editable chart | `font-family`, `font-size`, `color` (the axis and label ink) |
| `table` | `table` containing `tr`/`th`/`td`, plus an optional `colgroup` of `col style="width:…px"` | Native table | `font-*`, `color`, `border-bottom`; `background`, `color` and `font-weight` per cell; `height` per row |

**Text properties:** `font-family`, `font-size` (px), `font-weight` (700 = bold), `font-style`, `color`, `text-align`, `line-height` (unitless), `letter-spacing` (px), `text-transform: uppercase`, `padding` (px), and `margin-bottom`/`margin-top` on paragraphs (px).

**Vertical alignment:** `justify-content: center` (middle) or `justify-content: flex-end` (bottom). The template's frame CSS turns shapes into flex columns, so this works in the preview too.

**Roles:** `data-role` takes `title`, `subtitle`, `stat`, `caption`, `source` or `label`. It tells the checker how to judge the element. Titles are checked for position drift across slides. Captions and sources are allowed below 14pt.

## Motion attributes
These are optional. See `reference/motion.md (Slides)`.
- **On the slide section:** `data-transition` (`none`, `fade`, `push` or `morph`) and `data-transition-ms`.
- **On elements:** `data-build` (`0` = automatic, `1…n` = click), `data-anim` (`fade`, `float-up`, `wipe-up`, `wipe-right` or `appear`), `data-duration`, `data-delay`, and `data-morph="key"`.
- **On `<body>`:** `data-mode="live"` or `"pre-read"`.

The converter writes these as native PowerPoint transitions and entrance animations. The template's present mode (press **P**) plays them in the preview.

## Chart JSON
```json
{"type": "column", "categories": ["Q1","Q2","Q3"],
 "series": [{"name": "2025", "values": [12, 15, 19]}],
 "colors": ["var(--tide)"], "number_format": "0%", "labels": true, "legend": false,
 "gridlines": true, "gap_width": 60, "title": null, "source": "Finance, Sep 2026"}
```
- **`type`:** `column`, `stacked-column`, `bar`, `stacked-bar`, `line`, `pie` or `doughnut`.
- **`colors`:** one token per series, or one per slice for pie and doughnut charts.
- **`highlight`:** `"last"` or an index. On a single-series column or bar chart, that one point takes `highlight_color` (a token), and the rest keep the series color. This is the dataviz "grey everything, accent the subject" pattern. Don't fake it with stacked series.
- **Number format:** use Excel formats, for example `0%`, `#,##0` or `£#,##0.0,,"m"`.
- **One axis only.** Dual-axis charts are not supported (see `reference/typography-color.md (Charts)`).
- **Preview:** the template's preview script draws the chart as SVG in the HTML. The PowerPoint chart is built from the same JSON.

## Text fit
The checker estimates whether text overflows its box, using per-font glyph widths. When a real render shows an estimate is wrong (it's conservative for some fonts), mark the element `data-fit="verified" data-fit-reason="vds.py render: one line in the LibreOffice PNG"`. The error then becomes a recorded warning. Never mark it verified without a render.

## Images
SVG sources must carry `xmlns="http://www.w3.org/2000/svg"`. The converter adds it and warns if it's missing, because without it every renderer shows the file as plain XML.

## Video and low-poly 3D
PowerPoint can't run the page's canvas JavaScript, so a low-poly scene enters a deck as a rendered video, GIF or still frame. Make all three from the deck's own tokens with `vds.py lowpoly` (scenes: globe, turbine and cabinet loop; package and coin play once):
```bash
python3 scripts/vds.py lowpoly cabinet assets/cabinet --tokens deck.html --size 720x900       # cabinet.png + cabinet.mp4
python3 scripts/vds.py lowpoly coin assets/coin --tokens deck.html --size 480x480 --formats gif
```
- **Loops** (globe, turbine, cabinet) go in as video, because PowerPoint shows play and pause controls on a video:
  `<video data-pptx="video" src="assets/cabinet.mp4" poster="assets/cabinet.png" data-play="auto" loop muted playsinline aria-label="…" style="left:…">`. `data-play="auto"` starts it with the slide, and `loop` repeats it until the slide ends.
- **One-shots** (package, coin): a video with `data-play="click" data-build="n"` plays on that click and holds its last frame. Use the start frame as the poster (`--at 0 --formats png`), so the slide shows the closed box before the click. A short one-shot can instead be a GIF in an `img`; `vds.py lowpoly` writes GIFs that play once.
- **The poster carries the slide** in a PDF, a handout (`--no-motion`) and LibreOffice previews, so it must read on its own. Size the element to the video's aspect ratio, and use the slide's background as `--bg` (the default is `--surface`), so the video's edges disappear.
- **Checked:**
  - a missing file, poster or alt text, or an unknown `data-play` value (errors);
  - a video over 25 MB, or more than one video on a slide (warnings);
  - a GIF that loops forever (warning; use a GIF that plays once, or a video).

## Not supported (the checker reports an ERROR)
- Gradients, `box-shadow`, `transform`, `filter`, `clip-path`, blend modes, animations and transitions.
- Elements that aren't direct children of the slide, or that have no inline geometry.
- Named colors other than white, black and transparent; `hsl()`; and units other than px for geometry.
- Fonts that don't ship with Office (see `reference/typography-color.md`).

## Workarounds
- **Gradient background:** generate an image with Cowork's image generation and place it as a full-bleed `image` first in the slide.
- **Shadow:** use a tinted panel behind the card instead (`--mist` at an 8px offset), or leave it out.
- **Icons:** use simple single-color SVGs as `data:` URIs. The URL-encode `#` as `%23` inside the SVG.
- **Rounded image corners:** not supported. Put the image in a plain frame, or bake the rounding into the image.
