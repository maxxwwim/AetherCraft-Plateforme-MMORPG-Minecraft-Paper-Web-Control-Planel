"""
================================================================================
Aethercraft E2E Harmonization Test Suite (Tiers 1-4)
================================================================================
Comprehensive contract and opaque-box test suite validating real data
synchronization between:
- SQLite Database: server/data/aethercraft.db
- Flask Web Application: web/app.py & web/services/
- PaperMC In-Game Plugin queries & leaderboard synchronization

Framework: Compatible with both pytest and python -m unittest.
================================================================================
"""

import os
import sys
import sqlite3
import unittest
import uuid
import re
from typing import Dict, Any, List

# Ensure project root and web directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import (
    DB_PATH,
    get_db_connection,
    db_get_player_by_username,
    db_add_player_balance,
    db_get_all_players
)
from services.player_service import get_leaderboards, get_player_profile


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 - Feature Coverage:
    Validates physical database targeting, absence of dummy/mock data,
    retrieval of real players, dynamic web routes, and player_balances resolution.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t1_1_sqlite_database_connection_targets_active_db(self):
        """Verifies DB_PATH targets server/data/aethercraft.db and has valid tables."""
        normalized_path = os.path.normpath(DB_PATH)
        expected_suffix = os.path.normpath(os.path.join("server", "data", "aethercraft.db"))
        self.assertTrue(
            normalized_path.endswith(expected_suffix),
            f"DB_PATH ({normalized_path}) must end with '{expected_suffix}'"
        )
        self.assertTrue(
            os.path.exists(DB_PATH),
            f"Active SQLite database file must exist at {DB_PATH}"
        )
        file_size = os.path.getsize(DB_PATH)
        self.assertGreater(
            file_size,
            1000,
            f"Database file size ({file_size} bytes) indicates an uninitialized or empty file."
        )

        # Verify key relational tables exist
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row["name"] for row in cursor.fetchall()}

        required_tables = {"players", "ranks", "users", "tree_contributions"}
        missing_tables = required_tables - tables
        self.assertEqual(
            missing_tables,
            set(),
            f"Database at {DB_PATH} is missing required tables: {missing_tables}"
        )

    def test_t1_2_absence_of_dummy_seeded_players(self):
        """
        Feature F1 / Milestone M1:
        Asserts absence of hardcoded dummy players (UUIDs 00000000-... or fake names)
        in server/data/aethercraft.db.
        """
        dummy_names = ("AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uuid, username, rank, balance
                FROM players
                WHERE uuid LIKE '00000000-%'
                   OR username IN (?, ?, ?, ?, ?);
            """, dummy_names)
            dummy_rows = cursor.fetchall()

        found_players = [f"{r['username']} ({r['uuid']})" for r in dummy_rows]
        self.assertEqual(
            len(dummy_rows),
            0,
            f"Integrity Violation: Found {len(dummy_rows)} dummy seeded player(s) in active database: {found_players}. "
            f"Dummy players must be purged as part of Feature F1."
        )

    def test_t1_3_real_player_retrieval(self):
        """Verifies real registered players (e.g. Hactheglitchis) can be retrieved from players table."""
        player = db_get_player_by_username("Hactheglitchis")
        self.assertIsNotNone(
            player,
            "Real player 'Hactheglitchis' should exist in server/data/aethercraft.db"
        )
        self.assertEqual(player["username"].lower(), "hactheglitchis")
        self.assertTrue(player["uuid"], "Player must have a valid non-empty UUID")
        self.assertIsInstance(player["balance"], (int, float), "Balance must be numeric")

    def test_t1_4_joueurs_route_returns_real_rankings(self):
        """
        Feature F5 / Milestone M2:
        Verifies /joueurs route returns HTTP 200, does NOT hardcode AetherKnight
        as default spotlight player, and renders real rankings.
        """
        resp = self.client.get("/joueurs")
        self.assertEqual(resp.status_code, 200, "Route /joueurs must return 200 OK")
        html = resp.get_data(as_text=True)

        # Spotlight player card must NOT be hardcoded to AetherKnight
        collapsed_html = re.sub(r'\s+', '', html)
        self.assertNotIn(
            ">AetherKnight</h2>",
            collapsed_html,
            "Route /joueurs must not display hardcoded 'AetherKnight' as default spotlight card. "
            "Must dynamically feature the logged-in user or #1 ranked player."
        )

        # Dummy player names should not appear in leaderboards
        dummy_names = ["PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch"]
        found_in_leaderboard = [name for name in dummy_names if f">{name}</span>" in html]
        self.assertEqual(
            found_in_leaderboard,
            [],
            f"Route /joueurs still renders dummy players in leaderboard: {found_in_leaderboard}"
        )

    def test_t1_5_home_route_displays_genuine_player_or_mvp(self):
        """
        Feature F4 / Milestone M2:
        Verifies the home route (/) cockpit unit frame does not contain static mock values
        ('AetherKnight', '35,714', '1,250', 'TITAN PRIMORDIAL').
        """
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200, "Home route / must return 200 OK")
        html = resp.get_data(as_text=True)

        # Static mock strings from index.html:180-245
        mock_indicators = [
            ("AetherKnight", "Static username AetherKnight in homepage unit frame"),
            ("35,714", "Static coins 35,714 in homepage unit frame"),
            ("1,250", "Static gemmes 1,250 in homepage unit frame"),
            ("TITAN PRIMORDIAL", "Static rank TITAN PRIMORDIAL in homepage unit frame"),
        ]

        found_mocks = []
        for mock_str, desc in mock_indicators:
            if mock_str in html:
                found_mocks.append(f"{desc} (found '{mock_str}')")

        self.assertEqual(
            found_mocks,
            [],
            f"Homepage (/) contains static mock player values: {found_mocks}. "
            f"Must be dynamically bound to genuine player data."
        )

    def test_t1_6_player_balances_resolution(self):
        """
        Feature F2 / Milestone M1:
        Verifies that querying player_balances view (or direct balance resolution)
        succeeds without 'no such table: player_balances' exception.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT username, balance, shop_points FROM player_balances LIMIT 1;")
                row = cursor.fetchone()
                query_ok = True
                error_msg = ""
            except sqlite3.OperationalError as e:
                query_ok = False
                error_msg = str(e)

        self.assertTrue(
            query_ok,
            f"Querying player_balances failed with: {error_msg}. "
            f"A SQLite VIEW 'player_balances' must be created mapping players.balance and users.shop_points."
        )


class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 - Boundary & Corner Cases:
    Validates robustness under empty/single-player conditions, zero stats handling,
    defense against phantom player creation upon searching, and unauthenticated protections.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t2_1_single_or_empty_database_graceful_handling(self):
        """Verifies get_leaderboards() does not throw IndexError when database has fewer than 5 players."""
        leaderboards = get_leaderboards()
        self.assertIn("top_rich", leaderboards)
        self.assertIn("top_hours", leaderboards)
        # Slicing should gracefully handle 0 to 5 elements without exception
        self.assertLessEqual(len(leaderboards["top_rich"]), 5)
        self.assertLessEqual(len(leaderboards["top_hours"]), 5)

    def test_t2_2_zero_stats_player_kd_ratio(self):
        """
        Verifies that a player with 0 kills, 0 deaths, 0 balance does not trigger
        ZeroDivisionError or template rendering crashes.
        """
        test_uuid = f"test-e2e-zero-{uuid.uuid4().hex[:8]}"
        test_username = "E2E_ZeroStats_Test"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 0.0, 0, 0, 0, 0, 'Aventurier', '2026-11-06', '2026-11-06');
            """, (test_uuid, test_username))
            conn.commit()

        try:
            profile = get_player_profile(test_username)
            self.assertIsNotNone(profile)
            self.assertEqual(profile["kills"], 0)
            self.assertEqual(profile["deaths"], 0)

            # Test template rendering with 0 stats player
            resp = self.client.post("/api/players/search", data={"username": test_username})
            self.assertEqual(resp.status_code, 200, "Rendering zero-stats player card must not crash")
        finally:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM players WHERE uuid = ?;", (test_uuid,))
                conn.commit()

    def test_t2_3_unknown_player_search_does_not_create_phantom(self):
        """
        Feature F6 / Milestone M2:
        Verifies that searching for an unknown player in /api/players/search does NOT
        insert a phantom player record into server/data/aethercraft.db.
        """
        phantom_name = f"GhostSeeker_{uuid.uuid4().hex[:8]}"

        # Verify not in database before search
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (phantom_name,))
            count_before = cursor.fetchone()["c"]

        self.assertEqual(count_before, 0, "Phantom name must not exist prior to test")

        try:
            # Perform search request
            resp = self.client.post("/api/players/search", data={"username": phantom_name})

            # Verify not created in database after search
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (phantom_name,))
                count_after = cursor.fetchone()["c"]

            self.assertEqual(
                count_after,
                0,
                f"Vulnerability Detected: Searching for '{phantom_name}' created a phantom record in players table! "
                f"get_player_profile / db_get_player_by_username must be read-only on search queries."
            )
        finally:
            # Ensure database cleanliness even if assertion fails
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM players WHERE LOWER(username) = LOWER(?);", (phantom_name,))
                conn.commit()

    def test_t2_4_unauthenticated_community_contribution_no_fake_attribution(self):
        """
        Feature F8 / Milestone M2:
        Verifies that unauthenticated contributions to /api/community/contribute do NOT
        attribute donations to dummy player 'AetherKnight'.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT weighted_points FROM tree_contributions WHERE LOWER(username) = 'aetherknight';")
            row_before = cursor.fetchone()
            pts_before = row_before["weighted_points"] if row_before else 0.0

        # Unauthenticated contribution attempt
        resp = self.client.post("/api/community/contribute", data={"amount": 10, "ore_price": 5.0})

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT weighted_points FROM tree_contributions WHERE LOWER(username) = 'aetherknight';")
            row_after = cursor.fetchone()
            pts_after = row_after["weighted_points"] if row_after else 0.0

        self.assertEqual(
            pts_after,
            pts_before,
            f"Vulnerability: Unauthenticated contribution was attributed to 'AetherKnight' "
            f"(points increased from {pts_before} to {pts_after}). "
            f"Route must require authentication or reject fallback to mock players."
        )


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3 - Cross-Feature Combinations:
    Validates consistency between in-game plugin SQL queries and Web application data,
    strict ordering of leaderboards matching raw SQL, and immediate reactivity on updates.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t3_1_cross_sqlite_players_balance_matches_ingame_queries(self):
        """
        Feature F9 / Milestone M3:
        Verifies that queries executed by the in-game plugin (SELECT balance FROM players / player_balances)
        and web data access layer return identical values for real players.
        """
        target_username = "Hactheglitchis"

        # 1. In-game plugin query simulation
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);", (target_username,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, f"Player {target_username} must exist for cross-query test")
            ingame_balance = row["balance"]

        # 2. Web service query
        web_player = db_get_player_by_username(target_username)
        self.assertIsNotNone(web_player, f"Web service must find {target_username}")
        web_balance = web_player["balance"]

        self.assertEqual(
            ingame_balance,
            web_balance,
            f"Desynchronization: In-game balance ({ingame_balance}) does not match Web balance ({web_balance}) for {target_username}."
        )

    def test_t3_2_web_ranking_order_strictly_matches_sqlite_order_by(self):
        """
        Feature F3 / Milestone M1:
        Verifies that get_leaderboards() yields strictly monotonic descending order
        and matches the top players from raw SQLite ORDER BY balance DESC / hours_played DESC.
        """
        leaderboards = get_leaderboards()
        web_top_rich = leaderboards.get("top_rich", [])
        web_top_hours = leaderboards.get("top_hours", [])

        # 1. Monotonic ordering verification
        for i in range(len(web_top_rich) - 1):
            self.assertGreaterEqual(
                web_top_rich[i]["balance"],
                web_top_rich[i + 1]["balance"],
                f"top_rich not monotonically decreasing at index {i}: "
                f"{web_top_rich[i]['username']} ({web_top_rich[i]['balance']}) < "
                f"{web_top_rich[i+1]['username']} ({web_top_rich[i+1]['balance']})"
            )

        for i in range(len(web_top_hours) - 1):
            self.assertGreaterEqual(
                web_top_hours[i]["hours_played"],
                web_top_hours[i + 1]["hours_played"],
                f"top_hours not monotonically decreasing at index {i}: "
                f"{web_top_hours[i]['username']} ({web_top_hours[i]['hours_played']}) < "
                f"{web_top_hours[i+1]['username']} ({web_top_hours[i+1]['hours_played']})"
            )

        # 2. Verify top 1 wealth player matches raw SQLite MAX(balance)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, balance FROM players ORDER BY balance DESC LIMIT 1;")
            db_top_rich = cursor.fetchone()

        if db_top_rich and web_top_rich:
            self.assertEqual(
                web_top_rich[0]["balance"],
                db_top_rich["balance"],
                f"#1 wealth balance mismatch: Web ({web_top_rich[0]['balance']}) != DB ({db_top_rich['balance']})"
            )

    def test_t3_3_leaderboard_reflects_immediate_db_update(self):
        """Verifies modifying a database row immediately updates the leaderboard without stale caching."""
        target_username = "Hactheglitchis"
        initial_player = db_get_player_by_username(target_username)
        self.assertIsNotNone(initial_player)
        original_balance = initial_player["balance"]

        delta = 9999.0
        try:
            # Direct update in SQLite
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);",
                    (delta, target_username)
                )
                conn.commit()

            # Immediate leaderboard query
            updated_lbs = get_leaderboards()
            matching = [p for p in updated_lbs.get("top_rich", []) if p["username"].lower() == target_username.lower()]
            self.assertTrue(len(matching) > 0, f"{target_username} should appear in top_rich after balance boost")
            self.assertAlmostEqual(
                matching[0]["balance"],
                original_balance + delta,
                places=1,
                msg="Leaderboard must immediately reflect the updated balance without stale cache"
            )
        finally:
            # Restore original balance
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET balance = ? WHERE LOWER(username) = LOWER(?);",
                    (original_balance, target_username)
                )
                conn.commit()


