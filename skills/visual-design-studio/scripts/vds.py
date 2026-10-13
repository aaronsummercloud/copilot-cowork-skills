#!/usr/bin/env python3
"""visual-design-studio command line: one entry point for every script in the skill.

Usage: python3 scripts/vds.py <command> [args]

  lint <page.html | doc.md>            design + accessibility lint (ERROR/WARN; exit 1 on errors)
  chart <chart.json> <out.svg|out.png> token-styled chart from data (SVG for HTML/PDF, PNG for Word)
  pdf <page.html> <out.pdf>            print an A4 HTML document to PDF, then check page fill
  render <file> [outdir]               QA render of .pptx/.docx/.xlsx/.html/.pdf (text check, PDF, PNGs)
  deck-check <deck.html>               check a deck against reference/deck-contract.md
  deck <deck.html> <out.pptx> [--force] [--no-motion]   convert to native PowerPoint
  docx <content.md> <out.docx> [--theme theme.json]     build a designed Word document
  xlsx <spec.json> <out.xlsx>          build a live Excel dashboard
  lowpoly <scene> <out-base> [--formats png,mp4,gif] [--tokens deck.html] [--bg #hex]
                                       low-poly 3D scene as poster PNG, MP4 and GIF (for decks)

Standard library only, except: deck (python-pptx), docx (python-docx), xlsx (openpyxl),
chart PNG and lowpoly (Pillow), lowpoly MP4 (ffmpeg). All are preinstalled in Copilot Cowork.
"""
import base64
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# Lint: HTML pages and Markdown
# ============================================================================
FILLER = ["elevate", "seamless", "unleash", "next-gen", "revolutioniz", "delve", "tapestry", "game-changer",
          "leverage", "harness the power", "unlock the power", "synergy", "cutting-edge", "world-class",
          "in today's fast-paced", "supercharge", "empower", "effortless"]
PLACEHOLDER_NAMES = ["john doe", "jane doe", "acme", "lorem ipsum", "nexus", "smartflow", "your company",
                     "company name", "user name"]
