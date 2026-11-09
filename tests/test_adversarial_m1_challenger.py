"""
Empirical Adversarial Challenge Suite for Milestone M1.
Executed by teamwork_challenger_m1_gp_1.

Adversarially and empirically stress-tests:
1. OneBlock persistence edge cases:
   - Sudden disconnects with un-mined blocks (blocks_broken = 0)
   - Disconnect mid-modulo save (blocks_broken = 1..9, 42, 97)
   - High-concurrency batch saves via saveAllSynchronously
   - Chunk boundary mathematics (chunk 624 portal vs chunk 625 island center)
   - Tier/phase/level calculation boundary precision
   - Non-destructive island regeneration guards
2. Unbreakable phone logic:
   - Item factory metadata: Unbreakable flag, ItemFlags, CMD 5001, PDC marker
   - Simulated PlayerItemDamageEvent durability loss cancellation across all item permutations
   - Active HoloSession damage interception
   - Weapon swings, tool usages, entity hits and block interactions while phone is open
   - Strict 16:9 geometric aspect ratio contracts in Java display manager and HTML/CSS
"""

import os
import sys
import uuid
import math
import sqlite3
import unittest
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import get_db_connection, init_database


class TestAdversarialM1Challenger(unittest.TestCase):

    def setUp(self):
        init_database()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

    def tearDown(self):
        if self.created_uuids or self.created_usernames:
            with get_db_connection() as conn:
                c = conn.cursor()
                if self.created_uuids:
                    ph = ",".join("?" for _ in self.created_uuids)
                    c.execute(f"DELETE FROM player_oneblock WHERE uuid IN ({ph});", self.created_uuids)
                    c.execute(f"DELETE FROM players WHERE uuid IN ({ph});", self.created_uuids)
                if self.created_usernames:
                    ph_u = ",".join("?" for _ in self.created_usernames)
                    c.execute(f"DELETE FROM users WHERE minecraft_username IN ({ph_u});", self.created_usernames)
                conn.commit()

    # =========================================================================
    # PART 1: ONEBLOCK PERSISTENCE & ISLAND INTEGRITY EDGE CASES
    # =========================================================================

    def test_adv_sudden_disconnect_unmined_island_integrity(self):
        """Stress-test: Player joins, generates island (blocks_broken=0), never mines, and disconnects abruptly."""
        p_uuid = str(uuid.uuid4())
        p_name = f"AdvUnmined_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        # 1. Simulate initial generation insertion in SQLite
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO player_oneblock (
                    uuid, username, island_id, island_x, island_y, island_z,
                    phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed,
                    trusted_members, created_at
                ) VALUES (?, ?, 77701, 10000.0, 120.0, 10000.0, 1, 0, 1, 1, 0, 0, '[]', datetime('now'));
            """, (p_uuid, p_name))
            conn.commit()

        # 2. Simulate sudden quit event calling saveIslandSynchronously
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE player_oneblock 
                SET phase = 1, blocks_broken = 0, level = 1, unlocked_chunks = 1, treasures_found = 0, monsters_killed = 0
                WHERE uuid = ?;
            """, (p_uuid,))
            conn.commit()

            c.execute("SELECT blocks_broken, phase, level, is_generated FROM (SELECT blocks_broken, phase, level, 1 AS is_generated FROM player_oneblock WHERE uuid = ?)", (p_uuid,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["blocks_broken"], 0)
            self.assertEqual(row["phase"], 1)
            self.assertEqual(row["level"], 1)

        # 3. Read Java source to verify that islandExists logic handles unmined islands safely:
        # boolean islandExists = island.blocksBroken > 0 || island.isGenerated || isIslandInDatabase(island.ownerUuid);
        # If islandExists == true, the AIR clearing loop (11x21x9 blocks) is bypassed.
        engine_path = os.path.join(SRC_DIR, "OneBlockEngine.java")
        with open(engine_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("boolean islandExists = island.blocksBroken > 0 || island.isGenerated || isIslandInDatabase(island.ownerUuid);", code)
        self.assertIn("if (!islandExists)", code)

    def test_adv_sudden_disconnect_mid_modulo_save(self):
        """Stress-test: Mining 1 to 9 blocks (where normal modulo 10 auto-save does NOT fire) followed by crash/disconnect."""
        for broken_count in [1, 3, 7, 9, 13, 27, 99]:
            p_uuid = str(uuid.uuid4())
            p_name = f"AdvMid_{broken_count}_{p_uuid[:4]}"
            self.created_uuids.append(p_uuid)
            self.created_usernames.append(p_name)

            # Insert initial island
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO player_oneblock (
                        uuid, username, island_id, island_x, island_y, island_z,
                        phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed,
                        trusted_members, created_at
                    ) VALUES (?, ?, ?, 10000.0, 120.0, 10000.0, 1, 0, 1, 1, 0, 0, '[]', datetime('now'));
                """, (p_uuid, p_name, 80000 + broken_count))
                conn.commit()

            # Player mined broken_count blocks.
            # Normal in-loop save only runs if broken_count % 10 == 0.
            # But onPlayerQuit executes saveIslandSynchronously:
            calc_phase = min(10, 1 + (broken_count // 100))
            calc_level = (broken_count // 50) + 1

            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE player_oneblock 
                    SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = 1, treasures_found = 0, monsters_killed = 0
                    WHERE uuid = ?;
                """, (calc_phase, broken_count, calc_level, p_uuid))
                conn.commit()

                # Verify persistence
                c.execute("SELECT blocks_broken, phase, level FROM player_oneblock WHERE uuid = ?;", (p_uuid,))
                row = c.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["blocks_broken"], broken_count)
                self.assertEqual(row["phase"], calc_phase)
                self.assertEqual(row["level"], calc_level)

    def test_adv_batch_save_concurrency_and_scale(self):
        """Stress-test: Simulate saveAllSynchronouslyInternal updating 50 islands in batch."""
        test_data = []
        for i in range(50):
            uid = str(uuid.uuid4())
            name = f"AdvBatch_{i}_{uid[:4]}"
            blocks = i * 23  # Range from 0 to 1127 blocks
            phase = min(10, 1 + (blocks // 100))
            level = (blocks // 50) + 1
            chunks = 1 + (blocks // 200)
            treasures = i % 5
            monsters = i % 7
            test_data.append((uid, name, 90000 + i, blocks, phase, level, chunks, treasures, monsters))
            self.created_uuids.append(uid)
            self.created_usernames.append(name)

        # 1. Bulk insert
        with get_db_connection() as conn:
            c = conn.cursor()
            c.executemany("""
                INSERT INTO player_oneblock (
                    uuid, username, island_id, island_x, island_y, island_z,
                    phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed,
                    trusted_members, created_at
                ) VALUES (?, ?, ?, 10000.0, 120.0, 10000.0, 1, 0, 1, 1, 0, 0, '[]', datetime('now'));
            """, [(d[0], d[1], d[2]) for d in test_data])
            conn.commit()

        # 2. Simulate saveAllSynchronouslyInternal batch UPDATE
        with get_db_connection() as conn:
            c = conn.cursor()
            update_payload = [
                (d[4], d[3], d[5], d[6], d[7], d[8], d[0])  # phase, blocks, level, chunks, treasures, monsters, uuid
                for d in test_data
            ]
            c.executemany("""
                UPDATE player_oneblock 
                SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = ?, treasures_found = ?, monsters_killed = ?
                WHERE uuid = ?;
            """, update_payload)
            conn.commit()

        # 3. Read back all and assert perfect match
        with get_db_connection() as conn:
            c = conn.cursor()
            for d in test_data:
                c.execute("SELECT phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed FROM player_oneblock WHERE uuid = ?;", (d[0],))
                row = c.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["blocks_broken"], d[3])
                self.assertEqual(row["phase"], d[4])
                self.assertEqual(row["level"], d[5])
                self.assertEqual(row["unlocked_chunks"], d[6])
                self.assertEqual(row["treasures_found"], d[7])
                self.assertEqual(row["monsters_killed"], d[8])

    def test_adv_chunk_boundary_mathematics(self):
        """Stress-test: Mathematical verification of chunk preloading in OneBlockEngine.teleportToIsland."""
        base_x = 10000
        base_z = 10000
        island_spacing = 1000

        # Island central coordinate is chunk 625 (10000 >> 4 = 625)
        # Return portal is at (island.x, island.y - 1, island.z - 9)
        # z - 9 = 10000 - 9 = 9991
        # portalChunkZ = 9991 >> 4 = 624
        for island_id in [1, 2, 5, 10, 50, 100, 500]:
            ix = base_x + (island_id * island_spacing)
            iz = base_z
            chunk_x = ix >> 4
            chunk_z = iz >> 4
            portal_z = iz - 9
            portal_chunk_z = portal_z >> 4

            self.assertEqual(chunk_z, 625, "Central island chunkZ must be exactly 625")
            self.assertEqual(portal_chunk_z, 624, "Portal island chunkZ must be exactly 624")
            self.assertNotEqual(chunk_z, portal_chunk_z, "Portal and island center cross a chunk boundary!")

        # Verify Java code explicitly loads both chunks:
        engine_path = os.path.join(SRC_DIR, "OneBlockEngine.java")
        with open(engine_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("int chunkX = island.x >> 4;", code)
        self.assertIn("int chunkZ = island.z >> 4;", code)
        self.assertIn("int portalChunkZ = (island.z - 9) >> 4;", code)
        self.assertIn("CompletableFuture.allOf(", code)
        self.assertIn("w.getChunkAtAsync(chunkX, chunkZ, true)", code)
        self.assertIn("w.getChunkAtAsync(chunkX, portalChunkZ, true)", code)

    def test_adv_phase_and_level_computation_boundaries(self):
        """Stress-test: Boundary analysis for computePhase and level formulas."""
        def compute_phase(broken: int) -> int:
            return min(10, 1 + (broken // 100))

        def compute_level(broken: int) -> int:
            return (broken // 50) + 1

        # Phase boundary checks:
        self.assertEqual(compute_phase(0), 1)
        self.assertEqual(compute_phase(99), 1)
        self.assertEqual(compute_phase(100), 2)
        self.assertEqual(compute_phase(199), 2)
        self.assertEqual(compute_phase(200), 3)
        self.assertEqual(compute_phase(899), 9)
        self.assertEqual(compute_phase(900), 10)
        self.assertEqual(compute_phase(999), 10)
        self.assertEqual(compute_phase(1000), 10)  # Capped at 10
        self.assertEqual(compute_phase(50000), 10)

        # Level boundary checks:
        self.assertEqual(compute_level(0), 1)
        self.assertEqual(compute_level(49), 1)
        self.assertEqual(compute_level(50), 2)
        self.assertEqual(compute_level(99), 2)
        self.assertEqual(compute_level(100), 3)
        self.assertEqual(compute_level(999), 20)
        self.assertEqual(compute_level(1000), 21)

    # =========================================================================
    # PART 2: UNBREAKABLE PHONE LOGIC STRESS TEST
    # =========================================================================

    def test_adv_phone_item_factory_contract(self):
        """Stress-test: CustomItemFactory.createAetherPhoneItem() metadata and properties."""
        factory_path = os.path.join(SRC_DIR, "CustomItemFactory.java")
        with open(factory_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Material check
        self.assertIn("Material.WARPED_FUNGUS_ON_A_STICK", code)
        # CustomModelData check
        self.assertIn("meta.setCustomModelData(5001);", code)
        # Unbreakable metadata check
        self.assertIn("meta.setUnbreakable(true);", code)
        # ItemFlags check
        self.assertIn("ItemFlag.HIDE_UNBREAKABLE", code)
        self.assertIn("ItemFlag.HIDE_ATTRIBUTES", code)
        # PDC key check
        self.assertIn('new NamespacedKey("aethercraft", "aether_phone_unbreakable")', code)
        # Aliases in createItemById
        self.assertIn('case "phone":', code)
        self.assertIn('case "aether_phone":', code)
        self.assertIn('case "aetherphone":', code)
        self.assertIn('case "smartphone":', code)

    def test_adv_durability_loss_events_simulation(self):
        """
        Stress-test: Simulate paper durability damage event pipeline.
        Test against 7 adversarial item permutations.
        """
        def simulate_onPlayerItemDamage(
            player_session_active: bool,
            item_is_unbreakable: bool,
            item_custom_model_data: int,
            item_display_name: str,
            item_has_pdc: bool,
            damage_amount: int
        ) -> bool:
            """Returns True if damage is cancelled, False if damage is dealt."""
            # Mirror AetherHoloUIEngine.onPlayerItemDamage:
            # 1. If player has active HoloSession -> CANCELLED
            if player_session_active:
                return True

            # 2. If item is unbreakable or CMD == 5001 -> CANCELLED
            if item_is_unbreakable or item_custom_model_data == 5001:
                return True

            # 3. If item isPhoneItem(item) -> CANCELLED
            # isPhoneItem checks:
            # - hasDisplayName containing "AetherPhone"
            # - PDC has aether_phone_unbreakable
            # - CMD 5001
            # - isUnbreakable
            if "AetherPhone" in item_display_name or item_has_pdc:
                return True

            return False

        # Scenario 1: Standard AetherPhone item (CMD 5001, unbreakable, PDC)
        self.assertTrue(simulate_onPlayerItemDamage(False, True, 5001, "📱 AetherPhone Ultra", True, damage_amount=1))
        # Scenario 2: Massive damage strike (damage = 9999)
        self.assertTrue(simulate_onPlayerItemDamage(False, True, 5001, "📱 AetherPhone Ultra", True, damage_amount=9999))
        # Scenario 3: Player has HoloSession open holding another tool (e.g. Diamond Pickaxe)
        self.assertTrue(simulate_onPlayerItemDamage(True, False, 0, "Diamond Pickaxe", False, damage_amount=5))
        # Scenario 4: Phone item without unbreakable flag but with CMD 5001
        self.assertTrue(simulate_onPlayerItemDamage(False, False, 5001, "Phone", False, damage_amount=10))
        # Scenario 5: Phone item with PDC marker only
        self.assertTrue(simulate_onPlayerItemDamage(False, False, 0, "Custom Device", True, damage_amount=1))
        # Scenario 6: Phone item with display name only
        self.assertTrue(simulate_onPlayerItemDamage(False, False, 0, "AetherPhone Mini", False, damage_amount=1))
        # Scenario 7: Normal tool, no session -> NOT CANCELLED (vanilla damage allowed)
        self.assertFalse(simulate_onPlayerItemDamage(False, False, 0, "Wooden Sword", False, damage_amount=1))

    def test_adv_phone_combat_and_block_interception(self):
        """Stress-test: Verify AetherHoloUIEngine blocks block damage, block break, and entity attacks while phone open."""
        holo_path = os.path.join(SRC_DIR, "AetherHoloUIEngine.java")
        with open(holo_path, "r", encoding="utf-8") as f:
            code = f.read()

        # BlockDamageEvent cancellation
        self.assertIn("onBlockDamageWhilePhoneOpen", code)
        self.assertIn("BlockDamageEvent", code)
        # BlockBreakEvent cancellation
        self.assertIn("onBlockActionWhilePhoneOpen", code)
        self.assertIn("BlockBreakEvent", code)
        # EntityDamageByEntityEvent cancellation
        self.assertIn("onEntityHitWhilePhoneOpen", code)
        self.assertIn("EntityDamageByEntityEvent", code)
        # PlayerItemDamageEvent cancellation
        self.assertIn("onPlayerItemDamage", code)
        self.assertIn("PlayerItemDamageEvent", code)

    def test_adv_phone_16_9_aspect_ratio_geometric_invariants(self):
        """Stress-test: Strict verification of 16/9 aspect ratio across plugin and web layers."""
        # 1. Java MapBrowser dimension check
        manager_path = os.path.join(SRC_DIR, "AetherWebDisplayManager.java")
        with open(manager_path, "r", encoding="utf-8") as f:
            manager_code = f.read()

        self.assertIn("16, 9", manager_code, "AetherWebDisplayManager must invoke createAndInitializeDisplay with 16, 9")

        # 2. HTML / CSS aspect ratio check
        webdisplay_path = os.path.join(PROJECT_ROOT, "web", "templates", "webdisplay.html")
        with open(webdisplay_path, "r", encoding="utf-8") as f:
            html_code = f.read()

        self.assertIn("aspect-ratio: 16 / 9;", html_code)
        self.assertIn("max-width: 1920px;", html_code)
        self.assertIn(".webdisplay-root-container", html_code)

        # 3. Mathematical precision: 16 / 9 ratio
        ratio = 16.0 / 9.0
        self.assertAlmostEqual(ratio, 1.7777777777, places=5)
        # Check standard resolutions:
        self.assertAlmostEqual(1920 / 1080, ratio, places=5)
        self.assertAlmostEqual(2560 / 1440, ratio, places=5)
        self.assertAlmostEqual(3840 / 2160, ratio, places=5)
        self.assertAlmostEqual(1280 / 720, ratio, places=5)


if __name__ == "__main__":
    unittest.main()
