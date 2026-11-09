from typing import Dict, List, Optional, Tuple, Any
import uuid
import re
from services.database import (
    db_save_order,
    db_get_recent_orders,
    db_get_user_by_id,
    db_get_user_by_username,
    db_get_player_by_username,
    db_spend_shop_points,
    db_seed_store_items,
    db_get_store_items,
    db_get_store_item_by_id,
    db_unlock_item_for_user,
    db_get_user_unlocked_items,
    db_has_user_unlocked_item
)
from services.rcon_service import execute_server_command

STORE_ITEMS = [
    {
        "id": "rank_vip",
        "category": "grades",
        "name": "Grade VIP",
        "badge": "VIP",
        "badge_color": "emerald",
        "rarity": "RARE",
        "price": 4.99,
        "price_points": 500,
        "currency": "EUR",
        "icon": "👑",
        "image_url": "/static/images/items/rank_vip.png",
        "description": "Le grade idéal pour commencer l'aventure avec confort, style et commandes utiles.",
        "perks": [
            "Préfixe [VIP] émeraude dans le chat et le tablist",
            "Accès aux commandes /fly en lobby et /feed",
            "+2 Homes supplémentaires (/sethome)",
            "Kit VIP hebdomadaire (Armure fer P2 + 16 Pommes dorées)",
            "Accès prioritaire aux serveurs pleins"
        ]
    },
    {
        "id": "rank_aether",
        "category": "grades",
        "name": "Grade Aether (Héros)",
        "badge": "AETHER",
        "badge_color": "sky",
        "rarity": "ÉPIQUE",
        "price": 14.99,
        "price_points": 1500,
        "currency": "EUR",
        "icon": "🪐",
        "image_url": "/static/images/items/rank_aether.png",
        "popular": True,
        "description": "Le grade prestigieux conçu pour les maîtres et explorateurs du monde céleste Aether.",
        "perks": [
            "Préfixe [AETHER] cyan scintillant animé",
            "Commandes /fly partout en survie + /workbench + /anvil",
            "+10 Homes personnalisables",
            "Kit Aether légendaire (Armure diamant P4 + Pioche Fortune III)",
            "Accès exclusif au canal Discord VIP & Salons Vocaux",
            "2 Clés Mystiques offertes chaque mois"
        ]
    },
    {
        "id": "rank_titan",
        "category": "grades",
        "name": "Grade Titan Primordial",
        "badge": "TITAN",
        "badge_color": "amber",
        "rarity": "MYTHIQUE",
        "price": 29.99,
        "price_points": 3000,
        "currency": "EUR",
        "icon": "⚡",
        "image_url": "/static/images/items/rank_titan.png",
        "description": "La puissance ultime avec tous les privilèges cosmétiques, d'exploration et kits débloqués.",
        "perks": [
            "Préfixe [TITAN] or flamboyant dans le chat",
            "Commandes /god en zone paisible + /nick personnalisé",
            "Homes illimités & Accès au coffre Ender géant (/enderchest)",
            "Kit Titan Netherite enchanté complet toutes les 2 semaines",
            "Cape cosmétique cosmologique exclusive Aether",
            "Priorité absolue et multiplicateur x2 d'expérience"
        ]
    },
    {
        "id": "key_mystic_bundle",
        "category": "keys",
        "name": "Pack 5x Clés Célestes",
        "badge": "CLÉS",
        "badge_color": "purple",
        "rarity": "RARE",
        "price": 3.49,
        "price_points": 150,
        "currency": "EUR",
        "icon": "🗝️",
        "image_url": "/static/images/items/key_mystic.png",
        "description": "Ouvrez la Caisse des Étoiles au spawn et tentez de remporter des artéfacts rares.",
        "perks": [
            "5 Clés utilisables instantanément au Spawn",
            "Butins possibles : Armes légendaires, Spawners, Tokens",
            "Taux de drop d'items mythiques augmenté de 15%"
        ]
    },
    {
        "id": "key_omega_bundle",
        "category": "keys",
        "name": "Pack 12x Clés Oméga (Max)",
        "badge": "MEILLEURE OFFRE",
        "badge_color": "rose",
        "rarity": "LÉGENDAIRE",
        "price": 7.99,
        "price_points": 300,
        "currency": "EUR",
        "icon": "💎",
        "image_url": "/static/images/items/key_omega.png",
        "description": "Le pack ultime pour les chasseurs de trésors et pilleurs de donjons.",
        "perks": [
            "12 Clés de la Caisse Céleste",
            "Garantie d'au moins 1 item légendaire ou spawner rare",
            "+500 Aether Gems bonus offerts sur votre compte"
        ]
    },
    {
        "id": "cosmetic_wings",
        "category": "cosmetics",
        "name": "Ailes Quantiques Stellaires",
        "badge": "COSMÉTIQUE",
        "badge_color": "indigo",
        "rarity": "ÉPIQUE",
        "price": 4.50,
        "price_points": 200,
        "currency": "EUR",
        "icon": "🪽",
        "image_url": "/static/images/items/cosmetic_wings.png",
        "description": "Paire d'ailes luminescentes animées 3D flottant dans votre dos avec traînée d'étoiles.",
        "perks": [
            "Visibilité par tous les joueurs sur le serveur (sans mods)",
            "Battement sinusoïdal fluide en vol et au sol",
            "Désactivable à tout moment via /cosmetics wings"
        ]
    },
    {
        "id": "pet_dragon",
        "category": "pets",
        "name": "Mini Dragon Stellaire",
        "badge": "FAMILIER",
        "badge_color": "violet",
        "rarity": "MYTHIQUE",
        "price": 6.00,
        "price_points": 250,
        "currency": "EUR",
        "icon": "🐉",
        "image_url": "/static/images/items/pet_dragon.png",
        "description": "Compagnon volant en orbite avec une aura de braises et d'étincelles dorées.",
        "perks": [
            "Aura Flamme : +15% de vitesse de minage partagée avec les alliés (8 blocs)",
            "Orbite de vol continue et petites vocalises de dragon",
            "Invocable / rengainable via /pet dragon"
        ]
    },
    {
        "id": "pet_capybara",
        "category": "pets",
        "name": "Capybara Céleste (Gardien Zen)",
        "badge": "SÉRÉNITÉ",
        "badge_color": "emerald",
        "rarity": "ÉPIQUE",
        "price": 4.99,
        "price_points": 200,
        "currency": "EUR",
        "icon": "🐾",
        "image_url": "/static/images/items/pet_capybara.png",
        "description": "Le gardien suprême de la paix avec son lotus sacré et son aura régénératrice.",
        "perks": [
            "Aura Apaisement : confère Régénération I aux alliés réunis au bivouac",
            "Repousse les Phantoms et monstres hostiles nocturnes",
            "Particules de cœurs bienveillants et lotus sacré flottant"
        ]
    },
    {
        "id": "pet_fox",
        "category": "pets",
        "name": "Renard Astral (Kitsune Lunaire)",
        "badge": "COMMERCE",
        "badge_color": "sky",
        "rarity": "ÉPIQUE",
        "price": 5.49,
        "price_points": 220,
        "currency": "EUR",
        "icon": "🦊",
        "image_url": "/static/images/items/pet_fox.png",
        "description": "Renard céleste à 3 queues de comètes apportant chance et prospérité marchande.",
        "perks": [
            "Aura Prospérité : +10% de pièces d'or bonus sur tous les trocs et ventes",
            "3 Queues de comètes scintillantes en traînée lumineuse",
            "Acrobaties féeriques autour de votre aventurier"
        ]
    },
    {
        "id": "pet_goat",
        "category": "pets",
        "name": "Bélier des Nuages (Aérien)",
        "badge": "EXPLORATION",
        "badge_color": "indigo",
        "rarity": "RARE",
        "price": 4.50,
        "price_points": 180,
        "currency": "EUR",
        "icon": "🐐",
        "image_url": "/static/images/items/pet_goat.png",
        "description": "Bélier d'albâtre perché sur des cumulus et orné de cornes en spirale dorée.",
        "perks": [
            "Aura Saut Céleste : confère Saut II (Jump Boost) et immunité aux chutes",
            "Nuages vaporeux jaillissant sous les sabots à chaque foulée",
            "Idéal pour escalader les Skylands et donjons flottants"
        ]
    },
    {
        "id": "pet_phoenix",
        "category": "pets",
        "name": "Phénix d'Or Primordial",
        "badge": "RENAISSANCE",
        "badge_color": "amber",
        "rarity": "MYTHIQUE",
        "price": 7.99,
        "price_points": 350,
        "currency": "EUR",
        "icon": "🦅",
        "image_url": "/static/images/items/pet_phoenix.png",
        "description": "Sculpture 3D Multi-Blocs articulée : grand oiseau solaire aux ailes déployées et serres d'or.",
        "perks": [
            "Modèle 3D Volumétrique complet en jeu (Ailes battantes, crête & queue flamboyante)",
            "Aura Seconde Chance : absorbe un coup mortel et restaure 5 cœurs",
            "Bénédiction de résistance au feu pour tout le groupe (/pet phoenix)"
        ]
    },
    {
        "id": "pet_griffin",
        "category": "pets",
        "name": "Griffon Astral Souverain",
        "badge": "NOUVEAU 3D",
        "badge_color": "amber",
        "rarity": "LÉGENDAIRE",
        "price": 8.99,
        "price_points": 400,
        "currency": "EUR",
        "icon": "🦁",
        "image_url": "/static/images/items/pet_griffin.png",
        "popular": True,
        "description": "Créature royale 3D géante mi-lion d'or, mi-aigle céleste d'albâtre aux ailes de cristal.",
        "perks": [
            "Sculpture 3D Multi-Blocs articulée (4 pattes griffues, ailes battantes, tête d'aigle)",
            "Aura Force Souveraine : octroie Force I et vitesse d'attaque aux alliés proches",
            "Invocable instantanément en jeu via /pet griffin ou /shop"
        ]
    },
    {
        "id": "booster_mining",
        "category": "boosters",
        "name": "Booster de Minage Céleste (x2)",
        "badge": "BOOSTER",
        "badge_color": "amber",
        "rarity": "COMMUN",
        "price": 2.99,
        "price_points": 120,
        "currency": "EUR",
        "icon": "⛏️",
        "image_url": "/static/images/items/booster_mining.png",
        "description": "Multipliez par 2 vos récoltes de minerais et d'or pendant 2 heures de jeu.",
        "perks": [
            "Multiplicateur de drop x2 sur tous les minerais du monde",
            "Activable quand vous le souhaitez via /booster",
            "Cumulable avec les buffs mondiaux de l'Agora"
        ]
    },
    {
        "id": "rank_champion",
        "category": "grades",
        "name": "Grade Champion du Royaume",
        "badge": "PRESTIGE #1",
        "badge_color": "purple",
        "rarity": "LÉGENDAIRE",
        "price": 49.99,
        "price_points": 5000,
        "currency": "EUR",
        "icon": "👑",
        "image_url": "/static/images/items/rank_champion.png",
        "popular": True,
        "description": "Le titre suprême réservé aux légendes de l'Archipel Céleste avec privilèges cosmiques absolus.",
        "perks": [
            "Préfixe [CHAMPION] violet scintillant et titre d'honneur au spawn",
            "Déblocage automatique de l'Aura du Champion Primordial (/aura champion)",
            "Accès illimité aux donjons instanciés sans consommation de pass",
            "Kit Champion Netherite Légendaire + Ailes Quantiques offertes",
            "Solde bonus de 500k pièces d'or in-game",
            "Accès direct au salon vocal privé Discord avec les Créateurs"
        ]
    },
    {
        "id": "dungeon_pass_bundle",
        "category": "boosters",
        "name": "Pack 3x Pass Donjons Instanciés",
        "badge": "DONJONS ÉLITE",
        "badge_color": "sky",
        "rarity": "ÉPIQUE",
        "price": 4.99,
        "price_points": 250,
        "currency": "EUR",
        "icon": "🎫",
        "image_url": "/static/images/items/dungeon_pass.png",
        "description": "Accédez aux Donjons Célestes instanciés pour affronter les Boss mythiques et piller l'Archipel.",
        "perks": [
            "3 Pass utilisables au Portail des Donjons Instanciés",
            "Butins garantis : Pièces célestes, gemmes rares et fragments d'Aetherite",
            "Résurrection d'urgence incluse dans le donjon"
        ]
    },
    {
        "id": "aura_champion",
        "category": "cosmetics",
        "name": "Aura du Champion Primordial",
        "badge": "AURA ROYALE",
        "badge_color": "purple",
        "rarity": "MYTHIQUE",
        "price": 9.99,
        "price_points": 600,
        "currency": "EUR",
        "icon": "✨",
        "image_url": "/static/images/items/aura_champion.png",
        "description": "Halo stellaire royal, couronne de lumière et sceau arcanique pulsant sous vos pas.",
        "perks": [
            "Couronne céleste et anneau d'étoiles filantes animées 3D",
            "Sceau de lumière projeté au sol à vos pieds",
            "Activable / désactivable en 1-clic sur votre espace Mon Compte"
        ]
    },
    {
        "id": "magot_piece_bronze",
        "category": "magots",
        "name": "Pièce de Bronze (10 ⛃)",
        "badge": "10 ⛃ CONVERTIBLE",
        "badge_color": "amber",
        "rarity": "COMMUN",
        "price": 0.99,
        "price_points": 10,
        "currency": "EUR",
        "icon": "🪙",
        "image_url": "/static/images/items/magot_piece_bronze.png",
        "description": "Monnaie physique officielle convertible à 100% en +10 ⛃ Pièces par Clic-Droit en main.",
        "perks": [
            "Convertible à tout moment en +10 ⛃ Pièces par Clic-Droit",
            "Échangeable de joueur à joueur sans aucune taxe",
            "Déposable dans votre coffre-fort de Banque privée (/banque)"
        ]
    },
    {
        "id": "magot_piece_argent",
        "category": "magots",
        "name": "Pièce d'Argent Royale (50 ⛃)",
        "badge": "50 ⛃ CONVERTIBLE",
        "badge_color": "sky",
        "rarity": "RARE",
        "price": 2.49,
        "price_points": 50,
        "currency": "EUR",
        "icon": "🪙",
        "image_url": "/static/images/items/magot_piece_argent.png",
        "description": "Pièce d'argent frappée au sceau royal convertible en +50 ⛃ Pièces par Clic-Droit.",
        "perks": [
            "Convertible à tout moment en +50 ⛃ Pièces par Clic-Droit",
            "Sneak + Clic-Droit pour convertir toute votre pile en 1 instant",
            "Reconnue par tous les marchands et coffres de guilde"
        ]
    },
    {
        "id": "magot_sac_pieces",
        "category": "magots",
        "name": "Sac de Pièces d'Or (100 ⛃)",
        "badge": "100 ⛃ CONVERTIBLE",
        "badge_color": "amber",
        "rarity": "RARE",
        "price": 4.49,
        "price_points": 100,
        "currency": "EUR",
        "icon": "💰",
        "image_url": "/static/images/items/magot_sac_pieces.png",
        "description": "Bourse de cuir remplie de pièces d'or convertible en +100 ⛃ Pièces par Clic-Droit.",
        "perks": [
            "Convertible à 100% en +100 ⛃ Pièces sonnantes et trébuchantes",
            "Idéal pour régler de gros achats ou trocs sur l'Agora",
            "Stockable sans limite dans votre compte d'épargne"
        ]
    },
    {
        "id": "magot_lingot_or",
        "category": "magots",
        "name": "Lingot d'Or Habbo (250 ⛃)",
        "badge": "250 ⛃ HABBO CLASSIQUE",
        "badge_color": "amber",
        "rarity": "ÉPIQUE",
        "price": 9.99,
        "price_points": 250,
        "popular": True,
        "currency": "EUR",
        "icon": "🧈",
        "image_url": "/static/images/items/magot_lingot_or.png",
        "description": "Le mythique lingot d'or convertible style Habbo Hotel, valant 250 ⛃ Pièces garanties.",
        "perks": [
            "La valeur refuge par excellence de l'Archipel Céleste",
            "Convertible à 100% en +250 ⛃ Pièces par simple Clic-Droit",
            "Animation de lingot scintillant et carillon sonore à l'encaissement"
        ]
    },
    {
        "id": "magot_bloc_or",
        "category": "magots",
        "name": "Bloc d'Or Impérial (500 ⛃)",
        "badge": "500 ⛃ HAUTE VALEUR",
        "badge_color": "amber",
        "rarity": "LÉGENDAIRE",
        "price": 17.99,
        "price_points": 500,
        "currency": "EUR",
        "icon": "👑",
        "image_url": "/static/images/items/magot_bloc_or.png",
        "description": "Bloc d'argent haute valeur convertible instantanément en +500 ⛃ Pièces par Clic-Droit.",
        "perks": [
            "Convertible en +500 ⛃ Pièces nettes (garantie sans perte)",
            "Décoration prestigieuse ou réserve monétaire de guilde",
            "Sneak + Clic-Droit pour convertir tous vos blocs d'or en 1 clic"
        ]
    },
    {
        "id": "magot_bloc_emeraude",
        "category": "magots",
        "name": "Magot Suprême d'Émeraude (1 000 ⛃)",
        "badge": "1 000 ⛃ MAGOT MAX",
        "badge_color": "emerald",
        "rarity": "MYTHIQUE",
        "price": 29.99,
        "price_points": 1000,
        "popular": True,
        "currency": "EUR",
        "icon": "💎",
        "image_url": "/static/images/items/magot_bloc_emeraude.png",
        "description": "Le plus gros magot convertible du serveur : un cube d'émeraude pure valant 1 000 ⛃ Pièces !",
        "perks": [
            "Conversion royale : +1 000 ⛃ Pièces d'un seul clic",
            "Aura céleste de particules vertes émeraudes lors du dépôt",
            "Le symbole suprême de richesse sur l'Archipel AetherCraft"
        ]
    },
    {
        "id": "magot_bloc_diamant",
        "category": "magots",
        "name": "Magot Bloc de Diamant (2 500 ⛃)",
        "badge": "2 500 ⛃ HAUTE JOAILLERIE",
        "badge_color": "sky",
        "rarity": "MYTHIQUE",
        "price": 49.99,
        "price_points": 2500,
        "popular": True,
        "currency": "EUR",
        "icon": "💎",
        "image_url": "/static/images/blocks_3d/diamond_block.png",
        "description": "Somptueux cube de diamant brut d'Archipel convertible en +2 500 ⛃ Pièces par Clic-Droit.",
        "perks": [
            "Convertible instantanément en +2 500 ⛃ Pièces nettes",
            "Posable en jeu en meuble 3D de prestige ou réserve de guilde",
            "Récupérable intact par minage en survie"
        ]
    },
    {
        "id": "magot_trophee_or",
        "category": "magots",
        "name": "Trophée d'Or de Champion (5 000 ⛃)",
        "badge": "5 000 ⛃ MOBILIER PRESTIGE",
        "badge_color": "amber",
        "rarity": "LÉGENDAIRE",
        "price": 79.99,
        "price_points": 5000,
        "currency": "EUR",
        "icon": "🏆",
        "image_url": "/static/images/items/rank_champion.png",
        "description": "Mobilier 3D d'apparat sculpté à la gloire des champions, convertible en +5 000 ⛃ Pièces.",
        "perks": [
            "Trophée décoratif 3D posable au sol ou sur table",
            "Convertible à tout moment en +5 000 ⛃ Pièces",
            "Échangeable ou conservable comme monument de victoire"
        ]
    },
    {
        "id": "magot_trone_royal",
        "category": "magots",
        "name": "Trône Royal Céleste (10 000 ⛃)",
        "badge": "10 000 ⛃ TRÔNE MAJESTUEUX",
        "badge_color": "purple",
        "rarity": "MYTHIQUE",
        "price": 149.99,
        "price_points": 10000,
        "popular": True,
        "currency": "EUR",
        "icon": "👑",
        "image_url": "/static/images/blocks_3d/crying_obsidian.png",
        "description": "Le trône suprême du souverain de l'Archipel, chef-d'œuvre de mobilier valant 10 000 ⛃ Pièces.",
        "perks": [
            "Mobilier d'exception 3D posable avec couronne céleste",
            "Valeur colossale de 10 000 ⛃ Pièces récupérable par Clic-Droit",
            "Incassable à la mort, transférable entre joueurs"
        ]
    },
    {
        "id": "bloc_aether",
        "category": "magots",
        "name": "Bloc Céleste d'Aether (1 500 ⛃)",
        "badge": "1 500 ⛃ BLOC AETHER",
        "badge_color": "sky",
        "rarity": "ÉPIQUE",
        "price": 24.99,
        "price_points": 1500,
        "popular": True,
        "currency": "EUR",
        "icon": "🪐",
        "image_url": "/static/images/blocks_3d/sea_lantern.png",
        "description": "Bloc légendaire infusé de poussière d'étoiles, convertible en +1 500 ⛃ Pièces ou posable.",
        "perks": [
            "Bloc officiel d'AetherCraft à texture stellaire animée",
            "Convertible en +1 500 ⛃ Pièces par Clic-Droit",
            "Posable et cassable en survie avec restitution complète"
        ]
    },
    {
        "id": "minerai_aether",
        "category": "magots",
        "name": "Minerai d'Aether du Nether (750 ⛃)",
        "badge": "750 ⛃ FILON DU NETHER",
        "badge_color": "rose",
        "rarity": "RARE",
        "price": 12.99,
        "price_points": 750,
        "currency": "EUR",
        "icon": "☄️",
        "image_url": "/static/images/blocks_3d/ancient_debris.png",
        "description": "Filon rare cristallisé trouvable dans le Nether ou en boutique, convertible en +750 ⛃ Pièces.",
        "perks": [
            "Filon brut du Nether convertible en +750 ⛃ Pièces",
            "Peut être raffiné ou posé comme ornement minéral 3D",
            "Drop garanti et sécurisé en mode Survie et OneBlock"
        ]
    }
]

