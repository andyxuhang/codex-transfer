# Changelog

## 1.0.2 — 2026-09-09

- Avoid Windows `WinError 3` failures on deeply nested managed-workspace files by using extended-length paths and bounded copy retries.
- Exclude downloaded `.android-build-tools` workspace caches, which are regenerated and are not user-authored project data.
- Record the skipped cache-file count in the migration manifest and GUI output.

## 1.0.1 — 2026-09-09

- Split the GUI into separate Export and Import tabs while keeping the progress/output panel visible below both pages.
- Normalize Windows paths from file dialogs and manual input to backslashes.
- Normalize both sides of custom path maps to prevent mixed-separator results.

## 1.0.0 — 2026-09-09

- Initial public release.
- Bilingual Windows GUI and CLI.
- Replacement-only migration for chats, Work tasks, sidebar sections, automations, managed workspaces, rules, memories, and custom skills.
- Consistent SQLite snapshots and per-file SHA-256 verification.
- Automatic user-home, `.codex`, sidebar-profile, and custom project-path mapping.
- Pre-import backup, failure rollback, and post-import validation.
- Hard-coded exclusion of credentials, device identity, machine configuration, plugins, caches, logs, and external repositories.
- Sanitized sidebar-state export that excludes cloud conversation resume tokens.
