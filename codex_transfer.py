#!/usr/bin/env python3
"""Codex Transfer / Codex 迁移工具 — Windows GUI and CLI entry point."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

import codex_transfer_core as core


TEXT = {
    "zh": {
        "title": "Codex 迁移工具",
        "subtitle": "将旧电脑上的聊天、Work 任务、分区和自动任务安全覆盖到新电脑",
        "export": "⬆ 旧电脑：导出",
        "export_banner": "第 1 步 · 在旧电脑创建迁移包",
        "source": "Codex 数据目录",
        "package": "迁移包",
        "browse": "浏览…",
        "scan": "扫描",
        "create": "创建迁移包",
        "open_package_folder": "打开迁移包文件夹",
        "verify": "校验迁移包",
        "import": "⬇ 新电脑：覆盖导入",
        "import_banner": "第 2 步 · 在新电脑备份并覆盖导入",
        "destination": "目标 Codex 目录",
        "auto_map": "自动路径映射",
        "auto_map_default": "选择迁移包后自动显示；大多数用户无需手动映射",
        "auto_map_same": "源目录与目标目录相同，无需路径转换",
        "inspect_paths": "查看并设置路径映射",
        "path_map_summary": "尚未检查迁移包中的路径",
        "path_map_count": "已检查 {total} 个顶级路径，已设置 {custom} 项",
        "path_dialog_title": "迁移路径检查与映射",
        "path_privacy": "迁移包未加密，聊天和配置可被读取。下表只列出结构化路径，不扫描聊天正文。",
        "path_old": "旧电脑顶级路径",
        "path_new": "新电脑位置",
        "path_count": "引用次数",
        "path_source": "来源",
        "path_status": "状态",
        "path_auto": "自动映射",
        "path_exists": "原路径存在",
        "path_missing": "需要确认",
        "choose_new_path": "为选中项选择新位置",
        "keep_old_path": "保持原路径（不映射）",
        "clear_path": "恢复自动建议／暂不处理",
        "apply_path_maps": "应用所选映射",
        "select_path_row": "请先选择一条路径。",
        "confirm": "我确认目标中的聊天、Work、分区和自动任务可以被备份后覆盖（不合并）",
        "apply": "备份并覆盖导入",
        "log": "进度与结果",
        "ready": "就绪",
        "busy": "正在处理…",
        "done": "完成",
        "error": "错误",
        "warning": "安全提醒",
        "close_app": "执行导入前请完全退出 Codex/ChatGPT Desktop。",
        "confirm_dialog": "目标可迁移数据将先备份，再被迁移包完整替换。登录令牌和机器配置不会改变。确定继续吗？",
        "choose_source": "选择 .codex 数据目录",
        "choose_package_save": "保存 Codex Transfer 迁移包",
        "choose_package": "选择 Codex Transfer 迁移包",
        "choose_destination": "选择目标 .codex 目录",
        "package_ok": "迁移包校验通过",
        "version": "版本",
        "folder_missing": "迁移包所在文件夹尚不存在。",
        "codex_running": "● Codex/ChatGPT 正在运行：{names}。请完全关闭后再迁移",
        "codex_closed": "● Codex 已关闭，可以安全迁移",
    },
    "en": {
        "title": "Codex Transfer",
        "subtitle": "Safely replace chats, Work tasks, sidebar sections, and automations on a new PC",
        "export": "⬆ Old PC: Export",
        "export_banner": "STEP 1 · Create the package on the old PC",
        "source": "Codex data directory",
        "package": "Migration package",
        "browse": "Browse…",
        "scan": "Scan",
        "create": "Create package",
        "open_package_folder": "Open package folder",
        "verify": "Verify package",
        "import": "⬇ New PC: Replace import",
        "import_banner": "STEP 2 · Back up and replace on the new PC",
        "destination": "Destination Codex directory",
        "auto_map": "Automatic path maps",
        "auto_map_default": "Select a package to preview; most users need no manual map",
        "auto_map_same": "Source and destination paths match; no path conversion is needed",
        "inspect_paths": "Review and set path maps",
        "path_map_summary": "Package paths have not been inspected",
        "path_map_count": "Reviewed {total} top-level paths; {custom} custom choices",
        "path_dialog_title": "Migration path review and mapping",
        "path_privacy": "The package is not encrypted, so chats and settings are readable. Only structured paths are listed; chat text is not scanned.",
        "path_old": "Old PC top-level path",
        "path_new": "New PC location",
        "path_count": "References",
        "path_source": "Source",
        "path_status": "Status",
        "path_auto": "Automatic",
        "path_exists": "Original exists",
        "path_missing": "Review needed",
        "choose_new_path": "Choose new location",
        "keep_old_path": "Keep original (no mapping)",
        "clear_path": "Reset suggestion / leave unresolved",
        "apply_path_maps": "Apply selected maps",
        "select_path_row": "Select a path first.",
        "confirm": "I confirm destination chats, Work data, sections, and automations may be backed up and replaced (no merge)",
        "apply": "Back up and replace",
        "log": "Progress and results",
        "ready": "Ready",
        "busy": "Working…",
        "done": "Complete",
        "error": "Error",
        "warning": "Safety notice",
        "close_app": "Fully close Codex/ChatGPT Desktop before importing.",
        "confirm_dialog": "Migratable destination data will be backed up, then fully replaced. Account tokens and machine configuration remain untouched. Continue?",
        "choose_source": "Select .codex data directory",
        "choose_package_save": "Save Codex Transfer package",
        "choose_package": "Select Codex Transfer package",
        "choose_destination": "Select destination .codex directory",
        "package_ok": "Package verification passed",
        "version": "Version",
        "folder_missing": "The migration package folder does not exist yet.",
        "codex_running": "● Codex/ChatGPT is running: {names}. Fully close it before migration",
        "codex_closed": "● Codex is closed; migration is safe to start",
    },
}


def translation_key(widget_key: str) -> str:
    if widget_key == "package_import":
        return "package"
    if widget_key.endswith("_browse"):
        return "browse"
    return widget_key


class CodexTransferApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title("Codex Transfer")
        self.root.geometry("920x680")
        self.root.minsize(780, 590)
        self.language = tk.StringVar(value="zh")
        self.source = tk.StringVar(value=str(core.default_codex_dir()))
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        default_package = application_directory() / f"Codex-Transfer-{stamp}.codextransfer.zip"
        self.export_package = tk.StringVar(value=str(default_package))
        self.import_package = tk.StringVar(value="")
        self.destination = tk.StringVar(value=str(core.default_codex_dir()))
        self.auto_map_text = tk.StringVar(value=TEXT["zh"]["auto_map_default"])
        self.path_map_summary = tk.StringVar(value=TEXT["zh"]["path_map_summary"])
        self.custom_maps: list[tuple[str, str]] = []
        self.confirmed = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value=TEXT["zh"]["ready"])
        self.progress_value = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._last_progress_event_at = 0.0
        self._last_codex_processes: list[str] = []
        self.widgets: dict[str, Any] = {}
        self.busy_buttons: list[Any] = []
        self._build()
        self._translate()
        self._check_codex_status()
        self.root.after(100, self._drain_events)

    def t(self, key: str) -> str:
        return TEXT[self.language.get()][key]

    def _label(self, parent: Any, key: str, **kwargs: Any) -> Any:
        widget = self.ttk.Label(parent, **kwargs)
        self.widgets[key] = widget
        return widget

    def _button(self, parent: Any, key: str, command: Callable[[], None], **kwargs: Any) -> Any:
        widget = self.ttk.Button(parent, command=command, **kwargs)
        self.widgets[key] = widget
        self.busy_buttons.append(widget)
        return widget

    def _build_path_row(self, parent: Any, row: int, label_key: str, variable: Any, browse: Callable[[], None]) -> Any:
        self._label(parent, label_key).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        entry = self.ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        entry.bind("<FocusOut>", lambda _event: self._normalize_variable(variable))
        self._button(parent, f"{label_key}_browse", browse, width=11).grid(row=row, column=2, padx=(8, 0), pady=6)
        return entry

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        self.widgets["title"] = ttk.Label(header, font=("Segoe UI", 20, "bold"))
        self.widgets["title"].pack(side="left")
        language_box = ttk.Combobox(header, textvariable=self.language, values=("zh", "en"), state="readonly", width=5)
        language_box.pack(side="right")
        language_box.bind("<<ComboboxSelected>>", lambda _: self._translate())
        self.widgets["subtitle"] = ttk.Label(outer, foreground="#555555")
        self.widgets["subtitle"].pack(anchor="w", pady=(2, 6))
        self.codex_status_label = tk.Label(outer, anchor="w", padx=10, pady=7, font=("Segoe UI", 10, "bold"))
        self.codex_status_label.pack(fill="x", pady=(0, 8))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="x", pady=(0, 8))

        export_box = ttk.Frame(self.notebook, padding=12)
        export_box.columnconfigure(1, weight=1)
        self.notebook.add(export_box)
        self.export_page = export_box
        self.widgets["export_banner"] = tk.Label(export_box, bg="#1769AA", fg="white", anchor="w", padx=12, pady=9, font=("Segoe UI", 12, "bold"))
        self.widgets["export_banner"].grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self._build_path_row(export_box, 1, "source", self.source, self._browse_source)
        self._build_path_row(export_box, 2, "package", self.export_package, self._browse_export_package)
        actions = ttk.Frame(export_box)
        actions.grid(row=3, column=1, columnspan=2, sticky="e", pady=(8, 0))
        self._button(actions, "scan", self._scan).pack(side="left", padx=4)
        self._button(actions, "create", self._export).pack(side="left", padx=4)
        self._button(actions, "open_package_folder", self._open_export_folder).pack(side="left", padx=4)

        import_box = ttk.Frame(self.notebook, padding=12)
        import_box.columnconfigure(1, weight=1)
        self.notebook.add(import_box)
        self.import_page = import_box
        self.widgets["import_banner"] = tk.Label(import_box, bg="#B54708", fg="white", anchor="w", padx=12, pady=9, font=("Segoe UI", 12, "bold"))
        self.widgets["import_banner"].grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        package_entry = self._build_path_row(import_box, 1, "package_import", self.import_package, self._browse_import_package)
        destination_entry = self._build_path_row(import_box, 2, "destination", self.destination, self._browse_destination)
        package_entry.bind("<FocusOut>", self._path_inputs_changed, add="+")
        destination_entry.bind("<FocusOut>", self._path_inputs_changed, add="+")
        self._label(import_box, "auto_map").grid(row=3, column=0, sticky="nw", padx=(0, 10), pady=6)
        ttk.Label(import_box, textvariable=self.auto_map_text, foreground="#1769AA", wraplength=650, justify="left").grid(row=3, column=1, columnspan=2, sticky="w", pady=6)
        mapping_row = ttk.Frame(import_box)
        mapping_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(7, 2))
        mapping_row.columnconfigure(0, weight=1)
        ttk.Label(mapping_row, textvariable=self.path_map_summary, foreground="#7A4E00").grid(row=0, column=0, sticky="w")
        self._button(mapping_row, "inspect_paths", self._inspect_paths).grid(row=0, column=1, padx=(10, 0))
        self.widgets["confirm"] = ttk.Checkbutton(import_box, variable=self.confirmed)
        self.widgets["confirm"].grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 4))
        actions2 = ttk.Frame(import_box)
        actions2.grid(row=6, column=1, columnspan=2, sticky="e", pady=(4, 0))
        self._button(actions2, "verify", self._verify).pack(side="left", padx=4)
        self._button(actions2, "apply", self._import).pack(side="left", padx=4)

        status_row = ttk.Frame(outer)
        status_row.pack(fill="x", pady=(0, 8))
        ttk.Progressbar(status_row, variable=self.progress_value, maximum=100).pack(side="left", fill="x", expand=True)
        ttk.Label(status_row, textvariable=self.status, width=18, anchor="e").pack(side="right", padx=(10, 0))
        self.widgets["log"] = ttk.Label(outer)
        self.widgets["log"].pack(anchor="w")
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True, pady=(5, 0))
        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _translate(self) -> None:
        self.notebook.tab(self.export_page, text=self.t("export"))
        self.notebook.tab(self.import_page, text=self.t("import"))
        for key, widget in self.widgets.items():
            translated_key = translation_key(key)
            if translated_key in TEXT[self.language.get()]:
                widget.configure(text=self.t(translated_key))
        self.status.set(self.t("ready"))
        self.root.title(f"{self.t('title')} — {core.APP_VERSION}")
        self._render_codex_status()
        self._refresh_auto_map()
        if not self.custom_maps:
            self.path_map_summary.set(self.t("path_map_summary"))

    def _render_codex_status(self) -> None:
        if self._last_codex_processes:
            text = self.t("codex_running").format(names=", ".join(self._last_codex_processes))
            self.codex_status_label.configure(text=text, fg="#B42318", bg="#FEE4E2")
        else:
            self.codex_status_label.configure(text=self.t("codex_closed"), fg="#067647", bg="#ECFDF3")

    def _check_codex_status(self) -> None:
        self._last_codex_processes = core.codex_processes()
        self._render_codex_status()
        self.root.after(1000, self._check_codex_status)

    def _browse_source(self) -> None:
        from tkinter import filedialog
        value = filedialog.askdirectory(title=self.t("choose_source"), initialdir=self.source.get())
        if value:
            self.source.set(core.normalize_path_text(value))

    def _browse_export_package(self) -> None:
        from tkinter import filedialog
        value = filedialog.asksaveasfilename(
            title=self.t("choose_package_save"), initialfile="Codex-Transfer.codextransfer.zip",
            initialdir=str(Path(self.export_package.get()).parent),
            defaultextension=".zip", filetypes=(("Codex Transfer", "*.zip"),),
        )
        if value:
            self.export_package.set(core.normalize_path_text(value))

    def _browse_import_package(self) -> None:
        from tkinter import filedialog
        value = filedialog.askopenfilename(title=self.t("choose_package"), filetypes=(("Codex Transfer", "*.zip"), ("All files", "*.*")))
        if value:
            self.import_package.set(core.normalize_path_text(value))
            self.custom_maps.clear()
            self.path_map_summary.set(self.t("path_map_summary"))
            self._refresh_auto_map()

    def _browse_destination(self) -> None:
        from tkinter import filedialog
        value = filedialog.askdirectory(title=self.t("choose_destination"), initialdir=self.destination.get())
        if value:
            self.destination.set(core.normalize_path_text(value))
            self.custom_maps.clear()
            self.path_map_summary.set(self.t("path_map_summary"))
            self._refresh_auto_map()

    def _open_export_folder(self) -> None:
        from tkinter import messagebox
        folder = Path(self._normalize_variable(self.export_package)).parent.resolve()
        if not folder.is_dir():
            messagebox.showwarning(self.t("warning"), self.t("folder_missing"))
            return
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            else:
                raise OSError("This shortcut is available on Windows only.")
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc))

    def _refresh_auto_map(self) -> None:
        package_text = self.import_package.get().strip()
        if not package_text:
            self.auto_map_text.set(self.t("auto_map_default"))
            return
        try:
            package = Path(core.normalize_path_text(package_text))
            destination = Path(core.normalize_path_text(self.destination.get())).resolve()
            manifest = core.read_package_manifest(package)
            maps = core.automatic_path_maps(manifest, destination)
            if maps:
                self.auto_map_text.set("\n".join(f"{old}  →  {new}" for old, new in maps))
            else:
                self.auto_map_text.set(self.t("auto_map_same"))
        except (core.TransferError, OSError):
            self.auto_map_text.set(self.t("auto_map_default"))

    def _path_inputs_changed(self, _event: Any = None) -> None:
        self.custom_maps.clear()
        self.path_map_summary.set(self.t("path_map_summary"))
        self._refresh_auto_map()

    def _normalize_variable(self, variable: Any) -> str:
        value = core.normalize_path_text(variable.get())
        variable.set(value)
        return value

    def _map_values(self) -> list[tuple[str, str]]:
        return list(self.custom_maps)

    def _inspect_paths(self) -> None:
        from tkinter import messagebox
        package_text = self._normalize_variable(self.import_package)
        if not package_text or not Path(package_text).is_file():
            messagebox.showwarning(self.t("warning"), self.t("choose_package"))
            return
        package = Path(package_text)
        destination = Path(self._normalize_variable(self.destination))
        self._run(
            lambda: core.inspect_package_paths(package, destination, self._progress),
            self._show_path_dialog,
        )

    def _show_path_dialog(self, report: dict[str, Any]) -> None:
        from tkinter import filedialog, messagebox, ttk
        window = self.tk.Toplevel(self.root)
        window.title(self.t("path_dialog_title"))
        window.geometry("1040x560")
        window.minsize(820, 430)
        window.transient(self.root)
        window.grab_set()
        body = ttk.Frame(window, padding=14)
        body.pack(fill="both", expand=True)
        self.tk.Label(
            body, text=self.t("path_privacy"), bg="#FFF4E5", fg="#7A2E0E",
            anchor="w", justify="left", padx=10, pady=8,
        ).pack(fill="x", pady=(0, 10))
        columns = ("old", "new", "count", "source", "status")
        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "old": self.t("path_old"), "new": self.t("path_new"),
            "count": self.t("path_count"), "source": self.t("path_source"),
            "status": self.t("path_status"),
        }
        widths = {"old": 280, "new": 280, "count": 75, "source": 150, "status": 105}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], minwidth=60, stretch=column in {"old", "new", "source"})
        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        rows = report.get("paths", [])
        automatic = {item["old"].casefold(): item["new"] for item in report.get("automatic_maps", [])}
        existing_custom = {old.casefold(): new for old, new in self.custom_maps}

        def status_text(row: dict[str, Any]) -> str:
            if row.get("automatic"):
                return self.t("path_auto")
            return self.t("path_exists") if row.get("exists") else self.t("path_missing")

        def refresh_row(index: int) -> None:
            row = rows[index]
            tree.item(str(index), values=(
                row["old"], row.get("new", ""), row.get("count", 0),
                ", ".join(row.get("sources", [])), status_text(row),
            ))

        for index, row in enumerate(rows):
            if row["old"].casefold() in existing_custom:
                row["new"] = existing_custom[row["old"].casefold()]
            tree.insert("", "end", iid=str(index))
            refresh_row(index)

        def selected_index() -> Optional[int]:
            selection = tree.selection()
            if not selection:
                messagebox.showwarning(self.t("warning"), self.t("select_path_row"), parent=window)
                return None
            return int(selection[0])

        def choose_new() -> None:
            index = selected_index()
            if index is None:
                return
            row = rows[index]
            initial = row.get("new") or str(Path(self.destination.get()).parent)
            value = filedialog.askdirectory(title=self.t("choose_new_path"), initialdir=initial, parent=window)
            if value:
                row["new"] = core.normalize_path_text(value)
                refresh_row(index)

        def keep_old() -> None:
            index = selected_index()
            if index is not None:
                rows[index]["new"] = rows[index]["old"]
                refresh_row(index)

        def clear_new() -> None:
            index = selected_index()
            if index is not None:
                old = rows[index]["old"]
                rows[index]["new"] = automatic.get(old.casefold(), "")
                refresh_row(index)

        def apply_maps() -> None:
            choices: list[tuple[str, str]] = []
            for row in rows:
                old, new = row["old"], row.get("new", "")
                auto_new = automatic.get(old.casefold())
                if auto_new is not None:
                    if new and core.normalize_path_text(new).casefold() != core.normalize_path_text(auto_new).casefold():
                        choices.append((old, new))
                elif new and core.normalize_path_text(new).casefold() != core.normalize_path_text(old).casefold():
                    choices.append((old, new))
            self.custom_maps = core.parse_path_maps(choices) if choices else []
            self.path_map_summary.set(self.t("path_map_count").format(total=len(rows), custom=len(self.custom_maps)))
            window.destroy()

        controls = ttk.Frame(body)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text=self.t("choose_new_path"), command=choose_new).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text=self.t("keep_old_path"), command=keep_old).pack(side="left", padx=6)
        ttk.Button(controls, text=self.t("clear_path"), command=clear_new).pack(side="left", padx=6)
        ttk.Button(controls, text=self.t("apply_path_maps"), command=apply_maps).pack(side="right")
        self.path_map_summary.set(self.t("path_map_count").format(total=len(rows), custom=len(self.custom_maps)))

    def _set_busy(self, busy: bool) -> None:
        for button in self.busy_buttons:
            button.configure(state="disabled" if busy else "normal")
        self.status.set(self.t("busy") if busy else self.t("ready"))
        if not busy:
            self.progress_value.set(0)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        line_count = int(self.log.index("end-1c").split(".", 1)[0])
        if line_count > 2500:
            self.log.delete("1.0", "501.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _progress(self, message: str, fraction: Optional[float]) -> None:
        now = time.monotonic()
        force = fraction is None or fraction is not None and fraction >= 1.0
        if not force and now - self._last_progress_event_at < 0.15:
            return
        self._last_progress_event_at = now
        self.events.put(("progress", (message, fraction)))

    def _run(self, function: Callable[[], Any], success: Callable[[Any], None]) -> None:
        self._set_busy(True)
        def worker() -> None:
            try:
                result = function()
                self.events.put(("success", (success, result)))
            except Exception as exc:
                self.events.put(("error", (exc, traceback.format_exc())))
        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        from tkinter import messagebox
        try:
            for _ in range(50):
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    message, fraction = payload
                    self._append_log(message)
                    if fraction is not None:
                        self.progress_value.set(max(0, min(100, fraction * 100)))
                elif kind == "success":
                    callback, result = payload
                    self._set_busy(False)
                    callback(result)
                elif kind == "error":
                    exc, details = payload
                    self._set_busy(False)
                    self._append_log(details)
                    messagebox.showerror(self.t("error"), str(exc))
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _scan(self) -> None:
        source = Path(self._normalize_variable(self.source))
        self._run(lambda: core.source_inventory(source), self._show_json)

    def _export(self) -> None:
        source = Path(self._normalize_variable(self.source))
        package = Path(self._normalize_variable(self.export_package))
        self._run(
            lambda: core.create_package(source, package, self._progress),
            lambda result: self._finish_export(result),
        )

    def _finish_export(self, result: dict[str, Any]) -> None:
        from tkinter import messagebox
        self.import_package.set(self.export_package.get())
        self._refresh_auto_map()
        self._show_json(result)
        messagebox.showinfo(self.t("done"), str(Path(self.export_package.get()).resolve()))

    def _verify(self) -> None:
        package = Path(self._normalize_variable(self.import_package))
        self._run(lambda: core.verify_package(package, self._progress), self._finish_verify)

    def _finish_verify(self, result: dict[str, Any]) -> None:
        from tkinter import messagebox
        visible = {key: value for key, value in result.items() if key != "manifest"}
        self._show_json(visible)
        if result["ok"]:
            messagebox.showinfo(self.t("done"), self.t("package_ok"))
        else:
            messagebox.showerror(self.t("error"), json.dumps(visible, ensure_ascii=False, indent=2))

    def _import(self) -> None:
        from tkinter import messagebox
        if not self.confirmed.get():
            messagebox.showwarning(self.t("warning"), self.t("confirm"))
            return
        if not messagebox.askyesno(self.t("warning"), self.t("confirm_dialog"), icon="warning"):
            return
        package = Path(self._normalize_variable(self.import_package))
        destination = Path(self._normalize_variable(self.destination))
        result_path = package.with_name(package.stem + ".import-result.json")
        self._run(
            lambda: core.import_package(
                package, destination, self._map_values(), True, self._progress,
            ),
            lambda result: self._finish_import(result, result_path),
        )

    def _finish_import(self, result: dict[str, Any], result_path: Path) -> None:
        from tkinter import messagebox
        core.write_result(result_path, result)
        self._show_json(result)
        messagebox.showinfo(self.t("done"), f"{result_path}\n\n{self.t('close_app')}")

    def _show_json(self, value: Any) -> None:
        self._append_log(json.dumps(value, ensure_ascii=False, indent=2))

    def run(self) -> None:
        self.root.mainloop()


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Transfer — replacement-only local Codex migration")
    parser.add_argument("--version", action="version", version=f"%(prog)s {core.APP_VERSION}")
    sub = parser.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--codex-dir", default=str(core.default_codex_dir()))
    export = sub.add_parser("export")
    export.add_argument("--source", default=str(core.default_codex_dir()))
    export.add_argument("--package", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--package", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--package", required=True)
    imp.add_argument("--destination", default=str(core.default_codex_dir()))
    imp.add_argument("--map", action="append", default=[], metavar="OLD=NEW")
    imp.add_argument("--yes-replace", action="store_true")
    imp.add_argument("--result")
    return parser


def cli_progress(message: str, fraction: Optional[float]) -> None:
    if fraction is None:
        print(message)
    else:
        print(f"[{fraction * 100:5.1f}%] {message}")


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.command:
        CodexTransferApp().run()
        return 0
    try:
        if args.command == "scan":
            result = core.source_inventory(Path(args.codex_dir))
        elif args.command == "export":
            result = core.create_package(Path(args.source), Path(args.package), cli_progress)
        elif args.command == "verify":
            result = core.verify_package(Path(args.package), cli_progress)
            result = {key: value for key, value in result.items() if key != "manifest"}
            if not result["ok"]:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 4
        else:
            maps = []
            for value in args.map:
                if "=" not in value:
                    raise core.TransferError(f"Invalid --map value: {value}")
                maps.append(tuple(value.split("=", 1)))
            result = core.import_package(
                Path(args.package), Path(args.destination), maps, args.yes_replace, cli_progress,
            )
            result_path = Path(args.result) if args.result else Path(args.package).with_name(Path(args.package).stem + ".import-result.json")
            core.write_result(result_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (core.TransferError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
