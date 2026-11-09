package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.Statistic;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scheduler.BukkitTask;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur Intelligent de Mémorisation des Positions de Survie.
 * Évite les requêtes excessives grâce à un cache mémoire haute performance (ConcurrentHashMap).
 * Persistance asynchrone par lots dans SQLite uniquement lors des déconnexions ou du flush périodique.
 * Élimine les téléportations inutiles et intempestives.
 */
public class PlayerLocationEngine implements Listener, CommandExecutor {

    private final AetherVisualsPlugin plugin;
    private final SpawnProtectionEngine protectionEngine;

    // Cache mémoire ultra-rapide (Zéro requête DB lors des déplacements en jeu)
    private final Map<UUID, Location> lastSurvivalLocations = new ConcurrentHashMap<>();
    private final Map<UUID, Location> deathLocations = new ConcurrentHashMap<>();
    private final Set<UUID> dirtyLocations = ConcurrentHashMap.newKeySet();

    private BukkitTask flushTask;
    private final String dbUrl;

    public PlayerLocationEngine(AetherVisualsPlugin plugin, SpawnProtectionEngine protectionEngine) {
        this.plugin = plugin;
        this.protectionEngine = protectionEngine;
        this.dbUrl = "jdbc:sqlite:" + AetherDatabase.getDatabaseFile().getAbsolutePath();

        initDatabase();
        loadAllCachedLocations();
        startPeriodicFlush();
    }

    private void initDatabase() {
        try (Connection conn = DriverManager.getConnection(dbUrl);
             Statement stmt = conn.createStatement()) {
            stmt.execute("CREATE TABLE IF NOT EXISTS player_survival_locations (" +
                    "uuid TEXT PRIMARY KEY, " +
                    "username TEXT, " +
                    "world TEXT, " +
                    "x REAL, " +
                    "y REAL, " +
                    "z REAL, " +
                    "yaw REAL, " +
                    "pitch REAL, " +
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" +
                    ")");
        } catch (Throwable t) {
            plugin.getLogger().warning("Erreur initialisation table player_survival_locations: " + t.getMessage());
        }
    }

    public boolean isValidSurvivalLocation(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        if (!loc.getWorld().getName().equalsIgnoreCase("world")) return false;
        double dx = loc.getX() - SpawnProtectionEngine.SPAWN1_CENTER_X;
        double dz = loc.getZ() - SpawnProtectionEngine.SPAWN1_CENTER_Z;
        // Interdit toute position dans ou sous l'Agora Céleste (rayon 250 blocs)
        if ((dx * dx + dz * dz) < 250.0 * 250.0) return false;
        // Interdit formellement toute position dans l'arène du Donjon Céleste (2000, 2000)
        double ddx = loc.getX() - DungeonWaveEngine.ARENA_X;
        double ddz = loc.getZ() - DungeonWaveEngine.ARENA_Z;
        if ((ddx * ddx + ddz * ddz) < 100.0 * 100.0) return false;
        // Interdit toute position sur les îles OneBlock (zone isolée >= 9000)
        if (loc.getX() >= 9000 && loc.getZ() >= 9000) return false;
        // Altitude valide dans le monde survie
        if (loc.getY() < 55 || loc.getY() > 260) return false;
        // Hors esplanade protégée du spawn de survie
        if (protectionEngine != null && protectionEngine.isInSpawn2(loc)) return false;
        return true;
    }

