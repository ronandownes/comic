#!/usr/bin/env python3
"""Show size breakdown of E:\comic\ by top-level folders and files."""
import os
from pathlib import Path

ROOT = Path(r"E:\comic")

def fmt(b):
    if b >= 1 << 30: return f"{b / (1 << 30):.2f} GB"
    if b >= 1 << 20: return f"{b / (1 << 20):.1f} MB"
    if b >= 1 << 10: return f"{b / (1 << 10):.1f} KB"
    return f"{b} B"

def dir_stats(p):
    total = 0
    count = 0
    for f in p.rglob('*'):
        if f.is_file():
            total += f.stat().st_size
            count += 1
    return total, count

# Gather top-level entries
entries = []
grand_total = 0

for item in sorted(ROOT.iterdir()):
    if item.is_dir():
        size, count = dir_stats(item)
        entries.append((item.name + '/', size, count))
        grand_total += size
    elif item.is_file():
        size = item.stat().st_size
        entries.append((item.name, size, 1))
        grand_total += size

# Print
print(f"{'='*60}")
print(f"  {ROOT}")
print(f"{'='*60}")
print(f"  {'Name':<28} {'Size':>10} {'Files':>7} {'%':>6}")
print(f"  {'-'*28} {'-'*10} {'-'*7} {'-'*6}")

for name, size, count in sorted(entries, key=lambda x: -x[1]):
    pct = size / grand_total * 100 if grand_total else 0
    bar = '█' * int(pct / 2.5)
    print(f"  {name:<28} {fmt(size):>10} {count:>7} {pct:>5.1f}% {bar}")

print(f"  {'-'*28} {'-'*10} {'-'*7} {'-'*6}")
print(f"  {'TOTAL':<28} {fmt(grand_total):>10} {sum(e[2] for e in entries):>7}")
print()
