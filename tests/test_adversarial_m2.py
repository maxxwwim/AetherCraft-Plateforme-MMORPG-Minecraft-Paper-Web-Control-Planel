"""
================================================================================
Milestone M2 Adversarial Challenge Test Suite
================================================================================
Empirical challenge tests targeting Milestone M2:
Flask Web Application Harmonization.
Validates:
- Edge cases on /joueurs (?u=nonexistent, empty db, 1 player, extreme stats)
- Attack vectors on /api/players/search (SQLi, case variations, phantom row prevention)
- Security & attribution on /api/community/contribute (auth protection, user attribution)
- Dynamic homepage unit frame integrity & zero mocks
================================================================================
"""

import os
import sys
import uuid
import sqlite3
import unittest
from typing import Dict, Any, List

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
    db_get_leaderboards,
    db_get_top_player
)
from services.player_service import get_player_profile, get_leaderboards


class TestM2AdversarialJoueursRoute(unittest.TestCase):
    """Stress tests and boundary checks for /joueurs route."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_joueurs_query_param_nonexistent_player(self):
        """Requesting /joueurs?u=nonexistent_player_123 must return 200 without crashing."""
        resp = self.client.get("/joueurs?u=nonexistent_player_123")
        self.assertEqual(resp.status_code, 200, "Should return HTTP 200")
        html = resp.get_data(as_text=True)
        self.assertIn("PANTHÉON DES AVENTURIERS", html)
        self.assertIn("lb-panel-rich", html)
        self.assertIn("lb-panel-hours", html)
        self.assertIn("lb-panel-kills", html)

    def test_joueurs_query_param_does_not_insert_phantom_row(self):
        """Querying /joueurs with nonexistent username query parameters must not insert phantom rows."""
        phantom_pseudo = f"PhantomParam_{uuid.uuid4().hex[:8]}"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (phantom_pseudo,))
            count_pre = cursor.fetchone()["c"]

        self.assertEqual(count_pre, 0)

        # GET request with multiple query param variations
        self.client.get(f"/joueurs?u={phantom_pseudo}")
        self.client.get(f"/joueurs?username={phantom_pseudo}")
        self.client.get(f"/joueurs?player={phantom_pseudo}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (phantom_pseudo,))
            count_post = cursor.fetchone()["c"]

        self.assertEqual(count_post, 0, f"Query params on /joueurs must never create phantom player rows!")

    def test_joueurs_tab_switching_structure_intact(self):
        """Verifies that all 3 tabs (Fortune, Temps de jeu, Frags/Kills) are rendered in HTML."""
        resp = self.client.get("/joueurs")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('id="lb-panel-rich"', html)
        self.assertIn('id="lb-panel-hours"', html)
        self.assertIn('id="lb-panel-kills"', html)
        self.assertIn("switchLbTab('rich')", html)
        self.assertIn("switchLbTab('hours')", html)
        self.assertIn("switchLbTab('kills')", html)

    def test_joueurs_extreme_values_handling(self):
        """Insert a player with extreme stats: 0 kills, 0 deaths, 1,000,000,000 balance and verify rendering."""
        extreme_uuid = f"adv-ext-{uuid.uuid4().hex[:8]}"
        extreme_name = f"AdvExt_{uuid.uuid4().hex[:6]}"
        extreme_balance = 1_000_000_000.0

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'TITAN', ?, 9999, 0, 0, 1, 'Légende', '2026-01-01', '2026-11-06');
            """, (extreme_uuid, extreme_name, extreme_balance))
            conn.commit()

        try:
            resp = self.client.get("/joueurs")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(extreme_name, html, "Extreme player should appear on leaderboard")
            # Number formatting check: 1,000,000,000 -> 1 000 000 000
            self.assertIn("1 000 000 000", html)
        finally:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM players WHERE uuid = ?;", (extreme_uuid,))
                conn.commit()

    def test_joueurs_with_only_one_player(self):
        """Verifies /joueurs route handles a database with exactly 1 player cleanly without slicing IndexError."""
        # Create isolated temporary in-memory or file DB
        import tempfile
        temp_dir = tempfile.mkdtemp()
        temp_db = os.path.join(temp_dir, "test_single.db")

        # Copy schema from active DB
        with get_db_connection() as src_conn:
            schema_dump = "".join(src_conn.iterdump())

        conn = sqlite3.connect(temp_db)
        conn.executescript(schema_dump)
        # Delete all players and add only 1
        conn.execute("DELETE FROM players;")
        conn.execute("""
            INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
            VALUES ('solo-uuid-001', 'SoloPlayer', 'VIP', 500.0, 10, 5, 2, 0, 'Solo', '2026-01-01', '2026-11-06');
        """)
        conn.commit()
        conn.close()

        # Monkeypatch DB_PATH in database service
        import services.database as db_mod
        original_path = db_mod.DB_PATH
        try:
            db_mod.DB_PATH = temp_db
            lbs = db_get_leaderboards(5)
            self.assertEqual(len(lbs["top_rich"]), 1)
            self.assertEqual(lbs["top_rich"][0]["username"], "SoloPlayer")

            # Route test with 1 player
            resp = self.client.get("/joueurs")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn("SoloPlayer", html)
        finally:
            db_mod.DB_PATH = original_path
            try:
                os.remove(temp_db)
                os.rmdir(temp_dir)
            except OSError:
                pass

    def test_joueurs_with_empty_players_table(self):
        """Verifies /joueurs route does not throw IndexError or crash when players table is completely empty."""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        temp_db = os.path.join(temp_dir, "test_empty.db")

        with get_db_connection() as src_conn:
            schema_dump = "".join(src_conn.iterdump())

        conn = sqlite3.connect(temp_db)
        conn.executescript(schema_dump)
        conn.execute("DELETE FROM players;")
        conn.commit()
        conn.close()

        import services.database as db_mod
        original_path = db_mod.DB_PATH
        try:
            db_mod.DB_PATH = temp_db
            lbs = db_get_leaderboards(5)
            self.assertEqual(len(lbs["top_rich"]), 0)
            self.assertEqual(len(lbs["top_hours"]), 0)
            self.assertEqual(len(lbs["top_kills"]), 0)

            # Route test with 0 players
            resp = self.client.get("/joueurs")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn("Aucun profil actif", html)
            self.assertIn("Aucun joueur classé pour le moment", html)
        finally:
            db_mod.DB_PATH = original_path
            try:
                os.remove(temp_db)
                os.rmdir(temp_dir)
            except OSError:
                pass


