package io.aethercraft.visuals;

import org.bukkit.Material;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.*;

/**
 * Service de données SQLite unifié pour les interfaces holographiques 3D Paper 1.21.1.
 */
public class AetherHoloDataService {

    private final AetherVisualsPlugin plugin;

    public AetherHoloDataService(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        ensureExtendedSchema();
    }

    public void ensureExtendedSchema() { AetherHoloMaterialMapper.ensureExtendedSchema(plugin); }

    public static class PlayerProfileData {
        public String username, rank = "JOUEUR", guild = "Aventurier";
        public double coins = 1000.0, treeSharePct = 0.0;
        public int points = 10, kills = 0, deaths = 0, hoursPlayed = 1, treeUnits = 0, treeCurrent = 0, treeTarget = 50000;
        public int unlockedItemsCount = 0, unlockedAchCount = 0, totalAchCount = 6;
    }

    public static class ShopItemData {
        public String id, category, name, rarity, description;
        public int pricePoints, customModelData;
        public double priceEur;
        public Material material;
        public boolean unlocked;
    }

    public static class MarketListingData {
        public String id, seller, itemName, materialId, wantedItem;
        public int quantity;
        public double priceCoins;
        public boolean isTroc;
    }

    public static class OreData {
        public String id, name, rarity;
        public double price;
        public int totalTraded;
        public Material material;
    }

    public static class AchievementData {
        public String id, title, description, rarity, rewardTitle;
        public int rewardPoints;
        public boolean unlocked;
    }

    public static class QuestData {
        public String id, title, description, category, status, rewardItemId, rewardItemName;
        public int currentCount, targetCount, rewardPoints;
        public double rewardCoins;
    }

