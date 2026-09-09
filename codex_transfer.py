#!/usr/bin/env python3
"""Codex Transfer / Codex 迁移工具 — Windows GUI and CLI entry point."""

from __future__ import annotations

import argparse
import json
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
        "export": "旧电脑：导出",
        "source": "Codex 数据目录",
        "package": "迁移包",
        "browse": "浏览…",
        "scan": "扫描",
        "create": "创建迁移包",
        "verify": "校验迁移包",
        "import": "新电脑：覆盖导入",
        "destination": "目标 Codex 目录",
        "old_path": "旧路径前缀",
        "new_path": "新路径前缀",
        "add_map": "添加路径映射",
        "remove_map": "删除选中映射",
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
        "map_missing": "请同时填写旧路径和新路径。",
        "package_ok": "迁移包校验通过",
        "version": "版本",
    },
    "en": {
        "title": "Codex Transfer",
        "subtitle": "Safely replace chats, Work tasks, sidebar sections, and automations on a new PC",
        "export": "Old PC: Export",
        "source": "Codex data directory",
        "package": "Migration package",
        "browse": "Browse…",
        "scan": "Scan",
        "create": "Create package",
        "verify": "Verify package",
        "import": "New PC: Replace import",
        "destination": "Destination Codex directory",
        "old_path": "Old path prefix",
        "new_path": "New path prefix",
        "add_map": "Add path map",
        "remove_map": "Remove selected map",
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
        "map_missing": "Enter both old and new path prefixes.",
        "package_ok": "Package verification passed",
        "version": "Version",
    },
}


class CodexTransferApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title("Codex Transfer")
        self.root.geometry("900x690")
        self.root.minsize(760, 600)
        self.language = tk.StringVar(value="zh")
        self.source = tk.StringVar(value=str(core.default_codex_dir()))
        default_package = Path.home() / "Desktop" / "Codex-Transfer.codextransfer.zip"
        self.export_package = tk.StringVar(value=str(default_package))
        self.import_package = tk.StringVar(value="")
        self.destination = tk.StringVar(value=str(core.default_codex_dir()))
        self.old_path = tk.StringVar()
        self.new_path = tk.StringVar()
        self.confirmed = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value=TEXT["zh"]["ready"])
        self.progress_value = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._last_progress_event_at = 0.0
        self.widgets: dict[str, Any] = {}
        self.busy_buttons: list[Any] = []
        self._build()
        self._translate()
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

    def _build_path_row(self, parent: Any, row: int, label_key: str, variable: Any, browse: Callable[[], None]) -> None:
        self._label(parent, label_key).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        entry = self.ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        entry.bind("<FocusOut>", lambda _event: self._normalize_variable(variable))
        self._button(parent, f"{label_key}_browse", browse, width=11).grid(row=row, column=2, padx=(8, 0), pady=6)

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        self.widgets["title"] = ttk.Label(header, font=("Segoe UI", 20, "bold"))
        self.widgets["title"].pack(side="left")
        language_box = ttk.Combobox(header, textvariable=self.language, values=("zh", "en"), state="readonly", width=5)
        language_box.pack(side="right")
        language_box.bind("<<ComboboxSelected>>", lambda _: self._translate())
        self.widgets["subtitle"] = ttk.Label(outer, foreground="#555555")
        self.widgets["subtitle"].pack(anchor="w", pady=(3, 14))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="x", pady=(0, 12))

        export_box = ttk.Frame(self.notebook, padding=12)
        export_box.columnconfigure(1, weight=1)
        self.notebook.add(export_box)
        self.export_page = export_box
        self._build_path_row(export_box, 0, "source", self.source, self._browse_source)
        self._build_path_row(export_box, 1, "package", self.export_package, self._browse_export_package)
        actions = ttk.Frame(export_box)
        actions.grid(row=2, column=1, columnspan=2, sticky="e", pady=(8, 0))
        self._button(actions, "scan", self._scan).pack(side="left", padx=4)
        self._button(actions, "create", self._export).pack(side="left", padx=4)

        import_box = ttk.Frame(self.notebook, padding=12)
        import_box.columnconfigure(1, weight=1)
        self.notebook.add(import_box)
        self.import_page = import_box
        self._build_path_row(import_box, 0, "package_import", self.import_package, self._browse_import_package)
        self._build_path_row(import_box, 1, "destination", self.destination, self._browse_destination)
        self._label(import_box, "old_path").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        old_entry = ttk.Entry(import_box, textvariable=self.old_path)
        old_entry.grid(row=2, column=1, sticky="ew", pady=6)
        old_entry.bind("<FocusOut>", lambda _event: self._normalize_variable(self.old_path))
        self._label(import_box, "new_path").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
        new_entry = ttk.Entry(import_box, textvariable=self.new_path)
        new_entry.grid(row=3, column=1, sticky="ew", pady=6)
        new_entry.bind("<FocusOut>", lambda _event: self._normalize_variable(self.new_path))
        self._button(import_box, "add_map", self._add_map).grid(row=2, column=2, rowspan=2, padx=(8, 0))
        self.maps = tk.Listbox(import_box, height=3, selectmode="extended")
        self.maps.grid(row=4, column=1, sticky="ew", pady=6)
        self._button(import_box, "remove_map", self._remove_map).grid(row=4, column=2, padx=(8, 0))
        self.widgets["confirm"] = ttk.Checkbutton(import_box, variable=self.confirmed)
        self.widgets["confirm"].grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 4))
        actions2 = ttk.Frame(import_box)
        actions2.grid(row=6, column=1, columnspan=2, sticky="e", pady=(6, 0))
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
            translated_key = "package" if key == "package_import" else (key[:-7] if key.endswith("_browse") else key)
            if translated_key in TEXT[self.language.get()]:
                widget.configure(text=self.t(translated_key))
        self.status.set(self.t("ready"))
        self.root.title(f"{self.t('title')} — {core.APP_VERSION}")

    def _browse_source(self) -> None:
        from tkinter import filedialog
        value = filedialog.askdirectory(title=self.t("choose_source"), initialdir=self.source.get())
        if value:
            self.source.set(core.normalize_path_text(value))

    def _browse_export_package(self) -> None:
        from tkinter import filedialog
        value = filedialog.asksaveasfilename(
            title=self.t("choose_package_save"), initialfile="Codex-Transfer.codextransfer.zip",
            defaultextension=".zip", filetypes=(("Codex Transfer", "*.zip"),),
        )
        if value:
            self.export_package.set(core.normalize_path_text(value))

    def _browse_import_package(self) -> None:
        from tkinter import filedialog
        value = filedialog.askopenfilename(title=self.t("choose_package"), filetypes=(("Codex Transfer", "*.zip"), ("All files", "*.*")))
        if value:
            self.import_package.set(core.normalize_path_text(value))

    def _browse_destination(self) -> None:
        from tkinter import filedialog
        value = filedialog.askdirectory(title=self.t("choose_destination"), initialdir=self.destination.get())
        if value:
            self.destination.set(core.normalize_path_text(value))

    def _normalize_variable(self, variable: Any) -> str:
        value = core.normalize_path_text(variable.get())
        variable.set(value)
        return value

    def _add_map(self) -> None:
        from tkinter import messagebox
        old = self._normalize_variable(self.old_path)
        new = self._normalize_variable(self.new_path)
        if not old or not new:
            messagebox.showwarning(self.t("warning"), self.t("map_missing"))
            return
        self.maps.insert("end", f"{old}  →  {new}")
        self.old_path.set("")
        self.new_path.set("")

    def _remove_map(self) -> None:
        for index in reversed(self.maps.curselection()):
            self.maps.delete(index)

    def _map_values(self) -> list[tuple[str, str]]:
        output = []
        for item in self.maps.get(0, "end"):
            old, new = item.split("  →  ", 1)
            output.append((old, new))
        return output

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
