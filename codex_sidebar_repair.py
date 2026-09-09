#!/usr/bin/env python3
"""Codex Sidebar Repair / Codex 侧栏修复 — Windows GUI and CLI."""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

import codex_sidebar_repair_core as core
import codex_transfer_core as transfer


TEXT = {
    "zh": {
        "title": "Codex 侧栏修复",
        "subtitle": "清除已经删除却仍显示、且无法打开的侧栏缓存条目",
        "language": "语言",
        "codex_dir": "Codex 数据目录",
        "profile": "桌面应用缓存",
        "backup": "备份目录",
        "scan": "只读扫描",
        "repair": "备份并重建侧栏缓存",
        "confirm": "我确认 Codex 已关闭，并同意备份后重建侧栏缓存",
        "status": "进度与结果",
        "running": "● Codex/ChatGPT 正在运行：{names}。请完全关闭",
        "closed": "● Codex 已关闭，可以安全修复",
        "no_profile": "未找到 Codex Desktop 缓存目录",
        "profile_count": "已找到 {count} 个应用缓存目录",
        "warning_title": "修复确认",
        "warning": "本操作不会按标题删除聊天，也不会改动登录 Cookie。它会先备份，再重建桌面端的网页缓存和侧栏状态。云端仍存在的聊天会再次出现。确定继续吗？",
        "done": "修复完成",
        "done_text": "侧栏缓存已备份并移除。现在重新打开 Codex；应用会自动重建缓存。\n\n备份：{backup}",
        "error": "错误",
        "browse": "浏览…",
        "ready": "就绪",
    },
    "en": {
        "title": "Codex Sidebar Repair",
        "subtitle": "Remove stale sidebar cache entries that were deleted but still appear and cannot open",
        "language": "Language",
        "codex_dir": "Codex data directory",
        "profile": "Desktop app cache",
        "backup": "Backup directory",
        "scan": "Read-only scan",
        "repair": "Back up and rebuild sidebar cache",
        "confirm": "I confirm Codex is closed and allow its sidebar cache to be rebuilt after backup",
        "status": "Progress and results",
        "running": "● Codex/ChatGPT is running: {names}. Fully close it",
        "closed": "● Codex is closed; repair is safe to start",
        "no_profile": "Codex Desktop cache directory was not found",
        "profile_count": "Found {count} desktop cache profile(s)",
        "warning_title": "Confirm repair",
        "warning": "This does not delete chats by title and does not change login cookies. It backs up and rebuilds the desktop web/sidebar cache. Chats that still exist in the cloud will reappear. Continue?",
        "done": "Repair complete",
        "done_text": "The sidebar cache was backed up and removed. Reopen Codex; it will rebuild the cache automatically.\n\nBackup: {backup}",
        "error": "Error",
        "browse": "Browse…",
        "ready": "Ready",
    },
}

CORE_ZH_EXACT = {
    "Preparing sidebar cache for backup": "正在准备侧栏缓存备份",
    "Sidebar cache rebuild is ready": "侧栏缓存已准备好重建",
    "Explicit sidebar-cache rebuild confirmation is required.": "必须明确确认后才能重建侧栏缓存。",
    "No Codex Desktop web profile was found.": "未找到 Codex Desktop 网页缓存目录。",
    "No rebuildable Codex sidebar cache was found.": "未找到可以重建的 Codex 侧栏缓存。",
}

CORE_ZH_PREFIXES = (
    ("Close Codex/ChatGPT Desktop before repairing: ", "修复前请完全关闭 Codex/ChatGPT Desktop："),
    ("Refusing an unrecognized Codex web profile: ", "拒绝处理无法识别的 Codex 网页缓存目录："),
    ("Preparing ", "正在准备："),
    ("Backing up ", "正在备份："),
    ("Sidebar backup verification failed at: ", "侧栏备份校验失败："),
    ("Backup is valid, but temporary cache could not be removed: ", "备份有效，但无法移除临时缓存："),
)


