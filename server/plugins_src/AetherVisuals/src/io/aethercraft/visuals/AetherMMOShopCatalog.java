package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Catalogue d'articles, constructeurs d'icônes et accès SQLite pour AetherMMOInterfaceEngine.
 */
public class AetherMMOShopCatalog {

    public static class ShopCard {
        public final String id;
        public final String title;
        public final String category;
        public final int pricePoints;
        public final Material material;
        public final int customModelData;
        public final String description;

        public ShopCard(String id, String title, String category, int pricePoints, Material mat, int cmd, String desc) {
            this.id = id;
            this.title = title;
            this.category = category;
            this.pricePoints = pricePoints;
            this.material = mat;
            this.customModelData = cmd;
            this.description = desc;
        }
    }

    public static List<ShopCard> getShopCards(String category) {
        List<ShopCard> all = new ArrayList<>();
        all.add(new ShopCard("rank_vip", "👑 Couronne VIP Céleste", "ranks", 50, Material.GOLDEN_HELMET, 1001, "Prefixe VIP, Aura Émeraude & Accès Prioritaire"));
        all.add(new ShopCard("rank_titan", "🔥 Cimier du Titan Déchaîné", "ranks", 120, Material.NETHERITE_HELMET, 1002, "Halo de flammes, double hélice & XP x2"));
        all.add(new ShopCard("key_celestial", "🗝️ Clé Céleste des Étoiles", "keys", 25, Material.TRIPWIRE_HOOK, 2001, "Déverrouille la Caisse Céleste à l'Agora"));
        all.add(new ShopCard("key_omega", "🗝️ Clé Oméga Suprême", "keys", 80, Material.TRIPWIRE_HOOK, 2002, "Tirage Légendaire garanti dans la Caisse Oméga"));
        all.add(new ShopCard("quantum_wings", "🪽 Ailes Quantiques Stellaires", "cosmetics", 150, Material.FEATHER, 3001, "Particules de vol éthéré 3D & traînées célestes"));
        all.add(new ShopCard("pet_dragon", "🐾 Familier Dragoneau Céleste", "pets", 180, Material.DRAGON_BREATH, 4001, "Compagnon volant 3D cracheur d'étincelles"));
        all.add(new ShopCard("pet_phoenix", "🐾 Familier Phénix des Cendres", "pets", 160, Material.BLAZE_POWDER, 4002, "Aura de réincarnation & braises solaires"));
        all.add(new ShopCard("pet_capybara", "🐾 Familier Capybara Zen", "pets", 90, Material.TURTLE_HELMET, 4003, "Aura de sérénité & cœurs d'abondance"));
        all.add(new ShopCard("booster_mining", "⚡ Booster de Minage x2 (2h)", "boosters", 30, Material.GOLDEN_PICKAXE, 5001, "Double tous les drops de minerais pendant 2h"));

        if (category.equals("all")) return all;
        List<ShopCard> filtered = new ArrayList<>();
        for (ShopCard c : all) {
            if (c.category.equals(category)) filtered.add(c);
        }
        return filtered;
    }

    public static void deliverPurchasedItem(AetherVisualsPlugin plugin, Player player, String itemId) {
        switch (itemId) {
            case "rank_vip" -> {
                plugin.getCosmeticsEngine().setAura(player.getUniqueId(), "vip");
                player.sendMessage(ChatColor.GOLD + "👑 Rang VIP & Aura Émeraude activés !");
            }
            case "rank_titan" -> {
                plugin.getCosmeticsEngine().setAura(player.getUniqueId(), "titan");
                player.sendMessage(ChatColor.RED + "🔥 Cimier du Titan & Double Flamme activés !");
            }
            case "key_celestial" -> player.getInventory().addItem(CustomItemFactory.createCelestialKey(1));
            case "key_omega" -> player.getInventory().addItem(CustomItemFactory.createOmegaKey(1));
            case "quantum_wings" -> {
                plugin.getCosmeticsEngine().setWings(player.getUniqueId(), true);
                player.sendMessage(ChatColor.DARK_PURPLE + "🪽 Ailes Quantiques activées !");
            }
            case "pet_dragon" -> {
                plugin.getCosmeticsEngine().setPet(player.getUniqueId(), "dragon");
                player.sendMessage(ChatColor.AQUA + "🐾 Dragoneau Céleste invoqué à vos côtés !");
            }
            case "pet_phoenix" -> {
                plugin.getCosmeticsEngine().setPet(player.getUniqueId(), "phoenix");
                player.sendMessage(ChatColor.GOLD + "🐾 Phénix des Cendres invoqué !");
            }
            case "pet_capybara" -> {
                plugin.getCosmeticsEngine().setPet(player.getUniqueId(), "capybara");
                player.sendMessage(ChatColor.GREEN + "🐾 Capybara Zen invoqué !");
            }
            case "booster_mining" -> {
                plugin.getBoosterEngine().addMiningBooster(player.getUniqueId(), 2 * 3600);
                player.sendMessage(ChatColor.GREEN + "⚡ Booster de Minage x2 actif pour 2 heures !");
            }
        }
    }

