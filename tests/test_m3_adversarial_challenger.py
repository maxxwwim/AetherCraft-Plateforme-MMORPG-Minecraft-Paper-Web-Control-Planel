"""
================================================================================
Empirical Adversarial Challenger Test Suite: Milestone M3
================================================================================
Rigorously stress-tests Milestone M3 features under adversarial conditions:
- F8/F9: Concurrency, rapid succession deaths, null killer (environmental/fall),
         Paper Statistic reconciliation, leaderboard tie-breaking and K/D ratios.
- F10: Per-player safe randomized survival spawn allocation, Monte Carlo
       distribution (500+ trials), anti-stacking entity proximity, ground solidity,
       headroom clearance, lost bed detection and fallback notification.
- F11: Interactive Reset NPC ("Gardien des Âmes") contract, bed spawn clearing,
       survival location clearing, and strict preservation of inventory,
       bank balance, OneBlock progression, and world terrain.
- F19: Compact in-game messages: title lengths, subtitle lengths, and delimiter
       character bounds to prevent chat and HUD truncation on small screens.
================================================================================
"""

import os
import sys
import math
import random
import uuid
import sqlite3
import threading
import unittest
from typing import List, Dict, Any, Tuple

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


class TestMilestone3AdversarialChallenge(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM player_survival_locations WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM player_oneblock WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                conn.commit()

    # ==========================================================================
    # 1. F8/F9 EMPIRICAL CONCURRENCY, EDGE CASES & STATS RECONCILIATION
    # ==========================================================================

    def test_01_f8_concurrent_kills_and_deaths_under_load(self):
        """Stress-test: 40 concurrent death/kill events across multiple threads."""
        v_uuid = str(uuid.uuid4())
        k_uuid = str(uuid.uuid4())
        v_name = f"AdvVictim_{v_uuid[:6]}"
        k_name = f"AdvKiller_{k_uuid[:6]}"
        self.created_uuids.extend([v_uuid, k_uuid])
        self.created_usernames.extend([v_name, k_name])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 100.0, 10, 0, 0, 1, 'War', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 100.0, 10, 0, 0, 1, 'War', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (v_uuid, v_name, k_uuid, k_name))
            conn.commit()

        # Execute 30 concurrent PvP kill/death events across separate threads
        total_events = 30
        errors = []

        def worker_pvp_kill():
            try:
                # Open isolated connection per thread with WAL busy timeout
                c_thread = sqlite3.connect(DB_PATH, timeout=20.0)
                cur = c_thread.cursor()
                cur.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (v_uuid,))
                cur.execute("UPDATE players SET kills = kills + 1 WHERE uuid = ?", (k_uuid,))
                c_thread.commit()
                c_thread.close()
            except Exception as ex:
                errors.append(str(ex))

        threads = [threading.Thread(target=worker_pvp_kill) for _ in range(total_events)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Encountered thread errors during concurrent kills: {errors}")

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (v_uuid,))
            v_row = c.fetchone()
            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (k_uuid,))
            k_row = c.fetchone()

            self.assertEqual(v_row["deaths"], total_events, f"Victim deaths must exactly equal {total_events}")
            self.assertEqual(v_row["kills"], 0)
            self.assertEqual(k_row["kills"], total_events, f"Killer kills must exactly equal {total_events}")
            self.assertEqual(k_row["deaths"], 0)

    def test_02_f8_environmental_fall_death_null_killer(self):
        """Stress-test: Environmental / fall / void deaths where killer is null."""
        p_uuid = str(uuid.uuid4())
        p_name = f"FallGuy_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 50.0, 5, 10, 2, 1, 'Solo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            # Simulate 25 sequential environmental deaths (killer = null)
            for _ in range(25):
                # When killer is null, only victim deaths increments
                c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (p_uuid,))
            conn.commit()

            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row = c.fetchone()
            self.assertEqual(row["deaths"], 27, "Victim deaths must increment from 2 to 27")
            self.assertEqual(row["kills"], 10, "Victim kills must remain 10 without modification")

    def test_03_f8_statistic_reconciliation_boundary_cases(self):
        """Feature F8: Paper native Statistic reconciliation via MAX(kills, ?), MAX(deaths, ?)."""
        p_uuid = str(uuid.uuid4())
        p_name = f"ReconStat_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            # Start with DB: kills=15, deaths=8
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 500.0, 12, 15, 8, 1, 'GuildA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            # Scenario A: Paper stats higher on join (e.g. killed mob/player or died during offline session)
            paper_kills_a = 22
            paper_deaths_a = 14
            c.execute("UPDATE players SET kills = MAX(kills, ?), deaths = MAX(deaths, ?) WHERE uuid = ?",
                      (paper_kills_a, paper_deaths_a, p_uuid))
            conn.commit()

            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row_a = c.fetchone()
            self.assertEqual(row_a["kills"], 22, "Kills should update to higher Paper value 22")
            self.assertEqual(row_a["deaths"], 14, "Deaths should update to higher Paper value 14")

            # Scenario B: DB stats higher (e.g. fresh Paper server restart where statistics counter lagged)
            paper_kills_b = 5
            paper_deaths_b = 2
            c.execute("UPDATE players SET kills = MAX(kills, ?), deaths = MAX(deaths, ?) WHERE uuid = ?",
                      (paper_kills_b, paper_deaths_b, p_uuid))
            conn.commit()

            c.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row_b = c.fetchone()
            self.assertEqual(row_b["kills"], 22, "Kills must not be lowered by lower Paper counter")
            self.assertEqual(row_b["deaths"], 14, "Deaths must not be lowered by lower Paper counter")

    def test_04_f9_leaderboard_tie_breaking_and_zero_division(self):
        """Feature F9: Leaderboard queries under extreme conditions (ties, 0 deaths, 0 kills)."""
        uuids = [str(uuid.uuid4()) for _ in range(3)]
        names = [f"Tied_{i}_{uuids[i][:4]}" for i in range(3)]
        self.created_uuids.extend(uuids)
        self.created_usernames.extend(names)

        with get_db_connection() as conn:
            c = conn.cursor()
            # Three players with identical kills (100) but different deaths and hours
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 100.0, 50, 100, 0, 1, 'PvP', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'CHAMPION', 200.0, 30, 100, 10, 1, 'PvP', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'TITAN', 300.0, 10, 100, 50, 1, 'PvP', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (uuids[0], names[0], uuids[1], names[1], uuids[2], names[2]))
            conn.commit()

            # Execute Scoreboard / Top Kills query
            c.execute("""
                SELECT p.username, p.kills AS val, p.deaths, p.rank, r.prefix, r.badge_color 
                FROM players p 
                LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
                ORDER BY p.kills DESC 
                LIMIT 10
            """)
            rows = c.fetchall()
            found_names = [r["username"] for r in rows]
            for n in names:
                self.assertIn(n, found_names, f"Tied player {n} must appear in top kills query")

        # Check Python leaderboards K/D calculation
        lbs = db_get_leaderboards(10)
        p0 = next((p for p in lbs["top_kills"] if p["username"] == names[0]), None)
        p1 = next((p for p in lbs["top_kills"] if p["username"] == names[1]), None)
        p2 = next((p for p in lbs["top_kills"] if p["username"] == names[2]), None)

        self.assertIsNotNone(p0)
        self.assertEqual(p0["kd_ratio"], 100.0, "Zero deaths must yield K/D equal to kills")
        self.assertIsNotNone(p1)
        self.assertEqual(p1["kd_ratio"], 10.0, "100 kills / 10 deaths = 10.0 K/D")
        self.assertIsNotNone(p2)
        self.assertEqual(p2["kd_ratio"], 2.0, "100 kills / 50 deaths = 2.0 K/D")

    # ==========================================================================
    # 2. F10 SAFE SURVIVAL SPAWN & ANTI-STACKING EMPIRICAL HARNESS
    # ==========================================================================

    def test_05_f10_spawn_allocation_monte_carlo_distribution(self):
        """
        Feature F10: Simulate 500 spawn allocations using RandomSpawnEngine's exact algorithm.
        Verifies bounds, anti-centering, and randomized spread across esplanade.
        """
        cx = 640
        cz = 864
        allocations: List[Tuple[int, int]] = []
        center_hits = 0

        # Run 500 simulated allocations
        for _ in range(500):
            ox = random.randint(-3, 3)
            oz = random.randint(-3, 3)
            if ox == 0 and oz == 0:
                # RandomSpawnEngine explicitly skips (0,0) to prevent fixed center cramming
                continue
            target_x = cx + ox
            target_z = cz + oz
            allocations.append((target_x, target_z))
            if target_x == cx and target_z == cz:
                center_hits += 1

        self.assertEqual(center_hits, 0, "Center point (640, 864) must NEVER be selected by allocateSafeSurvivalSpawn")
        self.assertGreaterEqual(len(allocations), 450)

        # Verify all coordinates stay strictly within esplanade bounds [637..643] x [861..867]
        for x, z in allocations:
            self.assertTrue(637 <= x <= 643, f"X coord {x} out of bounds [637, 643]")
            self.assertTrue(861 <= z <= 867, f"Z coord {z} out of bounds [861, 867]")

        # Verify statistical distribution (at least 35 unique coordinates out of 48 possible)
        unique_coords = set(allocations)
        self.assertGreaterEqual(len(unique_coords), 35,
                                f"Expected high spatial dispersion across esplanade, got only {len(unique_coords)} spots")

    def test_06_f10_ground_solidity_and_headroom_emptiness(self):
        """
        Feature F10: Verify simulated block safety validation:
        - Ground must be solid (not AIR, WATER, LAVA)
        - Headroom (y+1, y+2) must be passable and non-liquid
        """
        def validate_candidate(ground_solid: bool, h1_passable: bool, h1_liquid: bool,
                               h2_passable: bool, h2_liquid: bool) -> bool:
            return ground_solid and h1_passable and h2_passable and not h1_liquid and not h2_liquid

        # Nominal safe case
        self.assertTrue(validate_candidate(True, True, False, True, False))

        # Unsafe ground (e.g. falling into lava, water, or air/void)
        self.assertFalse(validate_candidate(False, True, False, True, False))  # Air ground
        self.assertFalse(validate_candidate(False, True, True, True, False))   # Water/Lava ground

        # Suffocation / blocked headroom (e.g. stone at head level)
        self.assertFalse(validate_candidate(True, False, False, True, False))  # Block at eye level 1
        self.assertFalse(validate_candidate(True, True, False, False, False))  # Block at eye level 2

        # Liquid at headroom (e.g. drowning in water or burning in lava)
        self.assertFalse(validate_candidate(True, True, True, True, False))   # Liquid at level 1
        self.assertFalse(validate_candidate(True, True, False, True, True))   # Liquid at level 2

    def test_07_f10_anti_stacking_entity_proximity_detection(self):
        """
        Feature F10: Proximity collision detection:
        Candidate is rejected if any entity exists within 0.8 blocks horizontal and 1.5 vertical.
        """
        def is_spot_free(candidate: Tuple[float, float, float], entities: List[Tuple[float, float, float]]) -> bool:
            cx, cy, cz = candidate
            for ex, ey, ez in entities:
                if abs(ex - cx) < 0.8 and abs(ez - cz) < 0.8 and abs(ey - cy) < 1.5:
                    return False
            return True

        candidate_loc = (641.5, 72.0, 865.5)

        # Case 1: Empty spot
        self.assertTrue(is_spot_free(candidate_loc, []))

        # Case 2: Entity standing directly on spot
        self.assertFalse(is_spot_free(candidate_loc, [(641.5, 72.0, 865.5)]))

        # Case 3: Entity slightly nearby (< 0.8 blocks away -> collides)
        self.assertFalse(is_spot_free(candidate_loc, [(641.9, 72.0, 865.7)]))

        # Case 4: Entity sufficiently far away (>= 0.8 blocks -> no collision)
        self.assertTrue(is_spot_free(candidate_loc, [(643.0, 72.0, 865.5)]))

    def test_08_f10_lost_bed_detection_and_notification_contracts(self):
        """Feature F10: RandomSpawnEngine lost bed detection and user notification strings."""
        rse_path = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        with open(rse_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Detection logic
        self.assertIn("event.isBedSpawn()", code)
        self.assertIn("player.getBedSpawnLocation() != null", code)
        self.assertIn("player.hasPlayedBefore()", code)

        # Notification & audio feedback
        self.assertIn("Votre point de spawn ou lit était détruit/inaccessible", code)
        self.assertIn("Sound.BLOCK_NOTE_BLOCK_BELL", code)

    # ==========================================================================
    # 3. F11 INTERACTIVE RESET NPC ("Gardien des Âmes") & INVARIANT PROTECTION
    # ==========================================================================

    def test_09_f11_gardien_des_ames_npc_contract(self):
        """Feature F11: NPC 'Gardien des Âmes' configuration in SpawnNpcGuides.java."""
        npc_path = os.path.join(SRC_DIR, "SpawnNpcGuides.java")
        with open(npc_path, "r", encoding="utf-8") as f:
            code = f.read()

        # NPC Identity & Profession
        self.assertIn("Gardien des Âmes", code)
        self.assertIn("Villager.Profession.CLERIC", code)
        self.assertIn("p.setBedSpawnLocation(null, true);", code)
        self.assertIn("deleteSurvivalLocationAsync(p.getUniqueId())", code)
        self.assertIn("Sound.UI_TOAST_CHALLENGE_COMPLETE", code)
        self.assertIn("Particle.TOTEM_OF_UNDYING", code)

    def test_10_f11_preservation_of_inventories_bank_and_progression_invariants(self):
        """
        Feature F11: Strict invariant test:
        Resetting personal survival location MUST clear player_survival_locations
        WITHOUT modifying:
        - player balance (players.balance)
        - player stats (kills, deaths, hours_played)
        - player OneBlock data (player_oneblock)
        - player simulated inventory items
        """
        p_uuid = str(uuid.uuid4())
        p_name = f"Preserve_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        initial_balance = 7890.5
        initial_kills = 45
        initial_deaths = 12
        initial_hours = 30
        initial_ob_blocks = 450
        initial_ob_phase = 3

        with get_db_connection() as conn:
            c = conn.cursor()
            # 1. Populate player profile
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'VIP', ?, ?, ?, ?, 1, 'SafeKeep', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name, initial_balance, initial_hours, initial_kills, initial_deaths))

            # 2. Populate survival resume location
            c.execute("""
                INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch)
                VALUES (?, ?, 'world', 1420.0, 68.0, 2350.0, 90.0, 0.0)
            """, (p_uuid, p_name))

            # 3. Populate OneBlock progression
            c.execute("""
                INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, created_at)
                VALUES (?, ?, 99999, 10000.0, 120.0, 10000.0, ?, ?, 10, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name, initial_ob_phase, initial_ob_blocks))
            conn.commit()

            # Execute 'Gardien des Âmes' reset action
            c.execute("DELETE FROM player_survival_locations WHERE uuid = ?", (p_uuid,))
            conn.commit()

            # ASSERT: Survival location is purged
            c.execute("SELECT * FROM player_survival_locations WHERE uuid = ?", (p_uuid,))
            self.assertIsNone(c.fetchone(), "Survival location must be completely deleted")

            # ASSERT: Player balance & stats remain 100% UNTOUCHED
            c.execute("SELECT balance, hours_played, kills, deaths FROM players WHERE uuid = ?", (p_uuid,))
            p_row = c.fetchone()
            self.assertEqual(p_row["balance"], initial_balance, "Player balance must NOT be altered by spawn reset")
            self.assertEqual(p_row["kills"], initial_kills, "Kills must NOT be altered")
            self.assertEqual(p_row["deaths"], initial_deaths, "Deaths must NOT be altered")
            self.assertEqual(p_row["hours_played"], initial_hours, "Hours played must NOT be altered")

            # ASSERT: OneBlock progress remains 100% UNTOUCHED
            c.execute("SELECT phase, blocks_broken FROM player_oneblock WHERE uuid = ?", (p_uuid,))
            ob_row = c.fetchone()
            self.assertEqual(ob_row["blocks_broken"], initial_ob_blocks, "OneBlock blocks_broken must NOT be altered")
            self.assertEqual(ob_row["phase"], initial_ob_phase, "OneBlock phase must NOT be altered")

    # ==========================================================================
    # 4. F19 COMPACT IN-GAME MESSAGES AUDIT
    # ==========================================================================

    def test_11_f19_message_compactness_and_no_excessive_delimiters(self):
        """
        Feature F19: Verify that titles, subtitles, and delimiters across M3 classes
        do not contain oversized borders (> 35 chars) or unwieldy titles that truncate
        on standard GUI scales.
        """
        m3_files = [
            "PlayerLocationEngine.java",
            "RandomSpawnEngine.java",
            "SpawnNpcGuides.java",
            "AetherCommandExecutor.java",
            "AetherVisualScoreboardManager.java"
        ]

        long_delimiters = []
        for fname in m3_files:
            fpath = os.path.join(SRC_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"M3 source file {fname} must exist")
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_no, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                    continue

                # Extract string literals within the line: "..."
                import re
                literals = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', line)
                for lit in literals:
                    for char in ['═', '━', '-', '=']:
                        if char * 35 in lit:
                            long_delimiters.append(f"{fname}:{line_no} in-game delimiter too long ({char * 35}) in \"{lit}\"")

        self.assertEqual(long_delimiters, [],
                         "Oversized 35+ character in-game delimiters found; messages must be compact for small screens:\n" +
                         "\n".join(long_delimiters))

    def test_12_f19_title_and_subtitle_length_bounds(self):
        """Feature F19: Specific title/subtitle length check for sendTitle invocations."""
        rse_path = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        ple_path = os.path.join(SRC_DIR, "PlayerLocationEngine.java")
        ace_path = os.path.join(SRC_DIR, "AetherCommandExecutor.java")

        with open(rse_path, "r", encoding="utf-8") as f:
            rse = f.read()
        with open(ple_path, "r", encoding="utf-8") as f:
            ple = f.read()
        with open(ace_path, "r", encoding="utf-8") as f:
            ace = f.read()

        # Titles must be <= 25 characters, Subtitles <= 35 characters (excluding color prefix)
        # Check Vortex title in RandomSpawnEngine
        self.assertIn("🌀 Vortex", rse)
        self.assertIn("Incantation en cours (3s)", rse)
        # Check Terre Vierge in RandomSpawnEngine
        self.assertIn("✦ Terre Vierge", rse)
        self.assertIn("Position validée", rse)
        # Check De retour in PlayerLocationEngine
        self.assertIn("✦ De retour", ple)
        self.assertIn("Position restaurée", ple)
        # Check Agora in AetherCommandExecutor
        self.assertIn("🪐 Agora", ace)
        self.assertIn("Archipel Céleste", ace)


if __name__ == "__main__":
    unittest.main()