class TestM2AdversarialPlayerSearch(unittest.TestCase):
    """Stress and security tests for player search endpoint."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_search_nonexistent_player_returns_404_card_and_no_db_pollution(self):
        """Searching nonexistent player must display 'Joueur introuvable' and insert 0 rows."""
        fake_name = f"GhostSearch_{uuid.uuid4().hex[:10]}"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            players_before = cursor.fetchone()["c"]

        resp = self.client.post("/api/players/search", data={"username": fake_name})
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Joueur introuvable", html)
        self.assertIn("Aucun joueur enregistré sous ce pseudo", html)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            players_after = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (fake_name,))
            fake_count = cursor.fetchone()["c"]

        self.assertEqual(players_after, players_before, "Total players count in DB must remain strictly invariant!")
        self.assertEqual(fake_count, 0, "No phantom row may be inserted for searched nonexistent player!")

    def test_search_case_variations(self):
        """Case variations like hactheglitchis vs Hactheglitchis vs HACTHEGLITCHIS must all resolve."""
        real_player = "Hactheglitchis"
        variations = [
            "hactheglitchis",
            "Hactheglitchis",
            "HACTHEGLITCHIS",
            "HaCtHeGlItChIs",
            "hACTHEGLITCHIS"
        ]

        for var in variations:
            resp = self.client.post("/api/players/search", data={"username": var})
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn("Hactheglitchis", html, f"Failed to resolve player with case variant '{var}'")
            self.assertNotIn("Joueur introuvable", html, f"Should not show introuvable for variant '{var}'")

    def test_search_sql_injection_resilience(self):
        """Battery of SQL injection strings must neither crash, return unauthorized data, nor pollute SQLite."""
        sqli_payloads = [
            "' OR '1'='1",
            "' OR 1=1; --",
            "admin'--",
            '" OR ""="',
            "'; DROP TABLE players; --",
            "' UNION SELECT null, 'hacked', 'TITAN', 99999999, 100, 100, 0, 1, 'HACK', 'now', 'now' --",
            "Robert'); DROP TABLE players;--",
            "' AND 1=0 UNION ALL SELECT 1,2,3,4,5,6,7,8,9,10,11 --",
            "1' or '1' = '1",
            "<script>alert('xss')</script>"
        ]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            count_pre = cursor.fetchone()["c"]

        for payload in sqli_payloads:
            resp = self.client.post("/api/players/search", data={"username": payload})
            self.assertEqual(resp.status_code, 200, f"Payload '{payload}' crashed with code {resp.status_code}")
            html = resp.get_data(as_text=True)
            # Must return Joueur introuvable and must NOT return another player's data
            self.assertIn("Joueur introuvable", html, f"Payload '{payload}' should not match any user")

        # Verify database integrity was not breached
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            count_post = cursor.fetchone()["c"]

        self.assertEqual(count_post, count_pre, "Database player count must not be altered by SQL injection attempts!")

    def test_search_repeated_read_operations_purity(self):
        """Executing 30 randomized search queries must not insert a single byte or row into DB."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            init_players = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) AS c FROM users;")
            init_users = cursor.fetchone()["c"]

        for i in range(30):
            test_query = f"Probe_{uuid.uuid4().hex[:12]}"
            self.client.post("/api/players/search", data={"username": test_query})

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players;")
            final_players = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) AS c FROM users;")
            final_users = cursor.fetchone()["c"]

        self.assertEqual(final_players, init_players)
        self.assertEqual(final_users, init_users)


