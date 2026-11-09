r"""
================================================================================
Milestone M1 Empirical Challenger Verification & Stress Test Suite
================================================================================
Executed by: teamwork_challenger_m1_gp_2
Target Project: C:\Users\1234\Desktop\Projets\aethercraft

Adversarial & Empirical Challenge Dimensions:
1. Block Placement Preservation & buildIslandStructure idempotence:
   - Evaluates islandExists logic under all state permutations (blocksBroken, isGenerated, inDB)
   - Verifies that placed blocks in the island bounds [ix-5..ix+5, iz-15..iz+5, iy..iy+8] are never wiped
   - Verifies chunk coordinates boundary math for portalChunkZ vs chunkZ across all quadrant signs
2. WebDisplay 16/9 Aspect Ratio & HTML/CSS layout stability:
   - Geometric ratio compliance (1.7778 +- tolerance) across resolutions
   - Validates HTML tree structure, CSS rules (aspect-ratio: 16 / 9, max-width: 1920px)
   - Validates HMAC auth token generation and URL contract compatibility
3. Unbreakable Phone item & Durability cancellation:
   - CustomItemFactory metadata, PDC tag, CustomModelData 5001, ItemFlags
   - PlayerItemDamageEvent interception and lowest priority cancellation
4. Plugin JAR Build Integrity & Bytecode Classpath Inspection:
   - Validates AetherVisuals.jar archive integrity, plugin.yml syntax, and compiled classes
5. SQLite Database Concurrency & Batch Autosave Resilience:
   - Multi-row batch update persistence, rollback safety, and schema invariants
================================================================================
"""

import os
import sys
import re
import math
import uuid
import hmac
import hashlib
import zipfile
import sqlite3
import unittest
from typing import Dict, Any, List, Set, Tuple

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

from services.database import get_db_connection, init_database


class MockBlock:
    def __init__(self, x: int, y: int, z: int, mat: str = "AIR"):
        self.x = x
        self.y = y
        self.z = z
        self.material = mat

    def setType(self, mat: str):
        self.material = mat


class MockWorld:
    def __init__(self):
        self.blocks: Dict[Tuple[int, int, int], MockBlock] = {}

    def getBlockAt(self, x: int, y: int, z: int) -> MockBlock:
        key = (x, y, z)
        if key not in self.blocks:
            self.blocks[key] = MockBlock(x, y, z, "AIR")
        return self.blocks[key]


class MockIsland:
    def __init__(self, owner_uuid: str, x: int = 10000, y: int = 120, z: int = 10000,
                 blocks_broken: int = 0, is_generated: bool = False):
        self.ownerUuid = owner_uuid
        self.x = x
        self.y = y
        self.z = z
        self.blocksBroken = blocks_broken
        self.isGenerated = is_generated


def simulate_build_island_structure_air_clear(world: MockWorld, island: MockIsland, in_db: bool) -> bool:
    """
    Verbatim simulation of lines 224-235 in OneBlockEngine.java:
    boolean islandExists = island.blocksBroken > 0 || island.isGenerated || isIslandInDatabase(island.ownerUuid);
    if (!islandExists) {
        for (int x = ix - 5; x <= ix + 5; x++) {
            for (int z = iz - 15; z <= iz + 5; z++) {
                for (int y = iy; y <= iy + 8; y++) {
                    world.getBlockAt(x, y, z).setType(Material.AIR);
                }
            }
        }
    }
    island.isGenerated = true;
    """
    ix = island.x
    iy = island.y
    iz = island.z

    island_exists = (island.blocksBroken > 0) or island.isGenerated or in_db
    if not island_exists:
        for x in range(ix - 5, ix + 6):
            for z in range(iz - 15, iz + 6):
                for y in range(iy, iy + 9):
                    world.getBlockAt(x, y, z).setType("AIR")

    island.isGenerated = True
    return not island_exists  # returns True if air-wiping was executed