SCROLL_CUES = ["scroll to explore", "scroll down", "scroll to discover", "swipe down"]
CREAM = {"F4F1EA", "F5F1EA", "F7F5F1", "FBF8F1", "EFEAE0", "ECE6DB", "FAF7F1", "E8DFCB", "F5F5DC", "FAF0E6", "FFF8E1"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP_TEXT = {"script", "style", "svg", "noscript", "template"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.tags, self.css, self.text = [], [], [], []
        self.headings, self.sections, self.html_attrs = [], 0, {}
        self._style = False
        self.svg_hex = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self.tags.append((tag, a, line, tuple(self.stack)))
        if tag == "html":
            self.html_attrs = a
        if tag == "style":
            self._style = True
        if tag in ("section", "article") or (tag == "header" and "nav" not in (a.get("class") or "")):
            self.sections += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((int(tag[1]), line))
        if a.get("style"):
            self.css.append(("inline", a["style"], line, tuple(self.stack + [tag])))
        if tag == "svg" or "svg" in self.stack:
            self.svg_hex += sum(1 for k in ("fill", "stroke", "stop-color") if re.fullmatch(r"#[0-9a-fA-F]{3,6}", a.get(k) or ""))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._style:
            self.css.append(("block", data, self.getpos()[0], ()))
        elif not (set(self.stack) & SKIP_TEXT) and data.strip():
            self.text.append((data, self.getpos()[0]))


def hex6(value):
    v = value.strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", v):
        v = "".join(c * 2 for c in v)
    return v.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", v) else None


def luminance(h):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hue_sat(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0, 0
    d = mx - mn
    sat = d / (1 - abs(mx + mn - 1)) if (mx + mn) not in (0, 2) else 0
    if mx == r:
        hue = 60 * (((g - b) / d) % 6)
    elif mx == g:
        hue = 60 * ((b - r) / d + 2)
    else:
        hue = 60 * ((r - g) / d + 4)
    return hue, sat


def token_blocks(css):
    """{scope: {name: hex}} for :root blocks; scope 'light' or 'dark' (inside a dark media query/theme)."""
    scopes = {"light": {}, "dark": {}}
    for m in re.finditer(r"(@media[^{]*prefers-color-scheme:\s*dark[^{]*\{)?\s*(:root[^{]*)\{([^}]*)\}", css):
        scope = "dark" if (m.group(1) or "dark" in m.group(2)) else "light"
        for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+)(?:;|$)", m.group(3).strip()):
            h = hex6(value) if value.strip().startswith("#") else None
            if h:
                scopes[scope][name] = h
    return scopes


def lint_markdown(path):
    """Markdown deliverables: structure, copy tells, tables, images, Mermaid fallbacks."""
    errors, warns = [], []
    lines = open(path, encoding="utf-8").read().split("\n")
    in_fence, fence_lang, mermaid_ends, headings, prose = False, "", [], [], []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence, fence_lang = True, stripped[3:].strip().lower()
            else:
                in_fence = False
                if fence_lang == "mermaid":
                    mermaid_ends.append(i)
            continue
        if in_fence:
            continue
        heading = re.match(r"(#{1,6})\s+(.*)", line)
        if heading:
            headings.append((len(heading.group(1)), heading.group(2), i))
        elif stripped and not stripped.startswith(("|", "<", "---")):
            prose.append((line, i))
        for alt, _ in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            if not alt.strip():
                errors.append(f"line {i}: image without alt text")
        vague = re.search(r"\[(click here|here|link|this)\]\(", line, re.I)
        if vague:
            warns.append(f"line {i}: link text '{vague.group(1)}' doesn't say where it goes")
        if re.search(r"(?<![(<\[])https?://\S+", re.sub(r"\]\([^)]*\)", "]", line)):
            warns.append(f"line {i}: bare URL; give it link text")
    is_docx_source = lines and lines[0].strip() == "---" and any(l.startswith("title:") for l in lines[:20])
    if len([h for h in headings if h[0] == 1]) != 1 and not is_docx_source:  # docx sources use H1 per chapter
        warns.append("use exactly one H1, written as the claim")
    for (a, _, _), (b, _, line) in zip(headings, headings[1:]):
        if b > a + 1:
            warns.append(f"line {line}: heading level jumps from H{a} to H{b}")
    for _, title, line in headings:
        if title.rstrip().endswith("."):
            warns.append(f"line {line}: heading ends with a period")
    for end in mermaid_ends:
        after = " ".join(l for l in lines[end:end + 4] if l.strip())
        if not re.search(r"\d", after) and "|" not in after:
            warns.append(f"line {end}: Mermaid chart without a fallback; many viewers show the code, so follow it "
                         "with a table or a sentence carrying the numbers (or use a vds.py chart image)")
    text = " ".join(l for l, _ in prose)
    low = text.lower()
    if "—" in text:
        warns.append("em dash in copy: the most common AI-writing tell")
    for word in FILLER:
        if re.search(r"\b" + re.escape(word), low):
            warns.append(f"filler word '{word}'")
    for name in PLACEHOLDER_NAMES:
        if name in low:
            (errors if "lorem" in name else warns).append(f"placeholder content '{name}'")
    for l, i in prose:
        if len([w for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", l) if w.isupper()]) >= 2:
            warns.append(f"line {i}: ALL-CAPS text; write sentence case")
    if re.search(r"\{\{|\}\}|\bTODO\b", text):
        errors.append("unfilled template placeholder or TODO")
    table_rows = [l.strip() for l in lines if l.strip().startswith("|")]
    if table_rows and not any(re.fullmatch(r"\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{0,}:?\s*\|?", r) for r in table_rows):
        errors.append("table without a |---| separator row: it won't render as a table")
    return errors, warns


def lint(path):
    if path.lower().endswith((".md", ".markdown")):
        return lint_markdown(path)
    errors, warns = [], []
    src = open(path, encoding="utf-8").read()
    page = Page()
    page.feed(src)
    css_all = "\n".join(c for _, c, _, _ in page.css)
    blocks = "\n".join(c for kind, c, _, _ in page.css if kind == "block")
    text = " ".join(t for t, _ in page.text)
    low = text.lower()

    def E(msg, line=None):
        errors.append(f"line {line}: {msg}" if line else msg)

    def W(msg, line=None):
        warns.append(f"line {line}: {msg}" if line else msg)

    # ---------------- document basics
    if not any(t == "meta" and a.get("name") == "viewport" for t, a, _, _ in page.tags):
        E("missing <meta name=viewport>; the page won't scale on phones")
    if re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b", src):
        E("zoom is disabled (user-scalable=no / maximum-scale=1)")
    if not page.html_attrs.get("lang"):
        E("<html> has no lang attribute")
    if not any(t == "title" for t, _, _, _ in page.tags):
        E("missing <title>")
    h1s = [h for h in page.headings if h[0] == 1]
    if len(h1s) != 1:
        W(f"{len(h1s)} <h1> elements; use exactly one")
    for (prev, _), (cur, line) in zip(page.headings, page.headings[1:]):
        if cur > prev + 1:
            W(f"heading level jumps from h{prev} to h{cur}", line)

    # ---------------- elements
    for tag, a, line, stack in page.tags:
        if tag == "img":
            if "alt" not in a:
                E("<img> without alt (use alt=\"\" if decorative)", line)
            if not (a.get("width") and a.get("height")) and "svg" not in stack:
                W("<img> without width/height causes layout shift", line)
        if tag in ("div", "span") and any(k.startswith("on") for k in a):
            E(f"<{tag}> with a click handler; use <button> or <a>", line)
        if tag == "a" and a.get("href") in (None, "", "#") and not a.get("aria-label") and "role" not in a:
            pass  # in-page placeholders are common in prototypes; not flagged
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button"):
            if not (a.get("aria-label") or a.get("id") or a.get("aria-labelledby")):
                E(f"<{tag}> has no label", line)
            if "placeholder" in a and not (a.get("id") or a.get("aria-label")):
                W("placeholder used as the only label", line)

    # ---------------- CSS rules
    if re.search(r"transition\s*:\s*all\b", css_all):
        E("transition: all; list the exact properties")
    if re.search(r"outline\s*:\s*(none|0)\b", css_all) and ":focus-visible" not in css_all:
        E("outline removed without a :focus-visible replacement")
    animates = re.search(r"\b(transition|animation)\s*:", css_all) or "element.animate" in src or ".animate(" in src
    if animates and "prefers-reduced-motion" not in src:
        E("motion without a prefers-reduced-motion fallback")
    if re.search(r"cursor\s*:\s*url\(", css_all):
        W("custom cursor; dated and hostile to accessibility")
    if re.search(r"(?<![\w-])(height|min-height)\s*:\s*100vh", css_all):
        W("100vh jumps on mobile Safari; use 100dvh / min-height: 100dvh")
    if re.search(r"background-clip\s*:\s*text", css_all):
        W("gradient text on headings is a generic AI tell")
    for selector, _ in re.findall(r"([^{}]+)\{([^{}]*grid-template-columns\s*:\s*repeat\(\s*3\s*,\s*(?:1fr|minmax\([^)]*1fr\))\s*\)[^{}]*)\}", css_all):
        if not re.search(r"\bol\b|step|process|timeline|sequence", selector):
            W(f"three equal columns ({selector.strip()[:40]}): the 'three identical feature cards' row is a top AI tell; "
              "use an asymmetric split or bento (a real sequence in an <ol> is fine)")
            break
    radii = {r for r in re.findall(r"border-radius\s*:\s*([\d.]+(?:px|rem))", css_all)}
    if len(radii) > 4:
        W(f"{len(radii)} different border-radius values; lock one radius family (use --radius tokens)")
    eyebrows = len(re.findall(r"text-transform\s*:\s*uppercase[^}]*letter-spacing|letter-spacing[^}]*text-transform\s*:\s*uppercase", blocks))
    allowed = max(1, math.ceil(max(page.sections, 1) / 3))
    if eyebrows > allowed:
        W(f"{eyebrows} uppercase tracked label styles for {page.sections} sections; max {allowed} eyebrow(s) (1 per 3 sections)")
    for grad in re.findall(r"linear-gradient\(([^;]+)\)", css_all):
        hues = [hue_sat(h) for h in (hex6(x) for x in re.findall(r"#[0-9a-fA-F]{3,6}\b", grad)) if h]
        if sum(1 for hue, sat in hues if 250 <= hue <= 300 and sat > 0.45) >= 1 and len(hues) >= 2:
            W("purple/violet gradient: the default 'AI gradient' look; pick a palette from the subject")
            break

    # ---------------- fonts
    fams = [f.split(",")[0].strip().strip("'\"") for f in re.findall(r"--font-[\w-]+\s*:\s*([^;]+);", blocks)]
    fams += [f.split(",")[0].strip().strip("'\"") for f in re.findall(r"font-family\s*:\s*([^;}{]+)", css_all) if "var(" not in f]
    if any(f.lower() == "inter" for f in fams):
        W("Inter as a primary family is the default AI choice; pick a face with character (or justify it)")
    if fams and all(f.lower() in ("system-ui", "-apple-system", "arial", "helvetica", "sans-serif", "roboto") for f in fams):
        W("only system/default fonts; typography carries the personality, so choose a family deliberately")

    # ---------------- color system
    scopes = token_blocks(blocks)
    tokens = scopes["light"]
    if not tokens:
        W("no :root color tokens; define the palette once as custom properties")
    for scope, toks in scopes.items():
        for fg, bg, need in (("ink", "surface", 7.0), ("ink-muted", "surface", 4.5), ("ink", "surface-raised", 4.5),
                             ("ink-muted", "surface-raised", 4.5), ("accent-ink", "accent", 4.5)):
            if fg in toks and bg in toks:
                ratio = contrast(toks[fg], toks[bg])
                if ratio < need:
                    (E if need == 4.5 or ratio < 4.5 else W)(
                        f"[{scope}] --{fg} on --{bg} is {ratio:.2f}:1, needs {need}:1")
        for name, h in toks.items():
            if h == "000000":
                W(f"[{scope}] --{name} is pure #000; use a tinted off-black")
            if name in ("surface", "bg", "background", "paper") and h in CREAM:
                W(f"[{scope}] --{name} #{h} is the generic cream default; choose a background from the subject")
    raw = []
    for kind, css, line, stack in page.css:
        if "svg" in stack:
            continue
        body = re.sub(r":root[^{]*\{[^}]*\}", "", css) if kind == "block" else css
        body = re.sub(r"@media[^{]*prefers-color-scheme[^{]*\{\s*:root[^{]*\{[^}]*\}\s*\}", "", body)
        raw += [(h, line) for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", body)]
    if len(raw) > 2:
        W(f"{len(raw)} raw hex colors outside :root tokens (e.g. {raw[0][0]} near line {raw[0][1]}); use var(--token)")

    # ---------------- print documents
    if "@page" in css_all:
        for q in re.findall(r"@media\s*\(\s*max-width[^)]*\)", css_all):
            W(f"print document has '{q.strip()}' without 'screen and': A4 prints at about 794px, so phone rules "
              "would apply to the PDF and reflow the sheets")
            break

    # ---------------- inline SVG and SVG images
    if scopes["dark"] and page.svg_hex:
        W(f"{page.svg_hex} fixed hex colors inside inline SVG while the page has a dark theme; "
          "use style=\"fill:var(--token)\" so charts follow the theme (vds.py chart does this)")
    if "<svg" in src and not re.search(r"(^|[\s,}])svg[^{]*\{[^}]*max-width", css_all):
        W("inline SVG without an svg { max-width: 100%; height: auto } guard; wide charts overflow phones")
    for tag, a, line, _ in page.tags:
        src_attr = a.get("src") or ""
        if tag == "img" and ("image/svg+xml" in src_attr or src_attr.lower().endswith(".svg")):
            payload = src_attr
            if src_attr.startswith("data:"):
                head, _, data = src_attr.partition(",")
                payload = base64.b64decode(data).decode("utf-8", "replace") if ";base64" in head else urllib.parse.unquote(data)
            else:
                try:
                    payload = open(os.path.join(os.path.dirname(os.path.abspath(path)), src_attr), encoding="utf-8").read()
                except OSError:
                    payload = "xmlns"  # missing files are reported elsewhere
            if "xmlns" not in payload[:400]:
                E("SVG image without xmlns=\"http://www.w3.org/2000/svg\": browsers and PowerPoint treat it as plain XML", line)

    # ---------------- copy
    for t, line in page.text:
        caps = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", t) if w.isupper()]
        if len(caps) >= 2:
            W(f"literal ALL-CAPS text '{t.strip()[:40]}': a generic AI tell; write sentence case", line)
            break
    if "—" in text:
        W("em dash in visible copy: the most common AI-writing tell; use a period, comma or colon")
    if "..." in text:
        W("'...' should be the ellipsis character '…'")
    for word in FILLER:
        if re.search(r"\b" + re.escape(word), low):
            W(f"filler word '{word}'; say the specific thing")
    for name in PLACEHOLDER_NAMES:
        if name in low:
            (E if "lorem" in name else W)(f"placeholder content '{name}'")
    for cue in SCROLL_CUES:
        if cue in low:
            W(f"scroll cue '{cue}': visitors know how to scroll")
    if any(re.fullmatch(r"(section|step|stage|phase|part)\s*0?\d+\s*[:.]?", t.strip().lower()) for t, _ in page.text):
        W("generic numbered labels (Section 01, Step 1); let the content name itself")
    if re.search(r"\{\{|\}\}|\bTODO\b", text):
        E("unfilled template placeholder or TODO in visible text")
    return errors, warns


def main_lint():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    errors, warns = lint(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps({"errors": errors, "warnings": warns}, indent=2))
    else:
        for e in errors:
            print("ERROR", e)
        for w in warns:
            print("WARN ", w)
        print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)



# ============================================================================
# Render: QA previews of every output format
# ============================================================================
PLACEHOLDER = re.compile(r"lorem|ipsum|\bTODO\b|\{\{|\}\}|\bx{3,}\b|\[insert|placeholder", re.I)


def text_qa(path):
    """Print text per slide (pptx) or per heading block (docx) and flag placeholders."""
    problems, blocks = [], []
    if path.endswith(".pptx"):
        from pptx import Presentation
        for number, slide in enumerate(Presentation(path).slides, 1):
            texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
            blocks.append((f"slide {number}", texts))
    elif path.endswith(".docx"):
        from docx import Document
        current = ("start", [])
        for para in Document(path).paragraphs:
            if para.style.name.startswith("Heading"):
                blocks.append(current)
                current = (para.text[:40], [])
            elif para.text.strip():
                current[1].append(para.text)
        blocks.append(current)
    elif path.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(path)
        for ws in wb.worksheets:
            values = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
            formulas = sum(1 for v in values if v.startswith("="))
            texts = [v for v in values if not v.startswith("=")]
            blocks.append((f"sheet {ws.title} ({formulas} formulas, {len(ws._charts)} charts)", texts))
    for label, texts in blocks:
        if texts:
            print(f"--- {label}: " + " | ".join(t.replace("\n", " / ")[:80] for t in texts[:6]))
        for t in texts:
            if PLACEHOLDER.search(t):
                problems.append(f"{label}: placeholder text: {t[:60]!r}")
    return problems


def render(src_path, outdir):
    if src_path.endswith(".pdf"):
        os.makedirs(outdir, exist_ok=True)
        pdf = os.path.join(outdir, os.path.basename(src_path))
        if os.path.abspath(pdf) != os.path.abspath(src_path):
            shutil.copyfile(src_path, pdf)
        return pdf, _rasterize(pdf, outdir)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice not available: skipping visual render.")
        return None, []
    os.makedirs(outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf",
                        "--outdir", outdir, src_path], capture_output=True, timeout=300)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(src_path))[0] + ".pdf")
    if not os.path.exists(pdf):
        print("PDF conversion failed.")
        return None, []
    return pdf, _rasterize(pdf, outdir)


def _rasterize(pdf, outdir):
    pngs = []
    if shutil.which("pdftoppm"):
        prefix = os.path.join(outdir, "slide")
        for old in glob.glob(prefix + "-*.png"):
            os.remove(old)
        subprocess.run(["pdftoppm", "-png", "-r", "110", pdf, prefix], capture_output=True, timeout=300)
        pngs = sorted(glob.glob(prefix + "-*.png"))
    return pngs


EXCEL_ERRORS = re.compile(r"#(NAME\?|REF!|DIV/0!|VALUE!|N/A|NUM!|NULL!|SPILL!)")


def excel_errors(pdf):
    """Scan the computed PDF for Excel error values (needs pdftotext from poppler)."""
    if not shutil.which("pdftotext"):
        return ["pdftotext not available: inspect the PDF for #NAME?/#REF! errors by eye"]
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    found = sorted(set(EXCEL_ERRORS.findall(text)))
    return [f"formula errors in the computed workbook: {', '.join('#' + f for f in found)}"] if found else []


def contact_sheet(pngs, out_path, cols=3):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    thumbs = [Image.open(p).convert("RGB") for p in pngs]
    tw = 480
    th = int(thumbs[0].height * tw / thumbs[0].width)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 40) + 16), "#9AA0A6")
    draw = ImageDraw.Draw(sheet)
    for i, img in enumerate(thumbs):
        x, y = 16 + (i % cols) * (tw + 16), 16 + (i // cols) * (th + 40)
        sheet.paste(img.resize((tw, th)), (x, y + 22))
        draw.text((x, y + 4), f"Page {i + 1}", fill="#000000")
    sheet.save(out_path)
    return out_path


def main_render():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    src_path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(src_path)), "preview")
    problems = text_qa(src_path)
    pdf, pngs = render(src_path, outdir)
    if pdf:
        print(f"PDF preview: {pdf}")
    if pngs:
        sheet = contact_sheet(pngs, os.path.join(outdir, "contact-sheet.png"))
        print(f"{len(pngs)} page images in {outdir}" + (f"; contact sheet: {sheet}" if sheet else ""))
    elif pdf:
        print("pdftoppm not available: open the PDF preview to inspect each slide.")
    if pdf and src_path.endswith(".xlsx"):
        problems += excel_errors(pdf)
    for p in problems:
        print("WARN", p)
    sys.exit(1 if problems else 0)



