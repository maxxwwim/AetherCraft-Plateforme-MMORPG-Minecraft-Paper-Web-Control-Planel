package io.aethercraft.visuals;

import org.bukkit.Material;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Locale;

/**
 * Résolveur de matériaux Minecraft, schéma étendu, Magots Habbo et synchronisation des succès (Monnaie unique Pièces ⛃).
 */
public final class AetherHoloMaterialMapper {

    private AetherHoloMaterialMapper() {}

    public static void ensureExtendedSchema(AetherVisualsPlugin plugin) {
        try (Connection conn = AetherDatabase.getConnection()) {
            try (PreparedStatement ps1 = conn.prepareStatement(
                    "CREATE TABLE IF NOT EXISTS tree_contributions (" +
                    "username TEXT PRIMARY KEY, raw_units INTEGER NOT NULL DEFAULT 0, " +
                    "weighted_points REAL NOT NULL DEFAULT 0.0, last_donation_at TEXT NOT NULL)")) {
                ps1.executeUpdate();
            }
            try (PreparedStatement ps2 = conn.prepareStatement(
                    "CREATE TABLE IF NOT EXISTS tree_tier_rewards_log (" +
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, tier_percent INTEGER NOT NULL, username TEXT NOT NULL, " +
                    "raw_share_percent REAL NOT NULL, effective_share_percent REAL NOT NULL, coins_rewarded REAL NOT NULL, " +
                    "points_rewarded INTEGER NOT NULL, keys_rewarded INTEGER NOT NULL DEFAULT 0, bonus_item TEXT, " +
                    "contributor_count INTEGER NOT NULL DEFAULT 1, rewarded_at TEXT NOT NULL)")) {
                ps2.executeUpdate();
            }
            try (PreparedStatement ps3 = conn.prepareStatement(
                    "ALTER TABLE player_market_listings ADD COLUMN material_id TEXT DEFAULT 'ENDER_CHEST'")) {
                ps3.executeUpdate();
            } catch (Exception ignored) {}
            try (PreparedStatement ps4 = conn.prepareStatement(
                    "ALTER TABLE community_goals ADD COLUMN last_tier_reached INTEGER NOT NULL DEFAULT 0")) {
                ps4.executeUpdate();
            } catch (Exception ignored) {}

            seedHabboMagotsInStore(conn);
        } catch (Exception e) {
            plugin.getLogger().warning("[HoloData] Erreur vérification schéma étendu : " + e.getMessage());
        }
    }

