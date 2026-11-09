package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.scoreboard.DisplaySlot;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.ScoreboardManager;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Gestionnaire unifié des affichages in-game :
 * - Tablist (Header, Footer avec compteur en ligne, préfixe de rang dynamique)
 * - Scoreboard latéral interactif (Pseudo, Rang, Solde réel, Points boutique, En ligne)
 * - Synchronisation asynchrone directe avec SQLite aethercraft.db
 */
public class AetherVisualScoreboardManager implements Listener {

    private final AetherVisualsPlugin plugin;
    private BukkitTask refreshTask;

    public static class PlayerVisualData {
        public final String rankId;
        public final String prefix;
        public final String badgeColor;
        public final double balance;
        public final int shopPoints;

        public PlayerVisualData(String rankId, String prefix, String badgeColor, double balance, int shopPoints) {
            this.rankId = (rankId != null && !rankId.isEmpty()) ? rankId : "JOUEUR";
            this.prefix = (prefix != null && !prefix.isEmpty()) ? prefix : "[Joueur]";
            this.badgeColor = (badgeColor != null && !badgeColor.isEmpty()) ? badgeColor : "slate";
            this.balance = balance;
            this.shopPoints = shopPoints;
        }
    }

    public static class LeaderboardEntry {
        public final String username;
        public final double value;
        public final String rankId;
        public final String prefix;
        public final String badgeColor;

        public LeaderboardEntry(String username, double value, String rankId, String prefix, String badgeColor) {
            this.username = username;
            this.value = value;
            this.rankId = rankId;
            this.prefix = prefix;
            this.badgeColor = badgeColor;
        }

        public String getFormattedPrefix() {
            return AetherVisualScoreboardManager.getRankFormattedPrefix(rankId, prefix, badgeColor);
        }
    }

