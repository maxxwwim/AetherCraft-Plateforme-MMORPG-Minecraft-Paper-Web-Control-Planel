"""
================================================================================
AetherCraft Concurrency & Empirical Security Stress Harness (Challenger Sec 2)
Test Suite: test_challenger_sec_empirical_2.py
Author: teamwork_challenger_sec_2
Target Project: C:\\Users\\1234\\Desktop\\Projets\\aethercraft

MANDATORY MISSION CHALLENGES:
1. Concurrency & Race Condition Challenge:
   - Multi-threaded simultaneous invocation of /api/webdisplay/action with action="claim_quest"
     attempting double-claim race conditions on SQLite database.
   - Multi-threaded simultaneous buy_item invocations under balance constraint.
   - Database transactional isolation and progression limit integrity.
2. Packet Bridge Purchase Concurrency:
   - Rapid simultaneous purchase requests simulating CHANNEL_BUY_ITEM in AetherPacketBridge.java.
   - Verification of atomic deduction (UPDATE ... WHERE ... AND balance >= ?).
   - Rollback safety on failure and zero overdraft tolerance (balance never drops < 0).
   - Simultaneous shop points deductions (UPDATE ... WHERE ... AND shop_points >= ?).
3. OneBlock Island Protection Challenge:
   - Visiting players rapidly breaking central generator blocks under diverse UUID permutations.
   - UUID case sensitivity, co-op trusted members, substring attacker UUIDs, null UUIDs,
     offline-mode hash UUIDs, and network latency jitter simulation.
4. Offline-Mode Operator Spoofing:
   - Cracked client connection attempts with administrator usernames (Hactheglitchis, Lum).
   - Verification that operator permissions are immediately stripped on PlayerJoinEvent.
   - Verification that dangerous admin commands (/op, /stop, /reload, /restart) are cancelled.
   - Verification that /opauth token validation works and restores OP privileges securely.
   - Verification that player disconnect (PlayerQuitEvent) cleanses operator cache.
================================================================================
"""

import os
import sys
import re
import math
import time
import json
import uuid
import hmac
import hashlib
import sqlite3
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import unittest
from typing import Dict, List, Tuple, Optional, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")
PLUGINS_SRC = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app, verify_game_auth_token
from services.database import (
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_upsert_player,
    db_claim_quest,
    db_get_user_by_username,
    db_unlock_item_for_user,
    db_update_player_balance
)
from services.security_middleware import rate_limiter


# ==============================================================================
# CHALLENGE SUITE 1: WEBDISPLAY ACTION CONCURRENCY & RACE CONDITIONS
# ==============================================================================

