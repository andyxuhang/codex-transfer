# Codex Transfer 1.1.0

This update improves replacement safety and portable USB-drive use.

## Changes

- The final replacement-import button is disabled until the user selects the explicit overwrite confirmation checkbox.
- The documentation now recommends copying the executable to the root of a USB drive and running it there. The migration package is then created in the USB-drive root by default.
- New Windows executable builds include a GitHub build-provenance attestation in addition to the SHA-256 checksum.

## Downloads

- `Codex-Transfer.exe`: standalone Windows application; Python is not required.
- `Codex-Transfer.exe.sha256.txt`: SHA-256 checksum for the executable.
- Source archives are generated automatically by GitHub.

> The community executable is not currently Authenticode-signed with a commercial identity certificate, so Windows may still display a SmartScreen warning.

> Migration packages are unencrypted archives. Store and transfer them securely because they can contain private local Codex data.

---

# Codex 迁移工具 1.1.0

此版本增强了覆盖操作的安全性，并优化了 U 盘便携使用流程。

## 更新内容

- 只有勾选明确的覆盖确认框后，最终覆盖导入按钮才会启用；此前按钮保持灰色且不可点击。
- 说明文档现在建议把 EXE 复制到 U 盘根目录并从那里运行，迁移包默认也会直接生成在 U 盘根目录。
- 新构建的 Windows EXE 除 SHA-256 校验文件外，还会生成 GitHub 构建来源证明。

## 下载说明

- `Codex-Transfer.exe`：Windows 独立程序，不需要安装 Python。
- `Codex-Transfer.exe.sha256.txt`：EXE 的 SHA-256 校验文件。
- 源码压缩包由 GitHub 自动生成。

> 社区版 EXE 目前尚未使用商业身份验证证书进行 Authenticode 签名，因此 Windows 仍可能显示 SmartScreen 警告。

> 迁移包是未加密的压缩文件，其中可能包含私密的本地 Codex 数据，请安全保存和传输。
