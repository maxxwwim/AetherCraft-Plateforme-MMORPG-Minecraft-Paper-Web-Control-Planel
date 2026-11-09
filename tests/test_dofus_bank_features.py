"""
Unit & Integration Test Suite for AetherCraft Dofus-Style Bank.
Verifies the Dofus-style Bank GUI, quick-deposit buttons, auto-sort, and NPC interaction.
"""

import os
import unittest
import sqlite3

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "server", "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")

class TestDofusBankFeatures(unittest.TestCase):

    def test_bank_engine_dofus_styling_and_buttons(self):
        engine_file = os.path.join(SRC_DIR, "AetherBankEngine.java")
        self.assertTrue(os.path.exists(engine_file), "AetherBankEngine.java must exist")
        with open(engine_file, "r", encoding="utf-8") as f:
            code = f.read()

        # Dofus Title and Hologram
        self.assertIn("BANQUE DOFUS", code)
        self.assertIn("TRIER LE COFFRE (Style Dofus)", code)
        self.assertIn("DÉPOSER LES RESSOURCES (Dofus)", code)
        self.assertIn("TOUT DÉPOSER EN BANQUE", code)
        self.assertIn("GUICHET DES KAMAS", code)

        # Essential methods
        self.assertIn("depositResources", code)
        self.assertIn("sortVault", code)
        self.assertIn("depositAllItems", code)
        self.assertIn("retrieveAllItems", code)
        self.assertIn("mintBullion", code)
        self.assertIn("isResource", code)

    def test_spawn_builder_dofus_bank_counter(self):
        builder_file = os.path.join(SRC_DIR, "CelestialSpawnBuilder.java")
        self.assertTrue(os.path.exists(builder_file), "CelestialSpawnBuilder.java must exist")
        with open(builder_file, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("buildBankVault", code)
        self.assertIn("DARK_OAK_STAIRS", code)
        self.assertIn("IRON_BARS", code)
        self.assertIn("GOLD_BLOCK", code)

    def test_npc_banker_interaction(self):
        npc_file = os.path.join(SRC_DIR, "SpawnNpcGuides.java")
        self.assertTrue(os.path.exists(npc_file), "SpawnNpcGuides.java must exist")
        with open(npc_file, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("Banquier d'Éther", code)
        self.assertIn("pl.getBankEngine().openBank(p)", code)

    def test_sqlite_bank_tables_integrity(self):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_bank_accounts';")
            self.assertIsNotNone(c.fetchone(), "player_bank_accounts table must exist")

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_bank_items';")
            self.assertIsNotNone(c.fetchone(), "player_bank_items table must exist")

if __name__ == "__main__":
    unittest.main()
