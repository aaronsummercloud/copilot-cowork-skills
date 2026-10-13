"""Deck tools for visual-design-studio: parse and check deck.html, convert it to native PowerPoint.

Run through vds.py: `python3 scripts/vds.py deck-check deck.html` (standard library only) and
`python3 scripts/vds.py deck deck.html deck.pptx [--force] [--no-motion]` (needs python-pptx).
The deck contract is reference/deck-contract.md.
"""
import base64
import json
import math
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser
import io
import shutil
import subprocess
import tempfile

try:
    from lxml import etree
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.opc.package import Part
    from pptx.oxml.ns import qn
    from pptx.parts.image import Image as PptxImage
    from pptx.util import Emu, Pt
    _PPTX_MISSING = None
except ImportError as _exc:  # deck-check / lint paths don't need these
    _PPTX_MISSING = _exc


# ============================================================================
# Deck: parse and check deck.html (standard library)
# ============================================================================
SLIDE_W, SLIDE_H = 960, 540
PX_PER_IN = 96
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"}
INLINE_BOLD = {"b", "strong"}
INLINE_ITALIC = {"i", "em"}
ELEMENT_TYPES = {"text", "shape", "image", "chart", "table"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text", "line")

    def __init__(self, tag, attrs=None, parent=None, text=None, line=0):
        self.tag, self.attrs, self.parent, self.text, self.line = tag, dict(attrs or {}), parent, text, line
        self.children = []

    def get(self, key, default=None):
        return self.attrs.get(key, default)

    def classes(self):
        return (self.attrs.get("class") or "").split()

    def iter(self):
        yield self
        for child in self.children:
            yield from child.iter()

    def text_content(self):
        if self.tag == "#text":
            return self.text
        return "".join(c.text_content() for c in self.children if not (c.tag == "aside" and "notes" in c.classes()))


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root
        self.styles = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur, line=self.getpos()[0])
        self.cur.children.append(node)
        if tag == "style":
            self._in_style = True
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur, line=self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)
        self.cur.children.append(Node("#text", parent=self.cur, text=data))


# ---------------------------------------------------------------- styles

NAMED_COLORS = {"white": "FFFFFF", "black": "000000", "transparent": None}


def parse_root_vars(css_blocks):
    tokens = {}
    for css in css_blocks:
        for block in re.findall(r":root\s*\{([^}]*)\}", css):
            for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);?", block):
                tokens[name] = value.strip()
    return tokens


def parse_style(style):
    out = {}
    for decl in (style or "").split(";"):
        if ":" in decl:
            key, value = decl.split(":", 1)
            out[key.strip().lower()] = value.strip()
    return out


def resolve_vars(value, tokens, depth=0):
    if value is None or "var(" not in value or depth > 5:
        return value

    def repl(m):
        name, fallback = m.group(1), m.group(2)
        if name in tokens:
            return resolve_vars(tokens[name], tokens, depth + 1)
        return fallback.strip() if fallback else f"UNRESOLVED(--{name})"

    return re.sub(r"var\(\s*--([\w-]+)\s*(?:,\s*([^)]+))?\)", repl, value)


def to_hex(value):
    """CSS color -> 'RRGGBB' (no #), None for transparent; raises ValueError if unsupported."""
    if value is None:
        return None
    v = value.strip().lower()
    if v in NAMED_COLORS:
        return NAMED_COLORS[v]
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        return (h if len(h) == 6 else "".join(c * 2 for c in h)).upper()
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)", v)
    if m:
        return "".join(f"{int(x):02X}" for x in m.groups())
    raise ValueError(f"unsupported color '{value}' (use #hex or var(--token))")


def px(value, default=None):
    if value is None:
        return default
    m = re.fullmatch(r"\s*(-?[\d.]+)\s*(px)?\s*", str(value))
    if not m:
        raise ValueError(f"'{value}' is not a px length")
    return float(m.group(1))


def first_font(value):
    if not value:
        return None
    return value.split(",")[0].strip().strip("'\"")


def line_height_multiple(value, font_px):
    """CSS line-height -> multiple of font size (unitless number, px, or 'normal')."""
    if not value or value == "normal":
        return 1.2
    if value.endswith("px"):
        return px(value) / font_px
    return float(value)


# ---------------------------------------------------------------- deck model

class Deck:
    def __init__(self, path):
        self.path = path
        self.base_dir = os.path.dirname(os.path.abspath(path))
        with open(path, encoding="utf-8") as fh:
            builder = _TreeBuilder()
            builder.feed(fh.read())
        self.root = builder.root
        self.tokens = parse_root_vars(builder.styles)
        self.palette = set()
        for value in self.tokens.values():
            try:
                hexv = to_hex(value)
                if hexv:
                    self.palette.add(hexv)
            except ValueError:
                pass
        body = next((n for n in self.root.iter() if n.tag == "body"), self.root)
        self.title = body.get("data-deck-title") or next(
            (n.text_content().strip() for n in self.root.iter() if n.tag == "title"), "Deck")
        self.slides = [Slide(self, n, i + 1) for i, n in enumerate(
            n for n in self.root.iter() if n.tag == "section" and "slide" in n.classes())]

    def style(self, node):
        raw = parse_style(node.get("style"))
        return {k: resolve_vars(v, self.tokens) for k, v in raw.items()}

    def load_asset(self, src):
        """Return (bytes, ext) for a file path relative to the HTML file or a data: URI."""
        if src.startswith("data:"):
            header, _, payload = src.partition(",")
            mime = header[5:].split(";")[0]
            ext = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/svg+xml": "svg"}.get(mime)
            if not ext:
                raise ValueError(f"unsupported data URI type '{mime}'")
            data = base64.b64decode(payload) if ";base64" in header else urllib.parse.unquote(payload).encode()
            return fix_svg(data, self) if ext == "svg" else data, ext
        full = os.path.normpath(os.path.join(self.base_dir, urllib.parse.unquote(src)))
        with open(full, "rb") as fh:
            data, ext = fh.read(), os.path.splitext(full)[1].lower().lstrip(".").replace("jpeg", "jpg")
        return (fix_svg(data, self) if ext == "svg" else data), ext


def fix_svg(data, deck=None):
    """Add the SVG namespace when it's missing: without it, browsers, LibreOffice and PowerPoint read the file
    as plain XML (a page of source code instead of the picture)."""
    head = data[:600]
    if b"<svg" in head and b"xmlns=" not in head:
        data = data.replace(b"<svg", b'<svg xmlns="http://www.w3.org/2000/svg"', 1)
        if deck is not None:
            deck.svg_fixed = getattr(deck, "svg_fixed", 0) + 1
    return data


class Slide:
    def __init__(self, deck, node, number):
        self.deck, self.node, self.number = deck, node, number
        self.layout = node.get("data-layout", "")
        self.style = deck.style(node)
        bg = self.style.get("background-color") or self.style.get("background")
        self.background = bg
        notes = [c for c in node.children if c.tag == "aside" and "notes" in c.classes()]
        self.notes = "\n".join(_normalize(n.text_content()) for n in notes).strip()
        self.elements = []
        self.stray = []  # data-pptx elements that are not direct children
        for child in node.children:
            if child.tag != "#text" and child.get("data-pptx"):
                self.elements.append(Element(self, child, len(self.elements) + 1))
        for desc in node.iter():
            if desc is not node and desc.get("data-pptx") and desc.parent is not node:
                self.stray.append(desc)


class Element:
    def __init__(self, slide, node, index):
        self.slide, self.node, self.index = slide, node, index
        self.kind = node.get("data-pptx")
        self.role = node.get("data-role", "")
        self.id = node.get("id") or f"{self.kind}#{index}"
        self.style = slide.deck.style(node)
        self.errors = []
        try:
            self.x = px(self.style.get("left"))
            self.y = px(self.style.get("top"))
            self.w = px(self.style.get("width"))
            self.h = px(self.style.get("height"))
        except ValueError as exc:
            self.x = self.y = self.w = self.h = None
            self.errors.append(str(exc))
        if None in (self.x, self.y, self.w, self.h) and not self.errors:
            self.errors.append("needs inline left, top, width and height in px")

    @property
    def rect(self):
        return (self.x or 0, self.y or 0, self.w or 0, self.h or 0)

    def paragraphs(self):
        return paragraphs(self.node, self.style, self.slide.deck)


# ---------------------------------------------------------------- text model

def _normalize(text):
    return re.sub(r"\s+", " ", text)


TEXT_KEYS = ("font-family", "font-size", "font-weight", "font-style", "color", "text-align",
             "line-height", "letter-spacing", "text-transform", "margin-bottom", "margin-top")


def _merge(base, style):
    merged = dict(base)
    merged.update({k: v for k, v in style.items() if k in TEXT_KEYS})
    return merged


