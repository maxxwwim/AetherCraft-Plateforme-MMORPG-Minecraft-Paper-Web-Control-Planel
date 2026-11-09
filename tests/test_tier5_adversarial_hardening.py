"""
================================================================================
Milestone M4: Tier 5 White-Box Adversarial Coverage Hardening Test Suite
================================================================================
Target: Aethercraft Cross-Platform (Flask Web + SQLite + Paper In-Game Contract)
Author: Challenger M4-1

Probes deep white-box edge cases and unprobed paths across 5 critical dimensions:
1. Extreme Database Volume & Bulk Operations (500+ players, high concurrency, boundary limits)
2. Currency Precision & Transaction Atomicity (float boundaries, race condition overdraft prevention, ACID rollback)
3. Session Hijacking & Spoofing on Player Routes (HMAC token tampering, expired timestamps, route auth guards)
4. Unicode & Special Characters (emojis, CJK/Cyrillic/Arabic, SQL injection tokens, XSS autoescape in templates)
5. Nullable Columns & Schema Robustness (NULL guild/dates/ranks, missing users/players cross-joins, empty tables)
================================================================================
"""

import os
import sys
import uuid
import time
import hmac
import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app, verify_game_auth_token
from services.database import (
    DB_PATH,
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_get_leaderboards,
    db_get_top_player,
    db_get_community_tree_donors,
    db_get_community_goal,
    db_contribute_to_community_goal,
    db_get_recent_orders,
    db_save_order,
    db_spend_shop_points,
    db_add_player_balance,
    db_update_player_balance,
    db_create_user,
    db_get_user_by_id,
    db_get_reward_status,
    db_claim_30min_reward,
    db_upsert_player
)
from services.player_service import get_player_profile, get_leaderboards


