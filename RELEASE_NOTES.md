# Codex Transfer 1.0

The first public stable release of Codex Transfer, a Windows migration utility for replacing a new computer's local Codex Desktop data with data exported from an old computer.

## Highlights

- Separate Export and Import pages with bilingual English and Simplified Chinese interfaces.
- Transfers local chats, archived chats, project and workspace metadata, sidebar sections, and local scheduled-task definitions when present.
- Automatically suggests path mappings and lets users inspect detected paths before importing.
- Requires Codex Desktop to be closed and checks its status continuously.
- Replacement-only import with automatic destination backup; merging is intentionally unsupported.
- Standard-library Python source and a standalone Windows executable.

## Downloads

- `Codex-Transfer.exe`: standalone Windows application; Python is not required.
- `Codex-Transfer.exe.sha256.txt`: SHA-256 checksum for the executable.
- `Codex-Transfer-1.0.zip`: source package.

> The community executable is not commercially code-signed, so Windows may display a SmartScreen warning.

> Migration packages are unencrypted archives. Store and transfer them securely because they can contain private local Codex data.

---

# Codex 迁移工具 1.0

这是 Codex 迁移工具的首个公开稳定版本，用于在 Windows 上将旧电脑导出的 Codex Desktop 本地数据覆盖迁移到新电脑。

## 主要功能

- 导出和导入采用独立页面，支持 English 和中文简体界面。
- 迁移本地聊天、已归档聊天、项目与工作区元数据、侧边栏分区，以及存在时的本地定时任务定义。
- 自动建议路径映射，并可在导入前查看检测到的路径。
- 要求关闭 Codex Desktop，并持续检查其运行状态。
- 仅支持覆盖导入，不支持合并；导入前自动备份目标数据。
- 提供仅使用 Python 标准库的源码和独立 Windows EXE。

## 下载说明

- `Codex-Transfer.exe`：Windows 独立程序，不需要安装 Python。
- `Codex-Transfer.exe.sha256.txt`：EXE 的 SHA-256 校验文件。
- `Codex-Transfer-1.0.zip`：源码包。

> 社区版 EXE 没有商业代码签名，Windows 可能显示 SmartScreen 警告。

> 迁移包是未加密的压缩文件，其中可能包含私密的本地 Codex 数据，请安全保存和传输。