def paragraphs(node, base_style, deck):
    """Flatten an element into paragraphs: [{'style', 'runs', 'bullet', 'level'}].

    Block tags (p, div, h1-h6, li, blockquote) start a new paragraph; inline tags add runs.
    Each run is {'text', 'style', 'bold', 'italic'} or {'br': True}.
    """
    out, cur = [], [None]

    def is_bold(tag, style):
        return tag in INLINE_BOLD or tag in ("h1", "h2", "h3", "h4", "h5", "h6") or \
            style.get("font-weight", "") in ("bold", "600", "700", "800", "900")

    def open_para(style, bullet=None, level=0):
        cur[0] = {"style": style, "runs": [], "bullet": bullet, "level": level}
        out.append(cur[0])

    def walk(n, style, bold, italic, list_kind, level):
        for child in n.children:
            if child.tag == "#text":
                text = _normalize(child.text)
                if not text.strip() and (cur[0] is None or not cur[0]["runs"]):
                    continue
                if cur[0] is None:
                    open_para(style)
                cur[0]["runs"].append({"text": text, "style": style, "bold": bold, "italic": italic})
            elif child.tag == "br":
                if cur[0] is None:
                    open_para(style)
                cur[0]["runs"].append({"br": True})
            elif child.tag in ("aside", "script", "style", "svg"):
                continue
            elif child.tag in ("ul", "ol"):
                cur[0] = None
                walk(child, _merge(style, deck.style(child)), bold, italic, child.tag, level + 1)
                cur[0] = None
            elif child.tag in BLOCK_TAGS:
                cstyle = _merge(style, deck.style(child))
                open_para(cstyle, list_kind if child.tag == "li" else None, max(level - 1, 0))
                walk(child, cstyle, bold or is_bold(child.tag, cstyle),
                     italic or child.tag in INLINE_ITALIC or cstyle.get("font-style") == "italic", list_kind, level)
                cur[0] = None
            else:
                cstyle = _merge(style, deck.style(child))
                walk(child, cstyle, bold or is_bold(child.tag, cstyle),
                     italic or child.tag in INLINE_ITALIC or cstyle.get("font-style") == "italic", list_kind, level)

    base = {k: v for k, v in base_style.items() if k in TEXT_KEYS}
    walk(node, base, is_bold("", base), base.get("font-style") == "italic", None, 0)
    cleaned = []
    for para in out:
        runs = para["runs"]
        while runs and "text" in runs[-1] and not runs[-1]["text"].strip():
            runs.pop()
        if runs and "text" in runs[0]:
            runs[0]["text"] = runs[0]["text"].lstrip()
        if runs and "text" in runs[-1]:
            runs[-1]["text"] = runs[-1]["text"].rstrip()
        if any(r.get("text") for r in runs):
            cleaned.append(para)
    return cleaned


def para_text(para):
    return "".join(r.get("text", "\n") for r in para["runs"])


def chart_spec(element):
    raw = element.node.get("data-chart")
    if not raw:
        raise ValueError("chart element needs a data-chart JSON attribute")
    spec = json.loads(raw)
    deck = element.slide.deck
    spec["colors"] = [to_hex(resolve_vars(c, deck.tokens)) for c in spec.get("colors", [])]
    if spec.get("highlight_color"):
        spec["highlight_color"] = to_hex(resolve_vars(spec["highlight_color"], deck.tokens))
    return spec


# ---------------------------------------------------------------- motion vocabulary
# Shared with deck_to_pptx.py. See reference/motion.md (slides section).
TRANSITIONS = {"none", "fade", "push", "morph"}
ANIMS = {
    # name: (presetID, presetSubtype, filter or None, float offset)
    "appear": (1, 0, None, False),
    "fade": (10, 0, "fade", False),
    "float-up": (42, 0, "fade", True),
    "wipe-up": (22, 4, "wipe(up)", False),
    "wipe-right": (22, 8, "wipe(right)", False),
}
DEFAULT_ANIM, DEFAULT_MS, DEFAULT_STAGGER_MS = "fade", 400, 60


# ---------------------------------------------------------------- checks
# Fonts that ship with Microsoft 365 on Windows and Mac. Anything else falls back to a substitute on
# the presenter's machine. Fonts marked * may also render with different widths in LibreOffice previews.
OFFICE_FONTS = {
    "Arial", "Calibri", "Cambria", "Candara", "Consolas", "Constantia", "Corbel", "Georgia", "Segoe UI",
    "Segoe UI Semibold", "Segoe UI Light", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
    "Bahnschrift", "Sitka Text", "Sitka Heading", "Gill Sans MT", "Franklin Gothic Medium", "Century Gothic",
    "Rockwell", "Garamond", "Book Antiqua", "Palatino Linotype", "Bookman Old Style", "Century Schoolbook",
    "Courier New", "Arial Black", "Impact", "Aptos", "Aptos Display", "Grandview", "Seaford", "Tenorite",
    "Selawik",
}
ALLOWED = {
    "common": {"left", "top", "width", "height"},
    "text": {"font-family", "font-size", "font-weight", "font-style", "color", "text-align", "line-height",
             "letter-spacing", "text-transform", "padding", "display", "flex-direction", "justify-content",
             "margin-bottom", "margin-top"},
    "shape": {"background", "background-color", "border", "border-radius", "opacity"},
    "image": {"object-fit"},
    "video": set(),
    "chart": {"font-family", "font-size", "color"},
    "table": {"font-family", "font-size", "color", "font-weight", "text-align", "line-height", "border-bottom",
              "cell-padding-x", "cell-padding-y"},
}
ALLOWED["shape"] |= ALLOWED["text"]
BANNED_CSS = re.compile(r"gradient|box-shadow|transform|filter|clip-path|mix-blend|backdrop|animation|transition")
TIER1_WORDS = ["delve", "tapestry", "paradigm shift", "game-changer", "game changer", "leverage", "harness",
               "realm", "embark", "myriad", "plethora", "multifaceted", "groundbreaking", "revolutionize",
               "synergy", "testament", "unlock the power", "in today's fast-paced"]
TIER2_WORDS = ["robust", "seamless", "cutting-edge", "innovative", "comprehensive", "pivotal", "transformative",
               "unprecedented", "elevate", "empower", "streamline", "holistic"]
CREAM_DEFAULTS = {"F4F1EA", "F5F5DC", "FAF0E6", "FAEBD7", "FFF8E1", "F5F1E8", "FDF6EC"}


def safe_hex(value):
    """to_hex that returns None instead of raising; the style pass already reports bad colors."""
    try:
        return to_hex(value)
    except ValueError:
        return None


