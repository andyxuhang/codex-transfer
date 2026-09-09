"""Core migration engine for Codex Transfer.

This module is deliberately GUI-independent so every destructive path can be
tested. It migrates user data by replacement, never by database merging.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import ntpath
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Optional


APP_VERSION = "1.0.9"
FORMAT_NAME = "codex-transfer-package"
FORMAT_VERSION = 1
MANIFEST_NAME = "codex-transfer-manifest.json"

# User-created data. Machine identity, credentials, caches, logs, plugins, and
# temporary runtime data are intentionally absent from these allowlists.
DATA_DIRS = (
    "sessions",
    "archived_sessions",
    "attachments",
    "automations",
)
PLAIN_FILES = (
    "session_index.jsonl",
)
GLOBAL_STATE_FILE = ".codex-global-state.json"
DATABASE_FILES = (
    "state_5.sqlite",
)
DATABASE_SIDE_SUFFIXES = ("-wal", "-shm")
PATH_FIELD_NAMES = {
    "cwd", "path", "rollout_path", "session_path", "project_path",
    "workspace_path", "working_directory", "workdir", "output_dir",
}
PROFILE_STATE_KEYS = (
    "sidebar-custom-sections-v3",
    "chatgpt-sidebar-state-v1",
    "flat-project-sidebar-preferences-v1",
)
ELECTRON_SIDEBAR_KEYS = {
    "sidebar-custom-sections-v3",
    "chatgpt-sidebar-state-v1",
    "flat-project-sidebar-preferences-v1",
    "sidebar-collapsed-sections-v1",
    "sidebar-width",
}
TOP_LEVEL_SIDEBAR_KEYS = {
    "pinned-thread-ids",
    "app-server-migrated-pinned-thread-ids-by-host",
    "sidebar-project-thread-orders",
}
EXCLUDED_LABELS = (
    "auth.json / account tokens",
    ".env / API keys",
    "config.toml / machine-specific configuration",
    "installation_id / device identity",
    "plugins, cache, logs, sandbox and temporary runtime files",
    "managed workspace contents (.chatgpt-projects), project source and build output",
    "generated images, memories, rules, custom skills and vendor imports",
    "external repositories and OneDrive workspaces",
)
SAFE_AUTOMATION_ID = re.compile(r"^[A-Za-z0-9._-]+$")

Progress = Callable[[str, Optional[float]], None]


class TransferError(RuntimeError):
    """A safe, user-displayable migration failure."""


def noop_progress(message: str, fraction: Optional[float] = None) -> None:
    del message, fraction


def default_codex_dir() -> Path:
    if os.environ.get("CODEX_HOME"):
        return Path(os.environ["CODEX_HOME"]).expanduser()
    if os.environ.get("USERPROFILE"):
        return Path(os.environ["USERPROFILE"]) / ".codex"
    return Path.home() / ".codex"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def time_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for base, dirs, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        # Bundled skills are installed by Codex and should not be transferred.
        if base_path == root and root.name == "skills":
            dirs[:] = [name for name in dirs if name != ".system"]
        for name in names:
            path = base_path / name
            if not path.is_symlink():
                yield path


def count_files(root: Path) -> int:
    return sum(1 for _ in iter_files(root))


def windows_extended_path(path: Path) -> str:
    """Use Win32 extended paths so deeply nested project files remain copyable."""
    value = str(path.resolve())
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def copy2_resilient(source: Path, destination: Path, attempts: int = 3) -> None:
    """Copy a real project file with Windows long-path support and brief retries."""
    source_os = windows_extended_path(source)
    destination_os = windows_extended_path(destination)
    os.makedirs(windows_extended_path(destination.parent), exist_ok=True)
    last_error: Optional[OSError] = None
    for attempt in range(attempts):
        try:
            shutil.copy2(source_os, destination_os)
            return
        except (FileNotFoundError, PermissionError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.15 * (attempt + 1))
    raise TransferError(
        f"Unable to copy data after {attempts} attempts: {source}. "
        "Close programs that may be changing this file and try again. "
        f"Windows error: {last_error}"
    ) from last_error


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sqlite_snapshot(source: Path, target: Path) -> None:
    source_db: Optional[sqlite3.Connection] = None
    target_db: Optional[sqlite3.Connection] = None
    try:
        source_db = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        source_db.execute("PRAGMA query_only=ON")
        target_db = sqlite3.connect(str(target))
        source_db.backup(target_db)
        target_db.commit()
    except sqlite3.Error as exc:
        raise TransferError(f"SQLite snapshot failed for {source.name}: {exc}") from exc
    finally:
        if target_db is not None:
            target_db.close()
        if source_db is not None:
            source_db.close()


def source_inventory(source: Path) -> dict[str, Any]:
    source = source.resolve()
    inventory: dict[str, Any] = {
        "source": str(source),
        "present": source.is_dir(),
        "directories": {},
        "files": {},
    }
    for name in DATA_DIRS:
        inventory["directories"][name] = count_files(source / name)
    for name in PLAIN_FILES + (GLOBAL_STATE_FILE,) + DATABASE_FILES:
        path = source / name
        inventory["files"][name] = path.stat().st_size if path.is_file() else None
    inventory.update(inspect_codex_data(source, check_rollouts=False))
    return inventory


def _copy_source_to_stage(source: Path, stage: Path, progress: Progress) -> list[str]:
    candidates: list[tuple[Path, Path, int]] = []
    scanned = 0
    progress("Scanning conversations, attachments, and automations", 0.01)
    for dirname in DATA_DIRS:
        root = source / dirname
        for src in iter_files(root):
            scanned += 1
            relative = src.relative_to(source)
            try:
                size = src.stat().st_size
            except OSError as exc:
                raise TransferError(f"Unable to inspect source file: {src}: {exc}") from exc
            candidates.append((src, stage / relative, size))
            if scanned % 1000 == 0:
                progress(f"Scanning source: {scanned:,} files checked", 0.01)
    for filename in PLAIN_FILES:
        src = source / filename
        if src.is_file():
            candidates.append((src, stage / filename, src.stat().st_size))

    global_state = source / GLOBAL_STATE_FILE
    total = max(len(candidates) + len(DATABASE_FILES) + int(global_state.is_file()), 1)
    total_bytes = sum(item[2] for item in candidates)
    done = 0
    copied_bytes = 0
    progress(
        f"Found {len(candidates):,} migratable files ({total_bytes / 1024 / 1024:.1f} MB); starting copy",
        0.02,
    )
    for src, dst, size in candidates:
        relative = src.relative_to(source)
        fraction = copied_bytes / max(total_bytes, 1)
        progress(
            f"Copying {relative} ({done + 1:,}/{len(candidates):,}, {copied_bytes / 1024 / 1024:.1f}/{total_bytes / 1024 / 1024:.1f} MB)",
            0.02 + fraction * 0.53,
        )
        copy2_resilient(src, dst)
        done += 1
        copied_bytes += size
    progress(f"Copied {done:,} files ({copied_bytes / 1024 / 1024:.1f} MB)", 0.55)
    warnings = []
    if global_state.is_file():
        sanitized = sanitize_global_state(global_state)
        (stage / GLOBAL_STATE_FILE).write_text(
            json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        done += 1
        progress("Copying sanitized sidebar and section state", done / total * 0.55)
    for filename in DATABASE_FILES:
        src = source / filename
        if not src.is_file():
            continue
        dst = stage / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        progress(f"Snapshotting {filename}", done / total * 0.55)
        sqlite_snapshot(src, dst)
        done += 1
    return warnings


def create_package(
    source: Path,
    package: Path,
    progress: Progress = noop_progress,
) -> dict[str, Any]:
    source, package = source.resolve(), package.resolve()
    if not source.is_dir():
        raise TransferError(f"Codex data directory not found: {source}")
    running = codex_processes()
    if running:
        raise TransferError("Close Codex/ChatGPT Desktop before exporting: " + ", ".join(running))
    if package.exists():
        raise TransferError("The package already exists. Choose a new filename; existing packages are never overwritten.")
    if is_within(package, source):
        raise TransferError("The migration package must not be inside the source .codex directory.")
    package.parent.mkdir(parents=True, exist_ok=True)
    partial = package.with_suffix(package.suffix + ".partial")
    if partial.exists():
        raise TransferError(f"A partial package already exists: {partial}")

    progress("Preparing consistent snapshots", 0.01)
    with tempfile.TemporaryDirectory(prefix="codex-transfer-export-") as temp:
        stage = Path(temp) / "payload"
        stage.mkdir()
        export_warnings = _copy_source_to_stage(source, stage, progress)
        entries = []
        staged_files = sorted(iter_files(stage), key=lambda p: p.relative_to(stage).as_posix().lower())
        for index, path in enumerate(staged_files, 1):
            relative = path.relative_to(stage).as_posix()
            progress(f"Hashing {relative} ({index:,}/{len(staged_files):,})", 0.55 + ((index - 1) / max(len(staged_files), 1)) * 0.20)
            entries.append({"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)})
        manifest = {
            "format": FORMAT_NAME,
            "format_version": FORMAT_VERSION,
            "tool_version": APP_VERSION,
            "created_at": now_iso(),
            "source_codex_dir": str(source),
            "source_user_home": str(Path.home()),
            "payload_files": entries,
            "inventory": inspect_codex_data(stage, check_rollouts=False),
            "excluded_for_security": list(EXCLUDED_LABELS),
            "export_warnings": export_warnings,
            "mode": "replacement-only",
        }
        manifest_path = stage / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        progress("Writing migration package", 0.78)
        try:
            with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
                for index, path in enumerate(sorted(iter_files(stage)), 1):
                    progress(f"Packing {path.relative_to(stage)} ({index:,}/{len(entries) + 1:,})", 0.78 + (index - 1) / max(len(entries) + 1, 1) * 0.21)
                    archive.write(path, path.relative_to(stage).as_posix())
            os.replace(partial, package)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
    progress("Export complete", 1.0)
    return manifest


def _safe_zip_name(name: str) -> PurePosixPath:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise TransferError(f"Unsafe path in package: {name}")
    if pure.parts[0].endswith(":"):
        raise TransferError(f"Unsafe drive path in package: {name}")
    return pure


def read_package_manifest(package: Path) -> dict[str, Any]:
    if not package.is_file():
        raise TransferError(f"Migration package not found: {package}")
    try:
        with zipfile.ZipFile(package, "r") as archive:
            for info in archive.infolist():
                _safe_zip_name(info.filename)
            raw = archive.read(MANIFEST_NAME)
        manifest = json.loads(raw.decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError, OSError) as exc:
        raise TransferError(f"Invalid migration package: {exc}") from exc
    if manifest.get("format") != FORMAT_NAME or manifest.get("format_version") != FORMAT_VERSION:
        raise TransferError("Unsupported migration package format.")
    return manifest


def verify_package(package: Path, progress: Progress = noop_progress) -> dict[str, Any]:
    package = package.resolve()
    manifest = read_package_manifest(package)
    expected = {str(item["path"]): item for item in manifest.get("payload_files", [])}
    missing: list[str] = []
    changed: list[dict[str, Any]] = []
    unexpected: list[str] = []
    disallowed = sorted(name for name in expected if not is_allowed_payload_path(name))
    with zipfile.ZipFile(package, "r") as archive:
        actual = {info.filename: info for info in archive.infolist() if not info.is_dir() and info.filename != MANIFEST_NAME}
        for index, (name, item) in enumerate(expected.items(), 1):
            progress(f"Verifying {name}", index / max(len(expected), 1))
            info = actual.get(name)
            if info is None:
                missing.append(name)
                continue
            digest = hashlib.sha256()
            with archive.open(info, "r") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            if info.file_size != item.get("size") or digest.hexdigest() != item.get("sha256"):
                changed.append({"path": name, "expected_size": item.get("size"), "actual_size": info.file_size})
        unexpected = sorted(set(actual) - set(expected))
    result = {
        "ok": not missing and not changed and not unexpected and not disallowed,
        "file_count": len(expected),
        "missing": missing,
        "changed": changed,
        "unexpected": unexpected,
        "disallowed": disallowed,
        "manifest": manifest,
    }
    progress("Package verified" if result["ok"] else "Package verification failed", 1.0)
    return result


def is_allowed_payload_path(name: str) -> bool:
    pure = _safe_zip_name(name)
    root = pure.parts[0].casefold()
    allowed_dirs = {item.casefold() for item in DATA_DIRS}
    allowed_files = {item.casefold() for item in PLAIN_FILES + (GLOBAL_STATE_FILE,) + DATABASE_FILES}
    if len(pure.parts) == 1:
        return root in allowed_files
    return root in allowed_dirs


def extract_verified_package(package: Path, target: Path, manifest: dict[str, Any]) -> None:
    expected = {str(item["path"]) for item in manifest["payload_files"]}
    with zipfile.ZipFile(package, "r") as archive:
        for name in expected:
            pure = _safe_zip_name(name)
            destination = target.joinpath(*pure.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name, "r") as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)


def normalize_path_text(value: str) -> str:
    """Normalize a user-entered path without confusing POSIX and Windows roots."""
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    if not value:
        return value
    is_windows = bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith(("\\\\", "//"))
    if is_windows:
        return ntpath.normpath(value.replace("/", "\\"))
    return os.path.normpath(value)


def parse_path_maps(values: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    maps = []
    for old, new in values:
        old = normalize_path_text(old)
        new = normalize_path_text(new)
        if not old or not new:
            raise TransferError("Every path map requires both an old and a new prefix.")
        maps.append((old, new))
    unique: dict[str, tuple[str, str]] = {}
    for old, new in maps:
        unique[old.lower().replace("/", "\\")] = (old, new)
    return sorted(unique.values(), key=lambda item: len(item[0]), reverse=True)


def automatic_path_maps(manifest: dict[str, Any], destination: Path) -> list[tuple[str, str]]:
    destination = destination.resolve()
    pairs = [
        (str(manifest.get("source_codex_dir", "")), str(destination)),
        (str(manifest.get("source_user_home", "")), str(destination.parent)),
    ]
    return parse_path_maps(
        pair for pair in pairs
        if pair[0] and normalize_path_text(pair[0]).casefold() != normalize_path_text(pair[1]).casefold()
    )


WINDOWS_ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")


def _is_windows_absolute_path(value: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_PATH.match(str(value).strip().strip('"\'')))


def _collect_structured_paths(
    value: Any,
    found: dict[str, dict[str, Any]],
    source: str,
    path_fields_only: bool,
    parent_key: str = "",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _collect_structured_paths(child, found, source, path_fields_only, str(key).lower())
        return
    if isinstance(value, list):
        for child in value:
            _collect_structured_paths(child, found, source, path_fields_only, parent_key)
        return
    if not isinstance(value, str):
        return
    if path_fields_only and parent_key not in PATH_FIELD_NAMES:
        return
    if not _is_windows_absolute_path(value):
        return
    normalized = normalize_path_text(value)
    key = normalized.casefold()
    item = found.setdefault(key, {"path": normalized, "count": 0, "sources": set()})
    item["count"] += 1
    item["sources"].add(source)


def _top_mapping_root(path: str, source_home: str, source_codex: str) -> str:
    normalized = normalize_path_text(path)
    comparable = normalized.casefold()
    codex = normalize_path_text(source_codex) if source_codex else ""
    if codex and (comparable == codex.casefold() or comparable.startswith(codex.casefold() + "\\")):
        return codex
    home = normalize_path_text(source_home) if source_home else ""
    if home:
        if comparable == home.casefold():
            return home
        if comparable.startswith(home.casefold() + "\\"):
            remainder = normalized[len(home):].strip("\\/")
            first = remainder.replace("/", "\\").split("\\", 1)[0]
            return home + "\\" + first if first else home
    drive, tail = ntpath.splitdrive(normalized)
    parts = [part for part in tail.strip("\\/").replace("/", "\\").split("\\") if part]
    if not drive or not parts:
        return normalized
    if parts[0].casefold() == "users" and len(parts) >= 2:
        return drive + "\\" + "\\".join(parts[:2])
    return drive + "\\" + parts[0]


def inspect_package_paths(
    package: Path,
    destination: Path,
    progress: Progress = noop_progress,
) -> dict[str, Any]:
    """Read structured path references from a package without modifying it."""
    package = package.resolve()
    manifest = read_package_manifest(package)
    source_home = str(manifest.get("source_user_home", ""))
    source_codex = str(manifest.get("source_codex_dir", ""))
    found: dict[str, dict[str, Any]] = {}
    for name, value in (("manifest:source_user_home", source_home), ("manifest:source_codex_dir", source_codex)):
        if _is_windows_absolute_path(value):
            _collect_structured_paths({"path": value}, found, name, True)

    try:
        with zipfile.ZipFile(package, "r") as archive:
            names = [info.filename for info in archive.infolist() if not info.is_dir()]
            for index, name in enumerate(names, 1):
                progress(f"Inspecting paths in {name}", index / max(len(names), 1) * 0.9)
                lower = name.lower()
                if lower.endswith(".jsonl"):
                    try:
                        with archive.open(name) as raw:
                            reader = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
                            for line in reader:
                                if not line.strip():
                                    continue
                                try:
                                    _collect_structured_paths(json.loads(line), found, "JSONL", True)
                                except json.JSONDecodeError:
                                    continue
                    except (OSError, KeyError):
                        continue
                elif name == GLOBAL_STATE_FILE:
                    try:
                        value = json.loads(archive.read(name).decode("utf-8-sig"))
                        _collect_structured_paths(value, found, "sidebar state", False)
                    except (KeyError, UnicodeError, json.JSONDecodeError):
                        continue
                elif lower.endswith("automation.toml"):
                    try:
                        text = archive.read(name).decode("utf-8-sig", errors="replace")
                    except KeyError:
                        continue
                    for match in re.finditer(r"(?i)(?:[A-Z]:[\\/][^\"'\r\n]+|\\\\[^\\/\s]+[\\/][^\\/\s]+(?:[\\/][^\"'\r\n]+)?)", text):
                        _collect_structured_paths({"path": match.group(0).rstrip()}, found, "automation", True)

            if "state_5.sqlite" in names:
                with tempfile.TemporaryDirectory(prefix="codex-transfer-paths-") as temp:
                    database = Path(temp) / "state_5.sqlite"
                    database.write_bytes(archive.read("state_5.sqlite"))
                    conn: Optional[sqlite3.Connection] = None
                    try:
                        conn = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
                        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                        for (table,) in tables:
                            columns = conn.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()
                            for column in (str(c[1]) for c in columns if str(c[1]).lower() in PATH_FIELD_NAMES):
                                try:
                                    query = f"SELECT {quote_identifier(column)} FROM {quote_identifier(table)} WHERE {quote_identifier(column)} IS NOT NULL"
                                    for (value,) in conn.execute(query):
                                        _collect_structured_paths({column: value}, found, "SQLite", True)
                                except sqlite3.Error:
                                    continue
                    except sqlite3.Error:
                        pass
                    finally:
                        if conn is not None:
                            conn.close()
    except (zipfile.BadZipFile, OSError) as exc:
        raise TransferError(f"Unable to inspect package paths: {exc}") from exc

    roots: dict[str, dict[str, Any]] = {}
    for item in found.values():
        root = _top_mapping_root(item["path"], source_home, source_codex)
        key = root.casefold()
        grouped = roots.setdefault(key, {"old": root, "count": 0, "sources": set(), "examples": []})
        grouped["count"] += item["count"]
        grouped["sources"].update(item["sources"])
        if item["path"] not in grouped["examples"] and len(grouped["examples"]) < 3:
            grouped["examples"].append(item["path"])

    automatic = automatic_path_maps(manifest, destination)
    rows = []
    for grouped in roots.values():
        old = grouped["old"]
        suggested = replace_path_prefix(old, automatic)
        auto = suggested != old
        exists = Path(old).exists()
        rows.append({
            "old": old,
            "new": suggested if auto or exists else "",
            "automatic": auto,
            "exists": exists,
            "count": grouped["count"],
            "sources": sorted(grouped["sources"]),
            "examples": grouped["examples"],
        })
    rows.sort(key=lambda row: (not row["automatic"], row["old"].casefold()))
    progress("Path inspection complete", 1.0)
    return {
        "package": str(package),
        "plaintext": True,
        "automatic_maps": [{"old": old, "new": new} for old, new in automatic],
        "paths": rows,
    }


def replace_path_prefix(value: str, maps: list[tuple[str, str]]) -> str:
    normalized = value.replace("/", "\\")
    extended = normalized.startswith("\\\\?\\")
    comparable = normalized[4:] if extended else normalized
    for old, new in maps:
        old_cmp = old.replace("/", "\\")
        low_value, low_old = comparable.lower(), old_cmp.lower()
        if low_value == low_old or low_value.startswith(low_old + "\\"):
            replaced = normalize_path_text(new + comparable[len(old_cmp):])
            return "\\\\?\\" + replaced if extended else replaced
    return value


def transform_value(value: Any, maps: list[tuple[str, str]], path_only: bool, parent_key: str = "") -> tuple[Any, int]:
    count = 0
    if isinstance(value, dict):
        output = {}
        for key, child in value.items():
            output[key], child_count = transform_value(child, maps, path_only, str(key).lower())
            count += child_count
        return output, count
    if isinstance(value, list):
        output = []
        for child in value:
            converted, child_count = transform_value(child, maps, path_only, parent_key)
            output.append(converted)
            count += child_count
        return output, count
    if isinstance(value, str) and (not path_only or parent_key in PATH_FIELD_NAMES):
        converted = replace_path_prefix(value, maps)
        return converted, int(converted != value)
    return value, 0


def rewrite_json_file(path: Path, maps: list[tuple[str, str]], path_only: bool) -> int:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferError(f"Unable to rewrite JSON file {path}: {exc}") from exc
    converted, count = transform_value(value, maps, path_only)
    path.write_text(json.dumps(converted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return count


def rewrite_jsonl_file(path: Path, maps: list[tuple[str, str]]) -> int:
    temporary = path.with_name(path.name + ".rewrite")
    count = 0
    try:
        with path.open("r", encoding="utf-8-sig") as source, temporary.open("w", encoding="utf-8", newline="\n") as output:
            for line_no, line in enumerate(source, 1):
                if not line.strip():
                    output.write(line)
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise TransferError(f"Invalid JSONL at {path}, line {line_no}: {exc}") from exc
                converted, changed = transform_value(value, maps, path_only=True)
                count += changed
                output.write(json.dumps(converted, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return count


def rewrite_sqlite(path: Path, maps: list[tuple[str, str]]) -> int:
    if not path.is_file():
        return 0
    conn = sqlite3.connect(str(path))
    changed = 0
    try:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (table,) in tables:
            columns = conn.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()
            for column in (str(c[1]) for c in columns if str(c[1]).lower() in PATH_FIELD_NAMES):
                query = f"SELECT DISTINCT {quote_identifier(column)} FROM {quote_identifier(table)} WHERE {quote_identifier(column)} IS NOT NULL"
                try:
                    values = conn.execute(query).fetchall()
                    for (old_value,) in values:
                        if not isinstance(old_value, str):
                            continue
                        new_value = replace_path_prefix(old_value, maps)
                        if new_value != old_value:
                            update = f"UPDATE {quote_identifier(table)} SET {quote_identifier(column)}=? WHERE {quote_identifier(column)}=?"
                            cursor = conn.execute(update, (new_value, old_value))
                            changed += max(cursor.rowcount, 0)
                except sqlite3.Error:
                    continue
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise TransferError(f"Unable to rewrite staged database {path.name}: {exc}") from exc
    finally:
        conn.close()
    return changed


def discover_profile_key(global_state: Path) -> Optional[str]:
    if not global_state.is_file():
        return None
    try:
        data = json.loads(global_state.read_text(encoding="utf-8-sig"))
        electron = data.get("electron-persisted-atom-state", {})
        for state_name in PROFILE_STATE_KEYS:
            state = electron.get(state_name)
            if isinstance(state, dict) and state:
                return next(iter(state))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return None


def sanitize_global_state(path: Path) -> dict[str, Any]:
    """Export only sidebar state; account identity and resume tokens stay behind."""
    try:
        source = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferError(f"Unable to read global sidebar state: {exc}") from exc
    output: dict[str, Any] = {}
    electron_source = source.get("electron-persisted-atom-state")
    if isinstance(electron_source, dict):
        electron_output = {
            key: value for key, value in electron_source.items()
            if key in ELECTRON_SIDEBAR_KEYS or key.startswith("sidebar-project-expanded-v1-")
        }
        if electron_output:
            output["electron-persisted-atom-state"] = electron_output
    for key in TOP_LEVEL_SIDEBAR_KEYS:
        if key in source:
            output[key] = source[key]
    return output


def merge_global_state(staged: Path, destination_existing: Path) -> None:
    """Replace sidebar keys but preserve destination tokens, identity, and other UI state."""
    if not staged.is_file() or not destination_existing.is_file():
        return
    try:
        source = json.loads(staged.read_text(encoding="utf-8-sig"))
        destination = json.loads(destination_existing.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferError(f"Unable to merge sanitized sidebar state: {exc}") from exc
    source_electron = source.get("electron-persisted-atom-state", {})
    destination_electron = destination.setdefault("electron-persisted-atom-state", {})
    if not isinstance(source_electron, dict) or not isinstance(destination_electron, dict):
        raise TransferError("Unexpected global sidebar state structure.")
    for key in list(destination_electron):
        if key in ELECTRON_SIDEBAR_KEYS or key.startswith("sidebar-project-expanded-v1-"):
            destination_electron.pop(key, None)
    destination_electron.update(source_electron)
    for key in TOP_LEVEL_SIDEBAR_KEYS:
        if key in source:
            destination[key] = source[key]
        else:
            destination.pop(key, None)
    staged.write_text(json.dumps(destination, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remap_sidebar_profile(global_state: Path, target_profile: Optional[str]) -> int:
    if not target_profile or not global_state.is_file():
        return 0
    try:
        data = json.loads(global_state.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferError(f"Unable to read staged global sidebar state: {exc}") from exc
    electron = data.get("electron-persisted-atom-state")
    if not isinstance(electron, dict):
        return 0
    changes = 0
    for state_name in PROFILE_STATE_KEYS:
        state = electron.get(state_name)
        if not isinstance(state, dict) or not state or target_profile in state:
            continue
        if len(state) == 1:
            old_key = next(iter(state))
            state[target_profile] = state.pop(old_key)
            changes += 1
    if changes:
        global_state.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def rewrite_stage(stage: Path, maps: list[tuple[str, str]], target_profile: Optional[str], progress: Progress) -> dict[str, int]:
    counts = {"jsonl": 0, "json": 0, "toml": 0, "sqlite": 0, "sidebar_profiles": 0}
    files = list(iter_files(stage))
    for index, path in enumerate(files, 1):
        suffix = path.suffix.lower()
        relative = path.relative_to(stage)
        progress(f"Rewriting paths in {relative}", index / max(len(files), 1) * 0.55)
        if suffix == ".jsonl":
            counts["jsonl"] += rewrite_jsonl_file(path, maps)
        elif path.name == ".codex-global-state.json":
            counts["json"] += rewrite_json_file(path, maps, path_only=False)
            counts["sidebar_profiles"] += remap_sidebar_profile(path, target_profile)
        elif suffix == ".toml" and "automations" in relative.parts:
            text = path.read_text(encoding="utf-8")
            converted = text
            for old, new in maps:
                converted = re.sub(re.escape(old), lambda _: new, converted, flags=re.IGNORECASE)
            if converted != text:
                counts["toml"] += 1
                path.write_text(converted, encoding="utf-8")
        elif path.name in DATABASE_FILES:
            counts["sqlite"] += rewrite_sqlite(path, maps)
    return counts


def scoped_paths(codex_dir: Path) -> list[Path]:
    paths = [codex_dir / name for name in DATA_DIRS + PLAIN_FILES + (GLOBAL_STATE_FILE,) + DATABASE_FILES]
    for filename in DATABASE_FILES:
        paths.extend(codex_dir / (filename + suffix) for suffix in DATABASE_SIDE_SUFFIXES)
    return paths


def _archive_existing_destination(destination: Path, backup: Path, progress: Progress) -> int:
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        raise TransferError(f"Backup already exists: {backup}")
    existing_files = []
    for item in scoped_paths(destination):
        if item.is_file():
            existing_files.append((item, item.relative_to(destination)))
        elif item.is_dir():
            existing_files.extend((path, path.relative_to(destination)) for path in iter_files(item))
    with zipfile.ZipFile(backup, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for index, (path, relative) in enumerate(existing_files, 1):
            archive.write(path, relative.as_posix())
            progress(f"Backing up {relative}", index / max(len(existing_files), 1) * 0.20)
    return len(existing_files)


def clear_scoped_destination(destination: Path) -> None:
    destination = destination.resolve()
    for target in scoped_paths(destination):
        if not target.exists():
            continue
        # Resolve parent rather than a symlink target; only exact allowlisted
        # names immediately below .codex may be removed.
        if target.parent.resolve() != destination:
            raise TransferError(f"Unsafe destination target: {target}")
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()


def copy_stage_to_destination(stage: Path, destination: Path, progress: Progress) -> None:
    files = list(iter_files(stage))
    for index, source in enumerate(files, 1):
        relative = source.relative_to(stage)
        target = destination / relative
        copy2_resilient(source, target)
        progress(f"Installing {relative}", 0.75 + index / max(len(files), 1) * 0.20)


def restore_backup(destination: Path, backup: Path) -> None:
    clear_scoped_destination(destination)
    with zipfile.ZipFile(backup, "r") as archive:
        for info in archive.infolist():
            pure = _safe_zip_name(info.filename)
            if info.is_dir():
                continue
            target = destination.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)


def inspect_codex_data(root: Path, check_rollouts: bool = True) -> dict[str, Any]:
    active = sum(1 for p in iter_files(root / "sessions") if p.suffix.lower() == ".jsonl")
    archived = sum(1 for p in iter_files(root / "archived_sessions") if p.suffix.lower() == ".jsonl")
    automations = sum(1 for p in iter_files(root / "automations") if p.name == "automation.toml")
    result: dict[str, Any] = {
        "active_sessions": active,
        "archived_sessions": archived,
        "session_files": active + archived,
        "attachments": count_files(root / "attachments"),
        "automations": automations,
        "database_threads": None,
        "custom_sections": None,
        "missing_rollout_paths": [],
    }
    database = root / "state_5.sqlite"
    if database.is_file():
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='threads'").fetchone():
                result["database_threads"] = int(conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0])
                columns = {row[1].lower(): row[1] for row in conn.execute("PRAGMA table_info(threads)")}
                if check_rollouts and "rollout_path" in columns:
                    for thread_id, rollout in conn.execute("SELECT id, rollout_path FROM threads WHERE rollout_path IS NOT NULL"):
                        if not Path(str(rollout)).is_file():
                            result["missing_rollout_paths"].append({"thread_id": str(thread_id), "path": str(rollout)})
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='thread_sections'").fetchone():
                result["custom_sections"] = int(conn.execute("SELECT COUNT(*) FROM thread_sections").fetchone()[0])
        except sqlite3.Error as exc:
            result["database_error"] = str(exc)
        finally:
            if conn is not None:
                conn.close()
    result["ok"] = (
        result["database_threads"] == result["session_files"]
        and not result["missing_rollout_paths"]
        and not result.get("database_error")
    )
    return result


def codex_processes() -> list[str]:
    if os.name != "nt":
        return []
    expected = {"codex.exe", "chatgpt.exe"}
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessEntry32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", wintypes.WPARAM),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_snapshot = kernel32.CreateToolhelp32Snapshot
        create_snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
        create_snapshot.restype = wintypes.HANDLE
        process_first = kernel32.Process32FirstW
        process_first.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W))
        process_first.restype = wintypes.BOOL
        process_next = kernel32.Process32NextW
        process_next.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W))
        process_next.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL

        snapshot = create_snapshot(0x00000002, 0)
        if snapshot == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
        found = set()
        try:
            entry = ProcessEntry32W()
            entry.dwSize = ctypes.sizeof(entry)
            success = process_first(snapshot, ctypes.byref(entry))
            while success:
                name = entry.szExeFile.casefold()
                if name in expected:
                    found.add(name)
                success = process_next(snapshot, ctypes.byref(entry))
        finally:
            close_handle(snapshot)
        return sorted(found)
    except (AttributeError, OSError, ValueError):
        pass
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        output = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True, errors="replace", creationflags=flags)
        found = []
        for line in output.splitlines():
            name = line.split('","', 1)[0].strip('"').lower()
            if name in expected:
                found.append(name)
        return sorted(set(found))
    except (OSError, subprocess.SubprocessError):
        return []


def import_package(
    package: Path,
    destination: Path,
    custom_maps: Iterable[tuple[str, str]],
    confirmed_replace: bool,
    progress: Progress = noop_progress,
) -> dict[str, Any]:
    if not confirmed_replace:
        raise TransferError("Replacement confirmation is required. Merge mode is not supported.")
    package, destination = package.resolve(), destination.resolve()
    if is_within(package, destination) or is_within(destination, package):
        raise TransferError("The package and destination .codex directory must not contain one another.")
    running = codex_processes()
    if running:
        raise TransferError("Close Codex/ChatGPT Desktop before importing: " + ", ".join(running))
    verification = verify_package(package, lambda message, fraction: progress(message, None if fraction is None else fraction * 0.18))
    if not verification["ok"]:
        raise TransferError("Package hash verification failed. Destination was not changed.")
    manifest = verification["manifest"]
    maps = parse_path_maps(automatic_path_maps(manifest, destination) + list(custom_maps))
    destination.parent.mkdir(parents=True, exist_ok=True)
    target_profile = discover_profile_key(destination / ".codex-global-state.json")
    backup = destination.parent / "CodexTransferBackups" / f"before-import-{time_stamp()}.zip"
    result: dict[str, Any] = {
        "tool_version": APP_VERSION,
        "mode": "replacement-only",
        "package": str(package),
        "destination": str(destination),
        "started_at": now_iso(),
        "path_maps": [{"old": old, "new": new} for old, new in maps],
        "backup": str(backup),
        "backup_files": 0,
        "rewrite_counts": {},
        "applied": False,
        "rolled_back": False,
        "validation": None,
    }
    with tempfile.TemporaryDirectory(prefix="codex-transfer-import-", dir=str(destination.parent)) as temp:
        stage = Path(temp) / "payload"
        stage.mkdir()
        progress("Extracting verified package", 0.19)
        extract_verified_package(package, stage, manifest)
        result["rewrite_counts"] = rewrite_stage(
            stage, maps, target_profile,
            lambda message, fraction: progress(message, None if fraction is None else 0.20 + fraction * 0.45),
        )
        merge_global_state(stage / GLOBAL_STATE_FILE, destination / GLOBAL_STATE_FILE)
        result["backup_files"] = _archive_existing_destination(destination, backup, progress)
        try:
            clear_scoped_destination(destination)
            destination.mkdir(parents=True, exist_ok=True)
            copy_stage_to_destination(stage, destination, progress)
            result["applied"] = True
        except Exception as exc:
            try:
                restore_backup(destination, backup)
                result["rolled_back"] = True
            except Exception as rollback_exc:
                raise TransferError(f"Import failed and rollback also failed: {exc}; rollback: {rollback_exc}") from exc
            raise TransferError(f"Import failed; previous destination data was restored: {exc}") from exc
    progress("Validating imported data", 0.97)
    validation = inspect_codex_data(destination, check_rollouts=True)
    result["validation"] = validation
    result["finished_at"] = now_iso()
    progress("Import complete" if validation["ok"] else "Import completed with validation warnings", 1.0)
    return result


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