    private void loadAllCachedLocations() {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = DriverManager.getConnection(dbUrl);
                 PreparedStatement ps = conn.prepareStatement("SELECT uuid, world, x, y, z, yaw, pitch FROM player_survival_locations");
                 ResultSet rs = ps.executeQuery()) {
                int count = 0;
                while (rs.next()) {
                    try {
                        UUID uid = UUID.fromString(rs.getString("uuid"));
                        World w = Bukkit.getWorld(rs.getString("world"));
                        if (w != null) {
                            Location loc = new Location(w, rs.getDouble("x"), rs.getDouble("y"),
                                    rs.getDouble("z"), rs.getFloat("yaw"), rs.getFloat("pitch"));
                            if (isValidSurvivalLocation(loc)) {
                                lastSurvivalLocations.put(uid, loc);
                                count++;
                            } else {
                                deleteSurvivalLocationAsync(uid);
                            }
                        }
                    } catch (Exception ignored) {}
                }
                plugin.getLogger().info("✦ [PlayerLocationEngine] " + count + " positions de survie valides préchargées !");
            } catch (Throwable ignored) {}
        });
    }

    public void deleteSurvivalLocationAsync(UUID uid) {
        if (uid == null) return;
        lastSurvivalLocations.remove(uid);
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = DriverManager.getConnection(dbUrl);
                 PreparedStatement ps = conn.prepareStatement("DELETE FROM player_survival_locations WHERE uuid = ?")) {
                ps.setString(1, uid.toString());
                ps.executeUpdate();
            } catch (Throwable ignored) {}
        });
    }

    private void startPeriodicFlush() {
        this.flushTask = Bukkit.getScheduler().runTaskTimerAsynchronously(plugin, this::saveDirtyLocationsAsync, 20L * 120, 20L * 120);
    }

    public void recordSurvivalLocation(Player player) {
        if (player == null || !player.isOnline()) return;
        Location loc = player.getLocation();
        if (!isValidSurvivalLocation(loc)) return;
        lastSurvivalLocations.put(player.getUniqueId(), loc.clone());
        dirtyLocations.add(player.getUniqueId());
    }

    public Location getLastSurvivalLocation(UUID uuid) {
        Location loc = lastSurvivalLocations.get(uuid);
        if (loc != null && !isValidSurvivalLocation(loc)) {
            deleteSurvivalLocationAsync(uuid);
            return null;
        }
        return loc;
    }

    public boolean hasSavedSurvivalLocation(UUID uuid) {
        return getLastSurvivalLocation(uuid) != null;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerTeleport(PlayerTeleportEvent event) {
        Location from = event.getFrom();
        if (isValidSurvivalLocation(from)) {
            lastSurvivalLocations.put(event.getPlayer().getUniqueId(), from.clone());
            dirtyLocations.add(event.getPlayer().getUniqueId());
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerDeath(PlayerDeathEvent event) {
        Player player = event.getEntity();
        Location deathLoc = player.getLocation().clone();
        deathLocations.put(player.getUniqueId(), deathLoc);
        if (isValidSurvivalLocation(deathLoc)) {
            lastSurvivalLocations.put(player.getUniqueId(), deathLoc);
            dirtyLocations.add(player.getUniqueId());
        }

        // F8: Synchronisation des kills et des deaths dans SQLite
        final UUID victimUuid = player.getUniqueId();
        final Player killer = player.getKiller();
        final UUID killerUuid = (killer != null) ? killer.getUniqueId() : null;

        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = DriverManager.getConnection(dbUrl)) {
                try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET deaths = deaths + 1 WHERE uuid = ?")) {
                    ps.setString(1, victimUuid.toString());
                    ps.executeUpdate();
                }
                if (killerUuid != null) {
                    try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET kills = kills + 1 WHERE uuid = ?")) {
                        ps.setString(1, killerUuid.toString());
                        ps.executeUpdate();
                    }
                }
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur synchronisation kills/deaths lors du décès: " + t.getMessage());
            }
        });
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerJoin(PlayerJoinEvent event) {
        syncPlayerStatisticsAsync(event.getPlayer());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        recordSurvivalLocation(player);
        savePlayerLocationAsync(player);
        syncPlayerStatisticsAsync(player);
    }

    public void syncPlayerStatisticsAsync(Player player) {
        if (player == null) return;
        final UUID uid = player.getUniqueId();
        final int deaths = player.getStatistic(Statistic.DEATHS);
        final int kills = player.getStatistic(Statistic.PLAYER_KILLS);

        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = DriverManager.getConnection(dbUrl);
                 PreparedStatement ps = conn.prepareStatement(
                         "UPDATE players SET kills = MAX(kills, ?), deaths = MAX(deaths, ?) WHERE uuid = ?")) {
                ps.setInt(1, kills);
                ps.setInt(2, deaths);
                ps.setString(3, uid.toString());
                ps.executeUpdate();
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur réconciliation statistiques: " + t.getMessage());
            }
        });
    }

    private void savePlayerLocationAsync(Player player) {
        Location loc = lastSurvivalLocations.get(player.getUniqueId());
        if (loc == null || !isValidSurvivalLocation(loc)) return;

        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = DriverManager.getConnection(dbUrl);
                 PreparedStatement ps = conn.prepareStatement(
                         "INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch, updated_at) " +
                                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) " +
                                 "ON CONFLICT(uuid) DO UPDATE SET " +
                                 "username = excluded.username, world = excluded.world, x = excluded.x, y = excluded.y, " +
                                 "z = excluded.z, yaw = excluded.yaw, pitch = excluded.pitch, updated_at = CURRENT_TIMESTAMP")) {
                ps.setString(1, player.getUniqueId().toString());
                ps.setString(2, player.getName());
                ps.setString(3, loc.getWorld().getName());
                ps.setDouble(4, loc.getX());
                ps.setDouble(5, loc.getY());
                ps.setDouble(6, loc.getZ());
                ps.setFloat(7, loc.getYaw());
                ps.setFloat(8, loc.getPitch());
                ps.executeUpdate();
                dirtyLocations.remove(player.getUniqueId());
            } catch (Throwable ignored) {}
        });
    }

    private void persistDirtyLocations() {
        if (dirtyLocations.isEmpty()) return;
        for (UUID uid : dirtyLocations) {
            Location loc = lastSurvivalLocations.get(uid);
            if (loc == null || !isValidSurvivalLocation(loc)) continue;
            try (Connection conn = DriverManager.getConnection(dbUrl);
                 PreparedStatement ps = conn.prepareStatement(
                         "INSERT INTO player_survival_locations (uuid, username, world, x, y, z, yaw, pitch, updated_at) " +
                                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) " +
                                 "ON CONFLICT(uuid) DO UPDATE SET " +
                                 "world = excluded.world, x = excluded.x, y = excluded.y, " +
                                 "z = excluded.z, yaw = excluded.yaw, pitch = excluded.pitch, updated_at = CURRENT_TIMESTAMP")) {
                Player p = Bukkit.getPlayer(uid);
                String name = p != null ? p.getName() : uid.toString();
                ps.setString(1, uid.toString());
                ps.setString(2, name);
                ps.setString(3, loc.getWorld().getName());
                ps.setDouble(4, loc.getX());
                ps.setDouble(5, loc.getY());
                ps.setDouble(6, loc.getZ());
                ps.setFloat(7, loc.getYaw());
                ps.setFloat(8, loc.getPitch());
                ps.executeUpdate();
            } catch (Throwable ignored) {}
        }
        dirtyLocations.clear();
    }

    public void saveDirtyLocationsAsync() {
        persistDirtyLocations();
    }

    public void saveDirtyLocationsSync() {
        persistDirtyLocations();
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut exécuter la commande /back.");
            return true;
        }

        Player player = (Player) sender;
        Location last = lastSurvivalLocations.get(player.getUniqueId());

        if (last == null) {
            player.sendMessage(ChatColor.RED + "❌ Aucun emplacement de survie précédent enregistré.");
            return true;
        }

        player.sendMessage(ChatColor.AQUA + "⚡ Téléportation vers votre dernier emplacement de survie...");
        player.teleportAsync(last).thenRun(() -> {
            player.playSound(last, Sound.ENTITY_ENDERMAN_TELEPORT, 1.0f, 1.2f);
            player.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 6, 2, false, false, true));
            player.sendTitle(ChatColor.GREEN + "✦ De retour", ChatColor.GRAY + "Position restaurée", 5, 25, 10);
        });
        return true;
    }

    public void onDisable() {
        if (flushTask != null) {
            flushTask.cancel();
        }
        saveDirtyLocationsSync();
    }
}
