# Codex Transfer Maintainer Guide / Codex 迁移工具维护指南

This is the technical handoff for humans and coding agents maintaining Codex Transfer on another computer. Read it with the root `AGENTS.md`, `README.md`, `SECURITY.md`, and the tests.

本文档供在另一台电脑上接手项目的开发者或 GPT 编码助手使用。开始修改前，请同时阅读根目录的 `AGENTS.md`、`README.md`、`SECURITY.md` 和测试代码。

## English

### 1. Product contract

Codex Transfer is an unofficial, Windows-first, replacement-only migration utility for local Codex/ChatGPT Desktop conversations and selected UI metadata. It is intentionally conservative because `.codex` is an undocumented, version-dependent application state directory.

The stable contract is:

1. Export only explicitly allowlisted data from the old computer.
2. Never modify the source `.codex` directory.
3. Verify the ZIP manifest, paths, sizes, and SHA-256 hashes before import.
4. Rewrite paths only in a temporary staging directory.
5. Back up the destination's migratable scope.
6. Replace only that scope while preserving credentials and machine state.
7. Restore the backup if installation fails.
8. Validate thread/session counts and rollout paths after import.

Merge import is not implemented. A package containing one selected chat would still replace the destination unless a separately designed merge mode is added.

### 2. Repository map

```text
.
├─ AGENTS.md                         Mandatory guidance for coding agents
├─ codex_transfer.py                 Tkinter GUI, translations, CLI, worker queue
├─ codex_transfer_core.py            Migration, validation, mapping, and safety logic
├─ tests/test_core.py                Synthetic end-to-end and regression tests
├─ README.md                         Public bilingual user guide
├─ SECURITY.md                       Data-handling and vulnerability policy
├─ CHANGELOG.md                      Release history
├─ RELEASE_NOTES.md                  Current release notes
├─ pyproject.toml                    Package metadata and console entry point
├─ run_codex_transfer.cmd            Source-version Windows launcher
├─ .github/workflows/test.yml        Python 3.9/3.13 Windows tests
├─ .github/workflows/build-windows-exe.yml
│                                      PyInstaller release build and attestation
└─ docs/MAINTAINER_GUIDE.md          This document
```

Runtime code uses only the Python standard library. PyInstaller is a build-time dependency pinned in the release workflow.

### 3. Migration scope

The allowlist is defined near the top of `codex_transfer_core.py`.

Included directories:

```text
sessions/
archived_sessions/
attachments/
automations/
```

Included files:

```text
session_index.jsonl
state_5.sqlite
.codex-global-state.json   # sanitized; selected sidebar/UI keys only
```

Explicitly excluded:

```text
auth.json, .env, config.toml, installation_id
plugins, cache, logs, sandbox, and temporary/runtime data
.chatgpt-projects and external project/repository contents
generated_images, memories, and memories_1.sqlite
rules, custom skills, and vendor_imports
```

Import replaces only paths returned by `scoped_paths()`. Excluded destination data remains untouched.

When changing scope, update all of these together:

- `DATA_DIRS`, `PLAIN_FILES`, `DATABASE_FILES`, and `EXCLUDED_LABELS`
- `is_allowed_payload_path()` and `scoped_paths()` assumptions
- inventory and post-import validation
- synthetic fixtures and package-rejection tests
- `README.md` and `SECURITY.md`

Treat accidental inclusion of an excluded item as a security defect.

### 4. Package format

Packages are ZIP files normally named `*.codextransfer.zip`. They are compressed but not encrypted. The ZIP root contains the allowlisted payload plus `codex-transfer-manifest.json`.

Manifest format version 1 contains:

```json
{
  "format": "codex-transfer-package",
  "format_version": 1,
  "tool_version": "1.1.0",
  "created_at": "ISO-8601 timestamp",
  "source_codex_dir": "C:\\Users\\OldUser\\.codex",
  "source_user_home": "C:\\Users\\OldUser",
  "payload_files": [
    {"path": "sessions/...jsonl", "size": 123, "sha256": "..."}
  ],
  "inventory": {},
  "excluded_for_security": [],
  "export_warnings": [],
  "mode": "replacement-only"
}
```

