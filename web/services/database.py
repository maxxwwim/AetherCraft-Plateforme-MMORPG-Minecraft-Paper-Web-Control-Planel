from __future__ import annotations
import sqlite3
import os
import json
import uuid
import random
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "server", "data", "aethercraft.db")
)

class ManagedConnection(sqlite3.Connection):
    """Subclass ensuring connections are cleanly closed upon exiting 'with' blocks."""
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        except sqlite3.ProgrammingError:
            pass
        finally:
            try:
                self.close()
            except Exception:
                pass

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialise le schéma relationnel complet du serveur Minecraft & Web."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Rangs et permissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ranks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                prefix TEXT NOT NULL,
                badge_color TEXT NOT NULL,
                weight INTEGER NOT NULL DEFAULT 0,
                price_eur REAL NOT NULL DEFAULT 0.0
            );
        """)

        # 2. Joueurs du serveur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                uuid TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                rank TEXT NOT NULL DEFAULT 'JOUEUR',
                balance REAL NOT NULL DEFAULT 1000.0,
                hours_played INTEGER NOT NULL DEFAULT 0,
                kills INTEGER NOT NULL DEFAULT 0,
                deaths INTEGER NOT NULL DEFAULT 0,
                is_online INTEGER NOT NULL DEFAULT 0,
                guild TEXT DEFAULT 'Aventurier',
                first_join TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                FOREIGN KEY (rank) REFERENCES ranks(id)
            );
        """)

        # 2b. Comptes bancaires et coffres-forts des joueurs (AetherBankEngine)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_bank_accounts (
                username TEXT PRIMARY KEY,
                bank_coins REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_bank_items (
                username TEXT,
                slot INTEGER,
                item_b64 TEXT,
                PRIMARY KEY (username, slot)
            );
        """)

        # 2c. Îles OneBlock personnelles des joueurs (OneBlockEngine)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_oneblock (
                uuid TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                island_id INTEGER NOT NULL UNIQUE,
                island_x REAL NOT NULL,
                island_y REAL NOT NULL,
                island_z REAL NOT NULL,
                phase INTEGER NOT NULL DEFAULT 1,
                blocks_broken INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                unlocked_chunks INTEGER NOT NULL DEFAULT 1,
                treasures_found INTEGER NOT NULL DEFAULT 0,
                monsters_killed INTEGER NOT NULL DEFAULT 0,
                trusted_members TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
        """)

        # 3. Commandes & Transactions boutique
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_orders (
                order_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                total REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                items_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'LIVRE',
                rcon_executed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        # 4. File d'attente des commandes RCON
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rcon_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                target_player TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                executed_at TEXT
            );
        """)

        # 5. Métriques temps réel du serveur (TPS, RAM, Joueurs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tps REAL NOT NULL DEFAULT 20.0,
                online_players INTEGER NOT NULL DEFAULT 0,
                ram_used_mb REAL NOT NULL DEFAULT 1024.0,
                ram_max_mb REAL NOT NULL DEFAULT 4096.0
            );
        """)

        # 6. Comptes Utilisateurs Web & Liaison Minecraft
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                minecraft_username TEXT NOT NULL UNIQUE,
                shop_points INTEGER NOT NULL DEFAULT 10,
                last_reward_claim TEXT,
                reward_streak INTEGER NOT NULL DEFAULT 0,
                playtime_reward_minutes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
        """)

        # Migration dynamique pour les bases de données existantes
        cursor.execute("PRAGMA table_info(users);")
        user_cols = [row[1] for row in cursor.fetchall()]
        if "shop_points" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN shop_points INTEGER NOT NULL DEFAULT 10;")
        if "last_reward_claim" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_reward_claim TEXT;")
        if "reward_streak" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN reward_streak INTEGER NOT NULL DEFAULT 0;")
        if "playtime_reward_minutes" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN playtime_reward_minutes INTEGER NOT NULL DEFAULT 0;")
        if "is_admin" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;")

        # Garantir le bonus de 10 points offerts pour tous les comptes existants
        cursor.execute("UPDATE users SET shop_points = 10 WHERE shop_points IS NULL OR shop_points < 10;")

        # 7. Marché des Minerais & Bourse Virtuelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ores_market (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT NOT NULL,
                image_url TEXT,
                category TEXT NOT NULL,
                base_price REAL NOT NULL,
                current_price REAL NOT NULL,
                rarity TEXT NOT NULL,
                total_traded INTEGER NOT NULL DEFAULT 0
            );
        """)

        # Migration dynamique pour ores_market
        cursor.execute("PRAGMA table_info(ores_market);")
        ores_cols = [row[1] for row in cursor.fetchall()]
        if "image_url" not in ores_cols:
            cursor.execute("ALTER TABLE ores_market ADD COLUMN image_url TEXT;")

        # 8. Jauge Mondiale de Coopération & Objectif Serveur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_amount INTEGER NOT NULL,
                current_amount INTEGER NOT NULL DEFAULT 0,
                reward_title TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0
            );
        """)

        cursor.execute("PRAGMA table_info(community_goals);")
        cg_cols = [row[1] for row in cursor.fetchall()]
        if "last_tier_reached" not in cg_cols:
            cursor.execute("ALTER TABLE community_goals ADD COLUMN last_tier_reached INTEGER NOT NULL DEFAULT 0;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tree_contributions (
                username TEXT PRIMARY KEY,
                raw_units INTEGER NOT NULL DEFAULT 0,
                weighted_points REAL NOT NULL DEFAULT 0.0,
                last_donation_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tree_tier_rewards_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tier_percent INTEGER NOT NULL,
                username TEXT NOT NULL,
                raw_share_percent REAL NOT NULL,
                effective_share_percent REAL NOT NULL,
                coins_rewarded REAL NOT NULL,
                points_rewarded INTEGER NOT NULL,
                keys_rewarded INTEGER NOT NULL DEFAULT 0,
                bonus_item TEXT,
                contributor_count INTEGER NOT NULL DEFAULT 1,
                rewarded_at TEXT NOT NULL
            );
        """)

        # 9. Annonces de Troc & Hôtel des Ventes Joueurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_market_listings (
                id TEXT PRIMARY KEY,
                seller_username TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_icon TEXT NOT NULL,
                image_url TEXT,
                quantity INTEGER NOT NULL,
                price_coins REAL NOT NULL,
                is_troc INTEGER NOT NULL DEFAULT 0,
                wanted_item TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                material_id TEXT DEFAULT 'DIAMOND_BLOCK'
            );
        """)

        cursor.execute("PRAGMA table_info(player_market_listings);")
        mkt_cols = [row[1] for row in cursor.fetchall()]
        if "image_url" not in mkt_cols:
            cursor.execute("ALTER TABLE player_market_listings ADD COLUMN image_url TEXT;")
        if "material_id" not in mkt_cols:
            cursor.execute("ALTER TABLE player_market_listings ADD COLUMN material_id TEXT DEFAULT 'DIAMOND_BLOCK';")

        # 10. Familiers & Nouveaux Animaux Célestes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mystic_pets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                icon TEXT NOT NULL,
                image_url TEXT,
                aura_name TEXT NOT NULL,
                aura_desc TEXT NOT NULL,
                social_bonus TEXT NOT NULL,
                rarity TEXT NOT NULL,
                price_coins REAL NOT NULL
            );
        """)

        # Migration dynamique pour mystic_pets
        cursor.execute("PRAGMA table_info(mystic_pets);")
        pet_cols = [row[1] for row in cursor.fetchall()]
        if "image_url" not in pet_cols:
            cursor.execute("ALTER TABLE mystic_pets ADD COLUMN image_url TEXT;")

        # 11. Catalogue de la Boutique en Base de Données
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_items (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                badge TEXT NOT NULL,
                badge_color TEXT NOT NULL,
                rarity TEXT NOT NULL,
                price REAL NOT NULL,
                price_points INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                icon TEXT NOT NULL,
                image_url TEXT NOT NULL,
                description TEXT NOT NULL,
                perks TEXT NOT NULL,
                popular INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            );
        """)

        # 12. Objets & Familiers Débloqués / Possédés par les Joueurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_unlocked_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                minecraft_username TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                icon TEXT,
                image_url TEXT,
                unlocked_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'STORE',
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE (user_id, item_id)
            );
        """)

        # 13. Quêtes Célestes & Progression Joueurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                icon TEXT NOT NULL,
                image_url TEXT,
                target_count INTEGER NOT NULL DEFAULT 1,
                reward_coins REAL NOT NULL DEFAULT 0,
                reward_points INTEGER NOT NULL DEFAULT 0,
                reward_item_id TEXT,
                reward_item_name TEXT,
                order_index INTEGER NOT NULL DEFAULT 0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quest_id TEXT NOT NULL,
                current_count INTEGER NOT NULL DEFAULT 0,
                target_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'EN_COURS',
                claimed_at TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (quest_id) REFERENCES quests(id),
                UNIQUE (user_id, quest_id)
            );
        """)

        # 14. Succès & Trophées Royaux
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                rarity TEXT NOT NULL,
                badge_color TEXT NOT NULL,
                icon TEXT NOT NULL,
                image_url TEXT,
                reward_points INTEGER NOT NULL DEFAULT 0,
                reward_title TEXT,
                order_index INTEGER NOT NULL DEFAULT 0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id),
                UNIQUE (user_id, achievement_id)
            );
        """)

        # 15. Donjons Instanciés & Expéditions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeons (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                recommended_level INTEGER NOT NULL,
                boss_name TEXT NOT NULL,
                entry_cost_type TEXT NOT NULL DEFAULT 'PASS',
                icon TEXT NOT NULL,
                image_url TEXT,
                reward_desc TEXT NOT NULL,
                reward_coins REAL NOT NULL DEFAULT 0,
                reward_points INTEGER NOT NULL DEFAULT 0,
                coords_spawn TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeon_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                dungeon_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                wave INTEGER NOT NULL DEFAULT 1,
                coins_earned REAL NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (dungeon_id) REFERENCES dungeons(id)
            );
        """)

        # 16. Historique des Vainqueurs du Quiz Trivia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 5,
                won_at TEXT NOT NULL
            );
        """)

        # 17. Clés & Déballage de Caisses Célestes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_type TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE (user_id, key_type)
            );
        """)

        # 18. Bestiaire Procédural des Monstres (Rangs X1, X2, X3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_bestiary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                element TEXT NOT NULL,
                affix_tier INTEGER NOT NULL,
                kills_count INTEGER NOT NULL DEFAULT 1,
                first_killed_at TEXT NOT NULL,
                last_killed_at TEXT NOT NULL,
                UNIQUE (user_id, entity_type, element, affix_tier)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crate_openings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                crate_type TEXT NOT NULL,
                rarity TEXT NOT NULL,
                item_name TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                reward_value TEXT,
                icon TEXT,
                image_url TEXT,
                opened_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # 21. Emplacements de Survie Mémorisés (Cache & Reprise Intelligente)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_survival_locations (
                uuid TEXT PRIMARY KEY,
                username TEXT,
                world TEXT,
                x REAL,
                y REAL,
                z REAL,
                yaw REAL,
                pitch REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Garantir un pack de départ de 5 Clés Célestes et 3 Clés Oméga pour tous les utilisateurs
        cursor.execute("SELECT id FROM users;")
        user_ids = [r[0] for r in cursor.fetchall()]
        for uid in user_ids:
            cursor.execute("INSERT OR IGNORE INTO user_keys (user_id, key_type, quantity) VALUES (?, 'celestial', 5);", (uid,))
            cursor.execute("INSERT OR IGNORE INTO user_keys (user_id, key_type, quantity) VALUES (?, 'omega', 3);", (uid,))

        # Seeding des Rangs initiaux
        ranks = [
            ("JOUEUR", "Joueur", "[Joueur]", "slate", 0, 0.0),
            ("VIP", "Grade VIP", "[VIP]", "emerald", 10, 4.99),
            ("AETHER", "Grade Aether", "[AETHER]", "sky", 20, 14.99),
            ("TITAN", "Grade Titan", "[TITAN]", "amber", 30, 29.99),
            ("CHAMPION", "Champion du Royaume", "[CHAMPION]", "violet", 50, 49.99),
            ("CREATEUR", "Créateur", "[Créateur]", "rose", 100, 0.0),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO ranks (id, name, prefix, badge_color, weight, price_eur)
            VALUES (?, ?, ?, ?, ?, ?);
        """, ranks)

        # Nettoyage et purge des faux joueurs / données mockées pour garantir l'intégrité réelle
        cursor.execute("""
            DELETE FROM players 
            WHERE uuid LIKE '00000000-%' 
               OR username IN ('AetherKnight', 'PixelSorceress', 'VortexCrafter', 'ShadowRanger', 'Notch');
        """)

        # Vue SQLite player_balances pour synchroniser les soldes avec les plugins Java & modules Web
        cursor.execute("DROP TRIGGER IF EXISTS trg_player_balances_update_balance;")
        cursor.execute("DROP TRIGGER IF EXISTS trg_player_balances_update_points;")
        cursor.execute("DROP TRIGGER IF EXISTS trg_update_player_balance;")
        cursor.execute("DROP TRIGGER IF EXISTS trg_update_player_shop_points;")
        cursor.execute("DROP VIEW IF EXISTS player_balances;")
        cursor.execute("""
            CREATE VIEW player_balances AS
            SELECT 
                p.username COLLATE NOCASE AS username,
                p.balance,
                COALESCE(u.shop_points, 10) AS shop_points
            FROM players p
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username);
        """)
        cursor.execute("""
            CREATE TRIGGER trg_update_player_balance
            INSTEAD OF UPDATE OF balance ON player_balances
            BEGIN
                UPDATE players 
                SET balance = NEW.balance 
                WHERE username = OLD.username COLLATE NOCASE;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER trg_update_player_shop_points
            INSTEAD OF UPDATE OF shop_points ON player_balances
            BEGIN
                UPDATE users 
                SET shop_points = NEW.shop_points 
                WHERE minecraft_username = OLD.username COLLATE NOCASE;
            END;
        """)

        # Seeding de la Bourse des Minerais (Ores Market) avec Visuels 3D & Équilibrage Réduit (Anti-Inflation)
        ores = [
            ("coal", "Charbon d'Éther", "⛏️", "/static/images/ores/ore_coal.png", "Minerai Basique", 0.9, 1.0, "COMMUN", 4520),
            ("copper", "Cuivre Électrisé", "⚡", "/static/images/ores/ore_copper.png", "Minerai Basique", 1.8, 2.0, "COMMUN", 3110),
            ("iron", "Fer Runique", "🛡️", "/static/images/ores/ore_iron.png", "Métal Forgé", 4.0, 4.5, "RARE", 2890),
            ("gold", "Or Purifié", "🪙", "/static/images/ores/ore_gold.png", "Métal Précieux", 8.0, 9.0, "RARE", 1950),
            ("lapis", "Lapis Stellaire", "🔮", "/static/images/ores/ore_lapis.png", "Gemme Magique", 6.5, 7.5, "RARE", 1420),
            ("diamond", "Diamant Brut Céleste", "💎", "/static/images/ores/ore_diamond.png", "Gemme Royale", 28.0, 32.0, "ÉPIQUE", 860),
            ("netherite", "Lingot de Netherite", "🖤", "/static/images/ores/ore_netherite.png", "Alliage Ancien", 100.0, 120.0, "LÉGENDAIRE", 215),
            ("aetherite", "Fragment d'Aetherite", "🪐", "/static/images/ores/ore_aetherite.png", "Minerai Mythique", 380.0, 450.0, "MYTHIQUE", 48),
        ]
        cursor.executemany("""
            INSERT INTO ores_market (id, name, icon, image_url, category, base_price, current_price, rarity, total_traded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET base_price=excluded.base_price, current_price=excluded.current_price, image_url=excluded.image_url;
        """, ores)

        # Seeding de la Jauge Mondiale de Coopération (Départ à 0)
        cursor.execute("""
            INSERT INTO community_goals (id, title, description, target_amount, current_amount, reward_title, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET current_amount = excluded.current_amount, target_amount = excluded.target_amount;
        """, (
            's4_celestial_tree',
            "Éclosion de l’Arbre Primordial des Cieux",
            "Chaque minerai troqué ou livré à l'Agora alimente la jauge mondiale. Débloquez ensemble le Sanctuaire des Animaux et les auras partagées !",
            50000,
            0,
            "Sanctuaire des Animaux Mythiques & Buff Global x2 XP",
            0
        ))

        # Seeding des Nouveaux Animaux & Familiers Célestes avec Visuels 3D
        pets = [
            (
                "pet_dragon",
                "Mini-Dragon Stellaire",
                "Dragonneau Céleste",
                "🐉",
                "/static/images/items/pet_dragon.png",
                "Aura de Partage de Flamme",
                "+15% de vitesse de minage partagée avec les alliés dans un rayon de 8 blocs.",
                "Bonus de Guilde",
                "MYTHIQUE",
                35714.0
            ),
            (
                "pet_capybara",
                "Capybara Céleste",
                "Gardien de la Sérénité",
                "🐾",
                "/static/images/items/pet_capybara.png",
                "Aura d'Apaisement Nocturne",
                "Repousse les Phantoms et confère Régénération I aux joueurs réunis au bivouac.",
                "Sociabilité & Entraide",
                "ÉPIQUE",
                17143.0
            ),
            (
                "pet_fox",
                "Renard Astral",
                "Kitsune Lunaire",
                "🦊",
                "/static/images/items/pet_fox.png",
                "Aura de Prospérité Marchande",
                "+10% de pièces d'or bonus sur tous les trocs et transactions pour vous et votre binôme.",
                "Commerce & Troc",
                "ÉPIQUE",
                20714.0
            ),
            (
                "pet_goat",
                "Bélier des Nuages",
                "Chèvre Aérienne",
                "🐐",
                "/static/images/items/pet_goat.png",
                "Aura de Saut Céleste",
                "Octroie Saut II et immunité aux dégâts de chute à tous les explorateurs du groupe.",
                "Exploration Coop",
                "RARE",
                85000.0
            ),
            (
                "pet_phoenix",
                "Phénix d'Or",
                "Oiseau de Renaissance (Modèle 3D Volumétrique)",
                "🦅",
                "/static/images/items/pet_phoenix.png",
                "Aura de Seconde Chance",
                "Absorbe un coup fatal d'un allié blessé en lui restaurant 5 cœurs (Recharge: 1h).",
                "Protection Mutuelle",
                "MYTHIQUE",
                42857.0
            ),
            (
                "pet_griffin",
                "Griffon Astral Souverain",
                "Gardien Impérial Ailé (Modèle 3D Volumétrique)",
                "🦁",
                "/static/images/items/pet_griffin.png",
                "Aura de Force Souveraine",
                "Octroie Force I et +12% de dégâts critiques aux membres du groupe dans un rayon de 10 blocs.",
                "Assaut & Donjons",
                "LÉGENDAIRE",
                49500.0
            ),
        ]
        cursor.executemany("""
            INSERT INTO mystic_pets (id, name, species, icon, image_url, aura_name, aura_desc, social_bonus, rarity, price_coins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET image_url=excluded.image_url;
        """, pets)

        # Marché des Joueurs P2P : Zéro annonce fictive, réservé exclusivement aux dépôts réels des joueurs
        # (Table player_market_listings alimentée en direct via /marche sell ou l'espace web)

        # Seeding des Quêtes Célestes
        quests = [
            (
                "quest_champion_awakening",
                "L'Éveil du Champion",
                "Rejoignez l'Archipel Céleste et visitez la Stèle du Champion à l'Agora.",
                "Survie",
                "🏛️",
                "/static/images/items/wings_elytra_celestial.png",
                1,
                150.0,
                30,
                "celestial_key",
                "Clé Céleste Antique",
                1
            ),
            (
                "quest_cloud_miner",
                "Mineur des Nuages",
                "Extrayez 64 minerais précieux (Aetherite, Célestium, Diamant ou Or) dans les cieux.",
                "Minage",
                "⛏️",
                "/static/images/ores/ore_aetherite.png",
                64,
                350.0,
                60,
                "booster_mine_2x",
                "Booster Minage x2 (1h)",
                2
            ),
            (
                "quest_dungeon_pioneer",
                "Pionnier des Donjons",
                "Pénétrez dans le Sanctuaire de l'Aetherite et terrassez le Gardien Stellaire.",
                "Donjons",
                "⚔️",
                "/static/images/items/sword_celestial_blade.png",
                1,
                800.0,
                120,
                "dungeon_pass_bundle",
                "Passe Donjon Illimité",
                3
            ),
            (
                "quest_market_tycoon",
                "Magnat de l'Agora",
                "Échangez ou négociez des minerais sur la Bourse de l'Agora pour au moins 500 Coins.",
                "Économie",
                "🪙",
                "/static/images/ores/ore_diamond.png",
                500,
                500.0,
                80,
                "crystal_teleport_hub",
                "Cristal de Téléportation",
                4
            ),
            (
                "quest_celestial_patron",
                "Bienfaiteur du Royaume",
                "Obtenez un artefact ou un familier mystique dans la Boutique Céleste.",
                "Boutique",
                "👑",
                "/static/images/items/crown_celestial_champion.png",
                1,
                1200.0,
                250,
                "title_scroll_celestial",
                "Parchemin de Titre Héros Éternel",
                5
            ),
        ]
        cursor.executemany("""
            INSERT INTO quests (id, title, description, category, icon, image_url, target_count, reward_coins, reward_points, reward_item_id, reward_item_name, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                title=excluded.title,
                description=excluded.description,
                image_url=excluded.image_url,
                target_count=excluded.target_count,
                reward_coins=excluded.reward_coins,
                reward_points=excluded.reward_points,
                reward_item_id=excluded.reward_item_id,
                reward_item_name=excluded.reward_item_name;
        """, quests)

        # Seeding des Succès & Trophées Royaux
        achievements = [
            (
                "ach_first_steps",
                "Premier Pas Céleste",
                "Rejoindre le monde de l'Archipel Céleste pour la première fois.",
                "BRONZE",
                "slate",
                "✨",
                "/static/images/items/crystal_teleport_hub.png",
                15,
                "L'Initié",
                1
            ),
            (
                "ach_crowned_champion",
                "Champion Sacré",
                "Détenir le rang suprême du Royaume et veiller sur le Spawn de l'Agora.",
                "MYTHIQUE",
                "violet",
                "👑",
                "/static/images/items/crown_celestial_champion.png",
                150,
                "Champion Suprême",
                2
            ),
            (
                "ach_market_baron",
                "Maître de la Bourse",
                "Réaliser des transactions sur la Bourse des minerais d'Éther.",
                "ARGENT",
                "emerald",
                "💎",
                "/static/images/ores/ore_gold.png",
                35,
                "Négociant Stellaire",
                3
            ),
            (
                "ach_stellar_tamer",
                "Dompteur des Étoiles",
                "Adopter un Familier Mystique pour vous escorter dans vos aventures.",
                "OR",
                "amber",
                "🐾",
                "/static/images/items/pet_phoenix.png",
                50,
                "Ami des Astres",
                4
            ),
            (
                "ach_dungeon_slayer",
                "Conquérant des Abysses",
                "Triompher d'une vague de Boss dans un donjon instancié.",
                "OR",
                "cyan",
                "⚔️",
                "/static/images/items/sword_celestial_blade.png",
                60,
                "Fléau des Titans",
                5
            ),
            (
                "ach_vault_sentinel",
                "Garde de l'Aetherite",
                "Activer une aura céleste ou un booster d'efficacité minage.",
                "ARGENT",
                "sky",
                "🛡️",
                "/static/images/items/aura_celestial_halo.png",
                30,
                "Gardien de Lumière",
                6
            ),
            (
                "ach_bestiary_x1_first",
                "Premier Chasseur",
                "Terrasser un premier monstre d'élite de Rang X1 dans l'Aether.",
                "BRONZE",
                "slate",
                "🗡️",
                "/static/images/items/sword_celestial_blade.png",
                20,
                "Initié Chasseur",
                7
            ),
            (
                "ach_bestiary_x1_elements",
                "Maître des Éléments X1",
                "Vaincre des monstres de chacun des 5 Éléments au Rang X1.",
                "ARGENT",
                "emerald",
                "⚡",
                "/static/images/items/crystal_teleport_hub.png",
                50,
                "Élémentaliste",
                8
            ),
            (
                "ach_bestiary_x2_slayer",
                "Chasseur de Champions",
                "Terrasser 20 monstres Champions de Rang X2 (Double Affixe).",
                "OR",
                "amber",
                "👑",
                "/static/images/items/crown_celestial_champion.png",
                80,
                "Traqueur de Champions",
                9
            ),
            (
                "ach_bestiary_x2_species",
                "Grand Bestiaire X2",
                "Vaincre un Champion Rang X2 pour chacune des 8 espèces de monstres.",
                "OR",
                "sky",
                "📖",
                "/static/images/items/pickaxe_efficiency_token.png",
                100,
                "Zoologiste Céleste",
                10
            ),
            (
                "ach_bestiary_x3_titan",
                "Tombeur de Mythes",
                "Terrasser un monstre Titan Némésis de Rang X3 (Triple Affixe).",
                "MYTHIQUE",
                "violet",
                "💥",
                "/static/images/items/sword_celestial_blade.png",
                150,
                "Tueur de Titans",
                11
            ),
            (
                "ach_bestiary_x3_pantheon",
                "Fléau Primordial X3",
                "Vaincre un Titan Rang X3 de chacun des 5 Éléments primaires.",
                "MYTHIQUE",
                "rose",
                "🌟",
                "/static/images/items/wings_elytra_celestial.png",
                300,
                "Fléau Primordial",
                12
            ),
        ]
        cursor.executemany("""
            INSERT INTO achievements (id, title, description, rarity, badge_color, icon, image_url, reward_points, reward_title, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                rarity=excluded.rarity,
                badge_color=excluded.badge_color,
                image_url=excluded.image_url,
                reward_points=excluded.reward_points,
                reward_title=excluded.reward_title;
        """, achievements)

        # Seeding des Donjons Célestes Instanciés
        dungeons = [
            (
                "sanctuaire_aetherite",
                "Sanctuaire de l'Aetherite",
                "Niveau I - Les Cristaux Flottants",
                "Normal",
                10,
                "Gardien Stellaire Chronos",
                "CHAMPION_FREE_OR_PASS",
                "🏛️",
                "/static/images/items/pickaxe_efficiency_token.png",
                "150 Coins + 25 Points Boutique + Cristal d'Aetherite",
                150.0,
                25,
                "0,121,15",
                1
            ),
            (
                "citadelle_titan",
                "Citadelle du Titan d'Obsidienne",
                "Niveau II - Le Bastion Électrisé",
                "Héroïque",
                25,
                "Goliath d'Obsidienne",
                "CHAMPION_FREE_OR_PASS",
                "🏰",
                "/static/images/items/sword_celestial_blade.png",
                "400 Coins + 60 Points Boutique + Caisse Céleste",
                400.0,
                60,
                "0,121,15",
                2
            ),
            (
                "faille_dragon",
                "Faille du Dragon de l'Éther",
                "Niveau III - Le Cœur Cosmique",
                "Mythique",
                40,
                "Wyrm Céleste Déchu",
                "CHAMPION_FREE_OR_PASS",
                "🐉",
                "/static/images/items/wings_elytra_celestial.png",
                "1000 Coins + 150 Points Boutique + Élytres Célestes",
                1000.0,
                150,
                "0,121,15",
                3
            ),
        ]
        cursor.executemany("""
            INSERT INTO dungeons (id, name, subtitle, difficulty, recommended_level, boss_name, entry_cost_type, icon, image_url, reward_desc, reward_coins, reward_points, coords_spawn, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                subtitle=excluded.subtitle,
                difficulty=excluded.difficulty,
                recommended_level=excluded.recommended_level,
                boss_name=excluded.boss_name,
                image_url=excluded.image_url,
                reward_desc=excluded.reward_desc,
                reward_coins=excluded.reward_coins,
                reward_points=excluded.reward_points;
        """, dungeons)

        conn.commit()