    private static void seedHabboMagotsInStore(Connection conn) {
        Object[][] magots = {
            {"magot_piece_bronze", "magots", "🪙 Pièce de Bronze (10 ⛃)", "COMMUN", 1.0, 1, "Magot Habbo convertible à tout moment en +10 ⛃ Pièces (Clic-Droit)."},
            {"magot_piece_argent", "magots", "🪙 Pièce d'Argent (50 ⛃)", "RARE", 5.0, 5, "Magot Habbo convertible à tout moment en +50 ⛃ Pièces (Clic-Droit)."},
            {"magot_sac_pieces", "magots", "💰 Sac de Pièces (100 ⛃)", "RARE", 10.0, 10, "Bloc d'argent Habbo convertible en +100 ⛃ Pièces (Clic-Droit)."},
            {"magot_lingot_or", "magots", "🧈 Lingot d'Or Habbo (250 ⛃)", "EPIQUE", 25.0, 25, "Lingot d'Or Habbo convertible en +250 ⛃ Pièces (Clic-Droit)."},
            {"magot_bloc_or", "magots", "🟨 Bloc d'Or Impérial (500 ⛃)", "LEGENDAIRE", 50.0, 50, "Bloc d'Or Habbo convertible en +500 ⛃ Pièces (Clic-Droit)."},
            {"magot_bloc_emeraude", "magots", "🟩 Magot Émeraude (1000 ⛃)", "MYTHIQUE", 100.0, 100, "Magot Suprême Habbo convertible en +1000 ⛃ Pièces (Clic-Droit)."}
        };
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT OR REPLACE INTO store_items (id, category, name, rarity, price, price_points, icon, image_url, description, rcon_commands, is_active) " +
                "VALUES (?, ?, ?, ?, ?, ?, '🪙', '/static/images/items/magot.png', ?, '[]', 1)")) {
            for (Object[] m : magots) {
                ps.setString(1, (String) m[0]);
                ps.setString(2, (String) m[1]);
                ps.setString(3, (String) m[2]);
                ps.setString(4, (String) m[3]);
                ps.setDouble(5, (Double) m[4]);
                ps.setInt(6, (Integer) m[5]);
                ps.setString(7, (String) m[6]);
                ps.addBatch();
            }
            ps.executeBatch();
        } catch (Exception ignored) {}
    }

    public static void syncAchievementsInConn(Connection conn, int userId, String rank, double coins) {
        try {
            unlockAchInternal(conn, userId, "ach_first_steps");
            if ("CHAMPION".equalsIgnoreCase(rank)) unlockAchInternal(conn, userId, "ach_crowned_champion");
            if (coins >= 10000.0) unlockAchInternal(conn, userId, "ach_market_baron");
            try (PreparedStatement ps = conn.prepareStatement("SELECT item_id FROM user_unlocked_items WHERE user_id = ?")) {
                ps.setInt(1, userId);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        String id = rs.getString("item_id");
                        if (id != null && id.startsWith("pet_")) unlockAchInternal(conn, userId, "ach_stellar_tamer");
                        if (id != null && (id.startsWith("aura_") || id.startsWith("booster_"))) {
                            unlockAchInternal(conn, userId, "ach_vault_sentinel");
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
    }

    private static void unlockAchInternal(Connection conn, int userId, String achId) throws Exception {
        try (PreparedStatement chk = conn.prepareStatement("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?")) {
            chk.setInt(1, userId);
            chk.setString(2, achId);
            try (ResultSet rs = chk.executeQuery()) { if (rs.next()) return; }
        }
        int pts = 0;
        try (PreparedStatement q = conn.prepareStatement("SELECT reward_points FROM achievements WHERE id = ?")) {
            q.setString(1, achId);
            try (ResultSet rs = q.executeQuery()) { if (rs.next()) pts = rs.getInt(1); }
        }
        try (PreparedStatement ins = conn.prepareStatement(
                "INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, datetime('now'))")) {
            ins.setInt(1, userId);
            ins.setString(2, achId);
            ins.executeUpdate();
        }
        if (pts > 0) {
            try (PreparedStatement upd = conn.prepareStatement(
                    "UPDATE players SET balance = balance + ? WHERE LOWER(username) = (SELECT LOWER(minecraft_username) FROM users WHERE id = ?)")) {
                upd.setDouble(1, pts * 10.0);
                upd.setInt(2, userId);
                upd.executeUpdate();
            }
        }
    }

    public static Material mapShopMaterial(String id) {
        if (id == null) return Material.NETHER_STAR;
        return switch (id.toLowerCase(Locale.ROOT)) {
            case "magot_piece_bronze" -> Material.COPPER_INGOT;
            case "magot_piece_argent" -> Material.IRON_INGOT;
            case "magot_sac_pieces" -> Material.RAW_GOLD_BLOCK;
            case "magot_lingot_or" -> Material.GOLD_INGOT;
            case "magot_bloc_or" -> Material.GOLD_BLOCK;
            case "magot_bloc_emeraude" -> Material.EMERALD_BLOCK;
            case "rank_vip" -> Material.GOLDEN_HELMET;
            case "rank_aether" -> Material.DIAMOND_HELMET;
            case "rank_titan" -> Material.NETHERITE_HELMET;
            case "rank_champion" -> Material.BEACON;
            case "key_mystic_bundle", "key_celestial" -> Material.TRIPWIRE_HOOK;
            case "key_omega_bundle", "key_omega" -> Material.TRIAL_KEY;
            case "cosmetic_wings", "quantum_wings" -> Material.ELYTRA;
            case "aura_champion" -> Material.END_CRYSTAL;
            case "pet_dragon" -> Material.DRAGON_HEAD;
            case "pet_capybara" -> Material.SPORE_BLOSSOM;
            case "pet_fox" -> Material.SWEET_BERRIES;
            case "pet_goat" -> Material.GOAT_HORN;
            case "pet_phoenix" -> Material.BLAZE_ROD;
            case "pet_griffin" -> Material.FEATHER;
            case "animal_cow" -> Material.COW_SPAWN_EGG;
            case "animal_sheep" -> Material.SHEEP_SPAWN_EGG;
            case "animal_pig" -> Material.PIG_SPAWN_EGG;
            case "animal_chicken" -> Material.CHICKEN_SPAWN_EGG;
            case "animal_wolf" -> Material.WOLF_SPAWN_EGG;
            case "animal_horse" -> Material.HORSE_SPAWN_EGG;
            case "animal_bee" -> Material.BEE_SPAWN_EGG;
            case "booster_mining" -> Material.NETHERITE_PICKAXE;
            case "dungeon_pass_bundle" -> Material.ECHO_SHARD;
            default -> Material.NETHER_STAR;
        };
    }

    public static int mapCustomModelData(String id) {
        if (id == null) return 0;
        return switch (id.toLowerCase(Locale.ROOT)) {
            case "magot_piece_bronze" -> 6001;
            case "magot_piece_argent" -> 6002;
            case "magot_sac_pieces" -> 6003;
            case "magot_lingot_or" -> 6004;
            case "magot_bloc_or" -> 6005;
            case "magot_bloc_emeraude" -> 6006;
            default -> {
                if (id.contains("vip")) yield 1001;
                if (id.contains("titan")) yield 1002;
                if (id.contains("aether")) yield 1003;
                if (id.contains("mystic") || id.contains("celestial")) yield 2001;
                if (id.contains("omega")) yield 2002;
                if (id.contains("wings")) yield 3001;
                if (id.contains("dragon")) yield 4001;
                if (id.contains("phoenix")) yield 4002;
                if (id.contains("capybara")) yield 4003;
                if (id.contains("fox")) yield 4004;
                if (id.contains("goat")) yield 4005;
                if (id.contains("booster")) yield 5001;
                yield 0;
            }
        };
    }

    public static Material mapOreBlockMaterial(String oreId) {
        if (oreId == null) return Material.DIAMOND_ORE;
        return switch (oreId.toLowerCase(Locale.ROOT)) {
            case "coal" -> Material.COAL_ORE;
            case "copper" -> Material.COPPER_ORE;
            case "iron" -> Material.IRON_ORE;
            case "gold" -> Material.GOLD_ORE;
            case "lapis" -> Material.LAPIS_ORE;
            case "diamond" -> Material.DIAMOND_ORE;
            case "netherite" -> Material.ANCIENT_DEBRIS;
            case "aetherite" -> Material.CRYING_OBSIDIAN;
            default -> Material.EMERALD_ORE;
        };
    }

    public static Material resolveMaterialFromListing(String materialId, String itemName) {
        if (materialId != null && !materialId.isEmpty()) {
            try {
                Material m = Material.valueOf(materialId.toUpperCase(Locale.ROOT));
                if (m != Material.AIR) return m;
            } catch (Exception ignored) {}
        }
        if (itemName == null) return Material.ENDER_CHEST;
        String lower = itemName.toLowerCase(Locale.ROOT);
        for (Material mat : Material.values()) {
            if (mat.name().equalsIgnoreCase(itemName.trim().replace(' ', '_'))) return mat;
        }
        if (lower.contains("lingot") && lower.contains("or")) return Material.GOLD_INGOT;
        if (lower.contains("piece") || lower.contains("pièce")) return lower.contains("argent") ? Material.IRON_INGOT : Material.COPPER_INGOT;
        if (lower.contains("sac") && lower.contains("or")) return Material.RAW_GOLD_BLOCK;
        if (lower.contains("diamant") || lower.contains("diamond")) return lower.contains("bloc") ? Material.DIAMOND_BLOCK : Material.DIAMOND_ORE;
        if (lower.contains("netherite")) return lower.contains("bloc") ? Material.NETHERITE_BLOCK : Material.ANCIENT_DEBRIS;
        if (lower.contains("aetherite")) return Material.CRYING_OBSIDIAN;
        if (lower.contains("or") || lower.contains("gold")) return lower.contains("bloc") ? Material.GOLD_BLOCK : Material.GOLD_ORE;
        if (lower.contains("fer") || lower.contains("iron")) return lower.contains("bloc") ? Material.IRON_BLOCK : Material.IRON_ORE;
        if (lower.contains("emeraude") || lower.contains("émeraude")) return Material.EMERALD_BLOCK;
        return Material.ENDER_CHEST;
    }
}
