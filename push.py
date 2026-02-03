#!/usr/bin/env python3
"""
Auto-push to github.com/ronandownes/{folder_name}
Uses the folder where this script lives, not where you run it from.
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

GITHUB_USER = "ronandownes"

# Use script's folder, not cwd
script_dir = Path(__file__).parent.resolve()
os.chdir(script_dir)

folder = script_dir.name
remote = f"https://github.com/{GITHUB_USER}/{folder}.git"

def run(cmd):
    print(f"  {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

# Init if needed
if not Path(".git").exists():
    print(f"Initializing git repo for '{folder}'...")
    run("git init")
    run(f"git remote add origin {remote}")
    run("git branch -M main")

# Check remote is correct
result = run("git remote get-url origin")
if result.stdout.strip() != remote:
    print(f"Updating remote to {remote}")
    run("git remote remove origin")
    run(f"git remote add origin {remote}")

msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

print(f"Pushing '{folder}' → {GITHUB_USER}/{folder}")
run("git add -A")
run(f'git commit -m "{msg}"')
if run("git push -u origin main --force").returncode != 0:
    run("git push --force")
print("Done!")
