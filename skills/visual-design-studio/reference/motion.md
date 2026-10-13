# Motion for pages and UI

This draws on `ui-animation`, `animate`, `web-design-guidelines`, `taste-skill` and `hyperframes-animation`. Slide transitions and builds are covered in the Slides section below.

## The gate: should this move?
1. **Frequency:**

| How often it happens | Motion |
|---|---|
| 100+ times a day (shortcuts, palettes) | None, ever |
| Tens of times a day (hover, list navigation) | Near-imperceptible or none |
| Occasional (modals, drawers, toasts) | Standard |
| Rare (first visit, success, the hero) | This is where any delight goes |

2. **Purpose:** name it in one word, or don't animate: feedback, spatial continuity, state change, bridging a jarring change, explanation, or (rare moments only) delight.
3. **Function:** content people are reading or acting on doesn't move for style.

## Ingredients
- **Tool:** a CSS transition, then `@starting-style` for entry, then CSS keyframes for predetermined loops, then WAAPI (`el.animate`), then a library. Pages in Cowork are single files, so prefer CSS and WAAPI. Load GSAP from a CDN only if the page truly needs scroll choreography, and degrade gracefully if it doesn't load.
- **Properties:** `transform` and `opacity`; color and background only for state feedback. Never width, height, top or left, and never `transition: all` *(lint)*.
- **Curves:** enter `cubic-bezier(0.22, 1, 0.36, 1)`, move `cubic-bezier(0.25, 1, 0.5, 1)`, drawer `cubic-bezier(0.32, 0.72, 0, 1)`. Never `ease-in` on entrances. Springs (bounce 0.1–0.3) are for gestures and drag only.
- **Durations:**

| Element | Duration |
|---|---|
| Press feedback | 100–160ms |
| Tooltips | 125–200ms |
| Dropdowns | 150–250ms |
| Modals and drawers | 200–350ms |
| Page and section reveals | 400–700ms |
| Illustrative work | Up to 1,000ms |

  Routine UI stays under 300ms.
- **Scale:** start entrances from `scale(0.95–0.98)` and `opacity: 0`, never `scale(0)`. Set `transform-origin` to the trigger (modals are the exception and stay centered).
- **Stagger:** 30–80ms between items, most important first, with the whole group finishing under about 600ms. A container *or* its children enters, never both.
- **Interruption:** use transitions, which retarget, for anything triggered rapidly. Keyframes restart from zero.

## Page motion patterns (choose one or two per page)
| Pattern | Use | Rule |
|---|---|---|
| **One orchestrated entrance** | The hero on load | Headline, then subtext (+80ms), then the visual (+120ms), then the CTA (+160ms), once |
| **Reveal on scroll, once** | Two or three chosen sections on a marketing page | IntersectionObserver adds `.in` and is then removed; never re-animate on scroll-up. Never on product UI or above the fold. |
| **Drawn line** | Timelines, routes, progress | `transform: scaleX()` driven by `.in`, 1–1.6s with the enter curve |
| **Sticky stack or pin** | A real sequence | `position: sticky` and offset tops, with no JavaScript needed |
| **Hover lift and press** | Cards and buttons people click | Scale 1.02 or −2px y on hover, gated by `@media (hover: hover) and (pointer: fine)`; `scale(0.98)` on `:active` |
| **Number roll or pop-in** | A stat arriving | Once, 400–600ms, with tabular numbers |

## Required with every animation
- **Reduced motion:** under `@media (prefers-reduced-motion: reduce)`, travel becomes a fade or an instant change, and loops pause. Reduced means gentler, not nothing: keep opacity and color feedback *(lint)*.
- **Progressive enhancement:** content is visible without JavaScript. Add the hidden-before-reveal class from JavaScript (`.js .reveal`), so a failed script never hides content.
- **Loops longer than 5 seconds** next to content need a pause control. Pause loops when they're off-screen.
- **Check the result:** play it at 2–5× its duration or in DevTools' animation panel, and check the order and `transform-origin`.

