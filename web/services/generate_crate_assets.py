import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "static", "images", "items"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def add_pixel_sparkles(im, color=(255, 255, 255), count=16):
    d = ImageDraw.Draw(im)
    w, h = im.size
    random.seed(42)
    for _ in range(count):
        sx = random.randint(40, w - 40)
        sy = random.randint(40, h - 40)
        sz = random.choice([2, 4, 6])
        alpha = random.randint(180, 255)
        c = (color[0], color[1], color[2], alpha)
        d.rectangle([sx, sy - sz, sx + 2, sy + sz + 2], fill=c)
        d.rectangle([sx - sz, sy, sx + sz + 2, sy + 2], fill=c)

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

# ========================================================
# 1. RENDU DE LA NANO BANANA (BANANE QUANTIQUE D'OR VOXEL)
# ========================================================
def render_nano_banana(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (251, 191, 36), max_alpha=170, power=2.0)
    im.paste(glow, (0, 0), glow)

    # Ombre portée
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([140, 390, 372, 450], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    im.paste(shadow, (0, 0), shadow)

    draw = ImageDraw.Draw(im)

    # Courbure en voxel de la banane
    # Décomposition en 7 segments de cubes formant la banane stylisée Minecraft
    segments = [
        # (offset_x, offset_y, w, h, d, color_top, color_left, color_right)
        # Tige verte
        (190, 110, 3, 5, 3, (74, 222, 128), (34, 197, 94), (21, 128, 61)),
        # Haut de banane
        (205, 145, 6, 6, 6, (254, 240, 138), (250, 204, 21), (202, 138, 4)),
        # Tranche médiane haute
        (225, 185, 8, 8, 8, (255, 248, 160), (251, 191, 36), (217, 119, 6)),
        # Cœur / Centre courbé
        (240, 230, 9, 9, 9, (255, 255, 180), (252, 211, 77), (217, 119, 6)),
        # Tranche médiane basse
        (230, 280, 8, 8, 8, (255, 248, 160), (251, 191, 36), (217, 119, 6)),
        # Bas courbé vers l'intérieur
        (205, 325, 6, 7, 6, (254, 240, 138), (250, 204, 21), (202, 138, 4)),
        # Bout noir/brun
        (185, 360, 4, 4, 4, (120, 53, 15), (69, 26, 3), (35, 12, 1))
    ]

    for sx, sy, w, h, d, c_t, c_l, c_r in segments:
        draw_voxel_box(draw, sx, sy, w, h, d, 9, c_t, c_l, c_r)

    # Inscription Nano Circuit Cyan néon futuriste sur la banane
    cyan_glow = (56, 189, 248)
    draw.line([(240, 235), (265, 250), (265, 275), (290, 290)], fill=cyan_glow, width=3)
    draw.rectangle([238, 233, 244, 239], fill=(255, 255, 255))
    draw.rectangle([288, 288, 294, 294], fill=(255, 255, 255))

    add_pixel_sparkles(im, (255, 230, 120), count=18)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Nano Banana Voxel : {os.path.basename(output_path)}")

# ========================================================
# 2. RENDU DES COFFRES 3D ISOMÉTRIQUES (CÉLESTE & OMÉGA)
# ========================================================
def render_chest_celestial(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (168, 85, 247), max_alpha=160, power=2.0)
    im.paste(glow, (0, 0), glow)

    # Ombre
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([110, 370, 402, 450], fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    im.paste(shadow, (0, 0), shadow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 150

    # Base du Coffre de l'Ender (Obsidienne & Teal)
    draw_voxel_box(draw, cx, cy + 60, 14, 11, 14, 11, (30, 25, 45), (18, 14, 28), (12, 9, 20))

    # Bordures runiques cyan
    draw_voxel_box(draw, cx - 2, cy + 58, 14, 2, 14, 11, (56, 189, 248), (14, 165, 233), (2, 132, 199))

    # Couvercle entrouvert avec rayons d'énergie
    draw_voxel_box(draw, cx - 15, cy - 10, 15, 6, 15, 11, (45, 35, 65), (28, 20, 42), (18, 12, 28))

    # Serrure / Latch Doré
    draw_voxel_box(draw, cx - 10, cy + 65, 2, 4, 1, 10, (251, 191, 36), (245, 158, 11), (217, 119, 6))

    # Rayons magiques s'échappant de l'ouverture
    for _ in range(8):
        rx = cx + random.randint(-40, 40)
        ry = cy + random.randint(20, 60)
        draw.line([(rx, ry), (rx + random.randint(-25, 25), ry - random.randint(50, 110))], fill=(192, 132, 252, 160), width=3)

    add_pixel_sparkles(im, (230, 150, 255), count=20)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Coffre Céleste 3D : {os.path.basename(output_path)}")

def render_chest_omega(output_path):
    SIZE = 512
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, (239, 68, 68), max_alpha=160, power=2.0)
    im.paste(glow, (0, 0), glow)

    # Ombre
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([110, 370, 402, 450], fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    im.paste(shadow, (0, 0), shadow)

    draw = ImageDraw.Draw(im)
    cx, cy = 256, 150

    # Base Vault Trial 1.21 (Cuivre oxydé & Ardoise)
    draw_voxel_box(draw, cx, cy + 60, 14, 11, 14, 11, (180, 83, 9), (146, 64, 14), (120, 53, 15))

    # Armature d'épreuve en ardoise sombre
    draw_voxel_box(draw, cx - 2, cy + 58, 14, 2, 14, 11, (75, 85, 99), (55, 65, 81), (31, 41, 55))

    # Couvercle renforcé
    draw_voxel_box(draw, cx - 15, cy - 10, 15, 6, 15, 11, (217, 119, 6), (180, 83, 9), (146, 64, 14))

    # Serrure / Trou de Serrure d'Épreuve Oméga (Trial Vault Core)
    draw_voxel_box(draw, cx - 10, cy + 65, 3, 5, 1, 10, (254, 240, 138), (251, 191, 36), (245, 158, 11))
    draw.rectangle([cx - 8, cy + 78, cx - 4, cy + 86], fill=(220, 38, 38))

    # Flammes d'épreuve rougeoyantes
    for _ in range(10):
        rx = cx + random.randint(-45, 45)
        ry = cy + random.randint(20, 60)
        draw.line([(rx, ry), (rx + random.randint(-20, 20), ry - random.randint(60, 120))], fill=(251, 146, 60, 180), width=3)

    add_pixel_sparkles(im, (255, 120, 60), count=22)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Coffre Oméga 3D : {os.path.basename(output_path)}")

# ========================================================
# 3. RENDU DES DOS DE CARTES HOLOGRAPHIQUES (CARD BACKS)
# ========================================================
def render_card_back(theme, output_path):
    SIZE = 512
    CARD_W, CARD_H = 320, 440
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    border_col = (168, 85, 247) if theme == 'celestial' else (245, 158, 11)
    inner_glow = (56, 189, 248) if theme == 'celestial' else (239, 68, 68)

    # Glow d'ambiance
    glow = create_radial_glow(SIZE, border_col, max_alpha=140, power=2.2)
    im.paste(glow, (0, 0), glow)

    # Ombre de carte
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    ox = (SIZE - CARD_W) // 2
    oy = (SIZE - CARD_H) // 2
    sd.rounded_rectangle([ox - 10, oy - 10, ox + CARD_W + 10, oy + CARD_H + 10], radius=24, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    im.paste(shadow, (0, 0), shadow)

    draw = ImageDraw.Draw(im)

    # Corps de Carte Voxelisé
    bg_color = (18, 14, 28) if theme == 'celestial' else (28, 16, 12)
    draw.rounded_rectangle([ox, oy, ox + CARD_W, oy + CARD_H], radius=20, fill=bg_color, outline=border_col, width=4)

    # Cadre intérieur chanfreiné
    draw.rounded_rectangle([ox + 12, oy + 12, ox + CARD_W - 12, oy + CARD_H - 12], radius=14, outline=(255, 255, 255, 40), width=2)

    # Motif losange central (Étoile du Nether / Crest Oméga)
    cx, cy = SIZE // 2, SIZE // 2
    R = 65
    draw.polygon([(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)], fill=(border_col[0]//2, border_col[1]//2, border_col[2]//2, 140), outline=border_col, width=3)
    
    r_small = 35
    draw.polygon([(cx, cy - r_small), (cx + r_small, cy), (cx, cy + r_small), (cx - r_small, cy)], fill=inner_glow)

    # Rayons d'étoile
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        x2 = cx + int(math.cos(rad) * 95)
        y2 = cy + int(math.sin(rad) * 95)
        draw.line([(cx, cy), (x2, y2)], fill=(255, 255, 255, 80), width=2)

    # Textes stylisés
    title = "AETHER CAISSE" if theme == 'celestial' else "OMEGA VAULT"
    # Coins décorés
    draw.rectangle([ox + 20, oy + 20, ox + 32, oy + 32], fill=border_col)
    draw.rectangle([ox + CARD_W - 32, oy + 20, ox + CARD_W - 20, oy + 32], fill=border_col)
    draw.rectangle([ox + 20, oy + CARD_H - 32, ox + 32, oy + CARD_H - 20], fill=border_col)
    draw.rectangle([ox + CARD_W - 32, oy + CARD_H - 32, ox + CARD_W - 20, oy + CARD_H - 20], fill=border_col)

    add_pixel_sparkles(im, inner_glow, count=16)
    im.save(output_path, "PNG")
    print(f"[*] Rendu Card Back : {os.path.basename(output_path)}")

def main():
    print("=== DÉBUT GÉNÉRATION VISUELS DE CAISSES ET NANO BANANA ===")
    render_nano_banana(os.path.join(OUTPUT_DIR, "item_nano_banana.png"))
    render_chest_celestial(os.path.join(OUTPUT_DIR, "crate_chest_celestial.png"))
    render_chest_omega(os.path.join(OUTPUT_DIR, "crate_chest_omega.png"))
    render_card_back("celestial", os.path.join(OUTPUT_DIR, "crate_card_back_celestial.png"))
    render_card_back("omega", os.path.join(OUTPUT_DIR, "crate_card_back_omega.png"))
    print("=== VISUELS DE CAISSES GÉNÉRÉS AVEC SUCCÈS ===")

if __name__ == "__main__":
    main()