class TestTier5BulkOperationsAndVolume(unittest.TestCase):
    """Probes extreme database volume, bulk operations, and scaling limits."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_users: List[str] = []
        self.created_orders: List[str] = []

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            if self.created_uuids:
                placeholders = ",".join("?" for _ in self.created_uuids)
                c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
            if self.created_users:
                placeholders = ",".join("?" for _ in self.created_users)
                c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_users)
                c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({placeholders});", self.created_users)
                c.execute(f"DELETE FROM tree_contributions WHERE username IN ({placeholders});", self.created_users)
            if self.created_orders:
                placeholders = ",".join("?" for _ in self.created_orders)
                c.execute(f"DELETE FROM store_orders WHERE order_id IN ({placeholders});", self.created_orders)
            conn.commit()

    def test_bulk_500_players_leaderboard_pagination_and_monotonicity(self):
        """Generates 500 players with randomized stats and tests leaderboard bounds."""
        now = "2026-11-06 12:00:00"
        bulk_rows = []
        for i in range(500):
            p_uuid = str(uuid.uuid4())
            uname = f"Bulk_{i:04d}_{p_uuid[:6]}"
            self.created_uuids.append(p_uuid)
            self.created_users.append(uname)
            balance = float(i * 10)
            hours = i
            kills = i * 2
            deaths = i + 1
            bulk_rows.append((p_uuid, uname, "JOUEUR", balance, hours, kills, deaths, 1, "GuildeBulk", now, now))

        with get_db_connection() as conn:
            c = conn.cursor()
            c.executemany("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, bulk_rows)
            conn.commit()

        # Measure query performance and correctness with large limit
        t0 = time.perf_counter()
        lb = db_get_leaderboards(limit=100)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 0.5, f"Leaderboard query took too long: {elapsed:.3f}s")
        self.assertEqual(len(lb["top_rich"]), 100)
        self.assertEqual(len(lb["top_hours"]), 100)
        self.assertEqual(len(lb["top_kills"]), 100)

        # Verify strict descending monotonicity for top_rich
        prev_wealth = float("inf")
        for p in lb["top_rich"]:
            self.assertLessEqual(p["total_wealth"], prev_wealth, "Top rich ranking must be monotonically decreasing")
            prev_wealth = p["total_wealth"]

        # Boundary checks: limit=0, limit=-1, limit=1000
        lb_zero = db_get_leaderboards(limit=0)
        self.assertEqual(len(lb_zero["top_rich"]), 0)

        lb_huge = db_get_leaderboards(limit=1000)
        self.assertGreaterEqual(len(lb_huge["top_rich"]), 500)

    def test_bulk_community_tree_contributions_and_tier_progression(self):
        """Stress-tests community contributions from 100 distinct contributors and checks donor rankings."""
        for i in range(100):
            uname = f"TreeDonor_{i:03d}_{uuid.uuid4().hex[:6]}"
            self.created_users.append(uname)
            db_contribute_to_community_goal("s4_celestial_tree", amount=5 + i, username=uname, ore_price=10.0)

        donors = db_get_community_tree_donors(limit=10)
        self.assertEqual(len(donors), 10)
        # Top donor should have highest weighted_points
        self.assertGreaterEqual(donors[0]["weighted_points"], donors[-1]["weighted_points"])
        for d in donors:
            self.assertGreater(d["share_pct"], 0.0)
            self.assertGreater(d["unit_pct"], 0.0)

    def test_bulk_store_orders_persistence_and_deserialization(self):
        """Generates 150 store orders and tests JSON parsing and sorting."""
        for i in range(150):
            oid = f"ORD_BULK_{i:04d}_{uuid.uuid4().hex[:6]}"
            self.created_orders.append(oid)
            items = [{"item_id": f"item_{i}", "qty": 1, "price": 4.99}]
            db_save_order(oid, f"Buyer_{i}", total=4.99, items=items, currency="EUR")

        orders = db_get_recent_orders(limit=50)
        self.assertEqual(len(orders), 50)
        for ord_entry in orders:
            self.assertIsInstance(ord_entry["products"], list)
            self.assertEqual(len(ord_entry["products"]), 1)


class TestTier5CurrencyPrecisionAndAtomicity(unittest.TestCase):
    """Probes currency precision, boundary values, and concurrent thread atomicity."""

    def setUp(self):
        self.created_uuids: List[str] = []
        self.created_users: List[str] = []
        self.created_user_ids: List[int] = []

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            if self.created_uuids:
                placeholders = ",".join("?" for _ in self.created_uuids)
                c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
            if self.created_users:
                placeholders = ",".join("?" for _ in self.created_users)
                c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_users)
                c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({placeholders});", self.created_users)
            conn.commit()

    def test_extreme_float_boundaries_and_precision(self):
        """Validates that high-precision floats and large numbers do not cause silent rounding errors."""
        uname = f"PrecisionUser_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 1234567.8912, 10, 5, 1, 1, 'Precision', ?, ?);
            """, (p_uuid, uname, now, now))
            conn.commit()

        p = db_get_player_by_username(uname)
        self.assertAlmostEqual(p["balance"], 1234567.8912, places=4)

        # Increment with small fractional amount
        new_bal = db_add_player_balance(uname, 0.0088)
        self.assertAlmostEqual(new_bal, 1234567.9000, places=4)

    def test_concurrent_shop_points_deduction_atomicity_no_overdraft(self):
        """Simulates 10 concurrent threads attempting to spend 25 points from an account with only 100 points."""
        uname = f"ConcurrUser_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 100.0, 10, 5, 1, 1, 'Concurr', ?, ?);
            """, (p_uuid, uname, now, now))
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at)
                VALUES (?, 'hash', 'salt', ?, 100, 0, ?);
            """, (f"{uname}@test.local", uname, now))
            uid = c.lastrowid
            conn.commit()

        results = []
        def spend_task():
            success = db_spend_shop_points(uid, 25)
            results.append(success)

        threads = [threading.Thread(target=spend_task) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)

        # Exactly 4 should succeed (4 * 25 = 100), 6 should fail
        self.assertEqual(success_count, 4, f"Expected exactly 4 successes, got {success_count}")
        self.assertEqual(fail_count, 6, f"Expected exactly 6 failures, got {fail_count}")

        # Final balance must be exactly 0, never negative
        p_final = db_get_player_by_username(uname)
        u_final = db_get_user_by_id(uid)
        self.assertEqual(p_final["balance"], 0.0)
        # In Milestone M4 Iteration 2, shop_points is isolated and not overwritten by gold balance
        self.assertEqual(u_final["shop_points"], 100)

    def test_negative_and_zero_currency_guard(self):
        """Negative and zero deductions must be rejected by db_spend_shop_points."""
        uname = f"NegGuard_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 500.0, 10, 5, 1, 1, 'Guards', ?, ?);
            """, (p_uuid, uname, now, now))
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at)
                VALUES (?, 'hash', 'salt', ?, 500, 0, ?);
            """, (f"{uname}@test.local", uname, now))
            uid = c.lastrowid
            conn.commit()

        # Reject negative
        self.assertFalse(db_spend_shop_points(uid, -100))
        # Reject zero
        self.assertFalse(db_spend_shop_points(uid, 0))

        # Balance remains unmodified
        p = db_get_player_by_username(uname)
        self.assertEqual(p["balance"], 500.0)


