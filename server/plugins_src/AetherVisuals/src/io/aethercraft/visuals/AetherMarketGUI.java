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

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.*;

/**
 * Interface & Gestionnaire Réel de l'Hôtel des Ventes (L'Encan d'Éther).
 */
public class AetherMarketGUI implements Listener {

    public static final String TITLE = ChatColor.DARK_GRAY + "[" + ChatColor.GOLD + "" + ChatColor.BOLD + "HÔTEL DES VENTES" + ChatColor.DARK_GRAY + " • " + ChatColor.GREEN + "ÉTHER" + ChatColor.DARK_GRAY + "]";
    private final AetherVisualsPlugin plugin;

    public AetherMarketGUI(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public void openMarket(Player player) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.MARKET, null);
            return;
        }
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            List<MarketListing> listings = loadActiveListings();
            Bukkit.getScheduler().runTask(plugin, () -> {
                Inventory inv = Bukkit.createInventory(null, 54, TITLE);
                ItemStack cadreOr = createPane(Material.YELLOW_STAINED_GLASS_PANE, ChatColor.GOLD + "✦ Comptoir de l'Encan ✦");
                ItemStack cadreObs = createPane(Material.BLACK_STAINED_GLASS_PANE, ChatColor.DARK_GRAY + "✦ Coffre Scellé ✦");

                int[] borders = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 26, 27, 35, 36, 44, 45, 46, 47, 48, 50, 51, 52, 53};
                for (int i = 0; i < borders.length; i++) inv.setItem(borders[i], (i % 2 == 0) ? cadreOr : cadreObs);

                inv.setItem(4, createIcon(Material.GOLD_INGOT, ChatColor.GOLD + "" + ChatColor.BOLD + "📜 COMMENT METTRE EN VENTE ?",
                        ChatColor.DARK_GRAY + "Système de Vente Sécurisé", "",
                        ChatColor.WHITE + "Prenez un objet dans votre main principale et tapez :",
                        ChatColor.YELLOW + "  /marche sell <prix>", ChatColor.GRAY + "Exemple : /marche sell 500", "",
                        ChatColor.GREEN + "✦ Visible en jeu (/ah) et sur le site (http://.../marche)"));
                inv.setItem(49, createIcon(Material.BARRIER, ChatColor.RED + "" + ChatColor.BOLD + "✖ FERMER", ChatColor.GRAY + "Quitter l'Hôtel des Ventes"));

                int[] innerSlots = {10, 11, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 33, 34, 37, 38, 39, 40, 41, 42, 43};
                for (int i = 0; i < listings.size() && i < innerSlots.length; i++) {
                    inv.setItem(innerSlots[i], createListingItem(listings.get(i)));
                }
                player.openInventory(inv);
                player.playSound(player.getLocation(), Sound.BLOCK_CHEST_OPEN, 1.0f, 1.2f);
            });
        });
    }

    private List<MarketListing> loadActiveListings() {
        List<MarketListing> list = new ArrayList<>();
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT id, seller_username, item_name, quantity, price_coins, status FROM player_market_listings WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 28;");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                list.add(new MarketListing(rs.getString("id"), rs.getString("seller_username"),
                        rs.getString("item_name"), rs.getInt("quantity"),
                        rs.getDouble("price_coins"), rs.getString("status")));
            }
        } catch (Exception e) {
            plugin.getLogger().warning("[Market] Erreur lecture listings : " + e.getMessage());
        }
        return list;
    }

    private ItemStack createListingItem(MarketListing l) {
        ItemStack item = new ItemStack(resolveMaterial(l.itemName), Math.max(1, Math.min(64, l.quantity)));
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + l.itemName + ChatColor.YELLOW + " (x" + l.quantity + ")");
            meta.setLore(Arrays.asList(
                    ChatColor.DARK_GRAY + "Annonce #" + l.id, "",
                    ChatColor.WHITE + "✦ Vendeur : " + ChatColor.AQUA + l.sellerUsername,
                    ChatColor.WHITE + "✦ Prix : " + ChatColor.GOLD + String.format("%.0f", l.priceCoins) + " ⛁ Coins",
                    ChatColor.WHITE + "✦ Quantité : " + ChatColor.GREEN + "x" + l.quantity, "",
                    ChatColor.GREEN + "▶ Clic-gauche pour ACHETER cet objet"));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
        }
        return item;
    }

    private Material resolveMaterial(String name) {
        String lower = name.toLowerCase(Locale.ROOT);
        if (lower.contains("diamant") || lower.contains("diamond")) return Material.DIAMOND;
        if (lower.contains("netherite")) return Material.NETHERITE_INGOT;
        if (lower.contains("pioche") || lower.contains("pickaxe")) return Material.DIAMOND_PICKAXE;
        if (lower.contains("elytre") || lower.contains("élytre") || lower.contains("ailes")) return Material.ELYTRA;
        if (lower.contains("capybara") || lower.contains("pet") || lower.contains("dragon")) return Material.ALLAY_SPAWN_EGG;
        if (lower.contains("epee") || lower.contains("épée") || lower.contains("sword")) return Material.NETHERITE_SWORD;
        if (lower.contains("or") || lower.contains("gold")) return Material.GOLD_INGOT;
        if (lower.contains("fer") || lower.contains("iron")) return Material.IRON_INGOT;
        if (lower.contains("lapis")) return Material.LAPIS_LAZULI;
        return Material.ENDER_CHEST;
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (event.getView() == null || !TITLE.equals(event.getView().getTitle())) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player buyer)) return;
        ItemStack clicked = event.getCurrentItem();
        if (clicked == null || !clicked.hasItemMeta() || clicked.getItemMeta().getLore() == null) return;
        if (event.getRawSlot() == 49) {
            buyer.closeInventory();
            buyer.playSound(buyer.getLocation(), Sound.UI_BUTTON_CLICK, 1.0f, 1.0f);
            return;
        }
        for (String line : clicked.getItemMeta().getLore()) {
            if (line.contains("Annonce #")) {
                processPurchase(buyer, ChatColor.stripColor(line).replace("Annonce #", "").trim());
                break;
            }
        }
    }

    private void processPurchase(Player buyer, String listingId) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection()) {
                conn.setAutoCommit(false);
                String seller = null, itemName = null, status = null;
                int quantity = 1;
                double price = 0.0;

                try (PreparedStatement ps = conn.prepareStatement("SELECT seller_username, item_name, quantity, price_coins, status FROM player_market_listings WHERE id = ?;")) {
                    ps.setString(1, listingId);
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) {
                            seller = rs.getString("seller_username"); itemName = rs.getString("item_name");
                            quantity = rs.getInt("quantity"); price = rs.getDouble("price_coins"); status = rs.getString("status");
                        }
                    }
                }
                if (seller == null || !"ACTIVE".equalsIgnoreCase(status)) { notifyPlayer(buyer, ChatColor.RED + "❌ Cet objet n'est plus disponible."); conn.rollback(); return; }
                if (seller.equalsIgnoreCase(buyer.getName())) { notifyPlayer(buyer, ChatColor.RED + "❌ Vous ne pouvez pas acheter votre propre mise en vente !"); conn.rollback(); return; }

                double buyerBalance = 0.0;
                try (PreparedStatement ps = conn.prepareStatement("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);")) {
                    ps.setString(1, buyer.getName());
                    try (ResultSet rs = ps.executeQuery()) { if (rs.next()) buyerBalance = rs.getDouble("balance"); }
                }
                if (buyerBalance < price) {
                    notifyPlayer(buyer, ChatColor.RED + "❌ Solde insuffisant ! Vous avez " + String.format("%.0f", buyerBalance) + " Coins, il vous faut " + String.format("%.0f", price) + " Coins.");
                    conn.rollback(); return;
                }
                try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?);")) {
                    ps.setDouble(1, price); ps.setString(2, buyer.getName()); ps.executeUpdate();
                }
                try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?);")) {
                    ps.setDouble(1, price); ps.setString(2, seller); ps.executeUpdate();
                }
                try (PreparedStatement ps = conn.prepareStatement("UPDATE player_market_listings SET status = 'SOLD' WHERE id = ?;")) {
                    ps.setString(1, listingId); ps.executeUpdate();
                }
                conn.commit();

                final String fItemName = itemName, fSeller = seller;
                final int fQty = quantity;
                final double fPrice = price;
                Bukkit.getScheduler().runTask(plugin, () -> {
                    ItemStack purchased = new ItemStack(resolveMaterial(fItemName), Math.max(1, Math.min(64, fQty)));
                    ItemMeta im = purchased.getItemMeta();
                    if (im != null) { im.setDisplayName(ChatColor.GOLD + fItemName); purchased.setItemMeta(im); }
                    buyer.getInventory().addItem(purchased);
                    buyer.playSound(buyer.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
                    buyer.sendMessage(ChatColor.GREEN + "✦ Achat réussi ! Vous avez reçu " + ChatColor.YELLOW + fItemName + " (x" + fQty + ") pour " + ChatColor.GOLD + String.format("%.0f", fPrice) + " Coins.");
                    Bukkit.broadcastMessage("§8[§6★ ENCAN D'ÉTHER ★§8] §e" + buyer.getName() + " §fa acheté §b" + fItemName + " §fà §a" + fSeller + " §fpour §6" + String.format("%.0f", fPrice) + " ⛁ Coins §f!");
                    openMarket(buyer);
                });
            } catch (Exception e) {
                plugin.getLogger().warning("[Market] Erreur transaction : " + e.getMessage());
                notifyPlayer(buyer, ChatColor.RED + "❌ Erreur de transaction financière.");
            }
        });
    }

    public boolean sellItem(Player player, double price) {
        ItemStack inHand = player.getInventory().getItemInMainHand();
        if (inHand.getType() == Material.AIR) { player.sendMessage(ChatColor.RED + "❌ Tenez l'objet à vendre dans votre main principale."); return true; }
        if (price <= 0) { player.sendMessage(ChatColor.RED + "❌ Le prix doit être supérieur à 0."); return true; }
        String itemName = inHand.hasItemMeta() && inHand.getItemMeta().hasDisplayName()
                ? ChatColor.stripColor(inHand.getItemMeta().getDisplayName()) : formatName(inHand.getType().name());
        int quantity = inHand.getAmount();
        String listId = "list_" + UUID.randomUUID().toString().substring(0, 8);
        player.getInventory().setItemInMainHand(null);

        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                         "INSERT INTO player_market_listings (id, seller_username, item_name, item_icon, quantity, price_coins, is_troc, created_at, status) VALUES (?, ?, ?, '📦', ?, ?, 0, datetime('now'), 'ACTIVE');")) {
                ps.setString(1, listId); ps.setString(2, player.getName()); ps.setString(3, itemName);
                ps.setInt(4, quantity); ps.setDouble(5, price); ps.executeUpdate();
                Bukkit.getScheduler().runTask(plugin, () -> {
                    player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_BELL, 1.0f, 1.5f);
                    player.sendMessage(ChatColor.GREEN + "✦ Objet mis en vente à l'Encan d'Éther !");
                    Bukkit.broadcastMessage("§8[§6★ ENCAN D'ÉTHER ★§8] §e" + player.getName() + " §fa mis en vente §b" + itemName + " (x" + quantity + ") §fpour §6" + String.format("%.0f", price) + " ⛁ Coins §f! Tapez §a/ah §f!");
                });
            } catch (Exception e) {
                plugin.getLogger().warning("[Market] Erreur insertion vente : " + e.getMessage());
            }
        });
        return true;
    }

    private String formatName(String raw) {
        StringBuilder sb = new StringBuilder();
        for (String p : raw.toLowerCase().split("_")) if (!p.isEmpty()) sb.append(Character.toUpperCase(p.charAt(0))).append(p.substring(1)).append(" ");
        return sb.toString().trim();
    }

    private void notifyPlayer(Player p, String msg) {
        Bukkit.getScheduler().runTask(plugin, () -> { p.sendMessage(msg); p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f); });
    }

    private ItemStack createPane(Material mat, String name) { return createIcon(mat, name); }

    private ItemStack createIcon(Material mat, String title, String... lore) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(title);
            if (lore.length > 0) meta.setLore(Arrays.asList(lore));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static class MarketListing {
        public final String id, sellerUsername, itemName, status;
        public final int quantity;
        public final double priceCoins;
        public MarketListing(String id, String sellerUsername, String itemName, int quantity, double priceCoins, String status) {
            this.id = id; this.sellerUsername = sellerUsername; this.itemName = itemName;
            this.quantity = quantity; this.priceCoins = priceCoins; this.status = status;
        }
    }
}
