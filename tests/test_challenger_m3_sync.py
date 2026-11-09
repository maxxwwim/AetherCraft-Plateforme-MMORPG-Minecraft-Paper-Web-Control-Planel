"""
================================================================================
Empirical Challenger Test Suite: Milestone M3 Cross-Component Sync & Integrity
Target: Aethercraft Paper Server Visuals & Flask Web Data Sync
Author: Challenger M3-2
================================================================================
Empirically stress-tests:
1. Java SQL queries (AetherVisualScoreboardManager.java) vs Python db_get_leaderboards() & /joueurs.
2. Canonical rankings consistency on active database.
3. Multi-player synthetic dataset synchronization.
4. Edge cases & divergence stress testing (bank balances, ties, kd_ratio).
5. Comprehensive scan of all 50 Java source files for dummy mocks/stubs.
6. AetherVisuals.jar build verification.
7. WebDisplay template bindings.
================================================================================
"""

import os
import sys
import glob
import re
import zipfile
import sqlite3
import unittest
from typing import List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import get_db_connection, db_get_leaderboards, db_get_player_by_username
from services.player_service import get_leaderboards

JAVA_SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
JAR_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")


def simulate_java_query(conn: sqlite3.Connection, order_by_col: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Simulates verbatim the SQL query executed by Java AetherVisualScoreboardManager.queryLeaderboard:
    SELECT p.username, [col] AS val, p.rank, r.prefix, r.badge_color
    FROM players p
    LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id)
    ORDER BY [col] DESC
    LIMIT ?
    """
    valid_col = "p.balance"
    if order_by_col == "p.hours_played":
        valid_col = "p.hours_played"
    elif order_by_col == "p.kills":
        valid_col = "p.kills"

    sql = (
        f"SELECT p.username, {valid_col} AS val, p.rank, r.prefix, r.badge_color "
        f"FROM players p "
        f"LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) "
        f"ORDER BY {valid_col} DESC "
        f"LIMIT ?"
    )
    cursor = conn.cursor()
    cursor.execute(sql, (limit,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "username": r[0] if isinstance(r, (tuple, list)) else r["username"],
            "val": r[1] if isinstance(r, (tuple, list)) else r["val"],
            "rank": r[2] if isinstance(r, (tuple, list)) else r["rank"],
            "prefix": r[3] if isinstance(r, (tuple, list)) else r["prefix"],
            "badge_color": r[4] if isinstance(r, (tuple, list)) else r["badge_color"],
        })
    return results


class TestMilestone3CrossSyncChallenge(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # --------------------------------------------------------------------------
    # 1. Active Database Synchronization
    # --------------------------------------------------------------------------
    def test_01_active_db_rankings_strict_match(self):
        """
        Verify that rankings on active server/data/aethercraft.db match strictly
        between Java queries and Python db_get_leaderboards().
        """
        py_lbs = db_get_leaderboards(5)
        with get_db_connection() as conn:
            java_wealth = simulate_java_query(conn, "p.balance", 5)
            java_hours = simulate_java_query(conn, "p.hours_played", 5)
            java_kills = simulate_java_query(conn, "p.kills", 5)

        # 1. Wealth
        py_rich = py_lbs.get("top_rich", [])
        min_len = min(len(py_rich), len(java_wealth))
        for i in range(min_len):
            self.assertEqual(
                py_rich[i]["username"], java_wealth[i]["username"],
                f"Active DB Wealth mismatch at rank #{i+1}: Python={py_rich[i]['username']}, Java={java_wealth[i]['username']}"
            )
            self.assertEqual(
                float(py_rich[i]["balance"]), float(java_wealth[i]["val"]),
                f"Active DB Wealth value mismatch at rank #{i+1}"
            )

        # 2. Hours / Playtime
        py_hours = py_lbs.get("top_hours", [])
        min_len = min(len(py_hours), len(java_hours))
        for i in range(min_len):
            self.assertEqual(
                py_hours[i]["username"], java_hours[i]["username"],
                f"Active DB Playtime mismatch at rank #{i+1}: Python={py_hours[i]['username']}, Java={java_hours[i]['username']}"
            )
            self.assertEqual(
                int(py_hours[i]["hours_played"]), int(java_hours[i]["val"]),
                f"Active DB Playtime value mismatch at rank #{i+1}"
            )

        # 3. Kills
        py_kills = py_lbs.get("top_kills", [])
        min_len = min(len(py_kills), len(java_kills))
        for i in range(min_len):
            self.assertEqual(
                py_kills[i]["username"], java_kills[i]["username"],
                f"Active DB Kills mismatch at rank #{i+1}: Python={py_kills[i]['username']}, Java={java_kills[i]['username']}"
            )
            self.assertEqual(
                int(py_kills[i]["kills"]), int(java_kills[i]["val"]),
                f"Active DB Kills value mismatch at rank #{i+1}"
            )

    # --------------------------------------------------------------------------
    # 2. Synthetic Multi-Player Dataset Synchronization
    # --------------------------------------------------------------------------
    def test_02_synthetic_multi_player_cross_sync(self):
        """
        Inserts 5 synthetic test players with strictly distinct, monotonically decreasing
        metrics, verifies Java queries and Python queries match identically rank-for-rank.
        """
        synthetic_players = [
            ("test_sync_p1", "VIP", 50000.0, 120, 45, 10),
            ("test_sync_p2", "AETHER", 35000.0, 95, 30, 15),
            ("test_sync_p3", "TITAN", 20000.0, 70, 20, 20),
            ("test_sync_p4", "CHAMPION", 10000.0, 40, 10, 5),
            ("test_sync_p5", "JOUEUR", 2500.0, 15, 5, 2),
        ]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            for uname, rank, bal, hrs, k, d in synthetic_players:
                cursor.execute("""
                    INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'TestGuild', '2026-11-06', '2026-11-06')
                """, (f"uuid-{uname}", uname, rank, bal, hrs, k, d))
            conn.commit()

        try:
            py_lbs = db_get_leaderboards(5)
            with get_db_connection() as conn:
                j_wealth = simulate_java_query(conn, "p.balance", 5)
                j_hours = simulate_java_query(conn, "p.hours_played", 5)
                j_kills = simulate_java_query(conn, "p.kills", 5)

            # Check Wealth
            for i in range(5):
                self.assertEqual(py_lbs["top_rich"][i]["username"], j_wealth[i]["username"])
                self.assertEqual(py_lbs["top_rich"][i]["balance"], j_wealth[i]["val"])

            # Check Hours
            for i in range(5):
                self.assertEqual(py_lbs["top_hours"][i]["username"], j_hours[i]["username"])
                self.assertEqual(py_lbs["top_hours"][i]["hours_played"], j_hours[i]["val"])

            # Check Kills
            for i in range(5):
                self.assertEqual(py_lbs["top_kills"][i]["username"], j_kills[i]["username"])
                self.assertEqual(py_lbs["top_kills"][i]["kills"], j_kills[i]["val"])

            # Verify Flask /joueurs HTTP response renders the exact #1 player
            resp = self.client.get("/joueurs")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("test_sync_p1", resp.get_data(as_text=True))

        finally:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for uname, _, _, _, _, _ in synthetic_players:
                    cursor.execute("DELETE FROM players WHERE username = ?", (uname,))
                conn.commit()

    # --------------------------------------------------------------------------
    # 3. Stress-Test: Bank Coins Divergence Analysis
    # --------------------------------------------------------------------------
    def test_03_stress_test_bank_coins_divergence(self):
        """
        Adversarial test analyzing behavior when players have bank deposits.
        Documents whether total_wealth ordering in Python vs wallet balance in Java
        causes rank inversions.
        """
        p_wallet = ("test_bank_wallet_rich", "JOUEUR", 1000.0, 0.0)  # Wallet: 1000, Bank: 0
        p_bank = ("test_bank_bank_rich", "JOUEUR", 200.0, 5000.0)    # Wallet: 200, Bank: 5000 (Total: 5200)

        with get_db_connection() as conn:
            c = conn.cursor()
            for uname, rank, bal, bank_val in [p_wallet, p_bank]:
                c.execute("""
                    INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                    VALUES (?, ?, ?, ?, 10, 5, 2, 0, 'Guild', '2026-11-06', '2026-11-06')
                """, (f"uuid-{uname}", uname, rank, bal))
                c.execute("""
                    INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (uname, bank_val))
            conn.commit()

        try:
            py_lbs = db_get_leaderboards(5)
            with get_db_connection() as conn:
                j_wealth = simulate_java_query(conn, "p.balance", 5)

            py_names = [p["username"] for p in py_lbs["top_rich"]]
            j_names = [p["username"] for p in j_wealth]

            # In Python, p_bank is #1 because total_wealth = 5200 > 1000
            self.assertIn("test_bank_bank_rich", py_names[:2])
            # In Java, p_wallet is #1 because balance = 1000 > 200
            self.assertIn("test_bank_wallet_rich", j_names[:2])

            # Document the design difference:
            # Java /top fortune displays wallet balance:
            j_top1 = j_names[0]
            # Python displays total_wealth ordering:
            py_top1 = py_names[0]
            if j_top1 != py_top1:
                print(f"\n[INFO: DESIGN OBSERVATION] Bank coins creates divergence between Java wallet (/top) and Python total_wealth (/joueurs):")
                print(f"  Java Top #1: {j_top1} (Wallet Balance: {j_wealth[0]['val']})")
                print(f"  Python Top #1: {py_top1} (Total Wealth: {py_lbs['top_rich'][0].get('total_wealth')})")

        finally:
            with get_db_connection() as conn:
                c = conn.cursor()
                for uname, _, _, _ in [p_wallet, p_bank]:
                    c.execute("DELETE FROM players WHERE username = ?", (uname,))
                    c.execute("DELETE FROM player_bank_accounts WHERE username = ?", (uname,))
                conn.commit()

    # --------------------------------------------------------------------------
    # 4. Stress-Test: Kills & K/D Ratio Tie-Break Analysis
    # --------------------------------------------------------------------------
    def test_04_stress_test_kills_tie_break(self):
        """
        Adversarial test: two players with identical kills (25) but different deaths (1 vs 10).
        Python specifies secondary order: ORDER BY p.kills DESC, kd_ratio DESC.
        Java specifies: ORDER BY p.kills DESC.
        """
        p_high_kd = ("test_kd_high", "VIP", 100.0, 10, 25, 1)   # kd = 25.0
        p_low_kd = ("test_kd_low", "VIP", 100.0, 10, 25, 10)    # kd = 2.5

        with get_db_connection() as conn:
            c = conn.cursor()
            for uname, rank, bal, hrs, k, d in [p_high_kd, p_low_kd]:
                c.execute("""
                    INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'PvPGuild', '2026-11-06', '2026-11-06')
                """, (f"uuid-{uname}", uname, rank, bal, hrs, k, d))
            conn.commit()

        try:
            py_lbs = db_get_leaderboards(5)
            top_kills_py = [p["username"] for p in py_lbs["top_kills"]]
            # Python must place high_kd before low_kd due to secondary sort
            idx_high = top_kills_py.index("test_kd_high")
            idx_low = top_kills_py.index("test_kd_low")
            self.assertLess(idx_high, idx_low, "Python must rank higher K/D first on kill ties")

        finally:
            with get_db_connection() as conn:
                c = conn.cursor()
                for uname, _, _, _, _, _ in [p_high_kd, p_low_kd]:
                    c.execute("DELETE FROM players WHERE username = ?", (uname,))
                conn.commit()

    # --------------------------------------------------------------------------
    # 5. Scan All 50 Java Source Files for Dummy Mocks or Fallbacks
    # --------------------------------------------------------------------------
    def test_05_comprehensive_java_source_mock_scan(self):
        """
        Thoroughly inspect all .java files under AetherVisuals/src/io/aethercraft/visuals/
        for forbidden mock patterns, dummy players, hardcoded UUIDs, or fake return fallbacks.
        """
        java_files = glob.glob(os.path.join(JAVA_SRC_DIR, "*.java"))
        self.assertGreaterEqual(len(java_files), 50, f"Expected at least 50 Java files, found {len(java_files)}")

        forbidden_patterns = [
            (r'return\s+100\s*;', "Hardcoded return 100 fallback"),
            (r'return\s+10\s*;', "Hardcoded return 10 fallback"),
            (r'AetherKnight', "Legacy mock player AetherKnight"),
            (r'00000000-0000-0000-0000-000000000000', "Dummy zero UUID"),
            (r'player_balances', "Nonexistent table player_balances query"),
            (r'jdbc:sqlite:server/data/aethercraft\.db', "Relative hardcoded JDBC path"),
        ]

        violations = []
        for fpath in java_files:
            fname = os.path.basename(fpath)
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for line_no, line in enumerate(lines, 1):
                # Ignore comments
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue

                for pat, desc in forbidden_patterns:
                    if re.search(pat, line):
                        # Exclude legitimate occurrences (e.g. if a constant or comment)
                        violations.append(f"{fname}:{line_no} [{desc}] -> {stripped}")

        self.assertEqual(violations, [], f"Forbidden mock patterns detected in Java sources:\n" + "\n".join(violations))

    # --------------------------------------------------------------------------
    # 6. Plugin JAR Integrity and Entry Point Verification
    # --------------------------------------------------------------------------
    def test_06_plugin_jar_integrity_and_commands(self):
        """
        Verify AetherVisuals.jar exists, contains plugin.yml with required commands,
        and contains bytecode for key Milestone M3 classes.
        """
        self.assertTrue(os.path.exists(JAR_PATH), f"JAR does not exist at {JAR_PATH}")
        self.assertGreater(os.path.getsize(JAR_PATH), 500_000, "JAR must be > 500KB")

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = set(z.namelist())
            self.assertIn("plugin.yml", names)
            self.assertIn("io/aethercraft/visuals/AetherVisualScoreboardManager.class", names)
            self.assertIn("io/aethercraft/visuals/AetherCommandExecutor.class", names)
            self.assertIn("io/aethercraft/visuals/AetherTabCompleter.class", names)
            self.assertIn("io/aethercraft/visuals/AetherVisualsPlugin.class", names)

            yml = z.read("plugin.yml").decode("utf-8")
            self.assertIn("top:", yml)
            self.assertIn("baltop", yml)
            self.assertIn("classement", yml)

    # --------------------------------------------------------------------------
    # 7. WebDisplay Template Bindings
    # --------------------------------------------------------------------------
    def test_07_webdisplay_template_bindings(self):
        """
        Verify webdisplay.html contains tab [6] Classements, TOP FORTUNE,
        TOP TEMPS DE JEU, and dynamic bindings.
        """
        tmpl_path = os.path.join(WEB_DIR, "templates", "webdisplay.html")
        with open(tmpl_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("[6] Classements", html)
        self.assertIn("data-shortcut=\"6\"", html)
        self.assertIn("TOP FORTUNE", html)
        self.assertIn("TOP TEMPS DE JEU", html)
        self.assertIn("leaderboards.top_rich", html)
        self.assertIn("leaderboards.top_hours", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
