#!/usr/bin/env python3
"""Read-only inventory of the Cowork execution sandbox.

Reports the Python version, installed packages, command-line tools, fonts, and
writable paths, so skills can be designed around what actually exists.
Uses only the standard library. Makes no network calls and changes nothing,
except writing the report to the path given with --out.

Usage: python3 probe_env.py [--out report.md]
"""
import importlib.metadata as md
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import tempfile

# Python packages relevant to building documents, slides, and images.
PY_MODULES = [
    ("pptx", "python-pptx"), ("docx", "python-docx"), ("openpyxl", "openpyxl"),
    ("lxml", "lxml"), ("defusedxml", "defusedxml"), ("PIL", "Pillow"),
    ("cairosvg", "CairoSVG"), ("svglib", "svglib"), ("reportlab", "reportlab"),
    ("matplotlib", "matplotlib"), ("plotly", "plotly"), ("kaleido", "kaleido"),
    ("pandas", "pandas"), ("numpy", "numpy"), ("bs4", "beautifulsoup4"),
    ("html5lib", "html5lib"), ("markdown", "Markdown"), ("markitdown", "markitdown"),
    ("playwright", "playwright"), ("selenium", "selenium"), ("weasyprint", "weasyprint"),
    ("fitz", "PyMuPDF"), ("pypdf", "pypdf"), ("pdfplumber", "pdfplumber"),
    ("fontTools", "fonttools"), ("requests", "requests"),
]
# Command-line tools relevant to rendering and conversion.
COMMANDS = [
    "node", "npm", "npx", "soffice", "libreoffice", "pdftoppm", "rsvg-convert",
    "inkscape", "convert", "magick", "chromium", "chromium-browser", "google-chrome",
    "fc-list", "markitdown", "pandoc", "dotnet", "pwsh", "git", "pip", "pip3",
]
NODE_PACKAGES = ["pptxgenjs", "playwright", "puppeteer", "sharp", "react-icons", "html2pptx"]


def run(args, timeout=20):
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or out.stderr).strip()
    except Exception as exc:  # report, never crash the probe
        return f"error: {exc.__class__.__name__}"


def py_modules():
    rows = []
    for module, dist in PY_MODULES:
        if importlib.util.find_spec(module) is None:
            rows.append((dist, "missing"))
            continue
        try:
            rows.append((dist, md.version(dist)))
        except md.PackageNotFoundError:
            rows.append((dist, "present (version unknown)"))
    return rows


def commands():
    rows = []
    for cmd in COMMANDS:
        path = shutil.which(cmd)
        if not path:
            rows.append((cmd, "missing", ""))
            continue
        version = run([cmd, "--version"]).splitlines()
        rows.append((cmd, path, version[0][:80] if version else ""))
    return rows


def node_packages():
    if not shutil.which("node"):
        return []
    rows = []
    for pkg in NODE_PACKAGES:
        script = f"try{{console.log(require('{pkg}/package.json').version)}}catch(e){{console.log('missing')}}"
        rows.append((pkg, run(["node", "-e", script])))
    global_root = run(["npm", "root", "-g"]) if shutil.which("npm") else ""
    if global_root and os.path.isdir(global_root):
        rows.append(("(npm global root)", global_root))
        rows.append(("(global packages)", ", ".join(sorted(os.listdir(global_root))[:60])))
    return rows


def fonts():
    if shutil.which("fc-list"):
        families = set()
        for line in run(["fc-list", ":", "family"]).splitlines():
            families.update(f.strip() for f in line.split(","))
        return sorted(f for f in families if f)
    found = set()
    for root in ("/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")):
        for dp, _, fs in os.walk(root):
            found.update(os.path.splitext(f)[0] for f in fs if f.lower().endswith((".ttf", ".otf")))
    return sorted(found)


def paths():
    rows = [("cwd", os.getcwd()), ("home", os.path.expanduser("~")), ("tempdir", tempfile.gettempdir()),
            ("script dir", os.path.dirname(os.path.abspath(__file__)))]
    for candidate in ("/mnt", "/mnt/data", "/mnt/user-data", "/workspace", "/home", "/tmp", "/data", "/output", "/outputs"):
        if os.path.isdir(candidate):
            rows.append((candidate, f"exists, writable={os.access(candidate, os.W_OK)}, entries={sorted(os.listdir(candidate))[:15]}"))
    return rows


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(lines)


def main():
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    font_list = fonts()
    report = "\n\n".join([
        "# Cowork environment probe",
        table(["Item", "Value"], [
            ("python", sys.version.split()[0]), ("executable", sys.executable),
            ("platform", platform.platform()), ("machine", platform.machine()),
            ("cpu count", os.cpu_count()),
        ]),
        "## Python packages\n" + table(["Package", "Version"], py_modules()),
        "## Commands\n" + table(["Command", "Path", "Version"], commands()),
        "## Node packages\n" + (table(["Package", "Version"], node_packages()) if shutil.which("node") else "node not installed"),
        f"## Fonts ({len(font_list)} families)\n" + (", ".join(font_list[:200]) or "none found"),
        "## Paths\n" + table(["Path", "Details"], paths()),
    ]) + "\n"
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(report)
    print(report)


if __name__ == "__main__":
    main()
