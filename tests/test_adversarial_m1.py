"""
Adversarial Stress Test Suite for Milestone M1 (Data Layer & Mock Purge).
Executed by teamwork_challenger_m1_1.

Adversarially stress-tests:
1. SQL injection resilience, special characters, unicode, and emojis in player names.
2. Extreme values: quadrillion balances, negative balances, zero kills/deaths, zero division.
3. Foreign key / relation gaps: unmapped ranks, missing bank accounts, missing user accounts.
4. Strict leaderboard ordering and tie-breaking logic.
5. Deep semantics of player_balances VIEW and INSTEAD OF triggers:
   - Simultaneous update of balance and shop_points
   - Case sensitivity under BINARY vs COLLATE NOCASE
   - Silent point loss when player lacks a users table row
6. Multi-threaded concurrency under rapid read/write loads.
7. Mock player eradication casing resilience.
8. Fresh database initialization and missing table discovery (player_bank_accounts).
"""

import os
import sys
import uuid
import time
import tempfile
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

import services.database as db_mod
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


class TestAdversarialM1(unittest.TestCase):

    def setUp(self):
        init_database()
        self.created_uuids = []
        self.created_usernames = []

    def tearDown(self):
        # Comprehensive cleanup of all test rows after every test
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
                    c.execute(f"DELETE FROM tree_contributions WHERE username IN ({placeholders});", self.created_usernames)
                conn.commit()

    def _insert_player(self, username, rank="JOUEUR", balance=1000.0, hours=0, kills=0, deaths=0, is_online=0, guild="Adversarial"):
        p_uuid = str(uuid.uuid4())
        now = "2026-11-06 12:00:00"
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (p_uuid, username, rank, balance, hours, kills, deaths, is_online, guild, now, now))
            conn.commit()
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(username)
        return p_uuid

    def _insert_user(self, username, shop_points=10):
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at)
                VALUES (?, 'hash', 'salt', ?, ?, '2026-11-06');
            """, (f"{username}@adv.test", username, shop_points))
            conn.commit()
        if username not in self.created_usernames:
            self.created_usernames.append(username)

    def test_adv_special_characters_and_sql_injection(self):
        """Stress-test queries and helpers against SQL injection patterns, quotes, emojis, and unicode."""
        adversarial_names = [
            f"adv_sql_{uuid.uuid4().hex[:4]}'; DROP TABLE players; --",
            f"adv_or_{uuid.uuid4().hex[:4]}' OR '1'='1",
            f"adv_quote_{uuid.uuid4().hex[:4]}\" AND 1=1",
            f"adv_xss_{uuid.uuid4().hex[:4]}<script>alert(1)</script>",
            f"adv_unicode_{uuid.uuid4().hex[:4]}_⚔️👑🛡️",
            f"adv_accent_{uuid.uuid4().hex[:4]}_Élite_Céleste",
            f"adv_cyrillic_{uuid.uuid4().hex[:4]}_Игрок",
        ]

        for name in adversarial_names:
            u_id = self._insert_player(name, balance=500.0, hours=10, kills=5, deaths=2)
            
            # 1. Direct fetch
            profile = db_get_player_by_username(name)
            self.assertIsNotNone(profile, f"Failed to retrieve profile with adversarial username: {name}")
            self.assertEqual(profile["username"], name)
            self.assertEqual(profile["balance"], 500.0)

            # 2. View resolution
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT balance, shop_points FROM player_balances WHERE username = ?;", (name,))
                v_row = c.fetchone()
                self.assertIsNotNone(v_row, f"player_balances VIEW failed for: {name}")
                self.assertEqual(v_row["balance"], 500.0)

            # 3. View update with injection string
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE player_balances SET balance = 750.0 WHERE username = ?;", (name,))
                conn.commit()

            updated_profile = db_get_player_by_username(name)
            self.assertEqual(updated_profile["balance"], 750.0)

        # 4. Check leaderboards include the unicode / injection names cleanly without crashing
        lb = db_get_leaderboards(limit=20)
        top_rich_names = [p["username"] for p in lb["top_rich"]]
        for name in adversarial_names:
            self.assertIn(name, top_rich_names)

    def test_adv_extreme_balances_and_numeric_boundaries(self):
        """Stress-test numerical extremes: huge numbers, negative balances, division by zero."""
        huge_balance = 999_999_999_999_999.50  # ~1 Quadrillion
        negative_balance = -50000.0
        zero_balance = 0.0

        p1 = f"adv_huge_{uuid.uuid4().hex[:4]}"
        p2 = f"adv_neg_{uuid.uuid4().hex[:4]}"
        p3 = f"adv_zero_{uuid.uuid4().hex[:4]}"

        # p1: huge balance, max kills, zero deaths
        self._insert_player(p1, balance=huge_balance, hours=999999, kills=500000, deaths=0)
        # p2: negative balance, zero kills, huge deaths
        self._insert_player(p2, balance=negative_balance, hours=1, kills=0, deaths=9999)
        # p3: zero balance, zero kills, zero deaths
        self._insert_player(p3, balance=zero_balance, hours=0, kills=0, deaths=0)

        # 1. Check division by zero in leaderboards
        lb = db_get_leaderboards(limit=10)
        
        # Verify p1 kd_ratio when deaths = 0
        p1_entry = next((p for p in lb["top_rich"] if p["username"] == p1), None)
        self.assertIsNotNone(p1_entry)
        self.assertEqual(p1_entry["balance"], huge_balance)
        self.assertEqual(p1_entry["kd_ratio"], 500000)

        # Verify p3 kd_ratio when kills = 0 and deaths = 0
        prof3 = db_get_player_by_username(p3)
        self.assertEqual(prof3["balance"], 0.0)

        # 2. Check MVP score calculation with extreme values
        top = db_get_top_player()
        self.assertIsNotNone(top)
        self.assertIsInstance(top["mvp_score"], float)

        # 3. View update with huge balance
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE player_balances SET balance = ? WHERE username = ?;", (1e14, p1))
            conn.commit()

        updated = db_get_player_by_username(p1)
        self.assertEqual(updated["balance"], 1e14)

    def test_adv_null_fields_and_unregistered_ranks(self):
        """Stress-test foreign key gaps: unmapped rank, missing bank account, missing user account."""
        unmapped_rank_user = f"adv_norank_{uuid.uuid4().hex[:4]}"
        p_uuid = str(uuid.uuid4())
        now = "2026-11-06 12:00:00"

        # Insert player with a rank that does NOT exist in `ranks` table
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'NON_EXISTENT_RANK', 3000.0, 20, 10, 2, 1, 'Rogue', ?, ?);
            """, (p_uuid, unmapped_rank_user, now, now))
            conn.commit()
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(unmapped_rank_user)

        # Profile fetch must gracefully fall back without crashing
        profile = db_get_player_by_username(unmapped_rank_user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["rank"], "NON_EXISTENT_RANK")
        self.assertEqual(profile["rank_name"], "NON_EXISTENT_RANK")
        self.assertEqual(profile["badge_color"], "slate")
        self.assertEqual(profile["bank_coins"], 0.0)
        self.assertEqual(profile["total_wealth"], 3000.0)
        self.assertEqual(profile["shop_points"], 10)  # Default COALESCE

        # Leaderboard inclusion
        lb = db_get_leaderboards(limit=10)
        entry = next((p for p in lb["top_rich"] if p["username"] == unmapped_rank_user), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["rank_name"], "NON_EXISTENT_RANK")
        self.assertEqual(entry["badge_color"], "slate")

    def test_adv_leaderboard_strict_ordering_and_tie_breaks(self):
        """Verify strict ordering for wealth, hours, and kills; verify tie-breaking behavior."""
        prefix = f"adv_tie_{uuid.uuid4().hex[:4]}"
        uA = f"{prefix}_A"
        uB = f"{prefix}_B"
        uC = f"{prefix}_C"
        uD = f"{prefix}_D"

        # uA: Wealth 50,000 (bal 50000, bank 0), Hours 50, Kills 10, Deaths 1 -> kd=10.0
        self._insert_player(uA, balance=50000.0, hours=50, kills=10, deaths=1)
        # uB: Wealth 50,000 (bal 20000, bank 30000), Hours 100, Kills 10, Deaths 2 -> kd=5.0
        self._insert_player(uB, balance=20000.0, hours=100, kills=10, deaths=2)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO player_bank_accounts (username, bank_coins) VALUES (?, 30000.0);", (uB,))
            conn.commit()
        # uC: Wealth 10,000, Hours 200, Kills 50, Deaths 5 -> kd=10.0
        self._insert_player(uC, balance=10000.0, hours=200, kills=50, deaths=5)
        # uD: Wealth 50,000 (bal 50000, bank 0), Hours 50, Kills 20, Deaths 1 -> kd=20.0
        self._insert_player(uD, balance=50000.0, hours=50, kills=20, deaths=1)

        lb = db_get_leaderboards(limit=10)

        # 1. Wealth: uA, uB, uD all have 50,000 total wealth. uC has 10,000.
        rich_names = [p["username"] for p in lb["top_rich"]]
        self.assertIn(uC, rich_names)
        pos_uC = rich_names.index(uC)
        for u in [uA, uB, uD]:
            self.assertIn(u, rich_names)
            self.assertLess(rich_names.index(u), pos_uC, f"{u} must be ranked above {uC} in top_rich")

        # 2. Hours: uC (200) > uB (100) > uA (50) == uD (50)
        hour_names = [p["username"] for p in lb["top_hours"]]
        self.assertLess(hour_names.index(uC), hour_names.index(uB))
        self.assertLess(hour_names.index(uB), hour_names.index(uA))
        self.assertLess(hour_names.index(uB), hour_names.index(uD))

        # 3. Kills: uC (50) > uD (20) > uA & uB (tie at 10 kills)
        # Tie-break in query: ORDER BY p.kills DESC, kd_ratio DESC
        # uA kd_ratio = 10.0, uB kd_ratio = 5.0 -> uA must be ranked above uB!
        kill_names = [p["username"] for p in lb["top_kills"]]
        self.assertLess(kill_names.index(uC), kill_names.index(uD))
        self.assertLess(kill_names.index(uD), kill_names.index(uA))
        self.assertLess(kill_names.index(uA), kill_names.index(uB),
                        f"Tie-breaking failure: uA (kd=10) should be above uB (kd=5) in top_kills")

    def test_adv_player_balances_triggers_deep_semantics(self):
        """Stress-test INSTEAD OF triggers on player_balances under various update patterns."""
        user = f"adv_trg_{uuid.uuid4().hex[:6]}"
        self._insert_player(user, balance=100.0)
        self._insert_user(user, shop_points=20)

        with get_db_connection() as conn:
            c = conn.cursor()

            # 1. Update both balance and shop_points simultaneously
            c.execute("""
                UPDATE player_balances
                SET balance = 999.0, shop_points = 77
                WHERE username = ?;
            """, (user,))
            conn.commit()

            # Verify both underlying tables received updates
            c.execute("SELECT balance FROM players WHERE username = ?;", (user,))
            p_bal = c.fetchone()["balance"]
            c.execute("SELECT shop_points FROM users WHERE minecraft_username = ?;", (user,))
            u_pts = c.fetchone()["shop_points"]
            self.assertEqual(p_bal, 999.0, "Simultaneous update: players.balance not updated")
            self.assertEqual(u_pts, 77, "Simultaneous update: users.shop_points not updated")

            # 2. Case-insensitive trigger match with COLLATE NOCASE (as used in Java plugin queries)
            c.execute("""
                UPDATE player_balances
                SET balance = 1234.0
                WHERE username = ? COLLATE NOCASE;
            """, (user.upper(),))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (user,))
            self.assertEqual(c.fetchone()["balance"], 1234.0, "Case-insensitive update via COLLATE NOCASE failed")

            # 3. Update shop_points for a player who does NOT have a user account
            no_user_player = f"adv_nouser_{uuid.uuid4().hex[:6]}"
            self._insert_player(no_user_player, balance=250.0)

            # Trigger executes without SQL error
            c.execute("""
                UPDATE player_balances
                SET balance = 300.0, shop_points = 50
                WHERE username = ?;
            """, (no_user_player,))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE username = ?;", (no_user_player,))
            self.assertEqual(c.fetchone()["balance"], 300.0)

            # Check shop_points in view: since no user row exists, shop_points falls back to COALESCE(u.shop_points, 10) = 10
            c.execute("SELECT shop_points FROM player_balances WHERE username = ?;", (no_user_player,))
            v_pts = c.fetchone()["shop_points"]
            self.assertEqual(v_pts, 10, "Without users row, view defaults to COALESCE fallback 10")

    def test_adv_multi_threaded_concurrency(self):
        """Stress-test database under concurrent reads and writes across multiple threads."""
        player_names = [f"adv_conc_{uuid.uuid4().hex[:4]}_{i}" for i in range(8)]
        for name in player_names:
            self._insert_player(name, balance=1000.0, hours=10, kills=5)
            self._insert_user(name, shop_points=50)

        def worker_task(worker_id):
            errors = []
            for iteration in range(5):
                name = player_names[worker_id % len(player_names)]
                try:
                    # 1. Read leaderboards
                    lb = db_get_leaderboards(limit=5)
                    # 2. Read single profile
                    prof = db_get_player_by_username(name)
                    # 3. Write via player_balances view
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        new_bal = 1000.0 + (worker_id * 10) + iteration
                        c.execute("UPDATE player_balances SET balance = ? WHERE username = ?;", (new_bal, name))
                        conn.commit()
                except Exception as exc:
                    errors.append(f"Worker {worker_id} iteration {iteration} error: {exc}")
            return errors

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(worker_task, i) for i in range(6)]
            all_errors = []
            for f in as_completed(futures):
                all_errors.extend(f.result())

        self.assertEqual(len(all_errors), 0, f"Concurrency stress errors encountered: {all_errors}")

    def test_adv_mock_eradication_casing_resilience(self):
        """Stress-test mock eradication against different casing variations."""
        casing_variations = [
            "aetherknight", "AETHERKNIGHT", "AeThErKnIgHt",
            "notch", "NOTCH", "NoTcH",
            "pixelsorceress", "PIXELSORCERESS",
            "vortexcrafter", "VORTEXCRAFTER",
            "shadowranger", "SHADOWRANGER"
        ]

        for mock in casing_variations:
            res = db_upsert_player(mock)
            self.assertIsNotNone(res)
            # Verify NOT in active database
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) AS c FROM players WHERE LOWER(username) = LOWER(?);", (mock,))
                count = c.fetchone()["c"]
            self.assertEqual(count, 0, f"Mock player with variation '{mock}' was persisted in players table!")

    def test_adv_fresh_db_initialization_missing_bank_accounts_table(self):
        """Adversarial stress-test: fresh database creation with init_database().
        Exposes whether init_database() creates all tables required by db_get_leaderboards().
        Specifically, tests if player_bank_accounts is created by init_database()."""
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)
        orig_path = db_mod.DB_PATH
        try:
            db_mod.DB_PATH = temp_path
            db_mod.init_database()

            # Verify if player_bank_accounts table was created
            with db_mod.get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_bank_accounts';")
                row = c.fetchone()

            # We test whether db_get_leaderboards() crashes or succeeds on a freshly initialized database
            try:
                lb = db_mod.db_get_leaderboards(limit=5)
                # If it succeeds, player_bank_accounts was either created or handled gracefully
                self.assertIsInstance(lb, dict)
            except sqlite3.OperationalError as e:
                # Document empirical bug: no such table: player_bank_accounts
                self.assertIn("no such table: player_bank_accounts", str(e))
                # Re-raise to record as a documented adversarial vulnerability
                raise AssertionError(
                    f"CRITICAL VULNERABILITY: init_database() fails to create player_bank_accounts! "
                    f"db_get_leaderboards() crashes on fresh database: {e}"
                )
        finally:
            db_mod.DB_PATH = orig_path
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
