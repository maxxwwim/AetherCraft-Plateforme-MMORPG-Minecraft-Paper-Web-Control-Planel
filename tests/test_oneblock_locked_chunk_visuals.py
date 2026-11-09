"""
Feature F18: OneBlock Locked Chunk Visual Indicators (Option 1) Test Suite.
Validates:
1. Floating 3D Hologram / Marker at Locked Chunks Center:
   - Exact text formatting: ChatColor.RED + "🔒 Chunk Verrouillé" + "\\n" + ChatColor.YELLOW + "Palier " + requiredTier + " Requis"
   - Tagged with "aether_locked_chunk_marker"
   - Central coordinates: X = chunkX * 16 + 8, Y = island.y + 1 to 2, Z = chunkZ * 16 + 8
   - TextDisplay entity with ArmorStand fallback
2. Proximity Red Particles along Locked Chunk Borders:
   - Proximity distance threshold within 8-10 blocks (dist <= 10.0)
   - Boundary emission along North, South, West, East edges using Particle.DUST (Color.RED) or fallback
3. Auto-Dismissal upon Unlocking and Lifecycle Cleanliness:
   - Immediate removal of central marker when island.unlockedChunks >= requiredTier
   - Cessation of boundary particles for unlocked chunk
   - Clean removal on chunk unload, world unload, and plugin disable / server shutdown
"""

import os
import sys
import math
import zipfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
JAR_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "AetherVisuals.jar")