def luminance(hex6):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex6[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contains(outer, x, y):
    ox, oy, ow, oh = outer
    return ox <= x <= ox + ow and oy <= y <= oy + oh


def overlap_ratio(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    smaller = min(aw * ah, bw * bh) or 1
    return ix * iy / smaller


# Average glyph width in em for mixed-case title/body text, per Office font. Measured with Pillow on the
# installed fonts (Arial 0.454, Georgia 0.447, Times 0.408, Verdana 0.517, Trebuchet 0.459, Tahoma 0.453)
# plus about 5% margin; Office-only fonts are set from their published proportions relative to those.
# Digits are tabular (about 0.56 em) and are counted separately in text_em().
FONT_WIDTH = {
    "Arial": 0.48, "Calibri": 0.44, "Cambria": 0.47, "Candara": 0.45, "Consolas": 0.58, "Constantia": 0.47,
    "Corbel": 0.44, "Georgia": 0.47, "Segoe UI": 0.49, "Segoe UI Semibold": 0.51, "Segoe UI Light": 0.47,
    "Tahoma": 0.48, "Times New Roman": 0.43, "Trebuchet MS": 0.48, "Verdana": 0.54, "Bahnschrift": 0.46,
    "Sitka Text": 0.49, "Sitka Heading": 0.46, "Gill Sans MT": 0.43, "Franklin Gothic Medium": 0.47,
    "Century Gothic": 0.55, "Rockwell": 0.50, "Garamond": 0.43, "Book Antiqua": 0.47, "Palatino Linotype": 0.47,
    "Bookman Old Style": 0.53, "Century Schoolbook": 0.50, "Courier New": 0.60, "Arial Black": 0.59,
    "Impact": 0.43, "Aptos": 0.46, "Aptos Display": 0.45, "Grandview": 0.46, "Seaford": 0.47, "Tenorite": 0.48,
}


def char_width_factor(font):
    return FONT_WIDTH.get(font, 0.48)


def text_em(text, factor):
    """Width of a string in em: digits at tabular width, everything else at the font's average."""
    scale = factor / 0.454  # relative to Arial, where digits are 0.556 em
    return sum(0.56 * scale if ch.isdigit() else factor for ch in text)


def estimate_height(paragraphs, box_w):
    """Rough rendered text height in px: average glyph width x chars, wrapped to the box width."""
    total = 0.0
    for para in paragraphs:
        style = para["style"]
        size = px(style.get("font-size"), 16)
        font = first_font(style.get("font-family")) or "Calibri"
        bold = 1.06 if any(r.get("bold") for r in para["runs"]) else 1.0
        indent = size * 1.2 * (para["level"] + 1) if para["bullet"] else 0
        usable = max(box_w - indent, size)
        lines = 0
        for chunk in para_text(para).split("\n"):
            chunk_w = text_em(chunk, char_width_factor(font)) * size * bold
            lines += max(1, math.ceil(chunk_w / usable))
        total += lines * size * line_height_multiple(style.get("line-height"), size)
        total += px(style.get("margin-bottom"), 0) + px(style.get("margin-top"), 0)
    return total


def run_checks(path):
    errors, warnings = [], []
    deck = Deck(path)

    def err(slide, el, msg):
        errors.append(f"slide {slide.number}{' ' + el.id if el else ''}: {msg}")

    def warn(slide, el, msg):
        warnings.append(f"slide {slide.number}{' ' + el.id if el else ''}: {msg}")

    if not deck.slides:
        errors.append('no <section class="slide"> elements found')
        return errors, warnings
    if not deck.tokens:
        warnings.append("no :root color/font tokens found; define the palette as CSS variables")
    title_positions = {}
    previous_layout = None
    for slide in deck.slides:
        for stray in slide.stray:
            err(slide, None, f"<{stray.tag} data-pptx> on line {stray.line} must be a direct child of the slide")
        try:
            slide_bg = to_hex(slide.background) if slide.background else "FFFFFF"
        except ValueError as exc:
            err(slide, None, str(exc))
            slide_bg = "FFFFFF"
        if slide_bg in CREAM_DEFAULTS:
            warn(slide, None, f"background #{slide_bg} is a generic cream default; choose a background from the brief")
        if slide.layout and slide.layout == previous_layout and slide.layout not in ("section", "divider"):
            warn(slide, None, f"same layout '{slide.layout}' as the previous slide; vary the layout")
        previous_layout = slide.layout
        has_visual = False
        words = 0
        shapes_below = []  # (rect, fill) of shapes/images painted before the current element
        for el in slide.elements:
            for e in el.errors:
                err(slide, el, e)
            if el.kind not in ("text", "shape", "image", "chart", "table", "video"):
                err(slide, el, f"unknown data-pptx type '{el.kind}'")
                continue
            for key, value in el.style.items():
                if key not in ALLOWED["common"] | ALLOWED[el.kind]:
                    warn(slide, el, f"CSS '{key}' is ignored by the converter")
                if BANNED_CSS.search(f"{key}:{value}"):
                    err(slide, el, f"'{key}: {value}' has no PowerPoint equivalent")
                if "UNRESOLVED" in value:
                    err(slide, el, f"{key} uses an undefined token: {value}")
                if key in ("color", "background", "background-color") and "UNRESOLVED" not in value:
                    try:
                        hexv = to_hex(value)
                        if hexv and deck.palette and hexv not in deck.palette:
                            warn(slide, el, f"{key} #{hexv} is not a palette token; use var(--token)")
                    except ValueError as exc:
                        err(slide, el, str(exc))
            if el.errors:
                continue
            x, y, w, h = el.rect
            if x < -1 or y < -1 or x + w > SLIDE_W + 1 or y + h > SLIDE_H + 1:
                err(slide, el, f"extends outside the 960x540 slide ({x:.0f},{y:.0f},{w:.0f}x{h:.0f})")
            elif el.kind in ("text", "chart", "table") and (x < 40 or y < 24 or x + w > SLIDE_W - 40 or y + h > SLIDE_H - 24):
                warn(slide, el, "content sits inside the edge margin (keep >= 40px sides, 24px top/bottom)")

            if el.kind in ("image", "chart", "table", "video") or el.kind == "shape":
                has_visual = True
            if el.kind == "video":
                check_video(deck, slide, el, err, warn)
            if el.kind == "image":
                src = el.node.get("src") or ""
                try:
                    deck.load_asset(src)
                except Exception as exc:  # noqa: BLE001
                    err(slide, el, f"image source can't be loaded: {exc}")
                if not el.node.get("alt"):
                    warn(slide, el, "image has no alt text")
                if src.lower().split("?")[0].endswith(".gif") and gif_loops_forever(deck, src):
                    warn(slide, el, "GIF loops forever with no pause control; use a GIF that plays once, or a "
                                    "<video data-pptx=\"video\"> (vds.py lowpoly makes both)")
                if getattr(deck, "svg_fixed", 0):
                    warn(slide, el, "SVG had no xmlns; it was added for conversion, add it to the source too")
                    deck.svg_fixed = 0
            if el.kind == "chart":
                try:
                    spec = chart_spec(el)
                    n = len(spec["categories"])
                    if spec.get("type", "column") not in ("column", "stacked-column", "bar", "stacked-bar",
                                                          "line", "pie", "doughnut"):
                        err(slide, el, f"chart type '{spec.get('type')}' not supported")
                    for s in spec["series"]:
                        if len(s["values"]) != n:
                            err(slide, el, f"series '{s.get('name')}' has {len(s['values'])} values for {n} categories")
                    if len(spec["series"]) > 6:
                        warn(slide, el, "more than 6 series; fold extras into 'Other' or split the chart")
                    hl = spec.get("highlight")
                    if hl is not None and hl != "last" and not (isinstance(hl, int) and 0 <= hl < n):
                        err(slide, el, f"chart highlight '{hl}' must be \"last\" or an index 0..{n - 1}")
                    if spec.get("type") in ("pie", "doughnut") and n > 5:
                        warn(slide, el, "pie/doughnut with more than 5 slices; use a bar chart")
                    if len(spec["series"]) > 1 and len(spec.get("colors", [])) < len(spec["series"]):
                        warn(slide, el, "give each series its own palette color")
                    if not spec.get("source") and not el.slide.node.text_content().lower().count("source"):
                        warn(slide, el, "chart has no source line on the slide")
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    err(slide, el, f"invalid data-chart: {exc}")

            if el.kind in ("text", "shape", "table") and el.node.text_content().strip():
                paras = el.paragraphs() if el.kind != "table" else []
                text = " ".join(para_text(p) for p in paras) if paras else el.node.text_content()
                words += len(text.split())
                lowered = text.lower()
                for word in TIER1_WORDS:
                    if re.search(r"\b" + re.escape(word), lowered):
                        warn(slide, el, f"'{word}' reads as AI filler; say the specific thing")
                tier2 = [w for w in TIER2_WORDS if re.search(r"\b" + re.escape(w), lowered)]
                if len(tier2) >= 2:
                    warn(slide, el, f"buzzword cluster: {', '.join(tier2)}")
                for para in paras:
                    style = para["style"]
                    size = px(style.get("font-size"), 16)
                    font = first_font(style.get("font-family"))
                    if size < 13.3:
                        err(slide, el, f"font-size {size:.0f}px is below the 10pt floor (13.3px)")
                    elif size < 18.6 and len(para_text(para)) > 60 and el.role not in ("caption", "source", "label"):
                        warn(slide, el, f"body text at {size:.0f}px is below 14pt (18.7px)")
                    if font and font not in OFFICE_FONTS:
                        err(slide, el, f"font '{font}' doesn't ship with Office; PowerPoint will substitute it")
                    elif font == "Aptos":
                        warn(slide, el, "Aptos is missing from older Office installs; prefer Calibri/Segoe UI")
                    # contrast against what is painted underneath
                    fg = safe_hex(style.get("color") or "#000000")
                    if el.kind == "shape" and safe_hex(el.style.get("background") or el.style.get("background-color") or "transparent"):
                        bg, under = safe_hex(el.style.get("background") or el.style.get("background-color")), "shape"
                    else:
                        cx, cy = x + w / 2, y + min(h, size * 1.5) / 2
                        under = next((u for u in reversed(shapes_below) if contains(u[0], cx, cy)), None)
                        bg = under[1] if under else slide_bg
                        under = under[2] if under else "slide"
                    if bg == "IMAGE":
                        warn(slide, el, "text sits on an image; check contrast by eye or add a solid scrim shape")
                    elif fg and bg:
                        ratio = contrast(fg, bg)
                        large = size >= 24 or (size >= 18.6 and any(r.get("bold") for r in para["runs"]))
                        need = 3.0 if large else 4.5
                        if ratio < need:
                            err(slide, el, f"contrast {ratio:.1f}:1 (#{fg} on {under} #{bg}) is below {need}:1")
                    if style.get("text-transform") == "uppercase" and len(para_text(para)) > 3 and el.role != "title":
                        warn(slide, el, "all-caps label: a common AI-design tell; use sentence case")
                    if style.get("text-align") == "center" and el.role not in ("title", "subtitle", "stat", "label") \
                            and len(para_text(para)) > 90:
                        warn(slide, el, "centered body text; left-align paragraphs and lists")
                if el.role == "title" and paras and para_text(paras[0]).rstrip().endswith("."):
                    warn(slide, el, "slide titles don't end with a period")
                if el.role == "title" and slide.layout not in ("cover", "section", "closing", "divider"):
                    size = px(paras[0]["style"].get("font-size"), 16) if paras else 0
                    title_positions.setdefault((round(x), round(y), round(size)), []).append(slide.number)
                if paras:
                    pad = (el.style.get("padding") or "0").replace("px", "").split()
                    pad_v = float(pad[0]) * 2 if pad else 0
                    pad_h = float(pad[1 if len(pad) > 1 else 0]) * 2 if pad else 0
                    need_h = estimate_height(paras, w - pad_h) + pad_v
                    verified = el.node.get("data-fit") == "verified"
                    if verified and not el.node.get("data-fit-reason"):
                        err(slide, el, 'data-fit="verified" needs data-fit-reason (e.g. "vds.py render: one line")')
                    if need_h > h * 1.02 and verified:
                        warn(slide, el, f"estimate says ~{need_h:.0f}px in {h:.0f}px; fit verified: {el.node.get('data-fit-reason')}")
                    elif need_h > h * 1.02:
                        err(slide, el, f"text likely overflows: needs ~{need_h:.0f}px, box is {h:.0f}px "
                                       "(if a real render proves it fits, add data-fit=\"verified\" data-fit-reason=\"…\")")
                    elif need_h > h * 0.9:
                        warn(slide, el, f"text is tight: ~{need_h:.0f}px in a {h:.0f}px box; leave ~10% slack")
            if el.kind == "shape":
                fill = safe_hex(el.style.get("background") or el.style.get("background-color") or "transparent")
                if fill:
                    shapes_below.append((el.rect, fill, f"shape {el.id}"))
                # AI-tell geometry: thin accent rules and edge stripes
                if h <= 6 and w <= 320 and not el.node.text_content().strip():
                    near_title = any(o.role == "title" and abs(o.y + o.h - y) < 36 for o in slide.elements if o is not el)
                    if near_title:
                        warn(slide, el, "short accent line under the title is an AI-slide tell; use space instead")
                if (w <= 14 and h >= SLIDE_H * 0.5) or (h <= 14 and w >= SLIDE_W * 0.9 and (y < 30 or y + h > SLIDE_H - 30)):
                    warn(slide, el, "edge stripe/bar is decorative filler; drop it or make it carry information")
            if el.kind in ("image", "video"):
                shapes_below.append((el.rect, "IMAGE", f"{el.kind} {el.id}"))
        for i, a in enumerate(slide.elements):
            for b in slide.elements[i + 1:]:
                if a.kind == "text" and b.kind == "text" and not (a.errors or b.errors) \
                        and overlap_ratio(a.rect, b.rect) > 0.05:
                    warn(slide, b, f"overlaps text box {a.id}")
        if slide.layout not in ("cover", "section", "divider", "closing", "quote") and not has_visual:
            warn(slide, None, "text-only slide; add a chart, image, icon or shape that carries meaning")
        if words > 90:
            warn(slide, None, f"{words} words on one slide; cut to one message (aim for under 60)")
    if len(title_positions) > 1:
        detail = "; ".join(f"x={k[0]},y={k[1]},{k[2]}px on slides {v}" for k, v in title_positions.items())
        warnings.append(f"deck: content-slide titles drift between positions/sizes ({detail})")
    check_motion(deck, errors, warnings)
    return errors, warnings


def check_motion(deck, errors, warnings):
    """Motion rules adapted from the ui-animation and animate skills (reference/md)."""
    body = next((n for n in deck.root.iter() if n.tag == "body"), None)
    mode = body.get("data-mode", "live") if body is not None else "live"
    kinds, animated_slides, prev_keys = set(), 0, set()
    for slide in deck.slides:
        where = f"slide {slide.number}"
        kind = slide.node.get("data-transition", "none")
        if kind not in TRANSITIONS:
            errors.append(f"{where}: data-transition '{kind}' must be one of {sorted(TRANSITIONS)}")
        if kind not in ("none", "morph"):
            kinds.add(kind)
        ms = slide.node.get("data-transition-ms")
        if ms and not 150 <= int(ms) <= 1000:
            warnings.append(f"{where}: transition {ms}ms; keep slide transitions between 150 and 1000ms")
        keys = [e.node.get("data-morph") for e in slide.elements if e.node.get("data-morph")]
        if len(keys) != len(set(keys)):
            errors.append(f"{where}: duplicate data-morph key on one slide")
        if kind == "morph" and not set(keys) & prev_keys:
            warnings.append(f"{where}: Morph shares no data-morph key with the previous slide; use fade")
        prev_keys = set(keys)
        if mode == "pre-read" and kind not in ("none", "fade"):
            warnings.append(f"{where}: pre-read decks are read, not presented; use no transition or fade")
        videos = [e for e in slide.elements if e.kind == "video"]
        if len(videos) > 1:
            warnings.append(f"{where}: {len(videos)} videos on one slide; keep one moving object per slide")
        if videos and mode == "pre-read":
            warnings.append(f"{where}: a pre-read or PDF shows only the video's poster frame; make sure it reads alone")
        builds = [e for e in slide.elements if e.node.get("data-build") is not None and e.kind != "video"]
        if not builds:
            continue
        animated_slides += 1
        if mode == "pre-read":
            warnings.append(f"{where}: builds hide content in a pre-read or PDF; remove them")
        groups = {}
        for el in builds:
            try:
                group = int(el.node.get("data-build"))
                duration = int(el.node.get("data-duration", DEFAULT_MS))
                delay = int(el.node.get("data-delay") or 0)
            except ValueError:
                errors.append(f"{where} {el.id}: data-build, data-duration and data-delay must be integers")
                continue
            groups.setdefault(group, []).append((el, duration, delay))
            anim = el.node.get("data-anim", DEFAULT_ANIM)
            if anim not in ANIMS:
                errors.append(f"{where} {el.id}: data-anim '{anim}' must be one of {sorted(ANIMS)}")
            if not 150 <= duration <= 1000:
                warnings.append(f"{where} {el.id}: {duration}ms; builds run 250-600ms")
            elif duration > 600:
                warnings.append(f"{where} {el.id}: {duration}ms build makes the presenter wait; use 300-500ms")
            if el.role == "title":
                warnings.append(f"{where} {el.id}: don't hide the title; it is the slide's message")
            if group == 0 and slide.layout not in ("cover", "section", "divider", "closing", "quote"):
                warnings.append(f"{where} {el.id}: auto-play (data-build=0) belongs on cover, section or closing slides")
        if len([g for g in groups if g > 0]) > 5:
            warnings.append(f"{where}: more than 5 click builds; split the slide or show it whole")
        for group, members in groups.items():
            span = max(delay + duration for _, duration, delay in members)
            if span > 1200:
                warnings.append(f"{where}: build group {group} lasts {span}ms; keep a group under ~1s")
        built = [e for e in builds if e.kind == "shape"]
        for container in built:
            cx, cy, cw, ch = container.rect
            for el in slide.elements:
                if el is container or el.errors:
                    continue
                ex, ey, ew, eh = el.rect
                if cx <= ex + ew / 2 <= cx + cw and cy <= ey + eh / 2 <= cy + ch \
                        and el.node.get("data-build") != container.node.get("data-build"):
                    warnings.append(f"{where} {el.id}: enters separately from its container {container.id}; "
                                    "give them one entrance (same data-build)")
    if len(kinds) > 1:
        warnings.append(f"deck: {len(kinds)} transition styles ({', '.join(sorted(kinds))}); use one, plus Morph where objects persist")
    if deck.slides and animated_slides / len(deck.slides) > 0.6:
        warnings.append("deck: builds on most slides; motion loses meaning when everything moves")


VIDEO_EXT = {"mp4": "video/mp4", "m4v": "video/mp4", "mov": "video/quicktime"}


def check_video(deck, slide, el, err, warn):
    """<video data-pptx="video" src="x.mp4" poster="x.png" data-play="auto|click" aria-label="…">"""
    src, poster = el.node.get("src") or "", el.node.get("poster") or ""
    ext = os.path.splitext(src.split("?")[0])[1].lower().lstrip(".")
    if ext not in VIDEO_EXT:
        err(slide, el, f"video src must be .mp4 (H.264) or .mov, not '{src}'")
    elif not os.path.exists(os.path.join(deck.base_dir, urllib.parse.unquote(src))):
        err(slide, el, f"video file not found: {src}")
    elif os.path.getsize(os.path.join(deck.base_dir, urllib.parse.unquote(src))) > 25 * 1024 * 1024:
        warn(slide, el, "video is over 25 MB; shorten it or lower the size (vds.py lowpoly --size)")
    if not poster:
        err(slide, el, "video needs a poster image (the still frame shown in PDFs, handouts and before it plays)")
    else:
        try:
            deck.load_asset(poster)
        except Exception as exc:  # noqa: BLE001
            err(slide, el, f"poster can't be loaded: {exc}")
    if not (el.node.get("aria-label") or el.node.get("title")):
        warn(slide, el, "video has no aria-label (it becomes the alt text in PowerPoint)")
    play = el.node.get("data-play", "auto")
    if play not in ("auto", "click"):
        err(slide, el, f"data-play must be 'auto' or 'click', not '{play}'")
    if play == "click" and el.node.get("data-build") in (None, "0"):
        warn(slide, el, 'data-play="click" plays on the click given by data-build="n" (n >= 1); add one')


def gif_loops_forever(deck, src):
    """True when the GIF carries a NETSCAPE loop block with count 0 (loops forever)."""
    try:
        data, _ = deck.load_asset(src)
    except Exception:  # noqa: BLE001
        return False
    i = data.find(b"NETSCAPE2.0")
    return i >= 0 and len(data) >= i + 16 and data[i + 13:i + 15] == b"\x00\x00"


def mp4_duration_ms(path):
    """Duration from the mp4/mov 'mvhd' box (version 0 or 1); None if it can't be read."""
    import struct
    with open(path, "rb") as fh:
        data = fh.read()
    i = data.find(b"mvhd")
    if i < 0:
        return None
    version = data[i + 4]
    if version == 1:
        scale, dur = struct.unpack(">IQ", data[i + 24:i + 36])
    else:
        scale, dur = struct.unpack(">II", data[i + 16:i + 24])
    return round(dur * 1000 / scale) if scale else None


def print_report(errors, warnings):
    for e in errors:
        print("ERROR", e)
    for w in warnings:
        print("WARN ", w)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")


def main_check():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    errors, warnings = run_checks(sys.argv[1])
    print_report(errors, warnings)
    sys.exit(1 if errors else 0)



# ============================================================================
# Deck: convert deck.html -> native .pptx with motion (python-pptx)
# ============================================================================
EMU_PER_PX = 914400 // PX_PER_IN  # 9525
SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
SVG_NS = "http://schemas.microsoft.com/office/drawing/2016/SVG/main_convert"
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY}
ANCHOR = {"center": MSO_ANCHOR.MIDDLE, "flex-end": MSO_ANCHOR.BOTTOM, "end": MSO_ANCHOR.BOTTOM}
CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED, "stacked-column": XL_CHART_TYPE.COLUMN_STACKED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED, "stacked-bar": XL_CHART_TYPE.BAR_STACKED,
    "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT,
}


