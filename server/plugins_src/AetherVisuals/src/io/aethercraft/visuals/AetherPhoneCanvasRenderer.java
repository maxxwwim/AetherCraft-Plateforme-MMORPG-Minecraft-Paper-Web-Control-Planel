package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherHoloDataService.*;
import io.aethercraft.visuals.AetherHoloUIEngine.HoloMode;
import io.aethercraft.visuals.AetherHoloUIEngine.HoloSession;
import io.aethercraft.visuals.AetherHoloUIEngine.ProfileSubTab;
import org.bukkit.Bukkit;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import static io.aethercraft.visuals.AetherPhoneWallpaper.*;

/**
 * Rendu iPhone 2026 Soft UI (256x256 HD Lissé), Glassmorphism & Écriture Déroulante (Marquee).
 */
public final class AetherPhoneCanvasRenderer {

    public static final int SIZE = 128;
    public static final int SCALE = 2;
    public static final int PIXELS = SIZE * SCALE;

    private static final Font FONT_TITLE = new Font("SansSerif", Font.BOLD, 7);
    private static final Font FONT_SUB = new Font("SansSerif", Font.PLAIN, 6);
    private static final Font FONT_TINY = new Font("SansSerif", Font.BOLD, 6);

    private AetherPhoneCanvasRenderer() {}

    public static record CardEntry(String title, String sub, String badge, Color accent, String icon) {
        public CardEntry(String title, String sub, String badge, Color accent) {
            this(title, sub, badge, accent, "");
        }
    }