DEFAULT_ITEMS = STORE_ITEMS
ORDERS_HISTORY = []

# Initialisation & Synchronisation automatique de la Boutique avec SQLite
try:
    db_seed_store_items(STORE_ITEMS)
except Exception as e:
    pass

def get_store_items(category: Optional[str] = None) -> List[Dict]:
    """Récupère les articles directement depuis la base SQLite avec repli mémoire."""
    try:
        db_items = db_get_store_items(category)
        if db_items:
            return db_items
    except Exception:
        pass
    if not category or category == "all":
        return STORE_ITEMS
    return [item for item in STORE_ITEMS if item.get("category") == category]

def get_item_by_id(item_id: str) -> Optional[Dict]:
    """Recherche un article dans la base de données SQLite."""
    try:
        db_item = db_get_store_item_by_id(item_id)
        if db_item:
            return db_item
    except Exception:
        pass
    for item in STORE_ITEMS:
        if item["id"] == item_id:
            return item
    return None

def execute_item_delivery(username: str, item_id: str) -> List[str]:
    """Génère et exécute les commandes RCON adaptées à l'article commandé, avec don de l'objet réel in-game."""
    if not username or not re.match(r"^[a-zA-Z0-9_]{3,16}$", username.strip()):
        return []
    if not item_id or not re.match(r"^[a-zA-Z0-9_]{2,64}$", item_id.strip()):
        return []
    username = username.strip()
    item_id = item_id.strip()

    commands_to_run = []
    if item_id.startswith("rank_"):
        rank_name = item_id.replace("rank_", "").lower()
        commands_to_run.append(f"lp user {username} parent add {rank_name}")
        commands_to_run.append(f"aura {rank_name} {username}")
        commands_to_run.append(f"store give {username} {item_id}")
        commands_to_run.append(f"broadcast §e⭐ §fLe joueur §b{username} §fa obtenu le grade §a{rank_name.upper()} §f!")
        commands_to_run.append(f"title {username} title {{\"text\":\"Grade {rank_name.upper()} Débloqué !\",\"color\":\"gold\",\"bold\":true}}")
    elif "key" in item_id:
        crate_type = "omega" if "omega" in item_id else "celestial"
        count = 12 if "omega" in item_id else 5
        commands_to_run.append(f"crate give {username} {crate_type} {count}")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"+{count} Clés {crate_type.capitalize()} reçues !\",\"color\":\"purple\"}}")
    elif item_id.startswith("pet_"):
        pet_type = item_id.replace("pet_", "").lower()
        commands_to_run.append(f"pet {pet_type} {username}")
        commands_to_run.append(f"broadcast §e🐾 §fLe joueur §b{username} §fa adopté le familier céleste §a{pet_type.upper()} §f!")
        commands_to_run.append(f"title {username} title {{\"text\":\"Familier {pet_type.upper()} Débloqué !\",\"color\":\"gold\",\"bold\":true}}")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"Compagnon invoqué avec succès !\",\"color\":\"yellow\"}}")
    elif "cosmetic" in item_id:
        cosmetic_type = "wings" if "wings" in item_id else "dragon"
        commands_to_run.append(f"cosmetics unlock {username} {cosmetic_type}")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"Cosmétique débloqué !\",\"color\":\"aqua\"}}")
    elif "booster" in item_id:
        commands_to_run.append(f"booster give {username} mining_2x 7200")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"Booster Minage x2 activé (2h) !\",\"color\":\"gold\"}}")
    elif "dungeon_pass" in item_id:
        commands_to_run.append(f"store give {username} dungeon_pass_bundle 3")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"+3 Pass Donjons Instanciés reçus !\",\"color\":\"aqua\"}}")
    elif item_id.startswith("aura_"):
        aura_name = item_id.replace("aura_", "").lower()
        commands_to_run.append(f"aura {aura_name} {username}")
        commands_to_run.append(f"store give {username} {item_id}")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"✦ Aura {aura_name.upper()} Activée !\",\"color\":\"light_purple\"}}")
    elif item_id.startswith("magot_") or item_id.startswith("lingot_") or item_id in ("bloc_aether", "minerai_aether", "aether_block", "aether_ore") or "bloc" in item_id or "furniture" in item_id:
        commands_to_run.append(f"store give {username} {item_id} 1")
        commands_to_run.append(f"broadcast §6💰 §b{username} §fa acquis le bloc/mobilier officiel §e{item_id.upper()} §f!")
        commands_to_run.append(f"title {username} actionbar {{\"text\":\"💰 Bloc/Mobilier reçu ! (Clic-Droit pour convertir ou poser)\",\"color\":\"gold\"}}")
    else:
        commands_to_run.append(f"store give {username} {item_id}")

    # Exécution RCON
    for cmd in commands_to_run:
        execute_server_command(cmd, target_player=username)

    return commands_to_run