# Méthodes d'accès Joueurs
def db_get_all_players() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players ORDER BY balance DESC;")
        return [dict(row) for row in cursor.fetchall()]

def db_get_player_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.*,
                COALESCE(r.name, p.rank) AS rank_name,
                COALESCE(r.prefix, '[' || p.rank || ']') AS rank_prefix,
                COALESCE(r.badge_color, 'slate') AS badge_color,
                r.weight AS rank_weight,
                COALESCE(b.bank_coins, 0.0) AS bank_coins,
                (p.balance + COALESCE(b.bank_coins, 0.0)) AS total_wealth,
                COALESCE(u.shop_points, 10) AS shop_points
            FROM players p
            LEFT JOIN ranks r ON p.rank = r.id
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username)
            LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
            WHERE LOWER(p.username) = LOWER(?);
        """, (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

def db_get_leaderboards(limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """Retourne les classements réels depuis SQLite (top_rich, top_hours, top_kills)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Top Fortune / Richesse (Portefeuille + Banque)
        cursor.execute("""
            SELECT 
                p.uuid,
                p.username,
                p.rank,
                COALESCE(r.name, p.rank) AS rank_name,
                COALESCE(r.prefix, '[' || p.rank || ']') AS rank_prefix,
                COALESCE(r.badge_color, 'slate') AS badge_color,
                r.weight AS rank_weight,
                p.balance,
                COALESCE(b.bank_coins, 0.0) AS bank_coins,
                (p.balance + COALESCE(b.bank_coins, 0.0)) AS total_wealth,
                COALESCE(u.shop_points, 10) AS shop_points,
                p.hours_played,
                p.kills,
                p.deaths,
                CASE WHEN p.deaths = 0 THEN p.kills ELSE ROUND(CAST(p.kills AS REAL) / p.deaths, 2) END AS kd_ratio,
                p.is_online,
                p.guild,
                p.first_join,
                p.last_seen
            FROM players p
            LEFT JOIN ranks r ON p.rank = r.id
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username)
            LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
            ORDER BY (p.balance + COALESCE(b.bank_coins, 0.0)) DESC
            LIMIT ?;
        """, (limit,))
        top_rich = []
        for idx, row in enumerate(cursor.fetchall(), start=1):
            d = dict(row)
            d["rank_pos"] = idx
            d["rank_color"] = d["badge_color"]
            d["avatar_url"] = f"https://mc-heads.net/avatar/{d['username']}/96"
            d["body_url"] = f"https://mc-heads.net/body/{d['username']}/right"
            top_rich.append(d)

        # 2. Top Heures de jeu / Playtime
        cursor.execute("""
            SELECT 
                p.uuid,
                p.username,
                p.rank,
                COALESCE(r.name, p.rank) AS rank_name,
                COALESCE(r.prefix, '[' || p.rank || ']') AS rank_prefix,
                COALESCE(r.badge_color, 'slate') AS badge_color,
                r.weight AS rank_weight,
                p.balance,
                COALESCE(b.bank_coins, 0.0) AS bank_coins,
                (p.balance + COALESCE(b.bank_coins, 0.0)) AS total_wealth,
                COALESCE(u.shop_points, 10) AS shop_points,
                p.hours_played,
                p.kills,
                p.deaths,
                CASE WHEN p.deaths = 0 THEN p.kills ELSE ROUND(CAST(p.kills AS REAL) / p.deaths, 2) END AS kd_ratio,
                p.is_online,
                p.guild,
                p.first_join,
                p.last_seen
            FROM players p
            LEFT JOIN ranks r ON p.rank = r.id
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username)
            LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
            ORDER BY p.hours_played DESC
            LIMIT ?;
        """, (limit,))
        top_hours = []
        for idx, row in enumerate(cursor.fetchall(), start=1):
            d = dict(row)
            d["rank_pos"] = idx
            d["rank_color"] = d["badge_color"]
            d["avatar_url"] = f"https://mc-heads.net/avatar/{d['username']}/96"
            d["body_url"] = f"https://mc-heads.net/body/{d['username']}/right"
            top_hours.append(d)

        # 3. Top Kills / Frags PvP
        cursor.execute("""
            SELECT 
                p.uuid,
                p.username,
                p.rank,
                COALESCE(r.name, p.rank) AS rank_name,
                COALESCE(r.prefix, '[' || p.rank || ']') AS rank_prefix,
                COALESCE(r.badge_color, 'slate') AS badge_color,
                r.weight AS rank_weight,
                p.balance,
                COALESCE(b.bank_coins, 0.0) AS bank_coins,
                (p.balance + COALESCE(b.bank_coins, 0.0)) AS total_wealth,
                COALESCE(u.shop_points, 10) AS shop_points,
                p.hours_played,
                p.kills,
                p.deaths,
                CASE WHEN p.deaths = 0 THEN p.kills ELSE ROUND(CAST(p.kills AS REAL) / p.deaths, 2) END AS kd_ratio,
                p.is_online,
                p.guild,
                p.first_join,
                p.last_seen
            FROM players p
            LEFT JOIN ranks r ON p.rank = r.id
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username)
            LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
            ORDER BY p.kills DESC, kd_ratio DESC
            LIMIT ?;
        """, (limit,))
        top_kills = []
        for idx, row in enumerate(cursor.fetchall(), start=1):
            d = dict(row)
            d["rank_pos"] = idx
            d["rank_color"] = d["badge_color"]
            d["avatar_url"] = f"https://mc-heads.net/avatar/{d['username']}/96"
            d["body_url"] = f"https://mc-heads.net/body/{d['username']}/right"
            top_kills.append(d)

        return {
            "top_rich": top_rich,
            "top_hours": top_hours,
            "top_kills": top_kills
        }