def emu(value_px):
    return Emu(int(round(value_px * EMU_PER_PX)))


def pt(value_px):
    return Pt(value_px * 0.75)


def is_bold_weight(value):
    return str(value) in ("bold", "600", "700", "800", "900")


# ---------------------------------------------------------------- text

def apply_text(frame, style, paras):
    frame.word_wrap = True
    frame.auto_size = None
    pad = [px(v) for v in (style.get("padding") or "0").replace("px", "").split()] or [0]
    pad = (pad * 4)[:4] if len(pad) == 1 else (pad + pad)[:4] if len(pad) == 2 else (pad + [pad[1]])[:4]
    frame.margin_top, frame.margin_right, frame.margin_bottom, frame.margin_left = (emu(p) for p in pad)
    frame.vertical_anchor = ANCHOR.get(style.get("justify-content"), MSO_ANCHOR.TOP)

    for i, para in enumerate(paras):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        pstyle = para["style"]
        size_px = px(pstyle.get("font-size"), 16)
        p.alignment = ALIGN.get(pstyle.get("text-align", "left"), PP_ALIGN.LEFT)
        # CSS line-height is relative to font size; PowerPoint's multiple is relative to ~1.2x font size.
        p.line_spacing = round(line_height_multiple(pstyle.get("line-height"), size_px) / 1.2, 2)
        if pstyle.get("margin-bottom"):
            p.space_after = pt(px(pstyle["margin-bottom"]))
        if pstyle.get("margin-top"):
            p.space_before = pt(px(pstyle["margin-top"]))
        if para["bullet"]:
            set_bullet(p, para["bullet"], para["level"], size_px)
        for run_spec in para["runs"]:
            if run_spec.get("br"):
                p.add_line_break()
                continue
            text = run_spec["text"]
            rstyle = run_spec["style"]
            if rstyle.get("text-transform") == "uppercase":
                text = text.upper()
            run = p.add_run()
            run.text = text
            font = run.font
            font.size = pt(px(rstyle.get("font-size"), size_px))
            font.name = first_font(rstyle.get("font-family")) or "Calibri"
            font.bold = run_spec["bold"]
            font.italic = run_spec["italic"]
            color = to_hex(rstyle.get("color") or "#000000")
            if color:
                font.color.rgb = RGBColor.from_string(color)
            if rstyle.get("letter-spacing"):
                run._r.get_or_add_rPr().set("spc", str(int(round(px(rstyle["letter-spacing"]) * 75))))


