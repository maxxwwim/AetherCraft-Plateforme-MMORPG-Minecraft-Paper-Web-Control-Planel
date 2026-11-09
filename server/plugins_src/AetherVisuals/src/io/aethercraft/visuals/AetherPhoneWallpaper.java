package io.aethercraft.visuals;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.geom.RoundRectangle2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.InputStream;

/**
 * Service de Fond d'Écran AetherOS 2026, Glassmorphism Soft UI & Écriture Déroulante (Marquee).
 */
public final class AetherPhoneWallpaper {

    private static BufferedImage cachedWallpaper = null;
    private static final int W = 128, H = 128;

    public static final Color CYAN_SOFT = new Color(56, 228, 255);
    public static final Color EMERALD_SOFT = new Color(52, 232, 158);
    public static final Color GOLD_SOFT = new Color(255, 212, 75);
    public static final Color ROSE_SOFT = new Color(255, 105, 135);
    public static final Color WHITE_SOFT = new Color(248, 250, 255);
    public static final Color MUTED_SOFT = new Color(168, 184, 212);

    private AetherPhoneWallpaper() {}

    public static void configureQualityHints(Graphics2D g) {
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.setRenderingHint(RenderingHints.KEY_FRACTIONALMETRICS, RenderingHints.VALUE_FRACTIONALMETRICS_ON);
        g.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
    }

    public static synchronized BufferedImage getWallpaper() {
        if (cachedWallpaper != null) return cachedWallpaper;
        cachedWallpaper = loadFromFileOrClasspath();
        if (cachedWallpaper == null) cachedWallpaper = generateProceduralVoxelWallpaper();
        return cachedWallpaper;
    }

    private static BufferedImage loadFromFileOrClasspath() {
        String[] candidatePaths = {
            "data/phone_wallpaper_128.png",
            "data/phone_wallpaper.jpg",
            "plugins/AetherVisuals/phone_wallpaper_128.png",
            "server/data/phone_wallpaper_128.png"
        };
        for (String p : candidatePaths) {
            File f = new File(p);
            if (f.exists() && f.length() > 0) {
                try {
                    BufferedImage raw = ImageIO.read(f);
                    if (raw != null) return fitTo128(raw);
                } catch (Exception ignored) {}
            }
        }
        try (InputStream is = AetherPhoneWallpaper.class.getResourceAsStream("/phone_wallpaper_128.png")) {
            if (is != null) {
                BufferedImage raw = ImageIO.read(is);
                if (raw != null) return fitTo128(raw);
            }
        } catch (Exception ignored) {}
        return null;
    }

