#!/usr/bin/env python3
"""
MATHS COMIC PUSH
================
Quick git push - assumes you're the only contributor.
Uses force push if needed.

Usage:
  python push.py              # Auto commit message with timestamp
  python push.py "message"    # Custom commit message
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# CONFIG - Edit this path
COMIC_PATH = Path(r"E:\comic")

def run(cmd, check=True):
    """Run command and return output"""
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=COMIC_PATH, 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0 and check:
        if result.stderr.strip():
            print(f"  ✗ {result.stderr.strip()}")
        return False
    return True

def main():
    print("=" * 50)
    print("PUSH TO GIT")
    print("=" * 50)
    print(f"Path: {COMIC_PATH}")
    print("=" * 50)
    
    # Check if git repo
    if not (COMIC_PATH / ".git").exists():
        print("✗ Not a git repository!")
        print(f"  Run: cd {COMIC_PATH} && git init")
        return
    
    # Get commit message
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    print(f"\nCommit message: {msg}\n")
    
    # Git commands
    print("Adding files...")
    run("git add -A")
    
    print("\nCommitting...")
    # Don't fail if nothing to commit
    result = subprocess.run("git commit -m \"{msg}\"".format(msg=msg), 
                          shell=True, cwd=COMIC_PATH, capture_output=True, text=True)
    if "nothing to commit" in result.stdout + result.stderr:
        print("  Nothing to commit")
    else:
        print(f"  ✓ Committed")
    
    print("\nPushing (force)...")
    if run("git push --force-with-lease", check=False):
        print("\n✓ Pushed successfully!")
    else:
        # Try regular force if lease fails
        print("  Trying force push...")
        if run("git push --force", check=False):
            print("\n✓ Force pushed!")
        else:
            print("\n✗ Push failed - check remote settings")
            print("  Maybe run: git remote add origin <url>")
            print("  Or: git push -u origin main --force")
    
    print()

if __name__ == "__main__":
    main()