def db_get_top_player() -> Optional[Dict[str, Any]]:
    """Retourne le profil complet du meilleur joueur (MVP) du serveur depuis SQLite."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                p.uuid,
                p.username,
                p.rank,
                COALESCE(r.name, p.rank) AS rank_name,
                COALESCE(r.prefix, '[' || p.rank || ']') AS rank_prefix,
                COALESCE(r.badge_color, 'slate') AS badge_color,
                r.weight AS rank_weight,
                p.balance,
                p.balance AS coins,
                COALESCE(b.bank_coins, 0.0) AS bank_coins,
                (p.balance + COALESCE(b.bank_coins, 0.0)) AS total_wealth,
                COALESCE(u.shop_points, 10) AS points,
                COALESCE(u.shop_points, 10) AS shop_points,
                p.hours_played,
                p.kills,
                p.deaths,
                CASE WHEN p.deaths = 0 THEN p.kills ELSE ROUND(CAST(p.kills AS REAL) / p.deaths, 2) END AS kd_ratio,
                p.guild,
                p.is_online,
                p.first_join,
                p.last_seen,
                ROUND((p.hours_played * 10.0) + (p.kills * 5.0) - (p.deaths * 2.0) + (p.balance / 1000.0) + (COALESCE(r.weight, 0) * 20.0), 1) AS mvp_score
            FROM players p
            LEFT JOIN ranks r ON p.rank = r.id
            LEFT JOIN users u ON LOWER(p.username) = LOWER(u.minecraft_username)
            LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username)
            ORDER BY 
                CASE WHEN p.rank = 'CREATEUR' THEN 1 ELSE 0 END ASC,
                mvp_score DESC,
                p.balance DESC
            LIMIT 1;
        """
        cursor.execute(query)
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["rank_color"] = d["badge_color"]
        d["avatar_url"] = f"https://mc-heads.net/avatar/{d['username']}/96"
        d["body_url"] = f"https://mc-heads.net/body/{d['username']}/right"
        return d

