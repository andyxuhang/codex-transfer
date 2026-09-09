# Changelog

## 1.1.0 — 2026-09-09

- Keep the final replacement-import button disabled until the user selects the explicit overwrite confirmation.
- Recommend running the portable executable from a USB-drive root so the default package is created there.
- Publish GitHub build-provenance attestations for new Windows executables.

## 1.0 — 2026-09-09

- Prepare the first public release from the completed migration workflow.
- Replace technical language codes in the selector with `中文简体` and `English`.
- Add a reproducible GitHub Actions workflow for a portable Windows EXE and SHA-256 file.
- Include all fixes and safety improvements developed through internal versions 1.0.0–1.0.9.

## 1.0.9 — 2026-09-09

- Localize core migration errors and progress messages throughout the Chinese GUI, including the Codex-not-closed dialog.
- Localize path-source labels, file-dialog filters, verification failures, and the Windows-only shortcut message.
- Keep CLI output in English for scripting compatibility and hide raw English tracebacks from normal GUI users.
- Add regression coverage for Chinese and English message selection.

## 1.0.8 — 2026-09-09

- Fix all file/folder picker buttons incorrectly showing their adjacent field labels instead of the short Browse caption.
- Add a bilingual regression test for every fixed-width Browse button.

## 1.0.7 — 2026-09-09

- Add a separate path-review window that discovers structured path references without scanning chat prose.
- Group deep references into safe top-level roots and show automatic, existing, and unresolved paths.
- Let users choose a new folder, explicitly keep the old path, or leave a path unresolved before import.
- Make the main window more compact while retaining the shared progress/output panel.
- Clearly warn that migration ZIP packages are compressed but not encrypted.

## 1.0.6 — 2026-09-09

- Stop guessing the Windows Desktop path, which may be localized or redirected.
- Save new packages beside the migration tool by default, with a timestamped filename.
- Start the Save dialog in the displayed package directory and add an Open package folder button.

## 1.0.5 — 2026-09-09

- Check for Codex/ChatGPT processes at startup and every second using the native Windows process API.
- Show a prominent red running warning or green closed status in the GUI.
- Distinguish Export and Import with directional tab icons plus blue/orange step banners.
- Preview the exact automatic `.codex` and user-home mappings on the Import page; keep custom maps optional for changed external project roots.

## 1.0.4 — 2026-09-09

- Return to the proven conversation-only migration scope: sessions, archived sessions, attachments, session index, and `state_5.sqlite`.
- Add automations plus sanitized sidebar section, pin, expansion, and ordering state to that lightweight scope.
- Never scan, export, delete, or install `.chatgpt-projects`, project source/build output, generated images, memories, rules, custom skills, or vendor-import data.
- Reject older expanded-scope packages containing out-of-scope payloads instead of partially applying them.

## 1.0.3 — 2026-09-09

- Prevent the Tkinter window from appearing frozen when exporting workspaces containing tens of thousands of files.
- Throttle per-file GUI events, cap retained log lines, and bound each UI event-drain cycle.
- Show explicit scanning, file-count, data-size, copy, hashing, and pre-compression progress messages.

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
