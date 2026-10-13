#!/usr/bin/env python3
"""Sync shared files into each skill, validate, and package upload-ready zips.

Usage: python3 tools/build.py          # sync + validate + zip into dist/
       python3 tools/build.py --check  # validate only; fail if shared copies are stale
"""
import os, re, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS, SHARED, DIST = (os.path.join(ROOT, d) for d in ("skills", "shared", "dist"))
SUBFOLDERS = ("template", "scripts", "reference", "examples")
SHARED_PREFIX = "cycle-"  # shared/ files are synced only into the cycle-* suite
NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
REF_RE = re.compile(r"`((?:template|scripts|reference|examples)/[^`\s]+)`")
MD_LIMIT, ZIP_LIMIT, MAX_FILES = 1_000_000, 10_000_000, 21  # Cowork: 1 MB SKILL.md, 10 MB/skill, SKILL.md + 20 companion files


def shippable(dirpath, fname):
    """Exclude dotfiles and Python bytecode caches from validation and packaging."""
    return not fname.startswith(".") and "__pycache__" not in dirpath and not fname.endswith(".pyc")


def skill_dirs():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def sync(check_only):
    """Copy shared/<sub>/* into every cycle-* skill's <sub>/. Returns list of stale paths."""
    stale = []
    for sub in SUBFOLDERS:
        src_dir = os.path.join(SHARED, sub)
        if not os.path.isdir(src_dir):
            continue
        for fname in os.listdir(src_dir):
            src = os.path.join(src_dir, fname)
            for skill in skill_dirs():
                if not skill.startswith(SHARED_PREFIX):
                    continue
                dst = os.path.join(SKILLS, skill, sub, fname)
                if os.path.exists(dst) and open(src, "rb").read() == open(dst, "rb").read():
                    continue
                stale.append(os.path.relpath(dst, ROOT))
                if not check_only:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
    return stale


def validate(skill):
    errors, base = [], os.path.join(SKILLS, skill)
    text = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not fm:
        return ["missing YAML frontmatter"]
    name = re.search(r"^name:\s*(\S+)\s*$", fm.group(1), re.M)
    if not name or name.group(1) != skill or not NAME_RE.fullmatch(skill):
        errors.append("name must be kebab-case and match folder")
    if not re.search(r"^description:", fm.group(1), re.M):
        errors.append("missing description")
    if len(text.encode()) > MD_LIMIT:
        errors.append("SKILL.md over 1 MB")
    for ref in REF_RE.findall(text):
        if not os.path.isfile(os.path.join(base, ref)):
            errors.append(f"referenced file missing: {ref}")
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(base) for f in fs if shippable(dp, f)]
    if len(files) > MAX_FILES:
        errors.append(f"{len(files)} files exceeds {MAX_FILES}")
    for f in files:
        rel = os.path.relpath(f, base)
        if rel != "SKILL.md" and rel.split(os.sep)[0] not in SUBFOLDERS:
            errors.append(f"unexpected location: {rel} (use template/, scripts/, reference/ or examples/)")
    return errors


def package(skill):
    base = os.path.join(SKILLS, skill)
    out = os.path.join(DIST, f"{skill}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(base):
            for f in sorted(fs):
                if shippable(dp, f):
                    path = os.path.join(dp, f)
                    z.write(path, os.path.relpath(path, base))  # SKILL.md at zip root
    if os.path.getsize(out) > ZIP_LIMIT:
        raise SystemExit(f"{out} exceeds 10 MB")
    return out


def main():
    check_only = "--check" in sys.argv
    stale = sync(check_only)
    failed = False
    if check_only and stale:
        failed = True
        print("stale shared copies (run without --check):", *stale, sep="\n  ")
    for skill in skill_dirs():
        errs = validate(skill)
        failed |= bool(errs)
        print(f"{'FAIL' if errs else 'ok  '} {skill}", *[f"\n     - {e}" for e in errs])
    if failed:
        sys.exit(1)
    if not check_only:
        shutil.rmtree(DIST, ignore_errors=True)
        os.makedirs(DIST)
        for skill in skill_dirs():
            print("packaged", os.path.relpath(package(skill), ROOT))


if __name__ == "__main__":
    main()
