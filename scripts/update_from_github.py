#!/usr/bin/env python3
"""Fast-forward this skill clone from its configured GitHub origin."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run(*args: str, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=capture,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely update the skill with Git fast-forward only.")
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()

    if not (source / ".git").exists() or not (source / "SKILL.md").is_file():
        print(f"not a skill Git clone: {source}", file=sys.stderr)
        return 2

    status = run("status", "--porcelain", cwd=source, capture=True)
    if status.returncode != 0:
        print(status.stderr, file=sys.stderr)
        return status.returncode
    if status.stdout.strip():
        print("skip update: local changes detected", file=sys.stderr)
        return 3

    branch = run("branch", "--show-current", cwd=source, capture=True)
    if branch.returncode != 0 or branch.stdout.strip() != "main":
        print("skip update: source is not on main", file=sys.stderr)
        return 4

    fetched = run("fetch", "origin", "main", cwd=source)
    if fetched.returncode != 0:
        return fetched.returncode

    merged = run("merge", "--ff-only", "FETCH_HEAD", cwd=source)
    if merged.returncode != 0:
        print("skip update: remote cannot be fast-forwarded", file=sys.stderr)
    return merged.returncode


if __name__ == "__main__":
    raise SystemExit(main())
