"""
================================================================================
Milestone M3 Test Suite: Paper Server Visuals & Data Sync (F9, F10, F11, F12, F13)
================================================================================
Validates:
- F9: Eradication of broken player_balances queries and relative DB paths in Java classes.
- F10: Tablist header/footer format and rank prefix resolution.
- F11: Sidebar Scoreboard title and line structure.
- F12: Registration and implementation of /top, /baltop, /classement commands.
- F13: [6] Classements tab and live leaderboard integration in webdisplay.html.
- Compilation and integrity of server/plugins/AetherVisuals.jar.
================================================================================
"""

import os
import sys
import unittest
import zipfile
import sqlite3
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
JAR_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")
WEBDISPLAY_HTML = os.path.join(PROJECT_ROOT, "web", "templates", "webdisplay.html")


class TestM3VisualsSync(unittest.TestCase):

    def test_f9_no_broken_player_balances_or_relative_db_in_java(self):
        """Feature F9: Ensure MMORPGDisplayEngine, AetherMMOShopCatalog, and DungeonMobSpellCaster query players/users."""
        files_to_check = [
            os.path.join(SRC_DIR, "MMORPGDisplayEngine.java"),
            os.path.join(SRC_DIR, "AetherMMOShopCatalog.java"),
            os.path.join(SRC_DIR, "DungeonMobSpellCaster.java")
        ]
        for fpath in files_to_check:
            self.assertTrue(os.path.exists(fpath), f"File {fpath} must exist")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Must NOT reference nonexistent player_balances
            self.assertNotIn("player_balances", content, f"{fpath} must not query nonexistent player_balances table")

            # Must NOT use broken relative path
            self.assertNotIn('DriverManager.getConnection("jdbc:sqlite:server/data/aethercraft.db")', content,
                             f"{fpath} must not hardcode relative connection string")

            # Must use AetherDatabase.getConnection()
            self.assertIn("AetherDatabase.getConnection()", content,
                          f"{fpath} must use centralized AetherDatabase.getConnection()")

    def test_f9_no_hardcoded_balance_fallbacks(self):
        """Feature F9: Verify removal of hardcoded return 100 / return 10 fallbacks."""
        for fname in ["MMORPGDisplayEngine.java", "AetherMMOShopCatalog.java"]:
            fpath = os.path.join(SRC_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("return 100;", content, f"{fname} must not have hardcoded return 100 fallback")
            self.assertNotIn("return 10;", content, f"{fname} must not have hardcoded return 10 fallback")

    def test_f10_tablist_specifications_in_scoreboard_manager(self):
        """Feature F10: Verify Tablist header, footer, and rank prefix logic."""
        manager_file = os.path.join(SRC_DIR, "AetherVisualScoreboardManager.java")
        self.assertTrue(os.path.exists(manager_file), f"Manager {manager_file} must exist")
        with open(manager_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Header exact string check
        self.assertIn("§6✦ §lAETHERCRAFT §6✦\\n§7Archipel Céleste 1.21.1", content,
                      "Tablist header must match specification")

        # Footer format check
        self.assertIn("§e✦ Boutique: §faethercraft.io §8| §bJoueurs: §f%d/%d", content,
                      "Tablist footer must match specification with dynamic counts")

        # Rank prefix formatting and setPlayerListName
        self.assertIn("setPlayerListName", content, "Must format player tablist name with rank prefix")
        self.assertIn("getRankFormattedPrefix", content, "Must resolve rank prefix from SQLite ranks")

    def test_f11_sidebar_scoreboard_specification(self):
        """Feature F11: Verify in-game sidebar Scoreboard title and line items."""
        manager_file = os.path.join(SRC_DIR, "AetherVisualScoreboardManager.java")
        with open(manager_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("§6§l✦ AETHERCRAFT ✦", content, "Scoreboard objective title must match")
        self.assertIn("DisplaySlot.SIDEBAR", content, "Must display on SIDEBAR slot")
        self.assertIn("§fPseudo: §e", content, "Scoreboard must display player name")
        self.assertIn("§fRang: ", content, "Scoreboard must display player rank")
        self.assertIn("§fSolde: §6", content, "Scoreboard must display balance with ⛃ currency")
        self.assertIn("§fPoints: §b", content, "Scoreboard must display shop points")
        self.assertIn("§fEn ligne: §a", content, "Scoreboard must display online count")
        self.assertIn("§ewww.aethercraft.io", content, "Scoreboard must display server URL")

    def test_f12_ingame_ranking_commands_registered(self):
        """Feature F12: Verify /top, /baltop, /classement commands in executor and plugin.yml."""
        yml_path = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "plugin.yml")
        with open(yml_path, "r", encoding="utf-8") as f:
            yml_content = f.read()

        self.assertIn("top:", yml_content, "plugin.yml must declare command 'top'")
        self.assertIn("baltop", yml_content, "plugin.yml must alias 'baltop'")
        self.assertIn("classement", yml_content, "plugin.yml must alias 'classement'")

        exec_path = os.path.join(SRC_DIR, "AetherCommandExecutor.java")
        with open(exec_path, "r", encoding="utf-8") as f:
            exec_content = f.read()

        self.assertIn('"top"', exec_content, "AetherCommandExecutor must handle 'top'")
        self.assertIn("displayLeaderboard", exec_content, "AetherCommandExecutor must render leaderboards")

        tab_path = os.path.join(SRC_DIR, "AetherTabCompleter.java")
        with open(tab_path, "r", encoding="utf-8") as f:
            tab_content = f.read()
        self.assertIn('"fortune"', tab_content, "Tab completer must suggest 'fortune'")
        self.assertIn('"temps"', tab_content, "Tab completer must suggest 'temps'")
        self.assertIn('"kills"', tab_content, "Tab completer must suggest 'kills'")

    def test_f13_webdisplay_classements_tab_and_view(self):
        """Feature F13: Verify [6] Classements tab and leaderboard UI in webdisplay.html."""
        self.assertTrue(os.path.exists(WEBDISPLAY_HTML), f"webdisplay.html must exist at {WEBDISPLAY_HTML}")
        with open(WEBDISPLAY_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        # Tab button check
        self.assertIn("[6] Classements", html, "Must contain navigation tab [6] Classements")
        self.assertIn('data-shortcut="6"', html, "Must support numeric shortcut 6")

        # Mode panel check
        self.assertIn("active_mode in ['rankings', 'classements', 'top']", html,
                      "Must contain template block for rankings/classements mode")
        self.assertIn("TOP FORTUNE", html, "Must display Top Fortune section")
        self.assertIn("TOP TEMPS DE JEU", html, "Must display Top Temps de Jeu section")

        # Footer shortcut hint check
        self.assertIn("[1-6] : Onglets", html, "Footer must inform about shortcuts 1-6")

    def test_plugin_jar_compilation_and_bytecode_integrity(self):
        """Verifies server/plugins/AetherVisuals.jar exists, has valid bytecode, and includes M3 classes."""
        self.assertTrue(os.path.exists(JAR_PATH), f"Plugin JAR must exist at {JAR_PATH}")
        self.assertGreater(os.path.getsize(JAR_PATH), 500_000, "Plugin JAR size should exceed 500KB")

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = set(z.namelist())
            self.assertIn("plugin.yml", names, "JAR must contain plugin.yml in root")
            self.assertIn("io/aethercraft/visuals/AetherVisualScoreboardManager.class", names,
                          "JAR must contain compiled AetherVisualScoreboardManager.class")
            self.assertIn("io/aethercraft/visuals/AetherVisualScoreboardManager$LeaderboardEntry.class", names)
            self.assertIn("io/aethercraft/visuals/AetherVisualScoreboardManager$PlayerVisualData.class", names)
            self.assertIn("io/aethercraft/visuals/AetherVisualsPlugin.class", names)
            self.assertIn("io/aethercraft/visuals/AetherCommandExecutor.class", names)
            self.assertIn("io/aethercraft/visuals/MMORPGDisplayEngine.class", names)
            self.assertIn("io/aethercraft/visuals/AetherMMOShopCatalog.class", names)
            self.assertIn("io/aethercraft/visuals/DungeonMobSpellCaster.class", names)

            # Check plugin.yml inside JAR
            yml_data = z.read("plugin.yml").decode("utf-8")
            self.assertIn("top:", yml_data, "JAR plugin.yml must contain 'top:' command")


if __name__ == "__main__":
    unittest.main(verbosity=2)
