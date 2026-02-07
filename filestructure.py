#!/usr/bin/env python3
"""Show folder structure - writes to structure.txt"""
import sys
from pathlib import Path

lines = []

def show_structure(folder, prefix="", max_files=10):
    folder = Path(folder)
    items = sorted(folder.iterdir())
    dirs = [i for i in items if i.is_dir()]
    files = [i for i in items if i.is_file()]
    
    # Show files (limit per folder)
    for f in files[:max_files]:
        lines.append(f"{prefix}{f.name}")
    if len(files) > max_files:
        lines.append(f"{prefix}... and {len(files) - max_files} more files")
    
    # Recurse into dirs
    for d in dirs:
        lines.append(f"{prefix}{d.name}/")
        show_structure(d, prefix + "  ", max_files)

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    lines.append(f"{folder}/")
    show_structure(folder)
    Path("structure.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote structure.txt ({len(lines)} lines)")