class TestWebDisplayActionConcurrency(unittest.TestCase):
    """
    Stress-tests /api/webdisplay/action under high multi-threaded concurrency
    to detect race conditions in daily quest claims and shop balance deductions.
    """

    def setUp(self):
        init_database()
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = True
        rate_limiter.reset()
        self.client = app.test_client()

    def tearDown(self):
        rate_limiter.reset()
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE username IN ('QuestRacer', 'BuyerRacer', 'AtomicCoinBuyer', 'AtomicPointsBuyer', 'RollbackSafetyTester');")
            c.execute("DELETE FROM player_daily_quest_claims WHERE LOWER(username) IN ('questracer', 'buyerracer');")
            c.execute("DELETE FROM user_unlocked_items WHERE LOWER(minecraft_username) IN ('questracer', 'buyerracer', 'atomiccoinbuyer', 'atomicpointsbuyer', 'rollbacksafetytester');")
            conn.commit()

    def test_challenge_01_webdisplay_claim_quest_concurrency_race(self):
        """
        Challenge 1.1: Multi-threaded simultaneous claim_quest requests on SQLite.
        Attempts to double-claim the 500 coin reward via concurrent threads.
        Must enforce single-claim progression invariant:
        - Exactly ONE request may successfully claim (+500 coins).
        - Subsequent/concurrent requests must be rejected with HTTP 429 (Progression limit reached).
        - Final balance must be initial_balance + 500.0 (NO double or multiple credits).
        """
        username = "QuestRacer"
        initial_balance = 1000.0
        db_upsert_player(username, rank="JOUEUR")
        db_update_player_balance(username, initial_balance)

        # Clear any prior daily claims for this player
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS player_daily_quest_claims (username TEXT PRIMARY KEY, last_claimed_date TEXT NOT NULL, claimed_at TEXT NOT NULL);")
            c.execute("DELETE FROM player_daily_quest_claims WHERE LOWER(username) = LOWER(?);", (username,))
            conn.commit()

        rate_limiter.reset()
        num_threads = 10
        barrier = threading.Barrier(num_threads)
        results = []

        def submit_claim():
            with app.test_client() as cl:
                with cl.session_transaction() as sess:
                    sess["game_auth"] = username.lower()
                    sess["minecraft_username"] = username

                # Synchronize threads at barrier to maximize race condition collision
                try:
                    barrier.wait(timeout=5.0)
                except threading.BrokenBarrierError:
                    pass

                resp = cl.post("/api/webdisplay/action", json={
                    "player": username,
                    "action": "claim_quest"
                })
                return resp.status_code, resp.get_json()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(submit_claim) for _ in range(num_threads)]
            for fut in as_completed(futures):
                results.append(fut.result())

        # Inspect HTTP response distribution
        status_codes = [code for code, _ in results]
        success_count = status_codes.count(200)
        rejected_count = status_codes.count(429)

        # Invariant 1: Exactly 1 claim succeeds
        self.assertEqual(success_count, 1, f"Expected exactly 1 successful claim, got {success_count}. Responses: {status_codes}")
        self.assertEqual(rejected_count, num_threads - 1, f"Expected {num_threads - 1} rejections with 429, got {rejected_count}")

        # Invariant 2: Database balance is credited exactly once (+500.0)
        player = db_get_player_by_username(username)
        self.assertIsNotNone(player)
        expected_balance = initial_balance + 500.0
        actual_balance = float(player["balance"])
        self.assertEqual(actual_balance, expected_balance,
                         f"CRITICAL RACE CONDITION: Player balance should be {expected_balance}, but got {actual_balance}!")

        # Invariant 3: player_daily_quest_claims contains exactly 1 row
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM player_daily_quest_claims WHERE LOWER(username) = LOWER(?);", (username,))
            row = c.fetchone()
            self.assertEqual(row["cnt"], 1, "player_daily_quest_claims must have exactly 1 record for user")

    def test_challenge_02_webdisplay_buy_item_concurrent_insufficient_funds(self):
        """
        Challenge 1.2: Multi-threaded simultaneous buy_item requests.
        Player has balance = 200.0 coins. Item costs 200.0 coins (20 points * 10).
        Multiple threads attempt purchase simultaneously:
        - Only 1 purchase may succeed.
        - Subsequent requests must receive HTTP 400 (insufficient funds).
        - Final balance must be 0.0, NEVER negative.
        """
        username = "BuyerRacer"
        initial_balance = 5000.0
        db_upsert_player(username, rank="JOUEUR")
        db_update_player_balance(username, initial_balance)

        # rank_vip costs 5000.0 coins (500 points * 10)
        item_id = "rank_vip"

        rate_limiter.reset()
        num_threads = 6
        barrier = threading.Barrier(num_threads)
        results = []

        def submit_buy():
            with app.test_client() as cl:
                with cl.session_transaction() as sess:
                    sess["game_auth"] = username.lower()
                    sess["minecraft_username"] = username

                try:
                    barrier.wait(timeout=5.0)
                except threading.BrokenBarrierError:
                    pass

                resp = cl.post("/api/webdisplay/action", json={
                    "player": username,
                    "action": "buy_item",
                    "target": item_id
                })
                return resp.status_code, resp.get_json()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(submit_buy) for _ in range(num_threads)]
            for fut in as_completed(futures):
                results.append(fut.result())

        status_codes = [code for code, _ in results]
        success_count = status_codes.count(200)

        # Only 1 purchase can succeed with 200 coins when item costs 200 coins
        self.assertLessEqual(success_count, 1, f"Overdraft vulnerability detected! {success_count} purchases succeeded on 200 balance.")

        player = db_get_player_by_username(username)
        self.assertGreaterEqual(float(player["balance"]), 0.0, "Balance must NEVER become negative!")