def db_get_community_tree_donors(limit: int = 5) -> List[Dict[str, Any]]:
    """Retourne la liste des meilleurs donateurs pour l'Arbre Céleste ordonnés par points pondérés."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(weighted_points) as total_w, SUM(raw_units) as total_u FROM tree_contributions;")
        tot = cursor.fetchone()
        total_w = float(tot["total_w"] or 0.0) if tot else 0.0
        total_u = int(tot["total_u"] or 0) if tot else 0

        cursor.execute("""
            SELECT 
                t.username, 
                t.raw_units, 
                t.weighted_points, 
                t.last_donation_at,
                COALESCE(p.rank, 'JOUEUR') AS rank,
                COALESCE(r.name, 'Joueur') AS rank_name,
                COALESCE(r.badge_color, 'slate') AS badge_color
            FROM tree_contributions t
            LEFT JOIN players p ON LOWER(t.username) = LOWER(p.username)
            LEFT JOIN ranks r ON p.rank = r.id
            WHERE t.raw_units > 0 OR t.weighted_points > 0
            ORDER BY t.weighted_points DESC
            LIMIT ?;
        """, (limit,))
        rows = []
        for idx, r in enumerate(cursor.fetchall(), start=1):
            d = dict(r)
            d["rank_pos"] = idx
            d["rank_color"] = d["badge_color"]
            d["avatar_url"] = f"https://mc-heads.net/avatar/{d['username']}/96"
            d["share_pct"] = round((d["weighted_points"] / total_w) * 100.0, 1) if total_w > 0 else 0.0
            d["unit_pct"] = round((d["raw_units"] / total_u) * 100.0, 1) if total_u > 0 else 0.0
            rows.append(d)
        return rows

def db_upsert_player(username: str, rank: str = "JOUEUR") -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE LOWER(username) = LOWER(?);", (username,))
        row = cursor.fetchone()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        is_admin_user = (username.strip().lower() == "hactheglitchis")
        initial_balance = 10000.0 if is_admin_user else 1000.0
        actual_rank = "CREATEUR" if is_admin_user else rank
        guild = "Fondateur" if is_admin_user else "Aventurier"
        if row:
            if is_admin_user and (row["balance"] < 10000.0 or row["rank"] != "CREATEUR"):
                cursor.execute("""
                    UPDATE players SET balance = 10000.0, rank = 'CREATEUR', guild = 'Fondateur'
                    WHERE LOWER(username) = 'hactheglitchis';
                """)
                conn.commit()
            return db_get_player_by_username(username)

        # F1: Interdiction absolue de créer ou réinsérer des joueurs mockés dans SQLite
        dummy_names = {'aetherknight', 'pixelsorceress', 'vortexcrafter', 'shadowranger', 'notch'}
        if username.strip().lower() in dummy_names:
            return {
                "uuid": "00000000-0000-0000-0000-000000000000",
                "username": username,
                "rank": "JOUEUR",
                "rank_name": "Joueur",
                "rank_prefix": "[Joueur]",
                "badge_color": "slate",
                "balance": 0.0,
                "bank_coins": 0.0,
                "total_wealth": 0.0,
                "hours_played": 0,
                "kills": 0,
                "deaths": 0,
                "is_online": 0,
                "guild": "Aventurier",
                "first_join": now,
                "last_seen": now
            }

        import uuid
        new_uuid = "1e0619ac-7b68-460e-a5e8-a39042285700" if is_admin_user else str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen)
            VALUES (?, ?, ?, ?, 1, 0, 0, 0, ?, ?, ?);
        """, (new_uuid, username, actual_rank, initial_balance, guild, now, now))
        conn.commit()
        return db_get_player_by_username(username)

def db_update_player_balance(username: str, new_balance: float) -> bool:
    with get_db_connection() as conn:
        conn.execute("UPDATE players SET balance = ? WHERE LOWER(username) = LOWER(?);", (new_balance, username))
        conn.commit()
        return True

def db_add_player_balance(username: str, amount: float) -> float:
    with get_db_connection() as conn:
        conn.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);", (amount, username))
        conn.commit()
        p = db_get_player_by_username(username)
        return p.get("balance", 0.0) if p else 0.0

# Méthodes Commandes Boutique
def db_save_order(order_id: str, username: str, total: float, items: list, currency: str = "EUR") -> Dict[str, Any]:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO store_orders (order_id, username, total, currency, items_json, status, rcon_executed, created_at)
            VALUES (?, ?, ?, ?, ?, 'LIVRE', 1, ?);
        """, (order_id, username, total, currency, json.dumps(items), now))
        conn.commit()
    return {
        "order_id": order_id,
        "username": username,
        "total": total,
        "currency": currency,
        "created_at": now
    }

def db_get_recent_orders(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM store_orders ORDER BY created_at DESC LIMIT ?;", (limit,))
        orders = []
        for row in cursor.fetchall():
            d = dict(row)
            d["products"] = json.loads(d["items_json"])
            orders.append(d)
        return orders

# ========================================================
# Méthodes Comptes Utilisateurs (Auth)
# ========================================================

def db_create_user(email: str, password_hash: str, salt: str, minecraft_username: str) -> Optional[Dict[str, Any]]:
    """Crée un nouvel utilisateur avec un solde initial de 10 points (ou 10 000 points + rôle admin si Hactheglitchis)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    is_admin = 1 if minecraft_username.strip().lower() == "hactheglitchis" else 0
    shop_points = 10000 if minecraft_username.strip().lower() == "hactheglitchis" else 10
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, is_admin, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (email.lower().strip(), password_hash, salt, minecraft_username.strip(), shop_points, is_admin, now, now))
            user_id = cursor.lastrowid
            conn.commit()
            return db_get_user_by_id(user_id)
        except sqlite3.IntegrityError:
            return None

def db_get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?);", (email.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def db_get_user_by_username(minecraft_username: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(minecraft_username) = LOWER(?);", (minecraft_username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def db_get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def db_update_user_last_login(user_id: int):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?;", (now, user_id))
        conn.commit()

# ========================================================
# Système de Récompense 30 Minutes & Points Boutique
# ========================================================

REWARD_COOLDOWN_SECONDS = 1800  # 30 minutes exactes

def db_get_reward_status(user_id: int) -> Dict[str, Any]:
    """Calcule le compte à rebours et l'éligibilité au coffre de 30 minutes (Monnaie unique en Pièces ⛃)."""
    user = db_get_user_by_id(user_id)
    if not user:
        return {"can_claim": False, "seconds_remaining": REWARD_COOLDOWN_SECONDS, "streak": 0, "shop_points": 0, "coins_balance": 0, "next_reward_pts": 50}

    last_claim = user.get("last_reward_claim")
    streak = user.get("reward_streak", 0) or 0
    username = user.get("minecraft_username", "")
    player = db_get_player_by_username(username)
    coins_balance = int(player["balance"]) if player else int(user.get("shop_points", 1000))
    next_reward_pts = 50 + min(50, streak * 5)

    if not last_claim:
        return {
            "can_claim": True,
            "seconds_remaining": 0,
            "streak": streak,
            "shop_points": coins_balance,
            "coins_balance": coins_balance,
            "next_reward_pts": next_reward_pts
        }

    try:
        last_dt = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
        elapsed = (datetime.utcnow() - last_dt).total_seconds()
    except Exception:
        elapsed = REWARD_COOLDOWN_SECONDS

    if elapsed >= REWARD_COOLDOWN_SECONDS:
        return {
            "can_claim": True,
            "seconds_remaining": 0,
            "streak": streak,
            "shop_points": coins_balance,
            "coins_balance": coins_balance,
            "next_reward_pts": next_reward_pts
        }
    else:
        remaining = int(REWARD_COOLDOWN_SECONDS - elapsed)
        return {
            "can_claim": False,
            "seconds_remaining": remaining,
            "streak": streak,
            "shop_points": coins_balance,
            "coins_balance": coins_balance,
            "next_reward_pts": next_reward_pts
        }

def db_claim_30min_reward(user_id: int) -> Tuple[bool, str, int, int, int]:
    """
    Réclame le coffre de fidélité des 30 minutes (+50 ⛃ Pièces de base + bonus de série).
    Retourne (succès, message, pièces_gagnées, nouveau_solde_pièces, secondes_restantes).
    """
    status = db_get_reward_status(user_id)
    if not status["can_claim"]:
        rem = status["seconds_remaining"]
        mins = rem // 60
        secs = rem % 60
        return False, f"Coffre en recharge. Revenez dans {mins}m {secs}s.", 0, status["shop_points"], rem

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    user = db_get_user_by_id(user_id)
    username = user["minecraft_username"]
    current_streak = user.get("reward_streak", 0) or 0
    new_streak = current_streak + 1

    # Distribution calibrée : 50 ⛃ Pièces de base + 5 par streak (max 100 ⛃)
    pts_gain = 50 + min(50, current_streak * 5)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 1. Créditer directement le portefeuille du joueur in-game
        cursor.execute("""
            UPDATE players 
            SET balance = balance + ?
            WHERE LOWER(username) = LOWER(?);
        """, (float(pts_gain), username))

        # 2. Synchroniser le compte utilisateur web (série et cooldown)
        cursor.execute("""
            UPDATE users 
            SET last_reward_claim = ?,
                reward_streak = ?
            WHERE id = ?;
        """, (now, new_streak, user_id))
        conn.commit()

    # Annonce & son RCON in-game
    try:
        from services.rcon_service import execute_server_command
        execute_server_command(f'title {username} actionbar {{"text":"🎁 Coffre Céleste Réclamé : +{pts_gain} ⛃ Pièces ! (Série x{new_streak})","color":"gold"}}')
        execute_server_command(f'playsound minecraft:entity.player.levelup master {username}')
        execute_server_command(f'broadcast §e⭐ §fLe joueur §b{username} §fa ouvert son Coffre des 30m : §6+{pts_gain} ⛃ Pièces §f!')
    except Exception:
        pass

    updated_player = db_get_player_by_username(username)
    new_balance = int(updated_player["balance"]) if updated_player else 0
    return True, f"Félicitations ! +{pts_gain} ⛃ Pièces ajoutées à votre solde (Série: x{new_streak}) !", pts_gain, new_balance, REWARD_COOLDOWN_SECONDS

def db_spend_shop_points(user_id: int, points: int) -> bool:
    """Déduit des Pièces (⛃) de façon atomique du compte joueur Minecraft."""
    if points <= 0:
        return False
    user = db_get_user_by_id(user_id)
    if not user:
        return False
    username = user["minecraft_username"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE players 
            SET balance = balance - ? 
            WHERE LOWER(username) = LOWER(?) AND balance >= ?;
        """, (float(points), username, float(points)))
        success = cursor.rowcount > 0
        conn.commit()
        return success

def db_add_shop_points(user_id: int, points: int) -> int:
    """Crédite des Pièces (⛃) sur le solde joueur Minecraft."""
    user = db_get_user_by_id(user_id)
    if not user:
        return 0
    username = user["minecraft_username"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE players 
            SET balance = balance + ? 
            WHERE LOWER(username) = LOWER(?);
        """, (float(points), username))
        conn.commit()
    player = db_get_player_by_username(username)
    return int(player["balance"]) if player else 0

def db_record_playtime_and_reward(minecraft_username: str, minutes_elapsed: int = 30) -> Optional[Dict[str, Any]]:
    """Crédite automatiquement le temps de jeu actif et récompense le joueur in-game en Pièces (⛃)."""
    user = db_get_user_by_username(minecraft_username)
    if not user:
        return None

    user_id = user["id"]
    current_mins = user.get("playtime_reward_minutes", 0) or 0
    total_mins = current_mins + minutes_elapsed

    pts_granted = 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Si un cycle de 30 minutes est complété
    if total_mins >= 30:
        cycles = total_mins // 30
        pts_granted = cycles * 50
        remaining_mins = total_mins % 30

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE players 
                SET balance = balance + ?
                WHERE LOWER(username) = LOWER(?);
            """, (float(pts_granted), minecraft_username))
            cursor.execute("""
                UPDATE users 
                SET playtime_reward_minutes = ?,
                    last_reward_claim = ?
                WHERE id = ?;
            """, (remaining_mins, now, user_id))
            conn.commit()
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET playtime_reward_minutes = ?
                WHERE id = ?;
            """, (total_mins, user_id))
            conn.commit()

    updated = db_get_player_by_username(minecraft_username)
    return {
        "user_id": user_id,
        "minecraft_username": minecraft_username,
        "points_granted": pts_granted,
        "total_points": int(updated.get("balance", 0)) if updated else 0,
        "playtime_reward_minutes": remaining_mins if total_mins >= 30 else total_mins
    }

