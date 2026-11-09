"""
Validation Test Suite for Milestone M4 (Spawn Cleanup, Server Optimizations, Dungeons & Nether Aether Blocks)
Verifies:
- F12: Spawn gold slabs removal, polished blackstone pressure plates, and cleanSpawnGoldSlabs cleaner
- F13: Paper 1.21.1 server performance configurations (server.properties, bukkit.yml, spigot.yml, paper-world-defaults.yml)
- F14: Dungeon Mob health rebalance (Titan boss base HP 90.0) and wave 1-4 creature diversity (Bogged, Stray, Drowned, Evoker)
- F15: Dungeon Key access gating (CustomModelData 2003 / Pass des Donjons), key consumption, and VIP/Champion bypass
- F20: Aether Blocks in Nether generation (AetherNetherOreEngine.java) and registration in AetherVisualsPlugin
"""

import os
import sys
import unittest
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")


class TestM4WorkerValidation(unittest.TestCase):

    def test_f12_spawn_gold_slabs_removal_and_cleaner(self):
        """F12: Verify CelestialSpawnBuilder and SpawnAmbianceEngine jump pads & gold removal."""
        builder_file = os.path.join(SRC_DIR, "CelestialSpawnBuilder.java")
        ambiance_file = os.path.join(SRC_DIR, "SpawnAmbianceEngine.java")
        plugin_file = os.path.join(SRC_DIR, "AetherVisualsPlugin.java")

        self.assertTrue(os.path.exists(builder_file))
        self.assertTrue(os.path.exists(ambiance_file))
        self.assertTrue(os.path.exists(plugin_file))

        with open(builder_file, "r", encoding="utf-8") as f:
            builder_code = f.read()

        with open(ambiance_file, "r", encoding="utf-8") as f:
            ambiance_code = f.read()

        with open(plugin_file, "r", encoding="utf-8") as f:
            plugin_code = f.read()

        # Contract F12: buildJumpPads must NOT place LIGHT_WEIGHTED_PRESSURE_PLATE
        self.assertNotIn("Material.LIGHT_WEIGHTED_PRESSURE_PLATE", builder_code,
                         "LIGHT_WEIGHTED_PRESSURE_PLATE must be removed from CelestialSpawnBuilder")

        # Contract F12: buildJumpPads must use POLISHED_BLACKSTONE_PRESSURE_PLATE
        self.assertIn("Material.POLISHED_BLACKSTONE_PRESSURE_PLATE", builder_code,
                      "CelestialSpawnBuilder must use POLISHED_BLACKSTONE_PRESSURE_PLATE on jump pads")

        # Contract F12: cleanSpawnGoldSlabs method must exist in CelestialSpawnBuilder
        self.assertIn("cleanSpawnGoldSlabs", builder_code,
                      "CelestialSpawnBuilder must provide cleanSpawnGoldSlabs method")

        # Contract F12: cleanSpawnGoldSlabs must be called in AetherVisualsPlugin
        self.assertIn("cleanSpawnGoldSlabs", plugin_code,
                      "AetherVisualsPlugin must invoke cleanSpawnGoldSlabs on startup")

        # Contract F12: SpawnAmbianceEngine must handle POLISHED_BLACKSTONE_PRESSURE_PLATE
        self.assertIn("Material.POLISHED_BLACKSTONE_PRESSURE_PLATE", ambiance_code,
                      "SpawnAmbianceEngine must accept POLISHED_BLACKSTONE_PRESSURE_PLATE for jump pad trigger")

    def test_f13_server_performance_configurations(self):
        """F13: Verify tuned parameters in server.properties, bukkit.yml, spigot.yml, and paper-world-defaults.yml."""
        # 1. server.properties
        prop_path = os.path.join(SERVER_DIR, "server.properties")
        with open(prop_path, "r", encoding="utf-8") as f:
            props = dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))

        self.assertEqual(props.get("sync-chunk-writes"), "false", "sync-chunk-writes must be false")
        self.assertEqual(props.get("view-distance"), "8", "view-distance must be tuned to 8")
        self.assertEqual(props.get("simulation-distance"), "5", "simulation-distance must be tuned to 5")
        self.assertEqual(props.get("max-chained-neighbor-updates"), "10000", "max-chained-neighbor-updates must be 10000")
        self.assertEqual(props.get("network-compression-threshold"), "256", "network-compression-threshold must be 256")

        # 2. bukkit.yml
        bukkit_path = os.path.join(SERVER_DIR, "bukkit.yml")
        with open(bukkit_path, "r", encoding="utf-8") as f:
            bukkit_cfg = yaml.safe_load(f)

        self.assertGreaterEqual(bukkit_cfg["ticks-per"].get("autosave", 0), 6000, "autosave must be >= 6000 ticks")
        self.assertEqual(bukkit_cfg["spawn-limits"].get("monsters"), 50, "monster spawn limit must be 50")
        self.assertEqual(bukkit_cfg["spawn-limits"].get("animals"), 10, "animal spawn limit must be 10")
        self.assertEqual(bukkit_cfg["spawn-limits"].get("water-animals"), 5, "water-animals spawn limit must be 5")
        self.assertEqual(bukkit_cfg["spawn-limits"].get("ambient"), 1, "ambient spawn limit must be 1")

        # 3. spigot.yml
        spigot_path = os.path.join(SERVER_DIR, "spigot.yml")
        with open(spigot_path, "r", encoding="utf-8") as f:
            spigot_cfg = yaml.safe_load(f)

        world_default = spigot_cfg["world-settings"]["default"]
        tracking = world_default["entity-tracking-range"]
        self.assertEqual(tracking.get("players"), 48, "entity-tracking-range players must be 48")
        self.assertEqual(tracking.get("animals"), 32, "entity-tracking-range animals must be 32")
        self.assertEqual(tracking.get("monsters"), 48, "entity-tracking-range monsters must be 48")
        self.assertEqual(tracking.get("misc"), 32, "entity-tracking-range misc must be 32")
        self.assertFalse(world_default["entity-activation-range"].get("tick-inactive-villagers"),
                         "tick-inactive-villagers must be false")
        self.assertEqual(world_default["merge-radius"].get("item"), 2.5, "merge-radius.item must be 2.5")

        # 4. paper-world-defaults.yml
        paper_path = os.path.join(SERVER_DIR, "config", "paper-world-defaults.yml")
        with open(paper_path, "r", encoding="utf-8") as f:
            paper_cfg = yaml.safe_load(f)

        self.assertEqual(paper_cfg["misc"].get("redstone-implementation"), "ALTERNATE_CURRENT",
                         "redstone-implementation must be ALTERNATE_CURRENT")
        self.assertFalse(paper_cfg["entities"]["armor-stands"].get("tick"),
                         "armor-stands.tick must be false")
        self.assertTrue(paper_cfg["entities"]["spawning"]["alt-item-despawn-rate"].get("enabled"),
                        "alt-item-despawn-rate.enabled must be true")
        self.assertIn("despawn-ranges", paper_cfg["entities"]["spawning"],
                      "despawn-ranges must be configured")

    def test_f14_dungeon_mob_health_and_wave_diversity(self):
        """F14: Verify Titan boss base HP = 90.0, 250.0 removed, and 1.21 creature diversity."""
        spawner_file = os.path.join(SRC_DIR, "DungeonWaveSpawner.java")
        affix_file = os.path.join(SRC_DIR, "MobAffixEngine.java")

        with open(spawner_file, "r", encoding="utf-8") as f:
            spawner_code = f.read()

        with open(affix_file, "r", encoding="utf-8") as f:
            affix_code = f.read()

        # Boss HP checks
        self.assertIn("90.0", spawner_code, "Titan Boss base HP must be 90.0")
        self.assertNotIn("250.0", spawner_code, "Titan Boss excessive 250.0 base HP must be removed")

        # Wave creature diversity checks: Bogged, Stray, Drowned, Evoker
        for mob in ["BOGGED", "STRAY", "DROWNED", "EVOKER"]:
            self.assertIn(mob, spawner_code, f"DungeonWaveSpawner must include {mob} in wave tables")

        # Affix multiplier proportional scaling
        self.assertIn("2.2, 1.6", affix_code,
                      "MobAffixEngine AffixTier.TITAN must be scaled proportionally (2.2 health, 1.6 damage)")

    def test_f15_dungeon_pass_key_gating_and_bypass(self):
        """F15: Verify Dungeon pass key validation, consumption, and VIP/Champion rank bypass."""
        engine_file = os.path.join(SRC_DIR, "DungeonWaveEngine.java")
        with open(engine_file, "r", encoding="utf-8") as f:
            engine_code = f.read()

        # Key detection
        self.assertIn("2003", engine_code, "DungeonWaveEngine must check CustomModelData 2003")
        self.assertIn("Pass des Donjons", engine_code, "DungeonWaveEngine must check 'Pass des Donjons'")
        self.assertIn("consumeDungeonKey", engine_code, "DungeonWaveEngine must consume key on entry")

        # VIP/Champion bypass
        self.assertIn("hasDungeonBypass", engine_code, "DungeonWaveEngine must define hasDungeonBypass")
        self.assertIn("aether.dungeon.unlimited", engine_code,
                      "DungeonWaveEngine must check permission aether.dungeon.unlimited")
        self.assertIn("VIP", engine_code, "DungeonWaveEngine must check VIP rank")
        self.assertIn("CHAMPION", engine_code, "DungeonWaveEngine must check CHAMPION rank")

        # Exact rejected message
        self.assertIn("Vous devez posséder une Clé de Donjon (disponible en boutique) pour entrer !", engine_code,
                      "DungeonWaveEngine must show exact user rejection message when pass is missing")

    def test_f20_aether_nether_ore_generation_engine(self):
        """F20: Verify AetherNetherOreEngine generates exclusively in Nether and is registered in plugin."""
        ore_file = os.path.join(SRC_DIR, "AetherNetherOreEngine.java")
        plugin_file = os.path.join(SRC_DIR, "AetherVisualsPlugin.java")

        self.assertTrue(os.path.exists(ore_file), "AetherNetherOreEngine.java must exist")

        with open(ore_file, "r", encoding="utf-8") as f:
            ore_code = f.read()

        with open(plugin_file, "r", encoding="utf-8") as f:
            plugin_code = f.read()

        # Listener registration
        self.assertIn("AetherNetherOreEngine", plugin_code,
                      "AetherVisualsPlugin must instantiate and register AetherNetherOreEngine")
        self.assertIn("netherOreEngine", plugin_code,
                      "AetherVisualsPlugin must hold netherOreEngine reference")

        # Exclusively in Nether
        self.assertIn("isNetherWorld", ore_code, "AetherNetherOreEngine must check Nether dimension")
        self.assertIn("world_nether", ore_code, "AetherNetherOreEngine must reference world_nether")

        # Event listeners: ChunkLoadEvent and BlockBreakEvent
        self.assertIn("ChunkLoadEvent", ore_code, "AetherNetherOreEngine must listen to ChunkLoadEvent")
        self.assertIn("BlockBreakEvent", ore_code, "AetherNetherOreEngine must listen to BlockBreakEvent")

        # Generation parameters: ANCIENT_DEBRIS, NETHERRACK, Y between 15 and 95
        self.assertIn("ANCIENT_DEBRIS", ore_code, "Ore generation must place ANCIENT_DEBRIS")
        self.assertIn("NETHERRACK", ore_code, "Ore generation must replace NETHERRACK")
        self.assertIn("15", ore_code, "Ore generation must define Y floor at 15")
        self.assertIn("95", ore_code, "Ore generation must define Y ceiling at 95")

        # Custom item drop on mine: minerai_aether
        self.assertIn("minerai_aether", ore_code, "Mining Aether ore must drop minerai_aether")


if __name__ == "__main__":
    unittest.main()