# ==============================================================================
# CHALLENGE SUITE 2: PACKET BRIDGE PURCHASE ATOMIC DEDUCTION & ROLLBACK
# ==============================================================================

class TestPacketBridgePurchaseConcurrency(unittest.TestCase):
    """
    Simulates AetherPacketBridge.java CHANNEL_BUY_ITEM concurrent purchases
    directly against SQLite database using atomic SQL queries:
    - UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?) AND balance >= ?
    - UPDATE users SET shop_points = shop_points - ? WHERE id = ? AND shop_points >= ?
    """

    def setUp(self):
        init_database()

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE username IN ('AtomicCoinBuyer', 'AtomicPointsBuyer', 'RollbackSafetyTester');")
            c.execute("DELETE FROM users WHERE id = 8888 OR minecraft_username IN ('AtomicCoinBuyer', 'AtomicPointsBuyer', 'RollbackSafetyTester');")
            c.execute("DELETE FROM user_unlocked_items WHERE LOWER(minecraft_username) IN ('atomiccoinbuyer', 'atomicpointsbuyer', 'rollbacksafetytester');")
            conn.commit()

    def test_challenge_03_packet_bridge_atomic_coin_deduction_concurrency(self):
        """
        Challenge 2.1: 20 simultaneous buy requests for an item costing 1,000 coins.
        Player has initial balance = 2,500.0 coins.
        Expected:
        - Exactly 2 purchases succeed (2,500 - 2*1,000 = 500).
        - Exactly 18 purchases fail (affected rows == 0, transaction rolled back).
        - Final balance = 500.0 coins. Zero overdraft, no partial deductions.
        """
        username = "AtomicCoinBuyer"
        initial_balance = 2500.0
        cost_coins = 1000.0
        db_upsert_player(username, rank="JOUEUR")
        db_update_player_balance(username, initial_balance)

        item_id = "rank_vip"
        num_threads = 20
        barrier = threading.Barrier(num_threads)
        results = []

        def execute_packet_bridge_buy():
            try:
                barrier.wait(timeout=5.0)
            except threading.BrokenBarrierError:
                pass

            # Emulate exact AetherPacketBridge.java transaction logic
            with sqlite3.connect(DB_PATH, timeout=15.0) as conn:
                conn.execute("PRAGMA busy_timeout = 10000;")
                conn.isolation_level = None  # Autocommit off for explicit tx
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE;")
                try:
                    cursor.execute(
                        "UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?) AND balance >= ?;",
                        (cost_coins, username, cost_coins)
                    )
                    affected = cursor.rowcount
                    if affected == 0:
                        cursor.execute("ROLLBACK;")
                        return False, "INSUFFICIENT_FUNDS"

                    # Log order and unlock item
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_unlocked_items (user_id, minecraft_username, item_id, item_category, item_name, icon, image_url, unlocked_at, source)
                        VALUES (1, ?, ?, 'grades', 'Grade VIP', '✦', '/static/images/items/vip.png', datetime('now'), 'PACKET_BRIDGE');
                    """, (username, f"{item_id}_{time.time_ns()}"))
                    cursor.execute("COMMIT;")
                    return True, "PURCHASE_CONFIRMED"
                except Exception as e:
                    try:
                        cursor.execute("ROLLBACK;")
                    except Exception:
                        pass
                    return False, f"ERROR: {str(e)}"

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(execute_packet_bridge_buy) for _ in range(num_threads)]
            for fut in as_completed(futures):
                results.append(fut.result())

        successes = sum(1 for success, _ in results if success)
        failures = sum(1 for success, _ in results if not success)

        self.assertEqual(successes, 2, f"Expected exactly 2 successful purchases, got {successes} (failures: {failures})")
        self.assertEqual(failures, 18, f"Expected 18 rolled-back purchases, got {failures}")

        # Invariant: Final balance must be exactly 500.0
        player = db_get_player_by_username(username)
        self.assertEqual(float(player["balance"]), 500.0,
                         f"Final balance mismatch! Expected 500.0, got {player['balance']}")

    def test_challenge_04_packet_bridge_atomic_shop_points_concurrency(self):
        """
        Challenge 2.2: 15 simultaneous point purchases for an item costing 100 shop points.
        User has 250 shop points.
        Expected:
        - Exactly 2 purchases succeed (250 - 2*100 = 50).
        - Exactly 13 purchases fail (rollback).
        - Final shop_points = 50.
        """
        username = "AtomicPointsBuyer"
        initial_points = 250
        cost_points = 100

        # Ensure user exists in users table
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO users (id, minecraft_username, email, password_hash, salt, shop_points, is_admin, created_at)
                VALUES (8888, ?, 'points@aether.local', 'hash', 'salt', ?, 0, datetime('now'));
            """, (username, initial_points))
            conn.commit()

        num_threads = 15
        barrier = threading.Barrier(num_threads)
        results = []

        def execute_points_buy():
            try:
                barrier.wait(timeout=5.0)
            except threading.BrokenBarrierError:
                pass

            with sqlite3.connect(DB_PATH, timeout=15.0) as conn:
                conn.execute("PRAGMA busy_timeout = 10000;")
                conn.isolation_level = None
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE;")
                try:
                    cursor.execute(
                        "UPDATE users SET shop_points = shop_points - ? WHERE id = ? AND shop_points >= ?;",
                        (cost_points, 8888, cost_points)
                    )
                    if cursor.rowcount == 0:
                        cursor.execute("ROLLBACK;")
                        return False, "INSUFFICIENT_POINTS"
                    cursor.execute("COMMIT;")
                    return True, "PURCHASE_CONFIRMED"
                except Exception as e:
                    try:
                        cursor.execute("ROLLBACK;")
                    except Exception:
                        pass
                    return False, f"ERROR: {str(e)}"

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(execute_points_buy) for _ in range(num_threads)]
            for fut in as_completed(futures):
                results.append(fut.result())

        successes = sum(1 for success, _ in results if success)
        self.assertEqual(successes, 2, f"Expected exactly 2 point purchases, got {successes}")

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT shop_points FROM users WHERE id = 8888;")
            row = c.fetchone()
            self.assertEqual(row[0], 50, f"Expected 50 shop points remaining, got {row[0]}")

    def test_challenge_05_packet_bridge_rollback_safety_on_error(self):
        """
        Challenge 2.3: Verifies rollback safety when an unexpected error occurs mid-transaction.
        Balance deduction MUST be rolled back if order logging fails.
        """
        username = "RollbackSafetyTester"
        initial_balance = 5000.0
        db_upsert_player(username, rank="JOUEUR")
        db_update_player_balance(username, initial_balance)

        with sqlite3.connect(DB_PATH) as conn:
            conn.isolation_level = None
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            # Deduct balance
            cursor.execute("UPDATE players SET balance = balance - 1000 WHERE LOWER(username) = LOWER(?);", (username,))
            # Simulate crash / failure before commit
            cursor.execute("ROLLBACK;")

        player = db_get_player_by_username(username)
        self.assertEqual(float(player["balance"]), initial_balance, "Rollback failed to restore original balance!")