# ========================================================
# Méthodes Marché des Minerais & Économie
# ========================================================

def db_get_ores_market() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ores_market ORDER BY base_price ASC;")
        return [dict(row) for row in cursor.fetchall()]

def db_get_tree_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(weighted_points) as total_w, SUM(raw_units) as total_u FROM tree_contributions;")
        tot = cursor.fetchone()
        total_w = float(tot["total_w"] or 0.0) if tot else 0.0
        total_u = int(tot["total_u"] or 0) if tot else 0

        cursor.execute("""
            SELECT username, raw_units, weighted_points, last_donation_at
            FROM tree_contributions
            WHERE raw_units > 0
            ORDER BY weighted_points DESC
            LIMIT ?;
        """, (limit,))
        rows = []
        for idx, r in enumerate(cursor.fetchall(), start=1):
            d = dict(r)
            d["rank"] = idx
            d["share_pct"] = round((d["weighted_points"] / total_w) * 100.0, 1) if total_w > 0 else 0.0
            d["unit_pct"] = round((d["raw_units"] / total_u) * 100.0, 1) if total_u > 0 else 0.0
            rows.append(d)
        return rows

def db_get_tree_reward_logs(limit: int = 12) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tree_tier_rewards_log
            ORDER BY id DESC LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def db_get_community_goal(goal_id: str = "s4_celestial_tree") -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM community_goals WHERE id = ?;", (goal_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["percent"] = min(100, int((d["current_amount"] / max(1, d["target_amount"])) * 100))
        d["last_tier_reached"] = int(d.get("last_tier_reached") or 0)
        d["donors"] = db_get_tree_leaderboard(8)
        d["reward_logs"] = db_get_tree_reward_logs(8)
        return d

def _distribute_single_tree_tier(cursor, tier_pct: int) -> List[Dict[str, Any]]:
    """
    Algorithme mathématique Anti-Cheat de distribution des récompenses par palier (25%, 50%, 75%, 100%).
    - Si 1 seul joueur : plafond S_max = 35% du pool (empêche de rafler un jackpot serveur en solo).
    - Si 2 joueurs : plafond S_max = 45% max par joueur.
    - Si 3+ joueurs : plafond S_max = 60% max + répartition hybride 70% (% donation) + 30% (racine carrée √don).
    - Facteur d'échelle du pool selon le nombre de joueurs actifs : min(1.0, 0.35 + 0.15 * N).
    """
    base_coins_pool = {25: 10000.0, 50: 25000.0, 75: 50000.0, 100: 100000.0}.get(tier_pct, 10000.0)
    base_points_pool = {25: 250, 50: 600, 75: 1200, 100: 2500}.get(tier_pct, 250)

    cursor.execute("""
        SELECT username, raw_units, weighted_points
        FROM tree_contributions
        WHERE weighted_points > 0
        ORDER BY weighted_points DESC;
    """)
    donors = [dict(r) for r in cursor.fetchall()]
    if not donors:
        return []

    total_w = sum(float(d["weighted_points"]) for d in donors)
    sum_sqrt = sum((float(d["weighted_points"]) ** 0.5) for d in donors)
    if total_w <= 0:
        return []

    n = len(donors)
    scale_factor = min(1.0, 0.35 + (0.15 * n))
    max_individual_share = 0.35 if n == 1 else (0.45 if n == 2 else 0.60)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    distributed = []

    for d in donors:
        uname = d["username"]
        w = float(d["weighted_points"])
        raw_share = w / total_w
        sqrt_share = (w ** 0.5) / sum_sqrt if sum_sqrt > 0 else raw_share
        hybrid_weight = (0.70 * raw_share) + (0.30 * sqrt_share)
        effective_share = min(max_individual_share, hybrid_weight * scale_factor)

        coins_reward = max(50.0, round(base_coins_pool * effective_share))
        points_reward = max(5, int(round(base_points_pool * effective_share)))
        keys_reward = (2 if tier_pct >= 75 else 1) if effective_share >= 0.15 else 0

        cursor.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);", (coins_reward, uname))
        cursor.execute("UPDATE users SET shop_points = shop_points + ? WHERE LOWER(minecraft_username) = LOWER(?);", (points_reward, uname))
        cursor.execute("""
            INSERT INTO tree_tier_rewards_log (
                tier_percent, username, raw_share_percent, effective_share_percent,
                coins_rewarded, points_rewarded, keys_rewarded, bonus_item, contributor_count, rewarded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            tier_pct, uname, round(raw_share * 100.0, 1), round(effective_share * 100.0, 1),
            coins_reward, points_reward, keys_reward,
            "key_mystic_bundle" if keys_reward > 0 else "none", n, now
        ))
        distributed.append({
            "tier_percent": tier_pct,
            "username": uname,
            "raw_share_percent": round(raw_share * 100.0, 1),
            "effective_share_percent": round(effective_share * 100.0, 1),
            "coins_rewarded": coins_reward,
            "points_rewarded": points_reward,
            "keys_rewarded": keys_reward,
        })
    return distributed

def db_contribute_to_community_goal(goal_id: str, amount: int, username: Optional[str] = None, ore_price: float = 10.0) -> Dict[str, Any]:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    amount = max(1, int(amount))
    weight_mult = max(1.0, float(ore_price) / 10.0)
    weighted_gain = amount * weight_mult

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if username:
            cursor.execute("""
                INSERT INTO tree_contributions (username, raw_units, weighted_points, last_donation_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    raw_units = raw_units + excluded.raw_units,
                    weighted_points = weighted_points + excluded.weighted_points,
                    last_donation_at = excluded.last_donation_at;
            """, (username, amount, weighted_gain, now))

        cursor.execute("""
            UPDATE community_goals 
            SET current_amount = MIN(target_amount, current_amount + ?)
            WHERE id = ?;
        """, (amount, goal_id))

        cursor.execute("SELECT current_amount, target_amount, COALESCE(last_tier_reached, 0) as lt FROM community_goals WHERE id = ?;", (goal_id,))
        row = cursor.fetchone()
        new_rewards = []
        if row:
            curr = int(row["current_amount"])
            targ = max(1, int(row["target_amount"]))
            last_tier = int(row["lt"])
            pct = int((curr * 100.0) // targ)
            for tier in (25, 50, 75, 100):
                if pct >= tier and last_tier < tier:
                    new_rewards.extend(_distribute_single_tree_tier(cursor, tier))
                    cursor.execute(
                        "UPDATE community_goals SET last_tier_reached = ?, is_completed = ? WHERE id = ?;",
                        (tier, 1 if tier >= 100 else 0, goal_id)
                    )
                    last_tier = tier

        conn.commit()
    res = db_get_community_goal(goal_id) or {}
    res["new_tier_rewards"] = new_rewards
    return res

def reset_database_and_tree_to_zero() -> Dict[str, Any]:
    """
    Réinitialise proprement la base de données aethercraft.db :
    - Remet l'Arbre Céleste (s4_celestial_tree) à 0 / 50 000 et last_tier_reached à 0.
    - Purge tree_contributions, tree_tier_rewards_log, player_market_listings, store_orders.
    - Remet les volumes de ores_market à 0 et réinitialise le catalogue boutique & familiers 3D.
    """
    init_database()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE community_goals
            SET current_amount = 0, target_amount = 50000, is_completed = 0, last_tier_reached = 0
            WHERE id = 's4_celestial_tree';
        """)
        cursor.execute("DELETE FROM tree_contributions;")
        cursor.execute("DELETE FROM tree_tier_rewards_log;")
        cursor.execute("DELETE FROM player_market_listings;")
        cursor.execute("DELETE FROM store_orders;")
        cursor.execute("UPDATE ores_market SET total_traded = 0;")
        conn.commit()
    return db_get_community_goal("s4_celestial_tree")

def resolve_minecraft_item_asset(item_name: str, material_id: Optional[str] = None) -> str:
    """Mappe un bloc ou objet vers son rendu 3D isométrique de bloc du jeu (/api/minecraft/block-icon/<mat>.png)."""
    from services.block_renderer import normalize_material_key
    key = normalize_material_key(material_id if material_id else item_name)
    return f"/api/minecraft/block-icon/{key}.png"

def db_get_market_listings(status: str = "ACTIVE") -> List[Dict[str, Any]]:
    from services.block_renderer import normalize_material_key
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM player_market_listings WHERE status = ? ORDER BY created_at DESC;", (status,))
        rows = [dict(row) for row in cursor.fetchall()]
        for r in rows:
            mat_id = r.get("material_id") or normalize_material_key(r.get("item_name", "DIAMOND_BLOCK")).upper()
            r["material_id"] = mat_id
            r["block_3d_url"] = resolve_minecraft_item_asset(r.get("item_name", ""), mat_id)
            r["image_url"] = r["block_3d_url"]
        return rows

def db_buy_market_listing(user_id: int, listing_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Achète une annonce de l'hôtel des ventes avec des Aether Coins du joueur."""
    user = db_get_user_by_id(user_id)
    if not user:
        return False, "Utilisateur non trouvé.", {}

    buyer_username = user["minecraft_username"]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Vérifier l'annonce
        cursor.execute("SELECT * FROM player_market_listings WHERE id = ?;", (listing_id,))
        listing = cursor.fetchone()
        if not listing:
            return False, "Annonce introuvable.", {}

        listing_dict = dict(listing)
        if listing_dict["status"] != "ACTIVE":
            return False, "Cet objet a déjà été vendu ou retiré.", {}

        if listing_dict["seller_username"].lower() == buyer_username.lower():
            return False, "Vous ne pouvez pas acheter votre propre objet.", {}

        price = float(listing_dict["price_coins"])

        # 2. Vérifier le solde du joueur
        cursor.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);", (buyer_username,))
        player_row = cursor.fetchone()
        current_balance = float(player_row["balance"]) if player_row else 0.0

        if current_balance < price:
            return False, f"Solde insuffisant ! Vous avez {int(current_balance)} Coins, prix : {int(price)} Coins.", {}

        # 3. Transactions atomiques
        cursor.execute("UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?);", (price, buyer_username))
        cursor.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);", (price, listing_dict["seller_username"]))
        cursor.execute("UPDATE player_market_listings SET status = 'SOLD' WHERE id = ?;", (listing_id,))

        # 4. Enregistrer dans store_orders pour traçabilité
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        order_id = f"mkt_{uuid.uuid4().hex[:10]}"
        items_json = json.dumps([{"name": listing_dict["item_name"], "qty": listing_dict["quantity"], "price": price}], ensure_ascii=False)
        cursor.execute("""
            INSERT INTO store_orders (order_id, username, total, currency, items_json, status, created_at)
            VALUES (?, ?, ?, 'COINS', ?, 'LIVRE', ?);
        """, (order_id, buyer_username, price, items_json, now))

        conn.commit()

        # Débloquer le succès Market Baron
        try:
            db_unlock_achievement(user_id, "ach_market_baron")
        except Exception:
            pass

        return True, f"Félicitations ! Vous avez acquis {listing_dict['item_name']} (x{listing_dict['quantity']}) pour {int(price)} Coins !", listing_dict