## Low-poly 3D in plain JavaScript (`examples/motion-lowpoly.html`)
These are flat-shaded 3D objects drawn on a `<canvas>` with a renderer of about 200 lines and no libraries or CDN, so they work offline in Cowork's preview pane. The example contains a spinning globe, a package opening, a wind turbine and a coin flip.
- **When to use one:** for a single signature moment or an explanation. Use a globe for reach, a package for an order arriving, a turbine for what is being built, and a coin for a confirmed saving. Never more than one per screen, and never as decoration on product UI.
- **Loops vs one-shots:**
  - Ambient loops (the globe, the turbine) are slow (a 20–30 s rotation) and have a visible Pause/Play button, because loops longer than 5 seconds need one.
  - One-shots (the package, the coin) play when the user clicks, end in a meaningful still state, and stop. Timing is 1–2 s with an ease-out curve and no bounce.
- **Required behaviour:**
  - Reduced motion shows the end state as a still frame.
  - Animation pauses off screen (IntersectionObserver).
  - The canvas is scaled for `devicePixelRatio`, capped at 2.
  - Colours are read from CSS tokens, so dark mode works.
  - Each canvas has `role="img"` and an `aria-label` describing the object and its motion.
- **Engine limits:**
  - It sorts whole faces back to front (the painter's algorithm), so keep objects convex or simply nested, as in the examples.
  - Aim for under about 400 faces per scene to keep 60 fps on laptops.
  - For anything bigger (terrain, many objects, textures), a WebGL library is the right tool, but it needs a CDN, so give it a static fallback image.
- **Reuse:** copy the engine block and one scene function, set the colour tokens from DESIGN.md, and set the framing (`radius`, `fill`) so the object fits its canvas.
- **QA:** open the page with `#demo` to freeze every scene at a representative frame for screenshots. Check it in light and dark themes, and with reduced motion on.
- **In decks and documents:** `scripts/vds.py lowpoly` renders the same scenes in Python (Pillow, plus ffmpeg for MP4), with colours from the deck's or page's tokens. It writes a poster PNG, a seamless-loop or play-once MP4, and a play-once GIF. The deck rules are in `reference/deck-contract.md` (Video and low-poly 3D): loops go in as video with PowerPoint's own controls, one-shots play on a click, and the poster stands in for print. Word and PDF take the poster PNG.
- **New scenes** need adding in both places: a scene function in `examples/motion-lowpoly.html` and its port in `scripts/vds_lowpoly.py`, with the same numbers.

## Slides (native PowerPoint, previewed with P in deck.html)
The gate for slides is a purpose (explanation, continuity, emphasis or pacing) or delight on the cover or closing slide only. A pre-read deck (`<body data-mode="pre-read">`) has no builds *(checked)*.

| Attribute | Values | Rule |
|---|---|---|
| `data-transition` (slide) | `none`, `fade`, `push`, `morph` | One style per deck. Morph only where an object persists. Push only for a left-to-right sequence. 150–1000ms *(checked)*. |
| `data-build` (element) | `0` = automatic after the slide arrives; `1…n` = click | Automatic only on cover, section and closing slides. At most 5 clicks. Never hide the title *(checked)*. |
| `data-anim` | `fade`, `float-up`, `wipe-up`, `wipe-right`, `appear` | Wipe charts in the direction they're read. No spins, bounces or fly-ins. |
| `data-duration` and `data-delay` | 300–500ms; 60ms default stagger | A group finishes within about 1s. A card and its text enter together *(checked)*. |
| `data-play` (video) | `auto` (starts with the slide) or `click` (with `data-build="n"`) | One moving object per slide. Loops only where the slide is about the object. *(checked)* |
| `data-morph="key"` | The same key on adjacent slides | Morph moves and resizes that object (PowerPoint 2019 and later; older versions fall back to Fade) |

The converter writes native transitions and timing XML, with entrances that decelerate. The template's present mode plays the same motion, with the same curves, and respects reduced motion. Every slide's final state must read completely, as it will in a PDF.

There's a working example in `examples/landing-night-train.html` (one entrance, reveal once, a drawn route line, a sticky stack and press feedback).
