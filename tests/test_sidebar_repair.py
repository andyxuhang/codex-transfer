import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codex_sidebar_repair_core as repair
import codex_sidebar_repair as gui


class SidebarRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp_context = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_context.name)
        self.local = self.base / "Local"
        self.profile = (
            self.local / "Packages" / "OpenAI.Codex_test" / "LocalCache" / "Roaming"
            / "Codex" / "web" / "Codex" / "Default"
        )
        (self.profile / "Local Storage" / "leveldb").mkdir(parents=True)
        (self.profile / "Local Storage" / "leveldb" / "000001.log").write_bytes(b"stale sidebar")
        (self.profile / "Session Storage").mkdir()
        (self.profile / "Session Storage" / "CURRENT").write_text("MANIFEST", encoding="utf-8")
        (self.profile / "Network").mkdir()
        (self.profile / "Network" / "Cookies").write_bytes(b"KEEP-LOGIN")
        self.codex = self.base / "User" / ".codex"
        session = self.codex / "sessions" / "2026" / "01" / "01" / "rollout-valid.jsonl"
        session.parent.mkdir(parents=True)
        session.write_text("{}\n", encoding="utf-8")
        orphan = self.codex / "archived_sessions" / "rollout-orphan.jsonl"
        orphan.parent.mkdir()
        orphan.write_text("{}\n", encoding="utf-8")
        database = sqlite3.connect(self.codex / "state_5.sqlite")
        database.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, title TEXT)")
        database.execute("INSERT INTO threads VALUES ('valid', ?, 'Valid')", (str(session),))
        database.execute("INSERT INTO threads VALUES ('missing', ?, 'Missing')", (str(self.codex / "sessions" / "gone.jsonl"),))
        database.commit()
        database.close()

    def tearDown(self):
        self.temp_context.cleanup()

    def test_scan_distinguishes_missing_records_and_unreferenced_files(self):
        report = repair.scan_sidebar_state(self.codex, self.local)
        self.assertEqual(len(report["profiles"]), 1)
        self.assertEqual(report["local_threads"]["database_threads"], 2)
        self.assertEqual(report["local_threads"]["session_files"], 2)
        self.assertEqual(report["local_threads"]["missing_rollout_records"][0]["thread_id"], "missing")
        self.assertEqual(len(report["local_threads"]["unreferenced_session_files"]), 1)

    def test_rebuild_backs_up_cache_and_preserves_cookies(self):
        backup_dir = self.base / "Backups"
        with mock.patch.object(repair.transfer, "codex_processes", return_value=[]):
            result = repair.rebuild_sidebar_cache([self.profile], backup_dir, True)
        self.assertTrue(result["applied"])
        self.assertFalse((self.profile / "Local Storage").exists())
        self.assertFalse((self.profile / "Session Storage").exists())
        self.assertEqual((self.profile / "Network" / "Cookies").read_bytes(), b"KEEP-LOGIN")
        backup = Path(result["backup"])
        self.assertTrue(backup.is_file())
        with zipfile.ZipFile(backup) as archive:
            manifest = json.loads(archive.read("codex-sidebar-backup-manifest.json"))
            self.assertEqual(manifest["format"], repair.BACKUP_FORMAT)
            names = set(archive.namelist())
        self.assertIn("profiles/0/Local Storage/leveldb/000001.log", names)
        self.assertNotIn("profiles/0/Network/Cookies", names)

    def test_rebuild_requires_confirmation_and_closed_app(self):
        with self.assertRaises(repair.RepairError):
            repair.rebuild_sidebar_cache([self.profile], self.base / "Backups", False)
        with mock.patch.object(repair.transfer, "codex_processes", return_value=["codex.exe"]):
            with self.assertRaises(repair.RepairError):
                repair.rebuild_sidebar_cache([self.profile], self.base / "Backups", True)

    def test_gui_text_is_bilingual_and_fixed_buttons_fit(self):
        self.assertEqual(set(gui.TEXT["zh"]), set(gui.TEXT["en"]))
        self.assertEqual(gui.localize_core_message("Preparing Local Storage", "zh"), "正在准备：Local Storage")
        self.assertEqual(gui.localize_core_message("Preparing Local Storage", "en"), "Preparing Local Storage")
        widths = {"browse": 11, "scan": 18, "repair": 36}
        for language in ("zh", "en"):
            for key, width in widths.items():
                self.assertLessEqual(len(gui.TEXT[language][key]), width, (language, key))

    @unittest.skipUnless(sys.platform == "win32", "real Tk window construction is tested on Windows")
    def test_real_gui_window_can_be_constructed(self):
        with mock.patch.object(gui.transfer, "codex_processes", return_value=[]), mock.patch.object(
            gui.core, "discover_codex_profiles", return_value=[]
        ):
            try:
                app = gui.SidebarRepairApp()
            except Exception as exc:
                if "init.tcl" in str(exc):
                    self.skipTest("the local embedded Python runtime does not include Tcl/Tk")
                raise
            try:
                app.root.update_idletasks()
                self.assertTrue(app.root.winfo_exists())
            finally:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
