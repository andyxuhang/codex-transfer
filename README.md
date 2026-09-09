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

1. Download `Codex-Transfer.exe` from [Releases](https://github.com/andyxuhang/codex-transfer/releases/latest) and copy it to the root of a USB drive. Run it from the USB drive; no Python installation is required.
2. For the source version, download the source ZIP and double-click `run_codex_transfer.cmd`.
3. The top status bar checks every second: red means Codex/ChatGPT is running; green means it is fully closed.
4. On the blue **Old PC: Export** tab, select the `.codex` directory and package location, then scan and create the package.
5. Copy the complete migration package to the new PC.
6. On the orange **New PC: Replace import** tab, select the package and destination `.codex`, then verify the package.
7. Open **Review and set path maps**. It reads structured path fields, not chat prose, and groups deep references into safe top-level roots.
8. Choose new locations for missing project roots, explicitly keep old paths, or leave them unresolved. User-home and `.codex` changes are mapped automatically.
9. Wait for the status bar to turn green and select the replacement checkbox. The final import button remains disabled until this confirmation is selected. Accept the confirmation dialog and start the import.
10. Keep the backup and result JSON while checking chats, sections, and automations in Codex.

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
2. 如需使用源码版，下载源码 ZIP 后双击 `run_codex_transfer.cmd`。
3. 顶部状态条每秒检查一次 Codex/ChatGPT：红色表示仍在运行，绿色表示已经完全关闭。
4. 在蓝色“旧电脑：导出”页面选择 `.codex` 数据目录和迁移包位置，然后扫描并创建迁移包。
5. 把完整迁移包复制到新电脑。
6. 在橙色“新电脑：覆盖导入”页面选择迁移包和目标 `.codex`，然后校验迁移包。
7. 打开“查看并设置路径映射”。该窗口只读取结构化路径字段，不扫描聊天正文，并把深层引用归并为安全的顶级根目录。
8. 为找不到的项目根目录选择新位置，也可以保持原路径或暂不处理。用户名和 `.codex` 目录变化会自动映射。
9. 确认顶部状态条变绿并勾选覆盖确认框；未勾选时，最终导入按钮会保持灰色且不可点击。随后确认警告弹窗并开始导入。
10. 保存备份和结果 JSON，启动 Codex 检查聊天、分区和自动任务。

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
