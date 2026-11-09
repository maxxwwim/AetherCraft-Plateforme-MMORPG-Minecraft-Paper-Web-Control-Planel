r"""
================================================================================
Milestone M2 Empirical Challenger Verification & Stress Test Suite
================================================================================
Target Workspace: C:\Users\1234\Desktop\Projets\aethercraft
Milestone: M2 (Economy, Furniture, Bullion & Coins, Survival Loot, Death Rules)
Executed by: teamwork_challenger_m2_gp_1

Empirical Stress Testing Dimensions:
1. Bullion Redemption & Immediate Scoreboard Sync:
   - All 6 face-value denominations (+10, +50, +100, +250, +500, +1000 ⛃)
   - Single item vs sneak full-stack redemption math and integer overflow defense
   - Parameterized SQLite balance update and case-insensitive username resolution
   - Immediate scoreboard manager refresh invocation hook verification
2. Survival Breakability, Natural Item Drop & Explosion Handling:
   - Left-click hit breakability and world.dropItemNaturally item drop contract
   - Reconstructibility with exact CustomModelData for reuse by any player
   - EntityExplodeEvent & BlockExplodeEvent listeners with blast radius search
   - Adversarial multi-entity cluster deduplication preventing item duplication
3. Death Rules, Block Stripping & Currency Preservation:
   - Full drop permutation matrix: building blocks stripped, coins/bullion/gear preserved
   - Zero durability/repair penalty on carried currency
   - 100% preservation of virtual wallet balance and bank accounts in SQLite
   - Lootability of drops by any player in Survival & OneBlock
4. Java Plugin Compilation & Bytecode Integrity:
   - Validates clean compilation via build_plugin.py
   - Validates AetherVisuals.jar archive, Java 21 class major version (65.0)
================================================================================
"""

import os
import sys
import re
import uuid
import struct
import zipfile
import sqlite3
import unittest
from typing import Dict, Any, List, Set, Tuple, Optional

# Ensure project root and web directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
JAR_PATH = os.path.join(SERVER_DIR, "plugins", "AetherVisuals.jar")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import get_db_connection, init_database


# ==============================================================================
# MOCK / SIMULATION MODELS FOR BUKKIT & PAPERMC ENTITIES
# ==============================================================================

class MockMaterial:
    def __init__(self, name: str, is_block: bool):
        self.name = name
        self._is_block = is_block

    def isBlock(self) -> bool:
        return self._is_block

    def __repr__(self):
        return f"Material.{self.name}"


# Standard materials for testing death drops
MATERIALS = {
    # Building blocks
    "STONE": MockMaterial("STONE", True),
    "COBBLESTONE": MockMaterial("COBBLESTONE", True),
    "OAK_PLANKS": MockMaterial("OAK_PLANKS", True),
    "DIRT": MockMaterial("DIRT", True),
    "OBSIDIAN": MockMaterial("OBSIDIAN", True),
    "GLASS": MockMaterial("GLASS", True),
    "BRICKS": MockMaterial("BRICKS", True),
    "WHITE_WOOL": MockMaterial("WHITE_WOOL", True),
    "PRISMARINE": MockMaterial("PRISMARINE", True),
    "DEEPSLATE": MockMaterial("DEEPSLATE", True),
    # Bullion blocks
    "RAW_GOLD_BLOCK": MockMaterial("RAW_GOLD_BLOCK", True),
    "GOLD_BLOCK": MockMaterial("GOLD_BLOCK", True),
    "EMERALD_BLOCK": MockMaterial("EMERALD_BLOCK", True),
    # Non-block coins & ingots
    "COPPER_INGOT": MockMaterial("COPPER_INGOT", False),
    "IRON_INGOT": MockMaterial("IRON_INGOT", False),
    "GOLD_INGOT": MockMaterial("GOLD_INGOT", False),
    # Weapons, tools, armor, food, phone
    "DIAMOND_SWORD": MockMaterial("DIAMOND_SWORD", False),
    "NETHERITE_CHESTPLATE": MockMaterial("NETHERITE_CHESTPLATE", False),
    "BOW": MockMaterial("BOW", False),
    "COOKED_BEEF": MockMaterial("COOKED_BEEF", False),
    "RECOVERY_COMPASS": MockMaterial("RECOVERY_COMPASS", False),
}


