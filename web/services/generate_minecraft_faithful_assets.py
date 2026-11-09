import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_STATIC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "static"))

EXTRACTED_DIR = os.path.join(WEB_STATIC_DIR, "images", "extracted_textures")
ITEMS_DIR = os.path.join(WEB_STATIC_DIR, "images", "items")
ORES_DIR = os.path.join(WEB_STATIC_DIR, "images", "ores")

os.makedirs(ITEMS_DIR, exist_ok=True)
os.makedirs(ORES_DIR, exist_ok=True)

def create_radial_glow(size, color, max_alpha=160, power=2.0):
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    cx, cy = size // 2, size // 2
    r_max = size // 2
    for r in range(r_max, 0, -3):
        alpha = int(max_alpha * (1.0 - (r / r_max))**power)
        c = (color[0], color[1], color[2], alpha)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return glow

def add_pixel_sparkles(im, color=(255, 255, 255), count=14):
    d = ImageDraw.Draw(im)
    w, h = im.size
    random.seed(1337)
    for _ in range(count):
        sx = random.randint(50, w - 50)
        sy = random.randint(50, h - 50)
        sz = random.choice([2, 4, 6])
        # Cross pixel star
        alpha = random.randint(180, 255)
        c = (color[0], color[1], color[2], alpha)
        d.rectangle([sx, sy - sz, sx + 2, sy + sz + 2], fill=c)
        d.rectangle([sx - sz, sy, sx + sz + 2, sy + 2], fill=c)

