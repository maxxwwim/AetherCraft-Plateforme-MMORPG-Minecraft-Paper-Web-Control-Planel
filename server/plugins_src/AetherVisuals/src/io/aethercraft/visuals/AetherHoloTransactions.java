package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherHoloDataService.*;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.sql.*;
import java.util.*;

import static io.aethercraft.visuals.AetherTreeMilestoneDistributor.*;

/**
 * Moteur de Transactions Atomiques SQLite à Monnaie Unique (⛃ Pièces) & Magots Convertibles Habbo.
 */
public class AetherHoloTransactions {

    private final AetherVisualsPlugin plugin;
    private final AetherHoloDataService dataService;

    public AetherHoloTransactions(AetherVisualsPlugin plugin, AetherHoloDataService dataService) {
        this.plugin = plugin;
        this.dataService = dataService;
    }

    public static class TxResult {
        public final boolean success;
        public final String message;
        public TxResult(boolean success, String message) {
            this.success = success;
            this.message = message;
        }
    }

    public TxResult buyShopItem(Player p, ShopItemData item) {
        if (item == null) return new TxResult(false, "§cArticle introuvable.");
        PlayerProfileData prof = dataService.loadPlayerProfile(p.getName());
        double costCoins = Math.max(1, item.pricePoints) * 10.0;

        if (prof.coins < costCoins) {
            return new TxResult(false, "§cSolde insuffisant ! Il faut §6" + (int) costCoins + " ⛃ Pièces §c(Vous avez §e" + (int) prof.coins + " ⛃§c).");
        }

        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                int userId = getOrCreateUserId(c, p.getName());
                try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance - ? WHERE LOWER(username)=LOWER(?)")) {
                    ps.setDouble(1, costCoins);
                    ps.setString(2, p.getName());
                    ps.executeUpdate();
                }
                if (!"magots".equalsIgnoreCase(item.category)) {
                    try (PreparedStatement ps = c.prepareStatement(
                            "INSERT OR IGNORE INTO user_unlocked_items (user_id, minecraft_username, item_id, item_category, item_name, icon, image_url, unlocked_at, source) VALUES (?, ?, ?, ?, ?, '✦', ?, datetime('now'), 'HOLO_SHOP')")) {
                        ps.setInt(1, userId);
                        ps.setString(2, p.getName());
                        ps.setString(3, item.id);
                        ps.setString(4, item.category);
                        ps.setString(5, item.name);
                        ps.setString(6, "/static/images/items/" + item.id + ".png");
                        ps.executeUpdate();
                    }
                }
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO store_orders (order_id, username, total, currency, items_json, status, rcon_executed, created_at) VALUES (?, ?, ?, 'COINS', ?, 'LIVRE', 1, datetime('now'))")) {
                    ps.setString(1, "HOLO-" + (System.currentTimeMillis() % 1000000));
                    ps.setString(2, p.getName());
                    ps.setDouble(3, costCoins);
                    ps.setString(4, "[{\"id\":\"" + item.id + "\"}]");
                    ps.executeUpdate();
                }
                if ("grades".equalsIgnoreCase(item.category) || item.id.startsWith("rank_")) {
                    try (PreparedStatement ps = c.prepareStatement("UPDATE players SET rank=? WHERE LOWER(username)=LOWER(?)")) {
                        ps.setString(1, item.id.replace("rank_", "").toUpperCase(Locale.ROOT));
                        ps.setString(2, p.getName());
                        ps.executeUpdate();
                    }
                }
                c.commit();
            } catch (SQLException ex) { c.rollback(); throw ex; }
        } catch (SQLException e) {
            return new TxResult(false, "§cErreur SQLite lors de l'achat : " + e.getMessage());
        }

        deliverShopPurchaseInGame(plugin, p, item);
        if ("magots".equalsIgnoreCase(item.category) || item.id.startsWith("magot_")) {
            return new TxResult(true, "§a✔ Magot reçu : §e§l" + item.name + " §7(-" + (int) costCoins + " ⛃ Pièces) §8• §aClic-Droit en main pour reconvertir !");
        }
        return new TxResult(true, "§a✔ Achat réussi : §e§l" + item.name + " §7(-" + (int) costCoins + " ⛃ Pièces) !");
    }

    public TxResult buyMarketListing(Player buyer, MarketListingData listing) {
        if (listing == null) return new TxResult(false, "§cAnnonce introuvable.");
        if (listing.seller.equalsIgnoreCase(buyer.getName())) return new TxResult(false, "§cVous ne pouvez pas acheter votre propre annonce !");
        PlayerProfileData prof = dataService.loadPlayerProfile(buyer.getName());
        if (prof.coins < listing.priceCoins) {
            return new TxResult(false, "§cSolde insuffisant ! Prix : §6" + (int) listing.priceCoins + " ⛃ Pièces §c(Votre solde : §e" + (int) prof.coins + " ⛃§c).");
        }

        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                try (PreparedStatement check = c.prepareStatement("SELECT status FROM player_market_listings WHERE id=?")) {
                    check.setString(1, listing.id);
                    try (ResultSet rs = check.executeQuery()) {
                        if (!rs.next() || !"ACTIVE".equalsIgnoreCase(rs.getString("status"))) {
                            c.rollback();
                            return new TxResult(false, "§cCette annonce vient d'être vendue ou retirée !");
                        }
                    }
                }
                try (PreparedStatement ps = c.prepareStatement("UPDATE player_market_listings SET status='SOLD' WHERE id=?")) {
                    ps.setString(1, listing.id);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance - ? WHERE LOWER(username)=LOWER(?)")) {
                    ps.setDouble(1, listing.priceCoins);
                    ps.setString(2, buyer.getName());
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                    ps.setDouble(1, listing.priceCoins);
                    ps.setString(2, listing.seller);
                    ps.executeUpdate();
                }
                c.commit();
            } catch (SQLException ex) { c.rollback(); throw ex; }
        } catch (SQLException e) {
            return new TxResult(false, "§cErreur SQLite HDV : " + e.getMessage());
        }

        Material mat = AetherHoloDataService.resolveMaterialFromListing(listing.materialId, listing.itemName);
        ItemStack given = new ItemStack(mat, Math.max(1, Math.min(64, listing.quantity)));
        ItemMeta meta = given.getItemMeta();
        if (meta != null) {
            meta.setDisplayName("§e" + listing.itemName);
            meta.setLore(Arrays.asList("§7Acheté à §f" + listing.seller + " §7sur l'HDV", "§7Prix payé : §6" + (int) listing.priceCoins + " ⛃ Pièces"));
            given.setItemMeta(meta);
        }
        buyer.getInventory().addItem(given);
        buyer.playSound(buyer.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1.0f, 1.2f);

        Player sellerOnline = Bukkit.getPlayerExact(listing.seller);
        if (sellerOnline != null && sellerOnline.isOnline()) {
            sellerOnline.sendMessage("§6§l[HDV] §aVotre lot §e" + listing.quantity + "x " + listing.itemName + " §aa été acheté par §f" + buyer.getName() + " §apour §6+" + (int) listing.priceCoins + " ⛃ Pièces §a!");
            sellerOnline.playSound(sellerOnline.getLocation(), Sound.ENTITY_VILLAGER_YES, 1.0f, 1.2f);
        }
        return new TxResult(true, "§a✔ Achat HDV réussi : §f" + listing.quantity + "x " + listing.itemName + " §7(-" + (int) listing.priceCoins + " ⛃ Pièces) !");
    }

    public TxResult sellHeldItem(Player seller, double price) {
        ItemStack inHand = seller.getInventory().getItemInMainHand();
        if (inHand == null || inHand.getType() == Material.AIR || inHand.getAmount() <= 0) {
            return new TxResult(false, "§cTenez un bloc ou un objet dans votre main principale pour le mettre en vente !");
        }
        if (price < 1 || price > 10_000_000) return new TxResult(false, "§cPrix invalide (entre 1 et 10 000 000 ⛃ Pièces).");
        String matName = inHand.getType().name();
        int qty = inHand.getAmount();
        String displayName = (inHand.hasItemMeta() && inHand.getItemMeta() != null && inHand.getItemMeta().hasDisplayName())
                ? inHand.getItemMeta().getDisplayName().replaceAll("§[0-9a-fk-or]", "")
                : formatMaterialTitle(matName);

        try (Connection c = AetherDatabase.getConnection();
             PreparedStatement ps = c.prepareStatement(
                     "INSERT INTO player_market_listings (id, seller_username, item_name, item_icon, image_url, quantity, price_coins, is_troc, wanted_item, created_at, status, material_id) VALUES (?, ?, ?, '🧱', ?, ?, ?, 0, NULL, datetime('now'), 'ACTIVE', ?)")) {
            ps.setString(1, "MKT-" + (System.currentTimeMillis() % 10000000));
            ps.setString(2, seller.getName());
            ps.setString(3, displayName);
            ps.setString(4, "/api/minecraft/block-icon/" + matName.toLowerCase(Locale.ROOT) + ".png");
            ps.setInt(5, qty);
            ps.setDouble(6, price);
            ps.setString(7, matName);
            ps.executeUpdate();
        } catch (SQLException e) {
            return new TxResult(false, "§cErreur SQLite lors de la mise en vente : " + e.getMessage());
        }
        seller.getInventory().setItemInMainHand(null);
        seller.playSound(seller.getLocation(), Sound.BLOCK_ANVIL_USE, 0.7f, 1.4f);
        return new TxResult(true, "§a✔ Mis en vente sur l'HDV : §f" + qty + "x " + displayName + " §apour §6" + (int) price + " ⛃ Pièces §a!");
    }

    public TxResult sellPlayerOres(Player p, OreData ore) {
        if (ore == null || ore.material == null) return new TxResult(false, "§cMinerai invalide.");
        Material rawAlt = resolveRawOrIngotAlt(ore.id, ore.material);
        int countMat = countMaterialInInventory(p, ore.material);
        Material chosenMat = ore.material;
        if (countMat <= 0 && rawAlt != null) { countMat = countMaterialInInventory(p, rawAlt); chosenMat = rawAlt; }
        if (countMat <= 0) return new TxResult(false, "§cVous n'avez aucun §f" + ore.name + " §cdans votre inventaire !");

        int sellQty = Math.min(countMat, 64);
        removeMaterialFromInventory(p, chosenMat, sellQty);
        double payout = Math.round(sellQty * ore.price * 10.0) / 10.0;
        double weightedGain = sellQty * Math.max(1.0, ore.price / 10.0);
        List<String> milestoneAlerts = new ArrayList<>();

        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                    ps.setDouble(1, payout);
                    ps.setString(2, p.getName());
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("UPDATE ores_market SET total_traded = total_traded + ? WHERE id=?")) {
                    ps.setInt(1, sellQty);
                    ps.setString(2, ore.id);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO tree_contributions (username, raw_units, weighted_points, last_donation_at) VALUES (?, ?, ?, datetime('now')) " +
                        "ON CONFLICT(username) DO UPDATE SET raw_units = raw_units + excluded.raw_units, weighted_points = weighted_points + excluded.weighted_points, last_donation_at = datetime('now')")) {
                    ps.setString(1, p.getName());
                    ps.setInt(2, sellQty);
                    ps.setDouble(3, weightedGain);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("UPDATE community_goals SET current_amount = MIN(target_amount, current_amount + ?) WHERE id='s4_celestial_tree'")) {
                    ps.setInt(1, sellQty);
                    ps.executeUpdate();
                }
                milestoneAlerts.addAll(checkAndDistributeTreeMilestones(c));
                c.commit();
            } catch (SQLException ex) { c.rollback(); throw ex; }
        } catch (SQLException e) {
            return new TxResult(false, "§cErreur Bourse/Arbre : " + e.getMessage());
        }

        p.playSound(p.getLocation(), Sound.BLOCK_AMETHYST_BLOCK_CHIME, 1.0f, 1.3f);
        for (String alert : milestoneAlerts) Bukkit.broadcastMessage(alert);
        return new TxResult(true, "§a✔ Vendu §f" + sellQty + "x " + ore.name + " §apour §6+" + (int) payout + " ⛃ Pièces §7(& §2+" + sellQty + " 🌳 Arbre Céleste§7) !");
    }

    public TxResult claimOrProgressQuest(Player p, QuestData q) {
        if (q == null) return new TxResult(false, "§cQuête introuvable.");
        if ("RECLAMEE".equalsIgnoreCase(q.status)) return new TxResult(false, "§eVous avez déjà réclamé la récompense de cette quête !");

        double totalCoinsReward = q.rewardCoins + (q.rewardPoints * 10.0);
        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                int userId = getOrCreateUserId(c, p.getName());
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO user_quests (user_id, quest_id, current_count, target_count, status, claimed_at, updated_at) VALUES (?, ?, ?, ?, 'RECLAMEE', datetime('now'), datetime('now')) " +
                        "ON CONFLICT(user_id, quest_id) DO UPDATE SET current_count=?, status='RECLAMEE', claimed_at=datetime('now'), updated_at=datetime('now')")) {
                    ps.setInt(1, userId);
                    ps.setString(2, q.id);
                    ps.setInt(3, q.targetCount);
                    ps.setInt(4, q.targetCount);
                    ps.setInt(5, q.targetCount);
                    ps.executeUpdate();
                }
                if (totalCoinsReward > 0) {
                    try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                        ps.setDouble(1, totalCoinsReward);
                        ps.setString(2, p.getName());
                        ps.executeUpdate();
                    }
                }
                c.commit();
            } catch (SQLException ex) { c.rollback(); throw ex; }
        } catch (SQLException e) {
            return new TxResult(false, "§cErreur Quête : " + e.getMessage());
        }

        if (q.rewardItemId != null && !q.rewardItemId.isEmpty()) p.getInventory().addItem(CustomItemFactory.createItemById(q.rewardItemId, 1));
        p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.25f);
        return new TxResult(true, "§a✔ Quête §e" + q.title + " §aréclamée : §6+" + (int) totalCoinsReward + " ⛃ Pièces §a!");
    }

    public int syncPlayerAchievements(Player p) {
        return dataService.loadPlayerProfile(p.getName()).unlockedAchCount;
    }
}
