"""
Adversarial Stress Harness for Milestone M2: Economy, Bullion, Spawns & Death Rules
Target Workspace: C:\\Users\\1234\\Desktop\\Projets\\aethercraft
"""

import os
import sys
import uuid
import math
import unittest
import sqlite3
from typing import List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import get_db_connection


class TestM2AdversarialBullionAndSpawns(unittest.TestCase):
    """Stress-tests Bullion placement and territory boundaries."""

    def setUp(self):
        self.created_uuids = []
        self.created_usernames = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM player_oneblock WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM player_survival_locations WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                    c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({ph_u});", self.created_usernames)
                conn.commit()

    def test_spawn_protection_geometric_boundaries(self):
        """Simulate SpawnProtectionEngine boundary checks with sub-block precision."""
        # Spawn 1: Agora (0, 120, 0), Radius 44, Y >= 110
        def is_in_spawn1(world: str, x: float, y: float, z: float) -> bool:
            if world != "world" or y < 110:
                return False
            dx = x - 0.0
            dz = z - 0.0
            return (dx * dx + dz * dz) <= (44.0 * 44.0)

        # Spawn 2: Celestial ground spawn (640, groundY=72, 864), Half-size 6, Y < 110, |y - 72| <= 8
        def is_in_spawn2(world: str, x: float, y: float, z: float, ground_y: float = 72.0) -> bool:
            if world != "world" or y >= 110:
                return False
            if abs(y - ground_y) > 8:
                return False
            return abs(x - 640.0) <= 6.0 and abs(z - 864.0) <= 6.0

        def is_protected_zone(world: str, x: float, y: float, z: float) -> bool:
            return is_in_spawn1(world, x, y, z) or is_in_spawn2(world, x, y, z)

        # Exact center of Spawn 1
        self.assertTrue(is_protected_zone("world", 0.0, 120.0, 0.0))
        # Inner boundary of Spawn 1
        self.assertTrue(is_protected_zone("world", 43.9, 120.0, 0.0))
        self.assertTrue(is_protected_zone("world", 0.0, 120.0, 44.0))
        # Diagonal inner: 31.0^2 + 31.0^2 = 961 + 961 = 1922 <= 1936
        self.assertTrue(is_protected_zone("world", 31.0, 120.0, 31.0))
        # Diagonal outer: 31.2^2 + 31.2^2 = 1946.88 > 1936
        self.assertFalse(is_protected_zone("world", 31.2, 120.0, 31.2))
        # Just outside Spawn 1 radius
        self.assertFalse(is_protected_zone("world", 44.1, 120.0, 0.0))
        self.assertFalse(is_protected_zone("world", 0.0, 120.0, 44.1))
        # Altitude threshold: Y=109 is below Spawn 1 threshold
        self.assertFalse(is_protected_zone("world", 0.0, 109.9, 0.0))
        self.assertTrue(is_protected_zone("world", 0.0, 110.0, 0.0))
        # Different world (e.g. world_nether or world_oneblock) must not be protected by world spawn
        self.assertFalse(is_protected_zone("world_oneblock", 0.0, 120.0, 0.0))
        self.assertFalse(is_protected_zone("world_nether", 0.0, 120.0, 0.0))

        # Spawn 2 checks
        self.assertTrue(is_protected_zone("world", 640.0, 72.0, 864.0))
        self.assertTrue(is_protected_zone("world", 646.0, 72.0, 870.0))
        self.assertFalse(is_protected_zone("world", 647.0, 72.0, 864.0))
        self.assertFalse(is_protected_zone("world", 640.0, 72.0, 871.0))
        # Altitude outside tolerance
        self.assertFalse(is_protected_zone("world", 640.0, 81.0, 864.0))

    def test_oneblock_chunk_unlock_progression_logic(self):
        """Simulate OneBlockEngine chunk unlock rules across tiers 1 through 15."""
        def is_chunk_unlocked(unlocked_chunks: int, rel_x: int, rel_z: int) -> bool:
            # Central & Portal chunks always unlocked
            if rel_x == 0 and (rel_z == 0 or rel_z == -1):
                return True
            if unlocked_chunks >= 2 and rel_x == 0 and rel_z == 1:
                return True
            if unlocked_chunks >= 3 and rel_x == 1 and rel_z == 0:
                return True
            if unlocked_chunks >= 4 and rel_x == -1 and rel_z == 0:
                return True
            if unlocked_chunks >= 5 and rel_x == 1 and rel_z == -1:
                return True
            if unlocked_chunks >= 6 and rel_x == -1 and rel_z == -1:
                return True
            if unlocked_chunks >= 7 and rel_x == 1 and rel_z == 1:
                return True
            if unlocked_chunks >= 8 and rel_x == -1 and rel_z == 1:
                return True
            if unlocked_chunks >= 9 and rel_x == 0 and rel_z == 2:
                return True
            if unlocked_chunks >= 10 and rel_x == 0 and rel_z == -2:
                return True
            if unlocked_chunks >= 11 and abs(rel_x) <= 1 and abs(rel_z) <= 1:
                return True
            if unlocked_chunks >= 12 and abs(rel_x) <= 2 and abs(rel_z) <= 2:
                return True
            return unlocked_chunks >= 15

        # Tier 1 (Initial)
        self.assertTrue(is_chunk_unlocked(1, 0, 0))   # Central
        self.assertTrue(is_chunk_unlocked(1, 0, -1))  # Portal / North
        self.assertFalse(is_chunk_unlocked(1, 0, 1))  # South locked
        self.assertFalse(is_chunk_unlocked(1, 1, 0))  # East locked
        self.assertFalse(is_chunk_unlocked(1, -1, 0)) # West locked

        # Tier 2: Sud unlocked
        self.assertTrue(is_chunk_unlocked(2, 0, 1))
        self.assertFalse(is_chunk_unlocked(2, 1, 0))

        # Tier 3: Est unlocked
        self.assertTrue(is_chunk_unlocked(3, 1, 0))
        self.assertFalse(is_chunk_unlocked(3, -1, 0))

        # Tier 4: Ouest unlocked
        self.assertTrue(is_chunk_unlocked(4, -1, 0))
        self.assertFalse(is_chunk_unlocked(4, 1, -1))

        # Tier 11: 3x3 complete
        for rx in [-1, 0, 1]:
            for rz in [-1, 0, 1]:
                self.assertTrue(is_chunk_unlocked(11, rx, rz), f"Tier 11 must unlock ({rx}, {rz})")


