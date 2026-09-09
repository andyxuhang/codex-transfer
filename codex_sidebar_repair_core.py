"""Safe, reversible repair helpers for stale Codex Desktop sidebar entries."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import codex_transfer_core as transfer


REPAIR_VERSION = "1.2.1"
BACKUP_FORMAT = "codex-sidebar-cache-backup"
CACHE_DIRECTORIES = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "Local Storage",
    "Session Storage",
    "WebStorage",
    "blob_storage",
)

Progress = Callable[[str, Optional[float]], None]


class RepairError(RuntimeError):
    """An expected safety or repair error."""


def noop_progress(_message: str, _fraction: Optional[float] = None) -> None:
    return None


def default_local_app_data() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    if value:
        return Path(value)
    return Path.home() / "AppData" / "Local"


def discover_codex_profiles(local_app_data: Optional[Path] = None) -> list[Path]:
    """Return Chromium profiles used by known Windows Codex Desktop packages."""
    root = (local_app_data or default_local_app_data()).expanduser()
    candidates: list[Path] = []
    packages = root / "Packages"
    if packages.is_dir():
        for package in packages.glob("OpenAI.Codex_*"):
            candidates.append(package / "LocalCache" / "Roaming" / "Codex" / "web" / "Codex" / "Default")
    candidates.extend((
        root / "OpenAI" / "Codex" / "web" / "Codex" / "Default",
        root / "Codex" / "web" / "Codex" / "Default",
    ))
    unique: dict[str, Path] = {}
    for candidate in candidates:
        if candidate.is_dir():
            unique[str(candidate.resolve()).casefold()] = candidate.resolve()
    return sorted(unique.values(), key=lambda item: str(item).casefold())


def _validate_profile(profile: Path) -> Path:
    resolved = profile.expanduser().resolve()
    parts = [part.casefold() for part in resolved.parts]
    if resolved.name.casefold() != "default" or "codex" not in parts or "web" not in parts:
        raise RepairError(f"Refusing an unrecognized Codex web profile: {resolved}")
    return resolved


def _directory_stats(path: Path) -> tuple[int, int]:
    files = 0
    size = 0
    if not path.is_dir():
        return files, size
    for root, _dirs, names in os.walk(path):
        for name in names:
            item = Path(root) / name
            try:
                stat = item.stat()
            except OSError:
                continue
            files += 1
            size += stat.st_size
    return files, size


def _session_files(codex_dir: Path) -> set[str]:
    found: set[str] = set()
    for directory in (codex_dir / "sessions", codex_dir / "archived_sessions"):
        if directory.is_dir():
            for path in directory.rglob("*.jsonl"):
                try:
                    found.add(_path_key(path))
                except OSError:
                    found.add(_path_key(path.absolute()))
    return found


def _path_key(path: Path) -> str:
    value = str(path.resolve()).replace("/", "\\")
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return value.casefold()


def inspect_local_threads(codex_dir: Path) -> dict[str, Any]:
    """Read local thread metadata without modifying it."""
    root = codex_dir.expanduser().resolve()
    report: dict[str, Any] = {
        "database_threads": 0,
        "session_files": 0,
        "missing_rollout_records": [],
        "unreferenced_session_files": [],
        "warning": None,
    }
    sessions = _session_files(root)
    report["session_files"] = len(sessions)
    database = root / "state_5.sqlite"
    if not database.is_file():
        report["warning"] = f"Local thread database not found: {database}"
        report["unreferenced_session_files"] = sorted(sessions)
        return report
    connection: Optional[sqlite3.Connection] = None
    referenced: set[str] = set()
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
        has_threads = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='threads'"
        ).fetchone()
        if not has_threads:
            report["warning"] = "The database has no recognized threads table."
            return report
        columns = {str(row[1]).casefold(): str(row[1]) for row in connection.execute("PRAGMA table_info(threads)")}
        if "id" not in columns or "rollout_path" not in columns:
            report["warning"] = "The threads table has no recognized id/rollout_path columns."
            return report
        rows = connection.execute('SELECT "id", "rollout_path", "title" FROM threads' if "title" in columns else 'SELECT "id", "rollout_path", NULL FROM threads')
        for thread_id, rollout_path, title in rows:
            report["database_threads"] += 1
            if not rollout_path:
                report["missing_rollout_records"].append({"thread_id": str(thread_id), "title": title, "path": None})
                continue
            path = Path(str(rollout_path))
            try:
                normalized = _path_key(path)
            except OSError:
                normalized = _path_key(path.absolute())
            referenced.add(normalized)
            if not path.is_file():
                report["missing_rollout_records"].append({
                    "thread_id": str(thread_id), "title": title, "path": str(path),
                })
    except sqlite3.Error as exc:
        report["warning"] = f"Unable to inspect local thread database: {exc}"
    finally:
        if connection is not None:
            connection.close()
    report["unreferenced_session_files"] = sorted(sessions - referenced)
    return report


def scan_sidebar_state(
    codex_dir: Optional[Path] = None,
    local_app_data: Optional[Path] = None,
) -> dict[str, Any]:
    profiles = discover_codex_profiles(local_app_data)
    profile_rows = []
    for profile in profiles:
        targets = []
        total_files = 0
        total_bytes = 0
        for name in CACHE_DIRECTORIES:
            path = profile / name
            files, size = _directory_stats(path)
            if path.exists():
                targets.append({"name": name, "files": files, "bytes": size})
                total_files += files
                total_bytes += size
        profile_rows.append({
            "path": str(profile),
            "cache_targets": targets,
            "files": total_files,
            "bytes": total_bytes,
        })
    root = (codex_dir or transfer.default_codex_dir()).expanduser().resolve()
    return {
        "tool_version": REPAIR_VERSION,
        "mode": "read-only-scan",
        "codex_dir": str(root),
        "profiles": profile_rows,
        "local_threads": inspect_local_threads(root),
        "privacy": "Chat titles and message text are not scanned from browser storage.",
    }


def _archive_tree(archive: zipfile.ZipFile, source: Path, prefix: str) -> int:
    count = 0
    for root, dirs, files in os.walk(source):
        dirs.sort(key=str.casefold)
        files.sort(key=str.casefold)
        root_path = Path(root)
        relative_root = root_path.relative_to(source)
        if not files and not dirs:
            archive.writestr((Path(prefix) / relative_root / ".empty").as_posix(), b"")
        for name in files:
            path = root_path / name
            archive.write(path, (Path(prefix) / relative_root / name).as_posix())
            count += 1
    return count


def rebuild_sidebar_cache(
    profiles: Iterable[Path],
    backup_dir: Path,
    confirmed: bool,
    progress: Progress = noop_progress,
) -> dict[str, Any]:
    """Back up and remove only web-state/cache directories so Codex can rebuild them."""
    if not confirmed:
        raise RepairError("Explicit sidebar-cache rebuild confirmation is required.")
    running = transfer.codex_processes()
    if running:
        raise RepairError("Close Codex/ChatGPT Desktop before repairing: " + ", ".join(running))
    checked = [_validate_profile(Path(item)) for item in profiles]
    if not checked:
        raise RepairError("No Codex Desktop web profile was found.")
    selected: list[tuple[int, Path, str]] = []
    for profile_index, profile in enumerate(checked):
        for name in CACHE_DIRECTORIES:
            target = profile / name
            if target.is_dir():
                selected.append((profile_index, target, name))
    if not selected:
        raise RepairError("No rebuildable Codex sidebar cache was found.")

    backup_root = backup_dir.expanduser().resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_root / f"codex-sidebar-before-repair-{stamp}.zip"
    if backup.exists():
        backup = backup_root / f"codex-sidebar-before-repair-{stamp}-{uuid.uuid4().hex[:6]}.zip"
    partial = backup.with_suffix(backup.suffix + ".partial")
    token = uuid.uuid4().hex
    moved: list[tuple[Path, Path, int, str]] = []
    result: dict[str, Any] = {
        "tool_version": REPAIR_VERSION,
        "mode": "sidebar-cache-rebuild",
        "profiles": [str(item) for item in checked],
        "backup": str(backup),
        "removed_directories": [],
        "backup_files": 0,
        "applied": False,
        "warnings": [],
    }
    try:
        progress("Preparing sidebar cache for backup", 0.1)
        for index, (profile_index, target, name) in enumerate(selected):
            staged = target.with_name(f"{target.name}.codex-sidebar-repair-{token}")
            target.rename(staged)
            moved.append((target, staged, profile_index, name))
            progress(f"Preparing {name}", 0.1 + 0.2 * (index + 1) / len(selected))
        manifest = {
            "format": BACKUP_FORMAT,
            "format_version": 1,
            "tool_version": REPAIR_VERSION,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "profiles": [str(item) for item in checked],
            "directories": [
                {"profile_index": profile_index, "name": name}
                for _target, _staged, profile_index, name in moved
            ],
        }
        with zipfile.ZipFile(partial, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("codex-sidebar-backup-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for index, (_target, staged, profile_index, name) in enumerate(moved):
                result["backup_files"] += _archive_tree(archive, staged, f"profiles/{profile_index}/{name}")
                progress(f"Backing up {name}", 0.3 + 0.5 * (index + 1) / len(moved))
        with zipfile.ZipFile(partial, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise RepairError(f"Sidebar backup verification failed at: {bad}")
        partial.replace(backup)
        for target, staged, _profile_index, name in moved:
            try:
                shutil.rmtree(staged)
                result["removed_directories"].append(str(target))
            except OSError as exc:
                result["warnings"].append(f"Backup is valid, but temporary cache could not be removed: {staged}: {exc}")
        result["applied"] = True
        progress("Sidebar cache rebuild is ready", 1.0)
        return result
    except Exception:
        for target, staged, _profile_index, _name in reversed(moved):
            if staged.exists() and not target.exists():
                try:
                    staged.rename(target)
                except OSError:
                    pass
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass
        raise
