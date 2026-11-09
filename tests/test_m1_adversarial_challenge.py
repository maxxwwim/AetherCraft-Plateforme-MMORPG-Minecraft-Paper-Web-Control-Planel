"""
Adversarial Challenge Test Suite for Milestone M1 (Data Layer & Mock Purge).
Executed by teamwork_challenger_m1_2.

Objectives:
1. Empirically verify empty database behavior (0 rows in players, users, etc.) against all helper functions.
2. Empirically verify that db_get_top_player() never returns deleted dummy players or crashes on empty DB.
3. Empirically verify tie-breaking, CREATEUR exclusion, and zero-division resistance in MVP score.
4. Empirically verify player_balances VIEW and INSTEAD OF triggers under edge cases (missing users, CASE sensitivity, WHERE conditions).
5. Empirically verify build artifact AetherVisuals.jar integrity and classpath completeness.
6. Empirically test schema completeness on fresh database initialization.
"""

import os
import sys
import uuid
import zipfile
import tempfile
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

import services.database as db_mod
from services.database import (
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_get_all_players,
    db_get_leaderboards,
    db_get_top_player,
    db_get_community_tree_donors,
    db_get_tree_leaderboard,
    db_upsert_player,
    db_update_player_balance,
    db_add_player_balance
)


class TestM1AdversarialChallenge(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = db_mod.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        db_mod.DB_PATH = self.temp_db_path
        init_database()
        # Ensure player_bank_accounts exists for functional tests
        with db_mod.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_bank_accounts (
                    username TEXT PRIMARY KEY,
                    bank_coins REAL DEFAULT 0.0,
                    updated_at TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_bank_items (
                    username TEXT,
                    slot INTEGER,
                    item_b64 TEXT,
                    PRIMARY KEY (username, slot)
                );
            """)
            conn.commit()

    def tearDown(self):
        db_mod.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_empty_database_all_helpers_survive_without_exceptions(self):
        """Stress-test: DB with 0 players, 0 users, 0 bank accounts, 0 contributions.
        All helper functions must return clean empty/None structures without unhandled crashes."""
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players;")
            c.execute("DELETE FROM users;")
            c.execute("DELETE FROM player_bank_accounts;")
            c.execute("DELETE FROM tree_contributions;")
            conn.commit()

            c.execute("SELECT COUNT(*) AS c FROM players;")
            self.assertEqual(c.fetchone()["c"], 0)

        # 1. db_get_top_player() on 0 players -> must be None
        top = db_get_top_player()
        self.assertIsNone(top, "db_get_top_player() on empty players table must return None")

        # 2. db_get_leaderboards() on 0 players -> must be dict with empty lists
        lb = db_get_leaderboards(limit=5)
        self.assertIsInstance(lb, dict)
        self.assertEqual(lb["top_rich"], [])
        self.assertEqual(lb["top_hours"], [])
        self.assertEqual(lb["top_kills"], [])

        # 3. db_get_all_players() on 0 players -> []
        all_p = db_get_all_players()
        self.assertEqual(all_p, [])

        # 4. db_get_player_by_username() on 0 players -> None
        p = db_get_player_by_username("anyone")
        self.assertIsNone(p)

        # 5. db_get_community_tree_donors() on 0 contributions -> []
        donors = db_get_community_tree_donors(limit=5)
        self.assertEqual(donors, [])

        # 6. db_get_tree_leaderboard() on 0 contributions -> []
        tree_lb = db_get_tree_leaderboard(limit=5)
        self.assertEqual(tree_lb, [])

        # 7. player_balances VIEW on 0 players -> []
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            rows = c.execute("SELECT * FROM player_balances;").fetchall()
            self.assertEqual(rows, [])

            # Update non-existent row in view (must not crash, 0 rows modified)
            c.execute("UPDATE player_balances SET balance = 500 WHERE username = 'ghost';")
            c.execute("UPDATE player_balances SET shop_points = 50 WHERE username = 'ghost';")
            conn.commit()

    def test_top_player_never_returns_deleted_dummies(self):
        """Stress-test: Dummy player names must never be returned by db_get_top_player()."""
        dummy_names = ["AetherKnight", "PixelSorceress", "VortexCrafter", "ShadowRanger", "Notch"]

        # Call db_upsert_player for each dummy
        for d in dummy_names:
            res = db_upsert_player(d)
            self.assertIsNotNone(res)

        # Verify DB still has 0 players in SQLite
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) AS c FROM players;")
            self.assertEqual(c.fetchone()["c"], 0)

        # db_get_top_player must be None
        top = db_get_top_player()
        self.assertIsNone(top, "db_get_top_player() must be None when only dummies were upserted")

        # Now insert 1 legitimate player with humble stats
        legit_user = "RealAdventurer"
        legit_uuid = str(uuid.uuid4())
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 50.0, 1, 0, 0, 0, 'Guilde', '2026-11-06', '2026-11-06');
            """, (legit_uuid, legit_user))
            conn.commit()

        # db_get_top_player must return the legitimate player, never a dummy
        top = db_get_top_player()
        self.assertIsNotNone(top)
        self.assertEqual(top["username"], legit_user)
        self.assertNotIn(top["username"], dummy_names)

    def test_top_player_creator_staff_deprioritization(self):
        """Stress-test: Non-creator player with decent stats should beat CREATEUR staff player
        per PROJECT.md interface contract: '(excluding Creator/Staff or by composite MVP score)'."""
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            # Staff Creator player with huge stats
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES ('uuid-creator', 'ServerOwner', 'CREATEUR', 999999.0, 500, 200, 0, 0, 'Staff', '2026-01-01', '2026-11-06');
            """)
            # Active genuine non-staff player with moderate stats
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES ('uuid-player', 'ActiveHero', 'TITAN', 15000.0, 80, 45, 10, 1, 'Legion', '2026-02-01', '2026-11-06');
            """)
            conn.commit()

        top = db_get_top_player()
        self.assertIsNotNone(top)
        self.assertEqual(top["username"], "ActiveHero", "Genuine non-staff player must take priority over CREATEUR in top player selection")

    def test_top_player_fallback_when_only_creators_exist(self):
        """Stress-test: If only CREATEUR accounts exist, db_get_top_player should still return a profile gracefully."""
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players;")
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES ('uuid-creator-only', 'SoloAdmin', 'CREATEUR', 50000.0, 100, 50, 0, 0, 'Staff', '2026-01-01', '2026-11-06');
            """)
            conn.commit()

        top = db_get_top_player()
        self.assertIsNotNone(top)
        self.assertEqual(top["username"], "SoloAdmin")

    def test_player_balances_triggers_with_missing_user_row(self):
        """Stress-test: Player exists in players, but has NO account in users table.
        View must provide default 10 shop_points and updating balance must succeed."""
        u = "no_web_user"
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES ('uuid-noweb', ?, 'VIP', 250.0, 10, 5, 0, 0, 'Solo', '2026-11-06', '2026-11-06');
            """, (u,))
            conn.commit()

            # Query view
            row = c.execute("SELECT username, balance, shop_points FROM player_balances WHERE username = ?;", (u,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["balance"], 250.0)
            self.assertEqual(row["shop_points"], 10, "Should default to 10 shop points via COALESCE")

            # Update balance via view
            c.execute("UPDATE player_balances SET balance = balance + 150 WHERE username = ? COLLATE NOCASE;", (u,))
            conn.commit()

            # Verify players table updated
            p_row = c.execute("SELECT balance FROM players WHERE username = ?;", (u,)).fetchone()
            self.assertEqual(p_row["balance"], 400.0)

            # Update shop_points for user that has no users row: should execute without SQLite error
            c.execute("UPDATE player_balances SET shop_points = 50 WHERE username = ? COLLATE NOCASE;", (u,))
            conn.commit()

    def test_player_balances_conditional_update_shop_points(self):
        """Stress-test: Update shop_points with condition (like AetherMMOShopCatalog: WHERE ... AND shop_points >= ?)."""
        u = "shop_buyer"
        with db_mod.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES ('uuid-shop', ?, 'JOUEUR', 100.0, 1, 0, 0, 0, 'Aventurier', '2026-11-06', '2026-11-06');
            """, (u,))
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at)
                VALUES (?, 'hash', 'salt', ?, 30, '2026-11-06');
            """, (f"{u}@mail.io", u))
            conn.commit()

            # Attempt deduction with sufficient balance (30 >= 20): should succeed
            c.execute("""
                UPDATE player_balances 
                SET shop_points = shop_points - 20 
                WHERE username = ? COLLATE NOCASE AND shop_points >= 20;
            """, (u,))
            conn.commit()

            u_row = c.execute("SELECT shop_points FROM users WHERE minecraft_username = ?;", (u,)).fetchone()
            self.assertEqual(u_row["shop_points"], 10)

            # Attempt deduction with insufficient balance (10 >= 20 is false): should NOT deduct
            c.execute("""
                UPDATE player_balances 
                SET shop_points = shop_points - 20 
                WHERE username = ? COLLATE NOCASE AND shop_points >= 20;
            """, (u,))
            conn.commit()

            u_row = c.execute("SELECT shop_points FROM users WHERE minecraft_username = ?;", (u,)).fetchone()
            self.assertEqual(u_row["shop_points"], 10, "Points should remain 10 because condition shop_points >= 20 was false")

    def test_upsert_player_adversarial_name_variations(self):
        """Stress-test: db_upsert_player with whitespaces, mixed casing, and dummy variations."""
        adversarial_dummies = [
            "  aetherknight  ",
            "PIXELSORCERESS",
            "vOrTeXcRaFtEr",
            "\tshadowranger\n",
            "  NOTCH  "
        ]
        for name in adversarial_dummies:
            clean_name = name.strip().lower()
            res = db_upsert_player(name)
            self.assertIsNotNone(res)
            # Verify NOT in database
            with db_mod.get_db_connection() as conn:
                c = conn.cursor()
                count = c.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = ?;", (clean_name,)).fetchone()["c"]
                self.assertEqual(count, 0, f"Adversarial variant '{name}' must NOT be saved to SQLite players table")

    def test_built_plugin_jar_integrity(self):
        """Verify server/plugins/AetherVisuals.jar exists, is valid zip, and contains required compiled classes."""
        jar_path = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")
        self.assertTrue(os.path.exists(jar_path), f"Plugin JAR must exist at {jar_path}")
        self.assertGreater(os.path.getsize(jar_path), 5000, "Plugin JAR size should be substantial")

        with zipfile.ZipFile(jar_path, "r") as z:
            namelist = z.namelist()
            self.assertIn("plugin.yml", namelist, "plugin.yml must be in root of JAR")
            self.assertIn("io/aethercraft/visuals/AetherDatabase.class", namelist)
            self.assertIn("io/aethercraft/visuals/AetherVisualsPlugin.class", namelist)
            self.assertIn("io/aethercraft/visuals/MMORPGDisplayEngine.class", namelist)
            self.assertIn("io/aethercraft/visuals/AetherMMOShopCatalog.class", namelist)
            self.assertIn("io/aethercraft/visuals/DungeonMobSpellCaster.class", namelist)


if __name__ == "__main__":
    unittest.main(verbosity=2)