    public PlayerProfileData loadPlayerProfile(String username) {
        PlayerProfileData data = new PlayerProfileData();
        data.username = username;
        try (Connection conn = AetherDatabase.getConnection()) {
            try (PreparedStatement ps = conn.prepareStatement("SELECT rank, guild, balance, kills, deaths, hours_played FROM players WHERE LOWER(username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) {
                        data.rank = rs.getString("rank"); data.guild = rs.getString("guild"); data.coins = rs.getDouble("balance");
                        data.kills = rs.getInt("kills"); data.deaths = rs.getInt("deaths"); data.hoursPlayed = rs.getInt("hours_played");
                    } else {
                        try (PreparedStatement ins = conn.prepareStatement(
                                "INSERT OR IGNORE INTO players (uuid, username, rank, balance, hours_played, kills, deaths, is_online, guild, first_join, last_seen) VALUES (?, ?, 'JOUEUR', 1000.0, 1, 0, 0, 1, 'Aventurier', datetime('now'), datetime('now'))")) {
                            ins.setString(1, UUID.randomUUID().toString()); ins.setString(2, username); ins.executeUpdate();
                        }
                    }
                }
            }
            int userId = -1;
            try (PreparedStatement ps = conn.prepareStatement("SELECT id, shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) { userId = rs.getInt("id"); data.points = rs.getInt("shop_points"); } }
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT current_amount, target_amount FROM community_goals WHERE id = 's4_celestial_tree'"); ResultSet rs = ps.executeQuery()) {
                if (rs.next()) { data.treeCurrent = rs.getInt("current_amount"); data.treeTarget = Math.max(1, rs.getInt("target_amount")); }
            }
            double totalWeighted = 0.0;
            try (PreparedStatement ps = conn.prepareStatement("SELECT SUM(weighted_points) as total_w FROM tree_contributions"); ResultSet rs = ps.executeQuery()) {
                if (rs.next()) totalWeighted = rs.getDouble("total_w");
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT raw_units, weighted_points FROM tree_contributions WHERE LOWER(username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) {
                        data.treeUnits = rs.getInt("raw_units");
                        double w = rs.getDouble("weighted_points");
                        data.treeSharePct = (totalWeighted > 0) ? (w / totalWeighted) * 100.0 : 0.0;
                    }
                }
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT COUNT(*) FROM user_unlocked_items WHERE LOWER(minecraft_username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) data.unlockedItemsCount = rs.getInt(1); }
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT COUNT(*) FROM achievements"); ResultSet rs = ps.executeQuery()) {
                if (rs.next()) data.totalAchCount = rs.getInt(1);
            }
            if (userId > 0) {
                AetherHoloMaterialMapper.syncAchievementsInConn(conn, userId, data.rank, data.coins);
                try (PreparedStatement ps = conn.prepareStatement("SELECT COUNT(*) FROM user_achievements WHERE user_id = ?")) {
                    ps.setInt(1, userId);
                    try (ResultSet rs = ps.executeQuery()) { if (rs.next()) data.unlockedAchCount = rs.getInt(1); }
                }
            } else data.unlockedAchCount = 1;
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadPlayerProfile: " + e.getMessage()); }
        return data;
    }

    public List<ShopItemData> loadShopItems(String username, String categoryFilter) {
        List<ShopItemData> list = new ArrayList<>();
        Set<String> unlockedSet = new HashSet<>();
        try (Connection conn = AetherDatabase.getConnection()) {
            try (PreparedStatement ps = conn.prepareStatement("SELECT item_id FROM user_unlocked_items WHERE LOWER(minecraft_username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { while (rs.next()) unlockedSet.add(rs.getString("item_id")); }
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT id, category, name, rarity, price, price_points, description FROM store_items WHERE is_active = 1 ORDER BY price_points ASC"); ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String cat = rs.getString("category");
                    if (categoryFilter != null && !categoryFilter.equalsIgnoreCase("all") && !cat.equalsIgnoreCase(categoryFilter)) continue;
                    ShopItemData item = new ShopItemData();
                    item.id = rs.getString("id"); item.category = cat; item.name = rs.getString("name"); item.rarity = rs.getString("rarity");
                    item.priceEur = rs.getDouble("price"); item.pricePoints = rs.getInt("price_points"); item.description = rs.getString("description");
                    item.material = mapShopMaterial(item.id); item.customModelData = mapCustomModelData(item.id); item.unlocked = unlockedSet.contains(item.id);
                    list.add(item);
                }
            }
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadShopItems: " + e.getMessage()); }
        return list;
    }

    public List<MarketListingData> loadActiveMarketListings() {
        List<MarketListingData> list = new ArrayList<>();
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT id, seller_username, item_name, material_id, quantity, price_coins, is_troc, wanted_item FROM player_market_listings WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 30");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                MarketListingData d = new MarketListingData();
                d.id = rs.getString("id"); d.seller = rs.getString("seller_username"); d.itemName = rs.getString("item_name");
                d.materialId = rs.getString("material_id"); d.quantity = rs.getInt("quantity"); d.priceCoins = rs.getDouble("price_coins");
                d.isTroc = rs.getInt("is_troc") == 1; d.wantedItem = rs.getString("wanted_item");
                list.add(d);
            }
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadActiveMarketListings: " + e.getMessage()); }
        return list;
    }

    public List<OreData> loadOresMarket() {
        List<OreData> list = new ArrayList<>();
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT id, name, current_price, total_traded, rarity FROM ores_market ORDER BY base_price ASC");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                OreData o = new OreData();
                o.id = rs.getString("id"); o.name = rs.getString("name"); o.price = rs.getDouble("current_price");
                o.totalTraded = rs.getInt("total_traded"); o.rarity = rs.getString("rarity"); o.material = mapOreBlockMaterial(o.id);
                list.add(o);
            }
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadOresMarket: " + e.getMessage()); }
        return list;
    }

    public List<AchievementData> loadAchievements(String username) {
        List<AchievementData> list = new ArrayList<>();
        Set<String> unlockedIds = new HashSet<>();
        try (Connection conn = AetherDatabase.getConnection()) {
            int userId = -1;
            try (PreparedStatement ps = conn.prepareStatement("SELECT id FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) userId = rs.getInt("id"); }
            }
            if (userId > 0) {
                try (PreparedStatement ps = conn.prepareStatement("SELECT achievement_id FROM user_achievements WHERE user_id = ?")) {
                    ps.setInt(1, userId);
                    try (ResultSet rs = ps.executeQuery()) { while (rs.next()) unlockedIds.add(rs.getString(1)); }
                }
            } else unlockedIds.add("ach_first_steps");
            try (PreparedStatement ps = conn.prepareStatement("SELECT id, title, description, rarity, reward_points, reward_title FROM achievements ORDER BY order_index ASC"); ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    AchievementData a = new AchievementData();
                    a.id = rs.getString("id"); a.title = rs.getString("title"); a.description = rs.getString("description");
                    a.rarity = rs.getString("rarity"); a.rewardPoints = rs.getInt("reward_points"); a.rewardTitle = rs.getString("reward_title");
                    a.unlocked = unlockedIds.contains(a.id);
                    list.add(a);
                }
            }
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadAchievements: " + e.getMessage()); }
        return list;
    }

    public List<QuestData> loadQuests(String username) {
        List<QuestData> list = new ArrayList<>();
        try (Connection conn = AetherDatabase.getConnection()) {
            int userId = -1;
            try (PreparedStatement ps = conn.prepareStatement("SELECT id FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) userId = rs.getInt("id"); }
            }
            Map<String, int[]> progMap = new HashMap<>();
            Map<String, String> statusMap = new HashMap<>();
            if (userId > 0) {
                try (PreparedStatement ps = conn.prepareStatement("SELECT quest_id, current_count, target_count, status FROM user_quests WHERE user_id = ?")) {
                    ps.setInt(1, userId);
                    try (ResultSet rs = ps.executeQuery()) {
                        while (rs.next()) {
                            String qid = rs.getString("quest_id");
                            progMap.put(qid, new int[]{rs.getInt("current_count"), rs.getInt("target_count")});
                            statusMap.put(qid, rs.getString("status"));
                        }
                    }
                }
            }
            try (PreparedStatement ps = conn.prepareStatement("SELECT id, title, description, category, target_count, reward_coins, reward_points, reward_item_id, reward_item_name FROM quests ORDER BY order_index ASC"); ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    QuestData q = new QuestData();
                    q.id = rs.getString("id"); q.title = rs.getString("title"); q.description = rs.getString("description");
                    q.category = rs.getString("category"); q.targetCount = rs.getInt("target_count"); q.rewardCoins = rs.getDouble("reward_coins");
                    q.rewardPoints = rs.getInt("reward_points"); q.rewardItemId = rs.getString("reward_item_id"); q.rewardItemName = rs.getString("reward_item_name");
                    int[] p = progMap.get(q.id);
                    q.currentCount = (p != null) ? p[0] : 0; q.status = statusMap.getOrDefault(q.id, "EN_COURS");
                    list.add(q);
                }
            }
        } catch (Exception e) { plugin.getLogger().warning("[HoloData] loadQuests: " + e.getMessage()); }
        return list;
    }

    public List<AetherVisualScoreboardManager.LeaderboardEntry> loadLeaderboard(String category) {
        if ("fortune".equalsIgnoreCase(category)) {
            return AetherVisualScoreboardManager.getTopFortune(6);
        } else if ("kills".equalsIgnoreCase(category)) {
            return AetherVisualScoreboardManager.getTopKills(6);
        } else if ("playtime".equalsIgnoreCase(category)) {
            return AetherVisualScoreboardManager.getTopPlaytime(6);
        } else {
            return AetherVisualScoreboardManager.getTopOneBlock(6);
        }
    }

    public List<ShopItemData> loadAnimalShopItems(String username, String subFilter) {
        List<ShopItemData> list = new ArrayList<>();
        boolean includePets = (subFilter == null || subFilter.equalsIgnoreCase("familiers") || subFilter.equalsIgnoreCase("all"));
        boolean includeFarm = (subFilter != null && (subFilter.equalsIgnoreCase("ferme") || subFilter.equalsIgnoreCase("elevage") || subFilter.equalsIgnoreCase("all")));

        if (includePets) {
            list.addAll(loadShopItems(username, "pets"));
        }
        if (includeFarm) {
            String[][] farmDefs = {
                {"animal_cow", "ferme", "Couple de Vaches", "Élevage & Lait", "30"},
                {"animal_sheep", "ferme", "Couple de Moutons", "Laine & Tonte", "25"},
                {"animal_pig", "ferme", "Couple de Cochons", "Élevage OneBlock", "20"},
                {"animal_chicken", "ferme", "Couple de Poules", "Œufs & Plumes", "15"},
                {"animal_wolf", "ferme", "Loup Domestique", "Compagnon Garde", "50"},
                {"animal_horse", "ferme", "Cheval Pur-Sang", "Monture Rapide", "80"},
                {"animal_bee", "ferme", "Essaim d'Abeilles", "Pollinisation", "60"}
            };
            for (String[] def : farmDefs) {
                ShopItemData it = new ShopItemData();
                it.id = def[0];
                it.category = def[1];
                it.name = def[2];
                it.description = def[3];
                it.rarity = "COMMUN";
                it.pricePoints = Integer.parseInt(def[4]);
                it.priceEur = it.pricePoints / 10.0;
                it.material = mapShopMaterial(it.id);
                it.customModelData = mapCustomModelData(it.id);
                it.unlocked = false;
                list.add(it);
            }
        }
        return list;
    }

    public static Material mapShopMaterial(String id) { return AetherHoloMaterialMapper.mapShopMaterial(id); }
    public static int mapCustomModelData(String id) { return AetherHoloMaterialMapper.mapCustomModelData(id); }
    public static Material mapOreBlockMaterial(String oreId) { return AetherHoloMaterialMapper.mapOreBlockMaterial(oreId); }
    public static Material resolveMaterialFromListing(String materialId, String itemName) { return AetherHoloMaterialMapper.resolveMaterialFromListing(materialId, itemName); }
}
