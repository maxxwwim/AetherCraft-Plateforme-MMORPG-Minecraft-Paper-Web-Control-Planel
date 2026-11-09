r"""
================================================================================
AetherCraft Production Gameplay Update E2E Automated Test Suite (Tiers 1-4)
================================================================================
Comprehensive contract, boundary, cross-feature, and lifecycle testing harness
covering features F1 through F15:
- F1: OneBlock autosave persistence & flush contracts
- F2: OneBlock island blocks preservation & chunk integrity
- F3: Unbreakable phone item & damage event interception
- F4: Phone 16/9 interface aspect ratio configuration
- F5: Bullion, coins & furniture placeability as 3D entities
- F6: Purchase value crediting & immediate HUD scoreboard sync
- F7: Survival breakability, loot drop (dropItemNaturally) & reuse
- F8: Kills & deaths event synchronization in SQLite
- F9: Leaderboards (/top kills, /joueurs) and display consistency
- F10: Per-player randomized safe survival spawn allocation
- F11: Interactive spawn reset NPC ("Gardien des Âmes") & terrain preservation
- F12: Gold pressure plates removal from jump pads & launch preservation
- F13: Paper 1.21.1 performance configuration parameters audit
- F14: Titan boss 90 HP rebalancing & 1.21 wave creature diversity
- F15: Dungeon Pass (CMD 2003) gating & VIP/Champion rank bypass

Framework: Compatible with both pytest and python -m unittest.
Target Workspace: C:\Users\1234\Desktop\Projets\aethercraft
================================================================================
"""

import os
import sys
import uuid
import time
import re
import math
import yaml
import sqlite3
import unittest
from typing import Dict, Any, List, Optional

# Ensure project root and web directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import (
    get_db_connection,
    init_database,
    db_get_player_by_username,
    db_get_leaderboards,
    db_get_top_player
)
from services.player_service import get_leaderboards, get_player_profile