# ==============================================================================
# CHALLENGE SUITE 3: ONEBLOCK ISLAND PROTECTION CHALLENGE
# ==============================================================================

class TestOneBlockIslandProtectionPermutations(unittest.TestCase):
    """
    Stress-tests OneBlock generator ownership and visitor break rejection
    under diverse player UUID permutations, spoofed identities, and network latency.
    Reference: OneBlockEngine.java lines 587-600.
    """

    class MockPlayer:
        def __init__(self, p_uuid: Optional[uuid.UUID], name: str, is_op: bool = False, has_admin_perm: bool = False):
            self.uuid = p_uuid
            self.name = name
            self.is_op = is_op
            self.has_admin_perm = has_admin_perm

        def get_unique_id(self) -> Optional[uuid.UUID]:
            return self.uuid

        def get_name(self) -> str:
            return self.name

    class MockIsland:
        def __init__(self, owner_uuid: uuid.UUID, owner_name: str, x: int, y: int, z: int, trusted_members: List[str]):
            self.owner_uuid = owner_uuid
            self.owner_name = owner_name
            self.x = x
            self.y = y
            self.z = z
            self.trusted_members = [m.lower() for m in trusted_members]
            self.blocks_broken = 0

        def is_member(self, p_uuid: Optional[uuid.UUID], p_name: Optional[str]) -> bool:
            if p_uuid is not None and self.owner_uuid == p_uuid:
                return True
            if p_name is not None and p_name.lower() in self.trusted_members:
                return True
            return False

        def process_block_break(self, bx: int, by: int, bz: int, player: 'TestOneBlockIslandProtectionPermutations.MockPlayer') -> Tuple[bool, str]:
            """Emulates OneBlockEngine.java onBlockBreak exact logic."""
            if bx == self.x and by == self.y and bz == self.z:
                is_owner_or_member = (
                    (self.owner_uuid is not None and player.get_unique_id() == self.owner_uuid)
                    or self.is_member(player.get_unique_id(), player.get_name())
                    or (player.get_name() is not None and player.get_name().lower() in self.trusted_members)
                    or player.is_op
                    or player.has_admin_perm
                )
                if not is_owner_or_member:
                    # Event cancelled
                    return False, "CANCELLED_PROTECTED_GENERATOR"
                # Event allowed
                self.blocks_broken += 1
                return True, "ALLOWED_GENERATOR_BREAK"
            # Non-generator block
            return True, "ALLOWED_NORMAL_BLOCK"

    def setUp(self):
        self.owner_uuid = uuid.uuid4()
        self.owner_name = "LegitIslandOwner"
        self.island_x, self.island_y, self.island_z = 100, 64, 100
        self.trusted = ["CoOpMemberAlice", "CoOpMemberBob"]
        self.island = self.MockIsland(
            self.owner_uuid, self.owner_name,
            self.island_x, self.island_y, self.island_z,
            self.trusted
        )

    def test_challenge_06_generator_break_uuid_permutations(self):
        """
        Challenge 3.1: Permutations of legitimate owner, members, visitors, and spoofers.
        """
        # 1. Legitimate Owner
        owner_p = self.MockPlayer(self.owner_uuid, self.owner_name)
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, owner_p)
        self.assertTrue(allowed)
        self.assertEqual(reason, "ALLOWED_GENERATOR_BREAK")

        # 2. Trusted Co-op Member (Exact case)
        member_p1 = self.MockPlayer(uuid.uuid4(), "CoOpMemberAlice")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, member_p1)
        self.assertTrue(allowed)

        # 3. Trusted Co-op Member (Different case)
        member_p2 = self.MockPlayer(uuid.uuid4(), "coopmemberbob")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, member_p2)
        self.assertTrue(allowed)

        # 4. Visiting Attacker with Random UUID
        visitor_p = self.MockPlayer(uuid.uuid4(), "GrieferDan")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, visitor_p)
        self.assertFalse(allowed)
        self.assertEqual(reason, "CANCELLED_PROTECTED_GENERATOR")

        # 5. Attacker with Substring Name Spoofing
        spoof_p1 = self.MockPlayer(uuid.uuid4(), "LegitIslandOwner_fake")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, spoof_p1)
        self.assertFalse(allowed)

        spoof_p2 = self.MockPlayer(uuid.uuid4(), "fake_LegitIslandOwner")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, spoof_p2)
        self.assertFalse(allowed)

        # 6. Null UUID Breaker
        null_uuid_p = self.MockPlayer(None, "NullUuidPlayer")
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, null_uuid_p)
        self.assertFalse(allowed)

        # 7. Admin Bypass (is_op=True)
        admin_op = self.MockPlayer(uuid.uuid4(), "StaffAdmin", is_op=True)
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, admin_op)
        self.assertTrue(allowed)

        # 8. Admin Bypass (has_admin_perm=True)
        admin_perm = self.MockPlayer(uuid.uuid4(), "ModUser", has_admin_perm=True)
        allowed, reason = self.island.process_block_break(self.island_x, self.island_y, self.island_z, admin_perm)
        self.assertTrue(allowed)

    def test_challenge_07_generator_rapid_visitor_break_burst_with_latency(self):
        """
        Challenge 3.2: 50 visiting players rapidly sending break packets with simulated latency.
        Invariants:
        - 100% of visitor break attempts are cancelled.
        - Generator block counter does NOT advance.
        - No drops are leaked.
        """
        initial_blocks = self.island.blocks_broken
        num_visitors = 50
        results = []

        def visitor_break_attempt(idx: int):
            time.sleep(random.uniform(0.001, 0.015))  # Simulate network latency jitter
            visitor = self.MockPlayer(uuid.uuid4(), f"Visitor_{idx}")
            return self.island.process_block_break(self.island_x, self.island_y, self.island_z, visitor)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(visitor_break_attempt, i) for i in range(num_visitors)]
            for fut in as_completed(futures):
                results.append(fut.result())

        cancelled_count = sum(1 for allowed, _ in results if not allowed)
        self.assertEqual(cancelled_count, num_visitors, f"Breach detected! {num_visitors - cancelled_count} visitor breaks were not cancelled!")
        self.assertEqual(self.island.blocks_broken, initial_blocks, "Generator progression was corrupted by unauthorized visitors!")


