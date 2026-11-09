import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_STATIC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "static"))
ITEMS_DIR = os.path.join(WEB_STATIC_DIR, "images", "items")
BLOCKS_3D_DIR = os.path.join(WEB_STATIC_DIR, "images", "blocks_3d")
EXTRACTED_DIR = os.path.join(WEB_STATIC_DIR, "images", "extracted_textures")
os.makedirs(ITEMS_DIR, exist_ok=True)

SIZE = 512

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

def add_pixel_sparkles(im, color=(255, 255, 255), count=16, seed=42):
    d = ImageDraw.Draw(im)
    w, h = im.size
    random.seed(seed)
    for _ in range(count):
        sx = random.randint(70, w - 70)
        sy = random.randint(70, h - 70)
        sz = random.choice([3, 5, 8])
        alpha = random.randint(200, 255)
        c = (color[0], color[1], color[2], alpha)
        d.rectangle([sx, sy - sz, sx + 2, sy + sz + 2], fill=c)
        d.rectangle([sx - sz, sy, sx + sz + 2, sy + 2], fill=c)
        # Highlight center
        d.rectangle([sx, sy, sx + 2, sy + 2], fill=(255, 255, 255, 255))

def draw_coin(color_outer, color_main, color_inner, color_rim, symbol="⛃"):
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2
    r = 170

    # Shadow
    d.ellipse([cx - r + 8, cy - r + 18, cx + r + 8, cy + r + 18], fill=(0, 0, 0, 110))

    # Outer Rim
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color_outer, outline=color_rim, width=12)
    # Inner circle
    d.ellipse([cx - r + 24, cy - r + 24, cx + r - 24, cy + r - 24], fill=color_main, outline=color_inner, width=8)

    # Specular Arc highlight
    d.arc([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], start=200, end=340, fill=(255, 255, 255, 180), width=6)

    # Central Embossed Emblem (Star or Square / Habbo crest)
    crest_r = 75
    d.ellipse([cx - crest_r, cy - crest_r, cx + crest_r, cy + crest_r], fill=color_inner, outline=color_rim, width=4)
    # Beveled Star
    pts = []
    num_pts = 8
    for i in range(num_pts * 2):
        rad = (crest_r - 15) if i % 2 == 0 else (crest_r // 2)
        ang = i * math.pi / num_pts - math.pi / 2
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=color_outer, outline=color_rim)
    # Center diamond
    d.polygon([
        (cx, cy - 20), (cx + 20, cy), (cx, cy + 20), (cx - 20, cy)
    ], fill=(255, 255, 255, 220))

    return im

def draw_ingot(gold_top, gold_left, gold_right, stamp_text="999.9 HABBO"):
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2

    # Drop shadow
    shadow_pts = [(cx - 160, cy + 120), (cx + 80, cy + 140), (cx + 170, cy + 90), (cx - 70, cy + 70)]
    d.polygon(shadow_pts, fill=(0, 0, 0, 90))

    # Ingot Trapezoid Geometry (Isometric perspective)
    # Top face
    p_top = [(cx - 130, cy - 40), (cx + 50, cy - 80), (cx + 150, cy - 20), (cx - 30, cy + 20)]
    d.polygon(p_top, fill=gold_top, outline=(255, 245, 180, 230), width=4)

    # Left face
    p_left = [(cx - 130, cy - 40), (cx - 30, cy + 20), (cx - 40, cy + 90), (cx - 145, cy + 30)]
    d.polygon(p_left, fill=gold_left, outline=(180, 130, 20, 200), width=4)

    # Right face
    p_right = [(cx - 30, cy + 20), (cx + 150, cy - 20), (cx + 140, cy + 40), (cx - 40, cy + 90)]
    d.polygon(p_right, fill=gold_right, outline=(140, 95, 10, 200), width=4)

    # Engraved stamp inset
    inset_top = [(cx - 90, cy - 28), (cx + 30, cy - 58), (cx + 105, cy - 14), (cx - 15, cy + 14)]
    d.polygon(inset_top, fill=(215, 160, 25, 255), outline=(150, 100, 10, 180), width=3)
    # Stamp bars
    d.line([(cx - 45, cy - 15), (cx + 45, cy - 35)], fill=(255, 250, 200, 220), width=4)
    d.line([(cx - 30, cy), (cx + 60, cy - 20)], fill=(150, 100, 10, 220), width=3)

    return im

def draw_money_sack():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = SIZE // 2, SIZE // 2 + 30

    # Shadow
    d.ellipse([cx - 150, cy + 80, cx + 150, cy + 150], fill=(0, 0, 0, 110))

    # Pouch bottom body
    d.ellipse([cx - 140, cy - 70, cx + 140, cy + 110], fill=(160, 100, 45), outline=(100, 60, 25), width=8)
    # Shadow creases
    d.arc([cx - 120, cy - 50, cx + 120, cy + 95], start=40, end=140, fill=(110, 65, 25), width=10)

    # Neck tied
    d.polygon([(cx - 70, cy - 65), (cx + 70, cy - 65), (cx + 50, cy - 90), (cx - 50, cy - 90)], fill=(140, 85, 35), outline=(90, 50, 20), width=6)
    # Top frill
    d.polygon([(cx - 90, cy - 140), (cx + 90, cy - 140), (cx + 50, cy - 90), (cx - 50, cy - 90)], fill=(175, 115, 55), outline=(100, 60, 25), width=6)

    # Gold ribbon / tie
    d.line([(cx - 60, cy - 80), (cx + 60, cy - 80)], fill=(255, 215, 0), width=14)
    d.line([(cx, cy - 80), (cx - 35, cy - 40)], fill=(230, 190, 0), width=10)
    d.line([(cx, cy - 80), (cx + 25, cy - 35)], fill=(230, 190, 0), width=10)

    # Big Gold Dollar/Coin Crest on sack
    crest_cy = cy + 20
    d.ellipse([cx - 50, crest_cy - 50, cx + 50, crest_cy + 50], fill=(245, 185, 25), outline=(160, 110, 10), width=6)
    # ⛃ symbol / Habbo star
    d.polygon([(cx, crest_cy - 30), (cx + 28, crest_cy), (cx, crest_cy + 30), (cx - 28, crest_cy)], fill=(255, 235, 100), outline=(180, 130, 20), width=4)

    # Overflowing gold coins at the frill
    for ox, oy in [(-30, -110), (0, -125), (25, -112), (-10, -100)]:
        d.ellipse([cx + ox - 20, cy + oy - 12, cx + ox + 20, cy + oy + 12], fill=(255, 220, 50), outline=(190, 140, 20), width=4)

    return im