Archive names use POSIX `/` separators. `_safe_zip_name()` rejects absolute paths, drive paths, and `..` traversal. `verify_package()` rejects missing, changed, unexpected, and disallowed payloads. Keep this strict behavior.

### 5. Export pipeline

`create_package()` performs:

```text
validate source/output and require Codex to be closed
  → copy allowlisted files to a temporary stage
  → sanitize sidebar state
  → snapshot SQLite with sqlite3.backup()
  → hash every staged file and create the manifest
  → write <package>.partial
  → atomically rename to the final ZIP
```

The final package is never silently overwritten. An interrupted `.partial` file is not accepted as a package.

For the portable EXE, `application_directory()` makes the default package location the EXE directory. This is why the recommended workflow runs the EXE from a USB-drive root.

### 6. Import pipeline

`import_package()` performs:

```text
require explicit replacement confirmation and closed Codex
  → verify the complete package
  → extract beside the destination into a temporary stage
  → apply automatic/custom path maps to staged data
  → remap the sidebar profile and merge sanitized sidebar keys
  → back up the destination's scoped data
  → clear and install only scoped data
  → roll back from backup on installation failure
  → validate sessions, database rows, sections, and rollout paths
```

Backups are written outside `.codex`:

```text
C:\Users\<user>\CodexTransferBackups\before-import-YYYYMMDD-HHMMSS.zip
```

The result JSON is written beside the migration package. Do not place either output inside `.codex`.

### 7. SQLite and schema compatibility

`state_5.sqlite` is snapshotted through SQLite's backup API instead of being copied while active. Runtime schema is discovered through `sqlite_master` and `PRAGMA table_info`; unknown tables and columns should not crash path inspection or rewriting.

Only columns named in `PATH_FIELD_NAMES` are rewritten. Identifiers pass through `quote_identifier()` and values use SQL parameters. Current validation recognizes `threads` and `thread_sections` when present. Future schema support should use feature detection and synthetic compatibility tests.

### 8. Path mapping