def process_checkout(username: str, cart_items: List[Dict]) -> Dict:
    """Traite un panier complet d'achat en Euros (€)."""
    total = sum(item["price"] * item.get("quantity", 1) for item in cart_items)
    order_id = f"CMD-EUR-{str(uuid.uuid4())[:8].upper()}"

    all_commands = []
    for item in cart_items:
        cmds = execute_item_delivery(username, item["id"])
        all_commands.extend(cmds)

    # Persistance dans SQLite
    db_save_order(order_id, username, round(total, 2), cart_items, currency="EUR")

    # Enregistrement des objets/familiers débloqués dans le profil joueur
    user = db_get_user_by_username(username)
    if user:
        for item in cart_items:
            try:
                db_unlock_item_for_user(
                    user["id"],
                    item["id"],
                    item.get("category", "store"),
                    item.get("name", item["id"]),
                    icon=item.get("icon"),
                    image_url=item.get("image_url")
                )
                # Déblocage automatique de l'aura associée si achat d'un grade
                if item["id"].startswith("rank_"):
                    rank_key = item["id"].replace("rank_", "").lower()
                    db_unlock_item_for_user(
                        user["id"],
                        f"aura_{rank_key}",
                        "auras",
                        f"Aura {rank_key.upper()} Céleste",
                        icon="✨",
                        image_url=item.get("image_url")
                    )
            except Exception:
                pass

    order = {
        "order_id": order_id,
        "username": username,
        "total": round(total, 2),
        "currency": "EUR",
        "products": cart_items,
        "items_count": len(cart_items),
        "status": "LIVRÉ",
        "command_to_run": all_commands
    }
    ORDERS_HISTORY.insert(0, order)
    return order