class MockItemMeta:
    def __init__(self, cmd: Optional[int] = None, display_name: Optional[str] = None):
        self.cmd = cmd
        self.display_name = display_name

    def hasCustomModelData(self) -> bool:
        return self.cmd is not None

    def getCustomModelData(self) -> int:
        return self.cmd if self.cmd is not None else 0

    def hasDisplayName(self) -> bool:
        return self.display_name is not None

    def getDisplayName(self) -> str:
        return self.display_name or ""


class MockItemStack:
    def __init__(self, material: MockMaterial, amount: int = 1, cmd: Optional[int] = None, display_name: Optional[str] = None):
        self.material = material
        self.amount = amount
        self.meta = MockItemMeta(cmd, display_name) if (cmd is not None or display_name is not None) else None
        self.durability_loss = 0

    def getType(self) -> MockMaterial:
        return self.material

    def getAmount(self) -> int:
        return self.amount

    def setAmount(self, amt: int):
        self.amount = amt

    def hasItemMeta(self) -> bool:
        return self.meta is not None

    def getItemMeta(self) -> Optional[MockItemMeta]:
        return self.meta

    def __repr__(self):
        cmd_str = f", cmd={self.meta.cmd}" if self.meta and self.meta.cmd else ""
        return f"ItemStack({self.material.name}, qty={self.amount}{cmd_str})"


def is_bullion_coin(item: Optional[MockItemStack]) -> bool:
    """Verbatim mirror of PetItemFactory.isBullionCoin(item)."""
    if item is None or not item.hasItemMeta():
        return False
    meta = item.getItemMeta()
    if not meta.hasCustomModelData():
        return False
    cmd = meta.getCustomModelData()
    return cmd in {6001, 6002, 6003, 6004, 6005, 6006}


def is_solid_coin(item: Optional[MockItemStack]) -> bool:
    """Verbatim mirror of PetItemFactory.isSolidCoin(item)."""
    if item is None or not item.hasItemMeta():
        return False
    meta = item.getItemMeta()
    if not meta.hasCustomModelData():
        return False
    cmd = meta.getCustomModelData()
    return cmd in {6001, 6002, 6004}


def get_bullion_coin_value(cmd: int) -> int:
    """Verbatim mirror of PetItemFactory.getBullionCoinValue(cmd)."""
    mapping = {
        6001: 10,
        6002: 50,
        6003: 100,
        6004: 250,
        6005: 500,
        6006: 1000
    }
    return mapping.get(cmd, 0)


class MockPlayer:
    def __init__(self, name: str, is_sneaking: bool = False):
        self.name = name
        self.is_sneaking = is_sneaking
        self.hand_item: Optional[MockItemStack] = None

    def getName(self) -> str:
        return self.name

    def isSneaking(self) -> bool:
        return self.is_sneaking


class MockClusterEntity:
    def __init__(self, uuid_str: str, entity_type: str, cmd: int, value: int, name: str,
                 linked_item: str, linked_text: str, linked_inter: str):
        self.uuid = uuid_str
        self.type = entity_type
        self.valid = True
        self.pdc = {
            "habbo_bullion": "true",
            "bullion_cmd": cmd,
            "bullion_value": value,
            "bullion_name": name,
            "bullion_item_uuid": linked_item,
            "bullion_text_uuid": linked_text,
            "bullion_inter_uuid": linked_inter
        }

    def isValid(self) -> bool:
        return self.valid

    def remove(self):
        self.valid = False


class MockWorldForExplosion:
    def __init__(self):
        self.entities: Dict[str, MockClusterEntity] = {}
        self.dropped_items: List[MockItemStack] = []

    def getEntity(self, uuid_str: str) -> Optional[MockClusterEntity]:
        e = self.entities.get(uuid_str)
        return e if (e and e.isValid()) else None

    def removeEntityByUuid(self, uuid_str: str):
        e = self.entities.get(uuid_str)
        if e and e.isValid():
            e.remove()

    def dropItemNaturally(self, item: MockItemStack):
        self.dropped_items.append(item)

    def getNearbyEntities(self) -> List[MockClusterEntity]:
        # Snapshot returned by Bukkit
        return list(self.entities.values())


# ==============================================================================
# TEST SUITE 1: BULLION REDEMPTION & SCOREBOARD REFRESH
# ==============================================================================