def db_create_market_listing(user_id: int, item_name: str, quantity: int, price: float, is_troc: int = 0, wanted_item: str = None, material_id: str = None) -> Tuple[bool, str, str]:
    """Crée une nouvelle annonce sur l'Hôtel des Ventes avec son vrai bloc Minecraft 3D."""
    from services.block_renderer import normalize_material_key
    user = db_get_user_by_id(user_id)
    if not user:
        return False, "Utilisateur non trouvé.", ""

    seller_username = user["minecraft_username"]
    list_id = f"list_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    resolved_mat = (material_id.strip().upper() if material_id else normalize_material_key(item_name).upper())
    img_url = resolve_minecraft_item_asset(item_name, resolved_mat)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO player_market_listings (id, seller_username, item_name, item_icon, image_url, quantity, price_coins, is_troc, wanted_item, created_at, status, material_id)
            VALUES (?, ?, ?, '🧱', ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """, (list_id, seller_username, item_name, img_url, max(1, quantity), max(1.0, price), is_troc, wanted_item, now, resolved_mat))
        conn.commit()

    return True, f"Objet '{item_name}' (Bloc: {resolved_mat}, x{quantity}) mis en vente avec succès à l'Encan d'Éther !", list_id

def db_get_mystic_pets() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mystic_pets ORDER BY price_coins ASC;")
        return [dict(row) for row in cursor.fetchall()]

# ========================================================
# Méthodes Boutique & Objets Débloqués en Base de Données
# ========================================================

def db_seed_store_items(items: List[Dict[str, Any]]):
    """Initialise ou synchronise les articles de la boutique dans SQLite."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for it in items:
            perks_val = json.dumps(it.get("perks", []), ensure_ascii=False) if isinstance(it.get("perks"), list) else it.get("perks", "[]")
            cursor.execute("""
                INSERT OR REPLACE INTO store_items (
                    id, category, name, badge, badge_color, rarity, price, price_points,
                    currency, icon, image_url, description, perks, popular, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                it["id"],
                it.get("category", "autre"),
                it.get("name", "Article"),
                it.get("badge", ""),
                it.get("badge_color", "slate"),
                it.get("rarity", "COMMUN"),
                float(it.get("price", 0.0)),
                int(it.get("price_points", 0)),
                it.get("currency", "EUR"),
                it.get("icon", "📦"),
                it.get("image_url", ""),
                it.get("description", ""),
                perks_val,
                1 if it.get("popular") else 0,
                1 if it.get("is_active", True) else 0
            ))
        conn.commit()

def db_get_store_items(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Récupère tous les articles actifs de la boutique depuis SQLite."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if not category or category == "all":
            cursor.execute("SELECT * FROM store_items WHERE is_active = 1 ORDER BY category ASC, price ASC;")
        else:
            cursor.execute("SELECT * FROM store_items WHERE is_active = 1 AND category = ? ORDER BY price ASC;", (category,))
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            if isinstance(r.get("perks"), str):
                try:
                    r["perks"] = json.loads(r["perks"])
                except Exception:
                    r["perks"] = []
            r["popular"] = bool(r.get("popular", 0))
        return rows

def db_get_store_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """Récupère un article spécifique de la boutique depuis la base de données."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM store_items WHERE id = ?;", (item_id,))
        row = cursor.fetchone()
        if not row:
            return None
        r = dict(row)
        if isinstance(r.get("perks"), str):
            try:
                r["perks"] = json.loads(r["perks"])
            except Exception:
                r["perks"] = []
        r["popular"] = bool(r.get("popular", 0))
        return r

def db_unlock_item_for_user(
    user_id: int,
    item_id: str,
    item_category: str,
    item_name: str,
    icon: Optional[str] = None,
    image_url: Optional[str] = None,
    source: str = "STORE"
) -> bool:
    """Enregistre un familier ou cosmétique débloqué pour un utilisateur."""
    user = db_get_user_by_id(user_id)
    if not user:
        return False
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    minecraft_username = user["minecraft_username"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_unlocked_items (
                user_id, minecraft_username, item_id, item_category, item_name, icon, image_url, unlocked_at, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            minecraft_username,
            item_id,
            item_category,
            item_name,
            icon or "🐾",
            image_url or "",
            now,
            source
        ))
        conn.commit()
    return True

def db_get_user_unlocked_items(user_id: int) -> List[Dict[str, Any]]:
    """Récupère tous les articles et familiers débloqués par un utilisateur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM user_unlocked_items 
            WHERE user_id = ? 
            ORDER BY unlocked_at DESC;
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]

def db_has_user_unlocked_item(user_id: int, item_id: str) -> bool:
    """Vérifie si un joueur possède déjà un article ou familier."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_unlocked_items WHERE user_id = ? AND item_id = ?;", (user_id, item_id))
        return cursor.fetchone() is not None

# ==========================================
# 13. Moteur des Quêtes Célestes
# ==========================================

