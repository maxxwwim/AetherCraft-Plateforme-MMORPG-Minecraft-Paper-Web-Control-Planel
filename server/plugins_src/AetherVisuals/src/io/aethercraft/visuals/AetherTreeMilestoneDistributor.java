package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherHoloDataService.ShopItemData;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Moteur de distribution mathématique Anti-Cheat pour chaque palier de l'Arbre Céleste (25%, 50%, 75%, 100%)
 * et utilitaires d'inventaire/livraison pour AetherHoloTransactions.
 */
public final class AetherTreeMilestoneDistributor {

    private AetherTreeMilestoneDistributor() {}

    public static List<String> checkAndDistributeTreeMilestones(Connection c) throws SQLException {
        List<String> broadcasts = new ArrayList<>();
        int current = 0, target = 50000, lastTier = 0;

        try (PreparedStatement ps = c.prepareStatement(
                "SELECT current_amount, target_amount, COALESCE(last_tier_reached, 0) as lt FROM community_goals WHERE id='s4_celestial_tree'");
             ResultSet rs = ps.executeQuery()) {
            if (rs.next()) {
                current = rs.getInt("current_amount");
                target = Math.max(1, rs.getInt("target_amount"));
                lastTier = rs.getInt("lt");
            }
        }

        int pct = (int) Math.floor((current * 100.0) / target);
        for (int tier : new int[]{25, 50, 75, 100}) {
            if (pct >= tier && lastTier < tier) {
                distributeSingleTier(c, tier, broadcasts);
                try (PreparedStatement up = c.prepareStatement("UPDATE community_goals SET last_tier_reached=?, is_completed=? WHERE id='s4_celestial_tree'")) {
                    up.setInt(1, tier);
                    up.setInt(2, tier >= 100 ? 1 : 0);
                    up.executeUpdate();
                }
                lastTier = tier;
            }
        }
        return broadcasts;
    }

    private static void distributeSingleTier(Connection c, int tierPct, List<String> broadcasts) throws SQLException {
        double baseCoinsPool = switch (tierPct) { case 25 -> 10000.0; case 50 -> 25000.0; case 75 -> 50000.0; default -> 100000.0; };
        int basePointsPool = switch (tierPct) { case 25 -> 250; case 50 -> 600; case 75 -> 1200; default -> 2500; };

        List<DonorRow> donors = new ArrayList<>();
        double totalWeighted = 0, sumSqrt = 0;

        try (PreparedStatement ps = c.prepareStatement(
                "SELECT username, raw_units, weighted_points FROM tree_contributions WHERE weighted_points > 0 ORDER BY weighted_points DESC");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                double w = rs.getDouble("weighted_points");
                donors.add(new DonorRow(rs.getString("username"), rs.getInt("raw_units"), w));
                totalWeighted += w;
                sumSqrt += Math.sqrt(w);
            }
        }

        if (donors.isEmpty() || totalWeighted <= 0) return;
        int n = donors.size();
        double scaleFactor = Math.min(1.0, 0.35 + (0.15 * n));
        double maxIndividualShare = (n == 1) ? 0.35 : (n == 2 ? 0.45 : 0.60);

        broadcasts.add("§2§l🌳 [ARBRE CÉLESTE] §aLe Palier §e§l" + tierPct + "% §aa été atteint ! Distribution Anti-Cheat aux §f" + n + " §acontributeurs :");

