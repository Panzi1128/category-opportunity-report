#!/usr/bin/env python3
"""Safely update this Skill from its fixed GitHub Release source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


SKILL_NAME = "category-opportunity-report"
REPOSITORY = "Panzi1128/category-opportunity-report"
LATEST_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
LATEST_PAGE = f"https://github.com/{REPOSITORY}/releases/latest"
DIGEST_LABEL = f"{SKILL_NAME}-sha256"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
REQUIRED = (
    "VERSION",
    "SKILL.md",
    "agents/openai.yaml",
    "scripts/sync_skill_release.py",
    "references/self-update.md",
    "references/data-intake.md",
    "references/analysis-framework.md",
    "references/chart-rules.md",
    "references/document-spec.md",
)


def stable_version(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value.strip())
    return tuple(map(int, match.groups())) if match else None


def emit(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("message", ""))


def read_version(root: Path) -> str:
    value = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not stable_version(value):
        raise ValueError(f"invalid VERSION: {value or '(empty)'}")
    return value


def request_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{SKILL_NAME}-release-sync",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def expected_asset(tag: str) -> str:
    return f"{SKILL_NAME}-{tag}.zip"


def published_digest(release: dict[str, object], asset: dict[str, object]) -> str | None:
    digest = str(asset.get("digest") or "")
    if re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
        return digest.split(":", 1)[1].lower()
    body = str(release.get("body") or "")
    match = re.search(rf"{re.escape(DIGEST_LABEL)}:\s*([a-fA-F0-9]{{64}})", body)
    return match.group(1).lower() if match else None


def official_asset(release: dict[str, object], tag: str) -> tuple[dict[str, object], str]:
    name = expected_asset(tag)
    assets = release.get("assets") or []
    asset = next((item for item in assets if isinstance(item, dict) and item.get("name") == name), None)
    if not asset:
        raise ValueError(f"release is missing exact asset {name}")
    url = str(asset.get("browser_download_url") or "")
    prefix = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
    if url != prefix + name:
        raise ValueError("release asset URL is not the fixed official GitHub URL")
    digest = published_digest(release, asset)
    if not digest:
        raise ValueError("release is missing a published SHA-256 digest")
    return asset, digest


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": f"{SKILL_NAME}-release-sync"})
    with urllib.request.urlopen(request, timeout=120) as response:
        declared = int(response.headers.get("Content-Length") or 0)
        if declared > MAX_ARCHIVE_BYTES:
            raise ValueError("release archive exceeds size limit")
        data = response.read(MAX_ARCHIVE_BYTES + 1)
    if not data or len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("release archive is empty or exceeds size limit")
    destination.write_bytes(data)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_archive(archive: Path, expected_tag: str, extract_root: Path) -> Path:
    with zipfile.ZipFile(archive) as package:
        roots: set[str] = set()
        for item in package.infolist():
            normalized = item.filename.replace("\\", "/")
            parts = Path(normalized).parts
            if not parts or parts[0] == "__MACOSX":
                continue
            if normalized.startswith("/") or ".." in parts:
                raise ValueError(f"unsafe archive path: {item.filename}")
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"archive contains symbolic link: {item.filename}")
            roots.add(parts[0])
        if roots != {SKILL_NAME}:
            raise ValueError(f"archive must contain one {SKILL_NAME} root")
        package.extractall(extract_root)

    skill_root = extract_root / SKILL_NAME
    for relative in REQUIRED:
        if not (skill_root / relative).is_file():
            raise ValueError(f"release package is missing {relative}")
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    if not re.search(rf"^name:\s*{re.escape(SKILL_NAME)}\s*$", skill_text, re.MULTILINE):
        raise ValueError("release package has the wrong Skill identity")
    if read_version(skill_root) != expected_tag:
        raise ValueError("release tag and packaged VERSION do not match")
    return skill_root


def git_checkout(root: Path) -> Path | None:
    current = root.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def run_git(checkout: Path, *arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=checkout, text=True, capture_output=capture, check=False
    )


def update_checkout(checkout: Path, tag: str) -> dict[str, object]:
    remote = run_git(checkout, "remote", "get-url", "origin", capture=True)
    allowed = {
        f"https://github.com/{REPOSITORY}.git",
        f"git@github.com:{REPOSITORY}.git",
        f"ssh://git@github.com/{REPOSITORY}.git",
    }
    if remote.returncode or remote.stdout.strip() not in allowed:
        raise ValueError("Git checkout origin is not the fixed official repository")
    status_result = run_git(checkout, "status", "--porcelain", capture=True)
    if status_result.returncode or status_result.stdout.strip():
        raise ValueError("Git checkout has local changes")
    fetched = run_git(checkout, "fetch", "origin", f"refs/tags/{tag}:refs/tags/{tag}")
    if fetched.returncode:
        raise ValueError("could not fetch the stable Release tag")
    merged = run_git(checkout, "merge", "--ff-only", f"refs/tags/{tag}")
    if merged.returncode:
        raise ValueError("Git checkout cannot fast-forward to the stable Release tag")
    if read_version(checkout) != tag:
        raise ValueError("updated Git checkout VERSION does not match Release tag")
    return {"status": "updated", "installed_root": str(checkout), "method": "git_fast_forward"}


def replace_directory(root: Path, new_root: Path, local_tag: str) -> dict[str, object]:
    was_symlink = root.is_symlink()
    recognized = (root.resolve() / "SKILL.md").is_file() if was_symlink else (root / "SKILL.md").is_file()
    if not root.is_dir() or not recognized:
        raise ValueError("refusing to replace an unrecognized Skill root")
    backup = root.parent / f".{SKILL_NAME}.backup-{local_tag}"
    counter = 1
    while backup.exists():
        backup = root.parent / f".{SKILL_NAME}.backup-{local_tag}-{counter}"
        counter += 1
    root.rename(backup)
    try:
        new_root.rename(root)
    except Exception:
        backup.rename(root)
        raise
    method = "symlink_migration" if was_symlink else "atomic_replace"
    return {"status": "updated", "installed_root": str(root), "backup_path": str(backup), "method": method}


def apply_archive_release(
    root: Path,
    local_tag: str,
    tag: str,
    release: dict[str, object],
    asset_file: Path | None,
) -> dict[str, object]:
    asset, expected_digest = official_asset(release, tag)
    with tempfile.TemporaryDirectory(prefix=f"{SKILL_NAME}-update-", dir=root.parent) as staging:
        staging_path = Path(staging)
        archive = staging_path / expected_asset(tag)
        if asset_file:
            shutil.copy2(asset_file, archive)
        else:
            download(str(asset["browser_download_url"]), archive)
        if sha256(archive) != expected_digest:
            raise ValueError("Release ZIP SHA-256 does not match the published digest")
        new_root = validate_archive(archive, tag, staging_path / "extracted")
        return replace_directory(root, new_root, local_tag)


def remove_legacy_weekly_task() -> None:
    try:
        if sys.platform == "darwin":
            plist = Path.home() / "Library" / "LaunchAgents" / f"com.panzi.{SKILL_NAME}-update.plist"
            if plist.exists():
                subprocess.run(["launchctl", "unload", str(plist)], check=False, capture_output=True)
                plist.unlink(missing_ok=True)
        elif os.name == "nt":
            subprocess.run(["schtasks", "/Delete", "/F", "/TN", f"{SKILL_NAME}-update"], check=False, capture_output=True)
        else:
            current = subprocess.run(["crontab", "-l"], text=True, capture_output=True, check=False)
            marker = f"# {SKILL_NAME}-update"
            if marker in current.stdout:
                kept = "\n".join(line for line in current.stdout.splitlines() if marker not in line) + "\n"
                subprocess.run(["crontab", "-"], input=kept, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check and safely apply the latest stable Skill Release.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parent.parent)
    parser.add_argument("--release-json", type=Path)
    parser.add_argument("--asset-file", type=Path)
    args = parser.parse_args()
    if (args.release_json or args.asset_file) and os.environ.get("CATEGORY_SKILL_UPDATE_TEST_MODE") != "1":
        parser.error("test fixtures require CATEGORY_SKILL_UPDATE_TEST_MODE=1")
    return args


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().absolute()
    try:
        local_tag = read_version(root.resolve())
    except Exception as error:
        emit({"status": "update_failed", "blocking": False, "message": "无法读取本地 Skill 版本，继续使用当前文件", "detail": str(error)}, args.json)
        return 0

    try:
        release = json.loads(args.release_json.read_text()) if args.release_json else request_json(LATEST_API)
    except Exception as error:
        emit({"status": "check_unavailable", "local_version": local_tag, "blocking": False, "checked_url": LATEST_PAGE, "message": f"暂时无法检查更新，继续使用 {local_tag}", "detail": str(error)}, args.json)
        return 0

    tag = str(release.get("tag_name") or "").strip()
    if not stable_version(tag) or release.get("draft") is True or release.get("prerelease") is True:
        emit({"status": "update_failed", "local_version": local_tag, "blocking": False, "message": f"最新发布不是稳定版本，继续使用 {local_tag}"}, args.json)
        return 0
    if stable_version(tag) == stable_version(local_tag) and args.apply and root.is_symlink():
        try:
            result = apply_archive_release(root, local_tag, tag, release, args.asset_file)
            remove_legacy_weekly_task()
            result.update({"local_version": local_tag, "latest_version": tag, "reload_required": True, "checked_once_for_current_task": True, "message": f"已将 {tag} 从旧版软链接迁移为独立完整安装；重新读取 SKILL.md 后继续"})
            emit(result, args.json)
        except Exception as error:
            emit({"status": "update_failed", "local_version": local_tag, "latest_version": tag, "blocking": False, "release_page": LATEST_PAGE, "message": f"旧版软链接迁移未完成；继续使用 {local_tag}", "detail": str(error)}, args.json)
        return 0
    if stable_version(tag) <= stable_version(local_tag):
        remove_legacy_weekly_task()
        emit({"status": "up_to_date", "local_version": local_tag, "latest_version": tag, "checked_url": LATEST_PAGE, "message": f"当前 Skill 已是最新版 {local_tag}"}, args.json)
        return 0
    if not args.apply:
        emit({"status": "update_available", "local_version": local_tag, "latest_version": tag, "release_page": LATEST_PAGE, "message": f"发现新版 {tag}"}, args.json)
        return 0

    try:
        checkout = git_checkout(root)
        if checkout:
            result = update_checkout(checkout, tag)
        else:
            result = apply_archive_release(root, local_tag, tag, release, args.asset_file)
        remove_legacy_weekly_task()
        result.update({"local_version": local_tag, "latest_version": tag, "reload_required": True, "checked_once_for_current_task": True, "message": f"已从 {local_tag} 更新到 {tag}；重新读取新版 SKILL.md 后继续"})
        emit(result, args.json)
    except Exception as error:
        emit({"status": "update_failed", "local_version": local_tag, "latest_version": tag, "blocking": False, "release_page": LATEST_PAGE, "message": f"发现 {tag}，但自动更新未完成；继续使用 {local_tag}", "detail": str(error)}, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