    public static BufferedImage renderSmartphoneImage(HoloSession s) {
        BufferedImage img = new BufferedImage(PIXELS, PIXELS, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = img.createGraphics();
        configureQualityHints(g);
        g.scale(SCALE, SCALE);

        drawTitaniumChassis(g, SIZE);
        renderBackgroundWithGlassOverlay(g, 2, 2, SIZE - 4, SIZE - 4);
        drawStatusBarAndDynamicIsland(g, FONT_TINY);
        drawHeaderPill(g, s);
        drawNotificationBanner(g, s);
        drawCardsGrid(g, s);
        drawActionBar(g, s);
        drawDockAndHomeBar(g, s);
        drawMagneticReticle(g, s.cursorX, s.cursorY, SIZE);

        g.dispose();
        return img;
    }

    private static void drawHeaderPill(Graphics2D g, HoloSession s) {
        g.setPaint(new GradientPaint(3, 12, new Color(24, 36, 66, 218), 3, 25, new Color(14, 22, 42, 232)));
        g.fillRoundRect(3, 12, SIZE - 6, 13, 7, 7);
        g.setStroke(new BasicStroke(0.6f));
        g.setColor(new Color(56, 228, 255, 105));
        g.drawRoundRect(3, 12, SIZE - 6, 13, 7, 7);

        String title = (s.mode == HoloMode.COCKPIT) ? "AetherOS" : ("‹ " + modeTitle(s.mode));
        drawSoftText(g, title, 7f, 21f, WHITE_SOFT, FONT_TITLE);

        double bal = s.profile != null ? s.profile.coins : 1000.0;
        String balStr = (int) bal + "⛃";
        g.setColor(new Color(255, 212, 75, 32));
        g.fillRoundRect(52, 14, 33, 9, 4, 4);
        drawMarqueeText(g, balStr, 55, 21, 28, GOLD_SOFT, FONT_TINY);

        if (s.mode != HoloMode.COCKPIT) {
            g.setPaint(new GradientPaint(88, 14, new Color(36, 58, 108, 230), 88, 23, new Color(22, 36, 72, 230)));
            g.fillRoundRect(88, 14, 35, 9, 5, 5);
            g.setStroke(new BasicStroke(0.55f));
            g.setColor(new Color(255, 212, 75, 160));
            g.drawRoundRect(88, 14, 35, 9, 5, 5);
            drawMarqueeText(g, subButtonLabel(s), 91, 21, 29, WHITE_SOFT, FONT_TINY);
        } else {
            g.setColor(new Color(255, 105, 135, 35));
            g.fillRoundRect(88, 14, 35, 9, 5, 5);
            drawSoftText(g, "2026 PRO", 91.5f, 21f, ROSE_SOFT, FONT_TINY);
        }
    }

    private static void drawNotificationBanner(Graphics2D g, HoloSession s) {
        g.setColor(new Color(12, 18, 34, 165));
        g.fillRoundRect(4, 26, 120, 9, 5, 5);
        g.setStroke(new BasicStroke(0.45f));
        g.setColor(new Color(255, 255, 255, 28));
        g.drawRoundRect(4, 26, 120, 9, 5, 5);

        if (s.statusBanner != null && !s.statusBanner.isEmpty()) {
            drawMarqueeText(g, stripMcColors(s.statusBanner), 8, 33, 112, EMERALD_SOFT, FONT_SUB);
        } else if (s.mode == HoloMode.COCKPIT) {
            drawMarqueeText(g, "Visez une App • Clic G pour ouvrir", 8, 33, 112, MUTED_SOFT, FONT_SUB);
        } else {
            List<CardEntry> cards = buildCards(s);
            if (cards.size() > 6) {
                int p = (s.selectedIndex / 6) + 1;
                int totalP = (cards.size() + 5) / 6;
                drawMarqueeText(g, "Page " + p + "/" + totalP + " • Utilisez ◀ PRÉC / SUIV ▶", 8, 33, 112, CYAN_SOFT, FONT_SUB);
            } else {
                drawMarqueeText(g, "Clic D : ‹ Accueil • [F] : Changer filtre", 8, 33, 112, MUTED_SOFT, FONT_SUB);
            }
        }
    }

    private static void drawCardsGrid(Graphics2D g, HoloSession s) {
        List<CardEntry> cards = buildCards(s);
        int totalCards = Math.max(1, cards.size());
        if (s.selectedIndex >= totalCards) s.selectedIndex = totalCards - 1;

        int page = s.selectedIndex / 6;
        int totalPages = (totalCards + 5) / 6;
        int startIdx = page * 6;
        int countThisPage = Math.min(6, totalCards - startIdx);

        for (int i = 0; i < countThisPage; i++) {
            int actualIdx = startIdx + i;
            CardEntry c = cards.get(actualIdx);
            int cx = (i % 2 == 0) ? 4 : 65;
            int cy = 37 + (i / 2) * 21;
            boolean sel = (!s.dockFocused && actualIdx == s.selectedIndex);

            drawGlassCard(g, cx, cy, 59, 20, sel, sel ? GOLD_SOFT : c.accent());

            String ic = (c.icon() != null && !c.icon().isEmpty())
                    ? c.icon()
                    : (s.mode == HoloMode.COCKPIT ? c.badge() : (s.mode == HoloMode.LEADERBOARD ? "#" + (actualIdx + 1) : "✦"));
            drawSquircleIcon(g, cx + 3, cy + 3, 14, c.accent(), trimText(ic, 2), FONT_TINY);

            // Ligne 1 : Titre avec écriture déroulante automatique s'il dépasse la carte
            drawMarqueeText(g, c.title(), cx + 19, cy + 9, 37, sel ? GOLD_SOFT : WHITE_SOFT, FONT_TITLE);

            // Ligne 2 : Sous-titre / Prix avec écriture déroulante fluide
            if (s.mode == HoloMode.COCKPIT) {
                drawMarqueeText(g, c.sub(), cx + 19, cy + 16, 37, sel ? CYAN_SOFT : MUTED_SOFT, FONT_SUB);
            } else {
                String line2 = (c.sub() != null && !c.sub().isEmpty())
                        ? (c.badge() + " · " + c.sub())
                        : c.badge();
                drawMarqueeText(g, line2, cx + 19, cy + 16, 37, GOLD_SOFT, FONT_TINY);
            }
        }

        if (totalCards > 6) {
            g.setColor(new Color(12, 18, 34, 210));
            g.fillRoundRect(4, 102, 120, 9, 5, 5);
            if (page > 0) {
                g.setColor(new Color(26, 48, 86, 230));
                g.fillRoundRect(5, 103, 34, 7, 4, 4);
                g.setColor(CYAN_SOFT);
                g.drawRoundRect(5, 103, 34, 7, 4, 4);
                drawSoftText(g, "◀ PRÉC", 9f, 108.5f, CYAN_SOFT, FONT_TINY);
            }
            drawSoftText(g, "Page " + (page + 1) + "/" + totalPages, 47f, 108.5f, WHITE_SOFT, FONT_TINY);
            if (page < totalPages - 1) {
                g.setColor(new Color(78, 58, 18, 230));
                g.fillRoundRect(89, 103, 34, 7, 4, 4);
                g.setColor(GOLD_SOFT);
                g.drawRoundRect(89, 103, 34, 7, 4, 4);
                drawSoftText(g, "SUIV ▶", 93f, 108.5f, GOLD_SOFT, FONT_TINY);
            }
        }
    }

    private static void drawActionBar(Graphics2D g, HoloSession s) {
        if (buildCards(s).size() > 6) return;
        g.setPaint(new GradientPaint(4, 102, new Color(16, 62, 52, 215), 124, 111, new Color(12, 42, 58, 225)));
        g.fillRoundRect(4, 102, 120, 9, 5, 5);
        g.setStroke(new BasicStroke(0.55f));
        g.setColor(new Color(52, 232, 158, 140));
        g.drawRoundRect(4, 102, 120, 9, 5, 5);
        String act = (s.mode == HoloMode.COCKPIT) ? "OUVRIR L'APPLICATION" : primaryActionText(s.mode);
        drawMarqueeText(g, "▶ Clic G : " + act, 14, 108, 100, WHITE_SOFT, FONT_TINY);
    }

    private static void drawDockAndHomeBar(Graphics2D g, HoloSession s) {
        g.setPaint(new GradientPaint(3, 113, new Color(22, 30, 54, 225), 3, 125, new Color(12, 18, 34, 240)));
        g.fillRoundRect(3, 113, 122, 12, 7, 7);
        g.setStroke(new BasicStroke(0.55f));
        g.setColor(new Color(110, 145, 205, 95));
        g.drawRoundRect(3, 113, 122, 12, 7, 7);

        String[] labels = {"HOME", "SHOP", "PETS", "TOP", "PROF"};
        HoloMode[] modes = {HoloMode.COCKPIT, HoloMode.SHOP, HoloMode.PETS, HoloMode.LEADERBOARD, HoloMode.PROFILE};
        for (int i = 0; i < 5; i++) {
            int dx = 5 + i * 24;
            boolean active = (s.mode == modes[i]);
            boolean dockSel = (s.dockFocused && s.dockIndex == i);
            if (active || dockSel) {
                g.setColor(dockSel ? new Color(255, 212, 75, 55) : new Color(56, 228, 255, 42));
                g.fillRoundRect(dx, 114, 22, 7, 4, 4);
            }
            Color col = dockSel ? GOLD_SOFT : (active ? CYAN_SOFT : MUTED_SOFT);
            drawSoftText(g, labels[i], dx + 2.5f, 119.5f, col, FONT_TINY);
        }

        g.setColor(new Color(255, 255, 255, 195));
        g.fillRoundRect(46, 123, 36, 2, 2, 2);
    }

    public static boolean updatePointer(HoloSession s, double fx, double fy) {
        int nx = (int) Math.max(0, Math.min(SIZE - 1, Math.round(fx)));
        int ny = (int) Math.max(0, Math.min(SIZE - 1, Math.round(fy)));
        boolean changed = (nx != s.cursorX || ny != s.cursorY);
        s.cursorX = nx; s.cursorY = ny;

        if (ny >= 113) {
            int idx = Math.max(0, Math.min(4, (nx - 4) / 24));
            if (!s.dockFocused || s.dockIndex != idx) {
                s.dockFocused = true; s.dockIndex = idx; return true;
            }
            return changed;
        }
        int totalCards = Math.max(1, buildCards(s).size());
        if (totalCards > 6 && ny >= 101 && ny <= 112) {
            s.dockFocused = false;
            return changed;
        }
        s.dockFocused = false;
        int col = (nx < 64) ? 0 : 1;
        int row = (ny < 58) ? 0 : (ny < 79 ? 1 : 2);
        int page = s.selectedIndex / 6;
        int cardIdx = Math.min(page * 6 + row * 2 + col, totalCards - 1);
        if (s.selectedIndex != cardIdx) {
            s.selectedIndex = cardIdx;
            return true;
        }
        return changed;
    }

    public static void stepSelection(HoloSession s, int delta) {
        int count = Math.max(1, buildCards(s).size());
        int total = count + 5;
        int cur = s.dockFocused ? count + s.dockIndex : s.selectedIndex;
        cur = ((cur + delta) % total + total) % total;
        s.wheelMode = true;
        if (cur >= count) { s.dockFocused = true; s.dockIndex = cur - count; }
        else { s.dockFocused = false; s.selectedIndex = cur; }
        snapCursorToSelectedCard(s);
    }

    public static void snapCursorToSelectedCard(HoloSession s) {
        if (!s.wheelMode) return;
        if (s.dockFocused) {
            s.cursorX = 16 + s.dockIndex * 24; s.cursorY = 118;
        } else {
            int local = s.selectedIndex % 6;
            s.cursorX = (local % 2 == 0) ? 33 : 94;
            s.cursorY = 47 + (local / 2) * 21;
        }
    }

    public static void handleLeftClick(AetherHoloUIEngine engine, Player p, HoloSession s) {
        s.touchActivity();
        long now = System.currentTimeMillis();
        if (now - s.lastModeSwitchMillis < 250L) return;

        if (s.mode != HoloMode.COCKPIT && s.cursorY <= 25) {
            if (s.cursorX >= 85) cycleSubFilter(engine, p, s);
            else returnToHome(engine, p, s);
            return;
        }

        List<CardEntry> cards = buildCards(s);
        int totalCards = Math.max(1, cards.size());
        if (totalCards > 6 && s.cursorY >= 101 && s.cursorY <= 112) {
            int totalPages = (totalCards + 5) / 6;
            int curPage = s.selectedIndex / 6;
            if (s.cursorX >= 80 && curPage < totalPages - 1) {
                s.selectedIndex = Math.min((curPage + 1) * 6, totalCards - 1);
                s.wheelMode = true; snapCursorToSelectedCard(s);
                p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.6f);
                engine.pushPhoneFrame(p, s);
                return;
            } else if (s.cursorX <= 48 && curPage > 0) {
                s.selectedIndex = Math.max(0, (curPage - 1) * 6);
                s.wheelMode = true; snapCursorToSelectedCard(s);
                p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.4f);
                engine.pushPhoneFrame(p, s);
                return;
            }
        }