def localize_core_message(message: str, language: str) -> str:
    if language != "zh":
        return message
    if message in CORE_ZH_EXACT:
        return CORE_ZH_EXACT[message]
    for english, chinese in CORE_ZH_PREFIXES:
        if message.startswith(english):
            return chinese + message[len(english):]
    return message


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class SidebarRepairApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = tk.Tk()
        self.root.title("Codex Sidebar Repair")
        self.root.geometry("860x590")
        self.root.minsize(740, 520)
        self.language = tk.StringVar(value="中文简体")
        self.codex_dir = tk.StringVar(value=str(transfer.default_codex_dir()))
        self.backup_dir = tk.StringVar(value=str(application_directory() / "CodexSidebarRepairBackups"))
        self.profile_summary = tk.StringVar()
        self.confirmed = tk.BooleanVar(value=False)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.busy = False
        self.widgets: dict[str, Any] = {}
        self.profiles: list[Path] = []
        self._build()
        self._translate()
        self._check_processes()
        self._refresh_profiles()
        self.root.after(100, self._drain)

    def code(self) -> str:
        return "en" if self.language.get() == "English" else "zh"

    def t(self, key: str) -> str:
        return TEXT[self.code()][key]

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        self.widgets["title"] = ttk.Label(header, font=("Segoe UI", 19, "bold"))
        self.widgets["title"].pack(side="left")
        language = ttk.Combobox(header, textvariable=self.language, values=("中文简体", "English"), state="readonly", width=10)
        language.pack(side="right")
        language.bind("<<ComboboxSelected>>", lambda _event: self._translate())
        self.widgets["subtitle"] = ttk.Label(outer, foreground="#555555")
        self.widgets["subtitle"].pack(anchor="w", pady=(2, 8))
        self.process_label = tk.Label(outer, anchor="w", padx=10, pady=7, font=("Segoe UI", 10, "bold"))
        self.process_label.pack(fill="x", pady=(0, 10))

        form = ttk.LabelFrame(outer, padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.widgets["codex_dir"] = ttk.Label(form)
        self.widgets["codex_dir"].grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(form, textvariable=self.codex_dir).grid(row=0, column=1, sticky="ew", pady=6)
        self.widgets["profile"] = ttk.Label(form)
        self.widgets["profile"].grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Label(form, textvariable=self.profile_summary, foreground="#1769AA", wraplength=620).grid(row=1, column=1, sticky="w", pady=6)
        self.widgets["backup"] = ttk.Label(form)
        self.widgets["backup"].grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(form, textvariable=self.backup_dir).grid(row=2, column=1, sticky="ew", pady=6)
        self.widgets["browse"] = ttk.Button(form, command=self._browse_backup, width=11)
        self.widgets["browse"].grid(row=2, column=2, padx=(8, 0), pady=6)
        self.widgets["confirm"] = ttk.Checkbutton(form, variable=self.confirmed, command=self._update_repair_state, wraplength=690)
        self.widgets["confirm"].grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 6))
        buttons = ttk.Frame(form)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", pady=(5, 0))
        self.widgets["scan"] = ttk.Button(buttons, command=self._scan, width=18)
        self.widgets["scan"].pack(side="left", padx=5)
        self.widgets["repair"] = ttk.Button(buttons, command=self._repair, width=36)
        self.widgets["repair"].pack(side="left", padx=5)

        self.widgets["status"] = ttk.Label(outer, font=("Segoe UI", 10, "bold"))
        self.widgets["status"].pack(anchor="w", pady=(12, 4))
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, wrap="word", state="disabled", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _translate(self) -> None:
        for key in ("title", "subtitle", "codex_dir", "profile", "backup", "scan", "repair", "confirm", "status", "browse"):
            self.widgets[key].configure(text=self.t(key))
        self.root.title(self.t("title"))
        self._refresh_profiles()
        self._update_process_label()

    def _browse_backup(self) -> None:
        from tkinter import filedialog
        value = filedialog.askdirectory(title=self.t("backup"), initialdir=self.backup_dir.get() or str(application_directory()))
        if value:
            self.backup_dir.set(value)

    def _refresh_profiles(self) -> None:
        self.profiles = core.discover_codex_profiles()
        if self.profiles:
            self.profile_summary.set(self.t("profile_count").format(count=len(self.profiles)) + "\n" + "\n".join(str(item) for item in self.profiles))
        else:
            self.profile_summary.set(self.t("no_profile"))
        self._update_repair_state()

    def _check_processes(self) -> None:
        self.running = transfer.codex_processes()
        self._update_process_label()
        self._update_repair_state()
        self.root.after(1000, self._check_processes)

    def _update_process_label(self) -> None:
        if not hasattr(self, "running"):
            return
        if self.running:
            self.process_label.configure(text=self.t("running").format(names=", ".join(self.running)), bg="#FDE7E7", fg="#A61B1B")
        else:
            self.process_label.configure(text=self.t("closed"), bg="#E5F5E8", fg="#176B2C")

    def _update_repair_state(self) -> None:
        enabled = bool(self.confirmed.get() and self.profiles and not getattr(self, "running", []) and not self.busy)
        self.widgets["repair"].configure(state="normal" if enabled else "disabled")
        self.widgets["scan"].configure(state="disabled" if self.busy else "normal")

    def _append(self, value: Any) -> None:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _run(self, function: Callable[[], Any], success: Callable[[Any], None]) -> None:
        self.busy = True
        self._update_repair_state()
        def worker() -> None:
            try:
                self.events.put(("success", (success, function())))
            except Exception as exc:
                self.events.put(("error", (exc, traceback.format_exc())))
        threading.Thread(target=worker, daemon=True).start()

    def _drain(self) -> None:
        from tkinter import messagebox
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self._append(localize_core_message(payload[0], self.code()))
                elif kind == "success":
                    self.busy = False
                    self._update_repair_state()
                    callback, result = payload
                    callback(result)
                elif kind == "error":
                    self.busy = False
                    self._update_repair_state()
                    exc, _details = payload
                    visible = localize_core_message(str(exc), self.code())
                    self._append(f"{self.t('error')}: {visible}")
                    messagebox.showerror(self.t("error"), visible)
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _scan(self) -> None:
        self._run(lambda: core.scan_sidebar_state(Path(self.codex_dir.get())), self._append)

    def _repair(self) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno(self.t("warning_title"), self.t("warning"), icon="warning"):
            return
        def progress(message: str, fraction: Optional[float]) -> None:
            self.events.put(("progress", (message, fraction)))
        self._run(
            lambda: core.rebuild_sidebar_cache(self.profiles, Path(self.backup_dir.get()), True, progress),
            self._finish,
        )

    def _finish(self, result: dict[str, Any]) -> None:
        from tkinter import messagebox
        self._append(result)
        self.confirmed.set(False)
        self._refresh_profiles()
        messagebox.showinfo(self.t("done"), self.t("done_text").format(backup=result["backup"]))

    def run(self) -> None:
        self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely rebuild stale Codex Desktop sidebar cache")
    parser.add_argument("--version", action="version", version=f"%(prog)s {core.REPAIR_VERSION}")
    sub = parser.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--codex-dir", default=str(transfer.default_codex_dir()))
    repair = sub.add_parser("repair")
    repair.add_argument("--profile", action="append", default=[])
    repair.add_argument("--backup-dir", required=True)
    repair.add_argument("--yes-rebuild", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scan":
            result = core.scan_sidebar_state(Path(args.codex_dir))
        elif args.command == "repair":
            profiles = [Path(item) for item in args.profile] or core.discover_codex_profiles()
            result = core.rebuild_sidebar_cache(profiles, Path(args.backup_dir), args.yes_rebuild)
        else:
            SidebarRepairApp().run()
            return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (core.RepairError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
