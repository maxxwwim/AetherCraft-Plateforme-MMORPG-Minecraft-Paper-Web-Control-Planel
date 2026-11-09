"""
Générateur 3D Voxel Haute-Définition des Animaux Célestes (AetherCraft).
Remplace les anciens visuels "aplatis" (2 cubes sans pattes) par de véritables sculptures
voxel 3D isométriques complètes, grandes et stylées :
- Anatomie complète : 4 pattes articulées, torse volumétrique, poitrail, cou, tête haute,
  museau/bec, yeux lumineux, cornes/oreilles/crête, ailes déployées et queue articulée.
- Génère pet_dragon.png, pet_capybara.png, pet_fox.png, pet_goat.png, pet_phoenix.png, pet_griffin.png
  dans web/static/images/items/.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFilter

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "images", "items"))


def shade_color(rgb, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in rgb) + (255,)


def draw_iso_box(draw, cx, cy, x, y, z, dx, dy, dz, color, scale=11.0):
    """
    Dessine un parallélépipède 3D isométrique (x: droite-avant, y: gauche-avant, z: hauteur verticale).
    """
    cos30 = math.cos(math.radians(30))
    sin30 = 0.5

    def proj(px, py, pz):
        sx = cx + (px - py) * cos30 * scale
        sy = cy + (px + py) * sin30 * scale - pz * scale
        return (sx, sy)

    # Sommets de la boîte (x..x+dx, y..y+dy, z..z+dz)
    p001 = proj(x, y, z + dz)
    p101 = proj(x + dx, y, z + dz)
    p111 = proj(x + dx, y + dy, z + dz)
    p011 = proj(x, y + dy, z + dz)

    p100 = proj(x + dx, y, z)
    p110 = proj(x + dx, y + dy, z)
    p010 = proj(x, y + dy, z)

    top_col = shade_color(color, 1.16)
    left_col = shade_color(color, 0.88)
    right_col = shade_color(color, 0.68)
    edge_col = shade_color(color, 0.42)

    # Face supérieure (z + dz)
    draw.polygon([p001, p101, p111, p011], fill=top_col, outline=edge_col)
    # Face avant-droite (x + dx)
    draw.polygon([p101, p111, p110, p100], fill=left_col, outline=edge_col)
    # Face avant-gauche (y + dy)
    draw.polygon([p011, p111, p110, p010], fill=right_col, outline=edge_col)


def render_creature_canvas(boxes, glow_rgb, badge_rgb):
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 1. Halo énergétique radial & socle astral sous l'animal
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    gdraw.ellipse((90, 90, 422, 422), fill=glow_rgb + (55,))
    gdraw.ellipse((130, 330, 382, 445), fill=badge_rgb + (90,))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, glow_layer)

    draw = ImageDraw.Draw(img)

    # Socle cristal octogonal au sol
    draw_iso_box(draw, 256, 365, -4.2, -4.2, -1.2, 8.4, 8.4, 0.8, (30, 41, 59), scale=12.5)
    draw_iso_box(draw, 256, 365, -3.4, -3.4, -0.4, 6.8, 6.8, 0.4, badge_rgb, scale=12.5)

    # Tri des boîtes du fond vers l'avant (x + y + z croissant) pour un z-order isométrique parfait
    sorted_boxes = sorted(boxes, key=lambda b: (b[0] + b[3] * 0.5) + (b[1] + b[4] * 0.5) + (b[2] + b[5] * 0.5) * 1.2)
    for b in sorted_boxes:
        x, y, z, dx, dy, dz, col = b
        draw_iso_box(draw, 256, 345, x, y, z, dx, dy, dz, col, scale=13.5)

    return img


def build_all_pets():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. DRAGONEAU DE L'AETHER (Grand dragon articulé : 4 pattes griffues, queue crêtée, ailes déployées, cou, tête cornue, souffle d'or)
    dragon_boxes = [
        # 4 Pattes puissantes
        (-2.2, 1.4, 0.0, 1.3, 1.3, 3.2, (59, 7, 100)),
        (1.4, -2.2, 0.0, 1.3, 1.3, 3.2, (59, 7, 100)),
        (1.6, 1.6, 0.0, 1.4, 1.4, 3.4, (76, 29, 149)),
        (-2.0, -2.0, 0.0, 1.3, 1.3, 3.2, (46, 16, 101)),
        # Griffes dorées
        (1.8, 1.8, 0.0, 1.5, 1.5, 0.7, (245, 158, 11)),
        (-2.0, 1.6, 0.0, 1.4, 1.4, 0.7, (245, 158, 11)),
        (1.6, -2.0, 0.0, 1.4, 1.4, 0.7, (245, 158, 11)),
        # Queue longue articulée à crêtes d'or
        (-5.5, -5.5, 3.8, 2.2, 2.2, 1.4, (88, 28, 135)),
        (-3.8, -3.8, 3.2, 2.4, 2.4, 1.8, (107, 33, 168)),
        (-4.5, -4.5, 5.2, 0.9, 0.9, 1.2, (251, 191, 36)),
        # Torse volumétrique & Poitrail d'améthyste
        (-2.2, -2.2, 3.0, 5.2, 4.4, 3.6, (88, 28, 135)),
        (0.2, -1.8, 3.2, 3.2, 3.8, 3.8, (147, 51, 234)),
        (1.2, -1.2, 3.4, 2.4, 2.8, 3.2, (245, 158, 11)),
        # Crêtes dorsales
        (-1.2, -0.5, 6.6, 1.0, 1.0, 1.3, (251, 191, 36)),
        (0.4, -0.5, 6.8, 1.0, 1.0, 1.4, (251, 191, 36)),
        # Grandes Ailes Draconiques déployées (Gauche & Droite)
        (-1.5, -7.2, 5.5, 3.8, 5.2, 0.7, (168, 85, 247)),
        (-1.0, -7.5, 6.2, 1.2, 5.5, 0.8, (245, 158, 11)),
        (-7.2, -1.5, 5.5, 5.2, 3.8, 0.7, (168, 85, 247)),
        (-7.5, -1.0, 6.2, 5.5, 1.2, 0.8, (245, 158, 11)),
        # Cou & Tête Haute Sculptée
        (1.6, -1.2, 6.4, 2.4, 2.4, 2.4, (107, 33, 168)),
        (2.2, -1.8, 8.2, 3.6, 3.6, 3.2, (126, 34, 206)),
        # Museau & Mâchoire
        (4.8, -1.2, 8.4, 2.4, 2.4, 1.8, (88, 28, 135)),
        (5.4, -0.8, 9.2, 1.8, 1.6, 0.8, (251, 191, 36)),
        # Yeux stellaires & Grandes Cornes Royales
        (4.6, 1.2, 9.8, 0.9, 0.9, 0.9, (56, 189, 248)),
        (1.8, 1.0, 11.4, 1.1, 1.1, 3.0, (251, 191, 36)),
        (1.8, -2.0, 11.4, 1.1, 1.1, 3.0, (251, 191, 36)),
    ]

    # 2. CAPYBARA IMPÉRIAL CÉLESTE (Grand Capybara sur ses 4 pattes, manteau d'émeraude, tête haute noble, lotus sacré & auréole)
    capy_boxes = [
        # 4 Pattes robustes bien visibles
        (-2.4, 1.4, 0.0, 1.4, 1.4, 2.8, (92, 52, 24)),
        (1.4, -2.2, 0.0, 1.4, 1.4, 2.8, (92, 52, 24)),
        (1.6, 1.4, 0.0, 1.4, 1.4, 2.8, (108, 62, 30)),
        (-2.2, -2.0, 0.0, 1.4, 1.4, 2.8, (78, 42, 18)),
        # Corps volumétrique chaleureux
        (-2.6, -2.2, 2.6, 5.8, 4.8, 3.8, (146, 84, 38)),
        # Tapis/Selle de mousse émeraude & bordure d'or sur le dos
        (-1.8, -2.4, 4.2, 4.0, 5.2, 2.5, (16, 185, 129)),
        (-1.4, -2.5, 4.0, 3.2, 5.4, 0.7, (245, 158, 11)),
        # Lotus Céleste épanoui sur le dos
        (-0.8, -0.8, 6.7, 2.2, 2.2, 1.1, (244, 114, 182)),
        (-0.3, -0.3, 7.8, 1.2, 1.2, 1.0, (251, 191, 36)),
        # Cou & Grande Tête Noble de Capybara
        (1.8, -1.8, 5.4, 3.8, 3.8, 3.6, (161, 98, 48)),
        # Museau caractéristique carré
        (4.6, -1.4, 5.6, 2.2, 3.0, 2.6, (113, 63, 28)),
        # Yeux paisibles & Oreilles rondes
        (4.0, 1.4, 7.6, 0.8, 0.8, 0.8, (254, 240, 138)),
        (2.0, 1.2, 9.0, 1.0, 1.0, 1.2, (92, 52, 24)),
        (2.0, -2.0, 9.0, 1.0, 1.0, 1.2, (92, 52, 24)),
        # Mandarine / Couronne dorée sur la tête
        (3.0, -0.5, 9.0, 1.4, 1.4, 1.3, (249, 115, 22)),
        (3.4, -0.2, 10.3, 0.6, 0.6, 0.6, (34, 197, 94)),
    ]

    # 3. KITSUNE RENARD ASTRAL (Renard élancé sur 4 pattes, plastron blanc, tête fine à grandes oreilles, 3 grandes queues comètes déployées)
    fox_boxes = [
        # 4 Pattes noires/blanches élancées
        (-2.0, 1.2, 0.0, 1.1, 1.1, 3.2, (30, 41, 59)),
        (1.2, -1.8, 0.0, 1.1, 1.1, 3.2, (30, 41, 59)),
        (1.6, 1.2, 0.0, 1.2, 1.2, 3.2, (30, 41, 59)),
        (-1.8, -1.8, 0.0, 1.1, 1.1, 3.2, (30, 41, 59)),
        # 3 Grandes Queues de Comète Astrale déployées en éventail à l'arrière
        (-6.2, -2.0, 4.2, 3.8, 1.6, 2.6, (249, 115, 22)),
        (-7.4, -1.8, 5.0, 1.8, 1.4, 2.0, (56, 189, 248)),
        (-2.0, -6.2, 4.2, 1.6, 3.8, 2.6, (249, 115, 22)),
        (-1.8, -7.4, 5.0, 1.4, 1.8, 2.0, (56, 189, 248)),
        (-5.5, -5.5, 5.2, 3.4, 3.4, 2.8, (234, 88, 12)),
        (-6.8, -6.8, 6.2, 2.0, 2.0, 2.2, (251, 191, 36)),
        # Corps souple & Plastron blanc
        (-2.2, -1.6, 3.0, 4.8, 3.6, 3.2, (249, 115, 22)),
        (1.2, -1.4, 3.2, 2.2, 3.2, 3.2, (248, 250, 252)),
        # Tête de Kitsune & Museau pointu
        (1.8, -1.8, 6.0, 3.4, 3.6, 3.2, (249, 115, 22)),
        (4.6, -1.0, 6.0, 2.2, 2.0, 1.6, (248, 250, 252)),
        (6.2, -0.5, 6.8, 0.8, 1.0, 0.8, (15, 23, 42)),
        # Yeux cyan mystiques & Grandes Oreilles pointues dorées
        (4.2, 1.2, 7.6, 0.9, 0.9, 0.9, (56, 189, 248)),
        (2.2, 0.8, 9.2, 1.2, 1.2, 2.8, (249, 115, 22)),
        (2.4, 1.0, 11.2, 0.9, 0.9, 1.2, (251, 191, 36)),
        (2.2, -2.0, 9.2, 1.2, 1.2, 2.8, (249, 115, 22)),
        (2.4, -2.0, 11.2, 0.9, 0.9, 1.2, (251, 191, 36)),
    ]

    # 4. BÉLIER ROYAL DES NUAGES (Bélier majestueux sur 4 sabots d'or, toison nuageuse volumineuse, grandes cornes spiralées en or massif)
    goat_boxes = [
        # 4 Pattes & Sabots d'or
        (-2.2, 1.3, 0.0, 1.2, 1.2, 1.0, (245, 158, 11)),
        (1.3, -2.0, 0.0, 1.2, 1.2, 1.0, (245, 158, 11)),
        (1.5, 1.3, 0.0, 1.2, 1.2, 1.0, (245, 158, 11)),
        (-2.2, 1.3, 1.0, 1.2, 1.2, 2.4, (203, 213, 225)),
        (1.3, -2.0, 1.0, 1.2, 1.2, 2.4, (203, 213, 225)),
        (1.5, 1.3, 1.0, 1.2, 1.2, 2.4, (226, 232, 240)),
        (-2.0, -2.0, 0.0, 1.2, 1.2, 3.4, (148, 163, 184)),
        # Toison de laine céleste volumineuse & Caparaçon d'or et diamant
        (-2.6, -2.2, 3.2, 5.4, 4.6, 3.8, (248, 250, 252)),
        (-1.2, -2.4, 4.0, 3.0, 5.0, 3.2, (56, 189, 248)),
        (-0.8, -2.5, 4.2, 2.2, 5.2, 3.0, (251, 191, 36)),
        # Tête haute & Museau
        (1.8, -1.6, 6.4, 3.4, 3.2, 3.4, (241, 245, 249)),
        (4.4, -1.1, 6.6, 2.0, 2.2, 2.0, (203, 213, 225)),
        # Grandes Cornes Impériales recourbées en Or
        (1.2, 1.2, 9.2, 2.2, 1.4, 2.8, (245, 158, 11)),
        (0.2, 1.8, 7.6, 1.8, 1.4, 2.2, (217, 119, 6)),
        (1.2, -2.6, 9.2, 2.2, 1.4, 2.8, (245, 158, 11)),
        (0.2, -3.0, 7.6, 1.8, 1.4, 2.2, (217, 119, 6)),
        # Yeux d'azur
        (4.2, 1.1, 8.2, 0.8, 0.8, 0.8, (14, 165, 233)),
    ]

    # 5. PHÉNIX D'OR PRIMORDIAL (Grand Oiseau Solaire dressé, serres d'or, queue flamboyante, ailes immenses déployées, crête impériale)
    phoenix_boxes = [
        # Serres d'or
        (-0.8, 0.8, 0.0, 1.3, 1.3, 2.6, (245, 158, 11)),
        (0.8, -0.8, 0.0, 1.3, 1.3, 2.6, (245, 158, 11)),
        # Longue Queue de Flammes Solaire
        (-5.8, -5.8, 2.2, 3.6, 3.6, 1.2, (220, 38, 38)),
        (-4.2, -4.2, 2.8, 3.2, 3.2, 1.4, (249, 115, 22)),
        (-3.0, -3.0, 3.4, 2.6, 2.6, 1.6, (251, 191, 36)),
        # Corps dressé majestueux
        (-1.6, -1.6, 2.6, 3.8, 3.8, 4.6, (234, 88, 12)),
        (0.4, -1.2, 3.2, 2.4, 3.0, 4.0, (251, 191, 36)),
        # Ailes Solaires Géantes déployées (3 étages de plumes incandescentes)
        (-1.2, -7.8, 4.8, 3.2, 6.2, 0.9, (220, 38, 38)),
        (-0.8, -8.4, 5.8, 2.6, 6.8, 0.9, (249, 115, 22)),
        (-0.4, -9.0, 6.8, 2.0, 7.2, 0.9, (253, 224, 71)),
        (-7.8, -1.2, 4.8, 6.2, 3.2, 0.9, (220, 38, 38)),
        (-8.4, -0.8, 5.8, 6.8, 2.6, 0.9, (249, 115, 22)),
        (-9.0, -0.4, 6.8, 7.2, 2.0, 0.9, (253, 224, 71)),
        # Tête du Phénix, Bec d'Or & Couronne de Flammes
        (0.6, -1.4, 7.2, 3.2, 3.2, 3.2, (249, 115, 22)),
        (3.4, -0.8, 7.8, 2.2, 1.8, 1.4, (253, 224, 71)),
        (0.8, -0.6, 10.4, 1.4, 1.4, 3.0, (253, 224, 71)),
        (-0.4, -0.6, 10.0, 1.2, 1.2, 2.4, (239, 68, 68)),
    ]

    # 6. GRIFFON ASTRAL SOUVERAIN (Nouveau familier : corps de lion d'or, buste & tête d'aigle blanc céleste, grandes ailes de cristal)
    griffin_boxes = [
        # 4 Pattes (griffes d'or à l'avant, pattes de lion à l'arrière)
        (-2.2, 1.3, 0.0, 1.3, 1.3, 3.2, (217, 119, 6)),
        (1.3, -2.2, 0.0, 1.3, 1.3, 3.2, (217, 119, 6)),
        (1.6, 1.4, 0.0, 1.3, 1.3, 3.2, (251, 191, 36)),
        (-2.0, -2.0, 0.0, 1.3, 1.3, 3.2, (180, 83, 9)),
        # Queue de lion
        (-5.2, -5.2, 4.0, 2.6, 2.6, 1.2, (217, 119, 6)),
        # Corps de Lion d'Or & Poitrail d'Aigle d'Albâtre
        (-2.2, -2.0, 3.0, 5.0, 4.2, 3.6, (234, 179, 8)),
        (0.6, -1.8, 3.4, 2.8, 3.8, 3.8, (248, 250, 252)),
        # Grandes Ailes Célestes Blanc & Azur
        (-1.2, -7.4, 5.4, 3.4, 5.6, 0.9, (226, 232, 240)),
        (-0.8, -8.0, 6.4, 2.4, 6.2, 0.9, (56, 189, 248)),
        (-7.4, -1.2, 5.4, 5.6, 3.4, 0.9, (226, 232, 240)),
        (-8.0, -0.8, 6.4, 6.2, 2.4, 0.9, (56, 189, 248)),
        # Tête d'Aigle Impérial & Bec Crochu Doré
        (1.8, -1.6, 6.8, 3.4, 3.4, 3.4, (248, 250, 252)),
        (4.8, -0.9, 7.2, 2.2, 1.8, 1.8, (245, 158, 11)),
        (1.6, 1.0, 10.2, 1.0, 1.0, 2.2, (56, 189, 248)),
        (1.6, -2.0, 10.2, 1.0, 1.0, 2.2, (56, 189, 248)),
    ]

    configs = [
        ("pet_dragon.png", dragon_boxes, (168, 85, 247), (245, 158, 11)),
        ("pet_capybara.png", capy_boxes, (16, 185, 129), (244, 114, 182)),
        ("pet_fox.png", fox_boxes, (249, 115, 22), (56, 189, 248)),
        ("pet_goat.png", goat_boxes, (56, 189, 248), (245, 158, 11)),
        ("pet_phoenix.png", phoenix_boxes, (239, 68, 68), (251, 191, 36)),
        ("pet_griffin.png", griffin_boxes, (251, 191, 36), (56, 189, 248)),
    ]

    for filename, boxes, glow_col, badge_col in configs:
        out_path = os.path.join(OUTPUT_DIR, filename)
        img = render_creature_canvas(boxes, glow_col, badge_col)
        img.save(out_path, "PNG")
        print(f"[OK] Visuel 3D Voxel Haute-Définition généré : {out_path}")


if __name__ == "__main__":
    build_all_pets()
