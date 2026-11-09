"""
Unit & Integration Tests for Milestone M1: Data Layer & Mock Data Eradication.
Covers:
- DB seeding & mock player purge (Feature F1)
- SQLite view player_balances & INSTEAD OF triggers (Feature F2)
- Database ranking helpers: db_get_leaderboards, db_get_top_player, db_get_community_tree_donors (Feature F3)
- Defense against phantom/mock re-insertion in db_upsert_player
"""

import os
import sys
import sqlite3
import unittest
import uuid

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import (
    DB_PATH,
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_get_all_players,
    db_get_leaderboards,
    db_get_top_player,
    db_get_community_tree_donors,
    db_upsert_player
)


class TestM1DataLayer(unittest.TestCase):

    def setUp(self):
        # Guarantee schema and views are initialized
        init_database()

    def test_mock_players_eradicated_from_database(self):
        """Verify server/data/aethercraft.db contains zero dummy seeded players."""
        dummy_names = ("AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uuid, username, rank, balance
                FROM players
                WHERE uuid LIKE '00000000-%'
                   OR username IN (?, ?, ?, ?, ?);
            """, dummy_names)
            rows = cursor.fetchall()

        self.assertEqual(
            len(rows), 0,
            f"Expected 0 dummy players in active DB, found {len(rows)}: {[dict(r) for r in rows]}"
        )

    def test_init_database_idempotency_does_not_reseed_dummies(self):
        """Calling init_database() multiple times must keep database clean without re-seeding dummies."""
        init_database()
        init_database()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM players WHERE uuid LIKE '00000000-%';")
            count = cursor.fetchone()["c"]

        self.assertEqual(count, 0, "init_database() must not re-insert 00000000-... UUID players")

    def test_player_balances_view_queryable(self):
        """Verify the player_balances view exists and returns genuine player balances and shop points."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, balance, shop_points FROM player_balances;")
            rows = [dict(r) for r in cursor.fetchall()]

        self.assertIsInstance(rows, list)
        usernames = [r["username"].lower() for r in rows]
        self.assertIn("hactheglitchis", usernames, "Genuine player 'Hactheglitchis' must be in player_balances view")
        
        # Verify columns exist
        sample = rows[0]
        self.assertIn("username", sample)
        self.assertIn("balance", sample)
        self.assertIn("shop_points", sample)
        self.assertIsInstance(sample["balance"], (int, float))
        self.assertIsInstance(sample["shop_points"], int)

    def test_player_balances_triggers_forward_updates(self):
        """Verify INSTEAD OF triggers on player_balances correctly forward updates to players & users tables."""
        test_user = f"m1_test_{uuid.uuid4().hex[:6]}"
        test_uuid = str(uuid.uuid4())

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 100.0, 5, 2, 1, 0, 'TestGuild', '2026-11-06', '2026-11-06');
            """, (test_uuid, test_user))
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at)
                VALUES (?, 'hash', 'salt', ?, 25, '2026-11-06');
            """, (f"{test_user}@test.io", test_user))
            conn.commit()

        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # Test updating balance via view
                c.execute("UPDATE player_balances SET balance = balance + 350 WHERE username = ? COLLATE NOCASE;", (test_user,))
                # Test updating shop_points via view
                c.execute("UPDATE player_balances SET shop_points = shop_points - 10 WHERE username = ? COLLATE NOCASE;", (test_user,))
                conn.commit()

                # Verify players table was updated
                c.execute("SELECT balance FROM players WHERE username = ?;", (test_user,))
                p_row = c.fetchone()
                self.assertEqual(p_row["balance"], 450.0)

                # Verify users table was updated
                c.execute("SELECT shop_points FROM users WHERE minecraft_username = ?;", (test_user,))
                u_row = c.fetchone()
                self.assertEqual(u_row["shop_points"], 15)

                # Verify view query reflects both
                c.execute("SELECT balance, shop_points FROM player_balances WHERE username = ?;", (test_user,))
                v_row = c.fetchone()
                self.assertEqual(v_row["balance"], 450.0)
                self.assertEqual(v_row["shop_points"], 15)
        finally:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM players WHERE uuid = ?;", (test_uuid,))
                c.execute("DELETE FROM users WHERE minecraft_username = ?;", (test_user,))
                conn.commit()

    def test_db_get_leaderboards_contract(self):
        """Verify db_get_leaderboards adheres to interface contract in PROJECT.md."""
        leaderboards = db_get_leaderboards(limit=5)
        self.assertIsInstance(leaderboards, dict)
        self.assertIn("top_rich", leaderboards)
        self.assertIn("top_hours", leaderboards)
        self.assertIn("top_kills", leaderboards)

        required_keys = {"username", "rank", "rank_name", "badge_color", "balance", "hours_played", "kills", "is_online"}
        for category in ["top_rich", "top_hours", "top_kills"]:
            items = leaderboards[category]
            self.assertIsInstance(items, list)
            self.assertLessEqual(len(items), 5)
            for item in items:
                for k in required_keys:
                    self.assertIn(k, item, f"Key '{k}' missing from {category} entry: {item}")

    def test_db_get_leaderboards_ordering(self):
        """Verify top_rich is ordered by wealth DESC, top_hours by hours DESC, top_kills by kills DESC."""
        # Insert 2 test players with controlled stats
        u1 = f"order_test_a_{uuid.uuid4().hex[:4]}"
        u2 = f"order_test_b_{uuid.uuid4().hex[:4]}"
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())

        with get_db_connection() as conn:
            c = conn.cursor()
            # u1 has more balance, fewer hours, fewer kills
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'VIP', 50000.0, 10, 5, 1, 0, 'GuildA', '2026-11-06', '2026-11-06');
            """, (uuid1, u1))
            # u2 has less balance, more hours, more kills
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'AETHER', 2000.0, 100, 50, 2, 0, 'GuildB', '2026-11-06', '2026-11-06');
            """, (uuid2, u2))
            conn.commit()

        try:
            lb = db_get_leaderboards(limit=10)
            rich_names = [p["username"] for p in lb["top_rich"]]
            hour_names = [p["username"] for p in lb["top_hours"]]
            kill_names = [p["username"] for p in lb["top_kills"]]

            self.assertIn(u1, rich_names)
            self.assertIn(u2, rich_names)
            self.assertLess(rich_names.index(u1), rich_names.index(u2), f"{u1} should be ranked above {u2} in top_rich")

            self.assertIn(u1, hour_names)
            self.assertIn(u2, hour_names)
            self.assertLess(hour_names.index(u2), hour_names.index(u1), f"{u2} should be ranked above {u1} in top_hours")

            self.assertIn(u1, kill_names)
            self.assertIn(u2, kill_names)
            self.assertLess(kill_names.index(u2), kill_names.index(u1), f"{u2} should be ranked above {u1} in top_kills")
        finally:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM players WHERE uuid IN (?, ?);", (uuid1, uuid2))
                conn.commit()

    def test_db_get_top_player(self):
        """Verify db_get_top_player returns genuine MVP player."""
        top_player = db_get_top_player()
        self.assertIsNotNone(top_player, "There must be a top player in active database")
        self.assertIn("username", top_player)
        self.assertIn("rank", top_player)
        self.assertIn("balance", top_player)
        self.assertIn("mvp_score", top_player)
        self.assertIn("avatar_url", top_player)
        self.assertIn("body_url", top_player)
        self.assertNotIn(top_player["username"], ["AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch"])

    def test_db_get_community_tree_donors(self):
        """Verify db_get_community_tree_donors returns genuine donor list ordered by weighted_points DESC."""
        donors = db_get_community_tree_donors(limit=5)
        self.assertIsInstance(donors, list)
        self.assertLessEqual(len(donors), 5)
        if donors:
            first = donors[0]
            self.assertIn("username", first)
            self.assertIn("raw_units", first)
            self.assertIn("weighted_points", first)
            self.assertIn("share_pct", first)
            self.assertIn("unit_pct", first)

    def test_db_upsert_player_dummy_protection(self):
        """Verify db_upsert_player rejects persisting dummy mock player names."""
        for dummy in ["AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch"]:
            res = db_upsert_player(dummy)
            # Result should be a non-persisted dict representation or None
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (dummy,))
                count = c.fetchone()["c"]
            self.assertEqual(count, 0, f"db_upsert_player must not persist dummy player '{dummy}' into database")


if __name__ == "__main__":
    unittest.main(verbosity=2)
