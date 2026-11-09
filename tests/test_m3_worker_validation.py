"""
================================================================================
Milestone M3 Worker Validation Test Suite
================================================================================
Validates Milestone M3 gameplay features, contracts, and behavior:
1. F8: Kills & deaths event synchronization logic & Statistic reconciliation
2. F9: Displays & Leaderboards harmonization
3. F10: Per-player safe randomized survival spawn allocation & over-stacking prevention
4. F11: Interactive Spawn Reset NPC ("Gardien des Âmes")
5. F19: Compact in-game messages
================================================================================
"""

import os
import sys
import uuid
import sqlite3
import zipfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
JAR_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")

if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import get_db_connection, db_get_leaderboards
from services.player_service import get_player_profile


class TestMilestone3WorkerValidation(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids = []
        self.created_usernames = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM player_survival_locations WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                conn.commit()

    def test_f8_player_location_engine_kills_deaths_sync_contract(self):
        """Contract F8: PlayerLocationEngine must implement death increments and statistic reconciliation."""
        fpath = os.path.join(SRC_DIR, "PlayerLocationEngine.java")
        self.assertTrue(os.path.exists(fpath))
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Victim death increment in SQLite
        self.assertIn("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", code)
        # Killer kill increment in SQLite
        self.assertIn("UPDATE players SET kills = kills + 1 WHERE uuid = ?", code)
        # Statistic reconciliation with Paper native counters
        self.assertIn("Statistic.DEATHS", code)
        self.assertIn("Statistic.PLAYER_KILLS", code)
        self.assertIn("UPDATE players SET kills = MAX(kills, ?), deaths = MAX(deaths, ?) WHERE uuid = ?", code)

    def test_f9_leaderboards_and_profile_real_frags(self):
        """Feature F9: Real kills/deaths synchronized into leaderboards and profiles."""
        p_uuid = str(uuid.uuid4())
        p_name = f"FragMaster_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'CHAMPION', 5000.0, 25, 42, 6, 1, 'Warriors', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

        # Web Profile check
        profile = get_player_profile(p_name)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["kills"], 42)
        self.assertEqual(profile["deaths"], 6)

        # Leaderboards check
        lbs = db_get_leaderboards(10)
        found = next((p for p in lbs["top_kills"] if p["username"] == p_name), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["kills"], 42)
        self.assertEqual(found["deaths"], 6)
        self.assertEqual(found["kd_ratio"], 7.0)

    def test_f10_random_spawn_engine_contracts(self):
        """Feature F10: RandomSpawnEngine per-player allocation, over-stacking prevention, bed fallback."""
        fpath = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        self.assertTrue(os.path.exists(fpath))
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Safe allocation method must be present
        self.assertIn("allocateSafeSurvivalSpawn", code)
        # Anti-stacking proximity entity check
        self.assertIn("getNearbyEntities", code)
        # Bed fallback notification
        self.assertIn("Votre point de spawn ou lit était détruit/inaccessible", code)
        # Over-stacking prevention on teleport
        self.assertIn("onPlayerTeleport", code)

    def test_f11_spawn_reset_npc_contract(self):
        """Feature F11: 'Gardien des Âmes' reset NPC in SpawnNpcGuides.java."""
        fpath = os.path.join(SRC_DIR, "SpawnNpcGuides.java")
        self.assertTrue(os.path.exists(fpath))
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Registration of Gardien des Âmes with Cleric profession
        self.assertIn("Gardien des Âmes", code)
        self.assertIn("Villager.Profession.CLERIC", code)
        # Reset operations
        self.assertIn("setBedSpawnLocation(null, true)", code)
        self.assertIn("deleteSurvivalLocationAsync", code)
        # Visual & audio feedback
        self.assertIn("Sound.UI_TOAST_CHALLENGE_COMPLETE", code)
        self.assertIn("Particle.TOTEM_OF_UNDYING", code)

    def test_f19_compact_ingame_messages(self):
        """Feature F19: In-game titles, subtitles, and delimiters formatted compactly."""
        ple_path = os.path.join(SRC_DIR, "PlayerLocationEngine.java")
        rse_path = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        ace_path = os.path.join(SRC_DIR, "AetherCommandExecutor.java")

        with open(ple_path, "r", encoding="utf-8") as f:
            ple_code = f.read()
        with open(rse_path, "r", encoding="utf-8") as f:
            rse_code = f.read()
        with open(ace_path, "r", encoding="utf-8") as f:
            ace_code = f.read()

        # Check compact titles (not long legacy banners)
        self.assertIn("✦ De retour", ple_code)
        self.assertIn("🌀 Vortex", rse_code)
        self.assertIn("✦ Terre Vierge", rse_code)
        self.assertIn("🪐 Agora", ace_code)
        self.assertNotIn("═" * 40, rse_code, "Long 40+ character delimiters must be replaced with compact dividers")

    def test_plugin_jar_contains_m3_bytecode(self):
        """Plugin JAR verification: must contain compiled bytecode for all M3 classes."""
        self.assertTrue(os.path.exists(JAR_PATH))
        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = set(z.namelist())
            self.assertIn("io/aethercraft/visuals/PlayerLocationEngine.class", names)
            self.assertIn("io/aethercraft/visuals/RandomSpawnEngine.class", names)
            self.assertIn("io/aethercraft/visuals/SpawnNpcGuides.class", names)
            self.assertIn("io/aethercraft/visuals/AetherVisualScoreboardManager.class", names)
            self.assertIn("io/aethercraft/visuals/AetherCommandExecutor.class", names)


if __name__ == "__main__":
    unittest.main()