Windows paths entered with `/` or `\` are normalized. Automatic mappings cover old `.codex` to destination `.codex` and old user home to destination user home. Custom mappings are optional and sorted longest-prefix-first.

Rewriting occurs only in staged JSON/JSONL path fields, automation TOML, selected sidebar state, and recognized SQLite path columns. The path-review dialog extracts structured values and groups deep references into top-level roots; it must not scan arbitrary chat prose.

### 9. GUI architecture

`CodexTransferApp` uses Tkinter/ttk with a blue old-computer Export tab and an orange new-computer Replace Import tab. The output panel is shared below both tabs.

Long operations run on a daemon worker thread. Workers publish progress, success, or error events to `self.events`; `_drain_events()` updates Tk widgets on the main thread. Never update Tk widgets directly from a worker.

The process status is checked every second. Core export/import functions repeat the process check, so the colored label is guidance rather than the only protection. The final import button stays disabled until replacement is confirmed and remains disabled while another operation is busy.

All visible strings live in `TEXT["en"]` and `TEXT["zh"]`; both dictionaries must have identical keys. Core messages remain stable in English for CLI use and are translated in the GUI by `localize_core_message()`.

### 10. CLI

```powershell
python codex_transfer.py scan --codex-dir PATH
python codex_transfer.py export --source PATH --package FILE.zip
python codex_transfer.py verify --package FILE.zip
python codex_transfer.py import --package FILE.zip --destination PATH --map "OLD=NEW" --yes-replace
```

No subcommand opens the GUI. Exit codes: `0` success, `2` expected transfer/OS error, and `4` completed verification failure.

### 11. Tests and verification

Tests create synthetic `.codex` data in temporary directories. Never use real user data.

Run before every push:

```powershell
python -m unittest discover -s tests -v
python -m py_compile codex_transfer.py codex_transfer_core.py
python codex_transfer.py --version
git diff --check
```

Regression coverage includes end-to-end replacement, backup and validation, credential exclusion, tamper detection, ZIP allowlisting, replacement confirmation, Windows path mapping, bilingual key parity, button captions, structured path inspection, and final-button state.

### 12. Versioning and release

1. Update `APP_VERSION` in `codex_transfer_core.py` and `version` in `pyproject.toml`.
2. Update `CHANGELOG.md`, `RELEASE_NOTES.md`, and the workflow's default tag when appropriate.
3. Run all verification commands.
4. Commit, create an annotated version tag, and push both.
5. Create the GitHub Release before dispatching the EXE workflow.
6. Dispatch **build Windows EXE** with the exact release tag.
7. Verify the EXE, SHA-256 file, smoke test, and GitHub build-provenance attestation.

The EXE is not currently Authenticode-signed. GitHub provenance proves how it was built but does not display a Windows “Verified publisher” identity.

### 13. Safe extension points

- **Selective chat export:** feasible, but replacement import would leave only selected chats. Preserving destination chats needs a separately designed merge system.
- **Local memories:** excluded. Support requires coordinated handling of `memories/`, `memories_1.sqlite`, and possible SQLite sidecars while preserving destination configuration.
- **Code signing:** use a trusted Authenticode certificate or qualifying open-source signing service; never commit signing secrets.
- **New Codex schema:** add feature detection and synthetic tests rather than hard-coding one version.

Do not expand scope merely because a directory exists. First establish ownership, sensitivity, portability, replacement semantics, and rollback behavior.

---

## 中文维护说明

### 1. 产品约定

Codex Transfer 是一个 Windows 优先的非官方迁移工具，用于迁移本地 Codex/ChatGPT Desktop 聊天及部分界面元数据。它只支持覆盖导入。由于 `.codex` 是未公开、可能随版本变化的应用状态目录，实现必须保持保守。

稳定约定如下：

1. 只从旧电脑导出明确列入白名单的数据。
2. 永远不修改源 `.codex`。
3. 导入前校验 ZIP 清单、路径、大小和 SHA-256。
4. 只在临时目录改写路径。
5. 覆盖前备份目标端可迁移范围。
6. 只替换该范围，保留凭据和机器配置。
7. 安装失败时恢复备份。
8. 导入后检查线程数、会话数和 rollout 路径。

当前没有合并功能。即使未来只选择一条聊天打包，按现有语义导入后目标端也只会留下所选内容；保留目标聊天需要独立设计合并模式。

### 2. 代码分工

- `codex_transfer_core.py`：白名单、打包、校验、SQLite 快照、路径映射、备份、覆盖、回滚和验证。
- `codex_transfer.py`：Tkinter 界面、中英文翻译、后台线程事件队列和 CLI。
- `tests/test_core.py`：完全使用合成数据的端到端测试和回归测试。
- `AGENTS.md`：GPT 或其他编码代理开始工作时必须先读取的简短约束。
- `.github/workflows/`：Windows 测试、EXE 构建、校验值和来源证明。

运行代码只依赖 Python 标准库；PyInstaller 只在构建 EXE 时使用。

### 3. 当前迁移范围

包含：

```text
sessions/
archived_sessions/
attachments/
automations/
session_index.jsonl
state_5.sqlite
经过清理的 .codex-global-state.json
```

排除：

```text
auth.json、.env、config.toml、installation_id
plugins、cache、logs、sandbox、临时运行数据
.chatgpt-projects 和外部项目源码/仓库
generated_images、memories、memories_1.sqlite
rules、自定义 skills、vendor_imports
```

导入时只清理和替换 `scoped_paths()` 返回的内容，排除项在目标电脑保持不变。任何把排除项意外写入迁移包的改动都应视为安全漏洞。

如果修改迁移范围，必须同步检查：

- `DATA_DIRS`、`PLAIN_FILES`、`DATABASE_FILES`、`EXCLUDED_LABELS`
- `is_allowed_payload_path()` 的 ZIP 白名单
- `scoped_paths()` 的备份、清理和回滚范围
- 扫描结果和导入后验证
- 合成测试、README 和 SECURITY

### 4. 导出与导入

导出流程：

```text
检查路径和 Codex 进程
  → 复制白名单数据到临时目录
  → 清理侧边栏状态
  → 使用 SQLite backup API 创建一致快照
  → 计算每个文件的 SHA-256 并生成 manifest
  → 写入 .partial
  → 原子重命名为最终 ZIP