def set_bullet(paragraph, kind, level, size_px):
    pPr = paragraph._p.get_or_add_pPr()
    indent = int(size_px * 1.2 * EMU_PER_PX)
    pPr.set("marL", str(indent * (level + 1)))
    pPr.set("indent", str(-indent))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for old in pPr.findall(qn(tag)):
            pPr.remove(old)
    if kind == "ol":
        bullet = etree.SubElement(pPr, qn("a:buAutoNum"))
        bullet.set("type", "arabicPeriod")
    else:
        bullet = etree.SubElement(pPr, qn("a:buChar"))
        bullet.set("char", "•")


# ---------------------------------------------------------------- shapes

def set_alpha(fill_parent_xml, opacity):
    srgb = fill_parent_xml.find(".//" + qn("a:srgbClr"))
    if srgb is not None and opacity < 1:
        alpha = etree.SubElement(srgb, qn("a:alpha"))
        alpha.set("val", str(int(opacity * 100000)))


def add_shape(slide, element, deck):
    style = element.style
    radius = (style.get("border-radius") or "0").strip()
    x, y, w, h = element.rect
    if radius.endswith("%") and float(radius[:-1]) >= 50:
        kind = MSO_SHAPE.OVAL
    elif px(radius or "0", 0) > 0:
        kind = MSO_SHAPE.ROUNDED_RECTANGLE
    else:
        kind = MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, emu(x), emu(y), emu(w), emu(h))
    shape.name = element.id
    shape.shadow.inherit = False
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shape.adjustments[0] = min(px(radius) / min(w, h), 0.5)
    fill_hex = to_hex(style.get("background-color") or style.get("background") or "transparent")
    if fill_hex:
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(fill_hex)
        if style.get("opacity"):
            set_alpha(shape._element.spPr, float(style["opacity"]))
    else:
        shape.fill.background()
    border = style.get("border")
    if border and border not in ("none", "0"):
        parts = border.split()
        shape.line.width = pt(px(parts[0]))
        shape.line.color.rgb = RGBColor.from_string(to_hex(parts[-1]))
    else:
        shape.line.fill.background()
    if element.node.text_content().strip():
        apply_text(shape.text_frame, style, element.paragraphs())
    else:
        shape.text_frame.text = ""
    return shape


def add_textbox(slide, element, deck):
    x, y, w, h = element.rect
    box = slide.shapes.add_textbox(emu(x), emu(y), emu(w), emu(h))
    box.name = element.id
    apply_text(box.text_frame, element.style, element.paragraphs())
    return box


# ---------------------------------------------------------------- images

def _svg_size(blob):
    """Intrinsic SVG size in px from width/height or viewBox (fallback 512x512)."""
    root = etree.fromstring(blob)
    try:
        return int(float(str(root.get("width")).rstrip("px"))), int(float(str(root.get("height")).rstrip("px")))
    except (TypeError, ValueError):
        box = (root.get("viewBox") or "0 0 512 512").replace(",", " ").split()
        return int(float(box[2])), int(float(box[3]))