def draw_block_with_aura(block_filename, glow_color, sparkle_color, border_color):
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow = create_radial_glow(SIZE, glow_color, max_alpha=160, power=2.0)
    im.paste(glow, (0, 0), glow)

    block_path = os.path.join(BLOCKS_3D_DIR, block_filename)
    if os.path.exists(block_path):
        blk = Image.open(block_path).convert("RGBA")
        # Upscale with pixel-art preserving NEAREST or LANCZOS
        target_w = 340
        aspect = blk.height / blk.width
        target_h = int(target_w * aspect)
        blk_resized = blk.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Shadow underneath
        d = ImageDraw.Draw(im)
        cx, cy = SIZE // 2, SIZE // 2 + 100
        d.ellipse([cx - 170, cy, cx + 170, cy + 70], fill=(0, 0, 0, 120))

        # Paste block
        pos = ((SIZE - target_w) // 2, (SIZE - target_h) // 2 - 10)
        im.paste(blk_resized, pos, blk_resized)

    add_pixel_sparkles(im, color=sparkle_color, count=20, seed=77)
    return im

def generate_all():
    print("Génération des icônes Magots & Lingots Habbo...")

    # 1. Pièce de Bronze (10 ⛃)
    im1 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow1 = create_radial_glow(SIZE, (200, 110, 50), max_alpha=140)
    im1.paste(glow1, (0, 0), glow1)
    c1 = draw_coin(
        color_outer=(185, 95, 45),
        color_main=(215, 120, 60),
        color_inner=(150, 75, 30),
        color_rim=(110, 55, 20)
    )
    im1.paste(c1, (0, 0), c1)
    add_pixel_sparkles(im1, color=(255, 190, 140), count=14, seed=10)
    im1.save(os.path.join(ITEMS_DIR, "magot_piece_bronze.png"), "PNG")
    print("[OK] magot_piece_bronze.png genere")

    # 2. Pièce d'Argent Royale (50 ⛃)
    im2 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow2 = create_radial_glow(SIZE, (170, 200, 230), max_alpha=140)
    im2.paste(glow2, (0, 0), glow2)
    c2 = draw_coin(
        color_outer=(195, 210, 225),
        color_main=(235, 245, 255),
        color_inner=(160, 180, 200),
        color_rim=(120, 140, 160)
    )
    im2.paste(c2, (0, 0), c2)
    add_pixel_sparkles(im2, color=(220, 240, 255), count=16, seed=50)
    im2.save(os.path.join(ITEMS_DIR, "magot_piece_argent.png"), "PNG")
    print("[OK] magot_piece_argent.png genere")

    # 3. Sac de Pièces d'Or (100 ⛃)
    im3 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow3 = create_radial_glow(SIZE, (245, 185, 30), max_alpha=150)
    im3.paste(glow3, (0, 0), glow3)
    c3 = draw_money_sack()
    im3.paste(c3, (0, 0), c3)
    add_pixel_sparkles(im3, color=(255, 245, 160), count=18, seed=100)
    im3.save(os.path.join(ITEMS_DIR, "magot_sac_pieces.png"), "PNG")
    print("[OK] magot_sac_pieces.png genere")

    # 4. Lingot d'Or Habbo (250 ⛃)
    im4 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow4 = create_radial_glow(SIZE, (255, 195, 20), max_alpha=160)
    im4.paste(glow4, (0, 0), glow4)
    c4 = draw_ingot(
        gold_top=(255, 225, 60),
        gold_left=(220, 170, 20),
        gold_right=(175, 125, 10)
    )
    im4.paste(c4, (0, 0), c4)
    add_pixel_sparkles(im4, color=(255, 255, 200), count=22, seed=250)
    im4.save(os.path.join(ITEMS_DIR, "magot_lingot_or.png"), "PNG")
    print("[OK] magot_lingot_or.png genere")

    # 5. Bloc d'Or Impérial (500 ⛃)
    im5 = draw_block_with_aura(
        block_filename="gold_block.png",
        glow_color=(255, 200, 30),
        sparkle_color=(255, 255, 180),
        border_color=(255, 220, 50)
    )
    im5.save(os.path.join(ITEMS_DIR, "magot_bloc_or.png"), "PNG")
    print("[OK] magot_bloc_or.png genere")

    # 6. Magot Suprême Bloc d'Émeraude (1 000 ⛃)
    im6 = draw_block_with_aura(
        block_filename="emerald_block.png",
        glow_color=(20, 220, 110),
        sparkle_color=(180, 255, 210),
        border_color=(30, 240, 130)
    )
    im6.save(os.path.join(ITEMS_DIR, "magot_bloc_emeraude.png"), "PNG")
    print("[OK] magot_bloc_emeraude.png genere")

if __name__ == "__main__":
    generate_all()
