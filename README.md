# Codex Transfer / Codex 迁移工具

[![tests](https://github.com/andyxuhang/codex-transfer/actions/workflows/test.yml/badge.svg)](https://github.com/andyxuhang/codex-transfer/actions/workflows/test.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A safe, replacement-only Windows migration utility for local Codex and ChatGPT Desktop data.

用于在 Windows 电脑之间安全迁移本地 Codex / ChatGPT Desktop 数据的图形工具，仅支持覆盖，不支持合并。

> **Unofficial community tool / 非官方社区工具**
> Codex Transfer is not affiliated with or supported by OpenAI. Local Codex formats may change between app versions. Always retain the generated backup and migration package until the destination has been verified.

## 中文说明

### 能迁移什么

- 本地聊天与 Work 任务：`sessions`、`archived_sessions`
- 会话附件和生成内容
- SQLite 中的线程、项目、分区归属、排序及历史元数据
- 自定义侧栏分区、置顶状态和界面布局数据
- 自动任务及其定时计划：`automations/*/automation.toml`
- Codex 管理的本地工作目录：`.chatgpt-projects`
- 用户规则、记忆、自定义技能和导入数据
- 不同用户名、盘符和项目根目录的路径映射

### 永远不会迁移什么

为了防止账户接管或密钥泄漏，以下内容被硬编码排除，界面中无法开启：

- `auth.json` 和账户令牌
- `.env` 和 API 密钥
- `config.toml` 中的机器专用配置
- `installation_id` 和设备身份
- 插件运行时、缓存、日志、sandbox、锁和临时文件
- `.codex` 外部的 Git 仓库、OneDrive 文件夹和项目源码

外部项目源码请用 Git、OneDrive 或移动硬盘单独迁移，然后在工具中添加旧路径到新路径的映射。

### 安全模型

- 只支持完整覆盖，不提供数据库合并。
- 导出时使用 SQLite Backup API 创建一致性快照，不直接修改源数据库。
- 迁移包中的每个文件都有 SHA-256；任一文件缺失或改变都会阻止导入。
- 导入前把目标电脑的全部可迁移数据备份为 ZIP。
- 只清除明确白名单中的可迁移数据，目标电脑的登录状态和机器配置保留。
- 所有路径改写均在临时 staging 目录完成，不修改迁移包。
- 安装中途失败会自动恢复导入前备份。
- 导入后自动核对数据库线程数、JSONL 数量和每个 `rollout_path`。

### 要求

- Windows 10 或 Windows 11
- Python 3.9 或更高版本（只使用标准库）
- 建议旧、新电脑使用相同版本的 Codex/ChatGPT Desktop
- 导出和导入时应完全退出 Codex/ChatGPT Desktop

### 图形界面使用方法

1. 下载仓库或 Release ZIP。
2. 双击 `run_codex_transfer.cmd`。
3. 在“旧电脑：导出”页面选择 `.codex` 数据目录和迁移包位置，点击“扫描”，然后“创建迁移包”。
4. 把整个迁移包复制到新电脑。
5. 在新电脑打开本工具，切换到“新电脑：覆盖导入”页面，选择迁移包和目标 `.codex`，点击“校验迁移包”。
6. 如果项目路径改变，添加一项或多项“旧路径 → 新路径”。用户名和 `.codex` 根目录会自动映射。
7. 完全退出 Codex，勾选覆盖确认框，点击“备份并覆盖导入”。
8. 保存备份和结果 JSON，启动 Codex 检查聊天、分区和自动任务。

底部的“进度与结果”框在两个页面中始终可见。Windows 路径中的 `/` 和 `\` 均可输入，工具会在界面和路径映射中统一转换为 `\`。

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

导入前备份默认保存在目标 `.codex` 同级目录：

```text
C:\Users\<用户名>\CodexTransferBackups\before-import-YYYYMMDD-HHMMSS.zip
```

确认新电脑稳定工作之前，不要删除迁移包和备份。

---

## English

### What it transfers

- Local chats and Work tasks in `sessions` and `archived_sessions`
- Attachments and generated content
- Thread, project, section assignment, ordering, and history metadata stored in SQLite
- Custom sidebar sections, pins, and layout state
- Automations and schedules from `automations/*/automation.toml`
- Codex-managed local workspaces in `.chatgpt-projects`
- User rules, memories, custom skills, and imported data
- Automatic user-home and `.codex` path migration, plus custom path-prefix maps

### What it never transfers

These items are hard-coded exclusions to prevent credential or device-identity migration:

- `auth.json` and account tokens
- `.env` and API keys
- Machine-specific `config.toml`
- `installation_id` and device identity
- Plugin runtimes, caches, logs, sandboxes, locks, and temporary files
- Git repositories, OneDrive folders, and source trees outside `.codex`

Move external workspaces separately with Git, cloud storage, or removable media, then add old-to-new path maps in Codex Transfer.

### Safety model

- Replacement only. Database merge is intentionally unavailable.
- SQLite databases are exported through the Backup API for consistent snapshots.
- Every payload file is protected by SHA-256; verification failure blocks import.
- All migratable destination data is backed up before replacement.
- Only allowlisted user-data paths are cleared. Destination credentials and machine configuration remain intact.
- Path rewriting happens in a temporary staging directory and never changes the package.
- An interrupted installation attempts to restore the pre-import backup automatically.
- Post-import validation compares database threads with JSONL sessions and checks every rollout path.

### Requirements

- Windows 10 or Windows 11
- Python 3.9 or later; no third-party packages
- Prefer the same Codex/ChatGPT Desktop version on both computers
- Fully close Codex/ChatGPT Desktop during export and import

### GUI workflow

1. Download the repository or release ZIP.
2. Double-click `run_codex_transfer.cmd`.
3. On the **Old PC: Export** tab, select the `.codex` directory and a package path. Scan, then create the package.
4. Copy the package to the new PC.
5. On the new PC, open the **New PC: Replace import** tab, select and verify the package, then select the destination `.codex` directory.
6. Add path maps if external project locations changed. User-home and `.codex` roots are mapped automatically.
7. Fully close Codex, accept the replacement confirmation, and start the import.
8. Keep the backup and result JSON while checking chats, sections, and automations in Codex.

The progress/output panel remains visible below both tabs. Either `/` or `\` is accepted in Windows path fields; the GUI and path mapper normalize them to `\`.

### Important limitations

- Local data formats are undocumented implementation details and can change.
- Cloud-only data remains governed by the signed-in account and is not copied by this tool.
- External repositories are not silently bundled.
- Importing into a different application version can trigger that application's own database migrations.

## Development

```powershell
python -m unittest discover -s tests -v
python codex_transfer.py --version
```

## Security and privacy

Read [SECURITY.md](SECURITY.md). Never attach a real migration package to a public GitHub issue: it contains private conversations and may contain proprietary project metadata.

## License

MIT. See [LICENSE](LICENSE).