def process_points_checkout(user_id: int, item_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Achat immédiat 1-clic avec les Pièces (⛃) du joueur.
    Vérifie le solde en Pièces, déduit atomiquement les pièces du compte Minecraft, livre l'item par RCON et archive la commande.
    """
    user = db_get_user_by_id(user_id)
    if not user:
        return False, "Utilisateur introuvable.", None

    item = get_item_by_id(item_id)
    if not item:
        return False, "Article introuvable dans la boutique.", None

    points_cost = item.get("price_points", 0)
    username = user["minecraft_username"]

    # Solde joueur en Pièces
    player = db_get_player_by_username(username)
    current_balance = player.get("balance", 0.0) if player else float(user.get("shop_points", 0))

    if current_balance < points_cost:
        missing = int(points_cost - current_balance)
        return False, f"Solde insuffisant : il vous manque {missing} ⛃ Pièces.", None

    # Déduction atomique des pièces
    success = db_spend_shop_points(user_id, points_cost)
    if not success:
        return False, "Erreur lors du débit des pièces.", None

    order_id = f"CMD-COIN-{str(uuid.uuid4())[:8].upper()}"

    # Livraison RCON en jeu
    commands_run = execute_item_delivery(username, item_id)
    execute_server_command(
        f"broadcast §6🎁 §b{username} §fa débloqué §e{item['name']} §favec §a{points_cost} ⛃ Pièces §f!"
    )

    # Enregistrement en base de données
    db_save_order(order_id, username, float(points_cost), [item], currency="PIECES")

    # Enregistrement du familier / cosmétique débloqué
    try:
        db_unlock_item_for_user(
            user_id,
            item["id"],
            item.get("category", "store"),
            item.get("name", item["id"]),
            icon=item.get("icon"),
            image_url=item.get("image_url")
        )
        if item["id"].startswith("rank_"):
            rank_key = item["id"].replace("rank_", "").lower()
            db_unlock_item_for_user(
                user_id,
                f"aura_{rank_key}",
                "auras",
                f"Aura {rank_key.upper()} Céleste",
                icon="✨",
                image_url=item.get("image_url")
            )
    except Exception:
        pass

    updated_player = db_get_player_by_username(username)
    new_balance = int(updated_player["balance"]) if updated_player else 0
    order = {
        "order_id": order_id,
        "username": username,
        "item_name": item["name"],
        "points_spent": points_cost,
        "new_balance": new_balance,
        "currency": "PIECES",
        "status": "LIVRÉ",
        "commands": commands_run
    }
    return True, f"Félicitations ! {item['name']} a été débloqué et livré sur votre personnage !", order