        for (DonorRow d : donors) {
            double rawShare = d.weighted / totalWeighted;
            double sqrtShare = sumSqrt > 0 ? (Math.sqrt(d.weighted) / sumSqrt) : rawShare;
            double effectiveShare = Math.min(maxIndividualShare, ((0.70 * rawShare) + (0.30 * sqrtShare)) * scaleFactor);

            double coinsReward = Math.max(50.0, Math.round(baseCoinsPool * effectiveShare));
            int pointsReward = Math.max(5, (int) Math.round(basePointsPool * effectiveShare));
            int keysReward = (effectiveShare >= 0.15) ? (tierPct >= 75 ? 2 : 1) : 0;

            try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                ps.setDouble(1, coinsReward);
                ps.setString(2, d.username);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement("UPDATE users SET shop_points = shop_points + ? WHERE LOWER(minecraft_username)=LOWER(?)")) {
                ps.setInt(1, pointsReward);
                ps.setString(2, d.username);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO tree_tier_rewards_log (tier_percent, username, raw_share_percent, effective_share_percent, coins_rewarded, points_rewarded, keys_rewarded, bonus_item, contributor_count, rewarded_at) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))")) {
                ps.setInt(1, tierPct);
                ps.setString(2, d.username);
                ps.setDouble(3, Math.round(rawShare * 1000.0) / 10.0);
                ps.setDouble(4, Math.round(effectiveShare * 1000.0) / 10.0);
                ps.setDouble(5, coinsReward);
                ps.setInt(6, pointsReward);
                ps.setInt(7, keysReward);
                ps.setString(8, keysReward > 0 ? "key_mystic_bundle" : "none");
                ps.setInt(9, n);
                ps.executeUpdate();
            }
            broadcasts.add(String.format(" §8▪ §a%s §7(Don: §e%.1f%% §8➔ §7Part: §b%.1f%%§7) §f➔ §6+%d ⛃ §7& §d+%d 💎",
                    d.username, rawShare * 100.0, effectiveShare * 100.0, (int) coinsReward, pointsReward));
        }
    }

    public static void deliverShopPurchaseInGame(AetherVisualsPlugin plugin, Player p, ShopItemData item) {
        String id = item.id.toLowerCase(Locale.ROOT);
        CosmeticsEngine cos = plugin.getCosmeticsEngine();
        if (id.startsWith("pet_")) {
            if (cos != null) cos.setPet(p.getUniqueId(), id.replace("pet_", ""));
            p.sendMessage("§6§l[FAMILIER 3D] §eVotre compagnon volumétrique 3D §f" + item.name + " §ea été invoqué à vos côtés !");
        } else if (id.contains("wings")) {
            if (cos != null) cos.setWings(p.getUniqueId(), true);
            p.sendMessage("§d§l[COSMÉTIQUE] §fVos ailes §e" + item.name + " §fsont désormais équipées !");
        } else if (id.startsWith("aura_")) {
            if (cos != null) cos.setAura(p.getUniqueId(), id.replace("aura_", ""));
            p.sendMessage("§b§l[COSMÉTIQUE] §fVotre aura §e" + item.name + " §fbrille autour de vous !");
        } else {
            p.getInventory().addItem(CustomItemFactory.createItemById(item.id, 1));
        }
        p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 0.9f, 1.2f);
    }

    public static int getOrCreateUserId(Connection c, String username) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("SELECT id FROM users WHERE LOWER(minecraft_username)=LOWER(?)")) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) { if (rs.next()) return rs.getInt(1); }
        }
        try (PreparedStatement ins = c.prepareStatement(
                "INSERT INTO users (email, password_hash, salt, minecraft_username, shop_points, created_at) VALUES (?, 'ingame', 'ingame', ?, 10, datetime('now'))",
                Statement.RETURN_GENERATED_KEYS)) {
            ins.setString(1, username.toLowerCase(Locale.ROOT) + "@aethercraft.io");
            ins.setString(2, username);
            ins.executeUpdate();
            try (ResultSet rs = ins.getGeneratedKeys()) { if (rs.next()) return rs.getInt(1); }
        }
        return 1;
    }

    public static Material resolveRawOrIngotAlt(String oreId, Material primary) {
        if (oreId == null) return primary;
        return switch (oreId.toLowerCase(Locale.ROOT)) {
            case "coal" -> Material.COAL;
            case "copper" -> Material.COPPER_INGOT;
            case "iron" -> Material.IRON_INGOT;
            case "gold" -> Material.GOLD_INGOT;
            case "lapis" -> Material.LAPIS_LAZULI;
            case "diamond" -> Material.DIAMOND;
            case "netherite" -> Material.NETHERITE_INGOT;
            case "aetherite" -> Material.AMETHYST_SHARD;
            default -> primary;
        };
    }

    public static int countMaterialInInventory(Player p, Material mat) {
        int total = 0;
        for (ItemStack stack : p.getInventory().getContents()) {
            if (stack != null && stack.getType() == mat) total += stack.getAmount();
        }
        return total;
    }

    public static void removeMaterialFromInventory(Player p, Material mat, int amountToRemove) {
        int remaining = amountToRemove;
        ItemStack[] contents = p.getInventory().getContents();
        for (int i = 0; i < contents.length && remaining > 0; i++) {
            ItemStack stack = contents[i];
            if (stack != null && stack.getType() == mat) {
                int take = Math.min(remaining, stack.getAmount());
                stack.setAmount(stack.getAmount() - take);
                remaining -= take;
                if (stack.getAmount() <= 0) p.getInventory().setItem(i, null);
            }
        }
    }

    public static String formatMaterialTitle(String matName) {
        StringBuilder sb = new StringBuilder();
        for (String part : matName.toLowerCase(Locale.ROOT).split("_")) {
            if (part.isEmpty()) continue;
            if (sb.length() > 0) sb.append(" ");
            sb.append(Character.toUpperCase(part.charAt(0))).append(part.substring(1));
        }
        return sb.toString();
    }

    private record DonorRow(String username, int rawUnits, double weighted) {}
}
