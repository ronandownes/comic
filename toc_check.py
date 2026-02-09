#!/usr/bin/env python3
"""Diagnose toc.txt page refs vs actual capture files.
Run from E:\comic — outputs toc_check.txt"""
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"E:\comic")
PAGES = ROOT / "pages"

# Count actual files per chapter
chapter_files = defaultdict(list)
for f in sorted(PAGES.glob("*.webp")):
    parts = f.stem.split("-")
    if len(parts) == 3:
        key = f"{parts[0]}-{parts[1]}"  # e.g. "1-01"
        chapter_files[key].append(int(parts[2]))

# Parse toc.txt
lines = []
cur_book = cur_ch = None
sections = []

for raw in (ROOT / "toc.txt").read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    parts = [p.strip() for p in line.split("|")]
    if parts[0].upper().startswith("BOOK"):
        cur_book = int(parts[0].split()[1])
    elif parts[0].upper().startswith("CH"):
        cur_ch = int(parts[0].split()[1])
    elif cur_ch and parts[0].isdigit():
        pg = int(parts[0])
        name = parts[1] if len(parts) > 1 else ""
        key = f"{cur_book}-{cur_ch:02d}"
        ref = f"{cur_book}-{cur_ch:02d}-{pg:02d}"
        actual = chapter_files.get(key, [])
        max_pg = max(actual) if actual else 0
        exists = pg in actual
        sections.append((key, pg, name, len(actual), max_pg, exists, ref))

# Report
out = []
out.append("TOC CHECK — toc.txt refs vs actual capture files")
out.append("=" * 75)
out.append("")

# Summary per chapter
prev_key = None
for key, pg, name, count, mx, exists, ref in sections:
    if key != prev_key:
        actual = chapter_files.get(key, [])
        out.append(f"\n  {key}  ({count} captures, files 01–{mx:02d})")
        prev_key = key
    flag = "  ✓" if exists else f"  ✗ MISSING (max is {mx:02d})"
    out.append(f"    {ref}  {name:<35}{flag}")

# Stats
total = len(sections)
ok = sum(1 for s in sections if s[5])
bad = total - ok
out.append(f"\n{'=' * 75}")
out.append(f"  {total} section refs: {ok} exist, {bad} MISSING")
out.append("")

# Show chapter file counts
out.append("CAPTURES PER CHAPTER:")
for key in sorted(chapter_files.keys()):
    files = chapter_files[key]
    out.append(f"  {key}  {len(files):3d} files  (01–{max(files):02d})")

report = "\n".join(out)
print(report)
(ROOT / "toc_check.txt").write_text(report, encoding="utf-8")
print(f"\nSaved to {ROOT / 'toc_check.txt'}")