# ========================================================
# 1. RENDU 3D ISOMÉTRIQUE D'UN BLOC MINECRAFT RÉEL
# ========================================================
def render_faithful_ore_block(top_tex_name, side_tex_name, item_tex_name, glow_color, output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Glow d'ambiance
    glow = create_radial_glow(SIZE, glow_color, max_alpha=140)
    im.paste(glow, (0, 0), glow)

    # Charger textures
    top_path = os.path.join(EXTRACTED_DIR, top_tex_name)
    side_path = os.path.join(EXTRACTED_DIR, side_tex_name)
    
    top_tex = Image.open(top_path).convert("RGBA") if os.path.exists(top_path) else Image.new("RGBA", (16, 16), (120, 120, 120, 255))
    side_tex = Image.open(side_path).convert("RGBA") if os.path.exists(side_path) else top_tex

    cx = 256
    cy = 135
    dx = 9.2
    dy = 5.3
    dh = 146

    draw = ImageDraw.Draw(im)

    # Ombre au sol
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([cx - 160, cy + dh - 10, cx + 160, cy + dh + 100], fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    im.paste(shadow, (0, 0), shadow)
    draw = ImageDraw.Draw(im)

    def pt_top(u, v):
        return (cx + (u - v) * dx, cy + (u + v) * dy)

    # 1. Face Supérieure (Top)
    for v in range(16):
        for u in range(16):
            r, g, b, a = top_tex.getpixel((u, v))
            c = (min(255, int(r * 1.25)), min(255, int(g * 1.25)), min(255, int(b * 1.25)), a)
            poly = [pt_top(u, v), pt_top(u+1, v), pt_top(u+1, v+1), pt_top(u, v+1)]
            draw.polygon(poly, fill=c)

    # 2. Face Gauche (Left)
    for h in range(16):
        for u in range(16):
            r, g, b, a = side_tex.getpixel((u, h))
            c = (r, g, b, a)
            base_top_x, base_top_y = pt_top(u, 16)
            next_top_x, next_top_y = pt_top(u+1, 16)
            poly = [
                (base_top_x, base_top_y + h * (dh / 16.0)),
                (next_top_x, next_top_y + h * (dh / 16.0)),
                (next_top_x, next_top_y + (h+1) * (dh / 16.0)),
                (base_top_x, base_top_y + (h+1) * (dh / 16.0))
            ]
            draw.polygon(poly, fill=c)

    # 3. Face Droite (Right)
    for h in range(16):
        for w in range(16):
            r, g, b, a = side_tex.getpixel((w, h))
            c = (int(r * 0.72), int(g * 0.72), int(b * 0.72), a)
            base_top_x, base_top_y = pt_top(16, 16 - w)
            next_top_x, next_top_y = pt_top(16, 16 - (w+1))
            poly = [
                (base_top_x, base_top_y + h * (dh / 16.0)),
                (next_top_x, next_top_y + h * (dh / 16.0)),
                (next_top_x, next_top_y + (h+1) * (dh / 16.0)),
                (base_top_x, base_top_y + (h+1) * (dh / 16.0))
            ]
            draw.polygon(poly, fill=c)

    # Incrustation du minerai brut / lingot en bas à droite (comme sur les affiches officielles Minecraft)
    if item_tex_name:
        item_path = os.path.join(EXTRACTED_DIR, item_tex_name)
        if os.path.exists(item_path):
            item_raw = Image.open(item_path).convert("RGBA")
            item_scaled = item_raw.resize((150, 150), Image.NEAREST)
            # Item shadow
            item_shadow = Image.new("RGBA", (150, 150), (0, 0, 0, 160))
            item_shadow.putalpha(item_scaled.split()[3])
            im.paste(item_shadow, (320, 275), item_shadow)
            im.paste(item_scaled, (315, 270), item_scaled)

    add_pixel_sparkles(im, color=glow_color, count=12)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Bloc Minerai Minecraft Réel : {os.path.basename(output_path)}")

# ========================================================
# 2. RENDU VOXEL DES ANIMAUX CÉLESTES MINECRAFT RÉELS
# ========================================================

def draw_voxel_box(draw, cx, cy, w_vox, h_vox, d_vox, vox_sz, top_col, left_col, right_col):
    dx = vox_sz * 0.866
    dy = vox_sz * 0.5
    dh = vox_sz * 1.0

    def pt_t(u, v):
        return (cx + (u - v) * dx, cy + (u + v) * dy)

    # Top
    p1 = pt_t(0, 0)
    p2 = pt_t(w_vox, 0)
    p3 = pt_t(w_vox, d_vox)
    p4 = pt_t(0, d_vox)
    draw.polygon([p1, p2, p3, p4], fill=top_col, outline=(top_col[0]//2, top_col[1]//2, top_col[2]//2, 100))

    # Left
    draw.polygon([
        p4,
        p3,
        (p3[0], p3[1] + h_vox * dh),
        (p4[0], p4[1] + h_vox * dh)
    ], fill=left_col, outline=(left_col[0]//2, left_col[1]//2, left_col[2]//2, 100))

    # Right
    draw.polygon([
        p3,
        p2,
        (p2[0], p2[1] + h_vox * dh),
        (p3[0], p3[1] + h_vox * dh)
    ], fill=right_col, outline=(right_col[0]//2, right_col[1]//2, right_col[2]//2, 100))

def render_minecraft_dragon(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (168, 85, 247), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 170

    # Nuque / Cou
    draw_voxel_box(draw, cx - 10, cy - 30, 8, 12, 10, 8, (25, 25, 28), (18, 18, 20), (12, 12, 15))
    
    # Corne Gauche & Droite
    draw_voxel_box(draw, cx - 35, cy - 40, 2, 8, 2, 7, (45, 45, 50), (35, 35, 40), (25, 25, 30))
    draw_voxel_box(draw, cx + 20, cy - 50, 2, 8, 2, 7, (45, 45, 50), (35, 35, 40), (25, 25, 30))

    # Tête Principale (Ender Dragon Voxel)
    draw_voxel_box(draw, cx, cy, 12, 10, 14, 9, (32, 32, 36), (22, 22, 25), (15, 15, 18))

    # Museau / Mâchoire Supérieure
    draw_voxel_box(draw, cx - 35, cy + 45, 10, 6, 8, 8, (28, 28, 32), (20, 20, 24), (14, 14, 16))

    # Mâchoire Inférieure
    draw_voxel_box(draw, cx - 35, cy + 85, 9, 3, 7, 8, (22, 22, 25), (16, 16, 18), (10, 10, 12))

    # Yeux Violets Incandescents (Texture Minecraft Ender Dragon)
    eye_col = (216, 40, 248)
    eye_glow = (255, 100, 255)
    # Oeil gauche
    draw.polygon([(cx - 20, cy + 48), (cx - 8, cy + 42), (cx - 8, cy + 56), (cx - 20, cy + 62)], fill=eye_col)
    draw.rectangle([cx - 16, cy + 48, cx - 10, cy + 54], fill=eye_glow)
    # Oeil droit
    draw.polygon([(cx + 38, cy + 22), (cx + 50, cy + 16), (cx + 50, cy + 30), (cx + 38, cy + 36)], fill=eye_col)
    draw.rectangle([cx + 42, cy + 22, cx + 48, cy + 28], fill=eye_glow)

    # Épines dorsales
    draw_voxel_box(draw, cx - 2, cy - 25, 1, 3, 2, 7, (180, 50, 220), (140, 30, 180), (100, 20, 140))
    draw_voxel_box(draw, cx - 2, cy + 15, 1, 3, 2, 7, (180, 50, 220), (140, 30, 180), (100, 20, 140))

    add_pixel_sparkles(im, (230, 100, 255), 18)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Voxel Minecraft : {os.path.basename(output_path)}")

def render_minecraft_fox(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (249, 115, 22), max_alpha=150)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 180

    # Corps (Roux Fox)
    draw_voxel_box(draw, cx - 20, cy + 10, 8, 9, 12, 9, (220, 100, 25), (185, 75, 15), (140, 55, 10))
    
    # Queue avec pointe blanche
    draw_voxel_box(draw, cx + 50, cy - 10, 6, 7, 10, 8, (220, 100, 25), (185, 75, 15), (140, 55, 10))
    draw_voxel_box(draw, cx + 90, cy - 35, 4, 5, 6, 8, (250, 250, 250), (220, 220, 220), (190, 190, 190))

    # Tête (Renard Minecraft)
    draw_voxel_box(draw, cx - 30, cy - 30, 10, 8, 10, 10, (235, 115, 30), (195, 85, 20), (150, 60, 12))

    # Oreille gauche (Noire & Blanche)
    draw_voxel_box(draw, cx - 65, cy - 70, 3, 5, 2, 8, (30, 30, 30), (20, 20, 20), (15, 15, 15))
    draw_voxel_box(draw, cx - 60, cy - 65, 2, 3, 1, 7, (245, 245, 245), (220, 220, 220), (190, 190, 190))

    # Oreille droite
    draw_voxel_box(draw, cx + 5, cy - 85, 3, 5, 2, 8, (30, 30, 30), (20, 20, 20), (15, 15, 15))
    draw_voxel_box(draw, cx + 10, cy - 80, 2, 3, 1, 7, (245, 245, 245), (220, 220, 220), (190, 190, 190))

    # Museau avec truffe noire
    draw_voxel_box(draw, cx - 75, cy + 20, 5, 4, 4, 9, (245, 245, 245), (220, 220, 220), (180, 180, 180))
    draw_voxel_box(draw, cx - 85, cy + 30, 2, 2, 2, 9, (20, 20, 20), (15, 15, 15), (10, 10, 10))

    # Yeux du Renard (Style Minecraft avec pupille noire et blanc)
    draw.rectangle([cx - 48, cy + 10, cx - 40, cy + 22], fill=(20, 20, 20))
    draw.rectangle([cx - 48, cy + 10, cx - 44, cy + 16], fill=(255, 255, 255))
    draw.rectangle([cx - 10, cy - 5, cx - 2, cy + 7], fill=(20, 20, 20))
    draw.rectangle([cx - 10, cy - 5, cx - 6, cy + 1], fill=(255, 255, 255))

    add_pixel_sparkles(im, (255, 190, 120), 16)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Voxel Minecraft : {os.path.basename(output_path)}")

def render_minecraft_goat(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (217, 119, 6), max_alpha=140)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 175

    # Corps (Laine blanche / crème épaisse)
    draw_voxel_box(draw, cx - 15, cy + 10, 9, 10, 13, 9, (240, 238, 230), (210, 206, 195), (175, 170, 160))

    # Tête de Chèvre Minecraft
    draw_voxel_box(draw, cx - 35, cy - 35, 8, 9, 8, 9, (230, 228, 220), (200, 195, 185), (165, 160, 150))

    # Corne Gauche (Grise recourbée)
    draw_voxel_box(draw, cx - 60, cy - 80, 2, 7, 2, 7, (130, 125, 120), (100, 95, 90), (70, 65, 60))
    # Corne Droite
    draw_voxel_box(draw, cx - 5, cy - 90, 2, 7, 2, 7, (130, 125, 120), (100, 95, 90), (70, 65, 60))

    # Museau & Barbeille (Beard)
    draw_voxel_box(draw, cx - 65, cy + 15, 6, 5, 5, 8, (215, 210, 200), (185, 180, 170), (150, 145, 135))
    draw_voxel_box(draw, cx - 60, cy + 45, 3, 4, 3, 7, (240, 235, 225), (205, 200, 190), (160, 155, 145))

    # Yeux horizontaux de chèvre
    draw.rectangle([cx - 45, cy - 5, cx - 33, cy + 3], fill=(50, 45, 40))
    draw.rectangle([cx - 41, cy - 5, cx - 37, cy + 3], fill=(15, 15, 15))

    add_pixel_sparkles(im, (255, 220, 150), 14)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Voxel Minecraft : {os.path.basename(output_path)}")

def render_minecraft_capybara(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (16, 185, 129), max_alpha=150)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 185

    # Corps Voxel Capybara Zen (Pelage Brun Doré)
    draw_voxel_box(draw, cx - 10, cy + 15, 11, 10, 14, 9, (160, 105, 55), (130, 80, 40), (100, 60, 25))

    # Tête carrée typique du Capybara
    draw_voxel_box(draw, cx - 45, cy - 25, 9, 8, 9, 9, (170, 115, 60), (140, 90, 45), (105, 65, 30))

    # Oreilles rondes
    draw_voxel_box(draw, cx - 65, cy - 50, 2, 2, 2, 7, (90, 55, 25), (70, 40, 18), (50, 28, 12))
    draw_voxel_box(draw, cx - 15, cy - 60, 2, 2, 2, 7, (90, 55, 25), (70, 40, 18), (50, 28, 12))

    # Museau allongé flegmatique
    draw_voxel_box(draw, cx - 80, cy + 15, 6, 6, 6, 8, (140, 90, 45), (110, 70, 32), (80, 50, 20))
    # Narines
    draw.rectangle([cx - 72, cy + 30, cx - 68, cy + 36], fill=(30, 20, 10))
    draw.rectangle([cx - 62, cy + 25, cx - 58, cy + 31], fill=(30, 20, 10))

    # Yeux mi-clos zen
    draw.rectangle([cx - 50, cy - 2, cx - 38, cy + 3], fill=(20, 15, 10))

    # Trèfle / Mandarine Céleste posée sur sa tête (Mème Capybara zen)
    draw_voxel_box(draw, cx - 35, cy - 55, 4, 3, 4, 7, (245, 158, 11), (217, 119, 6), (180, 83, 9))
    draw_voxel_box(draw, cx - 33, cy - 65, 1, 2, 1, 6, (34, 197, 94), (22, 163, 74), (16, 120, 50))

    add_pixel_sparkles(im, (160, 240, 200), 16)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Voxel Minecraft : {os.path.basename(output_path)}")

def render_minecraft_phoenix(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (239, 68, 68), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 175

    # Corps de Flammes (Or, Orange, Carmin)
    draw_voxel_box(draw, cx - 10, cy + 15, 8, 11, 10, 9, (245, 158, 11), (217, 119, 6), (185, 28, 28))

    # Ailes Voxel déployées (Plumage de feu)
    draw_voxel_box(draw, cx - 70, cy + 5, 4, 12, 14, 8, (251, 191, 36), (239, 68, 68), (185, 28, 28))
    draw_voxel_box(draw, cx + 45, cy - 25, 4, 12, 14, 8, (251, 191, 36), (239, 68, 68), (185, 28, 28))

    # Tête d'Oiseau de Feu
    draw_voxel_box(draw, cx - 35, cy - 35, 8, 8, 8, 9, (254, 240, 138), (245, 158, 11), (220, 38, 38))

    # Crête de flammes au sommet
    draw_voxel_box(draw, cx - 30, cy - 65, 3, 5, 3, 8, (255, 255, 150), (245, 158, 11), (220, 38, 38))
    draw_voxel_box(draw, cx - 15, cy - 75, 2, 4, 2, 7, (255, 230, 100), (239, 68, 68), (185, 28, 28))

    # Bec doré
    draw_voxel_box(draw, cx - 65, cy + 5, 4, 3, 4, 8, (253, 224, 71), (234, 179, 8), (180, 83, 9))

    # Yeux Flamboyants
    draw.rectangle([cx - 46, cy - 10, cx - 38, cy - 2], fill=(255, 255, 255))
    draw.rectangle([cx - 44, cy - 8, cx - 40, cy - 4], fill=(220, 38, 38))

    add_pixel_sparkles(im, (255, 200, 100), 20)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Voxel Minecraft : {os.path.basename(output_path)}")

# ========================================================
# 3. RENDU DES OBJETS BOUTIQUE AVEC ITEMS MINECRAFT RÉELS
# ========================================================

def render_real_minecraft_item(src_filename, glow_color, output_path, badge_item=None, is_enchanted=True):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # 1. Glow céleste
    glow = create_radial_glow(SIZE, glow_color, max_alpha=160, power=2.2)
    im.paste(glow, (0, 0), glow)

    # 2. Ombre portée au sol
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([140, 380, 372, 440], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    im.paste(shadow, (0, 0), shadow)

    # 3. Charger l'item Minecraft 16x16 réel et l'agrandir en NEAREST
    src_path = os.path.join(EXTRACTED_DIR, src_filename)
    if not os.path.exists(src_path):
        # Fallback si fichier pas dans extracted
        src_path = os.path.join(ITEMS_DIR, src_filename)

    if os.path.exists(src_path):
        item_tex = Image.open(src_path).convert("RGBA")
        TARGET_SZ = 280
        item_scaled = item_tex.resize((TARGET_SZ, TARGET_SZ), Image.NEAREST)

        # Effet d'enchantement Minecraft (shimmer améthyste/rose/cyan)
        if is_enchanted:
            glint = Image.new("RGBA", (TARGET_SZ, TARGET_SZ), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glint)
            for i in range(-TARGET_SZ, TARGET_SZ * 2, 24):
                gd.line([(i, 0), (i + TARGET_SZ, TARGET_SZ)], fill=(180, 120, 255, 60), width=10)
            
            # Masquer le glint avec le canal alpha de l'item
            glint.putalpha(ImageEnhance.Brightness(item_scaled.split()[3]).enhance(0.45))
            item_scaled = Image.alpha_composite(item_scaled, glint)

        offset_x = (SIZE - TARGET_SZ) // 2
        offset_y = (SIZE - TARGET_SZ) // 2 - 15
        im.paste(item_scaled, (offset_x, offset_y), item_scaled)

    # Si badge / sous-élément à intégrer
    if badge_item:
        b_path = os.path.join(EXTRACTED_DIR, badge_item)
        if os.path.exists(b_path):
            b_tex = Image.open(b_path).convert("RGBA")
            b_scaled = b_tex.resize((100, 100), Image.NEAREST)
            im.paste(b_scaled, (320, 290), b_scaled)

    add_pixel_sparkles(im, glow_color, count=14)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Item Réel Minecraft : {os.path.basename(output_path)}")

# ========================================================
# 4. EXÉCUTION DU PIPELINE COMPLET
# ========================================================
def generate_all_assets():
    print("=== DÉBUT DE LA GÉNÉRATION DES ASSETS MINECRAFT RÉELS ===")

    # 1. Animaux & Familiers Voxel Célestes
    render_minecraft_dragon(os.path.join(ITEMS_DIR, "pet_dragon.png"))
    render_minecraft_fox(os.path.join(ITEMS_DIR, "pet_fox.png"))
    render_minecraft_goat(os.path.join(ITEMS_DIR, "pet_goat.png"))
    render_minecraft_capybara(os.path.join(ITEMS_DIR, "pet_capybara.png"))
    render_minecraft_phoenix(os.path.join(ITEMS_DIR, "pet_phoenix.png"))

    # 2. Cubes de Minerais Minecraft du Marché (3D Isométrie Voxel)
    ores_specs = [
        ("coal_ore.png", "coal_ore.png", "coal.png", (100, 100, 110), "ore_coal.png"),
        ("copper_ore.png", "deepslate_copper_ore.png", "raw_copper.png", (234, 88, 12), "ore_copper.png"),
        ("iron_ore.png", "deepslate_iron_ore.png", "raw_iron.png", (217, 119, 6), "ore_iron.png"),
        ("gold_ore.png", "deepslate_gold_ore.png", "raw_gold.png", (245, 158, 11), "ore_gold.png"),
        ("lapis_ore.png", "deepslate_lapis_ore.png", "lapis_lazuli.png", (37, 99, 235), "ore_lapis.png"),
        ("diamond_ore.png", "deepslate_diamond_ore.png", "diamond.png", (6, 182, 212), "ore_diamond.png"),
        ("ancient_debris_top.png", "ancient_debris_side.png", "netherite_ingot.png", (107, 70, 70), "ore_netherite.png"),
        ("crying_obsidian.png", "crying_obsidian.png", "nether_star.png", (168, 85, 247), "ore_aetherite.png")
    ]
    for top_t, side_t, item_t, col, fn in ores_specs:
        render_faithful_ore_block(top_t, side_t, item_t, col, os.path.join(ORES_DIR, fn))

    # 3. Les 15 Articles Boutique Réels
    # Grades
    render_real_minecraft_item("golden_helmet.png", (245, 158, 11), os.path.join(ITEMS_DIR, "rank_vip.png"))
    render_real_minecraft_item("diamond_helmet.png", (6, 182, 212), os.path.join(ITEMS_DIR, "rank_aether.png"))
    render_real_minecraft_item("netherite_helmet.png", (168, 85, 247), os.path.join(ITEMS_DIR, "rank_titan.png"))
    render_real_minecraft_item("netherite_chestplate.png", (234, 179, 8), os.path.join(ITEMS_DIR, "rank_champion.png"), badge_item="nether_star.png")

    # Clés & Coffres
    render_real_minecraft_item("tripwire_hook.png", (14, 165, 233), os.path.join(ITEMS_DIR, "key_mystic.png"))
    render_real_minecraft_item("trial_key.png", (245, 158, 11), os.path.join(ITEMS_DIR, "key_omega.png"))

    # Cosmétiques & Auras
    render_real_minecraft_item("elytra.png", (168, 85, 247), os.path.join(ITEMS_DIR, "cosmetic_wings.png"))
    render_real_minecraft_item("beacon.png", (217, 70, 239), os.path.join(ITEMS_DIR, "aura_champion.png"), badge_item="nether_star.png")

    # Boosters & Donjons
    render_real_minecraft_item("netherite_pickaxe.png", (234, 179, 8), os.path.join(ITEMS_DIR, "booster_mining.png"))
    render_real_minecraft_item("map.png", (245, 158, 11), os.path.join(ITEMS_DIR, "dungeon_pass.png"))

    print("=== GÉNÉRATION COMPLÈTE TERMINÉE AVEC SUCCÈS ===")

if __name__ == "__main__":
    generate_all_assets()