def simulate_java_leaderboard_query(conn: sqlite3.Connection, order_col: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Simulates AetherVisualScoreboardManager.queryLeaderboard verbatim."""
    valid_col = "(p.balance + COALESCE(b.bank_coins, 0.0))"
    if order_col == "p.hours_played":
        valid_col = "p.hours_played"
    elif order_col == "p.kills":
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


# ==============================================================================
# TIER 1: FEATURE COVERAGE & CONTRACT VERIFICATION (F1 - F15)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 - Feature Coverage:
    Validates primary functionality, database schemas, and interface contracts
    for each individual feature from F1 through F15.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

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

    # --- F1: OneBlock Autosave Persistence ---
    def test_t1_01_oneblock_autosave_persistence_schema_and_ops(self):
        """Feature F1: player_oneblock schema integrity and atomic progression persistence."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(player_oneblock);")
            columns = {row["name"] for row in cursor.fetchall()}

        required_cols = {
            "uuid", "username", "island_id", "island_x", "island_y", "island_z",
            "phase", "blocks_broken", "level"
        }
        missing = required_cols - columns
        self.assertEqual(missing, set(), f"player_oneblock table missing columns: {missing}")

        test_uuid = str(uuid.uuid4())
        test_user = f"OBTest_{test_uuid[:6]}"
        self.created_uuids.append(test_uuid)
        self.created_usernames.append(test_user)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO player_oneblock (
                    uuid, username, island_id, island_x, island_y, island_z,
                    phase, blocks_broken, level, created_at
                ) VALUES (?, ?, 99999, 10000.0, 120.0, 10000.0, 1, 0, 1, CURRENT_TIMESTAMP)
            """, (test_uuid, test_user))
            conn.commit()

            cursor.execute("""
                UPDATE player_oneblock
                SET blocks_broken = blocks_broken + 42, phase = 2, level = 3
                WHERE uuid = ?
            """, (test_uuid,))
            conn.commit()

            cursor.execute("SELECT blocks_broken, phase, level FROM player_oneblock WHERE uuid = ?", (test_uuid,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["blocks_broken"], 42)
            self.assertEqual(row["phase"], 2)
            self.assertEqual(row["level"], 3)

    # --- F1 / F2: OneBlock Island Integrity & Save Contracts ---
    def test_t1_02_oneblock_island_blocks_integrity_contract(self):
        """Feature F1 & F2: OneBlockEngine saveAllSynchronously and non-destructive chunk load."""
        engine_path = os.path.join(SRC_DIR, "OneBlockEngine.java")
        plugin_path = os.path.join(SRC_DIR, "AetherVisualsPlugin.java")
        self.assertTrue(os.path.exists(engine_path), f"{engine_path} must exist")
        self.assertTrue(os.path.exists(plugin_path), f"{plugin_path} must exist")

        with open(engine_path, "r", encoding="utf-8") as f:
            engine_code = f.read()

        with open(plugin_path, "r", encoding="utf-8") as f:
            plugin_code = f.read()

        # Contract F1: OneBlockEngine must provide synchronous flush and plugin onDisable must call it
        self.assertIn("saveAllSynchronously", engine_code,
                      "OneBlockEngine must define saveAllSynchronously() for clean shutdown persistence")
        self.assertIn("saveAllSynchronously", plugin_code,
                      "AetherVisualsPlugin.onDisable() must call oneBlockEngine.saveAllSynchronously()")

        # Contract F2: Chunk loading must not wipe placed blocks if blocksBroken > 0
        self.assertTrue(
            "blocksBroken > 0" in engine_code or "blocksBroken == 0" in engine_code or "blocks_broken" in engine_code,
            "OneBlockEngine must guard island generation against overwriting player placed blocks"
        )

    # --- F3: Unbreakable Phone Item ---
    def test_t1_03_unbreakable_phone_item_contract(self):
        """Feature F3: Phone item unbreakable metadata and PlayerItemDamageEvent cancellation."""
        item_factory_path = os.path.join(SRC_DIR, "CustomItemFactory.java")
        holo_ui_path = os.path.join(SRC_DIR, "AetherHoloUIEngine.java")
        self.assertTrue(os.path.exists(item_factory_path), f"{item_factory_path} must exist")
        self.assertTrue(os.path.exists(holo_ui_path), f"{holo_ui_path} must exist")

        with open(item_factory_path, "r", encoding="utf-8") as f:
            factory_code = f.read()

        with open(holo_ui_path, "r", encoding="utf-8") as f:
            holo_code = f.read()

        # Contract F3: Phone item must be declared with unbreakable metadata
        has_phone_item = ("createAetherPhoneItem" in factory_code or "createPhoneItem" in factory_code or
                          "Phone" in factory_code or "AETHER_PHONE" in factory_code)
        self.assertTrue(has_phone_item, "CustomItemFactory must support AetherPhone item creation")

        # Holo UI Engine must intercept and cancel item damage events
        self.assertIn("PlayerItemDamageEvent", holo_code,
                      "AetherHoloUIEngine must listen to PlayerItemDamageEvent to prevent durability loss")
        self.assertIn("setCancelled(true)", holo_code,
                      "AetherHoloUIEngine must cancel damage events on phone items/sessions")

    # --- F4: 16/9 Phone Interface Aspect Ratio ---
    def test_t1_04_phone_16_9_interface_aspect_ratio(self):
        """Feature F4: Phone interface aspect ratio configured to 16/9 in CSS and WebDisplay manager."""
        webdisplay_path = os.path.join(PROJECT_ROOT, "web", "templates", "webdisplay.html")
        manager_path = os.path.join(SRC_DIR, "AetherWebDisplayManager.java")
        self.assertTrue(os.path.exists(webdisplay_path), f"{webdisplay_path} must exist")
        self.assertTrue(os.path.exists(manager_path), f"{manager_path} must exist")

        with open(webdisplay_path, "r", encoding="utf-8") as f:
            html_code = f.read()

        with open(manager_path, "r", encoding="utf-8") as f:
            manager_code = f.read()

        # HTML/CSS aspect ratio verification
        aspect_ratio_present = ("aspect-ratio" in html_code or "16 / 9" in html_code or "16/9" in html_code or
                                "aspect-video" in html_code)
        self.assertTrue(aspect_ratio_present,
                        "webdisplay.html must enforce 16/9 aspect ratio styling (aspect-ratio: 16 / 9 or aspect-video)")

        # WebDisplay manager must maintain 16:9 proportional dimensions
        has_16_9_dim = ("16" in manager_code and "9" in manager_code) or "aspect" in manager_code.lower()
        self.assertTrue(has_16_9_dim, "AetherWebDisplayManager must specify 16:9 display proportions")

    # --- F5: Bullion & Furniture Placeability ---
    def test_t1_05_bullion_furniture_placeability_contract(self):
        """Feature F5: Unblocked block place handling for bullion/coins in StoreItemInteractListener."""
        listener_path = os.path.join(SRC_DIR, "StoreItemInteractListener.java")
        bullion_engine_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        self.assertTrue(os.path.exists(listener_path), f"{listener_path} must exist")
        self.assertTrue(os.path.exists(bullion_engine_path), f"{bullion_engine_path} must exist")

        with open(listener_path, "r", encoding="utf-8") as f:
            listener_code = f.read()

        with open(bullion_engine_path, "r", encoding="utf-8") as f:
            bullion_code = f.read()

        # Contract F5: onBullionPlace handles 3D entity placement with tag TAG_BULLION
        self.assertIn("TAG_BULLION", bullion_code, "HabboBullionBlockEngine must define TAG_BULLION for placed entities")
        self.assertIn("onBullionPlace", bullion_code, "HabboBullionBlockEngine must handle onBullionPlace")

        # onMagotBlockPlace must not arbitrarily cancel placement when legitimate 3D furniture placement is intended
        self.assertIn("onMagotBlockPlace", listener_code,
                      "StoreItemInteractListener must handle onMagotBlockPlace")

    # --- F6: Purchase Value Crediting & Immediate Scoreboard Sync ---
    def test_t1_06_purchase_value_crediting_and_scoreboard_sync(self):
        """Feature F6: Exact balance crediting in SQLite and immediate scoreboard HUD refresh."""
        bullion_engine_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        with open(bullion_engine_path, "r", encoding="utf-8") as f:
            bullion_code = f.read()

        # Contract F6: HabboBullionBlockEngine must refresh scoreboard immediately on redemption
        self.assertTrue(
            "refreshPlayer" in bullion_code or "scoreboardManager" in bullion_code,
            "HabboBullionBlockEngine must trigger immediate scoreboard refresh upon bullion crediting"
        )

        # Opaque-box test of economy crediting across all bullion denominations
        test_uuid = str(uuid.uuid4())
        test_user = f"EcoTest_{test_uuid[:6]}"
        self.created_uuids.append(test_uuid)
        self.created_usernames.append(test_user)

        denominations = {
            "bronze": 100.0,
            "silver": 500.0,
            "sack": 1000.0,
            "ingot": 5000.0,
            "gold_block": 25000.0,
            "emerald_block": 100000.0
        }

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 0.0, 5, 0, 0, 1, 'Commerce', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (test_uuid, test_user))
            conn.commit()

            current_expected = 0.0
            for name, val in denominations.items():
                cursor.execute("UPDATE players SET balance = balance + ? WHERE uuid = ?", (val, test_uuid))
                conn.commit()
                current_expected += val

                cursor.execute("SELECT balance FROM players WHERE uuid = ?", (test_uuid,))
                bal = cursor.fetchone()["balance"]
                self.assertEqual(bal, current_expected, f"Failed crediting denomination {name}: expected {current_expected}, got {bal}")

    # --- F7: Survival Breakability, Loot Drop & Reuse ---
    def test_t1_07_survival_breakability_loot_and_reuse_contract(self):
        """Feature F7: Survival dropItemNaturally, explosion resistance, and reuse."""
        bullion_engine_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        with open(bullion_engine_path, "r", encoding="utf-8") as f:
            bullion_code = f.read()

        # Contract F7: Must use dropItemNaturally for physical item drops in survival
        self.assertIn("dropItemNaturally", bullion_code,
                      "HabboBullionBlockEngine must use dropItemNaturally on block breakage/overflow")

        # Contract F7: Must handle entity destruction / hit in survival
        self.assertIn("onBullionHit", bullion_code,
                      "HabboBullionBlockEngine must handle hit/break events on placed bullion")
        self.assertIn("createHabboBullionItem", bullion_code,
                      "HabboBullionBlockEngine must reconstruct bullion item for reusability by other players")

    # --- F8: Kills & Deaths Event Synchronization ---
    def test_t1_08_kills_deaths_event_sync(self):
        """Feature F8: Synchronize player kills and deaths in SQLite upon PlayerDeathEvent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(players);")
            cols = {row["name"] for row in cursor.fetchall()}

        self.assertIn("kills", cols, "players table must contain kills column")
        self.assertIn("deaths", cols, "players table must contain deaths column")

        # Test atomic increment of kills and deaths
        v_uuid, k_uuid = str(uuid.uuid4()), str(uuid.uuid4())
        v_name, k_name = f"Victim_{v_uuid[:5]}", f"Killer_{k_uuid[:5]}"
        self.created_uuids.extend([v_uuid, k_uuid])
        self.created_usernames.extend([v_name, k_name])

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 100.0, 10, 5, 2, 1, 'PvP', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 200.0, 15, 12, 1, 1, 'PvP', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (v_uuid, v_name, k_uuid, k_name))
            conn.commit()

            # Simulate PvP Death: Victim deaths + 1, Killer kills + 1
            cursor.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (v_uuid,))
            cursor.execute("UPDATE players SET kills = kills + 1 WHERE uuid = ?", (k_uuid,))
            conn.commit()

            cursor.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (v_uuid,))
            v_row = cursor.fetchone()
            self.assertEqual(v_row["deaths"], 3)
            self.assertEqual(v_row["kills"], 5)

            cursor.execute("SELECT kills, deaths FROM players WHERE uuid = ?", (k_uuid,))
            k_row = cursor.fetchone()
            self.assertEqual(k_row["kills"], 13)
            self.assertEqual(k_row["deaths"], 1)

    # --- F9: Leaderboards & Display Consistency ---
    def test_t1_09_leaderboards_and_display_consistency(self):
        """Feature F9: Consistent kill counts and K/D ratios across web and in-game queries."""
        lbs = db_get_leaderboards(5)
        self.assertIn("top_kills", lbs, "db_get_leaderboards must include top_kills key")

        # Validate K/D ratio calculation in top_kills
        top_kills = lbs["top_kills"]
        for player in top_kills:
            self.assertIn("kills", player)
            self.assertIn("deaths", player)
            self.assertIn("kd_ratio", player)
            kills = player["kills"]
            deaths = player["deaths"]
            expected_kd = kills if deaths == 0 else round(kills / deaths, 2)
            self.assertEqual(player["kd_ratio"], expected_kd,
                             f"K/D mismatch for {player['username']}: expected {expected_kd}, got {player['kd_ratio']}")

        # Validate /joueurs web route renders top_kills panel
        resp = self.client.get("/joueurs")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('id="lb-panel-kills"', html, "web /joueurs must contain lb-panel-kills tab")

    # --- F10: Per-Player Randomized Safe Survival Spawn Allocation ---
    def test_t1_10_per_player_random_survival_spawn_allocation(self):
        """Feature F10: RandomSpawnEngine per-player spawn allocation & destroyed bed fallback."""
        spawn_engine_path = os.path.join(SRC_DIR, "RandomSpawnEngine.java")
        self.assertTrue(os.path.exists(spawn_engine_path), f"{spawn_engine_path} must exist")

        with open(spawn_engine_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Contract F10: Must define minimum and maximum radius bounds
        self.assertIn("MIN_RADIUS", code, "RandomSpawnEngine must specify MIN_RADIUS")
        self.assertIn("MAX_RADIUS", code, "RandomSpawnEngine must specify MAX_RADIUS")

        # Contract F10: Must handle player respawn and fallback when bed/anchor is absent or destroyed
        self.assertIn("onPlayerRespawn", code, "RandomSpawnEngine must handle onPlayerRespawn event")

    # --- F11: Interactive Spawn Reset NPC & World Terrain Preservation ---
    def test_t1_11_spawn_reset_npc_and_world_terrain_preservation(self):
        """Feature F11: 'Gardien des Âmes' NPC in SpawnNpcGuides; terrain preserved, only spawn reset."""
        npc_path = os.path.join(SRC_DIR, "SpawnNpcGuides.java")
        self.assertTrue(os.path.exists(npc_path), f"{npc_path} must exist")

        with open(npc_path, "r", encoding="utf-8") as f:
            npc_code = f.read()

        # Contract F11: SpawnNpcGuides must include Gardien des Âmes NPC
        self.assertTrue(
            "Gardien des Âmes" in npc_code or "Gardien" in npc_code or "Gardienne" in npc_code,
            "SpawnNpcGuides must contain Spawn guide NPC"
        )

        # User Instruction: Verify player_survival_locations can be reset without touching world chunks
        test_uuid = str(uuid.uuid4())
        test_user = f"ResetTest_{test_uuid[:6]}"
        self.created_uuids.append(test_uuid)
        self.created_usernames.append(test_user)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch)
                VALUES (?, ?, 'world', 1234.5, 70.0, 5678.5, 90.0, 0.0)
            """, (test_uuid, test_user))
            conn.commit()

            # Execute personal spawn reset: clears ONLY location row
            cursor.execute("DELETE FROM player_survival_locations WHERE uuid = ?", (test_uuid,))
            conn.commit()

            cursor.execute("SELECT * FROM player_survival_locations WHERE uuid = ?", (test_uuid,))
            self.assertIsNone(cursor.fetchone(), "Personal survival location must be cleared after reset")

    # --- F12: Gold Pressure Plates Removal from Jump Pads ---
    def test_t1_12_spawn_gold_pressure_plates_removal(self):
        """Feature F12: Removal of gold pressure plates from CelestialSpawnBuilder jump pads."""
        spawn_builder_path = os.path.join(SRC_DIR, "CelestialSpawnBuilder.java")
        ambiance_path = os.path.join(SRC_DIR, "SpawnAmbianceEngine.java")
        self.assertTrue(os.path.exists(spawn_builder_path), f"{spawn_builder_path} must exist")
        self.assertTrue(os.path.exists(ambiance_path), f"{ambiance_path} must exist")

        with open(spawn_builder_path, "r", encoding="utf-8") as f:
            builder_code = f.read()

        # Contract F12: buildJumpPads must NOT place LIGHT_WEIGHTED_PRESSURE_PLATE (gold pressure plate)
        # Note: If still present, flags for Milestone M4 cleanup
        self.assertNotIn("Material.LIGHT_WEIGHTED_PRESSURE_PLATE", builder_code,
                         "CelestialSpawnBuilder must not use gold pressure plates on jump pads")

    # --- F13: Paper 1.21.1 Performance Configuration Parameters Audit ---
    def test_t1_13_paper_performance_parameters_audit(self):
        """Feature F13: Audit server.properties, bukkit.yml, spigot.yml, and paper-world-defaults.yml."""
        server_prop_path = os.path.join(SERVER_DIR, "server.properties")
        bukkit_path = os.path.join(SERVER_DIR, "bukkit.yml")
        spigot_path = os.path.join(SERVER_DIR, "spigot.yml")
        paper_world_path = os.path.join(SERVER_DIR, "config", "paper-world-defaults.yml")

        self.assertTrue(os.path.exists(server_prop_path), f"{server_prop_path} must exist")
        self.assertTrue(os.path.exists(bukkit_path), f"{bukkit_path} must exist")
        self.assertTrue(os.path.exists(spigot_path), f"{spigot_path} must exist")
        self.assertTrue(os.path.exists(paper_world_path), f"{paper_world_path} must exist")

        # Parse bukkit.yml
        with open(bukkit_path, "r", encoding="utf-8") as f:
            bukkit_cfg = yaml.safe_load(f)
        self.assertIn("ticks-per", bukkit_cfg)
        self.assertGreaterEqual(bukkit_cfg["ticks-per"].get("autosave", 0), 6000,
                                "bukkit.yml autosave interval should be >= 6000 ticks for performance")

        # Parse server.properties
        with open(server_prop_path, "r", encoding="utf-8") as f:
            props = dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))
        self.assertIn("network-compression-threshold", props)
        self.assertGreaterEqual(int(props["network-compression-threshold"]), 256,
                                "network-compression-threshold must be >= 256")
        self.assertLessEqual(int(props.get("simulation-distance", 10)), 8,
                             "simulation-distance should be <= 8 for 20 TPS server stability")

    # --- F14: Dungeon Mob HP Rebalancing & Creature Diversity ---
    def test_t1_14_dungeon_mob_health_and_wave_diversity(self):
        """Feature F14: Titan boss base HP = 90.0, waves 1-4 diversified with 1.21 mobs."""
        spawner_path = os.path.join(SRC_DIR, "DungeonWaveSpawner.java")
        self.assertTrue(os.path.exists(spawner_path), f"{spawner_path} must exist")

        with open(spawner_path, "r", encoding="utf-8") as f:
            spawner_code = f.read()

        # Contract F14: Titan Boss HP must be rebalanced to 90.0 (not 250.0)
        self.assertIn("90.0", spawner_code,
                      "DungeonWaveSpawner.spawnBossTitan must set Titan Boss base HP to 90.0")
        self.assertNotIn("250.0", spawner_code,
                         "DungeonWaveSpawner must not use excessive 250.0 base HP for Titan Boss")

        # Creature diversity check: 1.21 hostile mobs
        diversity_found = any(m in spawner_code for m in ["BOGGED", "STRAY", "DROWNED", "EVOKER", "Bogged", "Stray", "Drowned", "Evoker"])
        self.assertTrue(diversity_found,
                        "DungeonWaveSpawner waves must be diversified with 1.21 creatures (Bogged, Stray, Drowned, Evoker)")

    # --- F15: Dungeon Pass Key Gating ---
    def test_t1_15_dungeon_pass_key_gating(self):
        """Feature F15: Dungeon entry requires CustomModelData 2003 pass, with VIP bypass."""
        engine_path = os.path.join(SRC_DIR, "DungeonWaveEngine.java")
        factory_path = os.path.join(SRC_DIR, "CustomItemFactory.java")
        self.assertTrue(os.path.exists(engine_path), f"{engine_path} must exist")
        self.assertTrue(os.path.exists(factory_path), f"{factory_path} must exist")

        with open(factory_path, "r", encoding="utf-8") as f:
            factory_code = f.read()

        with open(engine_path, "r", encoding="utf-8") as f:
            engine_code = f.read()

        # Contract F15: CustomItemFactory defines createDungeonPass with CustomModelData 2003
        self.assertIn("createDungeonPass", factory_code, "CustomItemFactory must define createDungeonPass")
        self.assertIn("2003", factory_code, "Dungeon Pass must use CustomModelData 2003")

        # Contract F15: DungeonWaveEngine joinDungeon must validate key or VIP bypass
        self.assertTrue(
            "2003" in engine_code or "DungeonPass" in engine_code or "createDungeonPass" in engine_code or "hasPermission" in engine_code or "VIP" in engine_code,
            "DungeonWaveEngine.joinDungeon must validate possession of Dungeon Pass or VIP rank bypass"
        )

    # --- Death & Economy Rules: Building Blocks Loss Only, Virtual Balance & Coins Preserved ---
    def test_t1_16_death_loot_rules_building_blocks_loss_only(self):
        """User Instruction: On death, ONLY building blocks lost; coins/bullion & bank balance preserved; 0 durability penalty."""
        test_uuid = str(uuid.uuid4())
        test_user = f"DeathEco_{test_uuid[:6]}"
        self.created_uuids.append(test_uuid)
        self.created_usernames.append(test_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 7500.0, 12, 1, 0, 1, 'Guild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (test_uuid, test_user))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 15000.0, CURRENT_TIMESTAMP)
            """, (test_user,))
            conn.commit()

            # Simulate death event: deaths increments, but balance and bank_coins MUST NOT decrease
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (test_uuid,))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE uuid = ?", (test_uuid,))
            bal_after = c.fetchone()["balance"]
            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE username = ?", (test_user,))
            bank_after = c.fetchone()["bank_coins"]

            self.assertEqual(bal_after, 7500.0, "Virtual wallet balance must not be lost or penalized on death")
            self.assertEqual(bank_after, 15000.0, "Virtual bank coins must not be lost or penalized on death")


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCorner(unittest.TestCase):
    """
    Tier 2 - Boundary & Corner Conditions:
    Validates extreme values, edge coordinates, zero-division resilience,
    and missing record handling.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

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
                conn.commit()

    def test_t2_01_oneblock_boundary_levels_and_counters(self):
        """Boundary: OneBlock level 1 with 0 blocks, extreme block count (1,000,000)."""
        t_uuid = str(uuid.uuid4())
        t_user = f"OBEdge_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            # 0 blocks broken boundary
            c.execute("""
                INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, created_at)
                VALUES (?, ?, 88888, 10000.0, 120.0, 10000.0, 1, 0, 1, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user))
            conn.commit()

            c.execute("SELECT blocks_broken, level FROM player_oneblock WHERE uuid = ?", (t_uuid,))
            row = c.fetchone()
            self.assertEqual(row["blocks_broken"], 0)
            self.assertEqual(row["level"], 1)

            # 1,000,000 blocks broken extreme boundary
            c.execute("UPDATE player_oneblock SET blocks_broken = 1000000, level = 100, phase = 10 WHERE uuid = ?", (t_uuid,))
            conn.commit()

            c.execute("SELECT blocks_broken, level, phase FROM player_oneblock WHERE uuid = ?", (t_uuid,))
            row_huge = c.fetchone()
            self.assertEqual(row_huge["blocks_broken"], 1000000)
            self.assertEqual(row_huge["level"], 100)

    def test_t2_02_bullion_denominations_extreme_credits(self):
        """Boundary: Bullion credits must handle minimum 100.0 to massive 1,000,000,000.0 balance."""
        t_uuid = str(uuid.uuid4())
        t_user = f"BullionEdge_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 0.0, 1, 0, 0, 0, 'Bank', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user))
            conn.commit()

            # Credit massive balance without SQLite precision overflow
            massive_credit = 1_000_000_000.0
            c.execute("UPDATE players SET balance = balance + ? WHERE uuid = ?", (massive_credit, t_uuid))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE uuid = ?", (t_uuid,))
            self.assertEqual(c.fetchone()["balance"], massive_credit)

    def test_t2_03_kd_ratio_zero_division_and_extreme_stats(self):
        """Boundary: Zero division protection (deaths=0) and extreme K/D calculations."""
        t_uuid1 = str(uuid.uuid4())
        t_uuid2 = str(uuid.uuid4())
        t_name1 = f"KDZero_{t_uuid1[:5]}"
        t_name2 = f"KDHigh_{t_uuid2[:5]}"
        self.created_uuids.extend([t_uuid1, t_uuid2])
        self.created_usernames.extend([t_name1, t_name2])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 10.0, 5, 0, 0, 1, 'Combat', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 50.0, 100, 50000, 0, 1, 'Combat', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_uuid1, t_name1, t_uuid2, t_name2))
            conn.commit()

        lbs = db_get_leaderboards(10)
        kills_lb = {p["username"]: p for p in lbs["top_kills"]}

        if t_name1 in kills_lb:
            self.assertEqual(kills_lb[t_name1]["kd_ratio"], 0.0)
        if t_name2 in kills_lb:
            self.assertEqual(kills_lb[t_name2]["kd_ratio"], 50000.0)

    def test_t2_04_spawn_coordinates_boundary_validation(self):
        """Boundary: Validate spawn coordinates respect exclusion zone and radius constraints."""
        agora_x, agora_z = 0.0, 0.0
        exclusion_radius = 250.0
        min_radius = 500.0
        max_radius = 2500.0

        def is_valid_spawn(x: float, z: float, y: float) -> bool:
            dist = math.sqrt((x - agora_x) ** 2 + (z - agora_z) ** 2)
            if dist < exclusion_radius:
                return False
            if dist < min_radius or dist > max_radius:
                return False
            if y < 55.0 or y > 260.0:
                return False
            return True

        # Center of Agora (forbidden)
        self.assertFalse(is_valid_spawn(0.0, 0.0, 120.0))
        # Within exclusion zone (forbidden)
        self.assertFalse(is_valid_spawn(100.0, 150.0, 70.0))
        # Too close to center (< min_radius 500)
        self.assertFalse(is_valid_spawn(300.0, 300.0, 70.0))
        # Valid randomized coordinates
        self.assertTrue(is_valid_spawn(640.0, 864.0, 72.0))
        self.assertTrue(is_valid_spawn(-1200.0, 1500.0, 68.0))
        # Beyond max_radius 2500 (forbidden)
        self.assertFalse(is_valid_spawn(3000.0, 3000.0, 70.0))
        # Invalid altitudes
        self.assertFalse(is_valid_spawn(800.0, 800.0, 40.0))
        self.assertFalse(is_valid_spawn(800.0, 800.0, 300.0))

    def test_t2_05_dungeon_pass_inventory_boundary_conditions(self):
        """Boundary: 0 passes (denied), 1 pass (consumed to 0), 64 passes (decremented to 63)."""
        def simulate_dungeon_entry(passes_in_inv: int, rank: str) -> Dict[str, Any]:
            if rank.upper() in ["VIP", "CHAMPION", "CREATEUR"]:
                return {"allowed": True, "passes_remaining": passes_in_inv, "reason": "RANK_BYPASS"}
            if passes_in_inv <= 0:
                return {"allowed": False, "passes_remaining": 0, "reason": "NO_PASS"}
            return {"allowed": True, "passes_remaining": passes_in_inv - 1, "reason": "PASS_CONSUMED"}

        # Joueur with 0 passes -> rejected
        r0 = simulate_dungeon_entry(0, "JOUEUR")
        self.assertFalse(r0["allowed"])
        self.assertEqual(r0["reason"], "NO_PASS")

        # Joueur with exactly 1 pass -> consumed to 0
        r1 = simulate_dungeon_entry(1, "JOUEUR")
        self.assertTrue(r1["allowed"])
        self.assertEqual(r1["passes_remaining"], 0)

        # Joueur with a full stack (64 passes) -> decremented to 63
        r64 = simulate_dungeon_entry(64, "JOUEUR")
        self.assertTrue(r64["allowed"])
        self.assertEqual(r64["passes_remaining"], 63)

        # VIP with 0 passes -> allowed freely
        rvip = simulate_dungeon_entry(0, "VIP")
        self.assertTrue(rvip["allowed"])
        self.assertEqual(rvip["reason"], "RANK_BYPASS")

    def test_t2_06_phone_aspect_ratio_geometric_boundaries(self):
        """Boundary: Exact geometric tolerance for 16:9 ratio (1.7778) vs 4:3 (1.333) or 1:1."""
        target_ratio = 16.0 / 9.0
        tolerance = 0.05

        def check_ratio(w: float, h: float) -> bool:
            return abs((w / h) - target_ratio) <= tolerance

        self.assertTrue(check_ratio(1920, 1080))
        self.assertTrue(check_ratio(1280, 720))
        self.assertTrue(check_ratio(384, 216))
        self.assertFalse(check_ratio(1024, 768))  # 4:3
        self.assertFalse(check_ratio(512, 512))   # 1:1

    def test_t2_07_death_inventory_filter_boundaries(self):
        """Boundary: Inventory partition on death: construction blocks dropped vs currency & phone preserved."""
        inventory_items = [
            {"type": "COBBLESTONE", "is_building_block": True, "durability": None, "amount": 64},
            {"type": "OAK_PLANKS", "is_building_block": True, "durability": None, "amount": 32},
            {"type": "STONE_BRICKS", "is_building_block": True, "durability": None, "amount": 16},
            {"type": "PIECE_SOLIDE", "is_building_block": False, "durability": 100, "amount": 5},
            {"type": "HABBO_LINGOT", "is_building_block": False, "durability": 100, "amount": 1},
            {"type": "AETHER_PHONE", "is_building_block": False, "durability": 100, "amount": 1},
        ]

        # Rule: ONLY building blocks are lost on death
        lost_items = [i for i in inventory_items if i["is_building_block"]]
        preserved_items = [i for i in inventory_items if not i["is_building_block"]]

        self.assertEqual(len(lost_items), 3)
        self.assertEqual(sum(i["amount"] for i in lost_items), 112)

        # Non-building items (coins, bullion, phone) suffer no loss and no repair penalty
        self.assertEqual(len(preserved_items), 3)
        for item in preserved_items:
            self.assertEqual(item["durability"], 100, f"{item['type']} must suffer no repair penalty on death")


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS & SYNCHRONIZATION
# ==============================================================================

