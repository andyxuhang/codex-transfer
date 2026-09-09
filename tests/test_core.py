import json
import hashlib
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_transfer_core as core
import codex_transfer as gui


THREAD_A = "11111111-1111-4111-8111-111111111111"
THREAD_B = "22222222-2222-4222-8222-222222222222"


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.process_patcher = mock.patch.object(core, "codex_processes", return_value=[])
        self.process_patcher.start()
        self.temp_context = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_context.name)
        self.old_home = self.base / "Old User"
        self.source = self.old_home / ".codex"
        self._build_source()

    def tearDown(self):
        self.temp_context.cleanup()
        self.process_patcher.stop()

    def _build_source(self):
        active = self.source / "sessions" / "2026" / "01" / "01"
        archived = self.source / "archived_sessions"
        active.mkdir(parents=True)
        archived.mkdir(parents=True)
        old_project = self.old_home / "Documents" / "Project"
        old_project.mkdir(parents=True)
        self.rollout_a = active / f"rollout-{THREAD_A}.jsonl"
        self.rollout_b = archived / f"rollout-{THREAD_B}.jsonl"
        self.rollout_a.write_text(json.dumps({"type": "session_meta", "payload": {"id": THREAD_A, "cwd": str(old_project)}}) + "\n", encoding="utf-8")
        self.rollout_b.write_text(json.dumps({"type": "session_meta", "payload": {"id": THREAD_B, "cwd": str(old_project)}}) + "\n", encoding="utf-8")
        (self.source / "attachments").mkdir()
        (self.source / "attachments" / "image.bin").write_bytes(b"image")
        automation = self.source / "automations" / "daily" / "automation.toml"
        automation.parent.mkdir(parents=True)
        automation.write_text(
            f'id = "daily"\nkind = "heartbeat"\nname = "Daily"\nprompt = "Run"\nstatus = "ACTIVE"\nrrule = "FREQ=DAILY;BYHOUR=8"\ntarget_thread_id = "{THREAD_A}"\n',
            encoding="utf-8",
        )
        managed = self.source / ".chatgpt-projects" / "managed"
        managed.mkdir(parents=True)
        (managed / "work.txt").write_text("work", encoding="utf-8")
        android_cache = managed.parent / "g-p-cache" / ".android-build-tools" / "cmd-stage"
        android_cache.mkdir(parents=True)
        (android_cache / "downloaded.jar").write_bytes(b"regenerable")
        (self.source / "rules").mkdir()
        (self.source / "rules" / "default.rules").write_text("rule", encoding="utf-8")
        (self.source / "skills" / "custom").mkdir(parents=True)
        (self.source / "skills" / "custom" / "SKILL.md").write_text("custom", encoding="utf-8")
        (self.source / "skills" / ".system").mkdir()
        (self.source / "skills" / ".system" / "SYSTEM.md").write_text("exclude", encoding="utf-8")
        (self.source / "session_index.jsonl").write_text(json.dumps({"id": THREAD_A}) + "\n", encoding="utf-8")
        profile = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        global_state = {
            "electron-persisted-atom-state": {
                "sidebar-custom-sections-v3": {
                    profile: {
                        "sections": [{"id": "section-ui", "name": "Project", "hostSectionIds": {"local": "section-db"}}],
                        "sectionOrder": ["custom:section-ui"],
                    }
                },
                "chatgpt-conversation-resume-tokens-v1": {"private": {"token": "SYNTHETIC-SOURCE-VALUE"}},
            }
        }
        (self.source / ".codex-global-state.json").write_text(json.dumps(global_state), encoding="utf-8")
        db = sqlite3.connect(self.source / "state_5.sqlite")
        db.execute("CREATE TABLE thread_sections (id TEXT PRIMARY KEY, name TEXT, appearance TEXT)")
        db.execute("INSERT INTO thread_sections VALUES ('section-db', 'Project', '{}')")
        db.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, cwd TEXT, archived INTEGER, thread_section_id TEXT)")
        db.execute("INSERT INTO threads VALUES (?, ?, ?, 0, 'section-db')", (THREAD_A, str(self.rollout_a), str(old_project)))
        db.execute("INSERT INTO threads VALUES (?, ?, ?, 1, NULL)", (THREAD_B, str(self.rollout_b), str(old_project)))
        db.commit()
        db.close()
        (self.source / "auth.json").write_text("SECRET", encoding="utf-8")
        (self.source / ".env").write_text("API_KEY=SECRET", encoding="utf-8")
        (self.source / "config.toml").write_text("secret='SECRET'", encoding="utf-8")

    def test_export_verify_import_replacement(self):
        package = self.base / "transfer.zip"
        manifest = core.create_package(self.source, package)
        self.assertEqual(manifest["inventory"]["session_files"], 2)
        verification = core.verify_package(package)
        self.assertTrue(verification["ok"])
        names = {item["path"] for item in manifest["payload_files"]}
        self.assertNotIn("auth.json", names)
        self.assertNotIn(".env", names)
        self.assertNotIn("config.toml", names)
        self.assertNotIn("skills/.system/SYSTEM.md", names)
        self.assertNotIn("skills/custom/SKILL.md", names)
        self.assertNotIn(".chatgpt-projects/managed/work.txt", names)
        self.assertNotIn("rules/default.rules", names)
        self.assertIn("automations/daily/automation.toml", names)
        self.assertNotIn(".chatgpt-projects/g-p-cache/.android-build-tools/cmd-stage/downloaded.jar", names)
        self.assertEqual(manifest["export_warnings"], [])
        with zipfile.ZipFile(package, "r") as archive:
            exported_state = archive.read(core.GLOBAL_STATE_FILE).decode("utf-8")
        self.assertNotIn("SYNTHETIC-SOURCE-VALUE", exported_state)
        self.assertNotIn("resume-tokens", exported_state)

        new_home = self.base / "NewUser"
        destination = new_home / ".codex"
        destination.mkdir(parents=True)
        (destination / "auth.json").write_text("NEW-LOGIN", encoding="utf-8")
        (destination / "config.toml").write_text("new-machine=true", encoding="utf-8")
        existing = destination / "sessions" / "old.jsonl"
        existing.parent.mkdir()
        existing.write_text("{}\n", encoding="utf-8")
        preserved_workspace = destination / ".chatgpt-projects" / "keep" / "source.txt"
        preserved_workspace.parent.mkdir(parents=True)
        preserved_workspace.write_text("KEEP-WORKSPACE", encoding="utf-8")
        preserved_rule = destination / "rules" / "keep.rules"
        preserved_rule.parent.mkdir()
        preserved_rule.write_text("KEEP-RULE", encoding="utf-8")
        new_profile = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        target_state = {"electron-persisted-atom-state": {
            "sidebar-custom-sections-v3": {new_profile: {"sections": []}},
            "chatgpt-conversation-resume-tokens-v1": {"new-private": {"token": "SYNTHETIC-TARGET-VALUE"}},
        }}
        (destination / ".codex-global-state.json").write_text(json.dumps(target_state), encoding="utf-8")

        with mock.patch.object(core, "codex_processes", return_value=[]):
            result = core.import_package(package, destination, [(str(self.old_home), str(new_home))], True)
        self.assertTrue(result["applied"])
        self.assertTrue(result["validation"]["ok"])
        self.assertEqual(result["validation"]["database_threads"], 2)
        self.assertEqual(result["validation"]["session_files"], 2)
        self.assertEqual(result["validation"]["automations"], 1)
        self.assertEqual(result["validation"]["custom_sections"], 1)
        self.assertTrue(Path(result["backup"]).is_file())
        self.assertEqual((destination / "auth.json").read_text(), "NEW-LOGIN")
        self.assertEqual((destination / "config.toml").read_text(), "new-machine=true")
        self.assertEqual(preserved_workspace.read_text(), "KEEP-WORKSPACE")
        self.assertEqual(preserved_rule.read_text(), "KEEP-RULE")
        imported_state = json.loads((destination / ".codex-global-state.json").read_text(encoding="utf-8"))
        sidebar = imported_state["electron-persisted-atom-state"]["sidebar-custom-sections-v3"]
        self.assertIn(new_profile, sidebar)
        self.assertNotIn("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sidebar)
        self.assertEqual(
            imported_state["electron-persisted-atom-state"]["chatgpt-conversation-resume-tokens-v1"]["new-private"]["token"],
            "SYNTHETIC-TARGET-VALUE",
        )
        db = sqlite3.connect(destination / "state_5.sqlite")
        rows = db.execute("SELECT rollout_path, cwd FROM threads ORDER BY id").fetchall()
        db.close()
        for rollout, cwd in rows:
            self.assertTrue(str(destination).lower() in rollout.lower())
            self.assertTrue(str(new_home).lower() in cwd.lower())

    def test_import_requires_explicit_replacement_confirmation(self):
        package = self.base / "transfer.zip"
        core.create_package(self.source, package)
        with self.assertRaises(core.TransferError):
            core.import_package(package, self.base / "new" / ".codex", [], False)

    def test_package_tamper_is_detected(self):
        package = self.base / "transfer.zip"
        core.create_package(self.source, package)
        rewritten = self.base / "tampered.zip"
        with zipfile.ZipFile(package, "r") as source, zipfile.ZipFile(rewritten, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename.endswith("image.bin"):
                    data = b"tampered"
                target.writestr(info, data)
        self.assertFalse(core.verify_package(rewritten)["ok"])

    def test_package_with_managed_workspace_payload_is_rejected(self):
        package = self.base / "transfer.zip"
        core.create_package(self.source, package)
        rewritten = self.base / "expanded-scope.zip"
        rogue_name = ".chatgpt-projects/project/source.txt"
        rogue_data = b"not allowed in lightweight packages"
        with zipfile.ZipFile(package, "r") as source:
            manifest = json.loads(source.read(core.MANIFEST_NAME))
            manifest["payload_files"].append({
                "path": rogue_name,
                "size": len(rogue_data),
                "sha256": hashlib.sha256(rogue_data).hexdigest(),
            })
            with zipfile.ZipFile(rewritten, "w") as target:
                for info in source.infolist():
                    if info.filename != core.MANIFEST_NAME:
                        target.writestr(info, source.read(info.filename))
                target.writestr(core.MANIFEST_NAME, json.dumps(manifest))
                target.writestr(rogue_name, rogue_data)
        result = core.verify_package(rewritten)
        self.assertFalse(result["ok"])
        self.assertEqual(result["disallowed"], [rogue_name])

    def test_windows_paths_are_normalized_before_mapping(self):
        self.assertEqual(
            core.normalize_path_text("D:/Users/Andy Xu/Desktop/Codex-Transfer.zip"),
            r"D:\Users\Andy Xu\Desktop\Codex-Transfer.zip",
        )
        self.assertEqual(core.normalize_path_text('"C:/Users/Andy Xu/.codex"'), r"C:\Users\Andy Xu\.codex")
        self.assertEqual(core.normalize_path_text("C:/"), "C:\\")
        maps = core.parse_path_maps([
            ("C:/Users/Andy Xu/Documents/Codex", "D:/Users/Andy Xu/Documents/Codex"),
        ])
        self.assertEqual(
            core.replace_path_prefix(r"C:\Users\Andy Xu\Documents\Codex\Project", maps),
            r"D:\Users\Andy Xu\Documents\Codex\Project",
        )
        automatic = core.automatic_path_maps(
            {
                "source_codex_dir": r"C:\Users\Old User\.codex",
                "source_user_home": r"C:\Users\Old User",
            },
            Path(r"D:\Users\New User\.codex"),
        )
        self.assertEqual(automatic[0], (r"C:\Users\Old User\.codex", r"D:\Users\New User\.codex"))
        self.assertEqual(automatic[1], (r"C:\Users\Old User", r"D:\Users\New User"))
        keep_original = core.parse_path_maps(automatic + [(r"C:\Users\Old User\Desktop", r"C:\Users\Old User\Desktop")])
        self.assertEqual(
            core.replace_path_prefix(r"C:\Users\Old User\Desktop\Project", keep_original),
            r"C:\Users\Old User\Desktop\Project",
        )

    def test_browse_buttons_always_use_short_browse_caption(self):
        for key in ("source_browse", "package_browse", "package_import_browse", "destination_browse"):
            self.assertEqual(gui.translation_key(key), "browse")
            self.assertLessEqual(len(gui.TEXT["zh"][gui.translation_key(key)]), 11)
            self.assertLessEqual(len(gui.TEXT["en"][gui.translation_key(key)]), 11)
        self.assertEqual(gui.translation_key("package_import"), "package")
        button_keys = (
            "browse", "scan", "create", "open_package_folder", "inspect_paths",
            "verify", "apply", "choose_new_path", "keep_old_path", "clear_path",
            "apply_path_maps",
        )
        for language in ("zh", "en"):
            for key in button_keys:
                self.assertTrue(gui.TEXT[language][key].strip(), f"Missing {language} caption for {key}")

    def test_package_path_inspection_groups_roots_without_reading_chat_text(self):
        external = r"D:\ESP32\AeroMeter"
        self.rollout_a.write_text(
            json.dumps({"type": "session_meta", "payload": {"cwd": external, "message": r"C:\Secret\MentionedOnly"}}) + "\n" +
            json.dumps({"type": "session_meta", "payload": {"cwd": str(Path.home() / "Documents" / "Example")}}) + "\n",
            encoding="utf-8",
        )
        package = self.base / "transfer.zip"
        core.create_package(self.source, package)
        destination = self.base / "New User" / ".codex"
        report = core.inspect_package_paths(package, destination)
        rows = {row["old"].casefold(): row for row in report["paths"]}
        self.assertIn(r"D:\ESP32".casefold(), rows)
        self.assertNotIn(r"C:\Secret".casefold(), rows)
        source_documents = str(Path.home().resolve() / "Documents").casefold()
        self.assertIn(source_documents, rows)
        self.assertTrue(report["plaintext"])
        expected_home = str(Path.home().resolve()).casefold()
        self.assertTrue(any(item["old"].casefold() == expected_home for item in report["automatic_maps"]))


if __name__ == "__main__":
    unittest.main()
