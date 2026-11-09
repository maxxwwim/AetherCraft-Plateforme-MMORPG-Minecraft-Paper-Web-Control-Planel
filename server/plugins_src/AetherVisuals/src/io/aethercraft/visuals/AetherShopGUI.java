package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.Particle;
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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * Interface Graphique In-Game Haute Fidélité de la Boutique Officielle AetherCraft.
 */
public class AetherShopGUI implements Listener {

    public static final String TITLE_PREFIX = ChatColor.DARK_GRAY + "[" + ChatColor.GOLD + "" + ChatColor.BOLD + "BOUTIQUE CÉLESTE" + ChatColor.DARK_GRAY + " • ";

    private final AetherVisualsPlugin plugin;
    private AetherOresGUI oresGUI;
    private AetherMarketGUI marketGUI;
    private AetherMenuGUI menuGUI;
    private final Map<UUID, String> playerCategoryMap = new ConcurrentHashMap<>();

    public AetherShopGUI(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public void setEngines(AetherOresGUI oresGUI, AetherMarketGUI marketGUI, AetherMenuGUI menuGUI) {
        this.oresGUI = oresGUI;
        this.marketGUI = marketGUI;
        this.menuGUI = menuGUI;
    }

    public void openShop(Player player) {
        openShopCategory(player, playerCategoryMap.getOrDefault(player.getUniqueId(), "all"));
    }

    public void openShopCategory(Player player, String category) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.SHOP, category);
            return;
        }
        playerCategoryMap.put(player.getUniqueId(), category);

        getPlayerBalance(player, balance -> {
            String invTitle = TITLE_PREFIX + getCategoryTitle(category) + ChatColor.DARK_GRAY + "]";
            Inventory inv = Bukkit.createInventory(null, 54, invTitle);

            inv.setItem(0, createTabItem(Material.GOLD_INGOT, category.equals("magots"), ChatColor.GOLD + "" + ChatColor.BOLD + "🧈 MAGOTS & LINGOTS HABBO", ChatColor.GRAY + "Blocs & Lingots convertibles en Pièces ⛃"));
            inv.setItem(1, createTabItem(Material.GOLDEN_HELMET, category.equals("ranks"), ChatColor.GOLD + "" + ChatColor.BOLD + "👑 RANGS VIP", ChatColor.GRAY + "Grades VIP, Aether, Titan, Champion"));
            inv.setItem(2, createTabItem(Material.TRIPWIRE_HOOK, category.equals("keys"), ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🗝️ CLÉS & CAISSES", ChatColor.GRAY + "Clés Célestes & Clés Oméga Suprêmes"));
            inv.setItem(3, createTabItem(Material.FEATHER, category.equals("cosmetics"), ChatColor.AQUA + "" + ChatColor.BOLD + "🪽 COSMÉTIQUES", ChatColor.GRAY + "Ailes Quantiques & Auras Divines"));
            inv.setItem(4, createTabItem(Material.MAGMA_CREAM, category.equals("pets"), ChatColor.GREEN + "" + ChatColor.BOLD + "🐾 FAMILIERS CÉLESTES", ChatColor.GRAY + "Dragons, Capybaras, Renards & Phénix"));
            inv.setItem(5, createTabItem(Material.NETHER_STAR, category.equals("all"), ChatColor.YELLOW + "" + ChatColor.BOLD + "⭐ TOUT LE CATALOGUE", ChatColor.GRAY + "Voir l'ensemble des articles boutique"));

            inv.setItem(6, createMenuItem(Material.EMERALD_BLOCK, ChatColor.GREEN + "" + ChatColor.BOLD + "⛏️ BOURSE DES MINERAIS", ChatColor.GREEN + "▶ Clic pour ouvrir (/marche ores)"));
            inv.setItem(7, createMenuItem(Material.ENDER_CHEST, ChatColor.GOLD + "" + ChatColor.BOLD + "🤝 HÔTEL DES VENTES", ChatColor.GOLD + "▶ Clic pour ouvrir (/marche)"));
            inv.setItem(8, createBalanceItem(balance));

            ItemStack paneCyan = createPane(Material.CYAN_STAINED_GLASS_PANE, ChatColor.AQUA + "✦ AetherCraft ✦");
            ItemStack panePurple = createPane(Material.PURPLE_STAINED_GLASS_PANE, ChatColor.LIGHT_PURPLE + "✦ Comptoir Stellaire ✦");
            for (int s = 9; s <= 17; s++) inv.setItem(s, (s % 2 == 0) ? paneCyan : panePurple);

            populateCategoryItems(inv, category, balance);

            inv.setItem(45, createMenuItem(Material.FILLED_MAP, ChatColor.AQUA + "" + ChatColor.BOLD + "🌐 BOUTIQUE EN LIGNE & JETONS", ChatColor.YELLOW + "▶ Clic pour recevoir le lien web"));
            inv.setItem(47, createMenuItem(Material.COMPASS, ChatColor.YELLOW + "" + ChatColor.BOLD + "🧭 MENU CENTRAL", ChatColor.YELLOW + "▶ Clic pour ouvrir (/menu)"));
            inv.setItem(49, createMenuItem(Material.BEACON, ChatColor.AQUA + "" + ChatColor.BOLD + "🪐 SPAWN AGORA (Y=120)", ChatColor.AQUA + "▶ Clic pour se téléporter (/spawn)"));
            inv.setItem(51, createMenuItem(Material.GRASS_BLOCK, ChatColor.GREEN + "" + ChatColor.BOLD + "🌲 MONDE SURVIE (Plaines)", ChatColor.GREEN + "▶ Clic pour se téléporter (/survie)"));
            inv.setItem(53, createMenuItem(Material.BARRIER, ChatColor.RED + "" + ChatColor.BOLD + "❌ FERMER", ChatColor.GRAY + "Quitter le menu boutique"));

            player.openInventory(inv);
            player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 0.9f, 1.3f);
        });
    }

    private String getCategoryTitle(String cat) {
        return switch (cat) {
            case "ranks" -> ChatColor.GOLD + "Rangs VIP";
            case "keys" -> ChatColor.LIGHT_PURPLE + "Clés & Caisses";
            case "cosmetics" -> ChatColor.AQUA + "Cosmétiques";
            case "pets" -> ChatColor.GREEN + "Familiers";
            case "boosters" -> ChatColor.RED + "Boosters";
            default -> ChatColor.YELLOW + "Catalogue Général";
        };
    }

    private void populateCategoryItems(Inventory inv, String cat, double balance) {
        List<ShopArticle> articles = AetherShopCatalog.getArticlesForCategory(plugin, cat);
        int[] slots = {19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 33, 34, 37, 38, 39, 40, 41, 42, 43};
        for (int i = 0; i < articles.size() && i < slots.length; i++) {
            inv.setItem(slots[i], articles.get(i).buildItem(balance));
        }
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (event.getView() == null || event.getView().getTitle() == null) return;
        if (!event.getView().getTitle().startsWith(TITLE_PREFIX)) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) return;

        int slot = event.getRawSlot();
        if (slot >= 0 && slot <= 5) {
            String[] cats = {"magots", "ranks", "keys", "cosmetics", "pets", "all"};
            player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.2f);
            openShopCategory(player, cats[slot]);
            return;
        }
        switch (slot) {
            case 6 -> { player.closeInventory(); if (oresGUI != null) oresGUI.openOresShop(player); else player.performCommand("marche ores"); return; }
            case 7 -> { player.closeInventory(); if (marketGUI != null) marketGUI.openMarket(player); else player.performCommand("marche"); return; }
            case 8 -> { player.playSound(player.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1.0f, 1.0f); player.sendMessage(ChatColor.GOLD + "✦ Utilisez /marche ores pour gagner des Coins !"); return; }
            case 45 -> { player.closeInventory(); player.sendMessage(ChatColor.AQUA + "👑 Boutique Web : " + ChatColor.WHITE + "http://127.0.0.1:5000/boutique"); return; }
            case 47 -> { player.closeInventory(); if (menuGUI != null) menuGUI.openMenu(player); else player.performCommand("menu"); return; }
            case 49 -> { player.closeInventory(); if (plugin.getPortalEngine() != null) plugin.getPortalEngine().teleportToHub(player); else player.performCommand("spawn"); return; }
            case 51 -> { player.closeInventory(); if (plugin.getPortalEngine() != null) plugin.getPortalEngine().teleportToSurvival(player); else player.performCommand("survie"); return; }
            case 53 -> { player.closeInventory(); player.playSound(player.getLocation(), Sound.BLOCK_CHEST_CLOSE, 0.8f, 1.2f); return; }
        }

        ItemStack clickedItem = event.getCurrentItem();
        if (clickedItem == null || clickedItem.getType() == Material.AIR) return;
        ShopArticle matchedArticle = AetherShopCatalog.findArticleByItem(plugin, clickedItem);
        if (matchedArticle != null) handlePurchase(player, matchedArticle);
    }

    private void handlePurchase(Player player, ShopArticle article) {
        getPlayerBalance(player, balance -> {
            if (balance < article.priceCoins) {
                player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                player.sendMessage(ChatColor.RED + "❌ Solde insuffisant pour acheter " + article.displayName + " !");
                return;
            }
            Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                boolean success = false;
                try (Connection conn = AetherDatabase.getConnection()) {
                    conn.setAutoCommit(false);
                    try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?) AND balance >= ?;")) {
                        ps.setDouble(1, article.priceCoins);
                        ps.setString(2, player.getName());
                        ps.setDouble(3, article.priceCoins);
                        if (ps.executeUpdate() > 0) {
                            success = true;
                            try (PreparedStatement psOrder = conn.prepareStatement(
                                    "INSERT INTO store_orders (order_id, username, total, currency, items_json, status, rcon_executed, created_at) VALUES (?, ?, ?, 'COINS', ?, 'LIVRE', 1, datetime('now'));")) {
                                psOrder.setString(1, "ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
                                psOrder.setString(2, player.getName());
                                psOrder.setDouble(3, article.priceCoins);
                                psOrder.setString(4, "[{\"id\":\"" + article.id + "\",\"name\":\"" + ChatColor.stripColor(article.displayName) + "\"}]");
                                psOrder.executeUpdate();
                            }
                            conn.commit();
                        } else conn.rollback();
                    } catch (Exception ex) { conn.rollback(); }
                } catch (Exception ignored) {}

                final boolean finalSuccess = success;
                Bukkit.getScheduler().runTask(plugin, () -> {
                    if (finalSuccess) {
                        article.deliver(player, plugin);
                        player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
                        player.spawnParticle(Particle.TOTEM_OF_UNDYING, player.getLocation().add(0, 1.2, 0), 35, 0.4, 0.6, 0.4, 0.1);
                        player.sendMessage(ChatColor.GREEN + "✔ COMMANDE VALIDÉE : " + article.displayName);
                        openShopCategory(player, playerCategoryMap.getOrDefault(player.getUniqueId(), "all"));
                    } else {
                        player.sendMessage(ChatColor.RED + "❌ Échec de la transaction.");
                    }
                });
            });
        });
    }

    private void getPlayerBalance(Player player, Consumer<Double> callback) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            double bal = 1000.0;
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);")) {
                ps.setString(1, player.getName());
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) bal = rs.getDouble("balance"); }
            } catch (Exception ignored) {}
            final double finalBal = bal;
            Bukkit.getScheduler().runTask(plugin, () -> callback.accept(finalBal));
        });
    }

    private ItemStack createTabItem(Material mat, boolean isSelected, String name, String desc) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName((isSelected ? ChatColor.GREEN + "▶ " : "") + name);
            meta.setLore(Arrays.asList(isSelected ? ChatColor.GREEN + "● CATÉGORIE SÉLECTIONNÉE" : ChatColor.DARK_GRAY + "Onglet du catalogue", "", desc, ChatColor.YELLOW + "▶ Clic pour filtrer"));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ENCHANTS);
            item.setItemMeta(meta);
        }
        return item;
    }

    private ItemStack createBalanceItem(double balance) {
        return createMenuItem(Material.GOLD_BLOCK, ChatColor.GOLD + "" + ChatColor.BOLD + "⛁ VOTRE SOLDE : " + ChatColor.YELLOW + String.format("%.0f", balance) + " COINS",
                ChatColor.DARK_GRAY + "Porte-monnaie joueur officiel", ChatColor.AQUA + "▶ Clic pour actualiser votre solde");
    }

    private ItemStack createPane(Material material, String name) {
        return createMenuItem(material, name);
    }

    private ItemStack createMenuItem(Material material, String name, String... loreLines) {
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            if (loreLines.length > 0) meta.setLore(Arrays.asList(loreLines));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ENCHANTS);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static class ShopArticle {
        public final String id;
        public final String category;
        public final String displayName;
        public final double priceCoins;
        public final ItemStack baseIcon;
        public final ArticleDeliverer deliverer;

        public ShopArticle(String id, String category, String displayName, double priceCoins, ItemStack baseIcon, ArticleDeliverer deliverer) {
            this.id = id;
            this.category = category;
            this.displayName = displayName;
            this.priceCoins = priceCoins;
            this.baseIcon = baseIcon;
            this.deliverer = deliverer;
        }

        public ItemStack buildItem(double currentBalance) {
            ItemStack item = baseIcon.clone();
            ItemMeta meta = item.getItemMeta();
            if (meta != null) {
                meta.setDisplayName(displayName);
                List<String> lore = meta.hasLore() ? new ArrayList<>(meta.getLore()) : new ArrayList<>();
                lore.add("");
                lore.add(ChatColor.GOLD + "⛁ Prix Boutique : " + ChatColor.YELLOW + String.format("%.0f", priceCoins) + " Aether Coins");
                lore.add(currentBalance >= priceCoins ? ChatColor.GREEN + "▶ Clic GAUCHE pour ACHETER" : ChatColor.RED + "❌ Coins insuffisants");
                meta.setLore(lore);
                meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ENCHANTS);
                item.setItemMeta(meta);
            }
            return item;
        }

        public void deliver(Player player, AetherVisualsPlugin plugin) {
            if (deliverer != null) deliverer.deliver(player, plugin);
        }
    }

    @FunctionalInterface
    public interface ArticleDeliverer {
        void deliver(Player player, AetherVisualsPlugin plugin);
    }
}