# ============================================================================
# Chart: one data spec -> token-styled SVG (HTML/PDF) or PNG (Word)
# ============================================================================
CHART_DEFAULTS = {"ink": "#1E2327", "ink_muted": "#55606B", "line": "#D3DAE1", "accent": "#2F51A3",
                  "neutral": "#B9C3CC", "series2": "#5F948A", "surface": "#FFFFFF",
                  "font": "system-ui, 'Segoe UI', sans-serif"}
CHART_TOKENS = {"ink": "--ink", "ink_muted": "--ink-muted", "line": "--line", "accent": "--accent",
                "neutral": "--chart-neutral", "series2": "--chart-2", "surface": "--surface"}


def fmt_number(value, pattern):
    """Format a number with a small Excel-like pattern: 0, 0.0, #,##0, 0%, €#,##0, #,##0" L"."""
    if value is None:
        return ""
    pattern = pattern or "0"
    m = re.match(r'^([^#0]*)([#0,]*0(?:\.0+)?)(%?)(.*)$', pattern)
    if not m:
        return str(value)
    prefix, core, pct, suffix = m.groups()
    signed = prefix.startswith("+")  # "+0%": the sign comes from the value (+17%, −8%, 0%)
    prefix = prefix.lstrip("+")
    decimals = len(core.split(".")[1]) if "." in core else 0
    v = value * 100 if pct else value
    text = f"{abs(v):,.{decimals}f}" if "," in core else f"{abs(v):.{decimals}f}"
    nonzero = float(text.replace(",", "")) != 0
    sign = "−" if v < 0 and nonzero else ("+" if signed and v > 0 and nonzero else "")
    return sign + prefix.replace('"', "") + text + pct + suffix.replace('"', "")


