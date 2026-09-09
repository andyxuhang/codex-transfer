# Security Policy / 安全政策

## Sensitive data / 敏感数据

Codex Transfer packages contain private conversations, filenames, local paths, automation prompts, sidebar/project metadata, and possibly proprietary work references. Treat every package and backup as confidential.

Codex Transfer 迁移包包含私人对话、文件名、本地路径、自动任务提示、侧边栏/项目元数据以及可能属于公司的工作引用。请始终把迁移包和备份视为机密文件。

Never upload a migration package, backup ZIP, real `.codex` database, `auth.json`, `.env`, or API key to a GitHub issue.

请勿把真实迁移包、备份 ZIP、`.codex` 数据库、`auth.json`、`.env` 或 API 密钥上传到 GitHub Issue。

## Reporting a vulnerability / 报告漏洞

Please use GitHub private vulnerability reporting when enabled. Otherwise contact the repository owner privately. Include synthetic reproduction data only.

请优先使用 GitHub 私密漏洞报告功能，并只使用合成测试数据复现问题。

## Scope / 范围

The project intentionally excludes account credentials, device identity, machine configuration, `state_5.sqlite` and its `-wal`/`-shm` sidecars, caches, logs, plugin runtimes, managed workspace contents (`.chatgpt-projects`), generated images, memories, rules, custom skills, vendor imports, and external repositories. The state database is machine-local and may contain computer/device metadata. A change that causes any excluded item to enter a package should be treated as a security vulnerability.

本项目明确排除账户凭据、设备身份、机器配置、`state_5.sqlite` 及其 `-wal`/`-shm` 辅助文件、缓存、日志、插件运行时、托管工作目录（`.chatgpt-projects`）、生成图片、记忆、规则、自定义技能、第三方导入目录和外部仓库。该状态数据库属于本机数据，可能包含电脑或设备信息。任何导致这些排除项进入迁移包的更改都应视为安全漏洞。
