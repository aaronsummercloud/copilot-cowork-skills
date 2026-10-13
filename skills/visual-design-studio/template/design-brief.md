<!-- TEMPLATE: design-brief.md (DESIGN.md). The single source of truth for one design system.
     Used by: visual-design-studio, step 2. Save it as {{project_path}}/outputs/design/DESIGN.md.
     Pages, the deck (template/deck.html) and Word documents (vds.py docx) all reuse its tokens.
     Replace every {{placeholder}}. Delete the sections for media you are not producing. -->
# Design system: {{project title}}

## 0. Design read
Reading this as: **{{medium}} in {{Persuade | Operate | Read | Experience}} mode** for **{{audience}}**, with a **{{vibe}}** language, leaning toward **{{aesthetic family or reference}}**.

| Dial | Value | Why |
|---|---|---|
| Variance | {{1-10}} | {{reason}} |
| Motion | {{1-10}} | {{reason}} |
| Density | {{1-10}} | {{reason}} |

## 1. Atmosphere
{{2–3 sentences in evocative but precise language. Name the subject's world: its materials, light and era. For example: "Night-time rail travel: deep blue dusk, sodium-lamp amber, confident grotesque type, calm and unhurried."}}

**Signature element:** {{the one memorable thing}}. **Motif:** {{a repeated device drawn from the subject}}.

## 2. Color roles
| Token | Hex (light) | Hex (dark) | Role | Contrast |
|---|---|---|---|---|
| --surface | {{#}} | {{#}} | Page background | |
| --surface-raised | {{#}} | {{#}} | Cards, panels | |
| --surface-sunken | {{#}} | {{#}} | Wells, alternating sections | |
| --ink | {{#}} | {{#}} | Primary text | {{n}}:1 on surface |
| --ink-muted | {{#}} | {{#}} | Secondary text | {{n}}:1 on surface |
| --line | {{#}} | {{#}} | Dividers | |
| --accent | {{#}} | {{#}} | The one accent | |
| --accent-ink | {{#}} | {{#}} | Text on the accent | {{n}}:1 on accent |

## 3. Typography
- **Display:** {{web font}}, with fallbacks {{…}}; Office mapping {{Office font}}. Weight {{…}}, tracking {{…}}.
- **Body:** {{web font}}, with fallbacks {{…}}; Office mapping {{Office font}}. Size {{…}}, leading {{…}}, measure {{60–70ch}}.
- **Scale:** {{the token steps used, and print sizes in pt}}.

### Office mapping (Word and PowerPoint render with the reader's installed fonts)
Copy these keys into the Word Markdown front matter, and use the fonts as the first family in deck.html's `:root` tokens.
```
font_display: {{Office font, e.g. Segoe UI Semibold}}
font_body: {{Office font, e.g. Cambria}}
ink: {{hex}}
ink_muted: {{hex}}
accent: {{hex}}
accent_ink: {{hex}}
surface_raised: {{hex}}
line: {{hex}}
```

## 4. Layout
- **Grid:** {{container width, columns, gutters}}. **Radius family:** {{sharp | soft | pill}} ({{values}}). **Spacing:** {{section and inner values}}.
- **Section plan** (at least 4 layout families, never the same family twice in a row):

| # | Section or page | Layout family | Visual element |
|---|---|---|---|
| 1 | {{hero / cover}} | {{asymmetric split}} | {{image prompt or illustration}} |

- **Mobile:** {{the collapse rule for each multi-column section}}.

### Deck story (presentations only; one message per slide)
- **Use:** {{live, ~N minutes | pre-read}}, about {{n}} slides. **Job:** {{decision | update | pitch | training}}.

| # | data-layout | Title (a claim, not a topic) | Visual element | Motion (purpose: transition / builds) |
|---|---|---|---|---|
| 1 | cover | {{…}} | {{motif or image}} | {{none, or delight: auto build}} |

## 5. Components
- **Buttons:** {{shape, fill, hover, active, focus}}. **Cards:** {{used only for…}}. **Inputs:** {{label above, error below}}.
- **States:** {{empty / loading / error / success treatment}}.

## 6. Imagery
- **Source:** {{Cowork image generation | inline illustration | supplied assets}}. **Treatment:** {{duotone, crop ratio, grain}}.
- **Prompts:** {{one per slot: subject, palette hexes, light, style, aspect ratio, "no text, no logos"}}

## 7. Motion
| Moment | Purpose | Recipe | Duration and curve |
|---|---|---|---|
| {{hero load}} | {{delight, once}} | {{orchestrated entrance}} | {{400–700ms, enter curve}} |

Reduced motion: {{what each item becomes}}.

## 8. Bans for this project
{{Pick from reference/quality.md (Part 1), plus any project-specific bans, e.g. "no stock photos of people pointing at screens".}}

## 9. Critique before building
- **Swap test:** {{which choices would have been the same for an unrelated brief, and what was changed instead}}
- **Defaults avoided:** {{…}}
- **Risks:** {{e.g. a font that may not load offline, so the fallback is chosen with care}}