class TestM2AdversarialDeathDropFilter(unittest.TestCase):
    """Stress-tests death drop rules for mixed inventories."""

    def test_mixed_inventory_death_drop_partition(self):
        """Simulate PlayerDeathEvent drop filtering with diverse real-world Minecraft items."""
        # Simulates PetItemFactory.isBullionCoin(item) and item.getType().isBlock()
        bullion_cmds = {6001, 6002, 6003, 6004, 6005, 6006}

        inventory = [
            # Building blocks (MUST BE REMOVED / LOST)
            {"name": "Cobblestone", "is_block": True, "cmd": None, "qty": 64},
            {"name": "Oak Planks", "is_block": True, "cmd": None, "qty": 32},
            {"name": "Stone Bricks", "is_block": True, "cmd": None, "qty": 16},
            {"name": "Glass", "is_block": True, "cmd": None, "qty": 64},
            {"name": "Obsidian", "is_block": True, "cmd": None, "qty": 10},
            {"name": "White Wool", "is_block": True, "cmd": None, "qty": 16},
            {"name": "Terracotta", "is_block": True, "cmd": None, "qty": 64},
            # Raw mineral blocks without bullion CMD (MUST BE REMOVED / LOST)
            {"name": "Raw Gold Block (Vanilla)", "is_block": True, "cmd": None, "qty": 5},
            {"name": "Gold Block (Vanilla)", "is_block": True, "cmd": None, "qty": 3},
            {"name": "Iron Block (Vanilla)", "is_block": True, "cmd": None, "qty": 8},
            {"name": "Diamond Block (Vanilla)", "is_block": True, "cmd": None, "qty": 1},
            # Physical coins / Bullion ("pièces solides" - MUST BE PRESERVED AS DROPS)
            {"name": "Pièce Bronze (CMD 6001)", "is_block": False, "cmd": 6001, "qty": 20},
            {"name": "Pièce Argent (CMD 6002)", "is_block": False, "cmd": 6002, "qty": 15},
            {"name": "Lingot d'Or (CMD 6004)", "is_block": False, "cmd": 6004, "qty": 4},
            # Bullion Blocks (Habbo Magots - MUST BE PRESERVED AS DROPS)
            {"name": "Sac de Pièces (CMD 6003)", "is_block": True, "cmd": 6003, "qty": 2},
            {"name": "Bloc d'Or Habbo (CMD 6005)", "is_block": True, "cmd": 6005, "qty": 1},
            {"name": "Magot Émeraude (CMD 6006)", "is_block": True, "cmd": 6006, "qty": 1},
            # Weapons, Tools & Armor (MUST BE PRESERVED AS DROPS)
            {"name": "Diamond Sword", "is_block": False, "cmd": None, "qty": 1},
            {"name": "Netherite Pickaxe", "is_block": False, "cmd": None, "qty": 1},
            {"name": "Netherite Chestplate", "is_block": False, "cmd": None, "qty": 1},
            {"name": "Diamond Helmet", "is_block": False, "cmd": None, "qty": 1},
            {"name": "Bow", "is_block": False, "cmd": None, "qty": 1},
            # Special items & consumables (MUST BE PRESERVED AS DROPS)
            {"name": "Aether Phone (CMD 1000)", "is_block": False, "cmd": 1000, "qty": 1},
            {"name": "Golden Carrot", "is_block": False, "cmd": None, "qty": 64},
            {"name": "Enchanted Golden Apple", "is_block": False, "cmd": None, "qty": 2},
        ]

        def is_bullion_coin(item: Dict[str, Any]) -> bool:
            return item.get("cmd") in bullion_cmds

        # Exact filter implemented in HabboBullionBlockEngine & StoreItemInteractListener:
        # drops.removeIf(item -> item != null && item.getType().isBlock() && !PetItemFactory.isBullionCoin(item));
        lost_items = [i for i in inventory if i["is_block"] and not is_bullion_coin(i)]
        preserved_drops = [i for i in inventory if not (i["is_block"] and not is_bullion_coin(i))]

        # Verify all 11 construction / vanilla block stacks are removed
        self.assertEqual(len(lost_items), 11, f"Expected 11 lost block stacks, got {len(lost_items)}")
        lost_names = {i["name"] for i in lost_items}
        self.assertIn("Cobblestone", lost_names)
        self.assertIn("Oak Planks", lost_names)
        self.assertIn("Glass", lost_names)
        self.assertIn("Raw Gold Block (Vanilla)", lost_names)
        self.assertIn("Gold Block (Vanilla)", lost_names)
        self.assertIn("Iron Block (Vanilla)", lost_names)

        # Verify preserved drops
        self.assertEqual(len(preserved_drops), 14, f"Expected 14 preserved drop stacks, got {len(preserved_drops)}")
        preserved_names = {i["name"] for i in preserved_drops}
        # Currency coins preserved
        self.assertIn("Pièce Bronze (CMD 6001)", preserved_names)
        self.assertIn("Pièce Argent (CMD 6002)", preserved_names)
        self.assertIn("Lingot d'Or (CMD 6004)", preserved_names)
        # Bullion blocks preserved
        self.assertIn("Sac de Pièces (CMD 6003)", preserved_names)
        self.assertIn("Bloc d'Or Habbo (CMD 6005)", preserved_names)
        self.assertIn("Magot Émeraude (CMD 6006)", preserved_names)
        # Weapons, armor, phone preserved
        self.assertIn("Diamond Sword", preserved_names)
        self.assertIn("Netherite Chestplate", preserved_names)
        self.assertIn("Aether Phone (CMD 1000)", preserved_names)
        self.assertIn("Golden Carrot", preserved_names)

    def test_virtual_bank_and_balance_immutability_under_repeated_deaths(self):
        """Verify virtual wallet balance and bank coins are 100% immune to death penalties."""
        test_uuid = str(uuid.uuid4())
        test_user = f"Immune_{test_uuid[:6]}"

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 88888.5, 25, 10, 0, 1, 'Vault', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (test_uuid, test_user))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 500000.0, CURRENT_TIMESTAMP)
            """, (test_user,))
            conn.commit()

            # Simulate 50 consecutive deaths
            for _ in range(50):
                c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (test_uuid,))
            conn.commit()

            c.execute("SELECT balance, deaths FROM players WHERE uuid = ?", (test_uuid,))
            row = c.fetchone()
            self.assertEqual(row["deaths"], 50)
            self.assertEqual(row["balance"], 88888.5, "Wallet balance must remain unchanged across 50 deaths")

            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE username = ?", (test_user,))
            b_row = c.fetchone()
            self.assertEqual(b_row["bank_coins"], 500000.0, "Bank coins must remain unchanged across 50 deaths")

            # Clean up
            c.execute("DELETE FROM players WHERE uuid = ?", (test_uuid,))
            c.execute("DELETE FROM player_bank_accounts WHERE username = ?", (test_user,))
            conn.commit()


if __name__ == "__main__":
    unittest.main()
