# Codex Transfer / Codex 迁移工具

[![tests](https://github.com/andyxuhang/codex-transfer/actions/workflows/test.yml/badge.svg)](https://github.com/andyxuhang/codex-transfer/actions/workflows/test.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A focused, replacement-only Windows migration utility for local Codex and ChatGPT Desktop conversations and their UI metadata.

用于在 Windows 电脑之间安全迁移本地 Codex / ChatGPT Desktop 聊天及其界面元数据的图形工具，仅支持覆盖，不支持合并。

> **Unofficial community tool / 非官方社区工具**
> Codex Transfer is not affiliated with or supported by OpenAI. Local Codex formats may change between app versions. Keep the generated backup and migration package until the destination has been verified.

## English

### What it transfers

- Local chats and Work tasks in `sessions` and `archived_sessions`
- Conversation attachments
- Thread paths and section assignments stored in `state_5.sqlite`
- Custom sidebar sections, pins, and layout state
- Automations and schedules from `automations/*/automation.toml`
- Automatic user-home and `.codex` path migration, plus custom path-prefix maps
- A separate path-review window that groups deep references and lets users decide each project-root mapping

### What it never transfers

These items are hard-coded exclusions to prevent credential or device-identity migration:

- `auth.json` and account tokens
- `.env` and API keys
- Machine-specific `config.toml`
- `installation_id` and device identity
- Plugin runtimes, caches, logs, sandboxes, locks, and temporary files
- Managed workspace contents under `.chatgpt-projects`, project source, and build output
- Generated images, memories, rules, custom skills, and vendor-import directories
- Git repositories, OneDrive folders, and source trees outside `.codex`

Move external workspaces separately with Git, cloud storage, or removable media, then map old roots to their new locations in Codex Transfer.

### Safety model

- Replacement only; database merge is intentionally unavailable.
- SQLite databases are exported through the Backup API for consistent snapshots.
- Every payload file is protected by SHA-256; verification failure blocks import.
- All migratable destination data is backed up before replacement.
- Only allowlisted user-data paths are cleared; destination credentials and machine configuration remain intact.
- Packages use ordinary ZIP compression and are not encrypted. Treat chats, settings, and attachments as sensitive backup data.
- Path rewriting happens in a temporary staging directory and never changes the package.
- Destination workspaces, rules, memories, and skills remain untouched.
- An interrupted installation attempts to restore the pre-import backup automatically.
- Post-import validation compares database threads with JSONL sessions and checks every rollout path.

### Requirements

- Windows 10 or Windows 11
- No Python installation for the portable EXE
- Python 3.9 or later for the source version; runtime code uses only the standard library
- Prefer the same Codex/ChatGPT Desktop version on both computers
- Fully close Codex/ChatGPT Desktop during export and import

### GUI workflow

**Recommended:** Copy `Codex-Transfer.exe` to the root of a USB drive and run it there. The default migration-package path will then also be the USB-drive root, so no extra copy step is needed after export. Keep enough free space on the drive and eject it safely after the package is complete.

1. Download `Codex-Transfer.exe` from [Releases](https://github.com/andyxuhang/codex-transfer/releases/latest), copy it to the root of a USB drive, and run it there. No Python installation is required.
2. On the old PC, fully close Codex/ChatGPT and wait for the status bar to turn green.
3. Open the blue **Old PC: Export** tab. The source `.codex` directory and the package location are normally filled in automatically; use **Scan** if you want to review the contents, then select **Create package**.
4. Wait for completion, close the tool, and safely eject the USB drive. The EXE and migration package are already together on the drive.
5. Connect the USB drive to the new PC and run the same EXE from the drive.
6. Fully close Codex/ChatGPT, open the orange **New PC: Replace import** tab, select the migration package on the USB drive, and verify it. The destination `.codex` directory is normally filled in automatically.
7. Use **Review and set path maps** only if project locations or drive letters changed. User-home and `.codex` changes are mapped automatically; unresolved external project paths can be assigned manually.
8. Select the replacement confirmation checkbox to enable the final import button, accept the warning dialog, and start the import.
9. After completion, open Codex and check chats, sections, and automations. Keep the USB migration package, automatic backup, and result JSON until everything is confirmed.

For the source version, download the source ZIP and double-click `run_codex_transfer.cmd`. The same workflow applies, but the default package location is beside the script rather than beside the EXE.

The progress/output panel remains visible below both tabs. Windows paths may use `/` or `\`; the tool normalizes them to `\` for mapping.

The language selector displays `中文简体` and `English`. The selected language applies to dialogs, errors, progress messages, file filters, and path-source descriptions. JSON report field names remain stable in English for machine-readable compatibility.

The public EXE is built automatically by this repository's GitHub Actions workflow and is published with a SHA-256 file and GitHub build-provenance attestation. The community build is not currently Authenticode-signed with a commercial identity certificate. Verify the Release source, checksum, and provenance if Windows displays an origin warning, or run the public source directly.

### CLI (optional)

```powershell
python codex_transfer.py scan --codex-dir "$env:USERPROFILE\.codex"

python codex_transfer.py export `
  --source "$env:USERPROFILE\.codex" `
  --package "E:\Codex-Transfer.codextransfer.zip"

python codex_transfer.py verify `
  --package "E:\Codex-Transfer.codextransfer.zip"

python codex_transfer.py import `
  --package "E:\Codex-Transfer.codextransfer.zip" `
  --destination "$env:USERPROFILE\.codex" `
  --map "D:\OldProjects=E:\Projects" `
  --yes-replace
```

Running the program without a subcommand opens the GUI.

### Backup location

Before import, the destination data is backed up beside the target `.codex` directory:

```text
C:\Users\<username>\CodexTransferBackups\before-import-YYYYMMDD-HHMMSS.zip
```

Keep both the migration package and backup until the new PC has been verified.

### Important limitations

- Local data formats are undocumented implementation details and may change.
- Cloud-only data remains governed by the signed-in account and is not copied.
- External repositories and `.chatgpt-projects` workspaces are not bundled.
- Importing into a different application version can trigger the application's own database migrations.

---

## 中文说明

### 可以迁移的内容

- `sessions`、`archived_sessions` 中的本地聊天和 Work 任务
- 会话附件
- `state_5.sqlite` 中的线程、项目路径和分区归属
- 自定义侧栏分区、置顶状态和界面布局数据
- `automations/*/automation.toml` 中的自动任务及定时计划
- 不同用户名、盘符和项目根目录的路径映射
- 独立路径检查窗口：归并深层路径、显示引用来源，并在导入前逐项决定是否映射

### 永远不会迁移的内容

为防止账户接管或密钥泄漏，以下项目被硬编码排除，界面中无法开启：

- `auth.json` 和账户令牌
- `.env` 和 API 密钥
- `config.toml` 中的机器专用配置
- `installation_id` 和设备身份
- 插件运行时、缓存、日志、sandbox、锁和临时文件
- `.chatgpt-projects` 托管工作目录、项目源码和构建输出
- 生成图片、记忆、规则、自定义技能及第三方导入目录
- `.codex` 外部的 Git 仓库、OneDrive 文件夹和项目源码

外部项目源码请通过 Git、云盘或移动硬盘单独迁移，然后在工具中把旧根目录映射到新位置。

### 安全设计

- 只支持完整覆盖，不提供数据库合并。
- 导出时使用 SQLite Backup API 创建一致性快照，不直接修改源数据库。
- 迁移包中的每个文件都有 SHA-256；任一文件缺失或改变都会阻止导入。
- 导入前会把目标电脑的全部可迁移数据备份为 ZIP。
- 只清除白名单内的可迁移数据；目标电脑的登录状态和机器配置会保留。
- 迁移包使用普通 ZIP 压缩但不加密；其中的聊天、配置和附件应作为敏感备份保管。
- 路径改写全部在临时目录中完成，不修改原迁移包。
- 目标电脑中的工作目录、规则、记忆和技能不会被覆盖。
- 安装中途失败时会尝试自动恢复导入前备份。
- 导入后自动核对数据库线程、JSONL 会话数量和每个 `rollout_path`。

### 系统要求

- Windows 10 或 Windows 11
- 便携 EXE 不需要安装 Python
- 源码版需要 Python 3.9 或更高版本；运行代码只使用标准库
- 建议旧、新电脑使用相同版本的 Codex/ChatGPT Desktop
- 导出和导入时必须完全退出 Codex/ChatGPT Desktop

### 图形界面使用方法

**推荐用法：**把 `Codex-Transfer.exe` 复制到 U 盘根目录，然后直接从 U 盘运行。程序默认会把迁移包也生成在 U 盘根目录，导出完成后无需再次复制。请确保 U 盘空间充足，并在打包完成后安全弹出。

1. 从 [Releases](https://github.com/andyxuhang/codex-transfer/releases/latest) 下载 `Codex-Transfer.exe`，复制到 U 盘根目录并从 U 盘运行，不需要安装 Python。
2. 在旧电脑上完全退出 Codex/ChatGPT，等待顶部状态条变成绿色。
3. 打开蓝色“旧电脑：导出”页面。源 `.codex` 目录和迁移包位置通常会自动填写；如需先查看内容可点击“扫描”，然后点击“创建迁移包”。
4. 等待创建完成，关闭工具并安全弹出 U 盘。此时 EXE 和迁移包已经一起保存在 U 盘中。
5. 把 U 盘连接到新电脑，直接运行 U 盘中的同一个 EXE。
6. 完全退出 Codex/ChatGPT，打开橙色“新电脑：覆盖导入”页面，选择 U 盘中的迁移包并进行校验。目标 `.codex` 目录通常会自动填写。
7. 只有在项目位置或盘符发生变化时，才需要打开“查看并设置路径映射”。用户目录和 `.codex` 的变化会自动映射；无法识别的外部项目路径可以手动指定。
8. 勾选覆盖确认框以启用最终导入按钮，确认警告弹窗，然后开始导入。
9. 完成后启动 Codex，检查聊天、分区和自动任务。确认全部正常之前，请保留 U 盘中的迁移包、自动备份和结果 JSON。

如需使用源码版，请下载源码 ZIP 并双击 `run_codex_transfer.cmd`。操作流程相同，但迁移包默认保存在脚本旁边，而不是 EXE 旁边。

底部“进度与结果”框会在两个页面中始终显示。Windows 路径可以使用 `/` 或 `\`，工具会统一转换为 `\` 后进行映射。

语言选择显示为“中文简体”和“English”。弹窗、错误、进度日志、文件筛选器和路径来源说明都会跟随界面语言；JSON 报告字段名保持英文，以维持机器可读格式兼容性。

公开 EXE 由本仓库的 GitHub Actions 自动构建，并同时发布 SHA-256 文件和 GitHub 构建来源证明。当前社区版本尚未使用商业身份验证证书进行 Authenticode 签名；如果 Windows 显示来源提醒，请先核对 Release 来源、SHA-256 和构建来源，也可以直接运行公开源码。

### 命令行（可选）

```powershell
python codex_transfer.py scan --codex-dir "$env:USERPROFILE\.codex"

python codex_transfer.py export `
  --source "$env:USERPROFILE\.codex" `
  --package "E:\Codex-Transfer.codextransfer.zip"

python codex_transfer.py verify `
  --package "E:\Codex-Transfer.codextransfer.zip"

python codex_transfer.py import `
  --package "E:\Codex-Transfer.codextransfer.zip" `
  --destination "$env:USERPROFILE\.codex" `
  --map "D:\OldProjects=E:\Projects" `
  --yes-replace
```

没有子命令时会启动图形界面。

### 备份位置

导入前，目标数据会备份到目标 `.codex` 的同级目录：

```text
C:\Users\<用户名>\CodexTransferBackups\before-import-YYYYMMDD-HHMMSS.zip
```

确认新电脑运行正常之前，请保留迁移包和备份。

### 重要限制

- 本地数据格式属于未公开的实现细节，后续可能发生变化。
- 仅存在于云端的数据由登录账号管理，本工具不会复制。
- 外部 Git 仓库和 `.chatgpt-projects` 工作目录不会被打包。
- 跨应用版本导入时，应用自身可能执行数据库迁移。

## Development

```powershell
python -m unittest discover -s tests -v
python codex_transfer.py --version
```

## Security and privacy

Read [SECURITY.md](SECURITY.md). Never attach a real migration package to a public GitHub issue: it contains private conversations and may contain proprietary project metadata.

## License

MIT. See [LICENSE](LICENSE).
