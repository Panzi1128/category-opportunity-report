#!/usr/bin/env python3
"""Link multiple local AI skill directories to this repository clone."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime


SKILL_NAME = "category-opportunity-report"
DEFAULT_ROOTS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
    "gemini": Path.home() / ".gemini" / "skills",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Make installed AI skills share this repository clone."
    )
    parser.add_argument(
        "--ai",
        action="append",
        choices=sorted(DEFAULT_ROOTS),
        help="AI installation to link; repeat as needed. Defaults to all known AIs.",
    )
    parser.add_argument(
        "--target",
        action="append",
        type=Path,
        default=[],
        help="Additional absolute target path for the skill link.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Move an existing target to a timestamped backup before linking.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def same_target(link: Path, source: Path) -> bool:
    if not link.is_symlink():
        return False
    return link.resolve() == source.resolve()


def link_target(target: Path, source: Path, replace: bool, dry_run: bool) -> bool:
    if target.resolve() == source.resolve():
        print(f"skip source directory: {target}")
        return True
    if same_target(target, source):
        print(f"already linked: {target} -> {source}")
        return True

    backup = None
    if target.exists() or target.is_symlink():
        if not replace:
            print(f"blocked existing target: {target} (use --replace)", file=sys.stderr)
            return False
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(f"{target.name}.backup-{stamp}")
        print(f"backup: {target} -> {backup}")

    print(f"link: {target} -> {source}")
    if dry_run:
        return True

    target.parent.mkdir(parents=True, exist_ok=True)
    if backup is not None:
        shutil.move(os.fspath(target), os.fspath(backup))
    target.symlink_to(source, target_is_directory=True)
    return True


def main() -> int:
    args = parse_args()
    source = Path(__file__).resolve().parent.parent
    if not (source / "SKILL.md").is_file():
        print(f"invalid skill source: {source}", file=sys.stderr)
        return 2

    ai_names = args.ai if args.ai is not None else ([] if args.target else sorted(DEFAULT_ROOTS))
    targets = [DEFAULT_ROOTS[name] / SKILL_NAME for name in ai_names]
    for custom in args.target:
        if not custom.is_absolute():
            print(f"custom target must be absolute: {custom}", file=sys.stderr)
            return 2
        targets.append(custom)

    ok = True
    seen: set[Path] = set()
    for target in targets:
        normalized = target.expanduser().absolute()
        if normalized in seen:
            continue
        seen.add(normalized)
        ok = link_target(normalized, source, args.replace, args.dry_run) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