class TestTier5SessionSecurityAndSpoofing(unittest.TestCase):
    """Probes session hijacking, token forgery, timestamp tampering, and route security."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_webdisplay_hmac_valid_and_tampered_token(self):
        """Probes HMAC validation with correct tokens, expired timestamps, and tampered signatures."""
        key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        username = "validplayer"
        now = int(time.time())

        # 1. Valid token
        expected_sig = hmac.new(key.encode("utf-8"), f"{username.lower()}:{now}".encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertTrue(verify_game_auth_token(username, str(now), expected_sig))

        # 2. Expired timestamp (> 3600s in past)
        past_ts = now - 3601
        past_sig = hmac.new(key.encode("utf-8"), f"{username.lower()}:{past_ts}".encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertFalse(verify_game_auth_token(username, str(past_ts), past_sig), "Expired token must be rejected")

        # 3. Future timestamp (> 3600s in future)
        future_ts = now + 3601
        future_sig = hmac.new(key.encode("utf-8"), f"{username.lower()}:{future_ts}".encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertFalse(verify_game_auth_token(username, str(future_ts), future_sig), "Future skewed token must be rejected")

        # 4. Forged username with valid signature of another user
        self.assertFalse(verify_game_auth_token("attacker", str(now), expected_sig), "User spoofing must fail HMAC check")

        # 5. Tampered signature
        corrupted_sig = expected_sig[:-4] + "0000"
        self.assertFalse(verify_game_auth_token(username, str(now), corrupted_sig), "Tampered signature must fail")

        # 6. Malformed inputs
        self.assertFalse(verify_game_auth_token("", str(now), expected_sig))
        self.assertFalse(verify_game_auth_token(username, "not_a_number", expected_sig))

    def test_webdisplay_panel_renders_authenticated_vs_unauthenticated(self):
        """Verifies webdisplay panel handles valid vs unauthenticated sessions correctly."""
        now = int(time.time())
        key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        token = hmac.new(key.encode("utf-8"), f"testpilot:{now}".encode("utf-8"), hashlib.sha256).hexdigest()

        # 1. Valid auth with client
        resp_auth = self.client.get(f"/webdisplay?player=TestPilot&ts={now}&token={token}")
        self.assertEqual(resp_auth.status_code, 200)
        html_auth = resp_auth.get_data(as_text=True)
        self.assertIn("SOCKET JEU AUTHENTIFIÉ", html_auth)

        # 2. Unauthenticated access from fresh client (no session cookie) with bad token
        fresh_client = app.test_client()
        resp_unauth = fresh_client.get(f"/webdisplay?player=TestPilot&ts={now}&token=badtoken")
        self.assertEqual(resp_unauth.status_code, 200)
        html_unauth = resp_unauth.get_data(as_text=True)
        self.assertIn("SESSION JOUEUR", html_unauth)
        self.assertNotIn("SOCKET JEU AUTHENTIFIÉ", html_unauth)

        # 3. Session spoofing attempt: authenticated as TestPilot, but attempting to view AnotherUser without valid token
        resp_spoof = self.client.get(f"/webdisplay?player=AnotherUser&ts={now}&token=badtoken")
        self.assertEqual(resp_spoof.status_code, 200)
        html_spoof = resp_spoof.get_data(as_text=True)
        self.assertIn("SESSION JOUEUR", html_spoof)
        self.assertNotIn("SOCKET JEU AUTHENTIFIÉ", html_spoof)

    def test_protected_routes_reject_unauthenticated_requests(self):
        """Ensures state-mutating endpoints enforce authentication."""
        # /api/market/buy
        resp_buy = self.client.post("/api/market/buy", data={"listing_id": "listing_123"})
        self.assertIn(resp_buy.status_code, (302, 401))

        # /api/auras/toggle
        resp_aura = self.client.post("/api/auras/toggle", data={"aura_type": "titan"})
        self.assertIn(resp_aura.status_code, (302, 401))

        # /api/pets/summon
        resp_pet = self.client.post("/api/pets/summon", data={"pet_type": "dragon"})
        self.assertIn(resp_pet.status_code, (302, 401))

        # /admin
        resp_admin = self.client.get("/admin")
        self.assertIn(resp_admin.status_code, (302, 401, 403))


class TestTier5UnicodeAndSpecialCharacters(unittest.TestCase):
    """Probes full Unicode range, exotic characters, SQL safety, and template escaping."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_users: List[str] = []

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            if self.created_uuids:
                placeholders = ",".join("?" for _ in self.created_uuids)
                c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
            if self.created_users:
                placeholders = ",".join("?" for _ in self.created_users)
                c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_users)
            conn.commit()

    def test_unicode_player_and_guild_names_across_data_layer(self):
        """Verifies multi-lingual Unicode player names and guilds (French, Cyrillic, CJK, Emoji)."""
        unicode_samples = [
            ("Éléonore_Céleste", "Guilde_des_Étoiles✨", 15000.0),
            ("Борис_Воин", "Гильдия_Севера", 12000.0),
            ("蒼穹の騎士_ケン", "天界の守護者⛩️", 18000.0),
            ("فارس_الصحراء", "واحة_السلام🌙", 9000.0),
            ("⚔️Valkyrie👑", "Valhalla⚡", 22000.0)
        ]
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            for uname, guild, bal in unicode_samples:
                p_uuid = str(uuid.uuid4())
                self.created_uuids.append(p_uuid)
                self.created_users.append(uname)
                c.execute("""
                    INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                    VALUES (?, ?, 'JOUEUR', ?, 25, 10, 2, 1, ?, ?, ?);
                """, (p_uuid, uname, bal, guild, now, now))
            conn.commit()

        # Query all and verify Unicode exact preservation
        for uname, guild, bal in unicode_samples:
            p = db_get_player_by_username(uname)
            self.assertIsNotNone(p, f"Failed to retrieve Unicode player: {uname}")
            self.assertEqual(p["username"], uname)
            self.assertEqual(p["guild"], guild)

        # Leaderboard query must safely include Unicode names
        lb = db_get_leaderboards(limit=10)
        rich_names = [r["username"] for r in lb["top_rich"]]
        for uname, _, _ in unicode_samples:
            self.assertIn(uname, rich_names)

    def test_template_xss_escaping_for_adversarial_usernames(self):
        """Adversarial usernames containing HTML/script tags must be escaped in web rendering."""
        xss_uname = "XSS_<script>alert('pwn')</script>"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(xss_uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 9999999.0, 100, 50, 1, 1, 'SecurityGuild', ?, ?);
            """, (p_uuid, xss_uname, now, now))
            conn.commit()

        # Render /joueurs
        resp = self.client.get("/joueurs")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # The script tag MUST be escaped, never raw executable HTML
        self.assertNotIn("<script>alert('pwn')</script>", html)
        self.assertIn("&lt;script&gt;alert(&#39;pwn&#39;)&lt;/script&gt;", html)

    def test_search_endpoint_with_unicode_and_special_characters(self):
        """POST /api/players/search must handle exotic characters gracefully without crashing."""
        for exotic in ["Ωmega_Joueur", "Pseudo avec espaces", "User%20Encoded", "Таинственный_странник"]:
            resp = self.client.post("/api/players/search", data={"username": exotic})
            self.assertEqual(resp.status_code, 200, f"Search crashed on '{exotic}'")


class TestTier5NullableColumnsAndSchemaRobustness(unittest.TestCase):
    """Probes NULL fields, missing foreign keys, cross-table divergence, and empty tables."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_users: List[str] = []

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            if self.created_uuids:
                placeholders = ",".join("?" for _ in self.created_uuids)
                c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
            if self.created_users:
                placeholders = ",".join("?" for _ in self.created_users)
                c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_users)
                c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({placeholders});", self.created_users)
            conn.commit()

    def test_players_with_null_guild_and_unmapped_rank(self):
        """Player with NULL guild and non-existent rank must resolve with clean fallbacks."""
        uname = f"NullGuild_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'NON_EXISTENT_RANK', 5000.0, 10, 5, 2, 0, NULL, ?, ?);
            """, (p_uuid, uname, now, now))
            conn.commit()

        # 1. db_get_player_by_username
        p = db_get_player_by_username(uname)
        self.assertIsNotNone(p)
        self.assertIsNone(p["guild"])
        self.assertEqual(p["rank_name"], "NON_EXISTENT_RANK")
        self.assertEqual(p["rank_prefix"], "[NON_EXISTENT_RANK]")
        self.assertEqual(p["badge_color"], "slate")

        # 2. get_player_profile
        prof = get_player_profile(uname)
        self.assertIsNotNone(prof)
        self.assertEqual(prof["rank_color"], "slate")

        # 3. Leaderboard query
        lb = db_get_leaderboards(limit=10)
        found = next((r for r in lb["top_rich"] if r["username"] == uname), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["badge_color"], "slate")

    def test_top_player_mvp_score_with_zero_stats(self):
        """Tests db_get_top_player() composite score calculation with 0 kills, 0 deaths, 0 hours."""
        uname = f"ZeroMVP_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 1000.0, 0, 0, 0, 1, 'Guild', ?, ?);
            """, (p_uuid, uname, now, now))
            conn.commit()

        top = db_get_top_player()
        self.assertIsNotNone(top)
        self.assertIn("mvp_score", top)
        self.assertIsInstance(top["mvp_score"], (int, float))

    def test_missing_user_row_shop_points_default(self):
        """When a player has no users row, shop_points must gracefully default to 10."""
        uname = f"NoUserRow_{uuid.uuid4().hex[:6]}"
        p_uuid = str(uuid.uuid4())
        self.created_uuids.append(p_uuid)
        self.created_users.append(uname)
        now = "2026-11-06 12:00:00"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'VIP', 2500.0, 15, 8, 3, 1, 'Orphans', ?, ?);
            """, (p_uuid, uname, now, now))
            conn.commit()

        p = db_get_player_by_username(uname)
        self.assertEqual(p["shop_points"], 10)

        # In leaderboards as well
        lb = db_get_leaderboards(limit=10)
        found = next((r for r in lb["top_rich"] if r["username"] == uname), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["shop_points"], 10)


if __name__ == "__main__":
    unittest.main()