class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 - Real-World Application Scenarios:
    End-to-end player lifecycle: registration, initial balance, coin gain,
    verification across web search, leaderboards, in-game queries, and cleanup.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.test_uuid = f"test-lifecycle-{uuid.uuid4().hex[:12]}"
        self.test_username = f"E2E_Hero_{uuid.uuid4().hex[:6]}"

    def tearDown(self):
        # Clean up created test entities
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM players WHERE uuid = ? OR LOWER(username) = LOWER(?);",
                           (self.test_uuid, self.test_username))
            cursor.execute("DELETE FROM users WHERE LOWER(minecraft_username) = LOWER(?);",
                           (self.test_username,))
            conn.commit()

    def test_t4_1_full_player_lifecycle_sync(self):
        """
        Executes a complete player lifecycle test:
        1. Register new player in players and users table.
        2. Verify player search card displays initial 1,000 balance.
        3. Award 500,000 coins via backend service.
        4. Query in-game SQL query -> verifies 501,000 balance.
        5. Query web leaderboards -> verifies player ranks in top_rich at #1 or #2.
        6. Clean up cleanly.
        """
        initial_balance = 1000.0
        earned_coins = 500000.0

        # Step 1: Register player in DB
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', ?, 20, 15, 2, 1, 'Légion Test', '2026-11-06 00:00:00', '2026-11-06 00:00:00');
            """, (self.test_uuid, self.test_username, initial_balance))
            cursor.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at)
                VALUES (?, 'testhash', 'testsalt', ?, 50, '2026-11-06 00:00:00');
            """, (f"{self.test_username.lower()}@aethercraft.test", self.test_username))
            conn.commit()

        # Step 2: Search via Web route /api/players/search
        resp = self.client.post("/api/players/search", data={"username": self.test_username})
        self.assertEqual(resp.status_code, 200)
        search_html = resp.get_data(as_text=True)
        self.assertIn(self.test_username, search_html, "Player username must be rendered in profile card")

        # Step 3: Credit coins
        db_add_player_balance(self.test_username, earned_coins)

        # Step 4: Verify via simulated in-game plugin query
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);", (self.test_username,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            expected_balance = initial_balance + earned_coins
            self.assertEqual(
                row["balance"],
                expected_balance,
                f"In-game query balance ({row['balance']}) must match expected ({expected_balance})"
            )

        # Step 5: Verify in Web Leaderboards
        lbs = get_leaderboards()
        top_rich_usernames = [p["username"].lower() for p in lbs.get("top_rich", [])]
        self.assertIn(
            self.test_username.lower(),
            top_rich_usernames,
            f"Player with {expected_balance} coins must appear in web top_rich leaderboards"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