def chart_svg(spec):
    """Column, bar or line chart as SVG; colors are CSS variables with hex fallbacks."""
    theme = dict(CHART_DEFAULTS, **spec.get("theme", {}))
    col = lambda role: f"var({CHART_TOKENS[role]}, {theme[role]})"
    kind = spec.get("type", "column")
    cats, series = spec["categories"], spec["series"]
    w, h = spec.get("width", 720), spec.get("height", 320)
    fs = spec.get("font_size", 13)
    fmt = spec.get("format", "0")
    n = len(cats)
    highlight = spec.get("highlight")
    if highlight == "last":
        highlight = n - 1
    vals = [v for s in series for v in s["values"] if v is not None]
    vmax = spec.get("max") or max(vals) * (1.12 if spec.get("labels", True) else 1.05)
    vmin = min(0, min(vals))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="{spec.get("aria", spec.get("title", "Chart"))}" font-family="{theme["font"]}" font-size="{fs}">']
    label_style = f'style="fill:{col("ink_muted")}"'
    strong_style = f'style="fill:{col("ink")}" font-weight="600"'
    halo = f'paint-order="stroke" style="stroke:{col("surface")};stroke-width:4px;fill:{col("ink")}"'
    if kind in ("column", "line"):
        pad_l, pad_r, pad_t, pad_b = (8 if spec.get("labels", True) and kind == "column" else 44), 12, 24, fs * 2.2
        pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
        y = lambda v: pad_t + ph * (1 - (v - vmin) / (vmax - vmin))
        band = pw / n
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y(0):.1f}" y2="{y(0):.1f}" style="stroke:{col("line")}"/>')
        if kind == "line" or not spec.get("labels", True):
            for k in range(1, 5):
                gv = vmin + (vmax - vmin) * k / 4
                out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y(gv):.1f}" y2="{y(gv):.1f}" style="stroke:{col("line")}" stroke-dasharray="2 3"/>')
                out.append(f'<text x="{pad_l - 6}" y="{y(gv) + 4:.1f}" text-anchor="end" {label_style}>{fmt_number(gv, fmt)}</text>')
        if spec.get("reference"):
            ry = y(spec["reference"]["value"])
            out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{ry:.1f}" y2="{ry:.1f}" style="stroke:{col("ink")}" stroke-dasharray="4 4"/>')
        for i, c in enumerate(cats):
            weight = strong_style if i == highlight else label_style
            out.append(f'<text x="{pad_l + band * (i + 0.5):.1f}" y="{h - fs * 0.6:.1f}" text-anchor="middle" {weight}>{c}</text>')
        if kind == "column":
            inner = band * 0.66
            bw = inner / len(series)
            for si, s in enumerate(series):
                for i, v in enumerate(s["values"]):
                    if v is None:
                        continue
                    if len(series) == 1:
                        role = "accent" if highlight is None or i == highlight else "neutral"
                    else:
                        role = ("neutral", "accent", "series2", "ink_muted")[si % 4]
                    x = pad_l + band * i + (band - inner) / 2 + bw * si
                    top = y(max(v, 0))
                    out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw - 2:.1f}" height="{abs(y(v) - y(0)):.1f}" rx="2" style="fill:{col(role)}"/>')
                    if spec.get("labels", True):
                        ly = top - 6
                        if spec.get("reference"):  # keep the label off the reference line
                            ry = y(spec["reference"]["value"])
                            if ry - 4 < ly < ry + fs + 2:
                                ly = ry - 5
                        ink = col("ink") if i == highlight else col("ink_muted")
                        weight = ' font-weight="600"' if i == highlight else ""
                        out.append(f'<text x="{x + (bw - 2) / 2:.1f}" y="{ly:.1f}" text-anchor="middle" paint-order="stroke" '
                                   f'style="stroke:{col("surface")};stroke-width:4px;fill:{ink}"{weight}>{fmt_number(v, fmt)}</text>')
        else:
            for si, s in enumerate(series):
                role = ("accent", "neutral", "series2", "ink_muted")[si % 4] if len(series) > 1 else "accent"
                pts = [(pad_l + band * (i + 0.5), y(v)) for i, v in enumerate(s["values"]) if v is not None]
                out.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="none" '
                           f'style="stroke:{col(role)}" stroke-width="2.5" stroke-linejoin="round"/>')
                lx, ly = pts[-1]
                out.append(f'<text x="{lx - 4:.1f}" y="{ly - 10:.1f}" text-anchor="end" {halo} font-weight="600">{s.get("name", "")}</text>')
            if highlight is not None:
                v = series[0]["values"][highlight]
                cx = pad_l + band * (highlight + 0.5)
                out.append(f'<circle cx="{cx:.1f}" cy="{y(v):.1f}" r="5" style="fill:{col("accent")}"/>')
                out.append(f'<text x="{cx:.1f}" y="{y(v) - 12:.1f}" text-anchor="middle" {halo}>{fmt_number(v, fmt)}</text>')
        ref = spec.get("reference")
        if ref:
            ry = y(ref["value"])
            out.append(f'<text x="{w - pad_r}" y="{ry - 6:.1f}" text-anchor="end" {halo} font-weight="600">{ref.get("label", "")}</text>')
    elif kind == "bar":
        label_w = spec.get("label_width", 120)
        pad_t, pad_r = 8, 64
        vmax = max(vals) * 1.05 if max(vals) > 0 else 0
        vmin = min(0, min(vals)) * 1.05
        plot_l = label_w + (fs * 4 if vmin < 0 else 0)  # room for negative value labels
        row = (h - pad_t) / n
        x = lambda v: plot_l + (w - plot_l - pad_r) * (v - vmin) / (vmax - vmin)
        for i, c in enumerate(cats):
            v = series[0]["values"][i]
            yy = pad_t + row * i
            role = "accent" if i == highlight or highlight is None else "neutral"
            sty = strong_style if i == highlight else label_style
            out.append(f'<text x="{label_w - 10}" y="{yy + row / 2 + 4:.1f}" text-anchor="end" {sty}>{c}</text>')
            x0, xv = x(0), x(v)
            out.append(f'<rect x="{min(x0, xv):.1f}" y="{yy + row * 0.18:.1f}" width="{abs(xv - x0):.1f}" height="{row * 0.64:.1f}" rx="2" style="fill:{col(role)}"/>')
            anchor, lx = ("start", xv + 6) if v >= 0 else ("end", xv - 6)
            out.append(f'<text x="{lx:.1f}" y="{yy + row / 2 + 4:.1f}" text-anchor="{anchor}" {sty}>{fmt_number(v, fmt)}</text>')
        if vmin < 0:
            out.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{pad_t}" y2="{h}" style="stroke:{col("line")}"/>')
    else:
        raise ValueError(f"chart type '{kind}' not supported (column, bar, line)")
    out.append("</svg>")
    return "\n".join(out)