def db_get_quests(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Récupère toutes les quêtes célestes configurées."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if category and category != "all":
            cursor.execute("SELECT * FROM quests WHERE category = ? ORDER BY order_index ASC;", (category,))
        else:
            cursor.execute("SELECT * FROM quests ORDER BY order_index ASC;")
        return [dict(r) for r in cursor.fetchall()]

def db_get_user_quests(user_id: int) -> List[Dict[str, Any]]:
    """
    Récupère l'ensemble des quêtes avec le statut et la progression personnalisée du joueur.
    Initialise automatiquement les quêtes si non existantes.
    """
    user = db_get_user_by_id(user_id)
    if not user:
        return []
    
    username = user["minecraft_username"]
    player = db_get_player_by_username(username)
    is_champion = player and player.get("rank") == "CHAMPION"

    quests = db_get_quests()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        user_quests = []
        for q in quests:
            cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?;", (user_id, q["id"]))
            uq_row = cursor.fetchone()
            
            if not uq_row:
                # Progression initiale
                current = 0
                status = "EN_COURS"
                
                # Bonus Champion ou progression existante
                if q["id"] == "quest_champion_awakening" and is_champion:
                    current = 1
                    status = "TERMINE"
                elif q["id"] == "quest_market_tycoon" and player and player.get("balance", 0) >= 500:
                    current = 500
                    status = "TERMINE"

                cursor.execute("""
                    INSERT INTO user_quests (user_id, quest_id, current_count, target_count, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (user_id, q["id"], current, q["target_count"], status, now))
                conn.commit()
                
                uq_data = {
                    "current_count": current,
                    "target_count": q["target_count"],
                    "status": status,
                    "claimed_at": None,
                    "updated_at": now
                }
            else:
                uq_data = dict(uq_row)
                # Si le joueur est devenu Champion après coup
                if q["id"] == "quest_champion_awakening" and is_champion and uq_data["status"] == "EN_COURS":
                    uq_data["current_count"] = 1
                    uq_data["status"] = "TERMINE"
                    cursor.execute("UPDATE user_quests SET current_count = 1, status = 'TERMINE', updated_at = ? WHERE user_id = ? AND quest_id = ?;", (now, user_id, q["id"]))
                    conn.commit()

            target = q["target_count"] or 1
            cur = min(uq_data["current_count"], target)
            pct = int((cur / target) * 100)
            
            merged = dict(q)
            merged["current_count"] = cur
            merged["status"] = uq_data["status"]
            merged["percent"] = pct
            merged["claimed_at"] = uq_data.get("claimed_at")
            merged["is_claimable"] = (uq_data["status"] == "TERMINE")
            user_quests.append(merged)

        return user_quests

def db_update_quest_progress(user_id: int, quest_id: str, count: int = 1, is_absolute: bool = False) -> Dict[str, Any]:
    """Incrémente ou met à jour l'avancement d'une quête."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target_count FROM quests WHERE id = ?;", (quest_id,))
        q_row = cursor.fetchone()
        if not q_row:
            return {"success": False, "error": "Quête introuvable"}
        target = q_row["target_count"]

        cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?;", (user_id, quest_id))
        uq_row = cursor.fetchone()
        
        if not uq_row:
            current = count
            status = "TERMINE" if current >= target else "EN_COURS"
            cursor.execute("""
                INSERT INTO user_quests (user_id, quest_id, current_count, target_count, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (user_id, quest_id, current, target, status, now))
        else:
            old_status = uq_row["status"]
            if old_status == "RECLAME":
                return {"success": True, "status": "RECLAME", "current_count": uq_row["current_count"]}
            
            new_count = count if is_absolute else uq_row["current_count"] + count
            new_status = "TERMINE" if new_count >= target else "EN_COURS"
            cursor.execute("""
                UPDATE user_quests 
                SET current_count = ?, target_count = ?, status = ?, updated_at = ?
                WHERE user_id = ? AND quest_id = ?;
            """, (new_count, target, new_status, now, user_id, quest_id))
            current = new_count
            status = new_status
        
        conn.commit()
        return {"success": True, "quest_id": quest_id, "current_count": current, "target_count": target, "status": status}

def db_claim_quest(user_id: int, quest_id: str) -> Dict[str, Any]:
    """Réclame les récompenses d'une quête terminée."""
    user = db_get_user_by_id(user_id)
    if not user:
        return {"success": False, "error": "Utilisateur non trouvé"}
    
    username = user["minecraft_username"]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE id = ?;", (quest_id,))
        q = cursor.fetchone()
        if not q:
            return {"success": False, "error": "Quête inexistante"}
        q = dict(q)

        cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?;", (user_id, quest_id))
        uq = cursor.fetchone()
        if not uq:
            return {"success": False, "error": "Quête non démarrée"}
        uq = dict(uq)

        if uq["status"] == "RECLAME":
            return {"success": False, "error": "Récompense déjà réclamée"}
        if uq["status"] != "TERMINE":
            return {"success": False, "error": "Quête pas encore complétée"}

        # 1. Créditer les Pièces (Coins + Points unifiés en Pièces ⛃)
        reward_coins = float(q.get("reward_coins", 0.0))
        reward_points = float(q.get("reward_points", 0.0))
        total_coins = reward_coins + reward_points
        if total_coins > 0:
            cursor.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);", (total_coins, username))
            if reward_points > 0:
                cursor.execute("UPDATE users SET shop_points = shop_points + ? WHERE id = ?;", (int(reward_points), user_id))

        # 3. Mettre à jour le statut
        cursor.execute("UPDATE user_quests SET status = 'RECLAME', claimed_at = ?, updated_at = ? WHERE user_id = ? AND quest_id = ?;", (now, now, user_id, quest_id))
        conn.commit()

    # 4. Débloquer l'objet en DB et en jeu
    reward_item_id = q.get("reward_item_id")
    if reward_item_id:
        db_unlock_item_for_user(
            user_id=user_id,
            item_id=reward_item_id,
            item_category="quête",
            item_name=q.get("reward_item_name", reward_item_id),
            icon=q.get("icon", "📦"),
            image_url=q.get("image_url", ""),
            source="QUEST"
        )
    try:
        from services.rcon_service import execute_server_command
        if reward_item_id:
            execute_server_command(f"store give {username} {reward_item_id} 1")
        execute_server_command(f'title {username} actionbar {{"text":"⭐ Quête Réclamée : {q["title"]} ! (+{int(total_coins)} ⛃ Pièces)","color":"gold"}}')
        execute_server_command(f'playsound minecraft:entity.player.levelup master {username}')
    except Exception:
        pass

    return {
        "success": True,
        "quest_id": quest_id,
        "title": q["title"],
        "reward_coins": total_coins,
        "reward_points": 0,
        "reward_item_name": q.get("reward_item_name")
    }

# ==========================================
# 14. Moteur des Succès & Trophées Royaux
# ==========================================

def db_get_all_achievements() -> List[Dict[str, Any]]:
    """Récupère l'ensemble des trophées disponibles."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM achievements ORDER BY order_index ASC;")
        return [dict(r) for r in cursor.fetchall()]

def db_get_user_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Récupère les succès du joueur avec état débloqué/verrouillé."""
    # Synchronise d'abord automatiquement les succès évidents
    db_sync_user_achievements_auto(user_id)

    achievements = db_get_all_achievements()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id = ?;", (user_id,))
        unlocked_map = {row["achievement_id"]: row["unlocked_at"] for row in cursor.fetchall()}

        result = []
        for ach in achievements:
            item = dict(ach)
            unlocked = ach["id"] in unlocked_map
            item["unlocked"] = unlocked
            item["unlocked_at"] = unlocked_map.get(ach["id"])
            result.append(item)
        return result

def db_unlock_achievement(user_id: int, achievement_id: str) -> Dict[str, Any]:
    """Débloque un succès pour l'utilisateur, attribue les points et déclenche la notification RCON."""
    user = db_get_user_by_id(user_id)
    if not user:
        return {"success": False, "error": "Utilisateur introuvable"}
    
    username = user["minecraft_username"]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM achievements WHERE id = ?;", (achievement_id,))
        ach = cursor.fetchone()
        if not ach:
            return {"success": False, "error": "Succès inconnu"}
        ach = dict(ach)

        cursor.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?;", (user_id, achievement_id))
        if cursor.fetchone():
            return {"success": True, "already_unlocked": True, "achievement": ach}

        cursor.execute("""
            INSERT INTO user_achievements (user_id, achievement_id, unlocked_at)
            VALUES (?, ?, ?);
        """, (user_id, achievement_id, now))

        points = int(ach.get("reward_points", 0))
        if points > 0:
            cursor.execute("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);", (float(points), username))
        
        conn.commit()

    # Déclencher le toast sonore et l'affichage in-game
    try:
        from services.rcon_service import execute_server_command
        execute_server_command(f'title {username} title {{"text":"🏆 SUCCÈS DÉBLOQUÉ !","color":"gold","bold":true}}')
        execute_server_command(f'title {username} subtitle {{"text":"{ach["title"]} (+{ach["reward_points"]} ⛃ Pièces)","color":"aqua"}}')
        execute_server_command(f'playsound minecraft:ui.toast.challenge_complete master {username}')
    except Exception:
        pass

    return {"success": True, "achievement": ach, "points_awarded": points}

def db_sync_user_achievements_auto(user_id: int):
    """Vérifie l'état du joueur et débloque les succès mérités."""
    user = db_get_user_by_id(user_id)
    if not user:
        return
    username = user["minecraft_username"]
    player = db_get_player_by_username(username)

    # 1. Premier Pas Céleste (tout joueur inscrit)
    db_unlock_achievement(user_id, "ach_first_steps")

    # 2. Champion Sacré (rang CHAMPION)
    if player and player.get("rank") == "CHAMPION":
        db_unlock_achievement(user_id, "ach_crowned_champion")

    # 3. Maître de la Bourse (balance >= 10,000)
    if player and player.get("balance", 0) >= 10000:
        db_unlock_achievement(user_id, "ach_market_baron")

    # 4. Dompteur des Étoiles (possède au moins un familier débloqué)
    unlocked = db_get_user_unlocked_items(user_id)
    has_pet = any("pet_" in it["item_id"] for it in unlocked)
    if has_pet:
        db_unlock_achievement(user_id, "ach_stellar_tamer")

    # 5. Garde de l'Aetherite (possède une aura ou booster)
    has_booster_or_aura = any("aura_" in it["item_id"] or "booster_" in it["item_id"] for it in unlocked)
    if has_booster_or_aura:
        db_unlock_achievement(user_id, "ach_vault_sentinel")

# ==========================================
# 15. Moteur des Donjons Instanciés
# ==========================================

def db_get_all_dungeons() -> List[Dict[str, Any]]:
    """Récupère l'ensemble des donjons instanciés disponibles."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dungeons ORDER BY order_index ASC;")
        return [dict(r) for r in cursor.fetchall()]

def db_can_enter_dungeon(user_id: int, dungeon_id: str) -> Tuple[bool, str]:
    """Vérifie si un joueur a accès au donjon (Champion gratuit ou possession d'un passe)."""
    user = db_get_user_by_id(user_id)
    if not user:
        return False, "Utilisateur introuvable"
    
    username = user["minecraft_username"]
    player = db_get_player_by_username(username)

    # Privilège Champion du Royaume : Accès Libre Illimité
    if player and player.get("rank") == "CHAMPION":
        return True, "Accès Libre (Privilège du Champion du Royaume)"

    # Vérifier s'il possède un passe de donjon débloqué
    if db_has_user_unlocked_item(user_id, "dungeon_pass_bundle"):
        return True, "Accès Valide (Passe Donjon Détenu)"

    return False, "Passe de Donjon requis (Disponible en Boutique ou offert aux Champions)"

def db_enter_dungeon(user_id: int, dungeon_id: str) -> Dict[str, Any]:
    """Initie une expédition de donjon pour le joueur."""
    user = db_get_user_by_id(user_id)
    if not user:
        return {"success": False, "error": "Utilisateur non trouvé"}

    can_enter, reason = db_can_enter_dungeon(user_id, dungeon_id)
    if not can_enter:
        return {"success": False, "error": reason}

    username = user["minecraft_username"]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dungeons WHERE id = ?;", (dungeon_id,))
        dungeon = cursor.fetchone()
        if not dungeon:
            return {"success": False, "error": "Donjon introuvable"}
        dungeon = dict(dungeon)

        cursor.execute("""
            INSERT INTO dungeon_runs (user_id, username, dungeon_id, status, wave, coins_earned, started_at)
            VALUES (?, ?, ?, 'ACTIVE', 1, 0, ?);
        """, (user_id, username, dungeon_id, now))
        run_id = cursor.lastrowid
        conn.commit()

    # Déclencher le téléporteur in-game / arène via RCON
    try:
        from services.rcon_service import execute_server_command
        execute_server_command(f"teleport {username} 0 121 15")
        execute_server_command(f'title {username} title {{"text":"⚔️ {dungeon["name"]}","color":"red","bold":true}}')
        execute_server_command(f'title {username} subtitle {{"text":"Boss : {dungeon["boss_name"]} !","color":"gold"}}')
        execute_server_command(f'playsound minecraft:entity.ender_dragon.growl master {username}')
    except Exception:
        pass

    return {
        "success": True,
        "run_id": run_id,
        "dungeon": dungeon,
        "reason": reason
    }

def db_get_user_dungeon_history(user_id: int) -> List[Dict[str, Any]]:
    """Récupère l'historique des expéditions de donjon du joueur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dr.*, d.name as dungeon_name, d.difficulty, d.boss_name 
            FROM dungeon_runs dr
            JOIN dungeons d ON dr.dungeon_id = d.id
            WHERE dr.user_id = ?
            ORDER BY dr.started_at DESC LIMIT 20;
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]

def db_get_recent_quiz_winners(limit: int = 10) -> List[Dict[str, Any]]:
    """Récupère les derniers gagnants du quiz in-game avec leurs gains de jetons."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 5,
                won_at TEXT NOT NULL
            );
        """)
        cursor.execute("""
            SELECT id, username, question, answer, points, won_at
            FROM quiz_winners
            ORDER BY id DESC
            LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def db_record_quiz_winner(username: str, question: str, answer: str, points: int = 5) -> bool:
    """Enregistre un gagnant du quiz et crédite ses jetons boutique."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 5,
                won_at TEXT NOT NULL
            );
        """)
        cursor.execute("""
            INSERT INTO quiz_winners (username, question, answer, points, won_at)
            VALUES (?, ?, ?, ?, ?);
        """, (username, question, answer, points, now))
        cursor.execute("""
            UPDATE players
            SET balance = balance + ?
            WHERE LOWER(username) = LOWER(?);
        """, (float(points), username))
        conn.commit()
        return True

# ========================================================
# 17. Moteur de Déballage de Caisses Célestes & RNG
# ========================================================

CELESTIAL_CRATE_LOOT_TABLE = [
    # COMMUN (55% = 550)
    {"id": "coins_150", "name": "150 Coins d'Éther", "rarity": "COMMUN", "weight": 200, "type": "coins", "amount": 150.0, "icon": "🪙", "image_url": "/static/images/ores/ore_coal.png"},
    {"id": "coins_300", "name": "300 Coins d'Éther", "rarity": "COMMUN", "weight": 150, "type": "coins", "amount": 300.0, "icon": "🪙", "image_url": "/static/images/ores/ore_copper.png"},
    {"id": "ore_coal_16", "name": "16x Charbon d'Éther", "rarity": "COMMUN", "weight": 100, "type": "ore", "amount": 16, "icon": "⛏️", "image_url": "/static/images/ores/ore_coal.png"},
    {"id": "key_mystic_refill", "name": "1x Clé Céleste Remplacée", "rarity": "COMMUN", "weight": 100, "type": "key", "amount": 1, "key_type": "celestial", "icon": "🗝️", "image_url": "/static/images/items/key_mystic.png"},

    # RARE (28% = 280)
    {"id": "coins_800", "name": "800 Coins d'Éther", "rarity": "RARE", "weight": 100, "type": "coins", "amount": 800.0, "icon": "🪙", "image_url": "/static/images/ores/ore_gold.png"},
    {"id": "ore_gold_8", "name": "8x Or Purifié", "rarity": "RARE", "weight": 80, "type": "ore", "amount": 8, "icon": "🪙", "image_url": "/static/images/ores/ore_gold.png"},
    {"id": "booster_mining", "name": "Booster de Minage x2 (1h)", "rarity": "RARE", "weight": 60, "type": "store_item", "icon": "⛏️", "image_url": "/static/images/items/booster_mining.png"},
    {"id": "points_50", "name": "50 Points Boutique", "rarity": "RARE", "weight": 40, "type": "points", "amount": 50, "icon": "⭐", "image_url": "/static/images/items/key_mystic.png"},

    # ÉPIQUE (12% = 120)
    {"id": "coins_2500", "name": "2,500 Coins d'Éther", "rarity": "ÉPIQUE", "weight": 40, "type": "coins", "amount": 2500.0, "icon": "🪙", "image_url": "/static/images/ores/ore_diamond.png"},
    {"id": "ore_diamond_4", "name": "4x Diamants Bruts Célestes", "rarity": "ÉPIQUE", "weight": 35, "type": "ore", "amount": 4, "icon": "💎", "image_url": "/static/images/ores/ore_diamond.png"},
    {"id": "dungeon_pass_bundle", "name": "1x Passe Donjon Instancié", "rarity": "ÉPIQUE", "weight": 25, "type": "store_item", "icon": "🎟️", "image_url": "/static/images/items/dungeon_pass.png"},
    {"id": "points_150", "name": "150 Points Boutique", "rarity": "ÉPIQUE", "weight": 20, "type": "points", "amount": 150, "icon": "⭐", "image_url": "/static/images/items/key_omega.png"},

    # LÉGENDAIRE (4.2% = 42)
    {"id": "coins_10000", "name": "10,000 Coins d'Éther", "rarity": "LÉGENDAIRE", "weight": 15, "type": "coins", "amount": 10000.0, "icon": "💰", "image_url": "/static/images/ores/ore_netherite.png"},
    {"id": "ore_netherite_1", "name": "1x Lingot de Netherite", "rarity": "LÉGENDAIRE", "weight": 12, "type": "ore", "amount": 1, "icon": "🖤", "image_url": "/static/images/ores/ore_netherite.png"},
    {"id": "pet_fox", "name": "Familier Renard Astral", "rarity": "LÉGENDAIRE", "weight": 10, "type": "pet", "icon": "🦊", "image_url": "/static/images/items/pet_fox.png"},
    {"id": "rank_vip", "name": "Grade VIP Royal", "rarity": "LÉGENDAIRE", "weight": 5, "type": "rank", "rank_id": "VIP", "icon": "👑", "image_url": "/static/images/items/rank_vip.png"},

    # MYTHIQUE (0.8% = 8)
    {"id": "coins_50000", "name": "50,000 Coins d'Éther (Jackpot)", "rarity": "MYTHIQUE", "weight": 3, "type": "coins", "amount": 50000.0, "icon": "💎", "image_url": "/static/images/ores/ore_aetherite.png"},
    {"id": "ore_aetherite_1", "name": "1x Fragment d'Aetherite", "rarity": "MYTHIQUE", "weight": 2, "type": "ore", "amount": 1, "icon": "🪐", "image_url": "/static/images/ores/ore_aetherite.png"},
    {"id": "item_nano_banana", "name": "Banane Quantique d'Or (Nano Banana)", "rarity": "MYTHIQUE", "weight": 2, "type": "artifact", "icon": "🍌", "image_url": "/static/images/items/item_nano_banana.png", "lore": "+500% Vitesse de Minage & Halo Cosmique"},
    {"id": "rank_aether", "name": "Grade Aether (Héros Céleste)", "rarity": "MYTHIQUE", "weight": 1, "type": "rank", "rank_id": "AETHER", "icon": "👑", "image_url": "/static/images/items/rank_aether.png"},
]

