import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_STATIC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "static"))

ITEMS_DIR = os.path.join(WEB_STATIC_DIR, "images", "items")
ORES_DIR = os.path.join(WEB_STATIC_DIR, "images", "ores")

os.makedirs(ITEMS_DIR, exist_ok=True)
os.makedirs(ORES_DIR, exist_ok=True)

def create_radial_glow(size, color, max_alpha=180):
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    cx, cy = size // 2, size // 2
    r_max = size // 2
    for r in range(r_max, 0, -2):
        alpha = int(max_alpha * (1.0 - (r / r_max))**1.8)
        c = (color[0], color[1], color[2], alpha)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return glow

def add_stars(draw, width, height, color, count=16):
    random.seed(42)
    for _ in range(count):
        sx = random.randint(30, width - 30)
        sy = random.randint(30, height - 30)
        s = random.randint(3, 8)
        draw.polygon([(sx, sy - s), (sx + s//3, sy - s//3), (sx + s, sy), (sx + s//3, sy + s//3),
                      (sx, sy + s), (sx - s//3, sy + s//3), (sx - s, sy), (sx - s//3, sy - s//3)],
                     fill=(255, 255, 255, random.randint(180, 255)))

# ========================================================
# 1. Rendu 3D Isométrique d'un Cube de Minerai Minecraft
# ========================================================
def render_3d_isometric_ore(gem_name, base_stone, gem_colors, glow_color, filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Glow d'ambiance
    glow = create_radial_glow(SIZE, glow_color, max_alpha=140)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)

    # Paramètres de projection isométrique
    cx = SIZE // 2
    cy = SIZE // 2 - 15
    L = 135   # Longueur d'un demi-côté
    H = 78    # Hauteur isométrique
    D = 150   # Hauteur verticale des faces latérales

    # Ombres portées au sol
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([cx - L - 20, cy + D - 20, cx + L + 20, cy + D + 80], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    im.paste(shadow, (0, 0), shadow)
    draw = ImageDraw.Draw(im)

    # 1. Face du Dessus (Top) - Éclairage zénithal direct (+35% luminosité)
    top_poly = [
        (cx, cy - H),
        (cx + L, cy),
        (cx, cy + H),
        (cx - L, cy)
    ]
    top_color = tuple(min(255, int(c * 1.35)) for c in base_stone)
    draw.polygon(top_poly, fill=top_color, outline=(255, 255, 255, 80))

    # 2. Face Gauche (Left) - Lumière diffuse intermédiaire (100% luminosité)
    left_poly = [
        (cx - L, cy),
        (cx, cy + H),
        (cx, cy + H + D),
        (cx - L, cy + D)
    ]
    left_color = base_stone
    draw.polygon(left_poly, fill=left_color, outline=(0, 0, 0, 80))

    # 3. Face Droite (Right) - Ombre portée propre (70% luminosité)
    right_poly = [
        (cx, cy + H),
        (cx + L, cy),
        (cx + L, cy + D),
        (cx, cy + H + D)
    ]
    right_color = tuple(int(c * 0.72) for c in base_stone)
    draw.polygon(right_poly, fill=right_color, outline=(0, 0, 0, 110))

    # Filons de minerais scintillants incrustés en 3D
    random.seed(hash(gem_name))
    
    # Gemmes sur Top
    for _ in range(8):
        u = random.uniform(0.15, 0.85)
        v = random.uniform(0.15, 0.85)
        # Interpolation bilinéaire sur top_poly
        gx = (1 - u) * (1 - v) * cx + u * (1 - v) * (cx + L) + u * v * cx + (1 - u) * v * (cx - L)
        gy = (1 - u) * (1 - v) * (cy - H) + u * (1 - v) * cy + u * v * (cy + H) + (1 - u) * v * cy
        gr = random.randint(8, 16)
        col = random.choice(gem_colors)
        draw.polygon([(gx, gy - gr//2), (gx + gr, gy), (gx, gy + gr//2), (gx - gr, gy)], fill=col, outline=(255, 255, 255, 180))

    # Gemmes sur Left Face
    for _ in range(9):
        lx = random.uniform(cx - L + 15, cx - 15)
        t = (lx - (cx - L)) / L
        base_y = cy + t * H
        ly = base_y + random.uniform(15, D - 15)
        gr = random.randint(8, 18)
        col = random.choice(gem_colors)
        draw.polygon([(lx, ly), (lx + gr, ly + gr//2), (lx + gr, ly + gr*1.2), (lx, ly + gr*0.7)], fill=col, outline=(255, 255, 255, 160))

    # Gemmes sur Right Face
    for _ in range(9):
        rx = random.uniform(cx + 15, cx + L - 15)
        t = (rx - cx) / L
        base_y = (cy + H) - t * H
        ry = base_y + random.uniform(15, D - 15)
        gr = random.randint(8, 18)
        col = tuple(int(c * 0.85) for c in random.choice(gem_colors))
        draw.polygon([(rx, ry), (rx + gr, ry - gr//2), (rx + gr, ry + gr*0.7), (rx, ry + gr*1.2)], fill=col, outline=(255, 255, 255, 140))

    # Éclats et étincelles
    add_stars(draw, SIZE, SIZE, glow_color, count=8)

    # Bords en biseau 3D brillant
    draw.line([(cx, cy - H), (cx, cy + H), (cx, cy + H + D)], fill=(255, 255, 255, 120), width=2)
    draw.line([(cx, cy + H), (cx - L, cy)], fill=(255, 255, 255, 90), width=2)
    draw.line([(cx, cy + H), (cx + L, cy)], fill=(0, 0, 0, 70), width=2)

    im.save(os.path.join(ORES_DIR, filename), "PNG")
    print(f"[+] Minerai 3D généré : {filename}")

# ========================================================
# 2. Rendu 3D Isométrique des Objets & Rangs de la Boutique
# ========================================================
def render_3d_champion_aura(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (192, 132, 252), max_alpha=180)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Sceau Arcanique 3D au Sol
    for r, col, w in [(180, (147, 51, 234, 180), 4), (150, (232, 121, 249, 220), 3), (120, (254, 240, 138, 240), 3), (90, (168, 85, 247, 160), 2)]:
        draw.ellipse([cx - r, cy + 40 - r//3, cx + r, cy + 40 + r//3], outline=col, width=w)

    # Rayons et Runes stellaires
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int(90 * math.cos(rad))
        y1 = cy + 40 + int(30 * math.sin(rad))
        x2 = cx + int(170 * math.cos(rad))
        y2 = cy + 40 + int(56 * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(254, 240, 138, 220), width=2)
        draw.ellipse([x2 - 4, y2 - 4, x2 + 4, y2 + 4], fill=(255, 255, 255))

    # Colonne de Lumière & Couronne Astrale Flottante
    beam = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    bd.polygon([(cx - 70, cy + 30), (cx + 70, cy + 30), (cx + 50, cy - 130), (cx - 50, cy - 130)], fill=(168, 85, 247, 70))
    beam = beam.filter(ImageFilter.GaussianBlur(10))
    im.paste(beam, (0, 0), beam)

    # Couronne de pure lumière au zénith
    draw = ImageDraw.Draw(im)
    cy_crown = cy - 80
    draw.ellipse([cx - 80, cy_crown - 20, cx + 80, cy_crown + 20], outline=(254, 240, 138), width=4)
    for dx, dy in [(-70, -25), (-35, -45), (0, -60), (35, -45), (70, -25)]:
        draw.polygon([(cx + dx - 6, cy_crown), (cx + dx, cy_crown + dy), (cx + dx + 6, cy_crown)], fill=(254, 240, 138), outline=(255, 255, 255))
        draw.ellipse([cx + dx - 4, cy_crown + dy - 4, cx + dx + 4, cy_crown + dy + 4], fill=(255, 255, 255))

    add_stars(draw, SIZE, SIZE, (254, 240, 138), count=18)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Aura Champion 3D générée : {filename}")

def render_3d_champion_crown(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (168, 85, 247), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2 + 10

    # Ombre
    sd = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(sd).ellipse([cx - 150, cy + 90, cx + 150, cy + 170], fill=(0, 0, 0, 180))
    sd = sd.filter(ImageFilter.GaussianBlur(16))
    im.paste(sd, (0, 0), sd)
    draw = ImageDraw.Draw(im)

    # Sceau stellaire 3D au sol
    for r in [170, 140, 110]:
        draw.ellipse([cx - r, cy + 60 - r//3, cx + r, cy + 60 + r//3], outline=(168, 85, 247, 140), width=3)

    # Couronne 3D Extrudée (Face Arrière -> Base -> Pointes)
    gold_top = (254, 240, 138)
    gold_mid = (245, 158, 11)
    gold_dark = (180, 83, 9)
    ruby = (244, 63, 94)
    sapphire = (56, 189, 248)

    # Base cylindrique or
    draw.ellipse([cx - 110, cy + 30, cx + 110, cy + 90], fill=gold_dark, outline=gold_top, width=3)
    draw.ellipse([cx - 110, cy + 10, cx + 110, cy + 70], fill=gold_mid, outline=gold_top, width=3)

    # 5 Pointes de la Couronne
    spikes = [
        (cx - 95, cy + 15, cx - 110, cy - 65, cx - 75, cy + 20),
        (cx - 55, cy + 22, cx - 60, cy - 100, cx - 25, cy + 28),
        (cx - 30, cy + 30, cx, cy - 135, cx + 30, cy + 30),
        (cx + 25, cy + 28, cx + 60, cy - 100, cx + 55, cy + 22),
        (cx + 75, cy + 20, cx + 110, cy - 65, cx + 95, cy + 15),
    ]

    for p in spikes:
        # Ombre latérale
        draw.polygon([(p[0]+4, p[1]), (p[2]+4, p[3]), (p[4]+4, p[5])], fill=gold_dark)
        # Face principale
        draw.polygon([(p[0], p[1]), (p[2], p[3]), (p[4], p[5])], fill=gold_mid, outline=gold_top, width=2)

    # Joyaux montés en 3D
    jewels = [
        (cx, cy - 135, ruby, 14),
        (cx - 60, cy - 100, sapphire, 11),
        (cx + 60, cy - 100, sapphire, 11),
        (cx - 110, cy - 65, ruby, 9),
        (cx + 110, cy - 65, ruby, 9),
        (cx, cy + 35, ruby, 12),
        (cx - 45, cy + 32, sapphire, 9),
        (cx + 45, cy + 32, sapphire, 9),
    ]
    for jx, jy, jcol, jr in jewels:
        draw.ellipse([jx - jr, jy - jr, jx + jr, jy + jr], fill=jcol, outline=(255, 255, 255, 220), width=2)
        draw.ellipse([jx - jr//2, jy - jr//2, jx, jy], fill=(255, 255, 255, 200))

    add_stars(draw, SIZE, SIZE, (254, 240, 138), count=12)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Item 3D généré : {filename}")

def render_3d_titan_crest(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (234, 88, 12), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Bouclier 3D Forgé
    shield_pts = [(cx, cy - 140), (cx + 120, cy - 80), (cx + 100, cy + 70), (cx, cy + 150), (cx - 100, cy + 70), (cx - 120, cy - 80)]
    draw.polygon([(x+8, y+8) for x, y in shield_pts], fill=(20, 10, 5, 200))
    draw.polygon(shield_pts, fill=(55, 20, 5), outline=(245, 158, 11), width=4)

    # Inlay lave
    inlay = [(cx, cy - 110), (cx + 90, cy - 60), (cx + 75, cy + 50), (cx, cy + 120), (cx - 75, cy + 50), (cx - 90, cy - 60)]
    draw.polygon(inlay, fill=(180, 50, 10), outline=(254, 240, 138), width=2)

    # Noyau Magma Pulsant
    draw.ellipse([cx - 45, cy - 25, cx + 45, cy + 65], fill=(234, 88, 12), outline=(254, 240, 138), width=3)
    draw.ellipse([cx - 25, cy - 5, cx + 25, cy + 45], fill=(254, 240, 138))

    add_stars(draw, SIZE, SIZE, (245, 158, 11), count=10)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Item 3D généré : {filename}")

def render_3d_aether_seal(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (56, 189, 248), max_alpha=170)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Anneaux célestes orbitaux en 3D
    draw.ellipse([cx - 150, cy - 50, cx + 150, cy + 50], outline=(56, 189, 248, 200), width=5)
    draw.ellipse([cx - 130, cy - 40, cx + 130, cy + 40], outline=(224, 242, 254, 230), width=3)

    # Cristal stellaire central à facettes
    crystal_pts = [(cx, cy - 130), (cx + 60, cy - 20), (cx, cy + 130), (cx - 60, cy - 20)]
    draw.polygon(crystal_pts, fill=(2, 132, 199), outline=(224, 242, 254), width=3)
    
    # Facettes éclairées
    draw.polygon([(cx, cy - 130), (cx + 60, cy - 20), (cx, cy + 130), (cx, cy - 20)], fill=(56, 189, 248), outline=(255, 255, 255))
    draw.polygon([(cx, cy - 130), (cx, cy - 20), (cx, cy + 130), (cx - 60, cy - 20)], fill=(3, 105, 161))

    add_stars(draw, SIZE, SIZE, (224, 242, 254), count=14)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Item 3D généré : {filename}")

def render_3d_vip_crown(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (16, 185, 129), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2 + 10

    # Couronne VIP or & émeraudes
    base_pts = [(cx - 100, cy + 40), (cx + 100, cy + 40), (cx + 80, cy + 80), (cx - 80, cy + 80)]
    draw.polygon(base_pts, fill=(217, 119, 6), outline=(254, 240, 138), width=3)

    spikes = [(cx - 95, cy + 40), (cx - 95, cy - 30), (cx - 50, cy + 10), (cx, cy - 70), (cx + 50, cy + 10), (cx + 95, cy - 30), (cx + 95, cy + 40)]
    draw.polygon(spikes, fill=(245, 158, 11), outline=(254, 240, 138), width=3)

    # Émeraudes taillées
    for ex, ey, er in [(cx, cy - 70, 12), (cx - 95, cy - 30, 9), (cx + 95, cy - 30, 9), (cx, cy + 60, 10), (cx - 50, cy + 60, 8), (cx + 50, cy + 60, 8)]:
        draw.polygon([(ex, ey - er), (ex + er, ey), (ex, ey + er), (ex - er, ey)], fill=(16, 185, 129), outline=(255, 255, 255), width=2)

    add_stars(draw, SIZE, SIZE, (52, 211, 153), count=10)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Item 3D généré : {filename}")

def render_3d_key(filename, color_theme, is_omega=False):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, color_theme, max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Rotation de 45 degrés pour effet 3D héroïque
    key_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    kd = ImageDraw.Draw(key_layer)

    # Anneau de la clé
    kd.ellipse([cx - 55, cy - 130, cx + 55, cy - 20], fill=color_theme, outline=(254, 240, 138), width=6)
    kd.ellipse([cx - 30, cy - 105, cx + 30, cy - 45], fill=(0, 0, 0, 0))

    # Tige de la clé
    kd.rectangle([cx - 10, cy - 30, cx + 10, cy + 130], fill=(245, 158, 11), outline=(254, 240, 138), width=3)

    # Dents de la clé
    kd.rectangle([cx + 10, cy + 60, cx + 45, cy + 85], fill=(245, 158, 11), outline=(254, 240, 138), width=3)
    kd.rectangle([cx + 10, cy + 95, cx + 55, cy + 120], fill=(245, 158, 11), outline=(254, 240, 138), width=3)

    # Cœur céleste de la clé
    kd.ellipse([cx - 15, cy - 85, cx + 15, cy - 55], fill=(255, 255, 255, 230))

    rotated_key = key_layer.rotate(-35, resample=Image.BICUBIC, center=(cx, cy))
    im.paste(rotated_key, (0, 0), rotated_key)

    add_stars(ImageDraw.Draw(im), SIZE, SIZE, color_theme, count=12)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Clé 3D générée : {filename}")

def render_3d_dungeon_pass(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (14, 165, 233), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Billet / Pass Isométrique 3D
    ticket = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(ticket)
    td.rounded_rectangle([cx - 130, cy - 80, cx + 130, cy + 80], radius=18, fill=(2, 132, 199), outline=(125, 211, 252), width=4)
    td.rounded_rectangle([cx - 110, cy - 65, cx + 110, cy + 65], radius=12, fill=(8, 47, 73), outline=(254, 240, 138), width=2)
    # Portail de Boss au centre
    td.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(14, 165, 233), outline=(254, 240, 138), width=3)
    td.polygon([(cx, cy - 25), (cx + 20, cy), (cx, cy + 25), (cx - 20, cy)], fill=(254, 240, 138))

    rot = ticket.rotate(-15, resample=Image.BICUBIC, center=(cx, cy))
    im.paste(rot, (0, 0), rot)

    add_stars(ImageDraw.Draw(im), SIZE, SIZE, (56, 189, 248), count=10)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Pass Donjon 3D généré : {filename}")

def render_3d_wings(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (99, 102, 241), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Ailes Quantiques Déployées
    for side in [-1, 1]:
        wing_pts = [
            (cx, cy + 40),
            (cx + side * 60, cy - 20),
            (cx + side * 150, cy - 90),
            (cx + side * 130, cy - 20),
            (cx + side * 160, cy + 30),
            (cx + side * 110, cy + 60),
            (cx + side * 130, cy + 100),
            (cx + side * 40, cy + 70)
        ]
        draw.polygon(wing_pts, fill=(79, 70, 229, 220), outline=(199, 210, 254), width=3)
        # Plumes intérieures luminescentes
        inner_pts = [
            (cx, cy + 40),
            (cx + side * 45, cy - 10),
            (cx + side * 115, cy - 65),
            (cx + side * 95, cy - 10),
            (cx + side * 120, cy + 25),
            (cx + side * 30, cy + 50)
        ]
        draw.polygon(inner_pts, fill=(165, 180, 252, 190), outline=(255, 255, 255), width=2)

    # Cœur d'énergie stellaire
    draw.ellipse([cx - 20, cy + 20, cx + 20, cy + 60], fill=(254, 240, 138), outline=(255, 255, 255), width=2)

    add_stars(draw, SIZE, SIZE, (165, 180, 252), count=12)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Ailes 3D générées : {filename}")

def render_3d_goat(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (129, 140, 248), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Nuages vaporeux au sol
    for ox, oy, r in [(-80, 100, 50), (-30, 90, 60), (30, 95, 55), (80, 100, 48)]:
        draw.ellipse([cx + ox - r, cy + oy - r//2, cx + ox + r, cy + oy + r//2], fill=(241, 245, 249, 220), outline=(199, 210, 254), width=2)

    # Tête du Bélier Céleste
    head_pts = [(cx - 45, cy - 40), (cx + 45, cy - 40), (cx + 35, cy + 45), (cx - 35, cy + 45)]
    draw.polygon(head_pts, fill=(248, 250, 252), outline=(148, 163, 184), width=3)
    # Museau
    draw.rounded_rectangle([cx - 25, cy + 10, cx + 25, cy + 45], radius=8, fill=(226, 232, 240), outline=(148, 163, 184), width=2)

    # Cornes en spirale dorée magistrales
    for side in [-1, 1]:
        horn_pts = [
            (cx + side * 30, cy - 35),
            (cx + side * 70, cy - 80),
            (cx + side * 110, cy - 70),
            (cx + side * 125, cy - 30),
            (cx + side * 105, cy + 10),
            (cx + side * 85, cy - 10),
            (cx + side * 95, cy - 45),
            (cx + side * 60, cy - 50)
        ]
        draw.polygon(horn_pts, fill=(245, 158, 11), outline=(254, 240, 138), width=3)

    # Yeux vifs
    draw.ellipse([cx - 28, cy - 15, cx - 18, cy - 5], fill=(15, 23, 42))
    draw.ellipse([cx + 18, cy - 15, cx + 28, cy - 5], fill=(15, 23, 42))

    add_stars(draw, SIZE, SIZE, (254, 240, 138), count=12)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Bélier 3D généré : {filename}")

def render_3d_booster(filename):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (245, 158, 11), max_alpha=160)
    im.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Pioche en or 3D & cristaux
    tool = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(tool)
    # Manche en bois forgé
    td.line([(cx - 70, cy + 100), (cx + 50, cy - 20)], fill=(120, 53, 15), width=14)
    td.line([(cx - 70, cy + 100), (cx + 50, cy - 20)], fill=(217, 119, 6), width=6)
    # Tête de pioche dorée
    td.polygon([(cx + 10, cy - 70), (cx + 80, cy - 40), (cx + 100, cy + 20), (cx + 85, cy + 10), (cx + 70, cy - 20), (cx + 20, cy - 40)], fill=(245, 158, 11), outline=(254, 240, 138), width=3)

    # Badge multiplicateur "x2"
    badge_poly = [(cx - 70, cy - 40), (cx - 10, cy - 40), (cx - 20, cy + 20), (cx - 80, cy + 20)]
    td.polygon(badge_poly, fill=(220, 38, 38), outline=(254, 240, 138), width=3)

    im.paste(tool, (0, 0), tool)
    add_stars(draw, SIZE, SIZE, (254, 240, 138), count=12)
    im.save(os.path.join(ITEMS_DIR, filename), "PNG")
    print(f"[+] Booster 3D généré : {filename}")

if __name__ == "__main__":
    print("--- Génération des 8 Minerais 3D du Marché ---")
    render_3d_isometric_ore("coal", (45, 45, 50), [(24, 24, 27), (39, 39, 42), (9, 9, 11)], (100, 100, 100), "ore_coal.png")
    render_3d_isometric_ore("copper", (55, 55, 60), [(234, 88, 12), (249, 115, 22), (45, 212, 191)], (249, 115, 22), "ore_copper.png")
    render_3d_isometric_ore("iron", (60, 60, 65), [(214, 211, 209), (231, 229, 228), (168, 162, 158)], (214, 211, 209), "ore_iron.png")
    render_3d_isometric_ore("gold", (50, 48, 45), [(245, 158, 11), (251, 191, 36), (254, 240, 138)], (245, 158, 11), "ore_gold.png")
    render_3d_isometric_ore("lapis", (45, 48, 55), [(29, 78, 216), (37, 99, 235), (96, 165, 250)], (37, 99, 235), "ore_lapis.png")
    render_3d_isometric_ore("diamond", (45, 52, 58), [(56, 189, 248), (14, 165, 233), (186, 230, 253)], (56, 189, 248), "ore_diamond.png")
    render_3d_isometric_ore("netherite", (30, 25, 28), [(68, 64, 60), (41, 37, 36), (120, 113, 108)], (168, 85, 247), "ore_netherite.png")
    render_3d_isometric_ore("aetherite", (35, 30, 50), [(192, 132, 252), (168, 85, 247), (232, 121, 249)], (216, 180, 254), "ore_aetherite.png")

    print("\n--- Génération des Objets et Rangs 3D de la Boutique ---")
    render_3d_champion_crown("rank_champion.png")
    render_3d_champion_aura("aura_champion.png")
    render_3d_titan_crest("rank_titan.png")
    render_3d_aether_seal("rank_aether.png")
    render_3d_vip_crown("rank_vip.png")
    render_3d_key("key_omega.png", (225, 29, 72), is_omega=True)
    render_3d_key("key_mystic.png", (147, 51, 234), is_omega=False)
    render_3d_dungeon_pass("dungeon_pass.png")
    render_3d_wings("cosmetic_wings.png")
    render_3d_goat("pet_goat.png")
    render_3d_booster("booster_mining.png")
    print("\n[V] Tous les visuels 3D ont été générés avec succès !")