```

导入流程：

```text
要求明确确认覆盖并检查 Codex 已关闭
  → 完整校验迁移包
  → 解压到目标目录旁的临时区
  → 在临时数据中执行路径和侧边栏 profile 映射
  → 备份目标端白名单范围
  → 清理并安装白名单数据
  → 失败时回滚
  → 验证聊天、数据库、分区和 rollout 路径
```

迁移包不会静默覆盖已有文件。迁移包是明文 ZIP，必须当作机密数据保存。备份默认位于：

```text
C:\Users\<用户名>\CodexTransferBackups\before-import-YYYYMMDD-HHMMSS.zip
```

### 5. SQLite 与路径映射

`state_5.sqlite` 通过 SQLite backup API 生成一致快照。表结构使用 `sqlite_master` 和 `PRAGMA table_info` 动态发现；遇到未知表或字段时应保持兼容。

只改写 `PATH_FIELD_NAMES` 中声明的路径字段。SQL 标识符必须使用 `quote_identifier()`，字段值必须参数化。不要把用户输入直接拼接进 SQL。

旧 `.codex` 到新 `.codex`、旧用户目录到新用户目录会自动映射。自定义映射按旧路径长度从长到短执行。路径查看窗口只提取结构化字段，不应扫描聊天正文。

### 6. GUI 维护要求

界面使用 Tkinter/ttk：蓝色页面负责旧电脑导出，橙色页面负责新电脑覆盖导入，底部输出框由两个页面共享。

耗时操作必须在后台线程执行，并通过 `self.events` 让主线程更新界面。禁止从后台线程直接操作 Tk 控件。进程状态每秒检查一次，核心导出/导入函数还会再次检查，不能只依赖界面颜色。

覆盖确认未勾选时，最终导入按钮必须保持灰色；任务执行期间也必须禁用。中英文 `TEXT` 字典必须拥有完全相同的键。CLI 核心消息保持英文稳定，GUI 通过 `localize_core_message()` 翻译。

### 7. 测试与发布

所有测试只能使用临时目录中的合成 `.codex` 数据，禁止把真实用户数据放入测试、提交、Issue 或 Release。

每次功能修改后运行：

```powershell
python -m unittest discover -s tests -v
python -m py_compile codex_transfer.py codex_transfer_core.py
python codex_transfer.py --version
git diff --check
```

发布时：

1. 同步修改 `codex_transfer_core.py` 和 `pyproject.toml` 的版本号。
2. 更新 CHANGELOG、RELEASE_NOTES 和必要时的工作流默认标签。
3. 完成测试并提交，创建带说明的版本标签。
4. 先创建 GitHub Release，再运行 **build Windows EXE**。
5. 核对 EXE、SHA-256、冒烟测试和 GitHub 构建来源证明。

当前 EXE 没有 Authenticode 发布者签名。GitHub 来源证明能验证构建来源，但不会让 Windows 显示“已验证的发布者”。

### 8. 后续功能边界

- 单聊天选择可以实现，但当前覆盖模式会清空目标端其他聊天；保留目标内容属于数据库合并，需要独立设计。
- 本地记忆目前排除。若加入，必须整体处理 `memories/`、`memories_1.sqlite` 和可能存在的 SQLite sidecar，同时保留目标端配置。
- 正式签名应使用受信任的 Authenticode 证书或符合条件的开源签名服务，私钥和签名凭据不得进入仓库。
- 遇到新版 Codex schema，应使用能力检测和合成测试，避免只适配单一固定版本。

增加任何数据范围前，先回答五个问题：数据归谁所有、是否敏感、能否跨机器使用、覆盖语义是什么、失败后如何恢复。
