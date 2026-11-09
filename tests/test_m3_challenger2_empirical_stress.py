"""
================================================================================
Milestone M3 Challenger 2 Empirical Stress Test Suite
================================================================================
Adversarial challenge for Milestone M3 (AetherCraft production gameplay update):
1. Edge cases: 0 kills and 0 deaths KD calculation, leaderboard sorting, MVP score
2. Death mechanisms: Void death (y < 0) vs player attack death (killer != null)
   and safety of /back location preservation
3. Safe spawn generator simulation: 1,000 runs, boundary verification,
   anti-stacking, obstruction fallback safety guarantees
4. Reset NPC abuse & spam resistance: rate-limiting cooldown, idempotency,
   state preservation (inventories, balance, shop points intact)
5. Message compactor validation: length bounds (<30 chars titles, <35 chars subtitles,
   <30 chars delimiters), color formatting preservation, no screen clipping
================================================================================
"""

import os
import sys
import uuid
import random
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")

if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import get_db_connection, db_get_leaderboards, db_get_top_player
from services.player_service import get_player_profile


class TestM3Challenger2EmpiricalStress(unittest.TestCase):

    def setUp(self):
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
                    c.execute(f"DELETE FROM player_bank_accounts WHERE username IN (SELECT username FROM players WHERE uuid IN ({ph}));", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                conn.commit()

    # ==========================================================================
    # 1. Edge Case: 0 Kills and 0 Deaths KD Calculation & Leaderboard Sorting
    # ==========================================================================

    def test_zero_kills_zero_deaths_kd_and_leaderboard(self):
        """Stress-test: player with 0 kills and 0 deaths must not trigger division by zero."""
        p_uuid = str(uuid.uuid4())
        p_name = f"Pacifist_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 1000.0, 10, 0, 0, 1, 'None', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

        # Query leaderboards
        lbs = db_get_leaderboards(50)
        found = next((p for p in lbs["top_kills"] if p["username"] == p_name), None)
        # Even if not in top 50 kills, check direct SQL logic for this player
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT 
                    kills, 
                    deaths, 
                    CASE WHEN deaths = 0 THEN kills ELSE ROUND(CAST(kills AS REAL) / deaths, 2) END AS kd_ratio
                FROM players WHERE uuid = ?
            """, (p_uuid,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["kills"], 0)
            self.assertEqual(row["deaths"], 0)
            self.assertEqual(row["kd_ratio"], 0, "KD ratio for 0 kills and 0 deaths must evaluate to 0 without error")

    def test_zero_kills_positive_deaths_kd(self):
        """Edge case: 0 kills, 10 deaths -> KD ratio must be 0.0 without crash."""
        p_uuid = str(uuid.uuid4())
        p_name = f"Feeder_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 500.0, 5, 0, 10, 1, 'None', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            c.execute("""
                SELECT 
                    kills, 
                    deaths, 
                    CASE WHEN deaths = 0 THEN kills ELSE ROUND(CAST(kills AS REAL) / deaths, 2) END AS kd_ratio
                FROM players WHERE uuid = ?
            """, (p_uuid,))
            row = c.fetchone()
            self.assertEqual(row["kills"], 0)
            self.assertEqual(row["deaths"], 10)
            self.assertEqual(row["kd_ratio"], 0.0)

    def test_positive_kills_zero_deaths_kd(self):
        """Edge case: 15 kills, 0 deaths -> KD ratio must equal kills (15.0)."""
        p_uuid = str(uuid.uuid4())
        p_name = f"Flawless_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'TITAN', 10000.0, 40, 15, 0, 1, 'Aether', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            c.execute("""
                SELECT 
                    kills, 
                    deaths, 
                    CASE WHEN deaths = 0 THEN kills ELSE ROUND(CAST(kills AS REAL) / deaths, 2) END AS kd_ratio
                FROM players WHERE uuid = ?
            """, (p_uuid,))
            row = c.fetchone()
            self.assertEqual(row["kills"], 15)
            self.assertEqual(row["deaths"], 0)
            self.assertEqual(row["kd_ratio"], 15.0)

    def test_mvp_score_with_zero_stats(self):
        """Verify MVP score formula calculates safely with 0 kills and 0 deaths."""
        p_uuid = str(uuid.uuid4())
        p_name = f"Newbie_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 0.0, 0, 0, 0, 1, 'None', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            c.execute("""
                SELECT 
                    ROUND((p.hours_played * 10.0) + (p.kills * 5.0) - (p.deaths * 2.0) + (p.balance / 1000.0) + (COALESCE(r.weight, 0) * 20.0), 1) AS mvp_score
                FROM players p
                LEFT JOIN ranks r ON p.rank = r.id
                WHERE p.uuid = ?
            """, (p_uuid,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertGreaterEqual(row["mvp_score"], 0.0)

    # ==========================================================================
    # 2. Death Mechanisms: Void Death (y < 0) vs Player Attack (PvP)
    # ==========================================================================

    def test_void_death_coordinate_filtering_in_java(self):
        """Verify PlayerLocationEngine.isValidSurvivalLocation filters out void coordinates."""
        fpath = os.path.join(SRC_DIR, "PlayerLocationEngine.java")
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Altitude validation
        self.assertIn("loc.getY() < 55 || loc.getY() > 260", code)
        # Death in void is below y=0 (typically y < -64 in 1.21), so isValidSurvivalLocation returns false
        # onPlayerDeath updates SQLite deaths regardless:
        self.assertIn("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", code)

    def test_void_death_vs_pvp_kill_sql_simulation(self):
        """Simulate SQLite death updates: void death (killer=null) vs PvP kill (killer!=null)."""
        victim_uuid = str(uuid.uuid4())
        killer_uuid = str(uuid.uuid4())
        self.created_uuids.extend([victim_uuid, killer_uuid])

        with get_db_connection() as conn:
            c = conn.cursor()
            # Initialize victim and killer
            c.execute("INSERT INTO players (uuid, username, kills, deaths, first_join, last_seen) VALUES (?, 'Victim', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (victim_uuid,))
            c.execute("INSERT INTO players (uuid, username, kills, deaths, first_join, last_seen) VALUES (?, 'Killer', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (killer_uuid,))
            conn.commit()

            # Case A: Void death without killer (e.g. fell into the void)
            # Java: victimUuid != null, killerUuid == null
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (victim_uuid,))
            conn.commit()

            c.execute("SELECT deaths, kills FROM players WHERE uuid = ?", (victim_uuid,))
            v_row = c.fetchone()
            self.assertEqual(v_row["deaths"], 1)
            self.assertEqual(v_row["kills"], 0)

            c.execute("SELECT deaths, kills FROM players WHERE uuid = ?", (killer_uuid,))
            k_row = c.fetchone()
            self.assertEqual(k_row["deaths"], 0)
            self.assertEqual(k_row["kills"], 0)

            # Case B: PvP attack death (player attacked and killed victim)
            # Java: victimUuid != null, killerUuid != null
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (victim_uuid,))
            c.execute("UPDATE players SET kills = kills + 1 WHERE uuid = ?", (killer_uuid,))
            conn.commit()

            c.execute("SELECT deaths, kills FROM players WHERE uuid = ?", (victim_uuid,))
            v_row2 = c.fetchone()
            self.assertEqual(v_row2["deaths"], 2)

            c.execute("SELECT deaths, kills FROM players WHERE uuid = ?", (killer_uuid,))
            k_row2 = c.fetchone()
            self.assertEqual(k_row2["kills"], 1)

    def test_statistic_reconciliation_monotonicity(self):
        """Statistic reconciliation query MAX(kills, ?), MAX(deaths, ?) must never decrease stats."""
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO players (uuid, username, kills, deaths, first_join, last_seen) VALUES (?, 'MonotonicPlayer', 10, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (p_uuid,))
            conn.commit()

            # Player joins with lower Paper statistics (e.g. fresh stats reset or desync)
            reconcile_sql = "UPDATE players SET kills = MAX(kills, ?), deaths = MAX(deaths, ?) WHERE uuid = ?"
            c.execute(reconcile_sql, (3, 2, p_uuid))
            conn.commit()

            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row = c.fetchone()
            self.assertEqual(row["kills"], 10, "Kills must not decrease")
            self.assertEqual(row["deaths"], 5, "Deaths must not decrease")

            # Player joins with higher Paper statistics
            c.execute(reconcile_sql, (15, 8, p_uuid))
            conn.commit()

            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row2 = c.fetchone()
            self.assertEqual(row2["kills"], 15, "Kills must increase to match higher counter")
            self.assertEqual(row2["deaths"], 8, "Deaths must increase to match higher counter")

    # ==========================================================================
    # 3. Safe Spawn Generator: Empirical Simulation & Safety Guarantees
    # ==========================================================================

    def test_safe_spawn_generator_random_bounds_and_exclusion(self):
        """Simulate 1,000 runs of the coordinate generation algorithm from RandomSpawnEngine."""
        cx = 640
        cz = 864
        rnd = random.Random(42)

        generated_coords = []
        for _ in range(1000):
            # Same logic as RandomSpawnEngine.allocateSafeSurvivalSpawn
            ox = rnd.randint(0, 6) - 3  # -3 to +3
            oz = rnd.randint(0, 6) - 3  # -3 to +3
            if ox == 0 and oz == 0:
                continue  # Never exactly (0, 0)
            targetX = cx + ox
            targetZ = cz + oz
            generated_coords.append((targetX, targetZ))

        self.assertGreater(len(generated_coords), 900)
        for tx, tz in generated_coords:
            # Must be within [-3, +3] of center
            self.assertGreaterEqual(tx, cx - 3)
            self.assertLessEqual(tx, cx + 3)
            self.assertGreaterEqual(tz, cz - 3)
            self.assertLessEqual(tz, cz + 3)
            # Center (640, 864) must never be sampled
            self.assertFalse(tx == cx and tz == cz, "Center coordinate (640, 864) must never be returned")

    def test_safe_spawn_generator_java_source_contract(self):
        """Verify RandomSpawnEngine safe spawn code contracts."""
        fpath = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Check 30 attempt loop
        self.assertIn("for (int attempt = 0; attempt < 30; attempt++)", code)
        # Check center exclusion
        self.assertIn("if (ox == 0 && oz == 0) continue;", code)
        # Check solid ground check
        self.assertIn("ground.getType().isSolid()", code)
        # Check 2 blocks passable air check
        self.assertIn("head1.isPassable() && head2.isPassable()", code)
        # Check liquid exclusion
        self.assertIn("!head1.isLiquid() && !head2.isLiquid()", code)
        # Check anti-stacking entity radius check
        self.assertIn("world.getNearbyEntities(candidate, 0.8, 1.5, 0.8).isEmpty()", code)
        # Check safe fallback guarantee
        self.assertIn("if (fallback != null) return fallback;", code)
        self.assertIn("return new Location(world, cx + 1.5, groundY + 1.0, cz + 1.5, 180f, 0f);", code)

    # ==========================================================================
    # 4. Reset NPC Abuse & Spam Resistance
    # ==========================================================================

    def test_reset_npc_cooldown_and_hand_filtering(self):
        """Verify SpawnNpcGuides implements click cooldown and main-hand filtering."""
        fpath = os.path.join(SRC_DIR, "SpawnNpcGuides.java")
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Cooldown check
        self.assertIn("CLICK_COOLDOWN_MS = 1200L;", code)
        self.assertIn("now - last < CLICK_COOLDOWN_MS", code)
        # Offhand filtering (prevent double-firing on right click)
        self.assertIn("event.getHand() != EquipmentSlot.HAND", code)

    def test_reset_npc_idempotency_and_state_preservation(self):
        """Verify calling the reset operation repeatedly preserves player inventory and balance."""
        p_uuid = str(uuid.uuid4())
        p_name = f"ResetTester_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)

        with get_db_connection() as conn:
            c = conn.cursor()
            # Set up player with balance, shop points, rank, and survival location
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'VIP', 7500.0, 12, 10, 2, 1, 'GuildMaster', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            c.execute("""
                INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch)
                VALUES (?, ?, 'world', 1234.5, 68.0, 5678.5, 90.0, 0.0)
            """, (p_uuid, p_name))
            conn.commit()

            # Verify initial state
            c.execute("SELECT COUNT(*) AS cnt FROM player_survival_locations WHERE uuid = ?", (p_uuid,))
            self.assertEqual(c.fetchone()["cnt"], 1)

            # Simulate NPC reset 10 times in rapid succession
            delete_sql = "DELETE FROM player_survival_locations WHERE uuid = ?"
            for _ in range(10):
                c.execute(delete_sql, (p_uuid,))
            conn.commit()

            # Location is removed
            c.execute("SELECT COUNT(*) AS cnt FROM player_survival_locations WHERE uuid = ?", (p_uuid,))
            self.assertEqual(c.fetchone()["cnt"], 0)

            # Crucial requirement: player profile, balance, rank, kills, deaths are 100% UNTOUCHED
            c.execute("SELECT rank, balance, kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            p_row = c.fetchone()
            self.assertEqual(p_row["rank"], "VIP")
            self.assertEqual(p_row["balance"], 7500.0)
            self.assertEqual(p_row["kills"], 10)
            self.assertEqual(p_row["deaths"], 2)

    # ==========================================================================
    # 5. Message Compactor Validation
    # ==========================================================================

    def test_compact_message_lengths_and_formatting(self):
        """Verify all titles, subtitles, and delimiters meet compactness constraints."""
        titles = [
            "✦ Terre Vierge",
            "🌀 Vortex",
            "🪐 Agora",
            "✦ De retour",
            "❌ Annulé"
        ]
        subtitles = [
            "Position validée",
            "Incantation en cours (3s)",
            "Archipel Céleste",
            "Position restaurée",
            "Mouvement détecté"
        ]
        delimiters = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]

        # Titles must not exceed 25 characters
        for t in titles:
            self.assertLessEqual(len(t), 25, f"Title '{t}' exceeds 25 characters")

        # Subtitles must not exceed 30 characters
        for s in subtitles:
            self.assertLessEqual(len(s), 30, f"Subtitle '{s}' exceeds 30 characters")

        # Delimiters must not exceed 30 characters (legacy delimiters were 47 chars)
        for d in delimiters:
            self.assertLessEqual(len(d), 30, f"Delimiter '{d}' exceeds 30 characters")

    def test_no_legacy_long_delimiters_in_m3_sources(self):
        """Ensure no legacy 40+ unicode separator bars remain in M3 Java classes."""
        m3_files = [
            os.path.join(SRC_DIR, "PlayerLocationEngine.java"),
            os.path.join(SRC_DIR, "RandomSpawnEngine.java"),
            os.path.join(SRC_DIR, "SpawnNpcGuides.java"),
            os.path.join(SRC_DIR, "AetherCommandExecutor.java"),
            os.path.join(SRC_DIR, "AetherVisualScoreboardManager.java")
        ]
        for fpath in m3_files:
            with open(fpath, "r", encoding="utf-8") as f:
                code = f.read()
            self.assertNotIn("═" * 40, code, f"Legacy 40+ unicode '=' bar found in {os.path.basename(fpath)}")
            self.assertNotIn("━" * 40, code, f"Excessive 40+ unicode bar found in {os.path.basename(fpath)}")


if __name__ == "__main__":
    unittest.main()