class TestM2AdversarialCommunityContribute(unittest.TestCase):
    """Stress and security tests for /api/community/contribute."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_unauthenticated_request_rejected_without_mutation(self):
        """Unauthenticated contribution must be rejected (302/401) and not mutate tree_contributions."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c, COALESCE(SUM(weighted_points), 0) AS s FROM tree_contributions;")
            row_pre = cursor.fetchone()
            count_pre = row_pre["c"]
            points_pre = row_pre["s"]

        resp = self.client.post("/api/community/contribute", data={"amount": 100, "ore_price": 50.0})
        # @login_required returns 302 redirect to /login
        self.assertIn(resp.status_code, (302, 401), f"Expected 302 or 401, got {resp.status_code}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c, COALESCE(SUM(weighted_points), 0) AS s FROM tree_contributions;")
            row_post = cursor.fetchone()
            count_post = row_post["c"]
            points_post = row_post["s"]

        self.assertEqual(count_post, count_pre, "tree_contributions row count must not change on unauthenticated post")
        self.assertEqual(points_post, points_pre, "tree_contributions total points must not change on unauthenticated post")

    def test_unauthenticated_never_credits_aetherknight(self):
        """Even with explicit username='AetherKnight' in form data, unauthenticated request must be rejected."""
        resp = self.client.post("/api/community/contribute", data={
            "username": "AetherKnight",
            "amount": 50,
            "ore_price": 10.0
        })
        self.assertIn(resp.status_code, (302, 401))

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM tree_contributions WHERE LOWER(username) = 'aetherknight';")
            count = cursor.fetchone()["c"]

        self.assertEqual(count, 0, "AetherKnight must never be present in tree_contributions!")

    def test_authenticated_request_attributes_to_session_user(self):
        """Authenticated contribution must attribute solely to the logged-in user."""
        test_uname = f"ContribHero_{uuid.uuid4().hex[:6]}"
        test_email = f"{test_uname.lower()}@test.local"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at)
                VALUES (?, 'hash', 'salt', ?, 100, 0, '2026-11-06 00:00:00');
            """, (test_email, test_uname))
            user_id = cursor.lastrowid
            conn.commit()

        try:
            with self.client.session_transaction() as sess:
                sess["user_id"] = user_id

            resp = self.client.post("/api/community/contribute", data={"amount": 25, "ore_price": 10.0})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "ok")

            # Check attribution in tree_contributions
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username, raw_units, weighted_points FROM tree_contributions WHERE LOWER(username) = LOWER(?);", (test_uname,))
                contrib = cursor.fetchone()
                self.assertIsNotNone(contrib, f"Contribution should be attributed to {test_uname}")
                self.assertEqual(contrib["raw_units"], 25)
        finally:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tree_contributions WHERE LOWER(username) = LOWER(?);", (test_uname,))
                cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
                conn.commit()


class TestM2AdversarialHomepageIntegrity(unittest.TestCase):
    """Stress tests on homepage (/) dynamic unit frame and mock eradication."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_homepage_absence_of_all_mock_indicators(self):
        """Homepage must be 100% clean of all static dummy strings."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        dummies = ["AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "TITAN PRIMORDIAL", "35,714", "1,250"]
        found = [d for d in dummies if d in html]
        self.assertEqual(found, [], f"Homepage still contains mock dummy strings: {found}")

    def test_homepage_authenticated_user_display(self):
        """When user is authenticated, unit frame displays current_user.minecraft_username."""
        test_uname = f"HomeHero_{uuid.uuid4().hex[:6]}"
        test_email = f"{test_uname.lower()}@test.local"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at)
                VALUES (?, 'hash', 'salt', ?, 150, 0, '2026-11-06 00:00:00');
            """, (test_email, test_uname))
            user_id = cursor.lastrowid
            conn.commit()

        try:
            with self.client.session_transaction() as sess:
                sess["user_id"] = user_id

            resp = self.client.get("/")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(test_uname, html, "Logged-in username must be featured in homepage unit frame")
        finally:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
                conn.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
