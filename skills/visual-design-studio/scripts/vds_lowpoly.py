"""Low-poly 3D scenes rendered in Python, for decks and documents (PowerPoint can't run the canvas JavaScript).

Run through vds.py:
  python3 scripts/vds.py lowpoly <scene> <out-base> [--formats png,mp4,gif] [--size 960x720] [--fps 30]
                                 [--bg #hex] [--tokens deck.html|tokens.css] [--color key=#hex ...] [--at seconds]

Scenes are a port of examples/motion-lowpoly.html (the same geometry, timing and shading), so a web page
and a deck show the same object: globe, turbine and cabinet are loops; package and coin are one-shots.
Outputs:
  <out-base>.png  the poster: a meaningful still frame (the end state for one-shots). Used by --no-motion
                  decks, PDFs and as the video's poster frame.
  <out-base>.mp4  H.264, one seamless cycle for loops, or the one-shot plus a 1 s hold (needs ffmpeg).
  <out-base>.gif  for short one-shots only: plays once and stops on the end frame.
Colors come from --tokens (the CSS custom properties in a page or deck: --accent, --surface, --sea, …),
then --color overrides. Needs Pillow; MP4 needs ffmpeg (both are in Copilot Cowork).
"""
import math
import os
import re
import shutil
import subprocess
import sys

DEFAULT_COLORS = {
    "surface": "#FAFBFB", "accent": "#2F51A3", "ink": "#1E2327",
    "sea": "#3E64B8", "land": "#6E9B6A", "ice": "#E8EEF3",
    "card": "#C9A26B", "card-dark": "#A9824E", "gold": "#E3A93B", "gold-face": "#F2C766",
    "cab-body": "#6A4630", "cab-dark": "#2A1E17", "cab-side": "#3E2C21", "cab-screen": "#120D0A", "felt": "#6FA89A",
}


# ---------------------------------------------------------------- engine (same as the JavaScript one)

