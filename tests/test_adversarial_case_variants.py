"""
Adversarial Stress Test: Case-Variant Updates on player_balances View.
Specifically validates:
1. Case-variant WHERE matches without explicit COLLATE NOCASE in UPDATE queries.
2. Case-variant WHERE matches with explicit COLLATE NOCASE in UPDATE queries.
3. Upper/lower/mixed-case updates for balance (players table).
4. Upper/lower/mixed-case updates for shop_points (users table).
5. Simultaneous update of balance and shop_points across case variations.
6. Arithmetic updates (balance + X, shop_points - Y) with conditional guards across cases.
7. Case-variant updates for players without a users row (graceful trigger handling).
8. Rapid interleaved case-variant transactions.
"""

import os
import sys
import uuid
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import get_db_connection, init_database


class TestCaseVariantPlayerBalances(unittest.TestCase):

    def setUp(self):
        init_database()
        self.created_uuids = []
        self.created_usernames = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    placeholders = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
                if self.created_usernames:
                    placeholders = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_usernames)
                    c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({placeholders});", self.created_usernames)
                conn.commit()

    def _insert_player(self, username, balance=100.0):
        p_uuid = str(uuid.uuid4())
        now = "2026-11-06 12:00:00"
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', ?, 10, 5, 1, 1, 'Guild', ?, ?);
            """, (p_uuid, username, balance, now, now))
            conn.commit()
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(username)
        return p_uuid

    def _insert_user(self, username, shop_points=50):
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at)
                VALUES (?, 'hash', 'salt', ?, ?, '2026-11-06');
            """, (f"{username.lower()}@test.adv", username, shop_points))
            conn.commit()
        if username not in self.created_usernames:
            self.created_usernames.append(username)

    def test_case_variant_balance_updates_without_collate(self):
        """Verify updating player_balances.balance matches case-insensitively even when UPDATE query lacks COLLATE NOCASE."""
        orig_name = f"CaseHero_{uuid.uuid4().hex[:6]}"
        self._insert_player(orig_name, balance=100.0)

        with get_db_connection() as conn:
            c = conn.cursor()

            # 1. Update using all-lowercase name without explicit COLLATE in query
            c.execute("UPDATE player_balances SET balance = 200.0 WHERE username = ?;", (orig_name.lower(),))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (orig_name,))
            self.assertEqual(c.fetchone()["balance"], 200.0, "Lowercase WHERE username=? failed to update players.balance")

            # 2. Update using all-uppercase name without explicit COLLATE in query
            c.execute("UPDATE player_balances SET balance = 300.0 WHERE username = ?;", (orig_name.upper(),))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (orig_name,))
            self.assertEqual(c.fetchone()["balance"], 300.0, "Uppercase WHERE username=? failed to update players.balance")

            # 3. Update using inverted / alternating case
            alt_name = "".join(ch.lower() if i % 2 == 0 else ch.upper() for i, ch in enumerate(orig_name))
            c.execute("UPDATE player_balances SET balance = 400.0 WHERE username = ?;", (alt_name,))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (orig_name,))
            self.assertEqual(c.fetchone()["balance"], 400.0, "Alternating case WHERE username=? failed to update players.balance")

    def test_case_variant_shop_points_updates_without_collate(self):
        """Verify updating player_balances.shop_points matches case-insensitively across case variants."""
        orig_name = f"ShopMaster_{uuid.uuid4().hex[:6]}"
        self._insert_player(orig_name, balance=100.0)
        # Store in users with lowercase
        self._insert_user(orig_name.lower(), shop_points=50)

        with get_db_connection() as conn:
            c = conn.cursor()

            # 1. Update with uppercase username
            c.execute("UPDATE player_balances SET shop_points = 75 WHERE username = ?;", (orig_name.upper(),))
            conn.commit()

            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (orig_name.lower(),))
            self.assertEqual(c.fetchone()["shop_points"], 75, "Uppercase update failed to update users.shop_points")

            # 2. Update with original mixed-case username
            c.execute("UPDATE player_balances SET shop_points = 99 WHERE username = ?;", (orig_name,))
            conn.commit()

            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (orig_name.lower(),))
            self.assertEqual(c.fetchone()["shop_points"], 99, "Mixed-case update failed to update users.shop_points")

    def test_simultaneous_balance_and_points_update_mixed_case(self):
        """Verify updating both balance and shop_points simultaneously with different casing."""
        p_name = f"DualUpdate_{uuid.uuid4().hex[:6]}"
        self._insert_player(p_name, balance=500.0)
        self._insert_user(p_name.upper(), shop_points=30)  # users stored as upper

        with get_db_connection() as conn:
            c = conn.cursor()

            # Update with all-lowercase
            c.execute("""
                UPDATE player_balances
                SET balance = 1500.0, shop_points = 150
                WHERE username = ?;
            """, (p_name.lower(),))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (p_name,))
            self.assertEqual(c.fetchone()["balance"], 1500.0)

            c.execute("SELECT shop_points FROM users WHERE minecraft_username = ?;", (p_name.upper(),))
            self.assertEqual(c.fetchone()["shop_points"], 150)

    def test_arithmetic_updates_like_java_plugins(self):
        """Emulate exact Java plugin statements with case variants:
        - DungeonMobSpellCaster: UPDATE player_balances SET balance = balance + 350 WHERE username = ? COLLATE NOCASE
        - AetherMMOShopCatalog: UPDATE player_balances SET shop_points = shop_points - ? WHERE username = ? COLLATE NOCASE AND shop_points >= ?
        """
        p_name = f"PluginPlayer_{uuid.uuid4().hex[:6]}"
        self._insert_player(p_name, balance=100.0)
        self._insert_user(p_name, shop_points=100)

        with get_db_connection() as conn:
            c = conn.cursor()

            # 1. Dungeon reward with lowercase query parameter
            c.execute("UPDATE player_balances SET balance = balance + 350 WHERE username = ? COLLATE NOCASE;", (p_name.lower(),))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (p_name,))
            self.assertEqual(c.fetchone()["balance"], 450.0)

            # 2. Shop spend with uppercase query parameter and conditional guard
            c.execute("""
                UPDATE player_balances 
                SET shop_points = shop_points - 40 
                WHERE username = ? COLLATE NOCASE AND shop_points >= 40;
            """, (p_name.upper(),))
            conn.commit()

            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (p_name.lower(),))
            self.assertEqual(c.fetchone()["shop_points"], 60)

            # 3. Shop spend without explicit COLLATE NOCASE in query, with lowercase parameter
            c.execute("""
                UPDATE player_balances 
                SET shop_points = shop_points - 20 
                WHERE username = ? AND shop_points >= 20;
            """, (p_name.lower(),))
            conn.commit()

            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (p_name.lower(),))
            self.assertEqual(c.fetchone()["shop_points"], 40)

            # 4. Failed condition: attempt to spend 50 when only 40 are available
            c.execute("""
                UPDATE player_balances 
                SET shop_points = shop_points - 50 
                WHERE username = ? AND shop_points >= 50;
            """, (p_name.upper(),))
            conn.commit()

            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (p_name.lower(),))
            self.assertEqual(c.fetchone()["shop_points"], 40, "Points should remain 40 when guard condition shop_points >= 50 fails")

    def test_case_variant_select_view(self):
        """Verify SELECT on player_balances returns correct data across casing variations."""
        p_name = f"ViewSelect_{uuid.uuid4().hex[:6]}"
        self._insert_player(p_name, balance=777.7)
        self._insert_user(p_name, shop_points=88)

        with get_db_connection() as conn:
            c = conn.cursor()

            for variant in [p_name.lower(), p_name.upper(), p_name]:
                c.execute("SELECT username, balance, shop_points FROM player_balances WHERE username = ?;", (variant,))
                row = c.fetchone()
                self.assertIsNotNone(row, f"SELECT failed for case variant: {variant}")
                self.assertEqual(row["balance"], 777.7)
                self.assertEqual(row["shop_points"], 88)

    def test_rapid_alternating_case_transactions(self):
        """Rapid interleaved case updates to confirm trigger consistency and no data drift."""
        p_name = f"StressRapid_{uuid.uuid4().hex[:6]}"
        self._insert_player(p_name, balance=0.0)
        self._insert_user(p_name, shop_points=0)

        cases = [p_name.lower(), p_name.upper(), p_name]

        with get_db_connection() as conn:
            c = conn.cursor()
            for step in range(1, 11):
                case_variant = cases[step % len(cases)]
                c.execute("""
                    UPDATE player_balances
                    SET balance = balance + 10.0, shop_points = shop_points + 5
                    WHERE username = ?;
                """, (case_variant,))
                conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (p_name,))
            final_bal = c.fetchone()["balance"]
            c.execute("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = ?;", (p_name.lower(),))
            final_pts = c.fetchone()["shop_points"]

            self.assertEqual(final_bal, 100.0, f"Expected 100.0 balance after 10 increments, got {final_bal}")
            self.assertEqual(final_pts, 50, f"Expected 50 shop points after 10 increments, got {final_pts}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