    private static BufferedImage fitTo128(BufferedImage src) {
        if (src.getWidth() == W && src.getHeight() == H) return src;
        BufferedImage out = new BufferedImage(W, H, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = out.createGraphics();
        configureQualityHints(g);
        g.drawImage(src, 0, 0, W, H, null);
        g.dispose();
        return out;
    }

    public static BufferedImage generateProceduralVoxelWallpaper() {
        BufferedImage img = new BufferedImage(W, H, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = img.createGraphics();
        configureQualityHints(g);
        // Ciel Crépuscule Synthwave Soft 2026
        g.setPaint(new GradientPaint(0, 0, new Color(18, 14, 48), 0, 82, new Color(135, 42, 102)));
        g.fillRect(0, 0, W, 82);
        // Halo solaire doux
        g.setColor(new Color(255, 170, 90, 55));
        g.fillOval(38, 34, 52, 46);
        g.setPaint(new GradientPaint(0, 42, new Color(255, 220, 95), 0, 70, new Color(255, 95, 125)));
        g.fillRoundRect(48, 44, 32, 26, 6, 6);
        // Océan Nocturne
        g.setPaint(new GradientPaint(0, 80, new Color(14, 32, 72), 0, H, new Color(6, 10, 26)));
        g.fillRect(0, 80, W, H - 80);
        // Gratte-ciels Voxel en silhouette avec fenêtres pastel
        drawCubicBuilding(g, 6, 28, 22, 52, new Color(14, 18, 38), CYAN_SOFT);
        drawCubicBuilding(g, 32, 36, 18, 44, new Color(20, 15, 42), GOLD_SOFT);
        drawCubicBuilding(g, 84, 24, 24, 56, new Color(12, 20, 40), ROSE_SOFT);
        drawCubicBuilding(g, 106, 38, 18, 42, new Color(18, 14, 36), EMERALD_SOFT);
        g.dispose();
        return img;
    }

    private static void drawCubicBuilding(Graphics2D g, int x, int y, int w, int h, Color body, Color windowGlow) {
        g.setColor(body);
        g.fillRoundRect(x, y, w, h, 2, 2);
        g.setColor(new Color(windowGlow.getRed(), windowGlow.getGreen(), windowGlow.getBlue(), 165));
        for (int row = y + 4; row < y + h - 6; row += 7) {
            for (int col = x + 3; col < x + w - 4; col += 6) {
                if ((col + row) % 2 == 0) g.fillRoundRect(col, row, 3, 3, 1, 1);
            }
        }
    }

    public static void drawTitaniumChassis(Graphics2D g, int size) {
        // Bordure extérieure Titane Naturel 2026 avec dégradé métallique doux
        g.setPaint(new GradientPaint(0, 0, new Color(64, 72, 92), size, size, new Color(30, 35, 48)));
        g.fillRoundRect(0, 0, size, size, 12, 12);
        // Cadre interne noir profond
        g.setColor(new Color(8, 11, 18));
        g.fillRoundRect(1, 1, size - 2, size - 2, 10, 10);
        // Fin liseré spéculaire sur le châssis
        g.setStroke(new BasicStroke(0.6f));
        g.setColor(new Color(140, 165, 210, 90));
        g.drawRoundRect(1, 1, size - 3, size - 3, 10, 10);
    }

    public static void renderBackgroundWithGlassOverlay(Graphics2D g, int x, int y, int w, int h) {
        Shape oldClip = g.getClip();
        g.setClip(new RoundRectangle2D.Float(x, y, w, h, 9, 9));
        BufferedImage wp = getWallpaper();
        if (wp != null) {
            g.drawImage(wp, x, y, w, h, null);
        }
        // Voile dépoli dégradé 2026 : adoucit le fond pour une lisibilité parfaite du texte
        g.setPaint(new GradientPaint(0, y, new Color(10, 15, 30, 168), 0, y + h, new Color(6, 10, 22, 208)));
        g.fillRect(x, y, w, h);
        // Halo ambiant Aurora subtil en haut de l'écran
        g.setPaint(new GradientPaint(x, y, new Color(56, 228, 255, 28), x + w, y + 40, new Color(165, 105, 255, 22)));
        g.fillRect(x, y, w, 45);
        g.setClip(oldClip);
    }

    public static void drawStatusBarAndDynamicIsland(Graphics2D g, Font fontTiny) {
        drawSoftText(g, "09:41", 6f, 9.5f, WHITE_SOFT, fontTiny);
        // Dynamic Island 2026 : pilule ultra-douce avec reflet subtil
        g.setColor(new Color(4, 6, 12, 240));
        g.fillRoundRect(43, 3, 42, 7, 7, 7);
        g.setStroke(new BasicStroke(0.5f));
        g.setColor(new Color(255, 255, 255, 35));
        g.drawRoundRect(43, 3, 42, 7, 7, 7);
        // Capteur optique & point d'activité émeraude doux
        g.setColor(new Color(28, 42, 78));
        g.fillOval(76, 5, 3, 3);
        g.setColor(EMERALD_SOFT);
        g.fillOval(50, 5, 2, 2);

        // Barres de réception 5G adoucies
        g.setColor(WHITE_SOFT);
        for (int i = 0; i < 4; i++) {
            g.fillRoundRect(89 + i * 2, 8 - i, 1, 2 + i, 1, 1);
        }
        drawSoftText(g, "5G", 98.5f, 9.5f, CYAN_SOFT, fontTiny);
        // Batterie iOS 2026
        g.setStroke(new BasicStroke(0.6f));
        g.setColor( new Color(255, 255, 255, 190));
        g.drawRoundRect(112, 4, 9, 5, 2, 2);
        g.fillRect(121, 5, 1, 3);
        g.setColor(EMERALD_SOFT);
        g.fillRoundRect(113, 5, 7, 3, 1, 1);
    }

    public static void drawGlassCard(Graphics2D g, int x, int y, int w, int h, boolean focused, Color accent) {
        // Ombre portée douce sous la carte
        g.setColor(new Color(0, 0, 0, focused ? 95 : 55));
        g.fillRoundRect(x, y + 1, w, h, 7, 7);

        // Corps de la carte en verre dépoli (dégradé vertical doux)
        Color topBg = focused
                ? new Color(38, 56, 96, 232)
                : new Color(24, 34, 58, 192);
        Color botBg = focused
                ? new Color(20, 32, 62, 242)
                : new Color(14, 20, 38, 212);
        g.setPaint(new GradientPaint(x, y, topBg, x, y + h, botBg));
        g.fillRoundRect(x, y, w, h, 7, 7);

        // Reflet supérieur verre (effet biseau doux 2026)
        g.setStroke(new BasicStroke(0.5f));
        g.setColor(new Color(255, 255, 255, focused ? 70 : 32));
        g.drawLine(x + 3, y + 1, x + w - 4, y + 1);

        // Bordure de la carte
        if (focused) {
            g.setStroke(new BasicStroke(0.9f));
            g.setColor(new Color(accent.getRed(), accent.getGreen(), accent.getBlue(), 230));
            g.drawRoundRect(x, y, w, h, 7, 7);
            // Barre lumineuse d'accent à gauche de la carte sélectionnée
            g.setColor(accent);
            g.fillRoundRect(x + 1, y + 4, 2, h - 8, 2, 2);
        } else {
            g.setStroke(new BasicStroke(0.55f));
            g.setColor(new Color(110, 140, 195, 75));
            g.drawRoundRect(x, y, w, h, 7, 7);
        }
    }

    public static void drawSquircleIcon(Graphics2D g, int x, int y, int size, Color accent, String iconTxt, Font font) {
        Color top = new Color(
                Math.min(255, accent.getRed() + 35),
                Math.min(255, accent.getGreen() + 35),
                Math.min(255, accent.getBlue() + 35), 240);
        Color bot = new Color(
                Math.max(0, accent.getRed() - 40),
                Math.max(0, accent.getGreen() - 40),
                Math.max(0, accent.getBlue() - 40), 240);
        g.setPaint(new GradientPaint(x, y, top, x, y + size, bot));
        g.fillRoundRect(x, y, size, size, 5, 5);

        g.setStroke(new BasicStroke(0.5f));
        g.setColor(new Color(255, 255, 255, 95));
        g.drawRoundRect(x, y, size, size, 5, 5);

        if (iconTxt != null && !iconTxt.isEmpty()) {
            g.setFont(font);
            FontMetrics fm = g.getFontMetrics();
            int tw = fm.stringWidth(iconTxt);
            float tx = x + (size - tw) / 2.0f;
            float ty = y + (size + fm.getAscent() - fm.getDescent()) / 2.0f - 0.5f;
            g.setColor(new Color(0, 0, 0, 95));
            g.drawString(iconTxt, tx + 0.4f, ty + 0.5f);
            g.setColor( new Color(18, 22, 34));
            g.drawString(iconTxt, tx, ty);
        }
    }

    public static void drawSoftText(Graphics2D g, String txt, float x, float y, Color col, Font f) {
        if (txt == null || txt.isEmpty()) return;
        g.setFont(f);
        g.setColor(new Color(0, 0, 0, 135));
        g.drawString(txt, x + 0.5f, y + 0.6f);
        g.setColor(col);
        g.drawString(txt, x, y);
    }

    /**
     * Affiche un texte lisible : s'il dépasse maxW, il défile automatiquement de manière fluide (Marquee 2026)
     * avec une pause de lecture initiale au lieu d'être coupé brutalement.
     */
    public static void drawMarqueeText(Graphics2D g, String txt, int x, int y, int maxW, Color col, Font f) {
        if (txt == null || txt.isEmpty()) return;
        g.setFont(f);
        FontMetrics fm = g.getFontMetrics();
        int textW = fm.stringWidth(txt);
        if (textW <= maxW) {
            drawSoftText(g, txt, x, y, col, f);
            return;
        }

        Shape oldClip = g.getClip();
        g.clipRect(x, y - fm.getAscent() - 1, maxW, fm.getHeight() + 3);

        String sep = "   •   ";
        int loopW = textW + fm.stringWidth(sep);
        long pauseMs = 1000L;
        long scrollMs = Math.max(1400L, (long) ((loopW / 13.5) * 1000.0));
        long cycleMs = pauseMs + scrollMs;
        long now = System.currentTimeMillis() % cycleMs;
        float offset = (now < pauseMs) ? 0f : (float) (((now - pauseMs) / (double) scrollMs) * loopW);

        drawSoftText(g, txt + sep + txt, x - offset, y, col, f);
        g.setClip(oldClip);
    }

    public static void drawMagneticReticle(Graphics2D g, int x, int y, int size) {
        int cx = Math.max(5, Math.min(size - 6, x));
        int cy = Math.max(5, Math.min(size - 6, y));
        // Curseur tactile VisionOS / iOS 2026 : anneau translucide doux qui ne masque pas le texte
        g.setColor(new Color(0, 0, 0, 90));
        g.setStroke(new BasicStroke(1.1f));
        g.drawOval(cx - 4, cy - 4, 8, 8);

        g.setColor(new Color(255, 255, 255, 185));
        g.setStroke(new BasicStroke(0.75f));
        g.drawOval(cx - 3, cy - 3, 6, 6);

        g.setColor(new Color(56, 228, 255, 210));
        g.fillOval(cx - 1, cy - 1, 2, 2);
    }
}
