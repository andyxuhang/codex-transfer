# Codex Transfer 1.2.0

This release adds a separate, safety-focused utility for repairing stale Codex Desktop sidebar entries.

## New: Codex Sidebar Repair

- Use `Codex-Sidebar-Repair.exe` when an already-deleted chat remains visible, cannot be opened, and fails when deleted again.
- Read-only scan distinguishes missing local thread files from unreferenced JSONL files; unreferenced files are never deleted.
- The repair creates a verified ZIP backup before rebuilding the desktop web/sidebar cache.
- Login cookies, local conversations, automations, workspaces, memories, credentials, and machine configuration are not deleted.
- Codex/ChatGPT Desktop must be fully closed and the confirmation box selected.

The tool does not delete by title. Cloud conversations that still exist on the account will return after synchronization; cloud-side deletion failures require the ChatGPT account interface or OpenAI support.

## Downloads

- `Codex-Transfer.exe`: replacement-only migration utility.
- `Codex-Sidebar-Repair.exe`: stale sidebar cache repair utility.
- Matching `.sha256.txt` files: SHA-256 checksums.
- Both executables receive GitHub build-provenance attestations.

---

# Codex 迁移工具 1.2.0

此版本新增一个独立、安全优先的工具，用于修复 Codex Desktop 侧栏中的无效残留条目。

## 新增：Codex 侧栏修复

- 当聊天已经删除，但条目仍显示、无法打开且再次删除失败时，可使用 `Codex-Sidebar-Repair.exe`。
- 只读扫描会区分本地数据库记录缺少聊天文件和当前未引用的 JSONL 文件；未引用文件绝不删除。
- 重建桌面端网页/侧栏缓存前，程序会先创建并校验 ZIP 备份。
- 不删除登录 Cookie、本地聊天、自动任务、工作目录、记忆、凭据或机器配置。
- 必须完全退出 Codex/ChatGPT Desktop，并勾选确认框后才能执行。

工具不会按标题删除聊天。如果聊天在账号云端仍存在，同步后仍会回来；云端删除失败需要在 ChatGPT 账号界面处理或联系 OpenAI 支持。

## 下载

- `Codex-Transfer.exe`：只支持覆盖的迁移工具。
- `Codex-Sidebar-Repair.exe`：侧栏残留缓存修复工具。
- 对应的 `.sha256.txt`：SHA-256 校验文件。
- 两个 EXE 都会生成 GitHub 构建来源证明。
