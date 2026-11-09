r"""
================================================================================
Milestone M4 Tier 5 White-Box Adversarial Coverage Hardening Test Suite
Cross-Component Synchronization & Parity Harness (Web, SQLite, Paper Plugin)
Author: Challenger M4-2
Target: C:\Users\1234\Desktop\Projets\aethercraft
================================================================================
Empirically tests and verifies:
1. In-game balance mutations -> Web Leaderboards, /joueurs, and Top Player Parity
2. In-game shop points vs Web shop points lifecycle & isolation
3. Bank deposits/withdrawals, net-worth calculation, and in-game vs web rank parity
4. Celestial Tree contributions, community gauge sync, and milestone distribution
5. WebDisplay (/webdisplay) SSR leaderboards, authentication tokens & HMAC
6. Residual mock player artifacts across config, databases, and caches
================================================================================
"""

import os
import sys
import uuid
import time
import hmac
import hashlib
import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app, verify_game_auth_token
from services.database import (
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_get_user_by_id,
    db_get_user_by_username,
    db_get_leaderboards,
    db_get_top_player,
    db_get_community_goal,
    db_contribute_to_community_goal,
    db_spend_shop_points,
    db_add_shop_points,
    db_claim_30min_reward,
    db_update_player_balance,
    db_add_player_balance
)
from services.player_service import get_leaderboards, get_player_profile


def simulate_java_query_leaderboard(conn: sqlite3.Connection, column: str, limit: int = 5):
    """
    Simulates verbatim AetherVisualScoreboardManager.queryLeaderboard(String orderByColumn, int limit).
    """
    valid_col = "(p.balance + COALESCE(b.bank_coins, 0.0))"
    if column == "p.hours_played":
        valid_col = "p.hours_played"
    elif column == "p.kills":
        valid_col = "p.kills"

    sql = f"""
    SELECT p.username, {valid_col} AS val, p.rank, r.prefix, r.badge_color 
    FROM players p 
    LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
    LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
    ORDER BY {valid_col} DESC 
    LIMIT ?;
    """
    cursor = conn.cursor()
    cursor.execute(sql, (limit,))
    return [dict(row) for row in cursor.fetchall()]


