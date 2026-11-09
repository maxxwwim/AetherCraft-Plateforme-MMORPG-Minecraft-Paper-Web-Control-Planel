"""
Test Suite for Feature F21 (Milestone M2B):
Shop Blocks Catalog Audit & In-Game Registration
"""

import os
import sys
import unittest
import sqlite3

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
SRC_DIR = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from services.database import get_db_connection
import services.store_service as store_service


class TestF21ShopBlocksCatalogAudit(unittest.TestCase):
    """Audit of store blocks catalog, database persistence, and in-game registration."""

    def test_01_store_service_items_and_default_items(self):
        """Audit STORE_ITEMS and DEFAULT_ITEMS in store_service.py."""
        self.assertTrue(hasattr(store_service, "STORE_ITEMS"), "store_service must define STORE_ITEMS")
        self.assertTrue(hasattr(store_service, "DEFAULT_ITEMS"), "store_service must define DEFAULT_ITEMS")
        self.assertEqual(store_service.STORE_ITEMS, store_service.DEFAULT_ITEMS)

        # Check all magots & block categories
        magots = [item for item in store_service.STORE_ITEMS if item.get("category") == "magots"]
        magot_ids = {item["id"] for item in magots}

        expected_magots = {
            "magot_piece_bronze",
            "magot_piece_argent",
            "magot_sac_pieces",
            "magot_lingot_or",
            "magot_bloc_or",
            "magot_bloc_emeraude",
            "magot_bloc_diamant",
            "magot_trophee_or",
            "magot_trone_royal",
            "bloc_aether",
            "minerai_aether"
        }
        for em in expected_magots:
            self.assertIn(em, magot_ids, f"Expected store block/furniture '{em}' in STORE_ITEMS")

    def test_02_sqlite_store_items_table_synchronization(self):
        """Ensure all blocks and furniture exist in SQLite server/data/aethercraft.db."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, price_points FROM store_items WHERE category='magots';")
            rows = {r["id"]: r for r in cur.fetchall()}

        expected_values = {
            "magot_piece_bronze": 10,
            "magot_piece_argent": 50,
            "magot_sac_pieces": 100,
            "magot_lingot_or": 250,
            "magot_bloc_or": 500,
            "magot_bloc_emeraude": 1000,
            "magot_bloc_diamant": 2500,
            "magot_trophee_or": 5000,
            "magot_trone_royal": 10000,
            "bloc_aether": 1500,
            "minerai_aether": 750
        }

        for item_id, expected_points in expected_values.items():
            self.assertIn(item_id, rows, f"SQLite store_items must contain '{item_id}'")
            self.assertEqual(rows[item_id]["price_points"], expected_points,
                             f"Item '{item_id}' price_points must equal {expected_points}")

    def test_03_java_pet_item_factory_bullion_and_pets(self):
        """Verify PetItemFactory defines all bullion blocks, values, and griffin pet."""
        pet_factory_path = os.path.join(SRC_DIR, "PetItemFactory.java")
        with open(pet_factory_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Check bullion block creation
        for item_id in ["magot_bloc_diamant", "magot_trophee_or", "magot_trone_royal", "bloc_aether", "minerai_aether"]:
            self.assertIn(item_id, code, f"PetItemFactory must recognize '{item_id}'")

        # Check griffin pet
        self.assertIn("createGriffinPetItem", code, "PetItemFactory must define createGriffinPetItem")
        self.assertIn("3008", code, "Griffin pet must use CustomModelData 3008")

        # Check CustomModelData mapping
        for cmd in ["6001", "6002", "6003", "6004", "6005", "6006", "6007", "6008", "6009", "6010", "6011"]:
            self.assertIn(cmd, code, f"PetItemFactory.getBullionCoinValue must handle CMD {cmd}")

    def test_04_java_custom_item_factory_registration(self):
        """Verify CustomItemFactory defines creators and maps all block items."""
        factory_path = os.path.join(SRC_DIR, "CustomItemFactory.java")
        with open(factory_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("createGriffinPetItem", code)
        self.assertIn("createAetherBlockItem", code)
        self.assertIn("createAetherOreItem", code)
        self.assertIn("createDiamondBullionBlock", code)
        self.assertIn("createHabboTrophyItem", code)
        self.assertIn("createHabboThroneItem", code)

        for item_id in ["magot_bloc_diamant", "magot_trophee_or", "magot_trone_royal", "bloc_aether", "minerai_aether", "pet_griffin"]:
            self.assertIn(item_id, code, f"CustomItemFactory.createItemById must handle '{item_id}'")

    def test_05_java_habbo_bullion_block_engine_mapping(self):
        """Verify HabboBullionBlockEngine registers all store blocks for 3D clusters."""
        engine_path = os.path.join(SRC_DIR, "HabboBullionBlockEngine.java")
        with open(engine_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Check reverse mapping CMD -> ID
        for cmd in [6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009, 6010, 6011]:
            self.assertIn(str(cmd), code, f"HabboBullionBlockEngine.getBullionIdFromCmd must map CMD {cmd}")

        # Check survival break & drop naturally
        self.assertIn("dropItemNaturally", code, "HabboBullionBlockEngine must use dropItemNaturally")
        self.assertIn("TAG_BULLION", code, "HabboBullionBlockEngine must tag clusters with TAG_BULLION")
        self.assertIn("onBullionHit", code, "HabboBullionBlockEngine must handle onBullionHit")
        self.assertIn("onBullionInteract", code, "HabboBullionBlockEngine must handle onBullionInteract")

    def test_06_java_aether_shop_catalog_articles(self):
        """Verify AetherShopCatalog offers all store blocks and griffin pet."""
        catalog_path = os.path.join(SRC_DIR, "AetherShopCatalog.java")
        with open(catalog_path, "r", encoding="utf-8") as f:
            code = f.read()

        expected_articles = [
            "magot_piece_bronze",
            "magot_piece_argent",
            "magot_sac_pieces",
            "magot_lingot_or",
            "magot_bloc_or",
            "magot_bloc_emeraude",
            "magot_bloc_diamant",
            "magot_trophee_or",
            "magot_trone_royal",
            "bloc_aether",
            "minerai_aether",
            "pet_griffin"
        ]
        for art in expected_articles:
            self.assertIn(art, code, f"AetherShopCatalog must include article '{art}'")

    def test_07_store_delivery_dispatch_command_generation(self):
        """Verify store_service.execute_item_delivery generates store give commands for all blocks."""
        test_user = "AetherTester"
        for block_id in ["magot_bloc_diamant", "magot_trophee_or", "magot_trone_royal", "bloc_aether", "minerai_aether"]:
            cmds = store_service.execute_item_delivery(test_user, block_id)
            has_give = any(f"store give {test_user} {block_id} 1" in cmd for cmd in cmds)
            self.assertTrue(has_give, f"execute_item_delivery must include store give command for '{block_id}'")


if __name__ == "__main__":
    unittest.main()
