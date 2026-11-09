package io.aethercraft.visuals;

import net.md_5.bungee.api.ChatColor;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.ClickEvent;
import net.md_5.bungee.api.chat.ComponentBuilder;
import net.md_5.bungee.api.chat.HoverEvent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.List;

/**
 * Moteur d'Affichage Plein Écran Haute-Fidélité MMORPG.
 * Remplace l'inventaire coffre standard par un véritable Grimoire Céleste interactif (Book GUI)
 * et une console HUD dynamique avec composants cliquables.
 */
public class MMORPGDisplayEngine {

    private final AetherVisualsPlugin plugin;
    private final AetherMenuGUI legacyMenuGUI;
    private final AetherShopGUI legacyShopGUI;

    public MMORPGDisplayEngine(AetherVisualsPlugin plugin, AetherMenuGUI legacyMenuGUI, AetherShopGUI legacyShopGUI) {
        this.plugin = plugin;
        this.legacyMenuGUI = legacyMenuGUI;
        this.legacyShopGUI = legacyShopGUI;
    }

    /**
     * Ouvre le Grimoire MMORPG Plein Écran (Zéro Grille d'Inventaire, Zéro Coffre).
     */
    public void openMenu(Player player) {
        // Sons immersifs d'ouverture de codex MMORPG
        player.playSound(player.getLocation(), Sound.ITEM_BOOK_PAGE_TURN, 1.0f, 0.9f);
        player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 0.5f, 1.4f);

        // Chargement des statistiques du joueur
        int coins = getPlayerCoins(player.getName());
        int points = getPlayerPoints(player.getName());
        int gauge = getCommunityGauge();

        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        if (meta == null) return;

        meta.setTitle("Grimoire AetherCraft");
        meta.setAuthor("Arbre Primordial");

        // --- PAGE 1 : COCKPIT JOUEUR MMORPG ---
        List<BaseComponent> page1 = new ArrayList<>();
        page1.add(new TextComponent(ChatColor.DARK_GREEN + "  ✦ " + ChatColor.BOLD + "AETHERCRAFT" + ChatColor.DARK_GREEN + " ✦\n"));
        page1.add(new TextComponent(ChatColor.DARK_GRAY + "  ── Codex Primordial ──\n\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Aventurier: " + ChatColor.DARK_GREEN + ChatColor.BOLD + player.getName() + "\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Or: " + ChatColor.GOLD + coins + " ⛁" + ChatColor.BLACK + " | Éther: " + ChatColor.AQUA + points + " ✪\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Arbre Céleste: " + ChatColor.DARK_GREEN + gauge + " / 50k\n\n"));