    public static ItemStack createShopCardItem(ShopCard card, int playerPoints) {
        ItemStack item = new ItemStack(card.material);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + card.title);
            if (card.customModelData > 0) meta.setCustomModelData(card.customModelData);
            boolean canAfford = playerPoints >= card.pricePoints;
            String priceTag = canAfford ? (ChatColor.GREEN + "Prix : " + card.pricePoints + " ✪ Points") : (ChatColor.RED + "Prix : " + card.pricePoints + " ✪ Points (Insuffisant)");
            String actionTag = canAfford ? (ChatColor.YELLOW + "▶ Clic Gauche : Acheter Immédiatement") : (ChatColor.GRAY + "Rechargez sur http://127.0.0.1:5000/boutique");
            meta.setLore(Arrays.asList(
                    ChatColor.DARK_GRAY + "────────────────────────────",
                    ChatColor.GRAY + card.description,
                    ChatColor.DARK_GRAY + "────────────────────────────",
                    priceTag, "", actionTag
            ));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ADDITIONAL_TOOLTIP);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createTabItem(String label, boolean active) {
        ItemStack item = new ItemStack(active ? Material.LIME_STAINED_GLASS_PANE : Material.GRAY_STAINED_GLASS_PANE);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(active ? (ChatColor.GREEN + "" + ChatColor.BOLD + "● " + label + " ●") : (ChatColor.GRAY + label));
            meta.setLore(Collections.singletonList(ChatColor.DARK_GRAY + "Cliquez pour filtrer"));
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createBorderItem() {
        ItemStack item = new ItemStack(Material.GRAY_STAINED_GLASS_PANE);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.DARK_GRAY + "•");
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createMMOItem(Material mat, String name, List<String> lore, int cmd) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            meta.setLore(lore);
            if (cmd > 0) meta.setCustomModelData(cmd);
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ADDITIONAL_TOOLTIP);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static String buildProgressBar(int pct) {
        int total = 20;
        int filled = (int) Math.round((pct / 100.0) * total);
        StringBuilder sb = new StringBuilder(ChatColor.GREEN + "[");
        for (int i = 0; i < total; i++) {
            if (i < filled) sb.append("█");
            else if (i == filled) sb.append(ChatColor.DARK_GRAY).append("░");
            else sb.append("░");
        }
        return sb.append(ChatColor.GREEN).append("] ").append(ChatColor.YELLOW).append(pct).append("%").toString();
    }

    public static int getPlayerCoins(String username) {
        if (username == null || username.trim().isEmpty()) return 0;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT balance FROM players WHERE LOWER(username) = LOWER(?)")) {
            ps.setString(1, username.trim());
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return (int) rs.getDouble("balance");
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    public static int getPlayerPoints(String username) {
        if (username == null || username.trim().isEmpty()) return 0;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
            ps.setString(1, username.trim());
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return rs.getInt("shop_points");
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    public static boolean deductPlayerPoints(String username, int amount) {
        if (username == null || username.trim().isEmpty() || amount <= 0) return false;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("UPDATE users SET shop_points = shop_points - ? WHERE LOWER(minecraft_username) = LOWER(?) AND shop_points >= ?")) {
            ps.setInt(1, amount);
            ps.setString(2, username.trim());
            ps.setInt(3, amount);
            return ps.executeUpdate() > 0;
        } catch (Throwable ignored) {}
        return false;
    }

    public static int getCommunityGauge() {
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT current_amount FROM community_goals WHERE id = 's4_celestial_tree'");
             ResultSet rs = ps.executeQuery()) {
            if (rs.next()) return rs.getInt("current_amount");
        } catch (Throwable ignored) {}
        return 0;
    }
}