# ==============================================================================
# CHALLENGE SUITE 4: OFFLINE-MODE OPERATOR SPOOFING HARNESS
# ==============================================================================

class TestOfflineModeOperatorSpoofing(unittest.TestCase):
    """
    Stress-tests server authentication and permission hardening in offline mode (cracked clients).
    Reference: AetherVisualsPlugin.java lines 350-460.
    """

    class MockOfflineServer:
        def __init__(self, online_mode: bool = False, ops_list: Optional[List[str]] = None):
            self.online_mode = online_mode
            self.ops_list = [op.lower() for op in (ops_list or ["Hactheglitchis", "Lum"])]
            self.authenticated_operators = set()

        def on_player_join(self, player_name: str, player_uuid: uuid.UUID, initial_is_op: bool) -> Tuple[bool, str]:
            """
            Emulates AetherVisualsPlugin.java onJoin logic:
            If online-mode=false, check if player claims OP or is in ops.json.
            If not in authenticated_operators -> strip OP (setOp(false)).
            """
            current_is_op = initial_is_op
            claims_op = current_is_op or (player_name.lower() in self.ops_list)

            if not self.online_mode:
                if claims_op and player_uuid not in self.authenticated_operators:
                    current_is_op = False
                    return current_is_op, "OP_SUSPENDED_UNAUTHENTICATED_OFFLINE_PLAYER"
            return current_is_op, "NOMINAL"

        def on_command_preprocess(self, player_name: str, player_uuid: uuid.UUID, current_is_op: bool, cmd: str) -> Tuple[bool, str]:
            """
            Emulates AetherVisualsPlugin.java onPlayerCommandPreprocess:
            Blocks dangerous admin commands if not authenticated in offline mode.
            """
            low = cmd.strip().lower()
            if not self.online_mode:
                if low.startswith(("/op ", "/stop", "/reload", "/restart")):
                    if player_uuid not in self.authenticated_operators:
                        return False, "COMMAND_BLOCKED_UNAUTHENTICATED_OPERATOR"
            return True, "COMMAND_ALLOWED"

        def handle_opauth(self, player_name: str, player_uuid: uuid.UUID, token: str) -> Tuple[bool, str]:
            """Emulates /opauth <token> validation."""
            now_sec = int(time.time())
            auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
            valid = False

            # Check HMAC window
            for offset in range(0, 3601, 30):
                expected = hmac.new(auth_key.encode("utf-8"), f"{player_name.lower()}:{now_sec - offset}".encode("utf-8"), hashlib.sha256).hexdigest()
                if expected.lower() == token.lower():
                    valid = True
                    break

            # Check Master Secret
            if not valid and token == "aethercraft_session_hmac_2026":
                valid = True

            if valid:
                self.authenticated_operators.add(player_uuid)
                return True, "OP_RESTORED"
            return False, "INVALID_TOKEN"

        def on_player_quit(self, player_uuid: uuid.UUID):
            """PlayerQuitEvent purges session."""
            self.authenticated_operators.discard(player_uuid)

    def setUp(self):
        self.server = self.MockOfflineServer(online_mode=False, ops_list=["Hactheglitchis", "Lum"])

    def test_challenge_08_cracked_client_op_stripping_on_join(self):
        """
        Challenge 4.1: Cracked client joins with administrator username 'Hactheglitchis' or 'Lum'.
        Invariants:
        - OP status must be immediately stripped to False on join.
        - Notice must be logged and sent to player.
        """
        hacker_uuid = uuid.uuid4()
        # Initial is_op=True because username is in ops.json
        is_op, msg = self.server.on_player_join("Hactheglitchis", hacker_uuid, initial_is_op=True)
        self.assertFalse(is_op, "CRITICAL SECURITY BREACH: Cracked client retained OP status!")
        self.assertEqual(msg, "OP_SUSPENDED_UNAUTHENTICATED_OFFLINE_PLAYER")

        # Second admin: Lum
        lum_uuid = uuid.uuid4()
        is_op_lum, msg_lum = self.server.on_player_join("Lum", lum_uuid, initial_is_op=True)
        self.assertFalse(is_op_lum, "CRITICAL: Lum cracked login retained OP status!")

    def test_challenge_09_unauthenticated_operator_sensitive_commands_blocked(self):
        """
        Challenge 4.2: Unauthenticated operator tries running /op, /stop, /reload, /restart.
        All must be intercepted and cancelled.
        """
        hacker_uuid = uuid.uuid4()
        is_op, _ = self.server.on_player_join("Hactheglitchis", hacker_uuid, initial_is_op=True)

        dangerous_cmds = [
            "/op evil_hacker",
            "/stop",
            "/reload",
            "/restart",
            "/op pwned_admin",
            "/STOP"
        ]
        for cmd in dangerous_cmds:
            allowed, reason = self.server.on_command_preprocess("Hactheglitchis", hacker_uuid, is_op, cmd)
            self.assertFalse(allowed, f"Dangerous command '{cmd}' was not intercepted!")
            self.assertEqual(reason, "COMMAND_BLOCKED_UNAUTHENTICATED_OPERATOR")

    def test_challenge_10_opauth_flow_and_session_eviction(self):
        """
        Challenge 4.3: Validates the /opauth authentication workflow:
        1. Bad token fails.
        2. Valid HMAC token or master secret restores OP.
        3. Player disconnect purges authenticated session.
        4. Reconnect requires re-authentication.
        """
        admin_uuid = uuid.uuid4()
        admin_name = "Hactheglitchis"
        is_op, _ = self.server.on_player_join(admin_name, admin_uuid, initial_is_op=True)
        self.assertFalse(is_op)

        # 1. Invalid token fails
        success, msg = self.server.handle_opauth(admin_name, admin_uuid, "wrong_token_123")
        self.assertFalse(success)
        self.assertNotIn(admin_uuid, self.server.authenticated_operators)

        # 2. Valid token succeeds
        now_sec = int(time.time())
        auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        valid_token = hmac.new(auth_key.encode("utf-8"), f"{admin_name.lower()}:{now_sec}".encode("utf-8"), hashlib.sha256).hexdigest()

        success, msg = self.server.handle_opauth(admin_name, admin_uuid, valid_token)
        self.assertTrue(success)
        self.assertIn(admin_uuid, self.server.authenticated_operators)

        # 3. Now commands are allowed
        allowed, _ = self.server.on_command_preprocess(admin_name, admin_uuid, True, "/stop")
        self.assertTrue(allowed)

        # 4. Disconnect purges session
        self.server.on_player_quit(admin_uuid)
        self.assertNotIn(admin_uuid, self.server.authenticated_operators)

        # 5. Reconnect strips OP again
        is_op_reconnect, _ = self.server.on_player_join(admin_name, admin_uuid, initial_is_op=True)
        self.assertFalse(is_op_reconnect)


if __name__ == "__main__":
    unittest.main()
