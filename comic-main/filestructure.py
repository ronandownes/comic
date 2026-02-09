#!/usr/bin/env python3
"""Show folder structure - writes to structure.txt"""
import sys
from pathlib import Path

lines = []

def show_structure(folder, prefix="", max_files=50):
    folder = Path(folder)
    try:
        items = sorted(folder.iterdir())
    except PermissionError:
        lines.append(f"{prefix}[access denied]")
        return
    
    dirs = [i for i in items if i.is_dir()]
    files = [i for i in items if i.is_file()]
    
    for f in files[:max_files]:
        lines.append(f"{prefix}{f.name}")
    if len(files) > max_files:
        lines.append(f"{prefix}... and {len(files) - max_files} more files")
    
    for d in dirs:
        lines.append(f"{prefix}{d.name}/")
        show_structure(d, prefix + "  ", max_files)

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else r"E:\comic"
    lines.append(f"{folder}/")
    show_structure(folder)
    out = Path(folder) / "structure.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")
