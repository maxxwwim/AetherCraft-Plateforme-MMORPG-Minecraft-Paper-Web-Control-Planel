package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.io.File;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.*;

/**
 * Interface de la Bourse des Minerais & Admin Shop (Comptoir de l'Agora).
 */
public class AetherOresGUI implements Listener {

    public static final String TITLE = ChatColor.DARK_GRAY + "[" + ChatColor.DARK_GREEN + "" + ChatColor.BOLD + "BOURSE DES MINERAIS" + ChatColor.DARK_GRAY + " • " + ChatColor.GOLD + "AGORA" + ChatColor.DARK_GRAY + "]";
    private final AetherVisualsPlugin plugin;

    public AetherOresGUI(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    private File getDatabaseFile() {
        return AetherDatabase.getDatabaseFile();
    }

    public void openOresShop(Player player) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.ORES, null);
            return;
        }
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            Map<String, OreInfo> ores = loadOres();
            Bukkit.getScheduler().runTask(plugin, () -> {
                Inventory inv = Bukkit.createInventory(null, 45, TITLE);
                ItemStack cadreVert = createPane(Material.LIME_STAINED_GLASS_PANE, ChatColor.GREEN + "✦ Comptoir Officiel ✦");
                ItemStack cadreObs = createPane(Material.BLACK_STAINED_GLASS_PANE, ChatColor.DARK_GRAY + "✦ Coffre de l'Agora ✦");
                int[] borders = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 26, 27, 35, 36, 37, 38, 39, 41, 42, 43, 44};
                for (int i = 0; i < borders.length; i++) {
                    inv.setItem(borders[i], (i % 2 == 0) ? cadreVert : cadreObs);
                }
                inv.setItem(40, createIcon(Material.BARRIER, ChatColor.RED + "" + ChatColor.BOLD + "✖ FERMER", ChatColor.GRAY + "Quitter la Bourse"));
                String[] oreKeys = {"coal", "copper", "iron", "gold", "lapis", "diamond", "netherite", "aetherite"};
                int[] slots = {11, 12, 13, 14, 15, 20, 21, 22};
                for (int i = 0; i < oreKeys.length && i < slots.length; i++) {
                    String k = oreKeys[i];
                    inv.setItem(slots[i], createOreItem(ores.getOrDefault(k, new OreInfo(k, k, 10.0, 0))));
                }
                player.openInventory(inv);
                player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 1.0f, 1.2f);
            });
        });
    }

    private Map<String, OreInfo> loadOres() {
        Map<String, OreInfo> map = new LinkedHashMap<>();
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT id, name, current_price, total_traded FROM ores_market;");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                map.put(rs.getString("id"), new OreInfo(
                        rs.getString("id"), rs.getString("name"),
                        rs.getDouble("current_price"), rs.getInt("total_traded")));
            }
        } catch (Exception e) {
            plugin.getLogger().warning("[Ores] Erreur lecture minerais : " + e.getMessage());
        }
        return map;
    }

    private ItemStack createOreItem(OreInfo info) {
        ItemStack item = new ItemStack(getMaterialForOre(info.id));
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + info.name);
            meta.setLore(Arrays.asList(
                    ChatColor.DARK_GRAY + "ID : " + info.id, "",
                    ChatColor.WHITE + "✦ Cours Unité : " + ChatColor.GOLD + String.format("%.1f", info.price) + " ⛁ Coins",
                    ChatColor.WHITE + "✦ Volume Échangé : " + ChatColor.AQUA + info.totalTraded + " u", "",
                    ChatColor.GREEN + "▶ Clic-gauche pour VENDRE tous vos minerais",
                    ChatColor.GRAY + "Alimente également la jauge de coopération !"));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
        }
        return item;
    }

    private Material getMaterialForOre(String id) {
        return switch (id) {
            case "coal" -> Material.COAL;
            case "copper" -> Material.RAW_COPPER;
            case "iron" -> Material.RAW_IRON;
            case "gold" -> Material.RAW_GOLD;
            case "lapis" -> Material.LAPIS_LAZULI;
            case "diamond" -> Material.DIAMOND;
            case "netherite" -> Material.NETHERITE_INGOT;
            case "aetherite" -> Material.ECHO_SHARD;
            default -> Material.PRISMARINE_SHARD;
        };
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (event.getView() == null || !TITLE.equals(event.getView().getTitle())) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) return;
        ItemStack clicked = event.getCurrentItem();
        if (clicked == null || !clicked.hasItemMeta() || clicked.getItemMeta().getLore() == null) return;
        if (event.getRawSlot() == 40) {
            player.closeInventory();
            player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 1.0f, 1.0f);
            return;
        }
        for (String line : clicked.getItemMeta().getLore()) {
            if (line.contains("ID : ")) {
                sellOres(player, ChatColor.stripColor(line).replace("ID : ", "").trim());
                break;
            }
        }
    }

    private void sellOres(Player player, String oreId) {
        Material targetMat = getMaterialForOre(oreId);
        Material altMat = (targetMat == Material.RAW_COPPER) ? Material.COPPER_INGOT
                : (targetMat == Material.RAW_IRON) ? Material.IRON_INGOT
                : (targetMat == Material.RAW_GOLD) ? Material.GOLD_INGOT : null;

        int totalCount = 0;
        for (ItemStack item : player.getInventory().getContents()) {
            if (item != null && (item.getType() == targetMat || item.getType() == altMat)) {
                totalCount += item.getAmount();
            }
        }
        if (totalCount <= 0) {
            player.sendMessage(ChatColor.RED + "❌ Vous n'avez aucun minerai de ce type dans votre inventaire !");
            player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
            return;
        }

        int toRemove = totalCount;
        for (int i = 0; i < player.getInventory().getSize() && toRemove > 0; i++) {
            ItemStack item = player.getInventory().getItem(i);
            if (item != null && (item.getType() == targetMat || item.getType() == altMat)) {
                int amt = item.getAmount();
                if (amt <= toRemove) {
                    player.getInventory().setItem(i, null);
                    toRemove -= amt;
                } else {
                    item.setAmount(amt - toRemove);
                    toRemove = 0;
                }
            }
        }

        final int soldCount = totalCount;
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection()) {
                conn.setAutoCommit(false);
                double price = 10.0;
                try (PreparedStatement ps = conn.prepareStatement("SELECT current_price FROM ores_market WHERE id = ?;")) {
                    ps.setString(1, oreId);
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) price = rs.getDouble("current_price");
                    }
                }
                double totalEarnings = soldCount * price;
                try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);")) {
                    ps.setDouble(1, totalEarnings);
                    ps.setString(2, player.getName());
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = conn.prepareStatement("UPDATE ores_market SET total_traded = total_traded + ? WHERE id = ?;")) {
                    ps.setInt(1, soldCount);
                    ps.setString(2, oreId);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = conn.prepareStatement("UPDATE community_goals SET current_amount = MIN(target_amount, current_amount + ?) WHERE id = 's4_celestial_tree';")) {
                    ps.setInt(1, soldCount);
                    ps.executeUpdate();
                }
                conn.commit();
                Bukkit.getScheduler().runTask(plugin, () -> {
                    player.playSound(player.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1.0f, 1.4f);
                    player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_PLING, 1.0f, 2.0f);
                    player.sendMessage(ChatColor.GREEN + "✦ " + ChatColor.WHITE + "Vente de " + ChatColor.YELLOW +
                            soldCount + "x minerais " + ChatColor.WHITE + "effectuée : " + ChatColor.GOLD + "+" +
                            String.format("%.1f", totalEarnings) + " Aether Coins §fcrédités !");
                    openOresShop(player);
                });
            } catch (Exception e) {
                plugin.getLogger().warning("[Ores] Erreur vente : " + e.getMessage());
            }
        });
    }

    private ItemStack createPane(Material mat, String name) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            item.setItemMeta(meta);
        }
        return item;
    }

    private ItemStack createIcon(Material mat, String title, String... lore) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(title);
            meta.setLore(Arrays.asList(lore));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static class OreInfo {
        public final String id;
        public final String name;
        public final double price;
        public final int totalTraded;

        public OreInfo(String id, String name, double price, int totalTraded) {
            this.id = id;
            this.name = name;
            this.price = price;
            this.totalTraded = totalTraded;
        }
    }
}