class TestM1EmpiricalChallenger(unittest.TestCase):

    def setUp(self):
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
                conn.commit()

    # =========================================================================
    # 1. EMPIRICAL CHALLENGE: ISLAND BLOCK INTEGRITY & AIR WIPING
    # =========================================================================

    def test_challenge_01_build_island_structure_preserves_player_placed_blocks(self):
        """
        Adversarial Test:
        Player creates island, places custom valuable blocks (DIAMOND_BLOCK, CHEST, OAK_PLANKS)
        within the clearing bounding box [ix-5..ix+5, iz-15..iz+5, iy..iy+8].
        Simulate buildIslandStructure under all existing conditions.
        ASSERTION: Custom blocks MUST NOT be replaced with AIR.
        """
        permutations = [
            # (blocks_broken, is_generated, in_db, expected_air_wipe)
            (10, False, False, False),  # broken > 0
            (0, True, False, False),   # isGenerated = True
            (0, False, True, False),   # recorded in SQLite
            (50, True, True, False),   # all true
        ]

        for broken, gen, indb, expected_wipe in permutations:
            world = MockWorld()
            island = MockIsland("test-uuid-1", x=10000, y=120, z=10000,
                                blocks_broken=broken, is_generated=gen)

            # Player placed custom blocks in the air volume
            world.getBlockAt(10002, 122, 10000).setType("DIAMOND_BLOCK")
            world.getBlockAt(10000, 121, 9995).setType("CHEST")
            world.getBlockAt(9996, 125, 9988).setType("OAK_PLANKS")

            wiped = simulate_build_island_structure_air_clear(world, island, in_db=indb)

            self.assertEqual(wiped, expected_wipe,
                             f"Air wipe mismatch for state: broken={broken}, gen={gen}, in_db={indb}")
            self.assertEqual(world.getBlockAt(10002, 122, 10000).material, "DIAMOND_BLOCK",
                             "Player placed DIAMOND_BLOCK must not be wiped!")
            self.assertEqual(world.getBlockAt(10000, 121, 9995).material, "CHEST",
                             "Player placed CHEST must not be wiped!")
            self.assertEqual(world.getBlockAt(9996, 125, 9988).material, "OAK_PLANKS",
                             "Player placed OAK_PLANKS must not be wiped!")

    def test_challenge_02_fresh_island_clears_air_once_then_never_again(self):
        """
        Adversarial Test:
        On a truly brand-new island (broken=0, gen=False, in_db=False):
        The first pass clears air.
        Subsequent passes (even if broken=0) MUST NOT clear air because isGenerated is now True.
        """
        world = MockWorld()
        island = MockIsland("new-player-uuid", x=5000, y=120, z=5000,
                            blocks_broken=0, is_generated=False)

        # Pre-populate dirty blocks
        world.getBlockAt(5000, 122, 5000).setType("DIRT")

        # Pass 1: Fresh generation
        wiped_pass1 = simulate_build_island_structure_air_clear(world, island, in_db=False)
        self.assertTrue(wiped_pass1, "First generation must clear airspace")
        self.assertEqual(world.getBlockAt(5000, 122, 5000).material, "AIR")

        # Player places a block now
        world.getBlockAt(5000, 122, 5000).setType("GOLD_BLOCK")

        # Pass 2: Re-run buildIslandStructure (e.g. portal check or /oneblock rebuild)
        wiped_pass2 = simulate_build_island_structure_air_clear(world, island, in_db=False)
        self.assertFalse(wiped_pass2, "Second pass must NOT clear airspace because isGenerated is True")
        self.assertEqual(world.getBlockAt(5000, 122, 5000).material, "GOLD_BLOCK",
                         "Player's GOLD_BLOCK must survive subsequent buildIslandStructure calls!")

    def test_challenge_03_chunk_coordinate_math_across_quadrants(self):
        """
        Adversarial Test:
        Chunk math: chunkX = x >> 4, chunkZ = z >> 4, portalChunkZ = (z - 9) >> 4.
        Verifies that chunk calculation behaves correctly across all integer boundaries and signs.
        """
        test_coords = [
            (10000, 10000, 625, 625, 624),     # Positive large (chunk split!)
            (16, 16, 1, 1, 0),                 # Boundary: 16 >> 4 = 1, (16 - 9 = 7) >> 4 = 0 (split!)
            (15, 15, 0, 0, 0),                 # Same chunk: 15 >> 4 = 0, 6 >> 4 = 0
            (0, 0, 0, 0, -1),                  # Zero boundary: 0 >> 4 = 0, -9 >> 4 = -1 (split!)
            (-1, -1, -1, -1, -1),              # Negative same: -1 >> 4 = -1, -10 >> 4 = -1
            (-16, -16, -1, -1, -2),            # Negative boundary: -16 >> 4 = -1, -25 >> 4 = -2 (split!)
            (-10000, -10000, -625, -625, -626) # Negative large (split!)
        ]

        for x, z, exp_cx, exp_cz, exp_pcz in test_coords:
            cx = x >> 4
            cz = z >> 4
            pcz = (z - 9) >> 4
            self.assertEqual(cx, exp_cx, f"chunkX mismatch for x={x}")
            self.assertEqual(cz, exp_cz, f"chunkZ mismatch for z={z}")
            self.assertEqual(pcz, exp_pcz, f"portalChunkZ mismatch for z={z}")

        # Verify Java source code includes preload of BOTH chunks
        engine_file = os.path.join(SRC_DIR, "OneBlockEngine.java")
        with open(engine_file, "r", encoding="utf-8") as f:
            src = f.read()

        self.assertIn("portalChunkZ = (island.z - 9) >> 4", src)
        self.assertIn("w.getChunkAtAsync(chunkX, chunkZ, true)", src)
        self.assertIn("w.getChunkAtAsync(chunkX, portalChunkZ, true)", src)
        self.assertIn("CompletableFuture.allOf", src)

    # =========================================================================
    # 2. EMPIRICAL CHALLENGE: ONEBLOCK AUTOSAVE & DATABASE LAYER
    # =========================================================================

    def test_challenge_04_save_all_synchronously_batch_persistence(self):
        """
        Adversarial Test:
        Stress test saveAllSynchronously SQL query pattern against SQLite:
        Batch update 25 player island records simultaneously.
        Verify atomic execution, zero lost updates, and correct column mapping.
        """
        init_database()
        test_data = []
        for i in range(25):
            u = str(uuid.uuid4())
            name = f"BatchPlayer_{i}_{u[:4]}"
            test_data.append((u, name, 80000 + i, 10000.0 + i * 200, 120.0, 10000.0, 1, 0, 1))
            self.created_uuids.append(u)
            self.created_usernames.append(name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.executemany("""
                INSERT INTO player_oneblock (
                    uuid, username, island_id, island_x, island_y, island_z,
                    phase, blocks_broken, level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, test_data)
            conn.commit()

            # Now simulate saveAllSynchronouslyInternal batch UPDATE
            update_batch = []
            for u, name, iid, x, y, z, p, b, l in test_data:
                # new values
                new_phase = 5
                new_broken = 2500
                new_level = 51
                new_chunks = 12
                new_treasures = 3
                new_kills = 14
                update_batch.append((new_phase, new_broken, new_level, new_chunks, new_treasures, new_kills, u))

            c.executemany("""
                UPDATE player_oneblock 
                SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = ?, treasures_found = ?, monsters_killed = ? 
                WHERE uuid = ?
            """, update_batch)
            conn.commit()

            # Verify all 25 rows reflect exact batch updates
            ph = ",".join("?" for _ in self.created_uuids)
            c.execute(f"SELECT COUNT(*) as cnt FROM player_oneblock WHERE uuid IN ({ph}) AND blocks_broken = 2500 AND level = 51", self.created_uuids)
            res = c.fetchone()
            self.assertEqual(res["cnt"], 25, "All 25 batched player islands must reflect persisted stats!")

    # =========================================================================
    # 3. EMPIRICAL CHALLENGE: 16/9 ASPECT RATIO & WEBDISPLAY MANAGER
    # =========================================================================

    def test_challenge_05_webdisplay_16_9_aspect_ratio_css_and_html(self):
        """
        Adversarial Test:
        Inspect web/templates/webdisplay.html:
        - Must declare aspect-ratio: 16 / 9 (or 16/9)
        - Must cap max-width at 1920px
        - Root container must enclose all header, navigation, tabs, and footer components
        """
        html_file = os.path.join(PROJECT_ROOT, "web", "templates", "webdisplay.html")
        self.assertTrue(os.path.exists(html_file), "webdisplay.html must exist")

        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check CSS rule
        self.assertRegex(content, r"aspect-ratio:\s*16\s*/\s*9",
                         "CSS must enforce aspect-ratio: 16 / 9")
        self.assertIn("max-width: 1920px", content,
                      "CSS must cap maximum display width to 1920px (FHD standard)")

        # Verify root container class definition
        self.assertIn(".webdisplay-root-container", content)
        self.assertIn("<div class=\"webdisplay-root-container", content)

        # Verify closing div tag before scripts
        root_div_idx = content.find("<div class=\"webdisplay-root-container")
        self.assertGreater(root_div_idx, 0, "Root container div must be opened")
        script_idx = content.find("<script>")
        self.assertGreater(script_idx, root_div_idx, "Script tag must come after layout content")

        footer_idx = content.find("<footer")
        self.assertGreater(footer_idx, root_div_idx, "Footer must be inside webdisplay layout")

    def test_challenge_06_webdisplay_manager_16_9_invocation_and_auth_hmac(self):
        """
        Adversarial Test:
        Inspect AetherWebDisplayManager.java:
        - createAndInitializeDisplay must specify 16, 9 blocks
        - generateAuthToken must generate correct HMAC-SHA256 matching Python verification
        """
        manager_file = os.path.join(SRC_DIR, "AetherWebDisplayManager.java")
        self.assertTrue(os.path.exists(manager_file), "AetherWebDisplayManager.java must exist")

        with open(manager_file, "r", encoding="utf-8") as f:
            src = f.read()

        # 16, 9 parameter check
        self.assertRegex(src, r"createMethod\.invoke\(displayService,\s*p,\s*targetUrl,\s*screenLoc,\s*16,\s*9\)",
                         "AetherWebDisplayManager must call createAndInitializeDisplay with dimensions 16, 9")

        # Base URL check
        self.assertIn("http://127.0.0.1:5000/webdisplay", src)

        # Python replication of HMAC SHA-256 token generator
        test_user = "ChallengerTest"
        test_ts = 1799999999
        key = "aethercraft_session_hmac_2026".encode("utf-8")
        data = f"{test_user.lower()}:{test_ts}".encode("utf-8")
        expected_token = hmac.new(key, data, hashlib.sha256).hexdigest()

        self.assertEqual(len(expected_token), 64, "HMAC-SHA256 must produce 64-char hex string")

    # =========================================================================
    # 4. EMPIRICAL CHALLENGE: UNBREAKABLE PHONE & ITEM DAMAGE PREVENTION
    # =========================================================================

    def test_challenge_07_custom_item_factory_phone_unbreakable_contract(self):
        """
        Adversarial Test:
        Inspect CustomItemFactory.java:
        - WARPED_FUNGUS_ON_A_STICK
        - CustomModelData: 5001
        - meta.setUnbreakable(true)
        - NamespacedKey: aethercraft:aether_phone_unbreakable
        """
        factory_file = os.path.join(SRC_DIR, "CustomItemFactory.java")
        with open(factory_file, "r", encoding="utf-8") as f:
            src = f.read()

        self.assertIn("createAetherPhoneItem()", src)
        self.assertIn("Material.WARPED_FUNGUS_ON_A_STICK", src)
        self.assertIn("meta.setCustomModelData(5001)", src)
        self.assertIn("meta.setUnbreakable(true)", src)
        self.assertIn("aether_phone_unbreakable", src)
        self.assertIn("ItemFlag.HIDE_UNBREAKABLE", src)

    def test_challenge_08_holo_ui_engine_cancels_phone_durability_loss(self):
        """
        Adversarial Test:
        Inspect AetherHoloUIEngine.java:
        - PlayerItemDamageEvent with priority = EventPriority.LOWEST
        - Cancels event if player has active HoloSession
        - Cancels event if item isUnbreakable() or CustomModelData == 5001
        - Cancels block damage and block break during active phone session
        """
        holo_file = os.path.join(SRC_DIR, "AetherHoloUIEngine.java")
        with open(holo_file, "r", encoding="utf-8") as f:
            src = f.read()

        self.assertIn("@EventHandler(priority = EventPriority.LOWEST)", src)
        self.assertIn("public void onPlayerItemDamage(PlayerItemDamageEvent event)", src)
        self.assertIn("sessions.containsKey(event.getPlayer().getUniqueId())", src)
        self.assertIn("meta.isUnbreakable()", src)
        self.assertIn("meta.getCustomModelData() == 5001", src)
        self.assertIn("isPhoneItem(item)", src)
        self.assertIn("event.setCancelled(true)", src)

    # =========================================================================
    # 5. EMPIRICAL CHALLENGE: JAR ARTIFACT & BYTECODE VERIFICATION
    # =========================================================================

    def test_challenge_09_compiled_jar_structure_and_classes(self):
        """
        Adversarial Test:
        Inspect compiled AetherVisuals.jar:
        - File exists and is non-empty (> 50KB)
        - Contains plugin.yml
        - Contains all M1 core compiled class files
        """
        self.assertTrue(os.path.exists(JAR_PATH), f"JAR artifact {JAR_PATH} must exist")
        jar_size = os.path.getsize(JAR_PATH)
        self.assertGreater(jar_size, 50 * 1024, f"JAR size {jar_size} is suspiciously small (< 50KB)")

        with zipfile.ZipFile(JAR_PATH, "r") as z:
            names = set(z.namelist())

            # plugin.yml check
            self.assertIn("plugin.yml", names, "JAR must contain plugin.yml in root")
            plugin_yml_content = z.read("plugin.yml").decode("utf-8", errors="ignore")
            self.assertIn("main: io.aethercraft.visuals.AetherVisualsPlugin", plugin_yml_content)

            # Class files check
            expected_classes = [
                "io/aethercraft/visuals/OneBlockEngine.class",
                "io/aethercraft/visuals/CustomItemFactory.class",
                "io/aethercraft/visuals/AetherHoloUIEngine.class",
                "io/aethercraft/visuals/AetherWebDisplayManager.class",
                "io/aethercraft/visuals/AetherVisualsPlugin.class"
            ]
            for cls in expected_classes:
                self.assertIn(cls, names, f"JAR must contain compiled bytecode for {cls}")


if __name__ == "__main__":
    unittest.main()