def chart_png(spec, out_path):
    """The same chart as a PNG via matplotlib, for Word and other raster destinations."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    theme = dict(CHART_DEFAULTS, **spec.get("theme", {}))
    kind = spec.get("type", "column")
    cats, series = spec["categories"], spec["series"]
    fmt = spec.get("format", "0")
    highlight = spec.get("highlight")
    if highlight == "last":
        highlight = len(cats) - 1
    fig, ax = plt.subplots(figsize=(spec.get("width", 720) / 110, spec.get("height", 320) / 110), dpi=200)
    fam = [f.strip().strip("'\"") for f in theme["font"].split(",")]
    plt.rcParams["font.family"] = ["sans-serif"]
    plt.rcParams["font.sans-serif"] = fam + plt.rcParams["font.sans-serif"]
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["line"])
    ax.tick_params(colors=theme["ink_muted"], length=0)
    if kind in ("column", "bar"):
        vals = series[0]["values"]
        colors = [theme["accent"] if (i == highlight or highlight is None) else theme["neutral"] for i in range(len(cats))]
        if kind == "column":
            bars = ax.bar(cats, vals, color=colors, width=0.62)
        else:
            bars = ax.barh(cats, vals, color=colors, height=0.62)
        if kind == "bar":
            ax.invert_yaxis()
            lo, hi = min(0, min(vals)), max(0, max(vals))
            span = hi - lo
            ax.set_xlim(lo - span * (0.18 if lo < 0 else 0), hi + span * 0.15)
            ax.axvline(0, color=theme["line"], linewidth=0.8)
        for i, (b, v) in enumerate(zip(bars, vals)):
            txt = fmt_number(v, fmt)
            weight = "bold" if i == highlight else "normal"
            if kind == "column":
                ly = b.get_height()
                ref = spec.get("reference")
                if ref:  # keep the label off the reference line
                    lo, hi = ax.get_ylim()
                    if 0 <= ref["value"] - ly < (hi - lo) * 0.07:
                        ly = ref["value"]
                ax.annotate(txt, (b.get_x() + b.get_width() / 2, ly), ha="center", va="bottom", xytext=(0, 3),
                            textcoords="offset points", color=theme["ink"], fontsize=8, fontweight=weight, zorder=4,
                            bbox=dict(boxstyle="square,pad=0.1", facecolor=theme["surface"], edgecolor="none"))
            else:
                neg = v < 0
                ax.annotate(txt, (b.get_width(), b.get_y() + b.get_height() / 2), ha="right" if neg else "left",
                            va="center", xytext=(-4 if neg else 4, 0), textcoords="offset points", color=theme["ink"],
                            fontsize=8, fontweight=weight)
        (ax.set_yticks if kind == "column" else ax.set_xticks)([])
    else:
        for si, s in enumerate(series):
            ax.plot(cats, s["values"], color=(theme["accent"], theme["neutral"], theme["series2"])[si % 3], linewidth=2,
                    label=s.get("name"))
        if len(series) > 1:
            ax.legend(frameon=False, fontsize=8, labelcolor=theme["ink_muted"])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt_number(v, fmt)))
        ax.grid(axis="y", color=theme["line"], linewidth=0.6)
    ref = spec.get("reference")
    if ref and kind != "bar":
        ax.axhline(ref["value"], color=theme["ink"], linestyle=(0, (4, 4)), linewidth=1)
        ax.annotate(ref.get("label", ""), (1, ref["value"]), xycoords=("axes fraction", "data"), ha="right", va="bottom",
                    xytext=(0, 3), textcoords="offset points", color=theme["ink"], fontsize=8, fontweight="bold")
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(8)
    if highlight is not None and kind in ("column", "bar"):
        ticks = ax.get_xticklabels() if kind == "column" else ax.get_yticklabels()
        if 0 <= highlight < len(ticks):
            ticks[highlight].set_fontweight("bold")
            ticks[highlight].set_color(theme["ink"])
    fig.tight_layout()
    fig.savefig(out_path, transparent=False, facecolor=theme["surface"])
    plt.close(fig)


def main_chart():
    if len(sys.argv) != 3:
        print("usage: vds.py chart <chart.json> <out.svg|out.png>")
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    out = sys.argv[2]
    if out.lower().endswith(".png"):
        chart_png(spec, out)
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(chart_svg(spec))
    print(f"Wrote {out}")


# ============================================================================
# PDF: print a document to PDF, then check page fill
# ============================================================================
def find_browser():
    for name in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge"):
        if shutil.which(name):
            return shutil.which(name)
    for path in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
        if os.path.exists(path):
            return path
    return None


def page_fill(pdf):
    """Lines of text per page (pdftotext, else pypdf). Returns a list, or [] if neither is available."""
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
        return [sum(1 for l in page.split("\n") if l.strip()) for page in text.split("\f") if page is not None][:-1] or []
    try:
        from pypdf import PdfReader
        return [sum(1 for l in (p.extract_text() or "").split("\n") if l.strip()) for p in PdfReader(pdf).pages]
    except Exception:  # noqa: BLE001
        return []


def main_pdf():
    """HTML: a browser engine prints it faithfully; LibreOffice (the only engine in Cowork) ignores grid, flex
    and custom properties, so for HTML without a browser this stops and recommends the Word route.
    .docx/.pptx/.xlsx: LibreOffice converts them faithfully."""
    if len(sys.argv) != 3:
        print("usage: vds.py pdf <document.html|.docx|.pptx|.xlsx> <out.pdf>")
        sys.exit(2)
    src, out = sys.argv[1], sys.argv[2]
    browser = find_browser()
    if src.lower().endswith((".html", ".htm")):
        if not browser:
            print("ERROR no browser engine here: LibreOffice would drop the CSS layout (grid, flex, variables).\n"
                  "Build the document as Word (vds.py docx) and run: vds.py pdf out.docx out.pdf")
            sys.exit(1)
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                        f"--print-to-pdf={os.path.abspath(out)}", "file://" + os.path.abspath(src)],
                       capture_output=True, timeout=180)
    else:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            print("ERROR LibreOffice not available")
            sys.exit(1)
        outdir = os.path.dirname(os.path.abspath(out))
        with tempfile.TemporaryDirectory() as profile:
            subprocess.run([soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf",
                            "--outdir", outdir, src], capture_output=True, timeout=300)
        made = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
        if made != os.path.abspath(out) and os.path.exists(made):
            os.replace(made, out)
    if not os.path.exists(out):
        print("ERROR PDF was not produced")
        sys.exit(1)
    fill = page_fill(out)
    print(f"Wrote {out} ({len(fill) or '?'} pages)")
    if len(fill) > 1:
        fullest = max(fill)
        for i, lines in enumerate(fill, 1):
            if lines == 0:
                print(f"WARN page {i} is empty")
            elif i == len(fill) and lines < 0.4 * fullest:
                print(f"WARN last page is underfilled ({lines} lines vs {fullest}): tighten to fewer pages or move content")


# ============================================================================
# Dispatcher
# ============================================================================
COMMANDS = {
    "lint": ("vds", "main_lint"), "chart": ("vds", "main_chart"), "pdf": ("vds", "main_pdf"),
    "render": ("vds", "main_render"), "deck-check": ("vds_deck", "main_check"),
    "deck": ("vds_deck", "main_convert"), "docx": ("vds_office", "main_docx"), "xlsx": ("vds_office", "main_xlsx"),
    "lowpoly": ("vds_lowpoly", "main_lowpoly"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    module, func = COMMANDS[sys.argv[1]]
    sys.argv = [f"vds.py {sys.argv[1]}"] + sys.argv[2:]
    target = sys.modules[__name__] if module == "vds" else __import__(module)
    getattr(target, func)()


if __name__ == "__main__":
    main()