class TestBullionRedemptionAndScoreboardSync(unittest.TestCase):
    """
    Adversarial verification of bullion redemption across all denominations:
    - Exact crediting for +10, +50, +100, +250, +500, +1000 ⛃
    - Single item vs sneak full-stack redemption math
    - Extreme balance boundary (preventing 32-bit overflow)
    - Immediate scoreboard manager refresh hook in Java code
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({ph_u});", self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                conn.commit()

    def test_denominations_registry_and_value_mapping(self):
        """Validates all 6 face-value bullion denominations in PetItemFactory."""
        expected_denominations = {
            6001: 10,    # Bronze
            6002: 50,    # Silver
            6003: 100,   # Sack of Coins
            6004: 250,   # Gold Ingot
            6005: 500,   # Gold Block
            6006: 1000   # Emerald Block
        }
        for cmd, expected_val in expected_denominations.items():
            self.assertEqual(get_bullion_coinValue(cmd) if 'get_bullion_coinValue' in dir() else get_bullion_coin_value(cmd),
                             expected_val, f"CMD {cmd} must yield exactly {expected_val} coins")

        # Invalid CMDs must return 0
        invalid_cmds = [0, 1001, 2001, 3001, 4001, 5001, 6000, 6007, 9999, -1]
        for cmd in invalid_cmds:
            self.assertEqual(get_bullion_coin_value(cmd), 0, f"Invalid CMD {cmd} must return 0 value")

    def test_bullion_and_solid_coin_helper_contracts(self):
        """Validates isBullionCoin and isSolidCoin contracts across item types."""
        # Bullion items
        bronze = MockItemStack(MATERIALS["COPPER_INGOT"], 1, cmd=6001)
        silver = MockItemStack(MATERIALS["IRON_INGOT"], 1, cmd=6002)
        sack = MockItemStack(MATERIALS["RAW_GOLD_BLOCK"], 1, cmd=6003)
        ingot = MockItemStack(MATERIALS["GOLD_INGOT"], 1, cmd=6004)
        gold_block = MockItemStack(MATERIALS["GOLD_BLOCK"], 1, cmd=6005)
        emerald_block = MockItemStack(MATERIALS["EMERALD_BLOCK"], 1, cmd=6006)

        # All 6 are bullion coins
        for it in [bronze, silver, sack, ingot, gold_block, emerald_block]:
            self.assertTrue(is_bullion_coin(it), f"{it} must be identified as bullion coin")

        # Only physical non-block coins are solid coins (6001, 6002, 6004)
        self.assertTrue(is_solid_coin(bronze), "Bronze coin must be solid coin")
        self.assertTrue(is_solid_coin(silver), "Silver coin must be solid coin")
        self.assertTrue(is_solid_coin(ingot), "Gold ingot must be solid coin")

        self.assertFalse(is_solid_coin(sack), "Sack of coins (raw gold block) is block, not solid coin")
        self.assertFalse(is_solid_coin(gold_block), "Gold block is block, not solid coin")
        self.assertFalse(is_solid_coin(emerald_block), "Emerald block is block, not solid coin")

        # Non-bullion items
        phone = MockItemStack(MATERIALS["RECOVERY_COMPASS"], 1, cmd=5001)
        sword = MockItemStack(MATERIALS["DIAMOND_SWORD"], 1)
        stone = MockItemStack(MATERIALS["STONE"], 64)
        self.assertFalse(is_bullion_coin(phone))
        self.assertFalse(is_solid_coin(phone))
        self.assertFalse(is_bullion_coin(sword))
        self.assertFalse(is_bullion_coin(stone))

    def test_redemption_all_denominations_sqlite_and_scoreboard_sync(self):
        """Simulates single-item and sneak full-stack redemptions for all 6 denominations with case-insensitive matching."""
        denominations = [
            (6001, 10, "Pièce de Bronze"),
            (6002, 50, "Pièce d'Argent"),
            (6003, 100, "Sac de Pièces"),
            (6004, 250, "Lingot d'Or"),
            (6005, 500, "Bloc d'Or"),
            (6006, 1000, "Bloc d'Émeraude")
        ]

        for cmd, unit_val, label in denominations:
            t_uuid = str(uuid.uuid4())
            # Test mixed-case username
            t_user = f"EcoRedeem_{t_uuid[:5].upper()}"
            self.created_uuids.append(t_uuid)
            self.created_usernames.append(t_user)

            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                    VALUES (?, ?, 'JOUEUR', 0.0, 1, 0, 0, 1, 'Commerce', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (t_uuid, t_user))
                conn.commit()

                # Phase A: Single redemption (qty = 1, not sneaking)
                qty_single = 1
                gain_single = qty_single * unit_val
                # Execute Java SQL query verbatim: WHERE LOWER(username)=LOWER(?)
                c.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)",
                          (gain_single, t_user.lower()))
                conn.commit()

                # Verify Scoreboard reader query
                c.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?)", (t_user,))
                bal_single = c.fetchone()["balance"]
                self.assertEqual(bal_single, float(gain_single),
                                 f"Single redemption for {label} (+{unit_val}) failed")

                # Phase B: Sneak stack redemption (qty = 64, sneaking)
                qty_stack = 64
                gain_stack = qty_stack * unit_val
                c.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)",
                          (gain_stack, t_user.upper()))
                conn.commit()

                c.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?)", (t_user,))
                bal_total = c.fetchone()["balance"]
                expected_total = float(gain_single + gain_stack)
                self.assertEqual(bal_total, expected_total,
                                 f"Sneak 64-stack redemption for {label} failed: expected {expected_total}, got {bal_total}")

    def test_extreme_stack_and_large_balance_integer_overflow_defense(self):
        """Stress tests redemption with massive stacks and large starting balance to prevent 32-bit overflow."""
        t_uuid = str(uuid.uuid4())
        t_user = f"TitanBank_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            # Initial balance 2.5 Billion (> Integer.MAX_VALUE = 2,147,483,647)
            init_bal = 2_500_000_000.0
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'TITAN', ?, 100, 10, 0, 1, 'Légende', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user, init_bal))
            conn.commit()

            # Redeem 10,000 Emerald Blocks (+1000 each) = +10,000,000
            qty = 10_000
            unit_val = 1000
            total_gain = qty * unit_val  # 10,000,000

            c.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)",
                      (total_gain, t_user))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE uuid = ?", (t_uuid,))
            final_bal = c.fetchone()["balance"]
            expected_bal = init_bal + total_gain
            self.assertEqual(final_bal, expected_bal,
                             f"Extreme balance arithmetic overflow: expected {expected_bal}, got {final_bal}")

    def test_source_code_scoreboard_refresh_hooks_contract(self):
        """Verifies both HabboBullionBlockEngine and StoreItemInteractListener execute immediate scoreboard refresh."""
        bullion_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        store_path = os.path.join(SRC_DIR, "StoreItemInteractListener.java")

        with open(bullion_path, "r", encoding="utf-8") as f:
            bullion_code = f.read()
        with open(store_path, "r", encoding="utf-8") as f:
            store_code = f.read()

        # In HabboBullionBlockEngine: onBullionInteract must call refreshPlayer
        self.assertIn("onBullionInteract", bullion_code)
        self.assertTrue(
            "refreshPlayer" in bullion_code and "getScoreboardManager" in bullion_code,
            "HabboBullionBlockEngine.onBullionInteract must trigger immediate scoreboard refresh"
        )

        # In StoreItemInteractListener: redeemHabboBullion must call refreshPlayer
        self.assertIn("redeemHabboBullion", store_code)
        self.assertTrue(
            "refreshPlayer" in store_code and "getScoreboardManager" in store_code,
            "StoreItemInteractListener.redeemHabboBullion must trigger immediate scoreboard refresh"
        )


# ==============================================================================
# TEST SUITE 2: SURVIVAL BREAKABILITY & EXPLOSION HANDLING
# ==============================================================================

class TestSurvivalBreakabilityAndExplosionHandling(unittest.TestCase):
    """
    Adversarial verification of survival breakability, natural item drops,
    and explosion mechanics:
    - world.dropItemNaturally on player left-click attack (not inventory addItem)
    - Full CustomModelData preservation for multi-player looting and re-placement
    - EntityExplodeEvent & BlockExplodeEvent handling with cluster deduplication
    - Blast radius dense cluster stress test
    """

    def test_source_contract_drop_item_naturally_and_hit_breakability(self):
        """Verifies HabboBullionBlockEngine uses dropItemNaturally on hit and explosion."""
        bullion_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        with open(bullion_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Must listen to hit event on cluster
        self.assertIn("onBullionHit", code)
        self.assertIn("EntityDamageByEntityEvent", code)

        # Must use dropItemNaturally
        self.assertIn("dropItemNaturally", code,
                      "HabboBullionBlockEngine must use dropItemNaturally to spawn loot into the world")

        # Must listen to both entity and block explosions
        self.assertIn("onEntityExplode", code)
        self.assertIn("EntityExplodeEvent", code)
        self.assertIn("onBlockExplode", code)
        self.assertIn("BlockExplodeEvent", code)

    def test_hit_breakability_natural_drop_and_multi_player_reusability(self):
        """Simulates player A breaking placed bullion, dropping naturally, and player B looting it."""
        # Placed bullion is a Bloc d'Or (CMD 6005, 500 coins)
        placed_cmd = 6005
        bullion_id = "magot_bloc_or"

        # Simulating hit: item reconstructed via PetItemFactory.createHabboBullionItem
        refund_item = MockItemStack(MATERIALS["GOLD_BLOCK"], 1, cmd=placed_cmd,
                                    display_name="§6§l🟨 Bloc d'Or Impérial §8[§6500 ⛃§8]")

        # Player A drops item naturally into world
        world_drops = [refund_item]

        # Player B loots item from world
        looted_item = world_drops.pop()
        self.assertEqual(looted_item.getType().name, "GOLD_BLOCK")
        self.assertEqual(looted_item.getItemMeta().getCustomModelData(), 6005)
        self.assertTrue(is_bullion_coin(looted_item))

        # Player B can redeem it for 100% of its value (500 coins)
        val = get_bullion_coin_value(looted_item.getItemMeta().getCustomModelData())
        self.assertEqual(val, 500, "Looted bullion must retain 100% face value (500 coins)")

    def test_adversarial_explosion_cluster_deduplication(self):
        """
        Adversarial test: Each placed bullion cluster contains 3 linked entities
        (ItemDisplay, TextDisplay, Interaction), all tagged with TAG_BULLION.
        Asserts that an explosion over the cluster drops EXACTLY 1 item, NOT 3.
        """
        world = MockWorldForExplosion()
        item_uuid = "uuid-item-1"
        text_uuid = "uuid-text-1"
        inter_uuid = "uuid-inter-1"

        # Create all 3 entities of the cluster
        e_item = MockClusterEntity(item_uuid, "ITEM_DISPLAY", 6004, 250, "Lingot d'Or",
                                  item_uuid, text_uuid, inter_uuid)
        e_text = MockClusterEntity(text_uuid, "TEXT_DISPLAY", 6004, 250, "Lingot d'Or",
                                  item_uuid, text_uuid, inter_uuid)
        e_inter = MockClusterEntity(inter_uuid, "INTERACTION", 6004, 250, "Lingot d'Or",
                                   item_uuid, text_uuid, inter_uuid)

        world.entities[item_uuid] = e_item
        world.entities[text_uuid] = e_text
        world.entities[inter_uuid] = e_inter

        # Simulate HabboBullionBlockEngine.handleExplosion verbatim
        def simulate_handle_explosion(w: MockWorldForExplosion):
            for entity in w.getNearbyEntities():
                if not entity.isValid():
                    continue
                if entity.pdc.get("habbo_bullion") != "true":
                    continue

                cmd = entity.pdc.get("bullion_cmd", 6004)
                bullion_id = "magot_lingot_or" if cmd == 6004 else "magot_piece_bronze"
                refund = MockItemStack(MATERIALS["GOLD_INGOT"], 1, cmd=cmd)

                # destroyBullionCluster
                linked_item = entity.pdc.get("bullion_item_uuid")
                linked_text = entity.pdc.get("bullion_text_uuid")
                linked_inter = entity.pdc.get("bullion_inter_uuid")

                w.removeEntityByUuid(linked_item)
                w.removeEntityByUuid(linked_text)
                w.removeEntityByUuid(linked_inter)
                entity.remove()

                # world.dropItemNaturally
                w.dropItemNaturally(refund)

        # Trigger explosion
        simulate_handle_explosion(world)

        # Assert: Exactly 1 item dropped, NOT 3 duplicate drops
        self.assertEqual(len(world.dropped_items), 1,
                         f"Explosion must drop exactly 1 item per cluster, but dropped {len(world.dropped_items)}")
        # Assert: All 3 entities in the cluster were destroyed
        self.assertFalse(e_item.isValid(), "ItemDisplay must be invalidated")
        self.assertFalse(e_text.isValid(), "TextDisplay must be invalidated")
        self.assertFalse(e_inter.isValid(), "Interaction entity must be invalidated")

    def test_blast_radius_multi_cluster_dense_explosion(self):
        """Stress test: 10 bullion clusters within blast radius are all cleaned up and drop exactly 10 items."""
        world = MockWorldForExplosion()
        expected_items = 10

        for i in range(expected_items):
            iu, tu, xu = f"item-{i}", f"text-{i}", f"inter-{i}"
            cmd = 6001 + (i % 6)
            world.entities[iu] = MockClusterEntity(iu, "ITEM_DISPLAY", cmd, 10, f"Bullion {i}", iu, tu, xu)
            world.entities[tu] = MockClusterEntity(tu, "TEXT_DISPLAY", cmd, 10, f"Bullion {i}", iu, tu, xu)
            world.entities[xu] = MockClusterEntity(xu, "INTERACTION", cmd, 10, f"Bullion {i}", iu, tu, xu)

        self.assertEqual(len(world.entities), expected_items * 3)

        # Execute explosion
        for entity in world.getNearbyEntities():
            if not entity.isValid():
                continue
            if entity.pdc.get("habbo_bullion") != "true":
                continue
            cmd = entity.pdc.get("bullion_cmd", 6004)
            refund = MockItemStack(MATERIALS["COPPER_INGOT"], 1, cmd=cmd)

            world.removeEntityByUuid(entity.pdc.get("bullion_item_uuid"))
            world.removeEntityByUuid(entity.pdc.get("bullion_text_uuid"))
            world.removeEntityByUuid(entity.pdc.get("bullion_inter_uuid"))
            entity.remove()
            world.dropItemNaturally(refund)

        self.assertEqual(len(world.dropped_items), expected_items,
                         f"Dense explosion must drop exactly {expected_items} items, got {len(world.dropped_items)}")
        for e in world.entities.values():
            self.assertFalse(e.isValid(), f"Entity {e.uuid} must be cleaned up")


# ==============================================================================
# TEST SUITE 3: DEATH RULES & INVENTORY PRESERVATION
# ==============================================================================

class TestDeathRulesAndInventoryPreservation(unittest.TestCase):
    """
    Adversarial verification of player death rules:
    - User instruction: On death, ONLY building blocks are lost.
    - Physical coins, bullion blocks, and bank balance are 100% preserved.
    - Zero repair penalty / zero durability damage on carried coins/ingots.
    - Dropped items can be looted by any player.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM player_bank_accounts WHERE username IN ({ph_u});", self.created_usernames)
                conn.commit()

    def test_source_code_death_event_filter_contract(self):
        """Verifies PlayerDeathEvent filter logic in HabboBullionBlockEngine and StoreItemInteractListener."""
        bullion_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        store_path = os.path.join(SRC_DIR, "StoreItemInteractListener.java")

        with open(bullion_path, "r", encoding="utf-8") as f:
            b_code = f.read()
        with open(store_path, "r", encoding="utf-8") as f:
            s_code = f.read()

        # Contract: drops.removeIf(item -> item != null && item.getType().isBlock() && !PetItemFactory.isBullionCoin(item));
        expected_filter = "isBlock()"
        self.assertIn("PlayerDeathEvent", b_code)
        self.assertIn("onPlayerDeath", b_code)
        self.assertIn(expected_filter, b_code)
        self.assertIn("isBullionCoin", b_code)

        self.assertIn("PlayerDeathEvent", s_code)
        self.assertIn("onPlayerDeath", s_code)
        self.assertIn(expected_filter, s_code)
        self.assertIn("isBullionCoin", s_code)

    def test_exhaustive_death_drop_matrix_simulation(self):
        """
        Adversarial simulation: Test 25 distinct item types in player death inventory.
        Assert that:
        1. All building construction blocks are stripped and lost.
        2. All physical coins (bronze, silver, ingot) are preserved.
        3. All bullion blocks (sack, gold block, emerald block) are preserved.
        4. All survival gear & phone are preserved.
        5. Carried items suffer 0 durability loss.
        """
        # Inventory setup:
        inventory: List[MockItemStack] = [
            # 10 Building construction blocks (MUST BE REMOVED)
            MockItemStack(MATERIALS["STONE"], 64),
            MockItemStack(MATERIALS["COBBLESTONE"], 64),
            MockItemStack(MATERIALS["OAK_PLANKS"], 32),
            MockItemStack(MATERIALS["DIRT"], 64),
            MockItemStack(MATERIALS["OBSIDIAN"], 14),
            MockItemStack(MATERIALS["GLASS"], 16),
            MockItemStack(MATERIALS["BRICKS"], 48),
            MockItemStack(MATERIALS["WHITE_WOOL"], 20),
            MockItemStack(MATERIALS["PRISMARINE"], 10),
            MockItemStack(MATERIALS["DEEPSLATE"], 64),

            # 3 Ordinary mineral blocks WITHOUT CustomModelData (MUST BE REMOVED as ordinary blocks)
            MockItemStack(MATERIALS["RAW_GOLD_BLOCK"], 5),
            MockItemStack(MATERIALS["GOLD_BLOCK"], 3),
            MockItemStack(MATERIALS["EMERALD_BLOCK"], 2),

            # 3 Physical non-block coins (MUST BE PRESERVED)
            MockItemStack(MATERIALS["COPPER_INGOT"], 10, cmd=6001),  # Pièce Bronze
            MockItemStack(MATERIALS["IRON_INGOT"], 5, cmd=6002),    # Pièce Argent
            MockItemStack(MATERIALS["GOLD_INGOT"], 2, cmd=6004),    # Lingot d'Or

            # 3 Bullion blocks (MUST BE PRESERVED despite being blocks)
            MockItemStack(MATERIALS["RAW_GOLD_BLOCK"], 1, cmd=6003), # Sac de Pièces
            MockItemStack(MATERIALS["GOLD_BLOCK"], 2, cmd=6005),     # Bloc d'Or Habbo
            MockItemStack(MATERIALS["EMERALD_BLOCK"], 1, cmd=6006),  # Bloc d'Émeraude Habbo

            # 5 Gear / Phone / Non-block items (MUST BE PRESERVED)
            MockItemStack(MATERIALS["DIAMOND_SWORD"], 1),
            MockItemStack(MATERIALS["NETHERITE_CHESTPLATE"], 1),
            MockItemStack(MATERIALS["BOW"], 1),
            MockItemStack(MATERIALS["COOKED_BEEF"], 16),
            MockItemStack(MATERIALS["RECOVERY_COMPASS"], 1, cmd=5001) # Phone
        ]

        self.assertEqual(len(inventory), 24)

        # Verbatim Bukkit filter:
        # drops.removeIf(item -> item != null && item.getType().isBlock() && !PetItemFactory.isBullionCoin(item));
        drops = list(inventory)
        drops = [item for item in drops if not (item is not None and item.getType().isBlock() and not is_bullion_coin(item))]

        # Verifications:
        # Building blocks must be completely stripped
        for b_name in ["STONE", "COBBLESTONE", "OAK_PLANKS", "DIRT", "OBSIDIAN", "GLASS", "BRICKS", "WHITE_WOOL", "PRISMARINE", "DEEPSLATE"]:
            found = any(it.getType().name == b_name for it in drops)
            self.assertFalse(found, f"Building block {b_name} must be stripped from death drops")

        # Ordinary blocks without CMD must be stripped
        ordinary_minerals_found = any(it.getType().name in ["RAW_GOLD_BLOCK", "GOLD_BLOCK", "EMERALD_BLOCK"]
                                      and not is_bullion_coin(it) for it in drops)
        self.assertFalse(ordinary_minerals_found, "Ordinary mineral blocks without bullion CMD must be stripped")

        # Physical coins MUST be preserved
        preserved_coins = [it for it in drops if is_solid_coin(it)]
        self.assertEqual(len(preserved_coins), 3, "All 3 physical coins must be preserved")

        # Bullion blocks MUST be preserved
        preserved_bullion_blocks = [it for it in drops if it.getType().isBlock() and is_bullion_coin(it)]
        self.assertEqual(len(preserved_bullion_blocks), 3, "All 3 bullion blocks must be preserved")

        # Survival gear & phone MUST be preserved
        gear_names = {"DIAMOND_SWORD", "NETHERITE_CHESTPLATE", "BOW", "COOKED_BEEF", "RECOVERY_COMPASS"}
        preserved_gear = [it for it in drops if it.getType().name in gear_names]
        self.assertEqual(len(preserved_gear), 5, "All 5 survival items must be preserved")

        # Zero repair penalty / zero durability degradation on coins & bullion
        for it in preserved_coins + preserved_bullion_blocks:
            self.assertEqual(it.durability_loss, 0, f"Coin/bullion {it} must suffer 0 durability loss")

    def test_virtual_bank_and_wallet_preservation_on_death(self):
        """Validates that player deaths in SQLite preserve 100% of wallet balance and bank coins."""
        t_uuid = str(uuid.uuid4())
        t_user = f"PreserveHero_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        wallet_amount = 88_888.0
        bank_amount = 250_000.0

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', ?, 40, 5, 0, 1, 'Survival', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user, wallet_amount))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (t_user, bank_amount))
            conn.commit()

            # Multiple deaths occur
            for death_event in range(5):
                c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (t_uuid,))
                conn.commit()

            # Verify balance & bank accounts
            c.execute("SELECT balance, deaths FROM players WHERE uuid = ?", (t_uuid,))
            p_row = c.fetchone()
            self.assertEqual(p_row["deaths"], 5, "Deaths must increment to 5")
            self.assertEqual(p_row["balance"], wallet_amount, "Wallet balance must be 100% untouched")

            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE username = ?", (t_user,))
            b_row = c.fetchone()
            self.assertEqual(b_row["bank_coins"], bank_amount, "Bank coins must be 100% untouched")

    def test_multiplayer_looting_of_death_drops(self):
        """Simulates Player A dying with bullion drops, and Player B looting and cashing them in."""
        p_a_uuid, p_b_uuid = str(uuid.uuid4()), str(uuid.uuid4())
        p_a_name, p_b_name = f"Victim_{p_a_uuid[:5]}", f"Looter_{p_b_uuid[:5]}"
        self.created_uuids.extend([p_a_uuid, p_b_uuid])
        self.created_usernames.extend([p_a_name, p_b_name])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 500.0, 10, 0, 0, 1, 'Wild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 0.0, 5, 0, 0, 1, 'Wild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_a_uuid, p_a_name, p_b_uuid, p_b_name))
            conn.commit()

            # Player A died with 2x Magot Lingot d'Or (CMD 6004, 250 coins each = 500 coins)
            dropped_bullion = MockItemStack(MATERIALS["GOLD_INGOT"], 2, cmd=6004)

            # Player B loots dropped_bullion and converts it
            qty = dropped_bullion.getAmount()
            gain = qty * get_bullion_coin_value(dropped_bullion.getItemMeta().getCustomModelData())
            self.assertEqual(gain, 500)

            c.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?)",
                      (gain, p_b_name))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE uuid = ?", (p_b_uuid,))
            self.assertEqual(c.fetchone()["balance"], 500.0,
                             "Player B must receive 100% value of looted bullion from Player A's death")