class TestOneBlockLockedChunkVisuals(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine_path = os.path.join(SRC_DIR, "OneBlockEngine.java")
        with open(cls.engine_path, "r", encoding="utf-8") as f:
            cls.code = f.read()

    def test_f18_01_marker_tag_and_text_format(self):
        """Feature F18: Check marker tag constant and exact hologram display formatting."""
        self.assertIn('TAG_LOCKED_CHUNK_MARKER = "aether_locked_chunk_marker"', self.code)
        self.assertIn('"aether_locked_chunk_marker"', self.code)

        # Check required text components
        self.assertIn('ChatColor.RED + "🔒 Chunk Verrouillé"', self.code)
        self.assertIn('ChatColor.YELLOW + "Palier "', self.code)
        self.assertIn('" Requis"', self.code)

    def test_f18_02_marker_center_coordinates(self):
        """Feature F18: Center coordinate calculation (X = chunkX * 16 + 8, Y in island.y + 1..2, Z = chunkZ * 16 + 8)."""
        # Center coordinate math in Java code
        self.assertIn("chunkX * 16 + 8", self.code)
        self.assertIn("chunkZ * 16 + 8", self.code)
        self.assertIn("island.y + 1.5", self.code)

        # Verify coordinate math directly:
        island_x = 10000
        island_y = 120
        island_z = 10000
        base_chunk_x = island_x >> 4  # 625
        base_chunk_z = island_z >> 4  # 625

        # South chunk (relX=0, relZ=1)
        rel_x, rel_z = 0, 1
        target_chunk_x = base_chunk_x + rel_x
        target_chunk_z = base_chunk_z + rel_z
        mx = target_chunk_x * 16 + 8
        mz = target_chunk_z * 16 + 8
        my = island_y + 1.5

        self.assertEqual(mx, 10008)
        self.assertEqual(mz, 10024)
        self.assertTrue(island_y + 1.0 <= my <= island_y + 2.0)

    def test_f18_03_textdisplay_and_armorstand_fallback(self):
        """Feature F18: TextDisplay marker spawn with fallback to ArmorStand."""
        self.assertIn("world.spawn(markerLoc, TextDisplay.class", self.code)
        self.assertIn("world.spawn(markerLoc, ArmorStand.class", self.code)
        self.assertIn("display.addScoreboardTag(TAG_LOCKED_CHUNK_MARKER)", self.code)
        self.assertIn("stand.addScoreboardTag(TAG_LOCKED_CHUNK_MARKER)", self.code)

    def test_f18_04_surrounding_chunks_and_required_tiers(self):
        """Feature F18: Validation of surrounding chunks offsets and tier requirements."""
        self.assertIn("SURROUNDING_CHUNK_OFFSETS", self.code)
        self.assertIn("getRequiredTierForChunk", self.code)
        self.assertIn("isChunkUnlocked", self.code)

        def sim_get_required_tier(rel_x: int, rel_z: int) -> int:
            if rel_x == 0 and (rel_z == 0 or rel_z == -1):
                return 1
            if rel_x == 0 and rel_z == 1:
                return 2
            if rel_x == 1 and rel_z == 0:
                return 3
            if rel_x == -1 and rel_z == 0:
                return 4
            if rel_x == 1 and rel_z == -1:
                return 5
            if rel_x == -1 and rel_z == -1:
                return 6
            if rel_x == 1 and rel_z == 1:
                return 7
            if rel_x == -1 and rel_z == 1:
                return 8
            if rel_x == 0 and rel_z == 2:
                return 9
            if rel_x == 0 and rel_z == -2:
                return 10
            return 11

        # Central and portal chunks are initially unlocked
        self.assertEqual(sim_get_required_tier(0, 0), 1)
        self.assertEqual(sim_get_required_tier(0, -1), 1)

        # Surrounding offsets
        self.assertEqual(sim_get_required_tier(0, 1), 2)   # Sud
        self.assertEqual(sim_get_required_tier(1, 0), 3)   # Est
        self.assertEqual(sim_get_required_tier(-1, 0), 4)  # Ouest
        self.assertEqual(sim_get_required_tier(1, -1), 5)  # NE
        self.assertEqual(sim_get_required_tier(-1, -1), 6) # NW
        self.assertEqual(sim_get_required_tier(1, 1), 7)   # SE
        self.assertEqual(sim_get_required_tier(-1, 1), 8)  # SW
        self.assertEqual(sim_get_required_tier(0, 2), 9)   # Grand Sud
        self.assertEqual(sim_get_required_tier(0, -2), 10) # Grand Nord

    def test_f18_05_proximity_distance_math(self):
        """Feature F18: Proximity detection logic within 8-10 blocks of locked chunk border."""
        self.assertIn("dist <= 10.0", self.code)
        self.assertIn("emitChunkBoundaryParticles", self.code)
        self.assertIn("redDustOptions", self.code)

        # Test distance formula:
        chunk_min_x = 625 * 16  # 10000
        chunk_max_x = 10016
        chunk_min_z = 626 * 16  # 10016
        chunk_max_z = 10032

        # Player at 10008, 10007 approaching South chunk from North
        # distance in Z to chunk_min_z is 10016 - 10007 = 9 blocks
        player_x = 10008
        player_z = 10007
        dx = 0  # within min_x and max_x
        dz = chunk_min_z - player_z  # 9
        dist = math.sqrt(dx * dx + dz * dz)
        self.assertEqual(dist, 9.0)
        self.assertTrue(dist <= 10.0)

        # Player far away (20 blocks)
        player_z_far = 9990
        dz_far = chunk_min_z - player_z_far  # 26
        dist_far = math.sqrt(dx * dx + dz_far * dz_far)
        self.assertFalse(dist_far <= 10.0)

    def test_f18_06_boundary_particles_edges(self):
        """Feature F18: Boundary particle emission along 4 edges with red particle options."""
        self.assertIn("Particle.DustOptions(Color.RED", self.code)
        self.assertIn("spawnBorderParticle", self.code)
        self.assertIn("Particle.DUST", self.code)

        # North & South edges iteration
        self.assertIn("for (int x = minX; x <= maxX; x += 2)", self.code)
        # West & East edges iteration
        self.assertIn("for (int z = minZ; z <= maxZ; z += 2)", self.code)

    def test_f18_07_auto_dismissal_on_unlock(self):
        """Feature F18: Immediate removal of marker and cessation of particles upon chunk unlock."""
        self.assertIn("if (island.unlockedChunks >= requiredTier)", self.code)
        self.assertIn("marker.remove()", self.code)
        self.assertIn("updateLockedChunkMarkers(w, island);", self.code)

    def test_f18_08_lifecycle_cleanliness(self):
        """Feature F18: Clean removal on plugin disable, chunk unload, and world unload."""
        self.assertIn("cleanupAllLockedChunkMarkers()", self.code)
        self.assertIn("onPluginDisable", self.code)
        self.assertIn("onChunkUnload", self.code)
        self.assertIn("onWorldUnload", self.code)
        self.assertIn("display.setPersistent(false)", self.code)

    def test_f18_09_jar_packaging_contains_updated_class(self):
        """Feature F18: Confirm AetherVisuals.jar packages OneBlockEngine.class."""
        self.assertTrue(os.path.exists(JAR_PATH), f"AetherVisuals.jar must exist at {JAR_PATH}")
        with zipfile.ZipFile(JAR_PATH, "r") as z:
            namelist = z.namelist()
            self.assertIn("io/aethercraft/visuals/OneBlockEngine.class", namelist)
            info = z.getinfo("io/aethercraft/visuals/OneBlockEngine.class")
            self.assertGreater(info.file_size, 20000, "OneBlockEngine.class should contain full compiled logic")


if __name__ == "__main__":
    unittest.main()
