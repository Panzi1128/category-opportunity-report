#!/usr/bin/env python3
"""Install a weekly updater for macOS, Linux, or Windows."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import plistlib
import platform
import shlex
import subprocess
import sys


JOB_NAME = "category-opportunity-report-update"


def updater_command(source: Path) -> list[str]:
    updater = source / "scripts" / "update_from_github.py"
    return [sys.executable, os.fspath(updater), "--source", os.fspath(source)]


def install_macos(command: list[str], dry_run: bool) -> int:
    target = Path.home() / "Library" / "LaunchAgents" / f"com.panzi.{JOB_NAME}.plist"
    payload = {
        "Label": f"com.panzi.{JOB_NAME}",
        "ProgramArguments": command,
        "StartCalendarInterval": {"Weekday": 1, "Hour": 3, "Minute": 0},
        "StandardOutPath": os.fspath(Path.home() / "Library" / "Logs" / f"{JOB_NAME}.log"),
        "StandardErrorPath": os.fspath(Path.home() / "Library" / "Logs" / f"{JOB_NAME}.log"),
    }
    print(f"install weekly updater: {target}")
    if dry_run:
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as stream:
        plistlib.dump(payload, stream, sort_keys=False)
    subprocess.run(["launchctl", "unload", os.fspath(target)], check=False, capture_output=True)
    loaded = subprocess.run(["launchctl", "load", os.fspath(target)], check=False)
    return loaded.returncode


def install_linux(command: list[str], dry_run: bool) -> int:
    marker = f"# {JOB_NAME}"
    entry = f"0 3 * * 0 {shlex.join(command)} {marker}"
    current = subprocess.run(["crontab", "-l"], text=True, capture_output=True, check=False)
    lines = [line for line in current.stdout.splitlines() if marker not in line]
    lines.append(entry)
    payload = "\n".join(lines) + "\n"
    print(f"install weekly updater: {entry}")
    if dry_run:
        return 0
    installed = subprocess.run(["crontab", "-"], input=payload, text=True, check=False)
    return installed.returncode


def install_windows(command: list[str], dry_run: bool) -> int:
    task_command = subprocess.list2cmdline(command)
    args = [
        "schtasks", "/Create", "/F", "/SC", "WEEKLY", "/D", "SUN", "/ST", "03:00",
        "/TN", JOB_NAME, "/TR", task_command,
    ]
    print("install weekly updater: " + subprocess.list2cmdline(args))
    if dry_run:
        return 0
    return subprocess.run(args, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a Sunday 03:00 weekly skill updater.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not (source / "scripts" / "update_from_github.py").is_file():
        print(f"updater not found in: {source}", file=sys.stderr)
        return 2

    system = platform.system()
    command = updater_command(source)
    try:
        if system == "Darwin":
            return install_macos(command, args.dry_run)
        if system == "Linux":
            return install_linux(command, args.dry_run)
        if system == "Windows":
            return install_windows(command, args.dry_run)
    except FileNotFoundError as error:
        print(f"scheduler command not found: {error.filename}", file=sys.stderr)
        return 2
    print(f"unsupported operating system: {system}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
