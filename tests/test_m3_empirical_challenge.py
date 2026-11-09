"""
================================================================================
Milestone M3 Empirical Challenge Test Harness
================================================================================
Empirically stress-tests:
1. Direct execution of all SQL queries used in Paper Java classes on aethercraft.db
2. Edge cases: 0 balance, unmapped rank, non-existent player, special chars/SQL injection
3. Tie-breaking behavior in rankings
4. Shop deduction constraints (preventing negative balance)
5. Comprehensive AetherVisuals.jar bytecode & packaging verification (50 classes, manifest, plugin.yml)
6. Jinja2 rendering of webdisplay.html with edge cases and XSS resilience
================================================================================
"""

import os
import sys
import unittest
import sqlite3
import zipfile
import jinja2

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")
JAR_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")
WEBDISPLAY_HTML = os.path.join(PROJECT_ROOT, "web", "templates", "webdisplay.html")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "web", "templates")


class TestM3DatabaseProbes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DB_PATH)
        cls.db.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.cursor = self.db.cursor()
        # Create a savepoint for isolation so we don't dirty the live DB
        self.cursor.execute("SAVEPOINT m3_probe_sp")

    def tearDown(self):
        self.cursor.execute("ROLLBACK TO SAVEPOINT m3_probe_sp")
        self.cursor.execute("RELEASE SAVEPOINT m3_probe_sp")

    def test_query_existing_player_nominal(self):
        """Verify nominal player lookup across players, ranks, and users."""
        sql = """
        SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
        WHERE LOWER(p.username) = LOWER(?)
        """
        row = self.cursor.execute(sql, ("Hactheglitchis",)).fetchone()
        self.assertIsNotNone(row, "Player Hactheglitchis should exist in database")
        self.assertIsInstance(row["balance"], (int, float))
        self.assertGreaterEqual(row["balance"], 0)

    def test_query_non_existent_player(self):
        """Querying a non-existent player must return None without raising SQLite errors."""
        sql = """
        SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
        WHERE LOWER(p.username) = LOWER(?)
        """
        row = self.cursor.execute(sql, ("GhostNonExistentPlayer_404",)).fetchone()
        self.assertIsNone(row, "Non-existent player query must return None")

    def test_query_player_with_zero_balance(self):
        """Edge case: player with exactly 0.0 balance."""
        self.cursor.execute("""
            INSERT INTO players (uuid, username, balance, hours_played, kills, deaths, is_online, guild, rank, first_join, last_seen)
            VALUES ('test-zero-bal-uuid', 'ZeroBalanceGuy', 0.0, 10, 5, 1, 0, 'None', 'JOUEUR', datetime('now'), datetime('now'))
        """)
        sql = """
        SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
        WHERE LOWER(p.username) = LOWER(?)
        """
        row = self.cursor.execute(sql, ("ZeroBalanceGuy",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["balance"], 0.0)
        self.assertEqual(row["shop_points"], 0)

    def test_query_player_with_unmapped_rank(self):
        """Edge case: player with an unmapped rank string not present in the ranks table."""
        self.cursor.execute("""
            INSERT INTO players (uuid, username, balance, hours_played, kills, deaths, is_online, guild, rank, first_join, last_seen)
            VALUES ('test-unmapped-rank-uuid', 'UnmappedRankGuy', 1500.0, 12, 8, 2, 0, 'None', 'UNKNOWN_RANK_TIER', datetime('now'), datetime('now'))
        """)
        sql = """
        SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
        WHERE LOWER(p.username) = LOWER(?)
        """
        row = self.cursor.execute(sql, ("UnmappedRankGuy",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["rank"], "UNKNOWN_RANK_TIER")
        self.assertIsNone(row["prefix"], "Prefix must be NULL when rank is unmapped in ranks table")
        self.assertIsNone(row["badge_color"], "badge_color must be NULL when rank is unmapped in ranks table")

    def test_query_special_characters_and_sql_injection_defense(self):
        """Edge case: usernames with single quotes, semicolons, dashes, and unicode."""
        dangerous_names = [
            "O'Connor",
            "'; DROP TABLE players; --",
            "Admin' OR '1'='1",
            "Player With Spaces",
            "Étienne_Céleste",
            "player.dot.name"
        ]
        sql = """
        SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) 
        WHERE LOWER(p.username) = LOWER(?)
        """
        for name in dangerous_names:
            try:
                row = self.cursor.execute(sql, (name,)).fetchone()
                # Should return None safely without syntax error or table drop
                self.assertIsNone(row)
            except sqlite3.OperationalError as e:
                self.fail(f"Parameterized query failed on dangerous name '{name}': {e}")

    def test_leaderboard_sorting_and_ties(self):
        """Stress-test: ranking sorting and behavior when two players have identical balance."""
        self.cursor.execute("""
            INSERT INTO players (uuid, username, balance, hours_played, kills, deaths, is_online, guild, rank, first_join, last_seen)
            VALUES 
            ('tie-uuid-1', 'TiePlayerA', 7777.0, 50, 10, 0, 0, 'None', 'VIP', datetime('now'), datetime('now')),
            ('tie-uuid-2', 'TiePlayerB', 7777.0, 60, 20, 0, 0, 'None', 'TITAN', datetime('now'), datetime('now')),
            ('tie-uuid-3', 'TiePlayerC', 9999.0, 70, 30, 0, 0, 'None', 'AETHER', datetime('now'), datetime('now'))
        """)
        sql = """
        SELECT p.username, p.balance AS val, p.rank, r.prefix, r.badge_color 
        FROM players p 
        LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) 
        ORDER BY p.balance DESC 
        LIMIT ?
        """
        rows = self.cursor.execute(sql, (3,)).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["username"], "TiePlayerC")
        self.assertEqual(rows[0]["val"], 9999.0)
        # Both tied players must have 7777.0
        self.assertEqual(rows[1]["val"], 7777.0)
        self.assertEqual(rows[2]["val"], 7777.0)
        usernames = {rows[1]["username"], rows[2]["username"]}
        self.assertEqual(usernames, {"TiePlayerA", "TiePlayerB"})

    def test_shop_deduct_points_atomic_constraint(self):
        """Stress-test: AetherMMOShopCatalog deductPlayerPoints SQL logic."""
        # Insert test user with 50 points
        self.cursor.execute("""
            INSERT INTO users (id, email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at)
            VALUES (99999, 'buyer@test.io', 'hash', 'salt', 'TestBuyer', 50, 0, datetime('now'))
        """)

        deduct_sql = """
        UPDATE users 
        SET shop_points = shop_points - ? 
        WHERE LOWER(minecraft_username) = LOWER(?) AND shop_points >= ?
        """

        # 1. Deduct 30 points (Affordable) -> should succeed
        self.cursor.execute(deduct_sql, (30, "TestBuyer", 30))
        self.assertEqual(self.cursor.rowcount, 1)

        # Check remaining points
        row = self.cursor.execute("SELECT shop_points FROM users WHERE id = 99999").fetchone()
        self.assertEqual(row["shop_points"], 20)

        # 2. Deduct 25 points (Insufficient, only 20 left) -> should affect 0 rows
        self.cursor.execute(deduct_sql, (25, "TestBuyer", 25))
        self.assertEqual(self.cursor.rowcount, 0, "Deduction must fail when balance is insufficient")

        # Verify balance remains unchanged
        row = self.cursor.execute("SELECT shop_points FROM users WHERE id = 99999").fetchone()
        self.assertEqual(row["shop_points"], 20, "Balance must not have gone negative")

    def test_dungeon_reward_victory_sql(self):
        """Stress-test: DungeonMobSpellCaster victory reward SQL execution."""
        # Setup player
        self.cursor.execute("""
            INSERT INTO players (uuid, username, balance, hours_played, kills, deaths, is_online, guild, rank, first_join, last_seen)
            VALUES ('dungeon-winner-uuid', 'DungeonWinner', 100.0, 5, 2, 0, 0, 'None', 'JOUEUR', datetime('now'), datetime('now'))
        """)
        # Award +350 balance
        self.cursor.execute("UPDATE players SET balance = balance + 350 WHERE LOWER(username) = LOWER(?)", ("dungeonwinner",))
        self.assertEqual(self.cursor.rowcount, 1)

        row = self.cursor.execute("SELECT balance FROM players WHERE username = 'DungeonWinner'").fetchone()
        self.assertEqual(row["balance"], 450.0)


class TestM3JarPackagingAndManifest(unittest.TestCase):
    def test_jar_structure_and_class_count(self):
        """Verifies AetherVisuals.jar exists, contains all 50 compiled classes and plugin.yml."""
        self.assertTrue(os.path.exists(JAR_PATH), f"JAR file missing at {JAR_PATH}")
        self.assertGreater(os.path.getsize(JAR_PATH), 500_000)

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = z.namelist()
            class_files = [n for n in names if n.endswith(".class")]
            # Check that at least 50 class files are present
            self.assertGreaterEqual(len(class_files), 50, f"Expected at least 50 class files, found {len(class_files)}")

            # Check key classes
            key_classes = [
                "io/aethercraft/visuals/AetherVisualsPlugin.class",
                "io/aethercraft/visuals/AetherDatabase.class",
                "io/aethercraft/visuals/AetherVisualScoreboardManager.class",
                "io/aethercraft/visuals/AetherVisualScoreboardManager$LeaderboardEntry.class",
                "io/aethercraft/visuals/AetherVisualScoreboardManager$PlayerVisualData.class",
                "io/aethercraft/visuals/AetherCommandExecutor.class",
                "io/aethercraft/visuals/AetherTabCompleter.class",
                "io/aethercraft/visuals/MMORPGDisplayEngine.class",
                "io/aethercraft/visuals/AetherMMOShopCatalog.class",
                "io/aethercraft/visuals/DungeonMobSpellCaster.class",
                "io/aethercraft/visuals/AetherShopGUI.class",
                "io/aethercraft/visuals/AetherMenuGUI.class",
                "io/aethercraft/visuals/CustomItemFactory.class"
            ]
            for kc in key_classes:
                self.assertIn(kc, names, f"Missing critical class in JAR: {kc}")

            # Verify plugin.yml in root
            self.assertIn("plugin.yml", names, "plugin.yml must be in JAR root")
            yml = z.read("plugin.yml").decode("utf-8")
            self.assertIn("name: AetherVisuals", yml)
            self.assertIn("main: io.aethercraft.visuals.AetherVisualsPlugin", yml)
            self.assertIn("top:", yml)
            self.assertIn("baltop", yml)
            self.assertIn("classement", yml)


class TestM3WebDisplayTemplateRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
            autoescape=jinja2.select_autoescape(["html", "xml"])
        )
        cls.template = cls.env.get_template("webdisplay.html")

    def test_render_with_full_leaderboard(self):
        """Render webdisplay.html with full leaderboard dataset."""
        player_ctx = {
            "username": "Hactheglitchis",
            "rank": "Aventurier",
            "coins": 25000,
            "points": 150,
            "guild": "Aether",
            "is_authenticated": True,
            "auth_token": "dummy_token",
            "auth_ts": "1234567890"
        }
        leaderboards = {
            "top_rich": [
                {"username": "RichPlayer1", "rank": "TITAN", "balance": 150000},
                {"username": "RichPlayer2", "rank": "VIP", "balance": 85000},
                {"username": "RichPlayer3", "rank": "JOUEUR", "balance": 42000}
            ],
            "top_hours": [
                {"username": "Veteran1", "hours_played": 340, "kills": 89},
                {"username": "Veteran2", "hours_played": 210, "kills": 45}
            ]
        }
        goal = {
            "donors": [
                {"username": "GenerousDonor", "total_amount": 500}
            ]
        }
        rendered = self.template.render(
            player=player_ctx,
            active_mode="rankings",
            active_cat="all",
            leaderboards=leaderboards,
            goal=goal,
            shop_items=[],
            market_items=[],
            ores=[],
            quests=[],
            achievements=[],
            dungeons=[]
        )
        self.assertIn("RichPlayer1", rendered)
        self.assertIn("150000 ⛃", rendered)
        self.assertIn("Veteran1", rendered)
        self.assertIn("340h de jeu", rendered)
        self.assertIn("GenerousDonor", rendered)
        self.assertIn("[6] Classements", rendered)

    def test_render_with_empty_or_none_leaderboard(self):
        """Render webdisplay.html when leaderboards is None (graceful fallback to loading/client fetch)."""
        player_ctx = {
            "username": "ZeroPlayer",
            "rank": "Joueur",
            "coins": 0,
            "points": 0,
            "guild": "None",
            "is_authenticated": False,
            "auth_token": "",
            "auth_ts": ""
        }
        rendered = self.template.render(
            player=player_ctx,
            active_mode="rankings",
            active_cat="all",
            leaderboards=None,
            goal=None,
            shop_items=[],
            market_items=[],
            ores=[],
            quests=[],
            achievements=[],
            dungeons=[]
        )
        self.assertIn("Chargement du classement Fortune...", rendered)
        self.assertIn("Chargement du classement Temps de jeu...", rendered)
        self.assertIn("[6] Classements", rendered)

    def test_render_xss_safety_in_leaderboard(self):
        """Ensure malicious player names in leaderboards are autoescaped by Jinja2."""
        player_ctx = {
            "username": "<script>alert('xss')</script>",
            "rank": "Hacker",
            "coins": 0,
            "points": 0,
            "guild": "None",
            "is_authenticated": False,
            "auth_token": "",
            "auth_ts": ""
        }
        leaderboards = {
            "top_rich": [
                {"username": "<b>BoldXSS</b>", "rank": "VIP", "balance": 1000}
            ],
            "top_hours": []
        }
        rendered = self.template.render(
            player=player_ctx,
            active_mode="rankings",
            active_cat="all",
            leaderboards=leaderboards,
            goal=None,
            shop_items=[],
            market_items=[],
            ores=[],
            quests=[],
            achievements=[],
            dungeons=[]
        )
        self.assertNotIn("<script>alert('xss')</script>", rendered)
        self.assertIn("&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;", rendered)
        self.assertNotIn("<b>BoldXSS</b>", rendered)
        self.assertIn("&lt;b&gt;BoldXSS&lt;/b&gt;", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