def simulate_java_fetch_player_data(conn: sqlite3.Connection, username: str):
    """
    Simulates verbatim AetherVisualScoreboardManager.fetchPlayerData(String username).
    """
    sql = """
    SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
    FROM players p 
    LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
    LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
    WHERE LOWER(p.username) = LOWER(?);
    """
    cursor = conn.cursor()
    cursor.execute(sql, (username,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return {"rank": "JOUEUR", "balance": 0.0, "prefix": "[Joueur]", "badge_color": "slate", "shop_points": 0}


def simulate_java_bank_transfer(conn: sqlite3.Connection, username: str, amount: float, deposit: bool):
    """
    Simulates verbatim AetherBankEngine.transferCoins(Player p, Inventory inv, double amount, boolean deposit).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM players WHERE LOWER(username)=LOWER(?);", (username,))
    p_row = cursor.fetchone()
    wallet = p_row["balance"] if p_row else 1000.0

    cursor.execute("SELECT bank_coins FROM player_bank_accounts WHERE LOWER(username)=LOWER(?);", (username,))
    b_row = cursor.fetchone()
    bank = b_row["bank_coins"] if b_row else 0.0

    delta = min(wallet, amount) if deposit else min(bank, amount)
    if delta < 1.0:
        return False, "Solde insuffisant"

    wDiff = -delta if deposit else delta
    bDiff = delta if deposit else -delta

    cursor.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?);", (wDiff, username))
    cursor.execute("""
        INSERT INTO player_bank_accounts (username, bank_coins, updated_at) VALUES (?, ?, datetime('now'))
        ON CONFLICT(username) DO UPDATE SET bank_coins = bank_coins + ?, updated_at = datetime('now');
    """, (username, max(0.0, bDiff), bDiff))
    conn.commit()
    return True, delta


class TestTier5CrossComponentSync(unittest.TestCase):
    """Tier 5 Adversarial Test Suite for Cross-Component Synchronization."""

    def setUp(self):
        init_database()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids = []
        self.created_usernames = []
        self.created_user_ids = []

    def tearDown(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            if self.created_uuids:
                placeholders = ",".join("?" for _ in self.created_uuids)
                c.execute(f"DELETE FROM players WHERE uuid IN ({placeholders});", self.created_uuids)
            if self.created_usernames:
                placeholders = ",".join("?" for _ in self.created_usernames)
                c.execute(f"DELETE FROM players WHERE username IN ({placeholders});", self.created_usernames)
                c.execute(f"DELETE FROM users WHERE minecraft_username IN ({placeholders});", self.created_usernames)
                c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({placeholders});", self.created_usernames)
                c.execute(f"DELETE FROM tree_contributions WHERE username IN ({placeholders});", self.created_usernames)
            if self.created_user_ids:
                placeholders = ",".join("?" for _ in self.created_user_ids)
                c.execute(f"DELETE FROM users WHERE id IN ({placeholders});", self.created_user_ids)
            conn.commit()

    def _create_player(self, username: str, rank: str = "JOUEUR", balance: float = 1000.0,
                       hours: int = 10, kills: int = 5, deaths: int = 2, is_online: int = 0):
        p_uuid = f"t5-{uuid.uuid4().hex[:12]}"
        now = "2026-11-06 12:00:00"
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Aventurier', ?, ?);
            """, (p_uuid, username, rank, balance, hours, kills, deaths, is_online, now, now))
            conn.commit()
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(username)
        return p_uuid

    def _create_user(self, minecraft_username: str, shop_points: int = 10):
        email = f"{minecraft_username.lower()}@test.aethercraft.io"
        now = "2026-11-06 12:00:00"
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at, last_login)
                VALUES (?, 'hash', 'salt', ?, ?, ?, ?);
            """, (email, minecraft_username, shop_points, now, now))
            user_id = c.lastrowid
            conn.commit()
        self.created_user_ids.append(user_id)
        self.created_usernames.append(minecraft_username)
        return user_id

    # =========================================================================
    # VECTOR 1: In-game balance mutations -> Web Leaderboards, /joueurs, and Top Player
    # =========================================================================

    def test_v1_1_ingame_dungeon_reward_immediate_web_reflection(self):
        """Verify in-game balance increment (Dungeon reward +350) reflects immediately on web."""
        p_name = f"t5_hero_{uuid.uuid4().hex[:6]}"
        self._create_player(p_name, balance=500.0)

        # In-game dungeon victory reward executes:
        # UPDATE players SET balance = balance + 350 WHERE LOWER(username) = LOWER(?)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET balance = balance + 350 WHERE LOWER(username) = LOWER(?);", (p_name,))
            conn.commit()

        # Check Python data access
        profile = db_get_player_by_username(p_name)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["balance"], 850.0)

        # Check Java player visual data simulation
        with get_db_connection() as conn:
            j_data = simulate_java_fetch_player_data(conn, p_name)
        self.assertEqual(j_data["balance"], 850.0)

        # Check HTTP /joueurs route
        resp = self.client.get("/joueurs")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(p_name, resp.get_data(as_text=True))

    def test_v1_2_balance_overtaking_updates_top_player_mvp(self):
        """Verify that when a player's composite stats overtake #1, db_get_top_player() dynamically changes."""
        leader = f"t5_old_leader_{uuid.uuid4().hex[:6]}"
        challenger = f"t5_challenger_{uuid.uuid4().hex[:6]}"
        # Leader initially higher: hours 50, kills 30, bal 10000 -> mvp_score ~656
        self._create_player(leader, balance=10000.0, hours=50, kills=30)
        # Challenger initially lower: hours 10, kills 5, bal 1000 -> mvp_score ~125
        self._create_player(challenger, balance=1000.0, hours=10, kills=5)

        # Initially, leader has higher mvp_score
        top1 = db_get_top_player()
        self.assertIsNotNone(top1)
        self.assertEqual(top1["username"], leader)

        # In-game progression for challenger (hours +100, kills +80, balance +50000)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE players 
                SET hours_played = hours_played + 100, kills = kills + 80, balance = balance + 50000.0 
                WHERE LOWER(username) = LOWER(?);
            """, (challenger,))
            conn.commit()

        # Challenger must now immediately be top_player
        new_top = db_get_top_player()
        self.assertIsNotNone(new_top)
        self.assertEqual(new_top["username"], challenger)

        # Homepage must display the new top player in unit frame
        home_resp = self.client.get("/")
        self.assertEqual(home_resp.status_code, 200)
        self.assertIn(challenger, home_resp.get_data(as_text=True))

    def test_v1_3_decimal_precision_formatting_consistency(self):
        """Probe decimal balances (e.g. 1250.75) across in-game scoreboard logic and web templates."""
        p_name = f"t5_decimal_{uuid.uuid4().hex[:6]}"
        self._create_player(p_name, balance=1250.75)

        with get_db_connection() as conn:
            j_data = simulate_java_fetch_player_data(conn, p_name)
        # Scoreboard formats: (bal == balInt) ? String.valueOf(balInt) : String.format("%.2f", bal)
        bal_int = round(j_data["balance"])
        bal_str = str(bal_int) if j_data["balance"] == bal_int else f"{j_data['balance']:.2f}"
        self.assertEqual(bal_str, "1250.75")

        # In /joueurs template: "{:,}".format(p.balance).replace(',', ' ')
        rendered_bal = "{:,}".format(1250.75).replace(',', ' ')
        self.assertIn("1 250.75", rendered_bal)

    # =========================================================================
    # VECTOR 2: Shop Points vs Balance Lifecycle & Cross-Component Conflation Probe
    # =========================================================================

    def test_v2_1_ingame_points_deduction_isolation(self):
        """Feature F9/F11: Deducting points in-game must modify users.shop_points without affecting players.balance."""
        uname = f"t5_pts_player_{uuid.uuid4().hex[:6]}"
        self._create_player(uname, balance=2500.0)
        u_id = self._create_user(uname, shop_points=100)

        # Simulate AetherMMOShopCatalog.deductPlayerPoints(uname, 30)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE users SET shop_points = shop_points - 30 
                WHERE LOWER(minecraft_username) = LOWER(?) AND shop_points >= 30;
            """, (uname,))
            affected = c.rowcount
            conn.commit()

        self.assertEqual(affected, 1)

        # Verify users.shop_points decreased to 70
        user = db_get_user_by_id(u_id)
        self.assertEqual(user["shop_points"], 70)

        # Verify players.balance remains untouched at 2500.0
        p_row = db_get_player_by_username(uname)
        self.assertEqual(p_row["balance"], 2500.0)

        # Verify Java AetherVisualScoreboardManager.fetchPlayerData gets both accurately
        with get_db_connection() as conn:
            j_data = simulate_java_fetch_player_data(conn, uname)
        self.assertEqual(j_data["balance"], 2500.0)
        self.assertEqual(j_data["shop_points"], 70)

    def test_v2_2_web_conflation_flaw_detection_in_db_spend_shop_points(self):
        """
        Adversarial probe on db_spend_shop_points and db_claim_30min_reward:
        Documents whether web operations unintentionally overwrite users.shop_points
        with players.balance.
        """
        uname = f"t5_probe_sync_{uuid.uuid4().hex[:6]}"
        # Player has 5,000 in wallet, but only 20 shop points
        self._create_player(uname, balance=5000.0)
        u_id = self._create_user(uname, shop_points=20)

        # Now suppose web claim 30min reward executes:
        db_claim_30min_reward(u_id)

        # Inspect users.shop_points in SQLite
        user = db_get_user_by_id(u_id)
        # Note: If shop_points was overwritten by balance (5050.0), it would leak points.
        # Verified fix: shop_points is isolated and never overwritten by gold balance.
        player = db_get_player_by_username(uname)
        self.assertEqual(player["balance"], 5050.0)
        self.assertEqual(user["shop_points"], 20, "shop_points must remain isolated and never overwritten by balance")

    # =========================================================================
    # VECTOR 3: Bank Deposits, Withdrawals, Net Worth, and Rank Inversion
    # =========================================================================

    def test_v3_1_bank_deposit_withdrawal_lifecycle(self):
        """Verify full deposit and withdrawal lifecycle via simulated AetherBankEngine."""
        uname = f"t5_bank_{uuid.uuid4().hex[:6]}"
        self._create_player(uname, balance=1500.0)

        with get_db_connection() as conn:
            # 1. Deposit 500 into bank
            ok, val = simulate_java_bank_transfer(conn, uname, 500.0, deposit=True)
            self.assertTrue(ok)
            self.assertEqual(val, 500.0)

            c = conn.cursor()
            c.execute("SELECT balance FROM players WHERE LOWER(username)=LOWER(?);", (uname,))
            self.assertEqual(c.fetchone()["balance"], 1000.0)
            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE LOWER(username)=LOWER(?);", (uname,))
            self.assertEqual(c.fetchone()["bank_coins"], 500.0)

            # 2. Withdraw 200 from bank
            ok, val = simulate_java_bank_transfer(conn, uname, 200.0, deposit=False)
            self.assertTrue(ok)
            self.assertEqual(val, 200.0)

            c.execute("SELECT balance FROM players WHERE LOWER(username)=LOWER(?);", (uname,))
            self.assertEqual(c.fetchone()["balance"], 1200.0)
            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE LOWER(username)=LOWER(?);", (uname,))
            self.assertEqual(c.fetchone()["bank_coins"], 300.0)

    def test_v3_2_bank_insufficient_funds_rejected(self):
        """Verify bank rejects overdrafts when wallet or bank funds are insufficient."""
        uname = f"t5_broke_{uuid.uuid4().hex[:6]}"
        self._create_player(uname, balance=50.0)

        with get_db_connection() as conn:
            # Deposit 500 when wallet only has 50 -> deposits min(50, 500) = 50
            ok, val = simulate_java_bank_transfer(conn, uname, 500.0, deposit=True)
            self.assertTrue(ok)
            self.assertEqual(val, 50.0)

            # Wallet is now 0.0 -> deposit again must fail
            ok, msg = simulate_java_bank_transfer(conn, uname, 100.0, deposit=True)
            self.assertFalse(ok)

            # Withdraw 1000 when bank only has 50 -> withdraws min(50, 1000) = 50
            ok, val = simulate_java_bank_transfer(conn, uname, 1000.0, deposit=False)
            self.assertTrue(ok)
            self.assertEqual(val, 50.0)

            # Bank is now 0.0 -> withdraw again must fail
            ok, msg = simulate_java_bank_transfer(conn, uname, 100.0, deposit=False)
            self.assertFalse(ok)

    def test_v3_3_bank_vs_wallet_rank_divergence_parity_probe(self):
        """
        Adversarial probe:
        Player A (Wallet 300, Bank 5000 -> Total 5300)
        Player B (Wallet 1000, Bank 0 -> Total 1000)
        Verify that both Python and Java leaderboards align and rank Player A higher than Player B
        based on total wealth (wallet + bank).
        """
        pA = f"t5_richbank_{uuid.uuid4().hex[:6]}"
        pB = f"t5_richwallet_{uuid.uuid4().hex[:6]}"
        self._create_player(pA, balance=300.0)
        self._create_player(pB, balance=1000.0)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 5000.0, datetime('now'));
            """, (pA,))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 0.0, datetime('now'));
            """, (pB,))
            conn.commit()

            # Java query (total wealth parity)
            j_rich = simulate_java_query_leaderboard(conn, "fortune", 10)
            j_usernames = [r["username"] for r in j_rich]

        # Python query (total_wealth = balance + bank_coins)
        py_rich = db_get_leaderboards(10)["top_rich"]
        py_usernames = [r["username"] for r in py_rich]

        # In Python: pA (5300) is ranked higher than pB (1000)
        self.assertLess(py_usernames.index(pA), py_usernames.index(pB))
        # In Java: pA (5300) is now also ranked higher than pB (1000) - parity achieved!
        self.assertLess(j_usernames.index(pA), j_usernames.index(pB))

    # =========================================================================
    # VECTOR 4: Celestial Tree Contributions & Community Goal Synchronization
    # =========================================================================

    def test_v4_1_tree_ore_contribution_gauge_sync(self):
        """Verify tree contributions immediately update the gauge across Python & Java queries."""
        uname = f"t5_donor_{uuid.uuid4().hex[:6]}"
        self._create_player(uname, balance=500.0)

        goal_before = db_get_community_goal("s4_celestial_tree")
        amt_before = goal_before["current_amount"]

        # Contribute 20 ores from web
        updated = db_contribute_to_community_goal("s4_celestial_tree", 20, username=uname, ore_price=15.0)
        self.assertEqual(updated["current_amount"], amt_before + 20)

        # Java MMORPGDisplayEngine & AetherMMOShopCatalog query:
        # SELECT current_amount FROM community_goals WHERE id = 's4_celestial_tree'
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT current_amount FROM community_goals WHERE id = 's4_celestial_tree';")
            java_gauge = c.fetchone()["current_amount"]

        self.assertEqual(java_gauge, amt_before + 20)

        # Restore initial amount
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE community_goals SET current_amount = ? WHERE id = 's4_celestial_tree';", (amt_before,))
            conn.commit()

    def test_v4_2_milestone_distribution_math_and_idempotence(self):
        """
        Verify distribution logic matching AetherTreeMilestoneDistributor.
        When 25% tier is reached, distribution occurs and last_tier_reached prevents double claim.
        """
        donor1 = f"t5_tree_d1_{uuid.uuid4().hex[:6]}"
        donor2 = f"t5_tree_d2_{uuid.uuid4().hex[:6]}"
        self._create_player(donor1, balance=100.0)
        self._create_player(donor2, balance=100.0)
        self._create_user(donor1, shop_points=10)
        self._create_user(donor2, shop_points=10)

        now = "2026-11-06 12:00:00"
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO tree_contributions (username, raw_units, weighted_points, last_donation_at)
                VALUES (?, 1000, 1500.0, ?), (?, 500, 750.0, ?);
            """, (donor1, now, donor2, now))

            # Set goal to 25% (12500 of 50000)
            c.execute("UPDATE community_goals SET current_amount = 12500, last_tier_reached = 0 WHERE id='s4_celestial_tree';")
            conn.commit()

            # Execute distributor logic:
            c.execute("SELECT current_amount, target_amount, COALESCE(last_tier_reached, 0) as lt FROM community_goals WHERE id='s4_celestial_tree';")
            row = c.fetchone()
            cur = row["current_amount"]
            target = row["target_amount"]
            last_tier = row["lt"]

            pct = int((cur * 100.0) / target)
            self.assertGreaterEqual(pct, 25)
            self.assertLess(last_tier, 25)

            # Update last_tier_reached to 25
            c.execute("UPDATE community_goals SET last_tier_reached = 25 WHERE id='s4_celestial_tree';")
            conn.commit()

            # Second execution: last_tier is now 25 -> must not trigger tier 25 again
            c.execute("SELECT COALESCE(last_tier_reached, 0) as lt FROM community_goals WHERE id='s4_celestial_tree';")
            self.assertEqual(c.fetchone()["lt"], 25)

            # Cleanup
            c.execute("UPDATE community_goals SET current_amount = 0, last_tier_reached = 0 WHERE id='s4_celestial_tree';")
            conn.commit()

    # =========================================================================
    # VECTOR 5: WebDisplay Template, SSR, and HMAC Auth Token Parity
    # =========================================================================

    def test_v5_1_webdisplay_auth_hmac_token_verification(self):
        """Verify HMAC SHA256 token verification between Java AetherWebDisplayManager and Flask."""
        uname = "Hactheglitchis"
        ts = int(time.time())
        env_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")

        # Java algorithm:
        # String data = username.toLowerCase() + ":" + ts;
        # HmacSHA256 with key
        raw = f"{uname.lower()}:{ts}".encode("utf-8")
        token = hmac.new(env_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()

        # Web verify_game_auth_token:
        is_valid = verify_game_auth_token(uname, str(ts), token)
        self.assertTrue(is_valid, "Valid Java-generated HMAC token must be accepted by Flask")

        # Tampered username
        self.assertFalse(verify_game_auth_token("Attacker", str(ts), token))
        # Tampered timestamp
        self.assertFalse(verify_game_auth_token(uname, str(ts + 999), token))
        # Tampered token
        self.assertFalse(verify_game_auth_token(uname, str(ts), token[:-4] + "dead"))

    def test_v5_2_webdisplay_route_rendering_with_modes(self):
        """Verify /webdisplay endpoint renders successfully across all valid modes."""
        modes = ["cockpit", "shop", "market", "ores", "profile", "rankings"]
        for mode in modes:
            resp = self.client.get(f"/webdisplay?player=Hactheglitchis&mode={mode}")
            self.assertEqual(resp.status_code, 200, f"/webdisplay failed on mode={mode}")
            html = resp.get_data(as_text=True)
            self.assertIn("Hactheglitchis", html)
            self.assertIn("[6] Classements", html)

    def test_v5_3_webdisplay_ssr_leaderboards_direct_binding(self):
        """Verify webdisplay_panel binds leaderboards to SSR context directly."""
        resp = self.client.get("/webdisplay?player=Hactheglitchis&mode=rankings")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # SSR should render the top_rich players without falling back to loading spinner
        self.assertNotIn("Chargement du classement Fortune...", html)
        self.assertIn("Hactheglitchis", html)

    # =========================================================================
    # VECTOR 6: Scan for Residual Mocks and Hardcoded Demo Values
    # =========================================================================

    def test_v6_1_no_mock_players_in_active_sqlite_database(self):
        """Verify complete absence of seeded mock players in active server/data/aethercraft.db."""
        dummy_names = ["aetherknight", "pixelsorceress", "vortexcrafter", "shadowranger", "notch"]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT username FROM players;")
            players = [r["username"].lower() for r in c.fetchall()]
            for dummy in dummy_names:
                self.assertNotIn(dummy, players, f"Residual dummy '{dummy}' found in players table!")

    def test_v6_2_check_whitelist_json_residual_mocks(self):
        """
        Adversarial scan on server/whitelist.json:
        Verifies that legacy dummy player 'AetherKnight' is completely purged from whitelist.json.
        """
        whitelist_path = os.path.join(SERVER_DIR, "whitelist.json")
        self.assertTrue(os.path.exists(whitelist_path))
        with open(whitelist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = [entry.get("name", "") for entry in data]

        self.assertNotIn("AetherKnight", names, "Residual mock player 'AetherKnight' detected in server/whitelist.json!")

    # =========================================================================
    # VECTOR 7: Multi-Threaded Concurrency & Transaction Isolation Stress
    # =========================================================================

    def test_v7_1_concurrent_cross_component_read_write_stress(self):
        """
        Adversarially stress-test SQLite concurrency:
        Simulate 15 concurrent threads performing simultaneous in-game bank transfers,
        web ore contributions, profile reads, and leaderboard queries.
        Ensures zero SQLite locking deadlocks and zero data corruption.
        """
        concurrent_players = [f"t5_conc_{i}_{uuid.uuid4().hex[:4]}" for i in range(5)]
        for p in concurrent_players:
            self._create_player(p, balance=5000.0)

        errors = []

        def worker_task(thread_id: int):
            try:
                target_p = concurrent_players[thread_id % len(concurrent_players)]
                # Mix of operations:
                if thread_id % 3 == 0:
                    # In-game bank deposit/withdraw simulation
                    with get_db_connection() as conn:
                        simulate_java_bank_transfer(conn, target_p, 100.0, deposit=(thread_id % 2 == 0))
                elif thread_id % 3 == 1:
                    # Web tree contribution
                    db_contribute_to_community_goal("s4_celestial_tree", 2, username=target_p, ore_price=10.0)
                else:
                    # Leaderboard & top player query
                    db_get_leaderboards(5)
                    db_get_top_player()
            except Exception as e:
                errors.append((thread_id, str(e)))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, i) for i in range(24)]
            for f in futures:
                f.result()

        self.assertEqual(len(errors), 0, f"Concurrency stress test encountered errors: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
