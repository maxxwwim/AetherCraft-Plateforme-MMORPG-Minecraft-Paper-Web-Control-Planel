import os
import json
import zipfile
from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_SERVER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(BASE_SERVER_DIR, ".."))

PACK_DIR = os.path.join(BASE_SERVER_DIR, "AetherPack")
STATIC_DIR = os.path.join(ROOT_DIR, "web", "static")
ZIP_OUT = os.path.join(STATIC_DIR, "AetherPack.zip")

TEXTURES_DIR = os.path.join(PACK_DIR, "assets", "minecraft", "textures", "item")
MODELS_DIR = os.path.join(PACK_DIR, "assets", "minecraft", "models", "item")

os.makedirs(TEXTURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# 1. pack.mcmeta
pack_mcmeta = {
    "pack": {
        "pack_format": 34,
        "description": "§6AetherCraft §7— Textures Officielles des Objets de Boutique"
    }
}
with open(os.path.join(PACK_DIR, "pack.mcmeta"), "w", encoding="utf-8") as f:
    json.dump(pack_mcmeta, f, indent=2, ensure_ascii=False)

# 2. Génération de pack.png
pack_icon = Image.new("RGBA", (64, 64), (6, 7, 11, 255))
d = ImageDraw.Draw(pack_icon)
d.ellipse([4, 4, 60, 60], fill=(24, 18, 12, 255), outline=(245, 158, 11, 255), width=2)
d.polygon([(32, 10), (42, 28), (60, 32), (44, 44), (48, 60), (32, 50), (16, 60), (20, 44), (4, 32), (22, 28)], fill=(245, 158, 11, 255), outline=(254, 240, 138, 255))
pack_icon.save(os.path.join(PACK_DIR, "pack.png"))

# 3. Génération des Textures Pixel-Art 32x32
def make_vip_crown():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Couronne dorée
    d.polygon([(4, 22), (6, 12), (11, 17), (16, 8), (21, 17), (26, 12), (28, 22)], fill=(245, 158, 11, 255), outline=(254, 240, 138, 255))
    d.rectangle([4, 22, 28, 25], fill=(217, 119, 6, 255), outline=(254, 240, 138, 255))
    # Émeraudes
    d.ellipse([15, 7, 17, 9], fill=(16, 185, 129, 255))
    d.ellipse([5, 11, 7, 13], fill=(16, 185, 129, 255))
    d.ellipse([25, 11, 27, 13], fill=(16, 185, 129, 255))
    d.rectangle([10, 23, 12, 24], fill=(16, 185, 129, 255))
    d.rectangle([20, 23, 22, 24], fill=(16, 185, 129, 255))
    return im

def make_aether_seal():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Anneau céleste
    d.ellipse([3, 10, 29, 22], outline=(56, 189, 248, 200), width=2)
    # Étoile stellaire
    d.polygon([(16, 3), (20, 12), (29, 16), (20, 20), (16, 29), (12, 20), (3, 16), (12, 12)], fill=(2, 132, 199, 255), outline=(56, 189, 248, 255))
    # Orbe central
    d.ellipse([13, 13, 19, 19], fill=(224, 242, 254, 255), outline=(56, 189, 248, 255))
    return im

def make_titan_crest():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Bouclier de magma
    d.polygon([(16, 4), (27, 8), (25, 22), (16, 28), (7, 22), (5, 8)], fill=(69, 26, 3, 255), outline=(245, 158, 11, 255))
    # Flammes titaniques
    d.polygon([(16, 8), (22, 16), (19, 22), (16, 18), (13, 22), (10, 16)], fill=(234, 88, 12, 255), outline=(254, 240, 138, 255))
    d.ellipse([14, 13, 18, 17], fill=(254, 240, 138, 255))
    return im

def make_key_mystic():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Anneau haut améthyste
    d.ellipse([18, 4, 28, 14], fill=(88, 28, 135, 255), outline=(192, 132, 252, 255), width=2)
    d.ellipse([21, 7, 25, 11], fill=(0, 0, 0, 0))
    # Tige clé
    d.line([(20, 12), (7, 25)], fill=(192, 132, 252, 255), width=3)
    # Dents clé
    d.line([(7, 25), (11, 29)], fill=(192, 132, 252, 255), width=2)
    d.line([(10, 22), (13, 25)], fill=(192, 132, 252, 255), width=2)
    return im

def make_key_omega():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Anneau Omega
    d.ellipse([17, 3, 29, 15], fill=(159, 18, 57, 255), outline=(244, 63, 94, 255), width=2)
    d.ellipse([21, 7, 25, 11], fill=(56, 189, 248, 255))
    # Tige
    d.line([(19, 13), (6, 26)], fill=(244, 63, 94, 255), width=3)
    # Dents
    d.line([(6, 26), (10, 30)], fill=(255, 255, 255, 255), width=2)
    d.line([(9, 23), (13, 27)], fill=(255, 255, 255, 255), width=2)
    return im

def make_cosmetic_wings():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Aile Gauche
    d.polygon([(14, 18), (6, 8), (2, 12), (4, 18), (8, 23)], fill=(99, 102, 241, 255), outline=(165, 180, 252, 255))
    # Aile Droite
    d.polygon([(18, 18), (26, 8), (30, 12), (28, 18), (24, 23)], fill=(99, 102, 241, 255), outline=(165, 180, 252, 255))
    # Coeur d'étoile
    d.ellipse([14, 16, 18, 20], fill=(224, 242, 254, 255), outline=(56, 189, 248, 255))
    return im

def make_cosmetic_dragon():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Tête dragon
    d.polygon([(11, 10), (21, 10), (24, 18), (21, 26), (11, 26), (8, 18)], fill=(109, 40, 217, 255), outline=(196, 181, 253, 255))
    # Cornes d'or
    d.polygon([(11, 10), (7, 4), (10, 8)], fill=(245, 158, 11, 255))
    d.polygon([(21, 10), (25, 4), (22, 8)], fill=(245, 158, 11, 255))
    # Yeux dorés
    d.rectangle([11, 16, 13, 18], fill=(254, 240, 138, 255))
    d.rectangle([19, 16, 21, 18], fill=(254, 240, 138, 255))
    return im

def make_booster_mining():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Manche
    d.line([(8, 24), (24, 8)], fill=(120, 53, 15, 255), width=3)
    # Tête pioche dorée
    d.arc([14, 4, 28, 18], start=180, end=270, fill=(245, 158, 11, 255), width=4)
    d.polygon([(13, 13), (25, 5), (27, 7), (15, 15)], fill=(254, 240, 138, 255))
    # Badge x2
    d.ellipse([18, 18, 28, 28], fill=(6, 7, 11, 255), outline=(254, 240, 138, 255))
    return im

def make_chest_reward():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Coffre bois
    d.rectangle([5, 10, 27, 26], fill=(120, 53, 15, 255), outline=(245, 158, 11, 255), width=2)
    # Cerclages or
    d.line([(10, 10), (10, 26)], fill=(245, 158, 11, 255), width=2)
    d.line([(22, 10), (22, 26)], fill=(245, 158, 11, 255), width=2)
    # Serrure
    d.rectangle([14, 15, 18, 19], fill=(254, 240, 138, 255))
    return im

def make_pet_capybara():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Corps et tête zen marron
    d.rectangle([8, 14, 24, 26], fill=(120, 53, 15, 255), outline=(245, 158, 11, 255))
    d.rectangle([10, 18, 22, 24], fill=(69, 26, 3, 255))
    # Lotus rose sur la tête
    d.polygon([(16, 7), (13, 13), (19, 13)], fill=(244, 114, 182, 255), outline=(253, 242, 248, 255))
    d.ellipse([14, 10, 18, 14], fill=(254, 240, 138, 255))
    # Yeux zen fermés
    d.line([(10, 16), (13, 16)], fill=(254, 240, 138, 255), width=1)
    d.line([(19, 16), (22, 16)], fill=(254, 240, 138, 255), width=1)
    return im

def make_pet_fox():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Tête et oreilles renard
    d.polygon([(8, 14), (16, 26), (24, 14), (20, 6), (16, 12), (12, 6)], fill=(249, 115, 22, 255), outline=(254, 215, 170, 255))
    d.polygon([(11, 18), (16, 24), (21, 18)], fill=(255, 255, 255, 255))
    d.rectangle([15, 23, 17, 25], fill=(12, 10, 9, 255))
    # Yeux cyan astraux
    d.rectangle([11, 14, 13, 16], fill=(56, 189, 248, 255))
    d.rectangle([19, 14, 21, 16], fill=(56, 189, 248, 255))
    # 3 Queues de comètes en arrière-plan
    d.line([(6, 22), (2, 28)], fill=(56, 189, 248, 255), width=2)
    d.line([(26, 22), (30, 28)], fill=(56, 189, 248, 255), width=2)
    return im

def make_pet_goat():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Tête bélier blanche
    d.ellipse([10, 12, 22, 24], fill=(255, 255, 255, 255), outline=(226, 232, 240, 255))
    d.polygon([(13, 20), (19, 20), (16, 26)], fill=(241, 245, 249, 255))
    # Cornes spirales dorées
    d.arc([4, 6, 14, 18], start=90, end=270, fill=(245, 158, 11, 255), width=3)
    d.arc([18, 6, 28, 18], start=270, end=90, fill=(245, 158, 11, 255), width=3)
    # Nuages sous le bélier
    d.ellipse([6, 24, 26, 30], fill=(224, 242, 254, 255), outline=(56, 189, 248, 255))
    return im

def make_pet_phoenix():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Ailes de flammes
    d.polygon([(4, 10), (16, 18), (8, 26)], fill=(234, 88, 12, 255), outline=(254, 240, 138, 255))
    d.polygon([(28, 10), (16, 18), (24, 26)], fill=(234, 88, 12, 255), outline=(254, 240, 138, 255))
    # Corps & tête de feu
    d.ellipse([12, 10, 20, 22], fill=(245, 158, 11, 255), outline=(254, 240, 138, 255))
    d.polygon([(14, 16), (18, 16), (16, 22)], fill=(254, 240, 138, 255))
    d.ellipse([15, 14, 17, 16], fill=(255, 255, 255, 255))
    return im

# Sauvegarde de toutes les images
textures = {
    "rank_vip_crown.png": make_vip_crown(),
    "rank_aether_seal.png": make_aether_seal(),
    "rank_titan_crest.png": make_titan_crest(),
    "key_mystic.png": make_key_mystic(),
    "key_omega.png": make_key_omega(),
    "cosmetic_wings.png": make_cosmetic_wings(),
    "cosmetic_dragon.png": make_cosmetic_dragon(),
    "pet_capybara.png": make_pet_capybara(),
    "pet_fox.png": make_pet_fox(),
    "pet_goat.png": make_pet_goat(),
    "pet_phoenix.png": make_pet_phoenix(),
    "booster_mining.png": make_booster_mining(),
    "chest_reward.png": make_chest_reward()
}

for name, img in textures.items():
    img.save(os.path.join(TEXTURES_DIR, name))
    print(f"Texture créée : {name}")

# 4. Modèles JSON personnalisés
for name in textures.keys():
    base = name.replace(".png", "")
    model_json = {
        "parent": "item/generated",
        "textures": {
            "layer0": f"item/{base}"
        }
    }
    with open(os.path.join(MODELS_DIR, f"{base}.json"), "w") as f:
        json.dump(model_json, f, indent=2)

# 5. Overrides CustomModelData sur les items vanilla
overrides_map = {
    "golden_helmet.json": [
        {"predicate": {"custom_model_data": 1001}, "model": "item/rank_vip_crown"}
    ],
    "nether_star.json": [
        {"predicate": {"custom_model_data": 1002}, "model": "item/rank_aether_seal"}
    ],
    "magma_cream.json": [
        {"predicate": {"custom_model_data": 1003}, "model": "item/rank_titan_crest"}
    ],
    "tripwire_hook.json": [
        {"predicate": {"custom_model_data": 2001}, "model": "item/key_mystic"},
        {"predicate": {"custom_model_data": 2002}, "model": "item/key_omega"}
    ],
    "feather.json": [
        {"predicate": {"custom_model_data": 3001}, "model": "item/cosmetic_wings"}
    ],
    "heart_of_the_sea.json": [
        {"predicate": {"custom_model_data": 3002}, "model": "item/cosmetic_dragon"},
        {"predicate": {"custom_model_data": 3003}, "model": "item/pet_capybara"},
        {"predicate": {"custom_model_data": 3004}, "model": "item/pet_fox"},
        {"predicate": {"custom_model_data": 3005}, "model": "item/pet_goat"},
        {"predicate": {"custom_model_data": 3006}, "model": "item/pet_phoenix"}
    ],
    "golden_pickaxe.json": [
        {"predicate": {"custom_model_data": 4001}, "model": "item/booster_mining"}
    ]
}

for vanilla_file, overrides in overrides_map.items():
    vanilla_name = vanilla_file.replace(".json", "")
    full_model = {
        "parent": "item/generated",
        "textures": {
            "layer0": f"item/{vanilla_name}"
        },
        "overrides": overrides
    }
    with open(os.path.join(MODELS_DIR, vanilla_file), "w") as f:
        json.dump(full_model, f, indent=2)

# 6. Création de l'archive ZIP
print(f"Création de {ZIP_OUT}...")
with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(PACK_DIR):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, PACK_DIR)
            z.write(full, rel)

print("AetherPack.zip créé et hébergé sur le web !")
