#!/usr/bin/env python3
"""Build the complete versioned Release ZIP and SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import zipfile


SKILL_NAME = "category-opportunity-report"
EXCLUDED_PARTS = {".git", "dist", "__pycache__", ".DS_Store"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    tag = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise SystemExit(f"invalid VERSION: {tag}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{SKILL_NAME}-{tag}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for source in sorted(root.rglob("*")):
            relative = source.relative_to(root)
            if any(part in EXCLUDED_PARTS or part.startswith(f".{SKILL_NAME}.backup-") for part in relative.parts):
                continue
            if source.is_file() and not source.is_symlink():
                package.write(source, Path(SKILL_NAME) / relative)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = output / f"{archive.name}.sha256"
    manifest.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(archive)
    print(f"{SKILL_NAME}-sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