OMEGA_CRATE_LOOT_TABLE = [
    # RARE (50% = 500)
    {"id": "coins_1500", "name": "1,500 Coins d'Éther", "rarity": "RARE", "weight": 200, "type": "coins", "amount": 1500.0, "icon": "🪙", "image_url": "/static/images/ores/ore_diamond.png"},
    {"id": "ore_diamond_16", "name": "16x Diamants Bruts Célestes", "rarity": "RARE", "weight": 150, "type": "ore", "amount": 16, "icon": "💎", "image_url": "/static/images/ores/ore_diamond.png"},
    {"id": "dungeon_pass_bundle", "name": "2x Passes Donjons Instanciés", "rarity": "RARE", "weight": 100, "type": "store_item", "icon": "🎟️", "image_url": "/static/images/items/dungeon_pass.png"},
    {"id": "points_150", "name": "150 Points Boutique", "rarity": "RARE", "weight": 50, "type": "points", "amount": 150, "icon": "⭐", "image_url": "/static/images/items/key_omega.png"},

    # ÉPIQUE (32% = 320)
    {"id": "coins_6000", "name": "6,000 Coins d'Éther", "rarity": "ÉPIQUE", "weight": 120, "type": "coins", "amount": 6000.0, "icon": "🪙", "image_url": "/static/images/ores/ore_netherite.png"},
    {"id": "ore_netherite_2", "name": "2x Lingots de Netherite", "rarity": "ÉPIQUE", "weight": 100, "type": "ore", "amount": 2, "icon": "🖤", "image_url": "/static/images/ores/ore_netherite.png"},
    {"id": "cosmetic_wings", "name": "Ailes Quantiques Stellaires", "rarity": "ÉPIQUE", "weight": 60, "type": "store_item", "icon": "🪽", "image_url": "/static/images/items/cosmetic_wings.png"},
    {"id": "pet_goat", "name": "Familier Bélier des Nuages", "rarity": "ÉPIQUE", "weight": 40, "type": "pet", "icon": "🐐", "image_url": "/static/images/items/pet_goat.png"},

    # LÉGENDAIRE (15% = 150)
    {"id": "coins_25000", "name": "25,000 Coins d'Éther", "rarity": "LÉGENDAIRE", "weight": 60, "type": "coins", "amount": 25000.0, "icon": "💰", "image_url": "/static/images/ores/ore_aetherite.png"},
    {"id": "ore_aetherite_2", "name": "2x Fragments d'Aetherite", "rarity": "LÉGENDAIRE", "weight": 40, "type": "ore", "amount": 2, "icon": "🪐", "image_url": "/static/images/ores/ore_aetherite.png"},
    {"id": "pet_phoenix", "name": "Phénix d'Or Primordial", "rarity": "LÉGENDAIRE", "weight": 30, "type": "pet", "icon": "🦅", "image_url": "/static/images/items/pet_phoenix.png"},
    {"id": "rank_titan", "name": "Grade Titan Primordial", "rarity": "LÉGENDAIRE", "weight": 20, "type": "rank", "rank_id": "TITAN", "icon": "👑", "image_url": "/static/images/items/rank_titan.png"},

    # MYTHIQUE (3% = 30)
    {"id": "coins_150000", "name": "150,000 Coins d'Éther (MEGA JACKPOT)", "rarity": "MYTHIQUE", "weight": 12, "type": "coins", "amount": 150000.0, "icon": "💎", "image_url": "/static/images/ores/ore_aetherite.png"},
    {"id": "pet_dragon", "name": "Mini-Dragon Stellaire", "rarity": "MYTHIQUE", "weight": 8, "type": "pet", "icon": "🐉", "image_url": "/static/images/items/pet_dragon.png"},
    {"id": "item_nano_banana", "name": "Nano Banana Primordiale (Artefact Mythique)", "rarity": "MYTHIQUE", "weight": 6, "type": "artifact", "icon": "🍌", "image_url": "/static/images/items/item_nano_banana.png", "lore": "+500% Vitesse de Minage & Aura Cosmique Légendaire"},
    {"id": "rank_champion", "name": "Grade Champion du Royaume (Rang Ultime)", "rarity": "MYTHIQUE", "weight": 4, "type": "rank", "rank_id": "CHAMPION", "icon": "👑", "image_url": "/static/images/items/rank_champion.png"},
]

def db_get_user_keys(user_id: int) -> Dict[str, int]:
    """Récupère le solde de clés Célestes et Oméga de l'utilisateur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key_type, quantity FROM user_keys WHERE user_id = ?;", (user_id,))
        rows = dict(cursor.fetchall())
        
        # Initialisation par défaut si nécessaire
        if "celestial" not in rows:
            cursor.execute("INSERT OR REPLACE INTO user_keys (user_id, key_type, quantity) VALUES (?, 'celestial', 5);", (user_id,))
            rows["celestial"] = 5
        if "omega" not in rows:
            cursor.execute("INSERT OR REPLACE INTO user_keys (user_id, key_type, quantity) VALUES (?, 'omega', 3);", (user_id,))
            rows["omega"] = 3
        conn.commit()
        return rows

def db_add_user_keys(user_id: int, key_type: str, quantity: int = 1) -> int:
    """Ajoute des clés au compte d'un joueur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_keys (user_id, key_type, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, key_type) DO UPDATE SET quantity = quantity + excluded.quantity;
        """, (user_id, key_type, quantity))
        conn.commit()
        cursor.execute("SELECT quantity FROM user_keys WHERE user_id = ? AND key_type = ?;", (user_id, key_type))
        r = cursor.fetchone()
        return r[0] if r else quantity

def select_crate_drop(crate_type: str) -> Dict[str, Any]:
    """Sélectionne un lot selon une distribution aléatoire pondérée stricte."""
    table = OMEGA_CRATE_LOOT_TABLE if crate_type.lower() == "omega" else CELESTIAL_CRATE_LOOT_TABLE
    total_weight = sum(it["weight"] for it in table)
    roll = random.uniform(0, total_weight)
    acc = 0.0
    for it in table:
        acc += it["weight"]
        if roll <= acc:
            return dict(it)
    return dict(table[-1])

def db_open_crate(user_id: int, crate_type: str) -> Dict[str, Any]:
    """Ouvre une caisse, consomme une clé, attribue les récompenses en DB et en jeu."""
    user = db_get_user_by_id(user_id)
    if not user:
        return {"success": False, "error": "Utilisateur non trouvé"}

    crate_type = crate_type.lower()
    if crate_type not in ["celestial", "omega"]:
        crate_type = "celestial"

    keys = db_get_user_keys(user_id)
    key_count = keys.get(crate_type, 0)
    if key_count <= 0:
        return {
            "success": False,
            "error": f"Vous n'avez pas de Clé {'Oméga' if crate_type == 'omega' else 'Céleste'} disponible !",
            "requires_purchase": True
        }

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    username = user["minecraft_username"]

    # 1. Décrémenter la clé
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_keys 
            SET quantity = quantity - 1 
            WHERE user_id = ? AND key_type = ? AND quantity > 0;
        """, (user_id, crate_type))
        conn.commit()

    # 2. Tirage RNG pondéré
    drop = select_crate_drop(crate_type)

    # 3. Attribution des récompenses en base
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rew_type = drop["type"]

        if rew_type == "coins":
            coins = float(drop.get("amount", 0.0))
            cursor.execute("UPDATE players SET balance = balance + ? WHERE username = ?;", (coins, username))
        elif rew_type == "points":
            pts = int(drop.get("amount", 0))
            cursor.execute("UPDATE users SET shop_points = shop_points + ? WHERE id = ?;", (pts, user_id))
        elif rew_type == "key":
            k_type = drop.get("key_type", "celestial")
            cursor.execute("""
                INSERT INTO user_keys (user_id, key_type, quantity) VALUES (?, ?, 1)
                ON CONFLICT(user_id, key_type) DO UPDATE SET quantity = quantity + 1;
            """, (user_id, k_type))
        elif rew_type == "rank":
            rank_id = drop.get("rank_id", "VIP")
            cursor.execute("UPDATE players SET rank = ? WHERE username = ?;", (rank_id, username))
        elif rew_type in ["store_item", "pet", "artifact", "ore"]:
            db_unlock_item_for_user(
                user_id=user_id,
                item_id=drop["id"],
                item_category="caisse",
                item_name=drop["name"],
                icon=drop.get("icon", "📦"),
                image_url=drop.get("image_url", ""),
                source="CRATE"
            )

        # 4. Enregistrement dans l'historique des ouvertures
        cursor.execute("""
            INSERT INTO crate_openings (user_id, username, crate_type, rarity, item_name, reward_type, reward_value, icon, image_url, opened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            username,
            crate_type,
            drop["rarity"],
            drop["name"],
            rew_type,
            str(drop.get("amount", "")),
            drop.get("icon", "🎁"),
            drop.get("image_url", ""),
            now
        ))
        conn.commit()

    # 5. Déclenchement de l'animation et de la livraison in-game via RCON
    try:
        from services.rcon_service import execute_server_command
        execute_server_command(f"crate open {username} {crate_type}")
        execute_server_command(f'title {username} actionbar {{"text":"🎁 Caisse {crate_type.capitalize()} : {drop["name"]} ({drop["rarity"]}) !","color":"gold"}}')
        execute_server_command(f"playsound minecraft:ui.toast.challenge_complete master {username}")
        
        # Don de l'objet physique in-game
        if drop["type"] in ["store_item", "artifact", "ore", "pet"]:
            execute_server_command(f"store give {username} {drop['id']} 1")
    except Exception:
        pass

    # 6. Génération de la bande de roulette (30 items) pour l'animation web fluide
    table = OMEGA_CRATE_LOOT_TABLE if crate_type == "omega" else CELESTIAL_CRATE_LOOT_TABLE
    roulette_items = [random.choice(table) for _ in range(30)]
    # Place le lot gagnant à l'index 25 pour l'arrêt précis de la roulette
    roulette_items[25] = drop

    updated_keys = db_get_user_keys(user_id)

    return {
        "success": True,
        "crate_type": crate_type,
        "drop": drop,
        "winning_index": 25,
        "roulette_items": roulette_items,
        "remaining_keys": updated_keys.get(crate_type, 0)
    }

def db_get_recent_crate_openings(limit: int = 15) -> List[Dict[str, Any]]:
    """Récupère les dernières caisses ouvertes pour le flux d'activité mondial."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, username, crate_type, rarity, item_name, icon, image_url, opened_at
            FROM crate_openings
            ORDER BY id DESC
            LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]


