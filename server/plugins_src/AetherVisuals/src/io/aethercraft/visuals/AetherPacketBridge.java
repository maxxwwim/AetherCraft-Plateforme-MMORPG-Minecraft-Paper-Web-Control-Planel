package io.aethercraft.visuals;

import com.google.common.io.ByteArrayDataInput;
import com.google.common.io.ByteArrayDataOutput;
import com.google.common.io.ByteStreams;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.messaging.PluginMessageListener;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Locale;

/**
 * Passerelle Réseau Serveur pour le Mod Client Fabric 1.21.1 AetherCraft.
 * Gère la communication bidirectionnelle entre le serveur Paper et les clients moddés :
 * Déclenchement des écrans MMORPG natifs, synchronisation des soldes et validation des achats.
 */
public class AetherPacketBridge implements PluginMessageListener {

    public static final String CHANNEL_OPEN_SHOP = "aether:open_shop";
    public static final String CHANNEL_OPEN_MENU = "aether:open_menu";
    public static final String CHANNEL_OPEN_CRATE = "aether:open_crate";
    public static final String CHANNEL_SYNC_DATA = "aether:sync_data";
    public static final String CHANNEL_BUY_ITEM = "aether:buy_item";
    public static final String CHANNEL_USE_KEY = "aether:use_key";
    public static final String CHANNEL_HELLO = "aether:hello";

    private final AetherVisualsPlugin plugin;
    private final CrateEngine crateEngine;
    private final java.util.Set<java.util.UUID> moddedPlayers = java.util.concurrent.ConcurrentHashMap.newKeySet();

    public AetherPacketBridge(AetherVisualsPlugin plugin, CrateEngine crateEngine) {
        this.plugin = plugin;
        this.crateEngine = crateEngine;
    }

    public boolean isModdedClient(Player player) {
        return player != null && moddedPlayers.contains(player.getUniqueId());
    }

    public void registerChannels() {
        // Canaux Sortants (Serveur -> Client)
        plugin.getServer().getMessenger().registerOutgoingPluginChannel(plugin, CHANNEL_OPEN_SHOP);
        plugin.getServer().getMessenger().registerOutgoingPluginChannel(plugin, CHANNEL_OPEN_MENU);
        plugin.getServer().getMessenger().registerOutgoingPluginChannel(plugin, CHANNEL_OPEN_CRATE);
        plugin.getServer().getMessenger().registerOutgoingPluginChannel(plugin, CHANNEL_SYNC_DATA);

        // Canaux Entrants (Client -> Serveur)
        plugin.getServer().getMessenger().registerIncomingPluginChannel(plugin, CHANNEL_BUY_ITEM, this);
        plugin.getServer().getMessenger().registerIncomingPluginChannel(plugin, CHANNEL_USE_KEY, this);
        plugin.getServer().getMessenger().registerIncomingPluginChannel(plugin, CHANNEL_HELLO, this);
    }

    public void openClientShop(Player player) {
        try {
            player.sendPluginMessage(plugin, CHANNEL_OPEN_SHOP, new byte[0]);
        } catch (Throwable ignored) {}
    }

    public void openClientMenu(Player player) {
        try {
            player.sendPluginMessage(plugin, CHANNEL_OPEN_MENU, new byte[0]);
        } catch (Throwable ignored) {}
    }

    public void openClientCrate(Player player) {
        try {
            player.sendPluginMessage(plugin, CHANNEL_OPEN_CRATE, new byte[0]);
        } catch (Throwable ignored) {}
    }

    public void syncPlayerData(Player player, int points, int coins, String rank) {
        try {
            ByteArrayDataOutput out = ByteStreams.newDataOutput();
            out.writeInt(points);
            out.writeInt(coins);
            out.writeUTF(rank != null ? rank : "Aventurier");
            player.sendPluginMessage(plugin, CHANNEL_SYNC_DATA, out.toByteArray());
        } catch (Throwable ignored) {}
    }

    @Override
    public void onPluginMessageReceived(String channel, Player player, byte[] message) {
        if (player != null) {
            moddedPlayers.add(player.getUniqueId());
        }
        if (channel.equalsIgnoreCase(CHANNEL_HELLO)) {
            return;
        }
        ByteArrayDataInput in = ByteStreams.newDataInput(message);

        if (channel.equalsIgnoreCase(CHANNEL_BUY_ITEM)) {
            String itemId = in.readUTF();
            boolean payWithPoints = in.readBoolean();
            handleBuyRequest(player, itemId, payWithPoints);
        } else if (channel.equalsIgnoreCase(CHANNEL_USE_KEY)) {
            boolean isOmega = in.readBoolean();
            handleUseKeyRequest(player, isOmega);
        }
    }

