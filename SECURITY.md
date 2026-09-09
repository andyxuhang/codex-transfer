# Security Policy / 安全政策

## Sensitive data / 敏感数据

Codex Transfer packages contain private conversations, filenames, local paths, automation prompts, memory data, and possibly proprietary work artifacts. Treat every package and backup as confidential.

Codex Transfer 迁移包包含私人对话、文件名、本地路径、自动任务提示、记忆数据以及可能属于公司的工作内容。请始终把迁移包和备份视为机密文件。

Never upload a migration package, backup ZIP, real `.codex` database, `auth.json`, `.env`, or API key to a GitHub issue.

请勿把真实迁移包、备份 ZIP、`.codex` 数据库、`auth.json`、`.env` 或 API 密钥上传到 GitHub Issue。

## Reporting a vulnerability / 报告漏洞

Please use GitHub private vulnerability reporting when enabled. Otherwise contact the repository owner privately. Include synthetic reproduction data only.

请优先使用 GitHub 私密漏洞报告功能，并只使用合成测试数据复现问题。

## Scope / 范围

The project intentionally excludes account credentials, device identity, machine configuration, caches, logs, plugin runtimes, and external repositories. A change that causes any excluded item to enter a package should be treated as a security vulnerability.

本项目明确排除账户凭据、设备身份、机器配置、缓存、日志、插件运行时和外部仓库。任何导致这些排除项进入迁移包的更改都应视为安全漏洞。