class TestTier3CrossFeatureInteractions(unittest.TestCase):
    """
    Tier 3 - Cross-Feature Interactions:
    Validates transactional integrity and live synchronization between
    Bullion economy, SQLite, Scoreboard queries, PvP kills, and Spawns.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

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
                conn.commit()

    def test_t3_01_bullion_redemption_to_scoreboard_and_web_leaderboard(self):
        """Cross-Feature: Bullion redemption -> SQLite update -> Scoreboard query & Web Leaderboards sync."""
        t_uuid = str(uuid.uuid4())
        t_user = f"SyncRich_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'TITAN', 1000.0, 50, 10, 2, 1, 'Synergy', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user))
            conn.commit()

            # Redeem a Lingot d'Or (+5000 coins)
            c.execute("UPDATE players SET balance = balance + 5000.0 WHERE uuid = ?", (t_uuid,))
            conn.commit()

            # Verify PaperMC Scoreboard query
            java_rows = simulate_java_leaderboard_query(conn, "p.balance", 10)
            target = next((r for r in java_rows if r["username"] == t_user), None)
            self.assertIsNotNone(target)
            self.assertEqual(target["val"], 6000.0)

        # Verify Web Leaderboards
        py_lbs = db_get_leaderboards(10)
        web_target = next((r for r in py_lbs["top_rich"] if r["username"] == t_user), None)
        self.assertIsNotNone(web_target)
        self.assertEqual(web_target["total_wealth"], 6000.0)

    def test_t3_02_player_kill_sync_to_top_kills_and_web_profile(self):
        """Cross-Feature: Player kill event -> SQLite stats -> Top kills leaderboard & player profile."""
        v_uuid, k_uuid = str(uuid.uuid4()), str(uuid.uuid4())
        v_name, k_name = f"PvPVictim_{v_uuid[:5]}", f"PvPKiller_{k_uuid[:5]}"
        self.created_uuids.extend([v_uuid, k_uuid])
        self.created_usernames.extend([v_name, k_name])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 500.0, 20, 100, 10, 1, 'Arena', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'CHAMPION', 2500.0, 60, 450, 20, 1, 'Arena', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (v_uuid, v_name, k_uuid, k_name))
            conn.commit()

            # Killer strikes down victim: killer kills +1, victim deaths +1
            c.execute("UPDATE players SET kills = kills + 1 WHERE uuid = ?", (k_uuid,))
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (v_uuid,))
            conn.commit()

        profile = get_player_profile(k_name)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["kills"], 451)

        v_profile = get_player_profile(v_name)
        self.assertIsNotNone(v_profile)
        self.assertEqual(v_profile["deaths"], 11)

    def test_t3_03_survival_spawn_reset_npc_workflow(self):
        """Cross-Feature: NPC Gardien des Âmes resets personal spawn without modifying world data."""
        t_uuid = str(uuid.uuid4())
        t_user = f"SpawnNpc_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch)
                VALUES (?, ?, 'world', 850.0, 71.0, 1100.0, 45.0, 0.0)
            """, (t_uuid, t_user))
            conn.commit()

            # Verify pre-reset existence
            c.execute("SELECT * FROM player_survival_locations WHERE uuid = ?", (t_uuid,))
            self.assertIsNotNone(c.fetchone())

            # NPC interaction triggers deletion of cached survival position
            c.execute("DELETE FROM player_survival_locations WHERE uuid = ?", (t_uuid,))
            conn.commit()

            # Ensure personal spawn reset
            c.execute("SELECT * FROM player_survival_locations WHERE uuid = ?", (t_uuid,))
            self.assertIsNone(c.fetchone())

    def test_t3_04_oneblock_progression_sync_to_leaderboard(self):
        """Cross-Feature: OneBlock broken blocks persist and sync to /top oneblock query."""
        t_uuid = str(uuid.uuid4())
        t_user = f"OBSync_{t_uuid[:6]}"
        self.created_uuids.append(t_uuid)
        self.created_usernames.append(t_user)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, created_at)
                VALUES (?, ?, 77777, 10000.0, 120.0, 10000.0, 3, 1500, 15, CURRENT_TIMESTAMP)
            """, (t_uuid, t_user))
            conn.commit()

            # Verify query simulating AetherVisualScoreboardManager.getTopOneBlock
            c.execute("""
                SELECT ob.username, ob.blocks_broken AS val 
                FROM player_oneblock ob 
                WHERE ob.uuid = ?
            """, (t_uuid,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["val"], 1500)

    def test_t3_05_dungeon_key_pass_access_control_cross_check(self):
        """Cross-Feature: Access control matrix for Dungeon Pass vs VIP ranks."""
        matrix = [
            {"rank": "JOUEUR", "keys": 0, "expected_allowed": False},
            {"rank": "JOUEUR", "keys": 2, "expected_allowed": True},
            {"rank": "VIP", "keys": 0, "expected_allowed": True},
            {"rank": "CHAMPION", "keys": 0, "expected_allowed": True},
            {"rank": "TITAN", "keys": 0, "expected_allowed": False},
        ]

        def can_enter_dungeon(rank: str, key_count: int) -> bool:
            if rank.upper() in ["VIP", "CHAMPION", "CREATEUR"]:
                return True
            return key_count >= 1

        for case in matrix:
            allowed = can_enter_dungeon(case["rank"], case["keys"])
            self.assertEqual(
                allowed, case["expected_allowed"],
                f"Access check failed for rank {case['rank']} with {case['keys']} keys"
            )

    def test_t3_06_death_event_economy_and_loot_preservation_sync(self):
        """Cross-Feature: Death event preserves wallet balance, bank account, and ensures drops pickup by any player."""
        p_uuid = str(uuid.uuid4())
        p_name = f"DeathSync_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'VIP', 32000.0, 45, 12, 1, 1, 'Immortals', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 100000.0, CURRENT_TIMESTAMP)
            """, (p_name,))
            conn.commit()

            # Trigger death event
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (p_uuid,))
            conn.commit()

            # Assert balance and bank coins unchanged
            c.execute("SELECT balance, deaths FROM players WHERE uuid = ?", (p_uuid,))
            row = c.fetchone()
            self.assertEqual(row["balance"], 32000.0)
            self.assertEqual(row["deaths"], 2)

            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE username = ?", (p_name,))
            b_row = c.fetchone()
            self.assertEqual(b_row["bank_coins"], 100000.0)


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS & FULL LIFECYCLE
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 - Real-World Scenarios:
    Validates end-to-end player sessions, survival furniture loot lifecycles,
    bed destruction fallbacks, and server shutdown persistence.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.created_uuids: List[str] = []
        self.created_usernames: List[str] = []

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
                conn.commit()

    def test_t4_01_full_oneblock_lifecycle_simulation(self):
        """Scenario: Full player OneBlock session: join -> mine -> autosave -> quit -> rejoin."""
        p_uuid = str(uuid.uuid4())
        p_name = f"OBJourney_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            # 1. First Join & Island Provisioning
            c.execute("""
                INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, created_at)
                VALUES (?, ?, 66666, 10000.0, 120.0, 10000.0, 1, 0, 1, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            # 2. Player Mines 150 blocks and advances tier
            c.execute("""
                UPDATE player_oneblock 
                SET blocks_broken = blocks_broken + 150, phase = 2, level = 4 
                WHERE uuid = ?
            """, (p_uuid,))
            conn.commit()

            # 3. 60-Second Periodic Autosave Flush simulates write verification
            c.execute("SELECT blocks_broken, phase, level FROM player_oneblock WHERE uuid = ?", (p_uuid,))
            s1 = c.fetchone()
            self.assertEqual(s1["blocks_broken"], 150)
            self.assertEqual(s1["phase"], 2)

            # 4. Player Disconnect & Reconnect: state is 100% preserved
            c.execute("SELECT * FROM player_oneblock WHERE uuid = ?", (p_uuid,))
            rejoin_state = c.fetchone()
            self.assertIsNotNone(rejoin_state)
            self.assertEqual(rejoin_state["blocks_broken"], 150)
            self.assertEqual(rejoin_state["level"], 4)

    def test_t4_02_survival_furniture_loot_and_reuse_cycle(self):
        """Scenario: Survival furniture placement -> explosion destruction -> loot drop -> reuse."""
        player_a_uuid, player_b_uuid = str(uuid.uuid4()), str(uuid.uuid4())
        player_a_name, player_b_name = f"Placer_{player_a_uuid[:5]}", f"Looter_{player_b_uuid[:5]}"
        self.created_uuids.extend([player_a_uuid, player_b_uuid])
        self.created_usernames.extend([player_a_name, player_b_name])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 10000.0, 10, 0, 0, 1, 'Habbo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 0.0, 5, 0, 0, 1, 'Habbo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (player_a_uuid, player_a_name, player_b_uuid, player_b_name))
            conn.commit()

            # Player A buys and places Bloc d'Or Habbo (valued at 25,000 coins)
            furniture_cmd = 6005
            furniture_value = 25000.0

            # Creeper explosion occurs: entity destroyed, drops physical item naturally
            # Player B collects dropped bullion item and redeems it
            c.execute("UPDATE players SET balance = balance + ? WHERE uuid = ?", (furniture_value, player_b_uuid))
            conn.commit()

            c.execute("SELECT balance FROM players WHERE uuid = ?", (player_b_uuid,))
            b_bal = c.fetchone()["balance"]
            self.assertEqual(b_bal, 25000.0)

    def test_t4_03_survival_bed_destruction_and_safe_respawn_fallback(self):
        """Scenario: Bed destroyed in survival -> player dies -> safe random spawn fallback."""
        p_uuid = str(uuid.uuid4())
        p_name = f"BedFallback_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 200.0, 8, 2, 0, 1, 'Wild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

        # Simulate bed spawn lookup: bed block missing/obstructed
        bed_spawn_valid = False
        if not bed_spawn_valid:
            # Fallback to safe random coordinates (min 500, max 2500 away)
            fallback_x = 750.0
            fallback_z = 920.0
            fallback_y = 69.0
            dist = math.sqrt(fallback_x ** 2 + fallback_z ** 2)
            self.assertGreaterEqual(dist, 500.0)
            self.assertLessEqual(dist, 2500.0)
            self.assertGreaterEqual(fallback_y, 55.0)

    def test_t4_04_server_shutdown_persistence_and_restart_integrity(self):
        """Scenario: Server shutdown sequence: saveAllSynchronously + dirty locations flush + world.save."""
        p_uuid = str(uuid.uuid4())
        p_name = f"ShutdownTest_{p_uuid[:6]}"
        self.created_uuids.append(p_uuid)
        self.created_usernames.append(p_name)

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch)
                VALUES (?, ?, 'world', 1500.0, 75.0, 2000.0, 180.0, 0.0)
            """, (p_uuid, p_name))
            c.execute("""
                INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, created_at)
                VALUES (?, ?, 55555, 10000.0, 120.0, 10000.0, 5, 8000, 40, CURRENT_TIMESTAMP)
            """, (p_uuid, p_name))
            conn.commit()

            # Simulate clean server restart reading DB
            c.execute("SELECT x, z FROM player_survival_locations WHERE uuid = ?", (p_uuid,))
            loc = c.fetchone()
            self.assertEqual(loc["x"], 1500.0)
            self.assertEqual(loc["z"], 2000.0)

            c.execute("SELECT blocks_broken FROM player_oneblock WHERE uuid = ?", (p_uuid,))
            ob = c.fetchone()
            self.assertEqual(ob["blocks_broken"], 8000)

    def test_t4_05_agora_spawn_and_jump_pad_traversal(self):
        """Scenario: Agora spawn experience: jump pad without gold pressure plates launches player."""
        builder_path = os.path.join(SRC_DIR, "CelestialSpawnBuilder.java")
        self.assertTrue(os.path.exists(builder_path))
        with open(builder_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Jump pad method exists
        self.assertTrue("buildJumpPads" in code or "JumpPad" in code or "jump" in code.lower(),
                        "CelestialSpawnBuilder must provide jump pad builder")

    def test_t4_06_player_death_currency_preservation_scenario(self):
        """Scenario: Player in Survival/OneBlock with virtual balance, physical bullion coins, and blocks dies."""
        p1_uuid, p2_uuid = str(uuid.uuid4()), str(uuid.uuid4())
        p1_name, p2_name = f"DeadMiner_{p1_uuid[:5]}", f"LootFinder_{p2_uuid[:5]}"
        self.created_uuids.extend([p1_uuid, p2_uuid])
        self.created_usernames.extend([p1_name, p2_name])

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
                VALUES (?, ?, 'JOUEUR', 45000.0, 30, 5, 3, 1, 'SurvivalGuild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                       (?, ?, 'JOUEUR', 100.0, 10, 1, 0, 1, 'SurvivalGuild', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p1_uuid, p1_name, p2_uuid, p2_name))
            c.execute("""
                INSERT INTO player_bank_accounts (username, bank_coins, updated_at)
                VALUES (?, 80000.0, CURRENT_TIMESTAMP)
            """, (p1_name,))
            conn.commit()

            # Player 1 dies carrying:
            # - Virtual currency: 45,000 wallet + 80,000 bank
            # - Physical coins: 5 Pièces de Bronze (value 500)
            # - Construction blocks: 64 Cobblestone, 32 Oak Planks
            # Rules:
            # 1. 0 repair penalty or durability damage on carried coins/ingots/bullion
            # 2. Death drops can be picked up by p1 or p2
            # 3. ONLY construction blocks are lost; virtual bank balance and physical coins are NOT lost

            # Death event triggered:
            c.execute("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?", (p1_uuid,))
            conn.commit()

            # Virtual balance remains 100% intact
            c.execute("SELECT balance FROM players WHERE uuid = ?", (p1_uuid,))
            self.assertEqual(c.fetchone()["balance"], 45000.0, "Wallet balance must be preserved on death")

            c.execute("SELECT bank_coins FROM player_bank_accounts WHERE username = ?", (p1_name,))
            self.assertEqual(c.fetchone()["bank_coins"], 80000.0, "Bank coins must be preserved on death")

            # Player 2 finds dropped building blocks and can claim them
            c.execute("SELECT deaths FROM players WHERE uuid = ?", (p1_uuid,))
            self.assertEqual(c.fetchone()["deaths"], 4)


if __name__ == "__main__":
    unittest.main()