        if (s.mode != HoloMode.COCKPIT && s.cursorY >= 122) {
            returnToHome(engine, p, s);
            return;
        }

        if (s.dockFocused) {
            HoloMode[] modes = {HoloMode.COCKPIT, HoloMode.SHOP, HoloMode.PETS, HoloMode.LEADERBOARD, HoloMode.PROFILE};
            HoloMode target = modes[Math.max(0, Math.min(4, s.dockIndex))];
            if (s.mode != target) openAppMode(engine, p, s, target);
            return;
        }
        executePrimaryAction(engine, p, s);
    }

    public static void handleRightClickCycleMode(AetherHoloUIEngine engine, Player p, HoloSession s) {
        s.touchActivity();
        if (System.currentTimeMillis() - s.lastModeSwitchMillis < 250L) return;
        if (s.mode != HoloMode.COCKPIT) { returnToHome(engine, p, s); return; }
        p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.35f, 1.2f);
    }

    private static void returnToHome(AetherHoloUIEngine engine, Player p, HoloSession s) {
        s.mode = HoloMode.COCKPIT; s.dockIndex = 0; s.dockFocused = false; s.selectedIndex = 0;
        s.lastModeSwitchMillis = System.currentTimeMillis(); s.lastClickMillis = s.lastModeSwitchMillis;
        snapCursorToSelectedCard(s); engine.reloadSessionData(p, s);
        p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.7f, 1.6f);
        engine.pushPhoneFrame(p, s);
    }

    public static void cycleSubFilter(AetherHoloUIEngine engine, Player p, HoloSession s) {
        s.touchActivity();
        if (s.mode == HoloMode.SHOP) {
            String[] cats = {"all", "magots", "grades", "pets", "cosmetics", "keys", "boosters"};
            for (int i = 0; i < cats.length; i++) if (cats[i].equalsIgnoreCase(s.shopCategory)) { s.shopCategory = cats[(i + 1) % cats.length]; break; }
        } else if (s.mode == HoloMode.PROFILE) {
            s.profileSubTab = (s.profileSubTab == ProfileSubTab.QUESTS) ? ProfileSubTab.OVERVIEW_AND_ACHIEVEMENTS : ProfileSubTab.QUESTS;
        } else if (s.mode == HoloMode.LEADERBOARD) {
            String[] cats = {"oneblock", "fortune", "kills", "playtime"};
            for (int i = 0; i < cats.length; i++) if (cats[i].equalsIgnoreCase(s.leaderboardCategory)) { s.leaderboardCategory = cats[(i + 1) % cats.length]; break; }
        } else if (s.mode == HoloMode.PETS) {
            s.petsSubFilter = s.petsSubFilter.equalsIgnoreCase("familiers") ? "ferme" : "familiers";
        }
        s.selectedIndex = 0; snapCursorToSelectedCard(s); engine.reloadSessionData(p, s);
        p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.7f, 1.35f);
        engine.pushPhoneFrame(p, s);
    }

    private static void executePrimaryAction(AetherHoloUIEngine engine, Player p, HoloSession s) {
        switch (s.mode) {
            case COCKPIT -> {
                HoloMode[] appModes = {HoloMode.SHOP, HoloMode.PETS, HoloMode.LEADERBOARD, HoloMode.MARKET, HoloMode.ORES, HoloMode.PROFILE};
                if (s.selectedIndex >= 0 && s.selectedIndex < appModes.length) openAppMode(engine, p, s, appModes[s.selectedIndex]);
                else if (s.selectedIndex == 6) { engine.closeSession(p.getUniqueId(), false); Bukkit.dispatchCommand(p, "banque"); }
                else { engine.closeSession(p.getUniqueId(), false); Bukkit.dispatchCommand(p, "spawn"); }
            }
            case SHOP -> { if (s.selectedIndex < s.shopItems.size()) finishTx(engine, p, s, engine.getTxService().buyShopItem(p, s.shopItems.get(s.selectedIndex)).message); }
            case PETS -> { if (s.selectedIndex < s.animalItems.size()) finishTx(engine, p, s, engine.getTxService().buyShopItem(p, s.animalItems.get(s.selectedIndex)).message); }
            case LEADERBOARD -> {
                if (s.selectedIndex < s.leaderboardEntries.size()) {
                    var e = s.leaderboardEntries.get(s.selectedIndex);
                    p.sendMessage("§6✦ [CLASSEMENT #" + (s.selectedIndex + 1) + "] §b" + e.username + " §e(" + e.rankId + ") : §a" + (int) e.value + " " + s.leaderboardCategory.toUpperCase(Locale.ROOT));
                    p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.4f);
                }
            }
            case MARKET -> { if (s.selectedIndex < s.marketItems.size()) finishTx(engine, p, s, engine.getTxService().buyMarketListing(p, s.marketItems.get(s.selectedIndex)).message); }
            case ORES -> { if (s.selectedIndex < s.oreItems.size()) finishTx(engine, p, s, engine.getTxService().sellPlayerOres(p, s.oreItems.get(s.selectedIndex)).message); }
            case PROFILE -> { if (s.profileSubTab == ProfileSubTab.QUESTS && s.selectedIndex < s.quests.size()) finishTx(engine, p, s, engine.getTxService().claimOrProgressQuest(p, s.quests.get(s.selectedIndex)).message); }
        }
    }

    private static void finishTx(AetherHoloUIEngine engine, Player p, HoloSession s, String msg) {
        s.statusBanner = msg; p.sendMessage(msg); engine.reloadSessionData(p, s); engine.pushPhoneFrame(p, s);
    }

    private static void openAppMode(AetherHoloUIEngine engine, Player p, HoloSession s, HoloMode targetMode) {
        s.mode = targetMode; s.dockIndex = Math.min(4, Math.max(0, targetMode.ordinal()));
        s.dockFocused = false; s.selectedIndex = 0;
        s.lastModeSwitchMillis = System.currentTimeMillis(); s.lastClickMillis = s.lastModeSwitchMillis;
        snapCursorToSelectedCard(s); engine.reloadSessionData(p, s);
        p.playSound(p.getLocation(), Sound.BLOCK_AMETHYST_BLOCK_CHIME, 0.85f, 1.5f);
        engine.pushPhoneFrame(p, s);
    }

    public static List<CardEntry> buildCards(HoloSession s) {
        List<CardEntry> list = new ArrayList<>();
        switch (s.mode) {
            case COCKPIT -> {
                list.add(new CardEntry("Boutique", "Cosmétiques & Clés", "🛒", EMERALD_SOFT));
                list.add(new CardEntry("Animaux", "Familiers & Ferme", "🐾", new Color(120, 220, 140)));
                list.add(new CardEntry("Classement", "Top Joueurs", "🏆", GOLD_SOFT));
                list.add(new CardEntry("Hôtel Ventes", "Échanges Joueurs", "⚖", new Color(255, 185, 65)));
                list.add(new CardEntry("Bourse", "Cours des Minerais", "💎", CYAN_SOFT));
                list.add(new CardEntry("Profil", "Quêtes & Succès", "👤", new Color(180, 130, 255)));
                list.add(new CardEntry("Banque", "Coffre Privé", "🏦", new Color(255, 155, 70)));
                list.add(new CardEntry("Agora", "Spawn Céleste", "🪐", CYAN_SOFT));
            }
            case LEADERBOARD -> {
                String unit = switch (s.leaderboardCategory.toLowerCase(Locale.ROOT)) { case "fortune" -> "⛃"; case "kills" -> "⚔"; case "playtime" -> "h"; default -> "⛏"; };
                for (int i = 0; i < s.leaderboardEntries.size(); i++) {
                    var e = s.leaderboardEntries.get(i);
                    Color col = (i == 0) ? GOLD_SOFT : (i == 1 ? CYAN_SOFT : (i == 2 ? new Color(235, 145, 75) : EMERALD_SOFT));
                    String prefix = (e.prefix != null && !e.prefix.isEmpty()) ? stripMcColors(e.prefix).trim() : e.rankId;
                    list.add(new CardEntry("#" + (i + 1) + " " + e.username, prefix, (int) e.value + unit, col));
                }
                if (list.isEmpty()) list.add(new CardEntry("Aucun rang", "En attente...", "🏆", GOLD_SOFT));
            }
            case PETS -> {
                for (ShopItemData it : s.animalItems) {
                    String priceTxt = (it.pricePoints > 0) ? (it.pricePoints * 10) + "⛃" : (int) it.priceEur + "⛃";
                    Color c = it.id.startsWith("animal_") ? new Color(130, 215, 125) : new Color(255, 155, 215);
                    list.add(new CardEntry(it.name, it.category.equalsIgnoreCase("pets") ? "3D" : "Ferme", priceTxt, c, "🐾"));
                }
                if (list.isEmpty()) list.add(new CardEntry("Animalerie", "Vide", "🐾", MUTED_SOFT, "🐾"));
            }
            case SHOP -> { for (ShopItemData it : s.shopItems) list.add(new CardEntry(it.name, it.category, (it.pricePoints * 10) + "⛃", EMERALD_SOFT, "🛒")); }
            case MARKET -> { for (MarketListingData m : s.marketItems) list.add(new CardEntry(m.itemName, m.seller, (int) m.priceCoins + "⛃", GOLD_SOFT, "⚖")); }
            case ORES -> { for (OreData o : s.oreItems) list.add(new CardEntry(o.name, "V:" + o.totalTraded, String.format(Locale.US, "%.0f⛃", o.price), CYAN_SOFT, "💎")); }
            case PROFILE -> {
                if (s.profileSubTab == ProfileSubTab.QUESTS) for (QuestData q : s.quests) list.add(new CardEntry(q.title, q.status, "+" + (int) (q.rewardCoins + q.rewardPoints * 10) + "⛃", EMERALD_SOFT));
                else for (AchievementData a : s.achievements) list.add(new CardEntry(a.title, a.unlocked ? "Débloqué" : "Verrouillé", a.unlocked ? "✔ OK" : "🔒", GOLD_SOFT));
            }
        }
        return list;
    }

    private static String modeTitle(HoloMode m) {
        return switch (m) { case COCKPIT -> "Hub"; case SHOP -> "Boutique"; case MARKET -> "HDV"; case ORES -> "Bourse"; case PROFILE -> "Profil"; case LEADERBOARD -> "Top"; case PETS -> "Animaux"; };
    }

    private static String subButtonLabel(HoloSession s) {
        return switch (s.mode) {
            case SHOP -> "F:" + s.shopCategory.toUpperCase(Locale.ROOT);
            case PROFILE -> s.profileSubTab == ProfileSubTab.QUESTS ? "F:QUÊTES" : "F:SUCCÈS";
            case LEADERBOARD -> "F:" + s.leaderboardCategory.toUpperCase(Locale.ROOT);
            case PETS -> s.petsSubFilter.equalsIgnoreCase("ferme") ? "F:FERME" : "F:FAMIL.";
            default -> "F:FILTRE";
        };
    }

    private static String primaryActionText(HoloMode m) {
        return switch (m) { case COCKPIT -> "OUVRIR APP"; case SHOP, MARKET, PETS -> "ACHETER"; case ORES -> "VENDRE LOT"; case PROFILE -> "RÉCLAMER"; case LEADERBOARD -> "VOIR RANG"; };
    }

    private static String stripMcColors(String s) { return s == null ? "" : s.replaceAll("§[0-9a-fk-orA-FK-OR]", ""); }
    private static String trimText(String s, int max) { return s == null ? "" : (s.length() <= max ? s : s.substring(0, max)); }
}
