# Codex Transfer 1.3.0

This privacy-focused update stops machine-local database files from moving between computers.

## Changes

- Migration packages never contain `state_5.sqlite`, `state_5.sqlite-wal`, or `state_5.sqlite-shm`.
- Replacement import backs up and removes the destination copies of those files. Codex creates a fresh machine-local index from the imported JSONL sessions on its next launch.
- This prevents computer-name and device metadata from the old PC from interfering with remote-control registration on the new PC.
- Version 1.3 uses package format 2. Re-export with 1.3 instead of importing an older package that contains the database.
- Sidebar definitions and layout still come from sanitized UI state. Individual chat-to-section assignments may need to be restored manually because their database is not transferred.

## Downloads

- `Codex-Transfer.exe`: standalone Windows application; Python is not required.
- `Codex-Transfer.exe.sha256.txt`: SHA-256 checksum for the executable.
- Source archives are generated automatically by GitHub.

> The community executable is not currently Authenticode-signed with a commercial identity certificate, so Windows may still display a SmartScreen warning.

> Migration packages are unencrypted archives. Store and transfer them securely because they can contain private local Codex data.

---

# Codex 迁移工具 1.3.0

这个版本重点加强隐私保护，阻止本机数据库在不同电脑之间迁移。

## 更新内容

- 迁移包绝不会包含 `state_5.sqlite`、`state_5.sqlite-wal` 或 `state_5.sqlite-shm`。
- 覆盖导入前会备份并删除新电脑上的这三个文件；下次启动 Codex 时，由它根据迁入的 JSONL 会话重建全新的本机索引。
- 这样可以防止旧电脑名称和设备信息干扰新电脑的手机远程控制注册。
- 1.3 使用迁移包格式 2。请使用 1.3 重新导出，不要继续导入包含数据库的旧版迁移包。
- 自定义侧栏分区定义和布局仍通过安全处理后的界面状态迁移；由于数据库不再迁移，个别聊天所属分区可能需要手动恢复。

## 下载说明

- `Codex-Transfer.exe`：Windows 独立程序，不需要安装 Python。
- `Codex-Transfer.exe.sha256.txt`：EXE 的 SHA-256 校验文件。
- 源码压缩包由 GitHub 自动生成。

> 社区版 EXE 目前尚未使用商业身份验证证书进行 Authenticode 签名，因此 Windows 仍可能显示 SmartScreen 警告。

> 迁移包是未加密的压缩文件，其中可能包含私密的本地 Codex 数据，请安全保存和传输。
