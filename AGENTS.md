# Maintainer instructions

Read `docs/MAINTAINER_GUIDE.md` before changing this repository.

Preserve these invariants:

- Migration is replacement-only. Do not add database merge behavior without a separate design and migration test suite.
- Export is allowlist-based. Never replace it with a broad copy of `.codex`.
- Credentials, device identity, machine configuration, plugins, caches, logs, managed workspaces, generated images, memories, rules, custom skills, vendor imports, and external repositories stay excluded unless the maintainer deliberately changes the product scope and security policy.
- Never modify the source `.codex` directory or the migration ZIP. Rewrite paths only in temporary staging data.
- Require Codex/ChatGPT Desktop to be closed for export and import.
- Verify every package before changing the destination; create a backup first and roll back on installation failure.
- Keep English and Simplified Chinese translation keys identical.
- Use only Python's standard library in runtime code unless the project requirements are intentionally changed.

After a functional change, run:

```powershell
python -m unittest discover -s tests -v
python -m py_compile codex_transfer.py codex_transfer_core.py
python codex_transfer.py --version
git diff --check
```

Never use real user `.codex` data in tests, commits, issues, or release artifacts. Use synthetic fixtures only.