    private void handleUseKeyRequest(Player player, boolean isOmega) {
        Bukkit.getScheduler().runTask(plugin, () -> {
            crateEngine.startOpeningAnimation(player, isOmega ? "omega" : "celestial", false);
        });
    }

    private void handleBuyRequest(Player player, String itemId, boolean payWithPoints) {
        if (player == null || itemId == null || itemId.trim().isEmpty()) {
            return;
        }
        final String rawItemId = itemId.trim();

        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            String resolvedId = rawItemId;
            String category = "items";
            String itemName = rawItemId;
            int pricePoints = 100;
            double costCoins = 1000.0;

            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                         "SELECT id, category, name, price_points FROM store_items WHERE is_active = 1")) {
                try (ResultSet rs = ps.executeQuery()) {
                    boolean found = false;
                    while (rs.next()) {
                        String dbId = rs.getString("id");
                        if (dbId.equalsIgnoreCase(rawItemId) || rawItemId.equalsIgnoreCase(dbId.replace("rank_", "").replace("cosmetic_", "").replace("key_", "").replace("pet_", "").replace("booster_", ""))) {
                            resolvedId = dbId;
                            category = rs.getString("category");
                            itemName = rs.getString("name");
                            pricePoints = rs.getInt("price_points");
                            costCoins = Math.max(1, pricePoints) * 10.0;
                            found = true;
                            break;
                        }
                    }
                    if (!found) {
                        String low = rawItemId.toLowerCase(Locale.ROOT);
                        if (low.contains("vip")) {
                            resolvedId = "rank_vip"; category = "grades"; itemName = "Grade VIP"; pricePoints = 500; costCoins = 5000.0;
                        } else if (low.contains("titan")) {
                            resolvedId = "rank_titan"; category = "grades"; itemName = "Grade Titan Primordial"; pricePoints = 3000; costCoins = 30000.0;
                        } else if (low.contains("aether") && low.contains("rank")) {
                            resolvedId = "rank_aether"; category = "grades"; itemName = "Grade Aether (Héros)"; pricePoints = 1500; costCoins = 15000.0;
                        } else if (low.contains("champion") && low.contains("rank")) {
                            resolvedId = "rank_champion"; category = "grades"; itemName = "Grade Champion du Royaume"; pricePoints = 5000; costCoins = 50000.0;
                        } else if (low.contains("wings")) {
                            resolvedId = "cosmetic_wings"; category = "cosmetics"; itemName = "Ailes Quantiques Stellaires"; pricePoints = 200; costCoins = 2000.0;
                        } else if (low.contains("celestial") || low.contains("mystic")) {
                            resolvedId = "key_mystic_bundle"; category = "keys"; itemName = "Pack 5x Clés Célestes"; pricePoints = 150; costCoins = 1500.0;
                        } else if (low.contains("omega")) {
                            resolvedId = "key_omega_bundle"; category = "keys"; itemName = "Pack 12x Clés Oméga (Max)"; pricePoints = 300; costCoins = 3000.0;
                        } else if (low.contains("booster")) {
                            resolvedId = "booster_mining"; category = "boosters"; itemName = "Booster de Minage Céleste (x2)"; pricePoints = 120; costCoins = 1200.0;
                        } else if (low.contains("dragon")) {
                            resolvedId = "pet_dragon"; category = "pets"; itemName = "Mini Dragon Stellaire"; pricePoints = 250; costCoins = 2500.0;
                        } else {
                            costCoins = Math.max(1, pricePoints) * 10.0;
                        }
                    }
                }
            } catch (SQLException e) {
                plugin.getLogger().warning("[AetherPacketBridge] Erreur consultation store_items: " + e.getMessage());
            }

            int currentPoints = 0;
            double currentCoins = 0.0;
            int userId = -1;

            try (Connection conn = AetherDatabase.getConnection()) {
                try (PreparedStatement ps = conn.prepareStatement(
                        "SELECT balance FROM players WHERE LOWER(username) = LOWER(?)")) {
                    ps.setString(1, player.getName());
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) {
                            currentCoins = rs.getDouble("balance");
                        }
                    }
                }
                try (PreparedStatement ps = conn.prepareStatement(
                        "SELECT id, shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
                    ps.setString(1, player.getName());
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) {
                            userId = rs.getInt("id");
                            currentPoints = rs.getInt("shop_points");
                        }
                    }
                }
            } catch (SQLException e) {
                plugin.getLogger().warning("[AetherPacketBridge] Erreur lecture solde: " + e.getMessage());
            }

            final String fResolvedId = resolvedId;
            final String fCategory = category;
            final String fItemName = itemName;
            final int fPricePoints = pricePoints;
            final double fCostCoins = costCoins;
            final int fCurrentPoints = currentPoints;
            final double fCurrentCoins = currentCoins;

            if (payWithPoints) {
                if (fCurrentPoints < fPricePoints) {
                    plugin.getLogger().warning("[Security] Suspicious purchase attempt by " + player.getName() +
                            ": insufficient points (" + fCurrentPoints + " < " + fPricePoints + ") for " + rawItemId);
                    Bukkit.getScheduler().runTask(plugin, () -> {
                        if (player.isOnline()) {
                            player.sendMessage(ChatColor.RED + "❌ Solde de points insuffisant ! Il vous faut " + fPricePoints + " points (Solde : " + fCurrentPoints + " pts).");
                            player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                        }
                    });
                    return;
                }
            } else {
                if (fCurrentCoins < fCostCoins) {
                    plugin.getLogger().warning("[Security] Suspicious purchase attempt by " + player.getName() +
                            ": insufficient coins (" + (int) fCurrentCoins + " < " + (int) fCostCoins + ") for " + rawItemId);
                    Bukkit.getScheduler().runTask(plugin, () -> {
                        if (player.isOnline()) {
                            player.sendMessage(ChatColor.RED + "❌ Solde insuffisant ! Il vous faut " + (int) fCostCoins + " ⛃ Pièces (Solde : " + (int) fCurrentCoins + " ⛃).");
                            player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                        }
                    });
                    return;
                }
            }

            boolean txSuccess = false;
            try (Connection c = AetherDatabase.getConnection()) {
                c.setAutoCommit(false);
                try {
                    int uid = AetherTreeMilestoneDistributor.getOrCreateUserId(c, player.getName());
                    if (payWithPoints) {
                        try (PreparedStatement ps = c.prepareStatement(
                                "UPDATE users SET shop_points = shop_points - ? WHERE id = ? AND shop_points >= ?")) {
                            ps.setInt(1, fPricePoints);
                            ps.setInt(2, uid);
                            ps.setInt(3, fPricePoints);
                            int affected = ps.executeUpdate();
                            if (affected == 0) {
                                c.rollback();
                                Bukkit.getScheduler().runTask(plugin, () -> {
                                    if (player.isOnline()) player.sendMessage(ChatColor.RED + "❌ Transaction annulée : solde de points insuffisant.");
                                });
                                return;
                            }
                        }
                    } else {
                        try (PreparedStatement ps = c.prepareStatement(
                                "UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?) AND balance >= ?")) {
                            ps.setDouble(1, fCostCoins);
                            ps.setString(2, player.getName());
                            ps.setDouble(3, fCostCoins);
                            int affected = ps.executeUpdate();
                            if (affected == 0) {
                                c.rollback();
                                Bukkit.getScheduler().runTask(plugin, () -> {
                                    if (player.isOnline()) player.sendMessage(ChatColor.RED + "❌ Transaction annulée : solde de pièces insuffisant.");
                                });
                                return;
                            }
                        }
                    }

                    try (PreparedStatement ps = c.prepareStatement(
                            "INSERT OR IGNORE INTO user_unlocked_items (user_id, minecraft_username, item_id, item_category, item_name, icon, image_url, unlocked_at, source) " +
                            "VALUES (?, ?, ?, ?, ?, '✦', ?, datetime('now'), 'PACKET_BRIDGE')")) {
                        ps.setInt(1, uid);
                        ps.setString(2, player.getName());
                        ps.setString(3, fResolvedId);
                        ps.setString(4, fCategory);
                        ps.setString(5, fItemName);
                        ps.setString(6, "/static/images/items/" + fResolvedId + ".png");
                        ps.executeUpdate();
                    }

                    try (PreparedStatement ps = c.prepareStatement(
                            "INSERT INTO store_orders (order_id, username, total, currency, items_json, status, rcon_executed, created_at) " +
                            "VALUES (?, ?, ?, ?, ?, 'LIVRE', 1, datetime('now'))")) {
                        ps.setString(1, "PKT-" + (System.currentTimeMillis() % 10000000));
                        ps.setString(2, player.getName());
                        ps.setDouble(3, payWithPoints ? fPricePoints : fCostCoins);
                        ps.setString(4, payWithPoints ? "POINTS" : "COINS");
                        ps.setString(5, "[{\"id\":\"" + fResolvedId + "\"}]");
                        ps.executeUpdate();
                    }

                    if ("grades".equalsIgnoreCase(fCategory) || fResolvedId.startsWith("rank_")) {
                        String rankName = fResolvedId.replace("rank_", "").toUpperCase(Locale.ROOT);
                        try (PreparedStatement ps = c.prepareStatement(
                                "UPDATE players SET rank = ? WHERE LOWER(username) = LOWER(?)")) {
                            ps.setString(1, rankName);
                            ps.setString(2, player.getName());
                            ps.executeUpdate();
                        }
                    }

                    c.commit();
                    txSuccess = true;
                } catch (SQLException ex) {
                    c.rollback();
                    plugin.getLogger().warning("[AetherPacketBridge] Rollback transaction achat: " + ex.getMessage());
                    Bukkit.getScheduler().runTask(plugin, () -> {
                        if (player.isOnline()) player.sendMessage(ChatColor.RED + "❌ Erreur base de données lors de la finalisation de l'achat.");
                    });
                    return;
                }
            } catch (SQLException e) {
                plugin.getLogger().warning("[AetherPacketBridge] Erreur connexion SQLite: " + e.getMessage());
                Bukkit.getScheduler().runTask(plugin, () -> {
                    if (player.isOnline()) player.sendMessage(ChatColor.RED + "❌ Erreur interne lors de la transaction.");
                });
                return;
            }

            if (!txSuccess) return;

            Bukkit.getScheduler().runTask(plugin, () -> {
                if (!player.isOnline()) return;

                if (fResolvedId.contains("vip") || rawItemId.contains("vip")) {
                    if (plugin.getCosmeticsEngine() != null) plugin.getCosmeticsEngine().setAura(player.getUniqueId(), "vip");
                    player.sendMessage(ChatColor.GOLD + "👑 " + ChatColor.GREEN + "Achat réussi ! Rang VIP et Aura activés.");
                } else if (fResolvedId.contains("titan") || rawItemId.contains("titan")) {
                    if (plugin.getCosmeticsEngine() != null) plugin.getCosmeticsEngine().setAura(player.getUniqueId(), "titan");
                    player.sendMessage(ChatColor.RED + "⚡ " + ChatColor.GREEN + "Achat réussi ! Rang Titan et Cimier de feu activés.");
                } else if (fResolvedId.contains("wings") || rawItemId.contains("wings")) {
                    if (plugin.getCosmeticsEngine() != null) plugin.getCosmeticsEngine().setWings(player.getUniqueId(), true);
                    player.getInventory().addItem(CustomItemFactory.createQuantumWingsItem());
                    player.sendMessage(ChatColor.AQUA + "🪽 " + ChatColor.GREEN + "Ailes Quantiques délivrées dans votre inventaire !");
                } else if (fResolvedId.contains("celestial") || rawItemId.contains("celestial") || fResolvedId.contains("mystic")) {
                    int qty = fResolvedId.contains("bundle") ? 5 : 1;
                    player.getInventory().addItem(CustomItemFactory.createCelestialKey(qty));
                    player.sendMessage(ChatColor.LIGHT_PURPLE + "🗝️ " + ChatColor.GREEN + qty + "x Clé(s) Céleste(s) délivrée(s) ! Clic-droit pour l'engager.");
                } else if (fResolvedId.contains("omega") || rawItemId.contains("omega")) {
                    int qty = fResolvedId.contains("bundle") ? 12 : 1;
                    player.getInventory().addItem(CustomItemFactory.createOmegaKey(qty));
                    player.sendMessage(ChatColor.RED + "💎 " + ChatColor.GREEN + qty + "x Clé(s) Oméga délivrée(s) ! Clic-droit pour l'engager.");
                } else if (fResolvedId.contains("booster") || rawItemId.contains("booster")) {
                    player.getInventory().addItem(CustomItemFactory.createMiningBoosterItem());
                    player.sendMessage(ChatColor.YELLOW + "⚡ " + ChatColor.GREEN + "Booster de Minage x2 délivré dans votre inventaire !");
                } else if (fResolvedId.contains("dragon") || rawItemId.contains("dragon")) {
                    if (plugin.getCosmeticsEngine() != null) plugin.getCosmeticsEngine().setPet(player.getUniqueId(), "dragon");
                    player.getInventory().addItem(CustomItemFactory.createDragonPetItem());
                    player.sendMessage(ChatColor.GREEN + "🐾 Familier Dragoneau délivré dans votre inventaire !");
                } else {
                    ItemStack customItem = CustomItemFactory.createItemById(fResolvedId, 1);
                    if (customItem != null) {
                        player.getInventory().addItem(customItem);
                    }
                    player.sendMessage(ChatColor.GREEN + "🛍️ Article " + fItemName + " acheté et synchronisé avec succès !");
                }

                player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);

                if (plugin.getScoreboardManager() != null) {
                    plugin.getScoreboardManager().refreshPlayer(player);
                }

                AetherVisualScoreboardManager.PlayerVisualData pData = AetherVisualScoreboardManager.fetchPlayerData(player.getName());
                syncPlayerData(player, pData.shopPoints, (int) pData.balance, pData.rankId);
            });
        });
    }
}