    public AetherVisualScoreboardManager(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public void start() {
        // Rafraîchissement périodique toutes les 5 secondes (100 ticks)
        this.refreshTask = Bukkit.getScheduler().runTaskTimer(plugin, this::refreshAllOnlinePlayers, 20L, 100L);
    }

    public void stop() {
        if (refreshTask != null) {
            refreshTask.cancel();
            refreshTask = null;
        }
    }

    @EventHandler
    public void onPlayerJoin(PlayerJoinEvent event) {
        Player p = event.getPlayer();
        // Délai de 10 ticks pour laisser le temps au client de finaliser la connexion
        Bukkit.getScheduler().runTaskLater(plugin, () -> refreshPlayer(p), 10L);
        // Rafraîchir les compteurs 'en ligne' de tous les joueurs connectés
        Bukkit.getScheduler().runTaskLater(plugin, this::refreshAllOnlinePlayers, 20L);
    }

    @EventHandler
    public void onPlayerQuit(PlayerQuitEvent event) {
        // Mettre à jour le décompte des joueurs restants
        Bukkit.getScheduler().runTaskLater(plugin, this::refreshAllOnlinePlayers, 5L);
    }

    public void refreshAllOnlinePlayers() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (p != null && p.isOnline()) {
                refreshPlayer(p);
            }
        }
    }

    public void refreshPlayer(Player player) {
        if (player == null || !player.isOnline()) return;

        final String username = player.getName();
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            PlayerVisualData data = fetchPlayerData(username);
            Bukkit.getScheduler().runTask(plugin, () -> {
                if (player.isOnline()) {
                    applyTablist(player, data);
                    applyScoreboard(player, data);
                }
            });
        });
    }

    public static PlayerVisualData fetchPlayerData(String username) {
        if (username == null || username.trim().isEmpty()) {
            return new PlayerVisualData("JOUEUR", "[Joueur]", "slate", 0.0, 0);
        }
        String sql = "SELECT p.rank, p.balance, r.prefix, r.badge_color, COALESCE(u.shop_points, 0) AS shop_points " +
                     "FROM players p " +
                     "LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) " +
                     "LEFT JOIN users u ON LOWER(u.minecraft_username) = LOWER(p.username) " +
                     "WHERE LOWER(p.username) = LOWER(?)";

        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, username.trim());
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    String rank = rs.getString("rank");
                    String prefix = rs.getString("prefix");
                    String badge = rs.getString("badge_color");
                    double balance = rs.getDouble("balance");
                    int shopPoints = rs.getInt("shop_points");
                    return new PlayerVisualData(rank, prefix, badge, balance, shopPoints);
                }
            }
        } catch (SQLException ignored) {}

        // Fallback si le joueur est inscrit dans users sans ligne players
        String sqlUsers = "SELECT shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?)";
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(sqlUsers)) {
            ps.setString(1, username.trim());
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    int pts = rs.getInt("shop_points");
                    return new PlayerVisualData("JOUEUR", "[Joueur]", "slate", 0.0, pts);
                }
            }
        } catch (SQLException ignored) {}

        return new PlayerVisualData("JOUEUR", "[Joueur]", "slate", 0.0, 0);
    }

    public static String getRankFormattedPrefix(String rankId, String dbPrefix, String badgeColor) {
        String color = "§7";
        if (badgeColor != null && !badgeColor.isEmpty()) {
            switch (badgeColor.toLowerCase()) {
                case "emerald", "green" -> color = "§a";
                case "sky", "aqua", "blue" -> color = "§b";
                case "amber", "gold", "yellow" -> color = "§6";
                case "violet", "purple" -> color = "§d";
                case "rose", "red" -> color = "§c";
                default -> color = "§7";
            }
        } else if (rankId != null && !rankId.isEmpty()) {
            switch (rankId.toUpperCase()) {
                case "VIP" -> color = "§a";
                case "AETHER" -> color = "§b";
                case "TITAN" -> color = "§6";
                case "CHAMPION" -> color = "§d";
                case "CREATEUR" -> color = "§c";
                default -> color = "§7";
            }
        }
        String pfx = (dbPrefix != null && !dbPrefix.isEmpty()) ? dbPrefix : "[" + (rankId != null ? rankId : "Joueur") + "]";
        return color + pfx;
    }

    private void applyTablist(Player player, PlayerVisualData data) {
        // Header & Footer conformes aux spécifications F10
        String header = "§6✦ §lAETHERCRAFT §6✦\n§7Archipel Céleste 1.21.1";
        int online = Bukkit.getOnlinePlayers().size();
        int max = Bukkit.getMaxPlayers();
        String footer = String.format("§e✦ Boutique: §faethercraft.io §8| §bJoueurs: §f%d/%d", online, max);

        player.setPlayerListHeaderFooter(header, footer);

        // Formatage du nom dans le Tablist avec préfixe de rang SQLite
        String rankFormatted = getRankFormattedPrefix(data.rankId, data.prefix, data.badgeColor);
        player.setPlayerListName(rankFormatted + " §f" + player.getName());
    }

    private void applyScoreboard(Player player, PlayerVisualData data) {
        ScoreboardManager sm = Bukkit.getScoreboardManager();
        if (sm == null) return;

        Scoreboard sb = player.getScoreboard();
        if (sb == null || sb == sm.getMainScoreboard()) {
            sb = sm.getNewScoreboard();
            player.setScoreboard(sb);
        }

        Objective obj = sb.getObjective("aether_sidebar");
        if (obj != null) {
            obj.unregister();
        }
        obj = sb.registerNewObjective("aether_sidebar", "dummy", "§6§l✦ AETHERCRAFT ✦");
        obj.setDisplaySlot(DisplaySlot.SIDEBAR);

        String rankFormatted = getRankFormattedPrefix(data.rankId, data.prefix, data.badgeColor);
        long balInt = Math.round(data.balance);
        String balStr = (data.balance == balInt) ? String.valueOf(balInt) : String.format("%.2f", data.balance);
        int online = Bukkit.getOnlinePlayers().size();

        // Lignes du Scoreboard (ordre décroissant des scores)
        obj.getScore("§7------------------").setScore(8);
        obj.getScore("§fPseudo: §e" + player.getName()).setScore(7);
        obj.getScore("§fRang: " + rankFormatted).setScore(6);
        obj.getScore("§fSolde: §6" + balStr + " ⛃").setScore(5);
        obj.getScore("§fPoints: §b" + data.shopPoints).setScore(4);
        obj.getScore("§fEn ligne: §a" + online).setScore(3);
        obj.getScore("§8------------------").setScore(2);
        obj.getScore("§ewww.aethercraft.io").setScore(1);
    }

    // =========================================================================
    // Méthodes pour les requêtes de classements réels SQLite (/top, /baltop, etc.)
    // =========================================================================

    public static List<LeaderboardEntry> getTopFortune(int limit) {
        return queryLeaderboard("fortune", limit);
    }

    public static List<LeaderboardEntry> getTopPlaytime(int limit) {
        return queryLeaderboard("p.hours_played", limit);
    }

    public static List<LeaderboardEntry> getTopKills(int limit) {
        return queryLeaderboard("p.kills", limit);
    }

    public static List<LeaderboardEntry> getTopOneBlock(int limit) {
        List<LeaderboardEntry> result = new ArrayList<>();
        String sql = "SELECT ob.username, ob.blocks_broken AS val, COALESCE(p.rank, 'JOUEUR') as rank, r.prefix, r.badge_color " +
                     "FROM player_oneblock ob " +
                     "LEFT JOIN players p ON LOWER(ob.username) = LOWER(p.username) " +
                     "LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) " +
                     "ORDER BY ob.blocks_broken DESC " +
                     "LIMIT ?";
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, Math.max(1, limit));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String username = rs.getString("username");
                    double val = rs.getDouble("val");
                    String rank = rs.getString("rank");
                    String prefix = rs.getString("prefix");
                    String badge = rs.getString("badge_color");
                    result.add(new LeaderboardEntry(username, val, rank, prefix, badge));
                }
            }
        } catch (SQLException e) {
            Bukkit.getLogger().warning("[AetherVisuals] Erreur classement OneBlock : " + e.getMessage());
        }
        return result;
    }

    private static List<LeaderboardEntry> queryLeaderboard(String orderByColumn, int limit) {
        List<LeaderboardEntry> result = new ArrayList<>();
        // Whitelist stricte de colonnes pour prévenir toute injection
        String validOrderCol;
        if ("p.hours_played".equals(orderByColumn)) {
            validOrderCol = "p.hours_played";
        } else if ("p.kills".equals(orderByColumn)) {
            validOrderCol = "p.kills";
        } else {
            validOrderCol = "(p.balance + COALESCE(b.bank_coins, 0.0))";
        }

        String sql = "SELECT p.username, " + validOrderCol + " AS val, p.rank, r.prefix, r.badge_color " +
                     "FROM players p " +
                     "LEFT JOIN ranks r ON UPPER(p.rank) = UPPER(r.id) " +
                     "LEFT JOIN player_bank_accounts b ON LOWER(p.username) = LOWER(b.username) " +
                     "ORDER BY " + validOrderCol + " DESC " +
                     "LIMIT ?";

        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, Math.max(1, limit));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String username = rs.getString("username");
                    double val = rs.getDouble("val");
                    String rank = rs.getString("rank");
                    String prefix = rs.getString("prefix");
                    String badge = rs.getString("badge_color");
                    result.add(new LeaderboardEntry(username, val, rank, prefix, badge));
                }
            }
        } catch (SQLException e) {
            Bukkit.getLogger().warning("[AetherVisuals] Erreur requête classement : " + e.getMessage());
        }
        return result;
    }
}
