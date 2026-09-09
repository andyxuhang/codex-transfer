# Changelog

## 1.0.0 — 2026-09-09

- Initial public release.
- Bilingual Windows GUI and CLI.
- Replacement-only migration for chats, Work tasks, sidebar sections, automations, managed workspaces, rules, memories, and custom skills.
- Consistent SQLite snapshots and per-file SHA-256 verification.
- Automatic user-home, `.codex`, sidebar-profile, and custom project-path mapping.
- Pre-import backup, failure rollback, and post-import validation.
- Hard-coded exclusion of credentials, device identity, machine configuration, plugins, caches, logs, and external repositories.
- Sanitized sidebar-state export that excludes cloud conversation resume tokens.