def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    length = math.sqrt(dot(a, a)) or 1
    return (a[0] / length, a[1] / length, a[2] / length)


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def rot_x(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


def rot_z(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def hex_rgb(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, k, base):
    f = base + (1 - base) * k
    return tuple(round(c * f) for c in rgb)


def ease_out(t):
    return 1 - (1 - min(max(t, 0), 1)) ** 3


def face(pts, color, two_sided=False, glow=False, bias=0.0):
    return {"pts": pts, "color": color, "two": two_sided, "glow": glow, "bias": bias}


def quad(a, b, c, d, color, two_sided=False):
    return face([a, b, c, d], color, two_sided)


def box(cx, cy, cz, sx, sy, sz, color, bias=0.0):
    x0, x1, y0, y1, z0, z1 = cx - sx, cx + sx, cy - sy, cy + sy, cz - sz, cz + sz
    quads = [[(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], [(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)],
             [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], [(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)],
             [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]]
    return [face(q, color, bias=bias) for q in quads]


def render(draw, w, h, faces, framing, ss, light, shade_base, cull=True):
    dist = framing.get("dist", 6)
    unit = min(w, h) / 2 * framing.get("fill", 0.85) / framing.get("radius", 1.5)
    cy = h * framing.get("cy", 0.5)
    drawn = []
    for f in faces:
        p = f["pts"]
        n = norm(cross(sub(p[1], p[0]), sub(p[2], p[0])))
        c = tuple(sum(q[i] for q in p) / len(p) for i in range(3))
        to_cam = norm(sub((0, 0, dist), c))
        facing = dot(n, to_cam)
        if cull and not f["two"] and facing <= 0:
            continue
        if facing < 0:
            n = (-n[0], -n[1], -n[2])
        drawn.append((c[2] + f["bias"], f, max(0.0, dot(n, light))))
    drawn.sort(key=lambda d: d[0])
    for _, f, lum in drawn:
        pts = []
        for q in f["pts"]:
            k = dist / (dist - q[2])
            pts.append(((w / 2 + q[0] * k * unit) * ss, (cy - q[1] * k * unit) * ss))
        rgb = f["color"] if f["glow"] else shade(f["color"], lum, shade_base)
        draw.polygon(pts, fill=rgb, outline=rgb)


# ---------------------------------------------------------------- scenes (ported from motion-lowpoly.html)

def icosphere(subdiv):
    t = (1 + math.sqrt(5)) / 2
    v = [norm(p) for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                           (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdiv):
        nf, mid = [], {}

        def m(a, b):
            key = (min(a, b), max(a, b))
            if key not in mid:
                v.append(norm(tuple((v[a][i] + v[b][i]) / 2 for i in range(3))))
                mid[key] = len(v) - 1
            return mid[key]
        for a0, b0, c0 in f:
            a, b, c = m(a0, b0), m(b0, c0), m(c0, a0)
            nf += [(a0, a, c), (b0, b, a), (c0, c, b), (a, b, c)]
        f = nf
    return v, f


SPHERE = icosphere(2)


def _landmask():
    v, f = SPHERE
    out = []
    for tri in f:
        c = norm(tuple(sum(v[i][k] for i in tri) for k in range(3)))
        h = math.sin(c[0] * 3.1 + 1.2) * math.cos(c[2] * 2.7 - 0.4) + 0.6 * math.sin(c[1] * 4.3 + c[0] * 1.7)
        out.append("ice" if abs(c[1]) > 0.88 else ("land" if h > 0.05 else "sea"))
    return out


LANDMASK = _landmask()


def scene_globe(t, col):
    a, tilt = t * (math.pi * 2 / 24), -0.41
    v, f = SPHERE
    return [face([rot_x(rot_y(tuple(x * 1.45 for x in v[k]), a), tilt) for k in tri], col[LANDMASK[i]])
            for i, tri in enumerate(f)]


def scene_package(t, col):
    card, inside, gold = col["card"], col["card-dark"], col["gold"]
    opening, rise = ease_out(t / 1.1), ease_out((t - 0.7) / 0.9)
    s, hgt = 0.8, 0.65
    faces = [q for i, q in enumerate(box(0, 0, 0, s, hgt, s, card)) if i != 4]
    faces.append(quad((-s, -hgt + 0.01, -s), (s, -hgt + 0.01, -s), (s, -hgt + 0.01, s), (-s, -hgt + 0.01, s), inside, True))
    for k, edge in enumerate((0, math.pi, math.pi / 2, -math.pi / 2)):
        ang = opening * (2.1 if k < 2 else 1.95)
        flap = []
        for q in ((-s, 0, 0), (s, 0, 0), (s, 0, -s * 0.96), (-s, 0, -s * 0.96)):
            r = rot_x(q, ang)
            r = rot_y((r[0], r[1], r[2] + s), edge)
            flap.append((r[0], r[1] + hgt, r[2]))
        faces.append(face(flap, card if k < 2 else inside, True))
    if rise > 0:
        y, r, spin = -0.2 + rise * 1.45, 0.38, t * 1.6
        top, bot = (0, y + r * 1.3, 0), (0, y - r * 1.3, 0)
        ring = [(math.cos(spin + i * math.pi / 2) * r, y, math.sin(spin + i * math.pi / 2) * r) for i in range(4)]
        for i in range(4):
            a1, b1 = ring[i], ring[(i + 1) % 4]
            faces += [face([top, b1, a1], gold), face([bot, a1, b1], gold)]
    return [dict(f, pts=[rot_x(rot_y(p, -0.6), 0.42) for p in f["pts"]]) for f in faces]


def scene_turbine(t, col):
    ink, accent = col["ice"], col["accent"]
    faces = box(0, -0.55, 0, 0.07, 1.05, 0.07, ink) + box(0, 0.55, 0.05, 0.12, 0.1, 0.22, ink)
    a = t * 1.8
    for b in range(3):
        ang = a + b * math.pi * 2 / 3
        blade = [(0, 0.06, 0.28), (0.05, 1.1, 0.29), (-0.03, 1.1, 0.27), (-0.09, 0.08, 0.27)]
        pts = [(q[0], q[1] + 0.55, q[2]) for q in (rot_z(p, ang) for p in blade)]
        faces.append(face(pts, accent if b == 0 else ink, True))
    faces += box(0, 0.55, 0.29, 0.07, 0.07, 0.03, accent)
    return [dict(f, pts=[rot_x(rot_y(p, -0.5), 0.12) for p in f["pts"]]) for f in faces]


def scene_coin(t, col):
    gold, edge = col["gold"], col["card-dark"]
    u = ease_out(t / 1.2)
    flip, y = u * math.pi * 4, math.sin(min(t / 1.2, 1) * math.pi) * 0.7 - 0.1
    n, r, th = 14, 0.75, 0.09
    faces, front, back = [], [], []
    for i in range(n):
        a, a2 = i / n * math.pi * 2, (i + 1) / n * math.pi * 2
        front.append((math.cos(a) * r, math.sin(a) * r, th))
        back.insert(0, (math.cos(a) * r, math.sin(a) * r, -th))
        faces.append(quad((math.cos(a) * r, math.sin(a) * r, -th), (math.cos(a2) * r, math.sin(a2) * r, -th),
                          (math.cos(a2) * r, math.sin(a2) * r, th), (math.cos(a) * r, math.sin(a) * r, th), edge))
    faces += [face(front, gold), face(back, gold)]
    faces.append(face([(math.cos(j / n * math.pi * 2) * r * 0.62, math.sin(j / n * math.pi * 2) * r * 0.62, th + 0.02)
                       for j in range(n)], col["gold-face"]))

    def place(p):
        q = rot_x(p, flip)
        return rot_x((q[0], q[1] + y, q[2]), 0.35)
    return [dict(f, pts=[place(p) for p in f["pts"]]) for f in faces]


CAB_PROFILE = [(0.42, -1.6), (0.42, -0.78), (0.72, -0.66), (0.72, -0.56), (0.40, -0.44), (0.30, -0.40),
               (0.10, 0.52), (0.44, 0.58), (0.44, 1.02), (-0.50, 1.02), (-0.50, -1.6)]
CAB_EDGES = ["cab-body", "cab-dark", "cab-dark", "cab-dark", "cab-dark", "cab-screen", "cab-dark", "accent",
             "cab-body", "cab-body", "cab-body"]


def scene_cabinet(t, col):
    """A 1981 upright arcade cabinet (from the Copper Comet page), swaying over a 14 s cycle."""
    sway = -0.6 + 0.38 * math.sin(t * math.pi * 2 / 14)
    P, hw, faces = CAB_PROFILE, 0.5, []
    for i, a in enumerate(P):
        b = P[(i + 1) % len(P)]
        key = CAB_EDGES[i]
        faces.append(face([(-hw, a[1], a[0]), (hw, a[1], a[0]), (hw, b[1], b[0]), (-hw, b[1], b[0])], col[key],
                          True, glow=key == "accent"))
    sides = []
    for s in (-1, 1):
        x, xo = s * hw, s * (hw + 0.004)
        sides.append((s, 0.0, face([(x, p[1], p[0]) for p in P], col["cab-side"], True)))
        sides.append((s, 0.5, face([(xo, -1.25, -0.42), (xo, -1.25, -0.26), (xo, 0.95, 0.36), (xo, 0.95, 0.2)], col["accent"], True)))
    sa, sb = P[5], P[6]

    def on_screen(u, x0, x1, th):
        def p(v): return (sa[0] + (sb[0] - sa[0]) * v + 0.01, sa[1] + (sb[1] - sa[1]) * v)
        a, b = p(u), p(u + th)
        return face([(x0, a[1], a[0]), (x1, a[1], a[0]), (x1, b[1], b[0]), (x0, b[1], b[0])], col["accent"], True, True, 0.05)
    faces += [on_screen(0.78, -0.3, 0.3, 0.05), on_screen(0.6, -0.34, 0.12, 0.035), on_screen(0.5, -0.34, 0.2, 0.035),
              on_screen(0.4, -0.34, 0.04, 0.035), on_screen(0.3, -0.34, 0.16, 0.035)]
    for x in (-0.12, 0.12):
        faces.append(face([(x - 0.05, -1.05, 0.43), (x + 0.05, -1.05, 0.43), (x + 0.05, -0.9, 0.43), (x - 0.05, -0.9, 0.43)],
                          col["accent"], True, True, 0.05))

    def py(z): return -0.56 + (0.72 - z) / 0.32 * 0.12
    faces += box(-0.24, py(0.6) + 0.07, 0.6, 0.015, 0.07, 0.015, col["cab-dark"], 0.1)
    faces += box(-0.24, py(0.6) + 0.15, 0.6, 0.045, 0.04, 0.045, col["felt"], 0.12)
    for n, x in enumerate((0.02, 0.14, 0.26)):
        faces += box(x, py(0.6 - n * 0.02) + 0.015, 0.6 - n * 0.02, 0.04, 0.015, 0.04, col["accent"], 0.1)

    def place(p): return rot_x(rot_y(p, sway), 0.2)
    out = [dict(f, pts=[place(p) for p in f["pts"]]) for f in faces]
    near = rot_y((1, 0, 0), sway)[2]
    for s, extra, f in sides:   # the near side panel is drawn last, the far one first
        out.append(dict(f, pts=[place(p) for p in f["pts"]], bias=(10 if s * near > 0 else -10) + extra))
    return out


# kind, cycle or end time (s), poster time, framing, light, shade base, back-face culling
SCENES = {
    "globe":   (scene_globe, "loop", 24.0, 3.0, {"radius": 1.55, "fill": 0.9}, (-0.5, 0.8, 0.9), 0.45, True),
    "turbine": (scene_turbine, "loop", 2 * math.pi / 1.8, 0.4, {"radius": 1.75}, (-0.5, 0.8, 0.9), 0.45, True),
    "cabinet": (scene_cabinet, "loop", 14.0, 0.0, {"radius": 1.55, "fill": 1.0, "dist": 7}, (0.6, 0.7, 0.9), 0.5, False),
    "package": (scene_package, "oneshot", 1.9, 1.9, {"radius": 1.9, "cy": 0.56}, (-0.5, 0.8, 0.9), 0.45, True),
    "coin":    (scene_coin, "oneshot", 1.3, 1.3, {"radius": 1.2}, (-0.5, 0.8, 0.9), 0.45, True),
}


# ---------------------------------------------------------------- output

def frame_image(scene, t, size, colors, bg, ss=3):
    from PIL import Image, ImageDraw
    fn, _, _, _, framing, light, base, cull = SCENES[scene]
    w, h = size
    mode, fill = ("RGBA", (0, 0, 0, 0)) if bg is None else ("RGB", bg)
    img = Image.new(mode, (w * ss, h * ss), fill)
    render(ImageDraw.Draw(img), w, h, fn(t, colors), framing, ss, norm(light), base, cull)
    return img.resize((w, h), Image.LANCZOS)


def read_tokens(path):
    """CSS custom properties (hex values only) from the :root blocks of a page, deck or tokens.css."""
    with open(path, encoding="utf-8") as fh:
        css = fh.read()
    out = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", css):   # first (light) definition wins
        for name, value in re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", block):
            out.setdefault(name, value[:7])
    return out


def timeline(scene, fps):
    _, kind, length, _, _, _, _, _ = SCENES[scene]
    if kind == "loop":   # one seamless cycle: frame n == frame 0, so stop one frame short
        n = max(1, round(length * fps))
        return [i * length / n for i in range(n)], kind, length
    n = max(1, round(length * fps))
    times = [min(i / fps, length) for i in range(n + 1)]
    return times + [length] * fps, kind, length   # hold the end state for 1 s


def write_mp4(scene, out, size, colors, bg, fps):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found; make the PNG and GIF only (--formats png,gif)")
    w, h = size
    times, _, _ = timeline(scene, fps)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
           "-i", "-", "-an", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    for codec in (["-c:v", "libx264", "-crf", "20", "-preset", "medium"], ["-c:v", "mpeg4", "-q:v", "3"]):
        proc = subprocess.Popen(cmd + codec + [out], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for t in times:
                proc.stdin.write(frame_image(scene, t, size, colors, bg).tobytes())
            proc.stdin.close()
        except BrokenPipeError:
            pass
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() == 0:
            return len(times) / fps
        print(f"WARN: {codec[1]} failed ({err.strip()[:120]}); trying the next encoder")
    raise RuntimeError("ffmpeg could not encode the video")


def write_gif(scene, out, size, colors, bg, fps):
    fps = min(fps, 25)
    times, kind, _ = timeline(scene, fps)
    if kind == "oneshot":
        times = times[:len(times) - fps + 1]   # the GIF's last frame holds by itself
    frames = [frame_image(scene, t, size, colors, bg).convert("P", palette=1, colors=128) for t in times]
    durations = [round(1000 / fps)] * len(frames)
    extra = {"loop": 0} if kind == "loop" else {}   # no loop block: plays once and stops on the last frame
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, disposal=1, optimize=False, **extra)
    if kind == "loop":
        print("WARN: a looping GIF has no pause control; in a deck use the MP4 (PowerPoint shows video controls)")


def main_lowpoly():
    args, opts, colors_cli = [], {}, {}
    it = iter(sys.argv[1:])
    for a in it:
        if a == "--color":
            k, _, v = next(it).partition("=")
            colors_cli[k.lstrip("-")] = v
        elif a.startswith("--"):
            opts[a[2:]] = next(it)
        else:
            args.append(a)
    if len(args) != 2 or args[0] not in SCENES:
        print(__doc__)
        print("scenes:", ", ".join(SCENES))
        sys.exit(2)
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("Pillow is required for lowpoly")
    scene, base = args
    colors = dict(DEFAULT_COLORS)
    if opts.get("tokens"):
        colors.update(read_tokens(opts["tokens"]))
    colors.update(colors_cli)
    rgb = {k: hex_rgb(v) for k, v in colors.items()}
    w, h = (int(v) for v in opts.get("size", "960x720").lower().split("x"))
    w, h = w - w % 2, h - h % 2   # H.264 needs even sizes
    fps = int(opts.get("fps", 30))
    bg_opt = opts.get("bg", colors.get("surface"))
    bg = None if bg_opt == "transparent" else hex_rgb(bg_opt)
    formats = [f.strip() for f in opts.get("formats", "png,mp4").split(",") if f.strip()]
    _, kind, length, poster_t, *_ = SCENES[scene]
    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)
    if "png" in formats:
        t = float(opts["at"]) if "at" in opts else poster_t
        frame_image(scene, t, (w, h), rgb, bg).save(base + ".png")
        print(f"Wrote {base}.png (poster at {t:.2f} s)")
    if "mp4" in formats or "gif" in formats:
        if bg is None:
            sys.exit("video and GIF need a solid --bg (use the slide's background token)")
    if "mp4" in formats:
        secs = write_mp4(scene, base + ".mp4", (w, h), rgb, bg, fps)
        print(f"Wrote {base}.mp4 ({secs:.1f} s, {'seamless loop' if kind == 'loop' else 'plays once, holds the end'})")
    if "gif" in formats:
        write_gif(scene, base + ".gif", (w, h), rgb, bg, fps)
        print(f"Wrote {base}.gif ({'loops' if kind == 'loop' else 'plays once'})")