        page1.add(createClickableBtn("🪐 [ AGORA CÉLESTE ]", "/spawn", "Téléportation instantanée à l'Archipel Céleste (Y=120)", ChatColor.DARK_AQUA));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("🌱 [ REPRENDRE SURVIE ]", "/survie", "Reprendre à votre dernière position de survie", ChatColor.DARK_GREEN));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("🔙 [ RETOUR /BACK ]", "/back", "Retourner à votre dernier emplacement ou mort", ChatColor.DARK_PURPLE));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("🌀 [ RITUEL RTP ]", "/rtp", "Téléportation aléatoire sécurisée sur terre ferme", ChatColor.BLUE));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("⚔️ [ DONJON D'ÉTHER ]", "/dungeon", "Défiez les 5 vagues du Sanctuaire de l'Aetherite", ChatColor.RED));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("🛍️ [ BOUTIQUE ]", "/shop", "Consulter les cosmétiques, rangs et familiers", ChatColor.GOLD));
        page1.add(new TextComponent("\n"));
        page1.add(createClickableBtn("⚖️ [ MARCHÉ & BOURSE ]", "/marche", "Hôtel des ventes et cotation des minerais", ChatColor.DARK_BLUE));

        meta.spigot().addPage(page1.toArray(new BaseComponent[0]));

        // --- PAGE 2 : TÉLÉPORTATIONS & INFORMATIONS SERVEUR ---
        List<BaseComponent> page2 = new ArrayList<>();
        page2.add(new TextComponent(ChatColor.DARK_AQUA + "  ✦ " + ChatColor.BOLD + "VOIES D'EXPLORATION" + ChatColor.DARK_AQUA + " ✦\n"));
        page2.add(new TextComponent(ChatColor.DARK_GRAY + "  ────────────────\n\n"));
        page2.add(new TextComponent(ChatColor.BLACK + "Explorez les dimensions de l'Archipel Primordial :\n\n"));

        page2.add(createClickableBtn("🐾 [ MES FAMILIERS ]", "/pet", "Invoquer Dragoneau, Capybara, Renard ou Phénix", ChatColor.DARK_GREEN));
        page2.add(new TextComponent("\n\n"));
        page2.add(createClickableBtn("🪽 [ MES AURAS & AILES ]", "/aura", "Activer ou changer votre aura particulaire", ChatColor.BLUE));
        page2.add(new TextComponent("\n\n"));
        page2.add(createClickableBtn("❓ [ QUIZ TRIVIA ]", "/quiz", "Participez au Quiz Céleste pour gagner des jetons", ChatColor.DARK_PURPLE));
        page2.add(new TextComponent("\n\n"));
        page2.add(createClickableBtn("📦 [ VUE INVENTAIRE GUI ]", "/menu gui", "Basculer vers l'interface coffre 54-slots", ChatColor.GRAY));

        meta.spigot().addPage(page2.toArray(new BaseComponent[0]));

        book.setItemMeta(meta);
        player.openBook(book);

        // Alerte visuelle et sonore d'accompagnement
        player.sendTitle(org.bukkit.ChatColor.GREEN + "✦ COCKPIT MMORPG ✦", org.bukkit.ChatColor.GOLD + "Grimoire Céleste Plein Écran Ouvert", 5, 35, 10);
    }

    /**
     * Ouvre la Boutique Céleste en Grimoire Plein Écran (Zéro Coffre).
     */
    public void openShop(Player player) {
        player.playSound(player.getLocation(), Sound.ITEM_BOOK_PAGE_TURN, 1.0f, 1.1f);
        player.playSound(player.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 0.4f, 1.8f);

        int points = getPlayerPoints(player.getName());

        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        if (meta == null) return;

        meta.setTitle("Boutique Céleste");
        meta.setAuthor("Agora d'Aether");

        // PAGE 1 : RANGS & CLÉS
        List<BaseComponent> page1 = new ArrayList<>();
        page1.add(new TextComponent(ChatColor.GOLD + " ✦ " + ChatColor.BOLD + "BOUTIQUE CÉLESTE" + ChatColor.GOLD + " ✦\n"));
        page1.add(new TextComponent(ChatColor.DARK_GRAY + " Solde: " + ChatColor.AQUA + points + " ✪ Points\n\n"));

        page1.add(new TextComponent(ChatColor.DARK_GREEN + "👑 " + ChatColor.BOLD + "Rang VIP Céleste\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Prefixe VIP, Aura Émeraude\n"));
        page1.add(createClickableBtn("  [ 🛒 Acheter • 50 ✪ ]", "/store buy rank_vip", "Cliquez pour obtenir le rang VIP", ChatColor.GOLD));
        page1.add(new TextComponent("\n\n"));

        page1.add(new TextComponent(ChatColor.DARK_RED + "🔥 " + ChatColor.BOLD + "Cimier du Titan\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Halo Flammes & XP x2\n"));
        page1.add(createClickableBtn("  [ 🛒 Acheter • 120 ✪ ]", "/store buy rank_titan", "Cliquez pour obtenir le rang Titan", ChatColor.RED));
        page1.add(new TextComponent("\n\n"));

        page1.add(new TextComponent(ChatColor.DARK_AQUA + "🗝️ " + ChatColor.BOLD + "Clé Céleste Lootbox\n"));
        page1.add(new TextComponent(ChatColor.BLACK + "Débloque la caisse de l'Agora\n"));
        page1.add(createClickableBtn("  [ 🛒 Acheter • 25 ✪ ]", "/store buy key_celestial", "Obtenir 1 Clé Céleste", ChatColor.AQUA));

        meta.spigot().addPage(page1.toArray(new BaseComponent[0]));

        // PAGE 2 : COSMÉTIQUES & FAMILIERS
        List<BaseComponent> page2 = new ArrayList<>();
        page2.add(new TextComponent(ChatColor.BLUE + " ✦ " + ChatColor.BOLD + "COSMÉTIQUES & PETS" + ChatColor.BLUE + " ✦\n\n"));

        page2.add(new TextComponent(ChatColor.DARK_PURPLE + "🪽 " + ChatColor.BOLD + "Ailes Quantiques\n"));
        page2.add(new TextComponent(ChatColor.BLACK + "Vol éthéré particulaire 3D\n"));
        page2.add(createClickableBtn("  [ 🛒 Acheter • 150 ✪ ]", "/store buy quantum_wings", "Débloquer les Ailes Quantiques", ChatColor.DARK_PURPLE));
        page2.add(new TextComponent("\n\n"));

        page2.add(new TextComponent(ChatColor.DARK_BLUE + "🐾 " + ChatColor.BOLD + "Dragoneau Céleste\n"));
        page2.add(new TextComponent(ChatColor.BLACK + "Familier volant cracheur d'étincelles\n"));
        page2.add(createClickableBtn("  [ 🛒 Acheter • 180 ✪ ]", "/store buy pet_dragon", "Adopter le Dragoneau Céleste", ChatColor.DARK_AQUA));
        page2.add(new TextComponent("\n\n"));

        page2.add(new TextComponent(ChatColor.DARK_GREEN + "⚡ " + ChatColor.BOLD + "Booster Minage x2 (2h)\n"));
        page2.add(new TextComponent(ChatColor.BLACK + "Double tous les drops de minerais\n"));
        page2.add(createClickableBtn("  [ 🛒 Acheter • 30 ✪ ]", "/store buy booster_mining", "Activer Booster x2", ChatColor.GREEN));

        meta.spigot().addPage(page2.toArray(new BaseComponent[0]));

        book.setItemMeta(meta);
        player.openBook(book);

        player.sendTitle(org.bukkit.ChatColor.GOLD + "🛍️ BOUTIQUE CÉLESTE", org.bukkit.ChatColor.AQUA + "Catalogue Plein Écran Ouvert", 5, 35, 10);
    }

    private TextComponent createClickableBtn(String text, String command, String hoverText, ChatColor color) {
        TextComponent btn = new TextComponent(text);
        btn.setColor(color);
        btn.setBold(true);
        btn.setClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND, command));
        btn.setHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT, new ComponentBuilder(hoverText).color(ChatColor.YELLOW).create()));
        return btn;
    }

    private int getPlayerCoins(String username) {
        if (username == null || username.trim().isEmpty()) return 0;
        try (Connection conn = AetherDatabase.getConnection()) {
            String sql = "SELECT balance FROM players WHERE LOWER(username) = LOWER(?)";
            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setString(1, username.trim());
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) return (int) rs.getDouble("balance");
                }
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    private int getPlayerPoints(String username) {
        if (username == null || username.trim().isEmpty()) return 0;
        try (Connection conn = AetherDatabase.getConnection()) {
            String sql = "SELECT shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?)";
            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setString(1, username.trim());
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) return rs.getInt("shop_points");
                }
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    private int getCommunityGauge() {
        try (Connection conn = AetherDatabase.getConnection()) {
            String sql = "SELECT current_amount FROM community_goals WHERE id = 's4_celestial_tree'";
            try (PreparedStatement ps = conn.prepareStatement(sql);
                 ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return rs.getInt("current_amount");
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    public AetherMenuGUI getLegacyMenuGUI() {
        return legacyMenuGUI;
    }

    public AetherShopGUI getLegacyShopGUI() {
        return legacyShopGUI;
    }
}