def rasterize_svgs(svg_blobs, scale=2):
    """SVG -> PNG fallbacks. Tries LibreOffice (present in Cowork), then CairoSVG, then a headless
    Chrome/Chromium. Returns {key: png_bytes}; keys that no renderer could handle are omitted."""
    out = {}
    if not svg_blobs:
        return out
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for key, blob in svg_blobs.items():
            path = os.path.join(tmp, f"{key}.svg")
            with open(path, "wb") as fh:
                fh.write(blob)
            paths[key] = path
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            profile = "file://" + os.path.join(tmp, "lo_profile")
            try:
                subprocess.run([soffice, f"-env:UserInstallation={profile}", "--headless", "--convert-to", "png",
                                "--outdir", tmp, *paths.values()], capture_output=True, timeout=180)
            except subprocess.TimeoutExpired:
                pass
            for key in svg_blobs:
                png = os.path.join(tmp, f"{key}.png")
                if os.path.exists(png):
                    with open(png, "rb") as fh:
                        out[key] = fh.read()
        missing = [k for k in svg_blobs if k not in out]
        if missing:
            try:
                import cairosvg
                for key in missing:
                    out[key] = cairosvg.svg2png(bytestring=svg_blobs[key], scale=scale)
            except ImportError:
                pass
        missing = [k for k in svg_blobs if k not in out]
        chrome = next((c for c in (shutil.which("chromium"), shutil.which("chromium-browser"),
                                   shutil.which("google-chrome"),
                                   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                       if c and os.path.exists(c)), None)
        for key in missing if chrome else []:
            w, h = _svg_size(svg_blobs[key])
            png = os.path.join(tmp, f"{key}-chrome.png")
            try:
                subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                                f"--force-device-scale-factor={scale}", f"--window-size={w},{h}",
                                "--default-background-color=00000000", f"--screenshot={png}",
                                "file://" + paths[key]], capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                continue
            if os.path.exists(png):
                with open(png, "rb") as fh:
                    out[key] = fh.read()
    return out


def make_png(width=1, height=1):
    """A valid fully transparent RGBA PNG, built with zlib (used when an SVG can't be rasterized)."""
    import struct
    import zlib

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"\x00\x00\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


BLANK_PNG = make_png()


def embed_svg(picture, slide, svg_blob):
    """Attach the original SVG to a picture so PowerPoint 365 renders it as vector art."""
    package = slide.part.package
    partname = package.next_partname("/ppt/media/svg%d.svg")
    svg_part = Part(partname, "image/svg+xml", package, svg_blob)
    rid = slide.part.relate_to(svg_part, RT.IMAGE)
    blip = picture._element.find(".//" + qn("a:blip"))
    ext_lst = blip.find(qn("a:extLst"))
    if ext_lst is None:
        ext_lst = etree.SubElement(blip, qn("a:extLst"))
    ext = etree.SubElement(ext_lst, qn("a:ext"))
    ext.set("uri", SVG_EXT_URI)
    svg_blip = etree.SubElement(ext, f"{{{SVG_NS}}}svgBlip", nsmap={"asvg": SVG_NS})
    svg_blip.set(qn("r:embed"), rid)


def add_image(slide, element, deck, raster_cache, motion_on=True):
    x, y, w, h = element.rect
    blob, ext = deck.load_asset(element.node.get("src"))
    if ext == "gif" and not motion_on:
        blob, ext = gif_still(blob), "png"
    svg_blob = None
    if ext == "svg":
        svg_blob = blob
        blob = raster_cache.get(element.id) or BLANK_PNG
    picture = slide.shapes.add_picture(io.BytesIO(blob), emu(x), emu(y), emu(w), emu(h))
    picture.name = element.id
    alt = element.node.get("alt")
    if alt:
        picture._element.nvPicPr.cNvPr.set("descr", alt)
    if element.style.get("object-fit") == "cover" and svg_blob is None:
        img_w, img_h = PptxImage.from_blob(blob).size
        box_ratio, img_ratio = w / h, img_w / img_h
        if img_ratio > box_ratio:  # image wider than box: crop left/right
            crop = (1 - box_ratio / img_ratio) / 2
            picture.crop_left = picture.crop_right = crop
        elif img_ratio < box_ratio:
            crop = (1 - img_ratio / box_ratio) / 2
            picture.crop_top = picture.crop_bottom = crop
    if svg_blob is not None:
        embed_svg(picture, slide, svg_blob)
    return picture


def add_video(slide, element, deck, motion_on):
    """An embedded H.264 video with its poster frame, or (without motion) just the poster as a picture."""
    x, y, w, h = element.rect
    poster, _ = deck.load_asset(element.node.get("poster"))
    alt = element.node.get("aria-label") or element.node.get("title") or ""
    if not motion_on:
        shape = slide.shapes.add_picture(io.BytesIO(poster), emu(x), emu(y), emu(w), emu(h))
    else:
        path = os.path.join(deck.base_dir, urllib.parse.unquote(element.node.get("src")))
        mime = VIDEO_EXT.get(os.path.splitext(path)[1].lower().lstrip("."), "video/mp4")
        shape = slide.shapes.add_movie(path, emu(x), emu(y), emu(w), emu(h), poster_frame_image=io.BytesIO(poster),
                                       mime_type=mime)
        for timing in slide._element.findall(qn("p:timing")):   # rebuilt with the slide's builds in add_builds
            slide._element.remove(timing)
    shape.name = element.id
    if alt:
        shape._element.nvPicPr.cNvPr.set("descr", alt)
    return shape


def gif_still(blob):
    """The last frame of a GIF as PNG bytes, for handout (--no-motion) decks."""
    from PIL import Image
    with Image.open(io.BytesIO(blob)) as img:
        img.seek(getattr(img, "n_frames", 1) - 1)
        out = io.BytesIO()
        img.convert("RGBA").save(out, "PNG")
    return out.getvalue()


# ---------------------------------------------------------------- charts

def add_chart(slide, element, deck):
    spec = chart_spec(element)
    x, y, w, h = element.rect
    kind = spec.get("type", "column")
    data = CategoryChartData(number_format=spec.get("number_format", "General"))
    data.categories = spec["categories"]
    for series in spec["series"]:
        data.add_series(series.get("name", ""), series["values"])
    frame = slide.shapes.add_chart(CHART_TYPES[kind], emu(x), emu(y), emu(w), emu(h), data)
    frame.name = element.id
    chart = frame.chart
    style = element.style
    font_name = first_font(style.get("font-family")) or "Calibri"
    font_px = px(style.get("font-size"), 14)
    ink = to_hex(style.get("color") or "#333333")
    chart.font.name = font_name
    chart.font.size = pt(font_px)
    chart.font.color.rgb = RGBColor.from_string(ink)
    chart.has_title = bool(spec.get("title"))
    if spec.get("title"):
        chart.chart_title.text_frame.text = spec["title"]
    multi = len(spec["series"]) > 1 or kind in ("pie", "doughnut")
    chart.has_legend = spec.get("legend", multi)
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP if kind not in ("pie", "doughnut") else XL_LEGEND_POSITION.RIGHT
        chart.legend.include_in_layout = False
        chart.legend.font.size = pt(font_px)
    colors = spec.get("colors") or []
    plot = chart.plots[0]
    if kind in ("pie", "doughnut"):
        for i, point in enumerate(plot.series[0].points):
            if colors:
                point.format.fill.solid()
                point.format.fill.fore_color.rgb = RGBColor.from_string(colors[i % len(colors)])
                point.format.line.color.rgb = RGBColor.from_string(to_hex(spec.get("gap_color", "#FFFFFF")))
                point.format.line.width = Pt(1.5)
    else:
        if hasattr(plot, "gap_width"):
            plot.gap_width = spec.get("gap_width", 60)
        if kind.startswith("stacked") and hasattr(plot, "overlap"):
            plot.overlap = 100
        for i, series in enumerate(plot.series):
            color = RGBColor.from_string(colors[i % len(colors)]) if colors else None
            if kind == "line":
                series.format.line.width = Pt(2.25)
                series.smooth = False
                if color:
                    series.format.line.color.rgb = color
                    series.marker.format.fill.solid()
                    series.marker.format.fill.fore_color.rgb = color
                    series.marker.format.line.color.rgb = color
                series.marker.size = 7
            elif color:
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = color
        if spec.get("highlight") is not None and kind in ("column", "bar") and plot.series:
            n_points = len(spec["categories"])
            idx = n_points - 1 if spec["highlight"] == "last" else int(spec["highlight"])
            point = plot.series[0].points[idx]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = RGBColor.from_string(spec.get("highlight_color") or colors[-1])
        grid = to_hex(spec.get("grid_color", "#E5E7EB"))
        value_axis, category_axis = chart.value_axis, chart.category_axis
        value_axis.has_major_gridlines = spec.get("gridlines", True)
        if value_axis.has_major_gridlines:
            value_axis.major_gridlines.format.line.color.rgb = RGBColor.from_string(grid)
            value_axis.major_gridlines.format.line.width = Pt(0.75)
        value_axis.format.line.fill.background()
        category_axis.format.line.color.rgb = RGBColor.from_string(grid)
        category_axis.has_major_gridlines = False
        value_axis.visible = spec.get("value_axis", not spec.get("labels", False))
        for axis in (value_axis, category_axis):
            axis.tick_labels.font.size = pt(font_px)
            axis.tick_labels.font.color.rgb = RGBColor.from_string(ink)
        if spec.get("number_format"):
            value_axis.tick_labels.number_format = spec["number_format"]
            value_axis.tick_labels.number_format_is_linked = False
    if spec.get("labels"):
        plot.has_data_labels = True
        labels = plot.data_labels
        labels.font.size = pt(font_px)
        labels.font.color.rgb = RGBColor.from_string(to_hex(spec.get("label_color") or style.get("color") or "#333333"))
        labels.number_format = spec.get("number_format", "General")
        labels.number_format_is_linked = False
        if kind in ("column", "bar"):
            labels.position = XL_LABEL_POSITION.OUTSIDE_END
        elif kind.startswith("stacked"):
            labels.position = XL_LABEL_POSITION.CENTER
    return frame