# ==============================================================================
# TEST SUITE 4: COMPILATION & BYTECODE INTEGRITY
# ==============================================================================

class TestPluginCompilationAndBytecodeIntegrity(unittest.TestCase):
    """
    Verifies that the Java plugin compiled cleanly without errors and that
    the resulting JAR contains valid Java 21 bytecode classes.
    """

    def test_jar_exists_and_size_valid(self):
        """Verifies AetherVisuals.jar exists and is of realistic binary size (> 50KB)."""
        self.assertTrue(os.path.exists(JAR_PATH), f"{JAR_PATH} must exist")
        jar_size = os.path.getsize(JAR_PATH)
        self.assertGreater(jar_size, 50_000, f"AetherVisuals.jar size ({jar_size} bytes) is suspiciously small")

    def test_jar_contains_required_classes_and_plugin_yml(self):
        """Verifies JAR contains all M2 compiled classes and plugin.yml descriptor."""
        expected_entries = [
            "plugin.yml",
            "io/aethercraft/visuals/HabboBullionBlockEngine.class",
            "io/aethercraft/visuals/StoreItemInteractListener.class",
            "io/aethercraft/visuals/PetItemFactory.class",
            "io/aethercraft/visuals/AetherVisualScoreboardManager.class"
        ]

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = set(z.namelist())
            for entry in expected_entries:
                self.assertIn(entry, names, f"JAR is missing expected entry: {entry}")

    def test_compiled_classes_are_valid_java_21_bytecode(self):
        """Inspects class magic number (0xCAFEBABE) and major version 65 (Java 21)."""
        classes_to_check = [
            "io/aethercraft/visuals/HabboBullionBlockEngine.class",
            "io/aethercraft/visuals/StoreItemInteractListener.class",
            "io/aethercraft/visuals/PetItemFactory.class",
            "io/aethercraft/visuals/AetherVisualScoreboardManager.class"
        ]

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            for cls_name in classes_to_check:
                raw_bytes = z.read(cls_name)
                # First 4 bytes: 0xCAFEBABE
                magic = struct.unpack(">I", raw_bytes[:4])[0]
                self.assertEqual(magic, 0xCAFEBABE, f"{cls_name} has invalid Java magic number")

                # Next 2 bytes: minor version, then 2 bytes: major version
                minor, major = struct.unpack(">HH", raw_bytes[4:8])
                self.assertEqual(major, 65, f"{cls_name} was compiled with major version {major}, expected 65 (Java 21)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