# ---------------------------------------------------------------- tables

def add_table(slide, element, deck):
    x, y, w, h = element.rect
    rows = [r for r in element.node.iter() if r.tag == "tr"]
    grid = [[c for c in r.children if c.tag in ("td", "th")] for r in rows]
    ncols = max(len(r) for r in grid)
    frame = slide.shapes.add_table(len(grid), ncols, emu(x), emu(y), emu(w), emu(h))
    frame.name = element.id
    table = frame.table
    table.first_row = table.horz_banding = False
    tbl_pr = table._tbl.tblPr
    style_id = tbl_pr.find(qn("a:tableStyleId"))
    if style_id is not None:
        style_id.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"  # "No Style, Table Grid" base, overridden below
    cols = [c for c in element.node.iter() if c.tag == "col"]
    widths = [px(deck.style(c).get("width")) for c in cols] if len(cols) == ncols else [w / ncols] * ncols
    scale = w / sum(widths)
    for i, cw in enumerate(widths):
        table.columns[i].width = emu(cw * scale)
    for r, (row_node, cells) in enumerate(zip(rows, grid)):
        rstyle = deck.style(row_node)
        table.rows[r].height = emu(px(rstyle.get("height"), h / len(grid)))
        for c, cell_node in enumerate(cells):
            cell = table.cell(r, c)
            cstyle = dict(element.style)
            cstyle.update(rstyle)
            cstyle.update(deck.style(cell_node))
            if cell_node.tag == "th" and "font-weight" not in deck.style(cell_node):
                cstyle["font-weight"] = "700"
            cell.text_frame.text = ""
            apply_text(cell.text_frame, cstyle, paragraphs(cell_node, cstyle, deck))
            cell.margin_left = cell.margin_right = emu(px(cstyle.get("cell-padding-x"), 8))
            cell.margin_top = cell.margin_bottom = emu(px(cstyle.get("cell-padding-y"), 4))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            fill = to_hex(cstyle.get("background") or cstyle.get("background-color") or "transparent") \
                if (deck.style(cell_node).get("background") or rstyle.get("background")) else None
            if fill:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(fill)
            else:
                cell.fill.background()
            set_cell_borders(cell, cstyle.get("border-bottom"))
    return frame


def set_cell_borders(cell, bottom):
    tc_pr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        line = etree.SubElement(tc_pr, qn(tag))
        if tag == "a:lnB" and bottom and bottom != "none":
            parts = bottom.split()
            line.set("w", str(int(px(parts[0]) * EMU_PER_PX)))
            fill = etree.SubElement(line, qn("a:solidFill"))
            clr = etree.SubElement(fill, qn("a:srgbClr"))
            clr.set("val", to_hex(parts[-1]))
        else:
            line.set("w", "0")
            etree.SubElement(line, qn("a:noFill"))
    # tcPr children must precede fill elements in schema order: move borders to the front.
    for tag in ("a:lnB", "a:lnT", "a:lnR", "a:lnL"):
        node = tc_pr.find(qn(tag))
        tc_pr.remove(node)
        tc_pr.insert(0, node)


# ---------------------------------------------------------------- motion (python-pptx has no API)
# Native transitions and entrance builds. Vocabulary: deck_check.py, reference/motion.md
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main_convert"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main_convert"
P159_NS = "http://schemas.microsoft.com/office/powerpoint/2015/09/main_convert"


def _el(parent, tag, **attrs):
    node = etree.SubElement(parent, qn(tag))
    for key, value in attrs.items():
        node.set(key, str(value))
    return node


def add_transition(slide, kind, ms):
    """Insert <p:transition> (or an mc:AlternateContent for Morph with a Fade fallback)."""
    if kind in (None, "", "none"):
        return
    sld = slide._element
    ms = int(ms or (800 if kind == "morph" else 350))
    speed = "fast" if ms < 500 else "med" if ms < 1000 else "slow"
    anchor = sld.find(qn("p:clrMapOvr"))
    index = list(sld).index(anchor) + 1 if anchor is not None else len(sld)
    if kind == "morph":
        xml = (
            f'<mc:AlternateContent xmlns:mc="{MC_NS}" xmlns:p="{P_NS}">'
            f'<mc:Choice xmlns:p159="{P159_NS}" xmlns:p14="{P14_NS}" Requires="p159">'
            f'<p:transition spd="{speed}" p14:dur="{ms}"><p159:morph option="byObject"/></p:transition>'
            f'</mc:Choice><mc:Fallback><p:transition spd="{speed}"><p:fade/></p:transition></mc:Fallback>'
            f'</mc:AlternateContent>')
        sld.insert(index, etree.fromstring(xml))
        return
    transition = etree.Element(qn("p:transition"))
    transition.set("spd", speed)
    if kind == "fade":
        _el(transition, "p:fade")
    elif kind == "push":
        _el(transition, "p:push", dir="l")  # new slide pushes in from the right: forward = left-to-right reading
    sld.insert(index, transition)


class _Ids:
    def __init__(self):
        self.n = 0

    def next(self):
        self.n += 1
        return self.n


def _behavior(parent, ids, spid, dur, attr_names=None, **ctn_attrs):
    c_bhvr = _el(parent, "p:cBhvr")
    _el(c_bhvr, "p:cTn", id=ids.next(), dur=dur, **ctn_attrs)
    tgt = _el(c_bhvr, "p:tgtEl")
    _el(tgt, "p:spTgt", spid=spid)
    if attr_names:
        lst = _el(c_bhvr, "p:attrNameLst")
        for name in attr_names:
            _el(lst, "p:attrName").text = name
    return c_bhvr


def _effect(parent, ids, spid, anim, dur, delay, node_type):
    preset, subtype, filt, floats = ANIMS[anim]
    par = _el(parent, "p:par")
    ctn = _el(par, "p:cTn", id=ids.next(), presetID=preset, presetClass="entr", presetSubtype=subtype,
              fill="hold", grpId=0, nodeType=node_type)
    _el(_el(ctn, "p:stCondLst"), "p:cond", delay=delay)
    kids = _el(ctn, "p:childTnLst")
    show = _el(kids, "p:set")
    bhvr = _behavior(show, ids, spid, 1, ["style.visibility"], fill="hold")
    _el(_el(bhvr.find(qn("p:cTn")), "p:stCondLst"), "p:cond", delay=0)
    _el(_el(show, "p:to"), "p:strVal", val="visible")
    if filt:
        effect = _el(kids, "p:animEffect", transition="in", filter=filt)
        _behavior(effect, ids, spid, dur)
    if floats:  # small rise with deceleration (ease-out): never fly in from off-slide
        for attr, start in (("ppt_x", "#ppt_x"), ("ppt_y", "#ppt_y+0.03")):
            anim_node = _el(kids, "p:anim", calcmode="lin", valueType="num")
            _behavior(anim_node, ids, spid, dur, [attr], decel="100000")
            tav_lst = _el(anim_node, "p:tavLst")
            for tm, val in (("0", start), ("100000", "#" + attr)):
                tav = _el(tav_lst, "p:tav", tm=tm)
                _el(_el(tav, "p:val"), "p:strVal", val=val)


def _media_effect(parent, ids, spid, dur, delay, node_type):
    """Start a video (PowerPoint's 'mediacall' play command): plays from the start, then holds its last frame."""
    par = _el(parent, "p:par")
    ctn = _el(par, "p:cTn", id=ids.next(), presetID=1, presetClass="mediacall", presetSubtype=0, fill="hold",
              nodeType=node_type)
    _el(_el(ctn, "p:stCondLst"), "p:cond", delay=delay)
    cmd = _el(_el(ctn, "p:childTnLst"), "p:cmd", type="call", cmd="playFrom(0.0)")
    _behavior(cmd, ids, spid, dur, fill="hold")


def add_builds(slide, builds):
    """builds: list of dicts {spid, group, anim, duration, delay, is_sp[, media, loop]}. Groups play in ascending
    order; group 0 starts automatically after the slide transition, other groups wait for a click. Media entries
    start a video instead of revealing a shape; looping videos repeat until the slide ends."""
    if not builds:
        return
    sld = slide._element
    ids = _Ids()
    timing = etree.Element(qn("p:timing"))
    root_ctn = _el(_el(_el(timing, "p:tnLst"), "p:par"), "p:cTn", id=ids.next(), dur="indefinite",
                   restart="never", nodeType="tmRoot")
    seq = _el(_el(root_ctn, "p:childTnLst"), "p:seq", concurrent=1, nextAc="seek")
    main_ctn = _el(seq, "p:cTn", id=ids.next(), dur="indefinite", nodeType="mainSeq")
    main_kids = _el(main_ctn, "p:childTnLst")
    main_id = main_ctn.get("id")
    for group in sorted({b["group"] for b in builds}):
        members = [b for b in builds if b["group"] == group]
        outer = _el(_el(main_kids, "p:par"), "p:cTn", id=ids.next(), fill="hold")
        conds = _el(outer, "p:stCondLst")
        _el(conds, "p:cond", delay="indefinite")
        if group == 0:
            auto = _el(conds, "p:cond", evt="onBegin", delay="0")
            _el(auto, "p:tn", val=main_id)
        inner = _el(_el(_el(outer, "p:childTnLst"), "p:par"), "p:cTn", id=ids.next(), fill="hold")
        _el(_el(inner, "p:stCondLst"), "p:cond", delay="0")
        inner_kids = _el(inner, "p:childTnLst")
        for i, b in enumerate(members):
            node_type = ("afterEffect" if group == 0 else "clickEffect") if i == 0 else "withEffect"
            delay = b["delay"] if b["delay"] is not None else i * DEFAULT_STAGGER_MS
            if b.get("media"):
                _media_effect(inner_kids, ids, b["spid"], b["duration"], 0, node_type)
            else:
                _effect(inner_kids, ids, b["spid"], b["anim"], b["duration"], delay, node_type)
    prev = _el(_el(seq, "p:prevCondLst"), "p:cond", evt="onPrev", delay="0")
    _el(_el(prev, "p:tgtEl"), "p:sldTgt")
    nxt = _el(_el(seq, "p:nextCondLst"), "p:cond", evt="onNext", delay="0")
    _el(_el(nxt, "p:tgtEl"), "p:sldTgt")
    for b in builds:   # one media node per video: volume, muting, looping
        if not b.get("media"):
            continue
        node = _el(_el(seq.getparent(), "p:video"), "p:cMediaNode", vol=80000, mute=1)
        extra = {"repeatCount": "indefinite"} if b.get("loop") else {}
        ctn = _el(node, "p:cTn", id=ids.next(), fill="hold", display=0, **extra)
        _el(_el(ctn, "p:stCondLst"), "p:cond", delay="indefinite")
        _el(_el(node, "p:tgtEl"), "p:spTgt", spid=b["spid"])
    bld_lst = _el(timing, "p:bldLst")
    for b in builds:
        if b["is_sp"]:
            _el(bld_lst, "p:bldP", spid=b["spid"], grpId=0, animBg=1)
    if not len(bld_lst):
        timing.remove(bld_lst)
    ext = sld.find(qn("p:extLst"))
    if ext is not None:
        ext.addprevious(timing)
    else:
        sld.append(timing)


# ---------------------------------------------------------------- deck

def convert(html_path, pptx_path, motion_on=True):
    deck = Deck(html_path)
    prs = Presentation()
    prs.slide_width, prs.slide_height = emu(SLIDE_W), emu(SLIDE_H)
    prs.core_properties.title = deck.title
    blank = prs.slide_layouts[6]
    svg_jobs = {}
    for slide in deck.slides:
        for el in slide.elements:
            if el.kind == "image":
                blob, ext = deck.load_asset(el.node.get("src"))
                if ext == "svg":
                    svg_jobs[el.id] = blob
    raster_cache = rasterize_svgs(svg_jobs)
    if svg_jobs and len(raster_cache) < len(svg_jobs):
        print(f"WARN: {len(svg_jobs) - len(raster_cache)} SVG image(s) have no PNG fallback; they show only in "
              "PowerPoint 365 (no LibreOffice, CairoSVG or Chrome available to rasterize them).")
    for slide in deck.slides:
        out = prs.slides.add_slide(blank)
        bg = to_hex(slide.background) if slide.background else None
        if bg:
            out.background.fill.solid()
            out.background.fill.fore_color.rgb = RGBColor.from_string(bg)
        builds = []
        for el in slide.elements:
            if el.kind == "text":
                shape = add_textbox(out, el, deck)
            elif el.kind == "shape":
                shape = add_shape(out, el, deck)
            elif el.kind == "image":
                shape = add_image(out, el, deck, raster_cache, motion_on)
            elif el.kind == "video":
                shape = add_video(out, el, deck, motion_on)
            elif el.kind == "chart":
                shape = add_chart(out, el, deck)
            else:
                shape = add_table(out, el, deck)
            if el.node.get("data-morph"):
                shape.name = "!!" + el.node.get("data-morph")  # '!!' forces Morph to pair same-named objects
            if el.kind == "video":
                if motion_on:
                    path = os.path.join(deck.base_dir, urllib.parse.unquote(el.node.get("src")))
                    click = el.node.get("data-play", "auto") == "click"
                    builds.append({"spid": shape.shape_id, "media": True, "loop": "loop" in el.node.attrs,
                                   "group": int(el.node.get("data-build") or 1) if click else 0,
                                   "duration": mp4_duration_ms(path) or 5000, "delay": 0, "is_sp": False})
            elif el.node.get("data-build") is not None:
                builds.append({
                    "spid": shape.shape_id, "group": int(el.node.get("data-build")),
                    "anim": el.node.get("data-anim", DEFAULT_ANIM),
                    "duration": int(el.node.get("data-duration", DEFAULT_MS)),
                    "delay": int(el.node.get("data-delay")) if el.node.get("data-delay") else None,
                    "is_sp": el.kind in ("text", "shape"),
                })
        if motion_on:
            add_transition(out, slide.node.get("data-transition"), slide.node.get("data-transition-ms"))
            add_builds(out, builds)
        if slide.notes:
            out.notes_slide.notes_text_frame.text = slide.notes
    prs.save(pptx_path)
    return len(deck.slides)


def verify_package(pptx_path):
    """Open every part of the saved package the way PowerPoint will: XML must parse, every
    relationship target must exist, and every image must decode. Returns a list of problems."""
    import posixpath
    import zipfile
    problems = []
    with zipfile.ZipFile(pptx_path) as z:
        if z.testzip() is not None:
            return ["zip archive is corrupt"]
        names = set(z.namelist())
        for name in sorted(names):
            data = z.read(name)
            if name.endswith((".xml", ".rels", ".svg")):
                try:
                    root = etree.fromstring(data)
                except etree.XMLSyntaxError as exc:
                    problems.append(f"{name}: XML does not parse ({exc})")
                    continue
                if name.endswith(".rels"):
                    base = posixpath.dirname(posixpath.dirname(name))
                    for rel in root:
                        if rel.get("TargetMode") == "External":
                            continue
                        target = posixpath.normpath(posixpath.join(base, rel.get("Target"))).lstrip("/")
                        if target not in names:
                            problems.append(f"{name}: relationship target missing: {target}")
            elif name.startswith("ppt/media/") and name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff")):
                try:
                    from PIL import Image
                    with Image.open(io.BytesIO(data)) as img:
                        img.load()
                except ImportError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"{name}: image does not decode ({exc})")
    return problems


def main_convert():
    if _PPTX_MISSING:
        sys.exit(f"python-pptx is required for conversion ({_PPTX_MISSING})")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    html_path, pptx_path = args
    errors, warnings = run_checks(html_path)
    print_report(errors, warnings)
    if errors and "--force" not in sys.argv:
        print("Stopped: fix the errors above (or pass --force).")
        sys.exit(1)
    count = convert(html_path, pptx_path, motion_on="--no-motion" not in sys.argv)
    problems = verify_package(pptx_path)
    for problem in problems:
        print("ERROR package:", problem)
    if problems:
        print(f"Wrote {pptx_path}, but it will not open cleanly in PowerPoint; fix the errors above.")
        sys.exit(1)
    print(f"Wrote {pptx_path} ({count} slides, package verified)")

